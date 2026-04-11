"""FastAPI backend entry point for the AI Portfolio Analyser."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import logging
from math import sqrt
from typing import List

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.ai_resolver import ai_resolve_ticker
from backend.ai_agent import generate_portfolio_swot
from backend.data_fetcher import (
	get_current_price,
	get_historical_returns,
	get_ticker_metadata,
	normalize_ticker,
)
from backend.diversification import calculate_diversification
from backend.portfolio_engine import calculate_portfolio_score
from backend.recommendation_engine import generate_swot_with_groq
from backend.rebalance import simulate_rebalance
from backend.risk_metrics import (
	calculate_portfolio_risk_metrics,
	compute_alpha,
	compute_beta,
	compute_daily_change,
	compute_portfolio_annual_return,
	select_benchmark,
)
from backend.sector_analysis import calculate_sector_exposure, infer_asset_class
from backend.simulation import simulate_portfolio_growth_intervals


logger = logging.getLogger(__name__)


class AssetInput(BaseModel):
	ticker: str = Field(..., min_length=1, description="Asset ticker symbol")
	quantity: float = Field(
		...,
		ge=0.0,
		description="Asset quantity used for market-value based weighting",
	)


class AnalyzePortfolioRequest(BaseModel):
	assets: List[AssetInput] = Field(..., min_length=1)


class RebalanceAssetInput(BaseModel):
	ticker: str = Field(..., min_length=1, description="Asset class or ticker name")
	weight: float = Field(..., ge=0.0, description="Target allocation weight")


class RebalanceRequest(BaseModel):
	assets: List[RebalanceAssetInput] = Field(..., min_length=1)
	total_value: float | None = Field(
		default=100_000.0,
		ge=0.0,
		description="Optional portfolio total used by clients for context",
	)


app = FastAPI(title="AI Portfolio Analyser API", version="1.0.0")

app.add_middleware(
	CORSMiddleware,
	allow_origins=[
		"http://localhost:3000",
		"https://ai-folio-analyser.vercel.app",
		"https://ai-portfolio-analyser-akash7-8s-projects.vercel.app",
	],
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
	"""Simple health endpoint."""
	return {"status": "ok"}


@app.post("/analyze_portfolio")
@app.post("/analyze_portfolio/")
@app.post("/analyser_portfolio")
@app.post("/analyser_portfolio/")
async def analyze_portfolio(payload: AnalyzePortfolioRequest) -> dict:
	"""Analyze a portfolio and return diversification, score, risk, and SWOT."""
	raw_tickers = [asset.ticker for asset in payload.assets]
	normalized_tickers = _normalize_tickers_parallel(raw_tickers)
	quantity_map: dict[str, float] = {}
	for ticker, asset in zip(normalized_tickers, payload.assets):
		quantity_map[ticker] = quantity_map.get(ticker, 0.0) + float(asset.quantity)
	data_warnings: list[str] = []
	fetched_data = await _fetch_current_prices_for_tickers(list(quantity_map.keys()), data_warnings)

	total_value = sum(
		float(fetched_data[ticker]["current_price"]) * quantity
		for ticker, quantity in quantity_map.items()
		if ticker in fetched_data
	)
	if not total_value or total_value <= 0:
		total_value = 100_000.0

	weights_by_ticker = {
		ticker: (float(fetched_data[ticker]["current_price"]) * quantity) / total_value
		for ticker, quantity in quantity_map.items()
		if ticker in fetched_data
	}
	if not weights_by_ticker:
		raise HTTPException(
			status_code=400,
			detail="Unable to derive portfolio weights from quantities and live prices",
		)

	asset_entries = [
		{"ticker": ticker, "weight": weight}
		for ticker, weight in weights_by_ticker.items()
	]
	normalized_asset_entries = [
		{"ticker": normalize_ticker(str(asset["ticker"])), "weight": float(asset["weight"])}
		for asset in asset_entries
	]
	weights = [asset["weight"] for asset in asset_entries]

	try:
		hhi_score, diversification_score = calculate_diversification(weights)
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc

	try:
		(
			expected_return,
			portfolio_volatility,
			history_warnings,
			risk_metrics,
			portfolio_returns,
		) = _compute_portfolio_metrics(asset_entries)
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(
			status_code=502,
			detail=f"Failed to fetch market data: {exc}",
		) from exc
	data_warnings.extend(history_warnings)

	scoring_result = calculate_portfolio_score(
		diversification_score=diversification_score,
		expected_return_cagr=expected_return,
		portfolio_risk_volatility=portfolio_volatility,
	)
	annual_return = compute_portfolio_annual_return(weights_by_ticker, fetched_data)

	sim_expected_return = _normalize_simulation_rate(float(annual_return))
	if not (0.0 < sim_expected_return < 0.5):
		sim_expected_return = 0.08
	sim_volatility = _normalize_simulation_rate(portfolio_volatility)
	if not (0.0 < sim_volatility < 0.5):
		sim_volatility = 0.12

	initial_investment = float(total_value)

	simulation = simulate_portfolio_growth_intervals(
		initial_investment=initial_investment,
		expected_annual_return=sim_expected_return,
		annual_volatility=sim_volatility,
		years=2,
		num_simulations=10_000,
		interval_months=2,
	)
	final_point = simulation[-1] if simulation else {"p10": total_value, "p50": total_value, "p90": total_value}
	simulation_summary = {
		"worst_case": float(final_point["p10"]),
		"median_value": float(final_point["p50"]),
		"best_case": float(final_point["p90"]),
	}

	try:
		sector_exposure = await calculate_sector_exposure(
			normalized_asset_entries,
			auto_update_map=True,
		)
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc

	explanation = generate_portfolio_swot(
		diversification_score=diversification_score,
		portfolio_score=float(scoring_result["portfolio_score"]),
		risk_level=str(scoring_result["risk_level"]),
		sector_exposure=sector_exposure,
		simulation_results=simulation_summary,
	)

	benchmark = select_benchmark(list(weights_by_ticker.keys()))
	risk_free_rate = 0.065 if benchmark == "^NSEI" else 0.05
	beta = compute_beta(portfolio_returns, benchmark)
	alpha = compute_alpha(
		portfolio_annual_return=annual_return,
		beta=beta,
		benchmark_ticker=benchmark,
		risk_free_rate=risk_free_rate,
	)
	daily_change = compute_daily_change(weights_by_ticker, total_value, fetched_data)

	recommendation_engine = await generate_swot_with_groq(
		diversification_score=diversification_score,
		sector_exposure=sector_exposure,
		holdings=[
			{
				"ticker": ticker,
				"weight": weights_by_ticker.get(ticker, 0.0),
				"sector": "Unknown",
				"current_price": fetched_data.get(ticker, {}).get("current_price", "N/A"),
			}
			for ticker in weights_by_ticker
		],
		metrics={
			"beta": beta,
			"alpha": alpha,
			"sharpe": float(risk_metrics["sharpe_ratio"]),
			"annualReturn": float(annual_return),
			"hhi_score": float(hhi_score),
			"portfolio_score": float(scoring_result["portfolio_score"]),
			"dailyChangePct": float(daily_change.get("dailyChangePct", 0.0)),
		},
		monte_carlo={
			"p10": float(final_point.get("p10", total_value)),
			"p50": float(final_point.get("p50", total_value)),
			"p90": float(final_point.get("p90", total_value)),
		},
		total_value=float(total_value),
	)

	total_value = round(float(total_value), 2)

	portfolio_score_block = {
		"score": round(float(scoring_result["portfolio_score"]), 2),
		"totalValue": total_value,
		"annualReturn": round(float(annual_return), 6),
		"dailyChangePct": float(daily_change["dailyChangePct"]),
		"dailyChangeDollar": float(daily_change["dailyChangeDollar"]),
		"sharpeRatio": round(float(risk_metrics["sharpe_ratio"]), 2),
		"volatility": round(float(risk_metrics["annualized_volatility"] * 100.0), 2),
		"beta": beta,
		"alpha": alpha,
		"benchmark": benchmark,
		"riskFreeRate": risk_free_rate,
	}

	asset_class_exposure = await _build_asset_class_exposure(normalized_asset_entries)
	diversification_block = {
		"score": round(diversification_score, 2),
		"assetClasses": asset_class_exposure,
	}

	sector_exposure_list = _build_named_value_list(
		sector_exposure,
		use_percentage=True,
	)

	explanation_list = [
		{"type": "positive", "title": "Strength", "text": explanation["strength"]},
		{"type": "warning", "title": "Weakness", "text": explanation["weakness"]},
		{"type": "positive", "title": "Opportunity", "text": explanation["opportunity"]},
		{"type": "negative", "title": "Threat", "text": explanation["threat"]},
	]

	return {
		"portfolio_score": portfolio_score_block,
		"diversification_score": diversification_block,
		"risk_level": str(scoring_result["risk_level"]),
		"annualReturn": round(float(annual_return), 6),
		"benchmark": benchmark,
		"riskFreeRate": risk_free_rate,
		"sector_exposure": sector_exposure_list,
		"simulation": simulation,
		"explanation": explanation_list,
		"recommendation_engine": recommendation_engine,
		"data_warnings": data_warnings,
		"legacy": {
			"diversification_score": round(diversification_score, 2),
			"portfolio_score": float(scoring_result["portfolio_score"]),
			"risk_metrics": risk_metrics,
			"riskMetrics": {
				"volatility": float(risk_metrics["annualized_volatility"]),
				"sharpeRatio": float(risk_metrics["sharpe_ratio"]),
				"annualReturn": float(annual_return),
				"beta": float(beta),
				"alpha": float(alpha),
				"benchmark": benchmark,
				"riskFreeRate": float(risk_free_rate),
				"maximumDrawdown": float(risk_metrics["maximum_drawdown"]),
			},
			"annualReturn": float(annual_return),
			"volatility": float(risk_metrics["annualized_volatility"]),
			"sharpeRatio": float(risk_metrics["sharpe_ratio"]),
			"beta": float(beta),
			"alpha": float(alpha),
			"simulation": simulation,
			"sector_exposure": sector_exposure,
			"explanation": explanation,
		},
	}


@app.post("/rebalance_simulation")
@app.post("/rebalance_simulation/")
@app.post("/rebalance_simulator")
@app.post("/rebalance_simulator/")
def rebalance_simulation(payload: RebalanceRequest) -> dict:
	"""Run rebalancing simulation and return updated portfolio metrics."""
	asset_entries = _build_rebalance_asset_entries(payload.assets)

	try:
		result = simulate_rebalance(asset_entries)
	except ValueError as exc:
		# Graceful fallback: when market data fetch fails for one or more symbols,
		# return a conservative estimate so frontend flow does not hard-fail.
		message = str(exc)
		message_lower = message.lower()
		if "fetch historical returns" in message_lower or "not enough overlapping return history" in message_lower:
			weights = [float(asset["weight"]) for asset in asset_entries]
			_, diversification_score = calculate_diversification(weights)
			heuristic = calculate_portfolio_score(
				diversification_score=diversification_score,
				expected_return_cagr=8.0,
				portfolio_risk_volatility=18.0,
			)
			return {
				"diversification_score": round(diversification_score, 2),
				"portfolio_score": float(heuristic["portfolio_score"]),
				"risk_level": str(heuristic["risk_level"]),
				"data_warnings": [
					message,
					"Used fallback assumptions (8% return, 18% volatility) due to missing market data.",
				],
			}
		raise HTTPException(status_code=400, detail=message) from exc
	except Exception as exc:
		raise HTTPException(
			status_code=502,
			detail=f"Failed to run rebalance simulation: {exc}",
		) from exc

	return {
		"diversification_score": float(result["diversification_score"]),
		"portfolio_score": float(result["portfolio_score"]),
		"risk_level": str(result["risk_level"]),
		"data_warnings": [],
	}


def _compute_portfolio_metrics(
	assets: List[dict[str, float | str]],
) -> tuple[float, float, list[str], dict[str, float], list[float]]:
	"""Compute expected annual return and annualized volatility from history."""
	series_list: list[pd.Series] = []
	weights: list[float] = []
	data_warnings: list[str] = []

	for idx, asset in enumerate(assets):
		ticker = str(asset["ticker"])
		weight = float(asset["weight"])
		try:
			returns_df = _fetch_returns_with_fallback(ticker)
		except ValueError as exc:
			data_warnings.append(f"Skipped ticker {ticker}: {exc}")
			continue
		if "daily_return" not in returns_df.columns:
			data_warnings.append(f"Skipped ticker {ticker}: missing daily_return series")
			continue

		series = returns_df[["date", "daily_return"]].copy()
		series["date"] = pd.to_datetime(series["date"])
		series = series.set_index("date")["daily_return"]
		series.name = f"asset_{idx}"

		series_list.append(series)
		weights.append(weight)

	if not series_list:
		raise ValueError("Unable to fetch valid return history for all requested tickers")

	if len(series_list) < 2:
		raise ValueError(
			"Need at least 2 assets with valid historical data to compute portfolio metrics"
		)

	returns_matrix = pd.concat(series_list, axis=1, join="inner").dropna()
	if returns_matrix.shape[0] < 2:
		raise ValueError("Not enough overlapping return history across assets")

	weights_array = np.array(weights, dtype=float)
	weights_array = weights_array / weights_array.sum()
	portfolio_daily_returns = returns_matrix.dot(weights_array)

	annual_expected_return = float(portfolio_daily_returns.mean() * 252.0)
	annual_volatility = float(portfolio_daily_returns.std(ddof=1) * sqrt(252.0))
	risk_metrics = calculate_portfolio_risk_metrics(
		historical_returns=returns_matrix,
		portfolio_weights=weights_array.tolist(),
	)

	if annual_volatility < 0:
		raise ValueError("Computed invalid portfolio volatility")

	return (
		annual_expected_return,
		annual_volatility,
		data_warnings,
		risk_metrics,
		portfolio_daily_returns.tolist(),
	)


def _build_asset_entries(assets: List[AssetInput]) -> list[dict[str, float | str]]:
	"""Convert quantity payload into normalized ticker/weight entries."""
	if not assets:
		raise ValueError("assets must not be empty")

	raw_quantities: list[float] = []
	raw_tickers: list[str] = []

	for asset in assets:
		ticker = asset.ticker.strip().upper()
		if not ticker:
			raise ValueError("asset ticker must be non-empty")
		quantity = float(asset.quantity)
		if quantity < 0:
			raise ValueError("asset quantity must be non-negative")

		raw_tickers.append(ticker)
		raw_quantities.append(quantity)

	normalized_tickers = _normalize_tickers_parallel(raw_tickers)
	aggregated_quantities: dict[str, float] = {}
	for ticker, quantity in zip(normalized_tickers, raw_quantities):
		aggregated_quantities[ticker] = aggregated_quantities.get(ticker, 0.0) + quantity

	tickers = list(aggregated_quantities.keys())
	raw_quantities = list(aggregated_quantities.values())

	if not raw_quantities or sum(raw_quantities) <= 0:
		raise ValueError("total portfolio quantity must be greater than 0")

	total = sum(raw_quantities)
	normalized_weights = [value / total for value in raw_quantities]

	return [
		{"ticker": ticker, "weight": weight}
		for ticker, weight in zip(tickers, normalized_weights)
	]


def _build_rebalance_asset_entries(
	assets: List[RebalanceAssetInput],
) -> list[dict[str, float | str]]:
	"""Convert rebalance payload into normalized ticker/weight entries."""
	if not assets:
		raise ValueError("assets must not be empty")

	raw_weights: list[float] = []
	raw_tickers: list[str] = []

	for asset in assets:
		ticker = asset.ticker.strip().upper()
		if not ticker:
			raise ValueError("asset ticker must be non-empty")

		weight = float(asset.weight)
		if weight < 0:
			raise ValueError("asset weights must be non-negative")

		raw_tickers.append(ticker)
		raw_weights.append(weight)

	normalized_tickers = _normalize_tickers_parallel(raw_tickers)
	aggregated_weights: dict[str, float] = {}
	for ticker, weight in zip(normalized_tickers, raw_weights):
		aggregated_weights[ticker] = aggregated_weights.get(ticker, 0.0) + weight

	tickers = list(aggregated_weights.keys())
	raw_weights = list(aggregated_weights.values())

	if not raw_weights or sum(raw_weights) <= 0:
		raise ValueError("total portfolio weight must be greater than 0")

	total = sum(raw_weights)
	normalized_weights = [value / total for value in raw_weights]

	return [
		{"ticker": ticker, "weight": weight}
		for ticker, weight in zip(tickers, normalized_weights)
	]


def _normalize_input_ticker(raw_ticker: str) -> str:
	"""Normalize ticker string with smart US/NSE/BSE fallback resolution."""
	clean = raw_ticker.strip().upper()
	if not clean:
		return clean
	return normalize_ticker(clean)


def _normalize_tickers_parallel(raw_tickers: List[str]) -> list[str]:
	"""Resolve ticker symbols concurrently to reduce normalization latency."""
	if not raw_tickers:
		return []

	with ThreadPoolExecutor(max_workers=10) as executor:
		return list(executor.map(_normalize_input_ticker, raw_tickers))


async def _build_asset_class_exposure(
	asset_entries: List[dict[str, float | str]],
) -> list[dict[str, float | str]]:
	"""Build simple asset-class exposure grouping for frontend charts."""
	groups: dict[str, float] = {}
	for entry in asset_entries:
		ticker = str(entry["ticker"])
		weight = float(entry["weight"])
		normalized = normalize_ticker(ticker)
		ticker_info_dict = await get_ticker_metadata(normalized)
		asset_class = await infer_asset_class(normalized, info=ticker_info_dict)
		groups[asset_class] = groups.get(asset_class, 0.0) + weight

	asset_class_map = {
		name: round(weight * 100.0, 2)
		for name, weight in sorted(groups.items())
	}

	# Ensure chart breakdown remains complete when classification misses part of
	# the portfolio (for example unresolved/unsupported instruments).
	total = sum(asset_class_map.values())
	remainder = round(100.0 - total, 2)
	if remainder > 0.5:
		asset_class_map["Other"] = remainder

	color_map = {
		"US Equities": "#3b82f6",
		"India Equities": "#10b981",
		"China Equities": "#f59e0b",
		"Japan Equities": "#ec4899",
		"Korea Equities": "#06b6d4",
		"HK Equities": "#f97316",
		"UK Equities": "#a78bfa",
		"European Equities": "#14b8a6",
		"Unknown": "#6b7280",
		"Other": "#8b5cf6",
	}
	return [
		{
			"name": name,
			"value": value,
			"color": color_map.get(name, "#8b5cf6"),
		}
		for name, value in sorted(asset_class_map.items())
	]


def _build_named_value_list(
	values: dict[str, float],
	use_percentage: bool,
) -> list[dict[str, float | str]]:
	"""Convert mapping payload to frontend-friendly array format."""
	color_palette = [
		"#3b82f6",
		"#10b981",
		"#f59e0b",
		"#ef4444",
		"#8b5cf6",
		"#06b6d4",
	]

	items: list[dict[str, float | str]] = []
	for idx, (name, value) in enumerate(sorted(values.items())):
		scaled = value * 100.0 if use_percentage else value
		items.append(
			{
				"name": name,
				"value": round(float(scaled), 2),
				"color": color_palette[idx % len(color_palette)],
			}
		)
	return items


def _normalize_simulation_rate(rate: float) -> float:
	"""Normalize rate input for simulation as decimal form.

	- If already decimal (0.085), keep as-is.
	- If percentage-like (8.5), convert to decimal (0.085).
	"""
	return rate / 100.0 if abs(rate) > 1.0 else rate


def _fetch_returns_with_fallback(ticker: str) -> pd.DataFrame:
	"""Fetch returns for ticker, trying raw symbol then NSE suffix fallback."""
	clean_ticker = ticker.strip().upper()
	if not clean_ticker:
		raise ValueError("ticker must be a non-empty string")

	candidates = [clean_ticker]
	if "." not in clean_ticker:
		candidates.append(f"{clean_ticker}.NS")

	last_error: Exception | None = None
	for candidate in candidates:
		try:
			return get_historical_returns(candidate)
		except Exception as exc:  # noqa: BLE001 - preserve source error for API context
			last_error = exc

	raise ValueError(
		f"Unable to fetch historical returns for ticker '{clean_ticker}'"
	) from last_error


async def _fetch_current_prices_for_tickers(
	tickers: List[str],
	data_warnings: list[str],
) -> dict[str, dict[str, float]]:
	"""Fetch current prices for tickers, keeping successful results only."""
	results: dict[str, dict[str, float]] = {}
	for ticker in tickers:
		try:
			price_df = await _fetch_current_price_with_fallback(ticker)
		except ValueError as exc:
			data_warnings.append(f"Skipped current price for {ticker}: {exc}")
			continue

		if price_df.empty or "current_price" not in price_df.columns:
			data_warnings.append(f"Skipped current price for {ticker}: missing current_price")
			continue

		results[ticker] = {"current_price": float(price_df["current_price"].iloc[-1])}

	return results


async def _fetch_current_price_with_fallback(ticker: str) -> pd.DataFrame:
	"""Fetch current price for ticker with Tier-2 AI resolver fallback."""
	clean_ticker = ticker.strip().upper()
	if not clean_ticker:
		raise ValueError("ticker must be a non-empty string")

	# Tier-1: try raw symbol then .NS suffix
	candidates = [clean_ticker]
	if "." not in clean_ticker:
		candidates.append(f"{clean_ticker}.NS")

	last_error: Exception | None = None
	for candidate in candidates:
		try:
			return get_current_price(candidate)
		except Exception as exc:
			last_error = exc

	# after the for loop over candidates
	logger.warning(
		"[main] All Tier-1 candidates failed for '%s', candidates tried: %s",
		clean_ticker,
		candidates,
	)
	# Tier-2: ask AI resolver for the correct normalized ticker
	logger.info("[main] Tier-1 price fetch failed for '%s', invoking Tier-2 AI resolver", clean_ticker)
	try:
		resolved = await ai_resolve_ticker(clean_ticker)
		logger.info("[main] Tier-2 raw result for '%s': %s", clean_ticker, resolved)
		if resolved and resolved.get("normalized_ticker"):
			t2 = resolved["normalized_ticker"]
			if t2 not in candidates:  # avoid retrying same symbols
				logger.info("[main] Tier-2 resolved '%s' -> '%s', retrying price fetch", clean_ticker, t2)
				return get_current_price(t2)
	except Exception as exc:
		last_error = exc

	raise ValueError(
		f"Unable to fetch current price for ticker '{clean_ticker}'"
	) from last_error

