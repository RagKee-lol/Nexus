"""
Risk Agent — evaluates the stock's risk characteristics AND, critically,
whether a larger position is suitable for THIS investor's portfolio and
risk profile. This is what prevents NEXUS from being "just a signal
aggregator": market attractiveness is deliberately kept separate from
portfolio suitability.
"""
from __future__ import annotations

from agents.base import BaseAgent, AgentResult, Evidence


class RiskAgent(BaseAgent):
    name = "risk"

    def run(self, ticker: str, market_data: dict, profile: dict, portfolio: dict,
            proposed_allocation_pct: float | None = None) -> AgentResult:
        return self._timed(self._analyze, ticker, market_data, profile, portfolio, proposed_allocation_pct)

    def _analyze(self, ticker: str, market_data: dict, profile: dict, portfolio: dict,
                 proposed_allocation_pct: float | None) -> AgentResult:
        t = market_data["technical"]
        volatility = t["volatility_30d"]
        sector = market_data["sector"]

        holdings = portfolio.get("holdings", {})
        current_alloc = holdings.get(ticker, {}).get("allocation_pct", 0.0)
        sector_exposure = portfolio.get("sector_exposure", {}).get(sector, 0.0)
        max_pref = profile["max_preferred_position_pct"]
        vol_tolerance = profile["volatility_tolerance"]

        proposed = proposed_allocation_pct if proposed_allocation_pct is not None else current_alloc

        factors: list[str] = []
        warnings: list[str] = []
        risk_score = 30  # baseline

        # Position concentration risk
        if proposed > max_pref:
            over_by = proposed - max_pref
            risk_score += min(40, round(over_by * 4))
            warnings.append(
                f"Proposed position ({proposed:.1f}%) exceeds the {profile['name']} profile's "
                f"preferred maximum of {max_pref:.1f}% by {over_by:.1f} points"
            )
            factors.append(f"Position concentration exceeds preferred maximum for {profile['name']} profile")
        else:
            factors.append(f"Position size of {proposed:.1f}% is within the preferred maximum of {max_pref:.1f}%")

        # Sector concentration
        if sector_exposure > 20:
            risk_score += 15
            warnings.append(f"Sector exposure to {sector} is already {sector_exposure:.1f}% of portfolio")
            factors.append(f"High existing sector concentration in {sector} ({sector_exposure:.1f}%)")
        elif sector_exposure > 12:
            risk_score += 7
            factors.append(f"Moderate sector concentration in {sector} ({sector_exposure:.1f}%)")
        else:
            factors.append(f"Sector concentration in {sector} is limited ({sector_exposure:.1f}%)")

        # Volatility vs tolerance
        vol_thresholds = {"LOW": 12, "MEDIUM": 18, "HIGH": 30}
        threshold = vol_thresholds.get(vol_tolerance, 18)
        if volatility > threshold:
            risk_score += 15
            warnings.append(
                f"Stock volatility ({volatility:.1f}%) exceeds this investor's {vol_tolerance} tolerance threshold (~{threshold}%)"
            )
            factors.append(f"30-day volatility of {volatility:.1f}% exceeds {vol_tolerance} tolerance")
        else:
            factors.append(f"30-day volatility of {volatility:.1f}% is within {vol_tolerance} tolerance")

        # Horizon-based drawdown sensitivity
        horizon = profile["investment_horizon"]
        if "1-3" in horizon and volatility > 15:
            risk_score += 8
            factors.append("Shorter investment horizon increases sensitivity to near-term drawdowns")

        risk_score = max(0, min(100, risk_score))

        if risk_score >= 65:
            signal = "CAUTION"
        elif risk_score >= 45:
            signal = "MONITOR"
        else:
            signal = "ACCEPTABLE"

        confidence = round(min(0.95, 0.55 + risk_score / 250), 2)

        evidence = [
            Evidence(
                source="Portfolio Snapshot (Demo)",
                document="data/portfolio.json",
                chunk=(
                    f"Profile={profile['name']}, current_allocation={current_alloc:.1f}%, "
                    f"proposed_allocation={proposed:.1f}%, sector_exposure({sector})={sector_exposure:.1f}%, "
                    f"max_preferred_position={max_pref:.1f}%, volatility_tolerance={vol_tolerance}"
                ),
                relevance=1.0,
                kind="dataset",
            )
        ]

        return AgentResult(
            agent=self.name,
            status="ok",
            signal=signal,
            confidence=confidence,
            score=risk_score,
            factors=factors,
            evidence=evidence,
            warnings=warnings,
        )
