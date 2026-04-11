"""Portfolio recommendation engine - Groq LLM SWOT with SearXNG news context."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Dict, List, Mapping, Optional

import httpx

logger = logging.getLogger(__name__)


# -- Groq SWOT (primary) -------------------------------------------------------


async def generate_swot_with_groq(
    diversification_score: float,
    sector_exposure: Mapping[str, float],
    holdings: List[Dict],
    metrics: Dict,
    monte_carlo: Dict,
    total_value: float,
    concentration_threshold: float = 0.40,
) -> Dict:
    """Primary SWOT engine using SearXNG context + Groq with safe fallback."""
    try:
        queries = _build_searxng_queries(holdings, sector_exposure)
        snippets = await _fetch_news_snippets(queries)
        prompt = _build_groq_prompt(
            diversification_score,
            sector_exposure,
            holdings,
            metrics,
            monte_carlo,
            total_value,
            snippets,
            concentration_threshold,
        )
        swot = await _call_groq_swot(prompt)
        swot["swot_source"] = "groq_llm"
        swot["swot_news_context"] = [
            s["title"] for s in snippets if s.get("title")
        ][:10]
        swot["summary"] = swot.get("summary", "")
        swot["actions"] = swot.get("strengths", []) + swot.get("opportunities", [])
        swot["concentration_flags"] = _get_concentration_flags(
            sector_exposure, concentration_threshold
        )
        return swot
    except Exception as exc:  # noqa: BLE001 - keep API resilient
        logger.warning("Groq SWOT failed (%s), falling back to rule-based.", exc)
        result = generate_swot_rule_based(
            diversification_score,
            sector_exposure,
            concentration_threshold,
        )
        result["swot_source"] = "rule_based"
        result["swot_news_context"] = []
        return result


def _build_searxng_queries(
    holdings: List[Dict],
    sector_exposure: Mapping[str, float],
) -> List[str]:
    queries: List[str] = []

    top_holdings = sorted(
        holdings,
        key=lambda h: float(h.get("weight", 0) or 0),
        reverse=True,
    )[:3]
    for holding in top_holdings:
        ticker = str(holding.get("ticker", "")).strip()
        if ticker:
            queries.append(f"{ticker} stock news 2026")

    top_sectors = sorted(
        sector_exposure.items(),
        key=lambda item: item[1],
        reverse=True,
    )[:2]
    for sector, _ in top_sectors:
        if sector:
            queries.append(f"{sector} sector India outlook 2026")

    return queries


async def _fetch_news_snippets(queries: List[str]) -> List[Dict]:
    base_url = os.environ.get("SEARXNG_BASE_URL", "").rstrip("/")
    if not base_url:
        logger.warning("SEARXNG_BASE_URL not set, skipping news fetch.")
        return []

    async def _search(query: str) -> List[Dict]:
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    f"{base_url}/search",
                    params={"q": query, "format": "json", "engines": "google,bing"},
                )
                resp.raise_for_status()
                results = resp.json().get("results", [])[:3]
                return [
                    {
                        "title": result.get("title"),
                        "content": result.get("content", ""),
                    }
                    for result in results
                ]
        except Exception as exc:  # noqa: BLE001 - best-effort market context
            logger.warning("SearXNG query failed for '%s': %s", query, exc)
            return []

    nested_results = await asyncio.gather(*[_search(query) for query in queries])
    return [item for sublist in nested_results for item in sublist]


def _build_groq_prompt(
    diversification_score: float,
    sector_exposure: Mapping[str, float],
    holdings: List[Dict],
    metrics: Dict,
    monte_carlo: Dict,
    total_value: float,
    snippets: List[Dict],
    concentration_threshold: float,
) -> str:
    holdings_text = "\n".join(
        f"  - {h['ticker']}: {float(h.get('weight', 0) or 0) * 100:.1f}% | {h.get('sector', 'Unknown')} | ?{h.get('current_price', 'N/A')}"
        for h in sorted(holdings, key=lambda x: float(x.get("weight", 0) or 0), reverse=True)[:10]
        if h.get("ticker")
    )
    sector_text = "\n".join(
        f"  - {sector}: {weight * 100:.1f}%"
        for sector, weight in sorted(
            sector_exposure.items(),
            key=lambda x: x[1],
            reverse=True,
        )
    )
    news_text = "\n".join(
        f"  [{idx + 1}] {snippet.get('title', '')}: {str(snippet.get('content', ''))[:200]}"
        for idx, snippet in enumerate(snippets[:9])
    ) or "  No live news context available."

    return f"""You are an expert portfolio analyst specialising in Indian and global equity markets.

