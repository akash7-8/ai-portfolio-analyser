"""Sector exposure utilities for portfolio analysis.

This module reads a ticker-to-sector map from data/sector_map.json and
aggregates portfolio weights by sector.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, Mapping

import yfinance as yf


DEFAULT_MAP_PATH = Path(__file__).resolve().parent.parent / "data" / "sector_map.json"


def load_sector_map(file_path: str | None = None) -> Dict[str, str]:
    """Load ticker-to-sector mapping from JSON.

    Args:
        file_path: Optional custom path to sector map JSON.
            If not provided, uses data/sector_map.json in project root.

    Returns:
        Dictionary mapping uppercase ticker symbols to sector names.

    Raises:
        FileNotFoundError: If the JSON file is missing.
        ValueError: If the JSON content is not a valid object map.
    """
    map_path = Path(file_path) if file_path else DEFAULT_MAP_PATH

    if not map_path.exists():
        raise FileNotFoundError(f"sector map file not found: {map_path}")

    with map_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if not isinstance(payload, dict):
        raise ValueError("sector map JSON must be an object of ticker to sector")

    normalized_map: Dict[str, str] = {}
    for ticker, sector in payload.items():
        if not isinstance(ticker, str) or not ticker.strip():
            raise ValueError("sector map contains an invalid ticker key")
        if not isinstance(sector, str) or not sector.strip():
            raise ValueError("sector map contains an invalid sector value")
        normalized_map[ticker.strip().upper()] = sector.strip()

    return normalized_map


def calculate_sector_exposure(
    assets: Iterable[Mapping[str, object]],
    sector_map: Mapping[str, str] | None = None,
    auto_update_map: bool = False,
    map_file_path: str | None = None,
) -> Dict[str, float]:
    """Calculate aggregated portfolio weight per sector.

    Args:
        assets: Iterable of asset entries, each with keys:
            - ticker: str
            - weight: float
        sector_map: Optional preloaded ticker-to-sector map.
            If omitted, load_sector_map() is used.
        auto_update_map: When True, newly discovered sectors from yfinance are
            persisted to the JSON map file.
        map_file_path: Optional custom map path for loading/saving.

    Returns:
        Dictionary where keys are sector names and values are total weights.

    Raises:
        ValueError: If asset entries are malformed.
    """
    mapping = dict(sector_map) if sector_map is not None else load_sector_map(map_file_path)
    discovered_mappings: dict[str, str] = {}
    exposure: Dict[str, float] = {}

    for asset in assets:
        ticker_value = asset.get("ticker")
        weight_value = asset.get("weight")

        if not isinstance(ticker_value, str) or not ticker_value.strip():
            raise ValueError("each asset must contain a non-empty 'ticker'")

        try:
            weight = float(weight_value)
        except (TypeError, ValueError) as exc:
            raise ValueError("each asset must contain a numeric 'weight'") from exc

        if weight < 0:
            raise ValueError("asset weights must be non-negative")

        ticker = ticker_value.strip().upper()
        sector = _resolve_sector(ticker, mapping)

        if sector == "Unknown":
            resolved_sector = get_sector_from_yfinance_metadata(ticker)
            if resolved_sector:
                sector = resolved_sector
                # Cache in-memory so subsequent lookups in the same run are fast.
                mapping[ticker] = sector
                if "." in ticker:
                    mapping[ticker.split(".", 1)[0]] = sector
                discovered_mappings[ticker] = sector

        exposure[sector] = exposure.get(sector, 0.0) + weight

    if auto_update_map and discovered_mappings and sector_map is None:
        _merge_and_save_sector_map(discovered_mappings, file_path=map_file_path)

    # Keep output clean and deterministic.
    return {sector: round(weight, 6) for sector, weight in sorted(exposure.items())}


def _resolve_sector(ticker: str, mapping: Mapping[str, str]) -> str:
    """Resolve sector for ticker with support for exchange-suffixed symbols."""
    candidates = _ticker_candidates(ticker)

    for candidate in candidates:
        sector = mapping.get(candidate)
        if sector:
            return sector

    return "Unknown"


@lru_cache(maxsize=512)
def get_sector_from_yfinance_metadata(ticker: str) -> str | None:
    """Fetch sector using yfinance metadata with safe fallbacks.

    The function never raises for network/metadata errors; it returns None when
    no reliable sector label is available.
    """
    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        return None

    candidates = _ticker_candidates(clean_ticker)

    for candidate in candidates:
        metadata = _get_ticker_metadata(candidate)
        sector = _extract_sector_label(candidate, metadata)
        if sector:
            return sector

    return None


def _get_ticker_metadata(ticker: str) -> dict:
    """Safely read yfinance info payload for a ticker."""
    try:
        info = yf.Ticker(ticker).info
    except Exception:  # noqa: BLE001 - avoid failing sector exposure on network calls
        return {}

    if not isinstance(info, dict):
        return {}
    return info


def _extract_sector_label(ticker: str, metadata: Mapping[str, object]) -> str | None:
    """Extract sector label, with ETF-aware classification rules."""
    sector = _classify_sector(ticker, metadata)
    if sector:
        return sector

    for key in ("sectorDisp", "sector", "category", "industryDisp", "industry"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _classify_sector(ticker: str, info: Mapping[str, object]) -> str | None:
    """Classify sector using quote type and metadata heuristics.

    Mirrors frontend/domain expectations for ETF categorization so unknown
    labels are minimized for instruments like GOLDBEES/SILVERBEES.
    """
    quote_type = str(info.get("quoteType", "")).strip().upper()
    category = str(info.get("category", "")).strip().lower()
    long_name = str(info.get("longName", "")).strip().lower()
    short_name = str(info.get("shortName", "")).strip().lower()
    combined = " ".join([category, long_name, short_name, ticker.lower()])

    if quote_type == "ETF" or "etf" in combined:
        if any(x in combined for x in ("gold", "silver", "precious metal", "commodity")):
            return "Commodities"
        if any(x in combined for x in ("bond", "debt", "fixed income", "treasury")):
            return "Bonds"
        if any(x in combined for x in ("real estate", "reit")):
            return "Real Estate"
        if any(x in combined for x in ("large blend", "large growth", "equity", "index", "nifty", "sensex")):
            return "Broad Market ETF"
        if any(x in combined for x in ("small", "mid", "midcap", "smallcap")):
            return "Equity ETF"
        return "ETF"

    sector = info.get("sector")
    if isinstance(sector, str) and sector.strip():
        return sector.strip()

    return None


def infer_asset_class(ticker: str, info: dict | None = None) -> str:
    # Tier-2 override: if AI resolver classified this, trust it
    if info and info.get("_ai_asset_class"):
        return info["_ai_asset_class"]

    return _infer_asset_class_cached(ticker)


@lru_cache(maxsize=512)
def _infer_asset_class_cached(ticker: str) -> str:
    clean_ticker = ticker.strip().upper()
    if not clean_ticker:
        return "Unknown"

    # Suffix-based — authoritative, no network call needed
    if clean_ticker.endswith(".NS") or clean_ticker.endswith(".BO"):
        return "India Equities"
    if clean_ticker.endswith(".L") or clean_ticker.endswith(".LON"):
        return "UK Equities"
    if clean_ticker.endswith(".T") or clean_ticker.endswith(".TYO"):
        return "Japan Equities"
    if clean_ticker.endswith(".HK"):
        return "HK Equities"
    if clean_ticker.endswith(".KS") or clean_ticker.endswith(".KQ"):
        return "Korea Equities"
    if clean_ticker.endswith(".SS") or clean_ticker.endswith(".SZ"):
        return "China Equities"
    if clean_ticker.endswith(".DE") or clean_ticker.endswith(".PA") or clean_ticker.endswith(".AS"):
        return "European Equities"

    # No suffix — try yfinance metadata
    for candidate in _ticker_candidates(clean_ticker):
        info = _get_ticker_metadata(candidate)
        if not info:
            continue

        country = str(info.get("country", "")).strip().lower()
        exchange = str(info.get("exchange", "")).strip().upper()

        if exchange in {"NSE", "NSI", "BSE", "MCX"}:
            return "India Equities"
        if exchange in {"LSE", "LON"}:
            return "UK Equities"
        if exchange in {"TSE", "TYO"}:
            return "Japan Equities"
        if exchange in {"HKEX", "HKG"}:
            return "HK Equities"
        if exchange in {"KRX", "KOSDAQ"}:
            return "Korea Equities"
        if exchange in {"NMS", "NYQ", "NGM", "PCX", "NAS", "NYSE", "NASDAQ"}:
            return "US Equities"

        country_map = {
            "india": "India Equities",
            "united states": "US Equities",
            "china": "China Equities",
            "japan": "Japan Equities",
            "united kingdom": "UK Equities",
            "south korea": "Korea Equities",
            "hong kong": "HK Equities",
            "germany": "European Equities",
            "france": "European Equities",
            "netherlands": "European Equities",
        }
        if country in country_map:
            return country_map[country]

    # No suffix, no metadata match — assume US (bare tickers with no suffix are almost always US)
    if "." not in clean_ticker:
        return "US Equities"

    return "Unknown"


def _ticker_candidates(ticker: str) -> list[str]:
    """Generate robust ticker candidates for map and metadata lookup."""
    clean = ticker.strip().upper()
    if not clean:
        return []

    candidates: list[str] = [clean]
    if "." in clean:
        base = clean.split(".", 1)[0]
        candidates.append(base)
    else:
        candidates.append(f"{clean}.NS")
        candidates.append(f"{clean}.BO")

    # Preserve order but remove duplicates.
    seen: set[str] = set()
    unique: list[str] = []
    for item in candidates:
        if item not in seen:
            seen.add(item)
            unique.append(item)
    return unique


def _merge_and_save_sector_map(
    discovered_mappings: Mapping[str, str],
    file_path: str | None = None,
) -> None:
    """Persist newly discovered mappings to the sector map JSON file."""
    if not discovered_mappings:
        return

    path = Path(file_path) if file_path else DEFAULT_MAP_PATH
    current_map = load_sector_map(str(path))

    for ticker, sector in discovered_mappings.items():
        normalized_ticker = ticker.strip().upper()
        current_map[normalized_ticker] = sector
        if "." in normalized_ticker:
            current_map[normalized_ticker.split(".", 1)[0]] = sector

    ordered = dict(sorted(current_map.items(), key=lambda item: item[0]))
    with path.open("w", encoding="utf-8") as handle:
        json.dump(ordered, handle, indent=2)
        handle.write("\n")


if __name__ == "__main__":
    sample_assets = [
        {"ticker": "TCS", "weight": 0.35},
        {"ticker": "HDFCBANK", "weight": 0.25},
        {"ticker": "RELIANCE", "weight": 0.40},
    ]
    print(calculate_sector_exposure(sample_assets))
