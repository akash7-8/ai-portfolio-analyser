"""Portfolio rebalancing simulation module.

This module simulates a post-rebalance portfolio by normalizing proposed
allocation weights, recomputing diversification, and estimating portfolio
quality metrics.
"""

from __future__ import annotations

from math import sqrt
from typing import Dict, Iterable, Mapping

import numpy as np
import pandas as pd

from backend.data_fetcher import get_historical_returns
from backend.diversification import calculate_diversification
from backend.portfolio_engine import calculate_portfolio_score


def simulate_rebalance(assets: Iterable[Mapping[str, object]]) -> Dict[str, float | str]:
    """Simulate portfolio metrics after rebalancing.

    Input assets are expected to contain ticker and new allocation weight.
    Accepted weight keys are ``new_weight`` and ``weight``.

    Steps:
    1. Normalize weights so they sum to 1.
    2. Calculate diversification score.
    3. Calculate portfolio score.
    4. Determine risk level.

    Args:
        assets: Iterable of dictionaries with ticker and new weight allocation.

    Returns:
        Dictionary with keys:
        - diversification_score
        - portfolio_score
        - risk_level

    Raises:
        ValueError: If input assets are invalid or market data cannot be used.
    """
    normalized_assets = _normalize_assets(assets)
    weights = [asset["weight"] for asset in normalized_assets]

    _, diversification_score = calculate_diversification(weights)
    expected_return, portfolio_volatility = _compute_portfolio_metrics(normalized_assets)

    scoring = calculate_portfolio_score(
        diversification_score=diversification_score,
        expected_return_cagr=expected_return,
        portfolio_risk_volatility=portfolio_volatility,
    )

    return {
        "diversification_score": round(diversification_score, 2),
        "portfolio_score": float(scoring["portfolio_score"]),
        "risk_level": str(scoring["risk_level"]),
    }


def _normalize_assets(assets: Iterable[Mapping[str, object]]) -> list[dict[str, float | str]]:
    """Validate asset entries and normalize weights to sum exactly to 1."""
    parsed: list[dict[str, float | str]] = []

    for asset in assets:
        ticker_value = asset.get("ticker")
        weight_value = asset.get("new_weight", asset.get("weight"))

        if not isinstance(ticker_value, str) or not ticker_value.strip():
            raise ValueError("each asset must include a non-empty ticker")

        try:
            weight = float(weight_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("each asset must include numeric new_weight or weight") from exc

        if weight < 0:
            raise ValueError("asset weights must be non-negative")

        parsed.append({"ticker": ticker_value.strip().upper(), "weight": weight})

    if not parsed:
        raise ValueError("assets must not be empty")

    total_weight = sum(float(item["weight"]) for item in parsed)
    if total_weight <= 0:
        raise ValueError("total portfolio weight must be greater than 0")

    for item in parsed:
        item["weight"] = float(item["weight"]) / total_weight

    return parsed


def _compute_portfolio_metrics(assets: list[dict[str, float | str]]) -> tuple[float, float]:
    """Compute annual expected return and annualized volatility from daily returns."""
    series_list: list[pd.Series] = []
    weights: list[float] = []

    for idx, asset in enumerate(assets):
        ticker = str(asset["ticker"])
        returns_df = _fetch_returns_with_fallback(ticker)

        if "daily_return" not in returns_df.columns:
            raise ValueError(f"missing daily_return series for ticker {ticker}")

        series = returns_df[["date", "daily_return"]].copy()
        series["date"] = pd.to_datetime(series["date"])
        series = series.set_index("date")["daily_return"]
        series.name = f"asset_{idx}"

        series_list.append(series)
        weights.append(float(asset["weight"]))

    returns_matrix = pd.concat(series_list, axis=1, join="inner").dropna()
    if returns_matrix.shape[0] < 2:
        raise ValueError("not enough overlapping return history across assets")

    weights_array = np.array(weights, dtype=float)
    portfolio_daily_returns = returns_matrix.dot(weights_array)

    annual_expected_return = float(portfolio_daily_returns.mean() * 252.0)
    annual_volatility = float(portfolio_daily_returns.std(ddof=1) * sqrt(252.0))

    return annual_expected_return, annual_volatility


def _fetch_returns_with_fallback(ticker: str) -> pd.DataFrame:
    """Fetch returns with fallback from plain ticker to NSE suffix."""
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
        except Exception as exc:  # noqa: BLE001
            last_error = exc

    raise ValueError(f"unable to fetch historical returns for ticker '{clean_ticker}'") from last_error


if __name__ == "__main__":
    sample_assets = [
        {"ticker": "TCS", "new_weight": 0.4},
        {"ticker": "HDFCBANK", "new_weight": 0.3},
        {"ticker": "RELIANCE", "new_weight": 0.3},
    ]
    print(simulate_rebalance(sample_assets))
