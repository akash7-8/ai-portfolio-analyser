"""Tier-2 AI resolver: SearXNG web search -> Groq LLM -> structured ticker metadata.
Called by normalize_ticker_with_fallback() in data_fetcher.py when yfinance
cannot validate a symbol from Tier-1 rule-based normalization.
"""

from __future__ import annotations

import asyncio
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
    searxng_url = os.environ.get("SEARXNG_BASE_URL", "").rstrip("/")
    if not searxng_url:
        logger.warning("[AI Resolver] SEARXNG_BASE_URL not set, skipping search")
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{searxng_url}/search",
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
    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    if not groq_api_key:
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
                    "Authorization": f"Bearer {groq_api_key}",
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


async def ai_resolve_tickers_batch(tickers: list[str]) -> dict[str, dict]:
    """Resolve multiple failed tickers in a single SearXNG + Groq round trip."""
    if not tickers:
        return {}

    groq_api_key = os.environ.get("GROQ_API_KEY", "")
    searxng_base_url = os.environ.get("SEARXNG_BASE_URL", "").rstrip("/")

    if not groq_api_key:
        logger.warning("[AI Resolver Batch] GROQ_API_KEY not set, skipping batch resolve.")
        return {}

    async def _search_one(ticker: str) -> tuple[str, list[str]]:
        if not searxng_base_url:
            return ticker, []
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    f"{searxng_base_url}/search",
                    params={
                        "q": f"{ticker} NSE BSE stock ticker symbol",
                        "format": "json",
                    },
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])[:3]
                snippets = [
                    f"{result.get('title', '')} {result.get('content', '')}"[:300]
                    for result in results
                ]
                return ticker, snippets
        except Exception as exc:  # noqa: BLE001 - best-effort context fetch
            logger.warning("[AI Resolver Batch] SearXNG failed for %s: %s", ticker, exc)
            return ticker, []

    search_results = await asyncio.gather(*[_search_one(ticker) for ticker in tickers])

    ticker_context_block = ""
    for ticker, snippets in search_results:
        snippet_text = " | ".join(snippets) if snippets else "No search results found."
        ticker_context_block += f"\nTicker: {ticker}\nContext: {snippet_text}\n"

    prompt = f"""You are a financial data expert. Resolve each ticker symbol below to its correct Yahoo Finance format using the search context provided.

{ticker_context_block}

Return ONLY a valid JSON array, no preamble, no markdown fences:
[
  {{
    "input": "<original ticker>",
    "normalized_ticker": "<Yahoo Finance format e.g. MAZDOCK.NS>",
    "exchange": "<NSE|BSE|NYSE|NASDAQ|etc>",
    "country": "<country name>",
    "sector": "<sector name>",
    "asset_class": "<India Equities|US Equities|ETF|etc>"
  }}
]

Rules:
- For Indian stocks use .NS suffix for NSE, .BO for BSE
- If you cannot confidently resolve a ticker, set normalized_ticker to null
- Return one object per input ticker, in the same order
- Return ONLY the JSON array"""

    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "llama-3.1-8b-instant",
        "max_tokens": 500,
        "temperature": 0.1,
        "messages": [{"role": "user", "content": prompt}],
    }

    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"].strip()
                if raw.startswith("```"):
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                parsed = json.loads(raw)

                result: dict[str, dict] = {}
                for item in parsed:
                    input_ticker = item.get("input")
                    if input_ticker and item.get("normalized_ticker"):
                        result[str(input_ticker)] = item

                logger.info(
                    "[AI Resolver Batch] Resolved %d/%d tickers in one Groq call.",
                    len(result),
                    len(tickers),
                )
                return result
        except (json.JSONDecodeError, KeyError) as exc:
            if attempt == 0:
                logger.warning("[AI Resolver Batch] Parse failed, retrying: %s", exc)
                continue
            logger.error("[AI Resolver Batch] Failed after 2 attempts: %s", exc)
            return {}
        except Exception as exc:  # noqa: BLE001 - API/network failure
            logger.error("[AI Resolver Batch] Groq call failed: %s", exc)
            return {}

    return {}
