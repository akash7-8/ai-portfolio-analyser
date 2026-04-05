"""Utilities to fetch stock prices and historical returns using yfinance."""

from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
import logging

import pandas as pd
import yfinance as yf
from backend.ai_resolver import ai_resolve_ticker


logger = logging.getLogger(__name__)


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
	as_is_price = _ticker_has_price_direct(mapped)

	ns_ticker = f"{mapped}.NS"
	ns_price = _ticker_has_price_direct(ns_ticker)
	if ns_price and (prefer_nse or not as_is_price):
		return ns_ticker

	if as_is_price:
		return mapped

	bo_ticker = f"{mapped}.BO"
	if _ticker_has_price_direct(bo_ticker):
		return bo_ticker

	return mapped


def _ticker_has_price_direct(ticker: str) -> bool:
	"""Return True when yfinance metadata includes a usable market price."""
	try:
		info = yf.Ticker(ticker).info
	except Exception:  # noqa: BLE001 - network/metadata access is best effort
		return False

	if not isinstance(info, dict):
		return False

	price = info.get("regularMarketPrice") or info.get("currentPrice")
	return price is not None


async def _ticker_has_price(ticker: str) -> bool:
	"""Return True when metadata contains any usable market/nav price."""
	try:
		info = await get_ticker_metadata(ticker)
	except Exception:
		return False

	if not isinstance(info, dict):
		return False

	price = (
		info.get("regularMarketPrice")
		or info.get("currentPrice")
		or info.get("navPrice")
	)
	return price is not None


def _validate_ticker(ticker: str) -> str:
	"""Validate and normalize ticker input."""
	if not isinstance(ticker, str) or not ticker.strip():
		raise ValueError("ticker must be a non-empty string")
	return ticker.strip().upper()


async def get_ticker_metadata(ticker: str) -> dict:
	"""
	Fetches yfinance .info dict for a ticker.
	Uses Tier-1 normalization with Tier-2 AI fallback.
	Injects resolution metadata into the returned dict.
	"""
	import yfinance as yf

	# Tier-1: rule-based normalization
	t1 = normalize_ticker(ticker)

	# Attempt yfinance full info fetch with Tier-1 normalized ticker
	try:
		info = yf.Ticker(t1).info or {}
	except Exception:
		info = {}

	if not isinstance(info, dict):
		info = {}

	logger.info(
		"[data_fetcher] Tier-1 info keys for '%s': regularMarketPrice=%s currentPrice=%s navPrice=%s info_len=%d",
		t1,
		info.get("regularMarketPrice"),
		info.get("currentPrice"),
		info.get("navPrice"),
		len(info),
	)

	# Determine if Tier-1 result is actually usable
	# A valid yfinance response always has at least "regularMarketPrice" or "currentPrice"
	price_present = (
		info.get("regularMarketPrice")
		or info.get("currentPrice")
		or info.get("navPrice")
	)

	if price_present:
		# Tier-1 success
		info["_normalized_ticker"] = t1
		info["_resolution_source"] = "tier1"
		return info

	# Tier-1 info fetch failed or returned empty — invoke Tier-2
	logger.info("[data_fetcher] Tier-1 info empty for '%s', invoking Tier-2 AI resolver", t1)
	resolved = await ai_resolve_ticker(ticker)

	if resolved and resolved.get("normalized_ticker"):
		t2 = resolved["normalized_ticker"]
		try:
			info2 = yf.Ticker(t2).info or {}
		except Exception:
			info2 = {}

		if not isinstance(info2, dict):
			info2 = {}

		info2["_normalized_ticker"] = t2
		info2["_resolution_source"] = "tier2"

		if not info2.get("sector") and resolved.get("sector"):
			info2["sector"] = resolved["sector"]
		if not info2.get("country") and resolved.get("country"):
			info2["country"] = resolved["country"]
		if resolved.get("asset_class"):
			info2["_ai_asset_class"] = resolved["asset_class"]

		return info2

	# Fallback: return whatever Tier-1 gave us even if empty
	logger.warning("[data_fetcher] Tier-2 failed for '%s', using Tier-1 result as fallback", ticker)
	info["_normalized_ticker"] = t1
	info["_resolution_source"] = "fallback"
	return info


if __name__ == "__main__":
	# Example usage
	print(get_current_price("AAPL").head())
	print(get_historical_returns("AAPL").head())

