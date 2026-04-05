"""Tier-2 AI resolver: SearXNG web search -> Groq LLM -> structured ticker metadata.
Called by normalize_ticker_with_fallback() in data_fetcher.py when yfinance
cannot validate a symbol from Tier-1 rule-based normalization.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)

SEARXNG_BASE_URL = os.getenv("SEARXNG_BASE_URL", "").rstrip("/")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

REQUIRED_KEYS = {"normalized_ticker", "exchange", "country", "sector", "asset_class"}

VALID_ASSET_CLASSES = {
    "India Equities",
    "US Equities",
    "UK Equities",
    "China Equities",
    "Japan Equities",
    "Korea Equities",
    "HK Equities",
    "European Equities",
    "Unknown",
}


async def _searxng_search(query: str, num_results: int = 5) -> list[dict]:
    print(f"[AI Resolver] _searxng_search called, SEARXNG_BASE_URL='{SEARXNG_BASE_URL}'", flush=True)
    if not SEARXNG_BASE_URL:
        logger.warning("[AI Resolver] SEARXNG_BASE_URL not set, skipping search")
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{SEARXNG_BASE_URL}/search",
                params={
                    "q": query,
                    "format": "json",
                    "language": "en",
                    "safesearch": "0",
                },
            )
            resp.raise_for_status()
            results = resp.json().get("results", [])[:num_results]
            return [
                {"title": result.get("title", ""), "content": result.get("content", "")}
                for result in results
            ]
    except Exception as exc:  # noqa: BLE001 - resolver must never raise
        logger.error("[AI Resolver] SearXNG search failed: %s", exc)
        return []


async def _groq_resolve(ticker: str, snippets: list[dict]) -> Optional[dict]:
    if not GROQ_API_KEY:
        logger.warning("[AI Resolver] GROQ_API_KEY not set")
        return None

    snippets_text = (
        "\n".join(
            f"- {snippet['title']}: {snippet['content']}"
            for snippet in snippets
            if snippet.get("content")
        )
        or "No search results available."
    )

    user_prompt = f"""Ticker symbol: {ticker}

Web search results about this ticker:
{snippets_text}

Return ONLY a JSON object with exactly these fields (no markdown, no explanation):
{{
  "normalized_ticker": "<how this ticker appears in yfinance, e.g. RELIANCE.NS or AAPL or 7203.T>",
  "exchange": "<e.g. NSE, BSE, NYSE, NASDAQ, LSE, TSE>",
  "country": "<e.g. India, USA, UK, Japan, China>",
  "sector": "<GICS sector e.g. Energy, Financials, Information Technology>",
  "asset_class": "<exactly one of: India Equities, US Equities, UK Equities, China Equities, Japan Equities, Korea Equities, HK Equities, European Equities, Unknown>"
}}"""

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": GROQ_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a financial data expert. Always respond with valid "
                                "JSON only. No markdown fences, no explanation, no extra text."
                            ),
                        },
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.1,
                    "max_tokens": 200,
                },
            )
            resp.raise_for_status()

            raw = resp.json()["choices"][0]["message"]["content"].strip()
            raw = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)

            if not isinstance(parsed, dict):
                return None
            if not REQUIRED_KEYS.issubset(parsed.keys()):
                logger.warning("[AI Resolver] Groq response missing keys: %s", parsed)
                return None

            if parsed["asset_class"] not in VALID_ASSET_CLASSES:
                parsed["asset_class"] = "Unknown"

            return parsed

    except json.JSONDecodeError as exc:
        logger.error("[AI Resolver] Groq non-JSON response for %s: %s", ticker, exc)
        return None
    except Exception as exc:  # noqa: BLE001 - resolver must never raise
        logger.error("[AI Resolver] Groq call failed for %s: %s", ticker, exc)
        return None


async def ai_resolve_ticker(ticker: str) -> Optional[dict]:
    """Run SearXNG -> Groq pipeline and return structured ticker metadata."""
    print(f"[AI Resolver] ai_resolve_ticker called for: {ticker}", flush=True)
    query = (
        f"{ticker} stock ticker symbol exchange yfinance "
        "site:finance.yahoo.com OR site:screener.in OR site:moneycontrol.com OR site:nseindia.com"
    )
    logger.info("[AI Resolver] Resolving ticker: %s", ticker)

    snippets = await _searxng_search(query)
    result = await _groq_resolve(ticker, snippets)

    if result:
        logger.info(
            "[AI Resolver] %s -> %s (%s)",
            ticker,
            result["normalized_ticker"],
            result["asset_class"],
        )
    else:
        logger.warning("[AI Resolver] Failed to resolve: %s", ticker)

    return result
