"""AI-style narrative generator for portfolio analysis.

This module converts quantitative portfolio metrics into concise, human-readable
SWOT insights for long-term investors.
"""

from __future__ import annotations

from typing import Dict, Mapping


def generate_portfolio_swot(
	diversification_score: float,
	portfolio_score: float,
	risk_level: str,
	sector_exposure: Mapping[str, float] | None = None,
	simulation_results: Mapping[str, float] | None = None,
) -> Dict[str, str]:
	"""Generate a SWOT-style explanation for a portfolio.

	Args:
		diversification_score: Diversification score on a 0-100 scale.
		portfolio_score: Composite portfolio score on a 0-100 scale.
		risk_level: Risk category (low, moderate, high).
		sector_exposure: Optional sector-to-weight map.
		simulation_results: Optional simulation output map with median_value,
			best_case, and worst_case.

	Returns:
		Dictionary with keys:
		- strength
		- weakness
		- opportunity
		- threat
	"""
	diversification = _clamp(diversification_score, 0.0, 100.0)
	score = _clamp(portfolio_score, 0.0, 100.0)
	normalized_risk = _normalize_risk_level(risk_level)
	normalized_sector_exposure = _normalize_sector_exposure(sector_exposure)
	normalized_simulation = _normalize_simulation(simulation_results)
	concentration_warnings = _concentration_warnings(normalized_sector_exposure)

	return {
		"strength": _build_strength(
			diversification,
			score,
			normalized_risk,
			normalized_sector_exposure,
			normalized_simulation,
		),
		"weakness": _build_weakness(
			diversification,
			score,
			normalized_risk,
			concentration_warnings,
		),
		"opportunity": _build_opportunity(
			diversification,
			score,
			normalized_risk,
			concentration_warnings,
			normalized_simulation,
		),
		"threat": _build_threat(
			diversification,
			score,
			normalized_risk,
			concentration_warnings,
			normalized_simulation,
		),
	}


def _build_strength(
	diversification: float,
	score: float,
	risk_level: str,
	sector_exposure: Mapping[str, float],
	simulation: Mapping[str, float],
) -> str:
	messages = []

	if score >= 75 and diversification >= 70:
		messages.append(
			"Your portfolio shows strong structural quality, with healthy "
			"diversification and a high overall score. This combination supports "
			"disciplined long-term compounding."
		)
	elif score >= 60:
		messages.append(
			"The portfolio has a solid foundation and appears reasonably aligned "
			"for long-horizon investing, especially if contributions remain steady."
		)
	elif risk_level == "low":
		messages.append(
			"Risk exposure is currently restrained, which can help protect capital "
			"during uncertain market periods."
		)
	else:
		messages.append(
			"The portfolio maintains investable structure and can still benefit from "
			"consistent, long-term management."
		)

	if sector_exposure and not _concentration_warnings(sector_exposure):
		messages.append(
			"Sector exposure appears reasonably balanced, reducing dependence on a "
			"single market segment."
		)

	if simulation:
		median = simulation.get("median_value", 0.0)
		best = simulation.get("best_case", 0.0)
		if median > 0 and best / median >= 1.6:
			messages.append(
				"Scenario analysis indicates meaningful upside potential under "
				"favorable market conditions."
			)

	return " ".join(messages)


def _build_weakness(
	diversification: float,
	score: float,
	risk_level: str,
	concentration_warnings: list[str],
) -> str:
	messages = []

	if diversification < 50:
		messages.append(
			"Diversification is limited, suggesting concentration in a small number "
			"of assets or themes."
		)

	if score < 60:
		messages.append(
			"The current portfolio score indicates room to improve balance between "
			"return potential and risk control."
		)

	if risk_level == "high":
		messages.append(
			"Volatility exposure may be too aggressive for investors who prioritize "
			"stable long-term outcomes."
		)

	if concentration_warnings:
		messages.append(" ".join(concentration_warnings))

	if not messages:
		return (
			"No critical structural weakness stands out, though periodic rebalancing "
			"is still important to keep allocations on target."
		)

	return " ".join(messages)


