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


async def scrape_screener_in(ticker: str) -> dict | None:
    """
    Fetch stock data from screener.in for Indian equities.
    Returns partial data dict or None if not found.
    """
    clean = ticker.replace(".NS", "").replace(".BO", "").upper()
    url = f"https://www.screener.in/company/{clean}/"

    try:
        async with httpx.AsyncClient(
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        result: dict[str, object] = {}

        ratios = soup.select("#top-ratios li")
        for li in ratios:
            label = li.select_one(".name")
            value = li.select_one(".number")
            if not label or not value:
                continue
            label_text = label.get_text(strip=True).lower()
            value_text = value.get_text(strip=True).replace(",", "")
            try:
                if "market cap" in label_text:
                    result["market_cap"] = float(value_text)
                elif "p/e" in label_text:
                    result["pe_ratio"] = float(value_text)
                elif "52w high" in label_text or "high" in label_text:
                    result["week_52_high"] = float(value_text)
                elif "52w low" in label_text or "low" in label_text:
                    result["week_52_low"] = float(value_text)
            except ValueError:
                continue

        price_candidates = soup.select(".company-ratios .number")
        if price_candidates:
            try:
                result["current_price"] = float(
                    price_candidates[0].get_text(strip=True).replace(",", "")
                )
            except ValueError:
                pass

        sector_el = soup.select_one(".company-links a")
        if sector_el:
            result["sector"] = sector_el.get_text(strip=True)

        if result:
            result["source"] = "screener.in"
            result["confidence"] = "medium"
            result["ticker"] = clean
            logger.info("[Screener.in] Fetched data for %s: %s", clean, result)
            return result
        return None

    except Exception as exc:  # noqa: BLE001 - scraper is best-effort
        logger.warning("[Screener.in] Failed for %s: %s", ticker, exc)
        return None


async def ai_web_search_price(ticker: str, context_hints: dict = None) -> dict | None:
    """
    Last-resort price fetch via SearXNG search + Groq extraction.
    Used when both yfinance and screener.in fail.

    Returns partial data dict with current_price and whatever else
    Groq could confidently extract, or None if extraction fails.
    """
    _ = context_hints
    searxng_base_url = os.environ.get("SEARXNG_BASE_URL", "").rstrip("/")
    groq_api_key = os.environ.get("GROQ_API_KEY", "")

    if not searxng_base_url or not groq_api_key:
        return None

    clean = ticker.replace(".NS", "").replace(".BO", "")
    queries = [
        f"{clean} share price today NSE",
        f"{clean} stock current price India 2026",
    ]

    snippets: list[str] = []
    async with httpx.AsyncClient(timeout=8) as client:
        for query in queries:
            try:
                resp = await client.get(
                    f"{searxng_base_url}/search",
                    params={"q": query, "format": "json"},
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])[:3]
                for result in results:
                    snippets.append(
                        f"{result.get('title', '')} | {result.get('content', '')[:300]}"
                    )
            except Exception as exc:  # noqa: BLE001 - continue with partial snippets
                logger.warning("[WebSearch] Query failed for %s: %s", ticker, exc)

    if not snippets:
        return None

    prompt = f"""Extract stock data for ticker {clean} from these search snippets.
Return ONLY valid JSON, no preamble:

Snippets:
{chr(10).join(snippets)}

{{
  "current_price": <number or null>,
  "currency": "<INR or USD or null>",
  "sector": "<sector name or null>",
  "market_cap": <number in crores or null>,
  "annual_return_1y": <decimal e.g. 0.12 for 12% or null>,
  "confidence": "<high|medium|low>"
}}

Rules:
- Only include values you are confident about from the snippets
- Set to null if not clearly mentioned
- current_price must be a recent trading price, not a historical one"""

    try:
        headers = {
            "Authorization": f"Bearer {groq_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "llama-3.1-8b-instant",
            "max_tokens": 200,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}],
        }
        async with httpx.AsyncClient(timeout=15) as client:
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
            if parsed.get("current_price"):
                parsed["source"] = "ai_web_search"
                parsed["ticker"] = clean
                logger.info("[WebSearch] Extracted data for %s: %s", clean, parsed)
                return parsed
            return None
    except Exception as exc:  # noqa: BLE001 - extraction should not crash flow
        logger.warning("[WebSearch] Groq extraction failed for %s: %s", ticker, exc)
        return None


async def fetch_finviz(ticker: str) -> dict | None:
    """
    Fetch US stock data from Finviz. Only call for tickers without .NS/.BO suffix.
    """
    if ".NS" in ticker or ".BO" in ticker:
        return None

    url = f"https://finviz.com/quote.ashx?t={ticker.upper()}"
    try:
        async with httpx.AsyncClient(
            timeout=10,
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
        ) as client:
            resp = await client.get(url)
            if resp.status_code in (404, 403):
                return None
            resp.raise_for_status()

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        result: dict[str, object] = {}

        table = soup.select("table.snapshot-table2 td")
        labels: dict[str, str] = {}
        for i in range(0, len(table) - 1, 2):
            label = table[i].get_text(strip=True).lower()
            value = table[i + 1].get_text(strip=True)
            labels[label] = value

        def parse_num(val: str) -> float | None:
            try:
                normalized = (
                    val.replace(",", "")
                    .replace("%", "")
                    .replace("B", "e9")
                    .replace("M", "e6")
                )
                return float(normalized)
            except ValueError:
                return None

        if "price" in labels:
            result["current_price"] = parse_num(labels["price"])
        if "beta" in labels:
            result["beta"] = parse_num(labels["beta"])
        if "52w high" in labels:
            result["week_52_high"] = parse_num(labels["52w high"])
        if "52w low" in labels:
            result["week_52_low"] = parse_num(labels["52w low"])
        if "sector" in labels:
            result["sector"] = labels["sector"]
        if "perf year" in labels:
            value = parse_num(labels["perf year"])
            if value is not None:
                result["annual_return_1y"] = value / 100

        if result.get("current_price"):
            result["source"] = "finviz"
            result["confidence"] = "high"
            result["ticker"] = ticker.upper()
            logger.info("[Finviz] Fetched data for %s: %s", ticker, result)
            return result
        return None

    except Exception as exc:  # noqa: BLE001 - scraper is best-effort
        logger.warning("[Finviz] Failed for %s: %s", ticker, exc)
        return None
