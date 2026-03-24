"""Monte Carlo simulation utilities for portfolio growth."""

from __future__ import annotations

from typing import Dict

import numpy as np


def simulate_portfolio_monte_carlo(
	initial_investment: float,
	expected_annual_return: float,
	annual_volatility: float,
	years: int,
	num_simulations: int = 10_000,
) -> Dict[str, float]:
	"""Run a Monte Carlo simulation for final portfolio values.

	The simulation samples annual returns from a normal distribution and applies
	compounding to estimate the portfolio value at the end of the horizon.

	Args:
		initial_investment: Starting portfolio amount.
		expected_annual_return: Expected annual return as decimal (0.10) or
			percent (10).
		annual_volatility: Annual volatility as decimal (0.15) or percent (15).
		years: Number of years to simulate.
		num_simulations: Number of simulation paths (default 10,000).

	Returns:
		A dictionary with:
		- median_value
		- best_case
		- worst_case

	Raises:
		ValueError: If inputs are invalid.
	"""
	if initial_investment <= 0:
		raise ValueError("initial_investment must be greater than 0")
	if years <= 0:
		raise ValueError("years must be greater than 0")
	if num_simulations <= 0:
		raise ValueError("num_simulations must be greater than 0")

	mu = _as_decimal_rate(expected_annual_return)
	sigma = _as_decimal_rate(annual_volatility)
	if sigma < 0:
		raise ValueError("annual_volatility must be non-negative")

	# Random annual returns matrix: shape (num_simulations, years)
	sampled_returns = np.random.normal(loc=mu, scale=sigma, size=(num_simulations, years))

	# Convert returns to growth factors and compound along each simulation path.
	growth_factors = 1.0 + sampled_returns
	final_values = initial_investment * np.prod(growth_factors, axis=1)

	# Keep values non-negative in edge cases with extreme negative returns.
	final_values = np.maximum(final_values, 0.0)

	return {
		"median_value": float(np.median(final_values)),
		"best_case": float(np.max(final_values)),
		"worst_case": float(np.min(final_values)),
	}


def monte_carlo_portfolio_growth(
	initial_investment: float,
	expected_annual_return: float,
	volatility: float,
	years: int,
	num_simulations: int = 10_000,
) -> Dict[str, float]:
	"""Backward-compatible wrapper for existing callers."""
	return simulate_portfolio_monte_carlo(
		initial_investment=initial_investment,
		expected_annual_return=expected_annual_return,
		annual_volatility=volatility,
		years=years,
		num_simulations=num_simulations,
	)


def _as_decimal_rate(value: float) -> float:
	"""Convert rate inputs to decimal format.

	Values with absolute magnitude above 1 are interpreted as percentages.
	"""
	if abs(value) > 1.0:
		return value / 100.0
	return value


if __name__ == "__main__":
	# Example usage
	result = monte_carlo_portfolio_growth(
		initial_investment=10_000,
		expected_annual_return=10,
		volatility=15,
		years=10,
		num_simulations=10_000,
	)
	print(result)

