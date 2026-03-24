"""Utilities to fetch stock prices and historical returns using yfinance."""

from __future__ import annotations

from datetime import datetime, timezone

import pandas as pd
import yfinance as yf


def get_current_price(ticker: str) -> pd.DataFrame:
	"""Fetch the latest market price for a ticker.

	Args:
		ticker: Stock ticker symbol (for example, ``AAPL``).

	Returns:
		A pandas DataFrame with one row and columns:
		- ticker
		- current_price
		- fetched_at_utc

	Raises:
		ValueError: If ticker is empty or no price is available.
	"""
	symbol = _validate_ticker(ticker)
	history = yf.Ticker(symbol).history(period="1d", interval="1m")

	if history.empty:
		raise ValueError(f"No recent pricing data found for ticker '{symbol}'")

	latest_price = float(history["Close"].dropna().iloc[-1])
	fetched_at = datetime.now(timezone.utc)

	return pd.DataFrame(
		[
			{
				"ticker": symbol,
				"current_price": latest_price,
				"fetched_at_utc": fetched_at,
			}
		]
	)


def get_historical_returns(ticker: str) -> pd.DataFrame:
	"""Fetch historical daily returns for a ticker.

	The function downloads 1 year of daily closes and computes percentage
	returns using ``pct_change()``.

	Args:
		ticker: Stock ticker symbol (for example, ``MSFT``).

	Returns:
		A pandas DataFrame with columns:
		- date
		- ticker
		- close
		- daily_return

	Raises:
		ValueError: If ticker is empty or historical data is unavailable.
	"""
	symbol = _validate_ticker(ticker)
	history = yf.download(
		tickers=symbol,
		period="1y",
		interval="1d",
		auto_adjust=True,
		progress=False,
	)

	if history.empty:
		raise ValueError(f"No historical data found for ticker '{symbol}'")

	if isinstance(history.columns, pd.MultiIndex):
		close_data = history["Close"]
		if isinstance(close_data, pd.DataFrame):
			close_series = close_data.iloc[:, 0]
		else:
			close_series = close_data
	else:
		close_series = history["Close"]

	df = close_series.to_frame(name="close")
	df["daily_return"] = df["close"].pct_change()
	df = df.dropna(subset=["daily_return"]).reset_index()
	df = df.rename(columns={df.columns[0]: "date"})
	df.insert(1, "ticker", symbol)
	return df[["date", "ticker", "close", "daily_return"]]


def _validate_ticker(ticker: str) -> str:
	"""Validate and normalize ticker input."""
	if not isinstance(ticker, str) or not ticker.strip():
		raise ValueError("ticker must be a non-empty string")
	return ticker.strip().upper()


if __name__ == "__main__":
	# Example usage
	print(get_current_price("AAPL").head())
	print(get_historical_returns("AAPL").head())