PORTFOLIO OVERVIEW:
  Total Value: ?{total_value:,.2f}
  Diversification Score: {diversification_score:.1f}/100
  Portfolio Score: {metrics.get('portfolio_score', 'N/A')}/100
  HHI Score: {metrics.get('hhi_score', 'N/A')}
  Concentration Threshold: {concentration_threshold:.2f}

RISK & RETURN METRICS:
  Beta: {metrics.get('beta', 'N/A')}
  Alpha: {metrics.get('alpha', 'N/A')}
  Sharpe Ratio: {metrics.get('sharpe', 'N/A')}
  Annual Return: {metrics.get('annualReturn', 'N/A')}
  Daily Change: {metrics.get('dailyChangePct', 'N/A')}%

TOP HOLDINGS:
{holdings_text}

SECTOR EXPOSURE:
{sector_text}

MONTE CARLO PROJECTION (24 months):
  Optimistic (P90): ?{monte_carlo.get('p90', 'N/A')}
  Base Case (P50): ?{monte_carlo.get('p50', 'N/A')}
  Pessimistic (P10): ?{monte_carlo.get('p10', 'N/A')}

LIVE MARKET CONTEXT:
{news_text}

Generate a SWOT analysis for this specific portfolio. Every point must reference actual tickers, weights, sectors, or news from above and avoid generic statements. Return ONLY this JSON:

