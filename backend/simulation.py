"""Monte Carlo simulation utilities for portfolio growth."""

from __future__ import annotations

from typing import Dict, List

import numpy as np


def simulate_portfolio_monte_carlo(
    initial_investment: float,
    expected_annual_return: float,
    annual_volatility: float,
    years: int,
    num_simulations: int = 10_000,
) -> Dict[str, float]:
    """Legacy single-endpoint result (kept for backward compat)."""
    mu = _as_decimal_rate(expected_annual_return)
    sigma = _as_decimal_rate(annual_volatility)
    monthly_mu = mu / 12
    monthly_sigma = sigma / (12 ** 0.5)
    months = years * 12

    sampled = np.random.normal(loc=monthly_mu, scale=monthly_sigma, size=(num_simulations, months))
    growth = np.prod(1.0 + sampled, axis=1)
    final_values = np.maximum(initial_investment * growth, 0.0)

    return {
        "median_value": float(np.median(final_values)),
        "best_case": float(np.percentile(final_values, 90)),
        "worst_case": float(np.percentile(final_values, 10)),
    }


def simulate_portfolio_growth_intervals(
    initial_investment: float,
    expected_annual_return: float,
    annual_volatility: float,
    years: int = 2,
    num_simulations: int = 10_000,
    interval_months: int = 2,
) -> List[Dict]:
    """
    Returns P10/P50/P90 at every `interval_months` checkpoint.
    Default: M0, M2, M4, ..., M24.
    """
    mu = _as_decimal_rate(expected_annual_return)
    sigma = _as_decimal_rate(annual_volatility)
    monthly_mu = mu / 12
    monthly_sigma = sigma / (12 ** 0.5)
    total_months = years * 12

    # Shape: (num_simulations, total_months)
    monthly_returns = np.random.normal(
        loc=monthly_mu,
        scale=monthly_sigma,
        size=(num_simulations, total_months),
    )

    # Cumulative product along months -> portfolio value at each month
    # Shape: (num_simulations, total_months)
    cumulative_growth = np.cumprod(1.0 + monthly_returns, axis=1)
    portfolio_paths = np.maximum(initial_investment * cumulative_growth, 0.0)

    results = [
        {
            "label": "M0",
            "p10": round(initial_investment, 2),
            "p50": round(initial_investment, 2),
            "p90": round(initial_investment, 2),
        }
    ]

    for month in range(interval_months, total_months + 1, interval_months):
        values_at_month = portfolio_paths[:, month - 1]
        results.append(
            {
                "label": f"M{month}",
                "p10": round(float(np.percentile(values_at_month, 10)), 2),
                "p50": round(float(np.percentile(values_at_month, 50)), 2),
                "p90": round(float(np.percentile(values_at_month, 90)), 2),
            }
        )

    return results


def monte_carlo_portfolio_growth(
    initial_investment: float,
    expected_annual_return: float,
    volatility: float,
    years: int,
    num_simulations: int = 10_000,
) -> Dict[str, float]:
    """Backward-compatible wrapper."""
    return simulate_portfolio_monte_carlo(
        initial_investment=initial_investment,
        expected_annual_return=expected_annual_return,
        annual_volatility=volatility,
        years=years,
        num_simulations=num_simulations,
    )


def _as_decimal_rate(value: float) -> float:
    if abs(value) > 1.0:
        return value / 100.0
    return value
