"""Portfolio risk metrics module.

Computes key portfolio risk metrics from historical asset returns and
portfolio weights.
"""

from __future__ import annotations

from typing import Dict, Sequence

import numpy as np
import pandas as pd
import yfinance as yf


def calculate_portfolio_risk_metrics(
    historical_returns: pd.DataFrame,
    portfolio_weights: Sequence[float],
    risk_free_rate: float = 0.02,
    periods_per_year: int = 252,
) -> Dict[str, float]:
    """Calculate annualized volatility, Sharpe ratio, and maximum drawdown.

    Args:
        historical_returns: DataFrame of periodic returns with one column per
            asset and one row per time period.
        portfolio_weights: Portfolio weights aligned to DataFrame columns.
        risk_free_rate: Annual risk-free rate in decimal form (default 0.02).
        periods_per_year: Number of return periods in one year (default 252 for
            daily returns).

    Returns:
        Dictionary with keys:
        - annualized_volatility
        - sharpe_ratio
        - maximum_drawdown

    Raises:
        ValueError: If input data is invalid.
    """
    if not isinstance(historical_returns, pd.DataFrame) or historical_returns.empty:
        raise ValueError("historical_returns must be a non-empty pandas DataFrame")

    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be greater than 0")

    returns_df = historical_returns.apply(pd.to_numeric, errors="coerce").dropna()
    if returns_df.empty:
        raise ValueError("historical_returns has no usable numeric rows")

    weights = np.asarray(portfolio_weights, dtype=float)
    if weights.ndim != 1:
        raise ValueError("portfolio_weights must be a 1D sequence")
    if len(weights) != returns_df.shape[1]:
        raise ValueError(
            "portfolio_weights length must match number of return columns"
        )
    if np.any(weights < 0):
        raise ValueError("portfolio_weights must be non-negative")

    total_weight = float(weights.sum())
    if total_weight <= 0:
        raise ValueError("portfolio_weights must sum to a positive value")

    # Normalize weights defensively to avoid user-input drift.
    normalized_weights = weights / total_weight

    portfolio_returns = returns_df.to_numpy().dot(normalized_weights)

    volatility_periodic = float(np.std(portfolio_returns, ddof=1))
    annualized_volatility = float(volatility_periodic * np.sqrt(periods_per_year))

    mean_return_periodic = float(np.mean(portfolio_returns))
    annualized_return = mean_return_periodic * periods_per_year
    excess_return = annualized_return - risk_free_rate
    sharpe_ratio = float(
        excess_return / annualized_volatility if annualized_volatility > 0 else 0.0
    )

    cumulative = np.cumprod(1.0 + portfolio_returns)
    running_peak = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative / running_peak) - 1.0
    maximum_drawdown = float(abs(np.min(drawdowns)))

    return {
        "annualized_volatility": float(annualized_volatility),
        "sharpe_ratio": sharpe_ratio,
        "maximum_drawdown": maximum_drawdown,
    }


def select_benchmark(tickers: list[str]) -> str:
    """Select benchmark by portfolio geography mix."""
    if not tickers:
        return "^GSPC"
    indian = sum(1 for ticker in tickers if ticker.upper().endswith(".NS"))
    return "^NSEI" if indian > (len(tickers) / 2.0) else "^GSPC"


def compute_beta(
    portfolio_returns: list[float],
    benchmark_ticker: str = "^GSPC",
) -> float:
    """Compute portfolio beta versus benchmark from daily return covariance."""
    try:
        benchmark = yf.Ticker(benchmark_ticker)
        hist = benchmark.history(period="1y")
        if hist.empty or "Close" not in hist.columns:
            return 1.0

        benchmark_returns = hist["Close"].pct_change().dropna().values
        if len(portfolio_returns) < 2 or len(benchmark_returns) < 2:
            return 1.0

        min_len = min(len(portfolio_returns), len(benchmark_returns))
        if min_len < 2:
            return 1.0

        p = np.array(portfolio_returns[-min_len:], dtype=float)
        b = np.array(benchmark_returns[-min_len:], dtype=float)

        covariance = float(np.cov(p, b)[0][1])
        variance = float(np.var(b))
        if variance == 0.0:
            return 1.0

        return round(covariance / variance, 2)
    except Exception:
        return 1.0


def compute_alpha(
    portfolio_annual_return: float,
    beta: float,
    benchmark_ticker: str = "^GSPC",
    risk_free_rate: float = 0.065,
) -> float:
    """Compute Jensen's alpha in percentage points."""
    try:
        benchmark = yf.Ticker(benchmark_ticker)
        hist = benchmark.history(period="1y")
        if hist.empty or "Close" not in hist.columns:
            return 0.0

        prices = hist["Close"].dropna()
        if len(prices) < 2 or prices.iloc[0] == 0:
            return 0.0

        benchmark_annual_return = float((prices.iloc[-1] - prices.iloc[0]) / prices.iloc[0])
        alpha = portfolio_annual_return - (
            risk_free_rate + beta * (benchmark_annual_return - risk_free_rate)
        )
        return round(alpha * 100.0, 2)
    except Exception:
        return 0.0


def compute_daily_change(
    weights: dict[str, float],
    total_value: float,
    fetched_data: dict[str, dict[str, float]],
) -> dict[str, float]:
    """Compute one-day portfolio change as both percent and dollar amount."""
    try:
        if total_value <= 0:
            return {"dailyChangePct": 0.0, "dailyChangeDollar": 0.0}

        daily_pct = 0.0
        for ticker, weight in weights.items():
            if ticker not in fetched_data:
                continue
            hist = yf.Ticker(ticker).history(period="2d")
            if hist.empty or "Close" not in hist.columns:
                continue

            closes = hist["Close"].dropna()
            if len(closes) < 2 or closes.iloc[-2] == 0:
                continue

            pct = float((closes.iloc[-1] - closes.iloc[-2]) / closes.iloc[-2])
            daily_pct += float(weight) * pct

        return {
            "dailyChangePct": round(daily_pct * 100.0, 2),
            "dailyChangeDollar": round(float(total_value) * daily_pct, 2),
        }
    except Exception:
        return {"dailyChangePct": 0.0, "dailyChangeDollar": 0.0}


def compute_portfolio_annual_return(
    weights: dict[str, float],
    fetched_data: dict[str, dict[str, float]],
) -> float:
    """Compute weighted 1Y portfolio return from constituent ticker prices."""
    try:
        total_return = 0.0
        for ticker, weight in weights.items():
            if ticker not in fetched_data:
                continue

            hist = yf.Ticker(ticker).history(period="1y")
            if hist.empty or "Close" not in hist.columns:
                continue

            closes = hist["Close"].dropna()
            if len(closes) < 2 or closes.iloc[0] == 0:
                continue

            ticker_return = float((closes.iloc[-1] - closes.iloc[0]) / closes.iloc[0])
            total_return += float(weight) * ticker_return

        return float(total_return) if total_return != 0.0 else 0.08
    except Exception:
        return 0.08


if __name__ == "__main__":
    # Example usage
    np.random.seed(42)
    sample_returns = pd.DataFrame(
        {
            "Asset_A": np.random.normal(0.0005, 0.012, 252),
            "Asset_B": np.random.normal(0.0004, 0.010, 252),
            "Asset_C": np.random.normal(0.0006, 0.015, 252),
        }
    )
    sample_weights = [0.4, 0.35, 0.25]

    print(calculate_portfolio_risk_metrics(sample_returns, sample_weights))
