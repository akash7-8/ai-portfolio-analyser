"""Utilities to fetch stock prices and historical returns using yfinance."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache

import pandas as pd
import yfinance as yf


TICKER_ALIASES = {
	"HUL": "HINDUNILVR",
	"HDFC": "HDFCBANK",
	"ICICBANK": "ICICIBANK",
	"INFOSYS": "INFY",
	"KOTAK": "KOTAKBANK",
	"RELIANCEIND": "RELIANCE",
	"MARICOIND": "MARICO",
}


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


@lru_cache(maxsize=2048)
def normalize_ticker(ticker: str) -> str:
	"""Resolve a user-provided ticker to the most likely exchange symbol.

	Resolution order:
	1. Return as-is when ticker already has an exchange suffix.
	2. Check configured aliases.
	3. Validate base ticker as-is (commonly US symbols).
	4. Fallback to NSE (.NS), then BSE (.BO).
	"""
	clean = _validate_ticker(ticker)
	if "." in clean:
		return clean

	mapped = TICKER_ALIASES.get(clean, clean)
	prefer_nse = mapped in TICKER_ALIASES.values() or clean in TICKER_ALIASES
	as_is_price = _ticker_has_price(mapped)

	ns_ticker = f"{mapped}.NS"
	ns_price = _ticker_has_price(ns_ticker)
	if ns_price and (prefer_nse or not as_is_price):
		return ns_ticker

	if as_is_price:
		return mapped

	bo_ticker = f"{mapped}.BO"
	if _ticker_has_price(bo_ticker):
		return bo_ticker

	return mapped


def _ticker_has_price(ticker: str) -> bool:
	"""Return True when yfinance metadata includes a usable market price."""
	try:
		info = yf.Ticker(ticker).info
	except Exception:  # noqa: BLE001 - network/metadata access is best effort
		return False

	if not isinstance(info, dict):
		return False

	price = info.get("regularMarketPrice") or info.get("currentPrice")
	return price is not None


def _validate_ticker(ticker: str) -> str:
	"""Validate and normalize ticker input."""
	if not isinstance(ticker, str) or not ticker.strip():
		raise ValueError("ticker must be a non-empty string")
	return ticker.strip().upper()


def get_ticker_metadata(ticker: str) -> dict:
	"""Return yfinance .info dict for the normalized ticker symbol.

	Always normalizes the ticker first so callers receive metadata
	for the correct exchange (NSE/BSE) rather than a bare symbol.
	"""
	normalized = normalize_ticker(ticker)
	try:
		info = yf.Ticker(normalized).info
	except Exception:
		return {}
	if not isinstance(info, dict):
		return {}
	info["_normalized_ticker"] = normalized
	return info


if __name__ == "__main__":
	# Example usage
	print(get_current_price("AAPL").head())
	print(get_historical_returns("AAPL").head())

