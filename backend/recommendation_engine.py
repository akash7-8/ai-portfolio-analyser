"""Portfolio recommendation engine.

Generates portfolio-improvement suggestions from diversification score and
sector concentration patterns.
"""

from __future__ import annotations

from typing import Dict, List, Mapping


def generate_portfolio_recommendations(
    diversification_score: float,
    sector_exposure: Mapping[str, float],
    concentration_threshold: float = 0.40,
) -> Dict[str, object]:
    """Generate actionable recommendations for portfolio improvement.

    Args:
        diversification_score: Portfolio diversification score in range 0-100.
        sector_exposure: Mapping of sector -> weight.
        concentration_threshold: Sector concentration warning threshold.

    Returns:
        Dictionary with summary, action items, and concentration flags.
        This is designed as an additive feature and does not replace existing
        explanation modules.
    """
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
    }


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


if __name__ == "__main__":
    sample = generate_portfolio_recommendations(
        diversification_score=42.5,
        sector_exposure={"Technology": 0.62, "Banking": 0.25, "Energy": 0.13},
    )
    print(sample)
