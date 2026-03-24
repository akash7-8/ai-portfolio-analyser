"""Portfolio scoring engine.

This module combines diversification, expected return, and risk metrics into a
single portfolio score on a 0-100 scale.
"""

from __future__ import annotations

from typing import Dict


def calculate_portfolio_score(
	diversification_score: float,
	expected_return_cagr: float,
	portfolio_risk_volatility: float,
) -> Dict[str, float | str]:
	"""Calculate a final portfolio score and risk level.

	Formula:
	Portfolio Score =
	0.35 * diversification
	+ 0.25 * return_score
	+ 0.20 * risk_score
	+ 0.20 * stability_score

	Notes on component scores:
	- diversification: Expected to already be in 0-100.
	- return_score: Normalized from CAGR, where higher is better.
	- risk_score: Normalized from volatility, where lower is better.
	- stability_score: Also based on volatility, on a wider risk range to
	  reflect overall stability under market movement.

	Args:
		diversification_score: Diversification score in the range 0-100.
		expected_return_cagr: CAGR as decimal (0.12) or percent (12).
		portfolio_risk_volatility: Volatility as decimal (0.18) or percent (18).

	Returns:
		A dictionary with:
		- portfolio_score: Final score normalized to 0-100.
		- risk_level: One of low, moderate, high.
	"""
	diversification = _clamp(diversification_score, 0.0, 100.0)
	cagr = _as_decimal_rate(expected_return_cagr)
	volatility = _as_decimal_rate(portfolio_risk_volatility)

	# Typical CAGR range for score normalization: 0% to 20%.
	return_score = _normalize(cagr, min_value=0.0, max_value=0.20, higher_is_better=True)

	# Typical volatility range for risk normalization: 5% to 35%.
	risk_score = _normalize(
		volatility, min_value=0.05, max_value=0.35, higher_is_better=False
	)

	# Wider range for stability sensitivity: 0% to 40% (lower is better).
	stability_score = _normalize(
		volatility, min_value=0.0, max_value=0.40, higher_is_better=False
	)

	raw_score = (
		0.35 * diversification
		+ 0.25 * return_score
		+ 0.20 * risk_score
		+ 0.20 * stability_score
	)
	portfolio_score = round(_clamp(raw_score, 0.0, 100.0), 2)

	return {
		"portfolio_score": portfolio_score,
		"risk_level": _risk_level(volatility),
	}


def _normalize(
	value: float, min_value: float, max_value: float, higher_is_better: bool
) -> float:
	"""Normalize a numeric value to a 0-100 score."""
	if max_value <= min_value:
		raise ValueError("max_value must be greater than min_value")

	bounded = _clamp(value, min_value, max_value)
	ratio = (bounded - min_value) / (max_value - min_value)

	if higher_is_better:
		score = ratio * 100.0
	else:
		score = (1.0 - ratio) * 100.0

	return _clamp(score, 0.0, 100.0)


def _as_decimal_rate(value: float) -> float:
	"""Convert a rate to decimal form.

	Accepts values as either decimal (0.12) or percent (12). For values above
	1 and up to 100 in absolute magnitude, the function treats them as
	percentage points.
	"""
	if 1.0 < abs(value) <= 100.0:
		return value / 100.0
	return value


def _risk_level(volatility_decimal: float) -> str:
	"""Classify risk level using volatility (decimal form)."""
	if volatility_decimal <= 0.10:
		return "low"
	if volatility_decimal <= 0.20:
		return "moderate"
	return "high"


def _clamp(value: float, minimum: float, maximum: float) -> float:
	"""Clamp a numeric value between minimum and maximum."""
	return max(minimum, min(value, maximum))


if __name__ == "__main__":
	# Example usage
	result = calculate_portfolio_score(
		diversification_score=71.5,
		expected_return_cagr=12,
		portfolio_risk_volatility=18,
	)
	print(result)