def _build_opportunity(
	diversification: float,
	score: float,
	risk_level: str,
	concentration_warnings: list[str],
	simulation: Mapping[str, float],
) -> str:
	if concentration_warnings:
		return (
			"A targeted rebalance away from concentrated sectors can improve "
			"resilience while keeping long-term return objectives intact."
		)

	if simulation:
		median = simulation.get("median_value", 0.0)
		worst = simulation.get("worst_case", 0.0)
		if median > 0 and worst / median < 0.55:
			return (
				"Adding more defensive assets and setting rebalancing bands can "
				"improve downside resilience shown in stress scenarios."
			)

	if diversification < 65:
		return (
			"Expanding exposure across additional sectors, regions, and asset types "
			"could improve resilience and raise long-term risk-adjusted returns."
		)

	if score < 75:
		return (
			"A gradual optimization of allocation weights and periodic rebalancing "
			"can lift portfolio efficiency without requiring major strategy shifts."
		)

	if risk_level == "low":
		return (
			"With risk currently contained, there may be room to selectively add "
			"higher-quality growth exposure to strengthen long-term return potential."
		)

	return (
		"Continuing a rules-based contribution and rebalancing plan can further "
		"enhance compounding while keeping behavior disciplined through cycles."
	)


def _build_threat(
	diversification: float,
	score: float,
	risk_level: str,
	concentration_warnings: list[str],
	simulation: Mapping[str, float],
) -> str:
	if concentration_warnings:
		return (
			"Sector concentration above 40% can amplify drawdowns when that segment "
			"underperforms, increasing portfolio fragility in weak cycles."
		)

	if simulation:
		median = simulation.get("median_value", 0.0)
		worst = simulation.get("worst_case", 0.0)
		if median > 0 and worst / median < 0.50:
			return (
				"Simulation outcomes show meaningful downside tails, so adverse market "
				"regimes could materially delay long-term wealth goals."
			)

	if risk_level == "high" and diversification < 60:
		return (
			"A concentrated and high-volatility profile increases downside risk in "
			"prolonged market drawdowns and may pressure long-term decision-making."
		)

	if risk_level == "high":
		return (
			"Elevated volatility can trigger deeper interim losses, which may reduce "
			"the probability of meeting long-term goals if not actively managed."
		)

	if score < 55:
		return (
			"If current portfolio efficiency is not improved, inflation and uneven "
			"market cycles may erode real wealth accumulation over time."
		)

	return (
		"The main risk is strategic drift over time; without regular reviews, even "
		"a healthy portfolio can gradually lose its intended risk-return profile."
	)


def _normalize_risk_level(risk_level: str) -> str:
	value = risk_level.strip().lower()
	if value not in {"low", "moderate", "high"}:
		raise ValueError("risk_level must be one of: low, moderate, high")
	return value


def _normalize_sector_exposure(
	sector_exposure: Mapping[str, float] | None,
) -> dict[str, float]:
	if not sector_exposure:
		return {}

	normalized: dict[str, float] = {}
	for sector, weight in sector_exposure.items():
		if not isinstance(sector, str) or not sector.strip():
			continue
		try:
			normalized[sector.strip()] = float(weight)
		except (TypeError, ValueError):
			continue
	return normalized


def _normalize_simulation(
	simulation_results: Mapping[str, float] | None,
) -> dict[str, float]:
	if not simulation_results:
		return {}

	keys = ("median_value", "best_case", "worst_case")
	normalized: dict[str, float] = {}
	for key in keys:
		value = simulation_results.get(key)
		if value is None:
			continue
		try:
			normalized[key] = float(value)
		except (TypeError, ValueError):
			continue
	return normalized


def _concentration_warnings(sector_exposure: Mapping[str, float]) -> list[str]:
	warnings: list[str] = []
	for sector, weight in sorted(sector_exposure.items()):
		if weight > 0.40:
			warnings.append(
				f"Warning: {sector} exposure is {weight:.2f}, above the 0.40 concentration threshold."
			)
	return warnings


def _clamp(value: float, minimum: float, maximum: float) -> float:
	return max(minimum, min(value, maximum))


if __name__ == "__main__":
	# Example usage
	swot = generate_portfolio_swot(
		diversification_score=71.5,
		portfolio_score=62.36,
		risk_level="moderate",
		sector_exposure={"Technology": 0.70, "Semiconductors": 0.30},
		simulation_results={
			"median_value": 180000,
			"best_case": 320000,
			"worst_case": 70000,
		},
	)
	print(swot)