{{
  "strengths": ["...", "...", "..."],
  "weaknesses": ["...", "...", "..."],
  "opportunities": ["...", "...", "..."],
  "threats": ["...", "...", "..."],
  "summary": "2-3 sentence executive summary referencing this portfolio specifically"
}}"""


def _parse_groq_swot(raw: str) -> Optional[Dict]:
    text = raw.strip()
    if text.startswith("```"):
        parts = text.split("```")
        if len(parts) >= 2:
            text = parts[1].strip()
        if text.startswith("json"):
            text = text[4:].strip()

    parsed = json.loads(text)
    if not isinstance(parsed, dict):
        return None

    for key in ("strengths", "weaknesses", "opportunities", "threats"):
        if not isinstance(parsed.get(key), list):
            return None
    if not isinstance(parsed.get("summary", ""), str):
        return None

    return parsed


async def _call_groq_swot(prompt: str) -> Dict:
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not set")

    payload = {
        "model": "llama-3.1-8b-instant",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error: Exception | None = None
    for attempt in range(2):
        try:
            async with httpx.AsyncClient(timeout=20) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )
                resp.raise_for_status()
                raw = resp.json()["choices"][0]["message"]["content"]
                parsed = _parse_groq_swot(raw)
                if not parsed:
                    raise ValueError("Groq SWOT response missing expected JSON structure")
                return parsed
        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            last_error = exc
            if attempt == 0:
                logger.warning("Groq SWOT parse failed, retrying: %s", exc)
                continue
            raise RuntimeError("Groq SWOT failed after 2 attempts") from exc
        except Exception as exc:  # noqa: BLE001 - network/API failure
            last_error = exc
            if attempt == 0:
                logger.warning("Groq SWOT request failed, retrying: %s", exc)
                continue
            raise RuntimeError("Groq SWOT failed after 2 attempts") from exc

    raise RuntimeError("Groq SWOT failed after 2 attempts") from last_error


# -- Rule-based fallback (original logic, renamed) -----------------------------


def generate_swot_rule_based(
    diversification_score: float,
    sector_exposure: Mapping[str, float],
    concentration_threshold: float = 0.40,
) -> Dict[str, object]:
    """Generate actionable recommendations for portfolio improvement."""
    diversification = _clamp(diversification_score, 0.0, 100.0)
    normalized_sector_exposure = _normalize_sector_exposure(sector_exposure)

    concentration_flags = [
        {
            "sector": sector,
            "weight": round(weight, 4),
            "threshold": concentration_threshold,
        }
        for sector, weight in sorted(normalized_sector_exposure.items())
        if weight > concentration_threshold
    ]

    actions: List[str] = []

    if diversification < 50:
        actions.append(
            "Increase diversification by adding assets from unrepresented sectors "
            "and reducing dependence on a few holdings."
        )
    elif diversification < 70:
        actions.append(
            "Improve diversification gradually through periodic rebalancing toward "
            "a broader sector mix."
        )
    else:
        actions.append(
            "Diversification is healthy; maintain it with disciplined rebalancing "
            "and position-size limits."
        )

    if concentration_flags:
        flagged = ", ".join(
            f"{item['sector']} ({item['weight']:.2f})" for item in concentration_flags
        )
        actions.append(
            "Reduce sector concentration to below "
            f"{concentration_threshold:.2f} for: {flagged}."
        )
        actions.append(
            "Reallocate part of concentrated exposure into defensive or "
            "low-correlation sectors to improve downside resilience."
        )
    else:
        actions.append(
            "No sector exceeds the concentration threshold; keep monitoring sector "
            "drift during market rallies."
        )

    if "Unknown" in normalized_sector_exposure:
        actions.append(
            "Map unknown tickers to sectors to improve recommendation precision "
            "and risk attribution quality."
        )

    summary = _build_summary(diversification, concentration_flags)

    return {
        "summary": summary,
        "actions": actions,
        "concentration_flags": concentration_flags,
        "strengths": [],
        "weaknesses": [],
        "opportunities": actions[:2],
        "threats": [],
    }


def _get_concentration_flags(
    sector_exposure: Mapping[str, float],
    threshold: float,
) -> List[Dict[str, float | str]]:
    return [
        {"sector": sector, "weight": round(weight, 4), "threshold": threshold}
        for sector, weight in sector_exposure.items()
        if weight > threshold
    ]


def _build_summary(diversification: float, concentration_flags: List[dict]) -> str:
    """Create a concise overall recommendation summary."""
    if diversification < 50 and concentration_flags:
        return (
            "Portfolio improvement priority is high: diversification is weak and "
            "sector concentration risk is elevated."
        )
    if diversification < 50:
        return (
            "Portfolio improvement priority is medium-high: diversification is below "
            "target levels."
        )
    if concentration_flags:
        return (
            "Portfolio improvement priority is medium: concentration hotspots should "
            "be reduced to improve risk balance."
        )
    return (
        "Portfolio structure is broadly balanced; focus on maintenance rebalancing "
        "and periodic allocation reviews."
    )


def _normalize_sector_exposure(sector_exposure: Mapping[str, float]) -> Dict[str, float]:
    """Normalize and sanitize sector exposure inputs."""
    normalized: Dict[str, float] = {}
    for sector, weight in sector_exposure.items():
        if not isinstance(sector, str) or not sector.strip():
            continue
        try:
            numeric_weight = float(weight)
        except (TypeError, ValueError):
            continue
        normalized[sector.strip()] = numeric_weight
    return normalized


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))


# keep old name as alias so nothing else breaks if called directly
generate_portfolio_recommendations = generate_swot_rule_based


if __name__ == "__main__":
    sample = generate_swot_rule_based(
        diversification_score=42.5,
        sector_exposure={"Technology": 0.62, "Banking": 0.25, "Energy": 0.13},
    )
    print(sample)
