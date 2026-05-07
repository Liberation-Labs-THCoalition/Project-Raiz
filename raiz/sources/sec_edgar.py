"""SEC EDGAR — following the money to the pollution.

pip install edgartools

Every publicly traded company files 10-K (annual) and 10-Q (quarterly)
reports with the SEC. Buried in these filings are environmental
liability disclosures — remediation costs, Superfund designations,
EPA consent decrees, pending environmental litigation.

The community downwind doesn't read 10-Ks. Raíz does.

When Springfield Chemical Corp discloses "$4.2 million in environmental
remediation reserves" in their 10-K, that's an admission that they
know they're contaminating something. Raíz finds it, maps it to the
facility, maps the facility to the neighborhood.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EnvironmentalDisclosure:
    """An environmental disclosure extracted from an SEC filing."""
    company: str
    ticker: str
    filing_type: str  # 10-K, 10-Q, 8-K
    filing_date: str
    section: str  # e.g., "Environmental Matters", "Legal Proceedings"
    excerpt: str
    disclosure_type: str  # remediation, litigation, consent_decree, superfund, penalty
    dollar_amount: float = 0.0
    facilities_mentioned: list[str] = field(default_factory=list)
    chemicals_mentioned: list[str] = field(default_factory=list)
    regulatory_actions: list[str] = field(default_factory=list)
    severity: str = "low"  # low, medium, high, critical


@dataclass
class CorporateEnvironmentalProfile:
    """Complete environmental accountability profile for a company."""
    company: str
    ticker: str
    cik: str = ""
    disclosures: list[EnvironmentalDisclosure] = field(default_factory=list)
    total_remediation_reserves: float = 0.0
    active_consent_decrees: int = 0
    superfund_sites: int = 0
    pending_litigation: int = 0
    epa_penalties_disclosed: float = 0.0

    def summarize(self) -> str:
        parts = [f"Corporate Environmental Profile: {self.company} ({self.ticker})"]
        parts.append("=" * 60)

        if self.total_remediation_reserves > 0:
            parts.append(
                f"  Remediation reserves: ${self.total_remediation_reserves:,.0f}"
                " — they KNOW they're contaminating"
            )
        if self.superfund_sites > 0:
            parts.append(f"  Superfund sites: {self.superfund_sites}")
        if self.active_consent_decrees > 0:
            parts.append(f"  Active consent decrees: {self.active_consent_decrees}")
        if self.pending_litigation > 0:
            parts.append(f"  Pending environmental litigation: {self.pending_litigation}")
        if self.epa_penalties_disclosed > 0:
            parts.append(f"  EPA penalties disclosed: ${self.epa_penalties_disclosed:,.0f}")

        if self.disclosures:
            parts.append(f"\n  Recent disclosures ({len(self.disclosures)}):")
            for d in self.disclosures[:5]:
                parts.append(f"    [{d.filing_date}] {d.disclosure_type}: {d.excerpt[:120]}...")
                if d.dollar_amount > 0:
                    parts.append(f"      Amount: ${d.dollar_amount:,.0f}")

        return "\n".join(parts)


# Keywords that indicate environmental liability in SEC filings
ENVIRONMENTAL_KEYWORDS = [
    r"environmental\s+remediation",
    r"remediation\s+(costs?|reserves?|liabilit)",
    r"superfund",
    r"cercla",
    r"consent\s+decree",
    r"clean\s+air\s+act",
    r"clean\s+water\s+act",
    r"rcra",
    r"environmental\s+litigation",
    r"environmental\s+proceedings",
    r"contamination",
    r"groundwater\s+(contamination|pollution|remediation)",
    r"soil\s+(contamination|remediation)",
    r"epa\s+(enforcement|penalty|fine|notice|violation)",
    r"nox|sox|particulate\s+matter|pm2\.?5",
    r"toxic\s+(release|substance|waste)",
    r"hazardous\s+(waste|substance|material)",
    r"emission[s]?\s+(exceedance|violation|limit)",
    r"environmental\s+reserve",
    r"pollution\s+(control|prevention|liability)",
    r"asbestos\s+liabilit",
]

# Patterns for extracting dollar amounts near environmental context
DOLLAR_PATTERN = re.compile(
    r"\$\s*([\d,]+(?:\.\d+)?)\s*(million|billion|thousand)?",
    re.IGNORECASE,
)

DISCLOSURE_TYPE_PATTERNS = {
    "remediation": re.compile(r"remediat|cleanup|restoration", re.I),
    "litigation": re.compile(r"litigation|lawsuit|legal\s+proceed|plaintiff|defendant", re.I),
    "consent_decree": re.compile(r"consent\s+decree|settlement\s+agreement", re.I),
    "superfund": re.compile(r"superfund|cercla|national\s+priorities\s+list", re.I),
    "penalty": re.compile(r"penalty|fine|civil\s+penalty|stipulated\s+penalty", re.I),
    "violation": re.compile(r"violation|non-?compliance|exceedance|notice\s+of\s+violation", re.I),
}


class SecEdgarSource:
    """Search SEC filings for environmental liability disclosures.

    Uses edgartools for filing access. Falls back to dry-run mode
    if not installed.
    """

    def __init__(self, dry_run: bool = False) -> None:
        self._dry_run = dry_run
        self._compiled_keywords = [re.compile(k, re.I) for k in ENVIRONMENTAL_KEYWORDS]

    async def search_company(self, ticker: str) -> CorporateEnvironmentalProfile:
        """Search a company's recent filings for environmental disclosures."""
        if self._dry_run:
            return self._mock_profile(ticker)

        try:
            from edgar import Company
        except ImportError:
            logger.error("edgartools not installed — pip install edgartools")
            return CorporateEnvironmentalProfile(company="", ticker=ticker)

        try:
            company = Company(ticker)
            profile = CorporateEnvironmentalProfile(
                company=company.name,
                ticker=ticker,
                cik=str(company.cik),
            )

            filings = company.get_filings(form=["10-K", "10-Q"]).latest(10)

            for filing in filings:
                try:
                    text = filing.text()[:500000]
                    disclosures = self._extract_disclosures(
                        text, company.name, ticker,
                        filing.form, filing.filing_date,
                    )
                    profile.disclosures.extend(disclosures)
                except Exception as e:
                    logger.warning("Failed to process filing: %s", e)

            self._compute_aggregates(profile)
            return profile

        except Exception as e:
            logger.error("SEC EDGAR search failed for %s: %s", ticker, e)
            return CorporateEnvironmentalProfile(company="", ticker=ticker)

    async def search_by_facility_owner(self, parent_company: str) -> CorporateEnvironmentalProfile | None:
        """Try to find SEC filings for a facility's parent company."""
        if self._dry_run:
            return self._mock_profile("CHEM")

        try:
            from edgar import find
            results = find(parent_company)
            if results:
                ticker = results[0].ticker or ""
                if ticker:
                    return await self.search_company(ticker)
        except Exception as e:
            logger.warning("Could not find SEC filings for %s: %s", parent_company, e)

        return None

    def _extract_disclosures(
        self, text: str, company: str, ticker: str,
        form: str, filing_date: str,
    ) -> list[EnvironmentalDisclosure]:
        """Extract environmental disclosures from filing text."""
        disclosures = []
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            if len(para) < 50:
                continue

            matches = sum(1 for kw in self._compiled_keywords if kw.search(para))
            if matches < 2:
                continue

            disclosure_type = "general"
            for dtype, pattern in DISCLOSURE_TYPE_PATTERNS.items():
                if pattern.search(para):
                    disclosure_type = dtype
                    break

            dollar_amount = 0.0
            dollar_match = DOLLAR_PATTERN.search(para)
            if dollar_match:
                amount_str = dollar_match.group(1).replace(",", "")
                multiplier_str = (dollar_match.group(2) or "").lower()
                dollar_amount = float(amount_str)
                if "billion" in multiplier_str:
                    dollar_amount *= 1_000_000_000
                elif "million" in multiplier_str:
                    dollar_amount *= 1_000_000
                elif "thousand" in multiplier_str:
                    dollar_amount *= 1_000

            severity = "low"
            if dollar_amount >= 100_000_000:
                severity = "critical"
            elif dollar_amount >= 10_000_000:
                severity = "high"
            elif dollar_amount >= 1_000_000:
                severity = "medium"
            elif disclosure_type in ("consent_decree", "superfund"):
                severity = "high"

            disclosures.append(EnvironmentalDisclosure(
                company=company,
                ticker=ticker,
                filing_type=form,
                filing_date=filing_date,
                section="",
                excerpt=para[:300].strip(),
                disclosure_type=disclosure_type,
                dollar_amount=dollar_amount,
                severity=severity,
            ))

        return disclosures

    def _compute_aggregates(self, profile: CorporateEnvironmentalProfile) -> None:
        """Compute aggregate metrics from disclosures."""
        for d in profile.disclosures:
            if d.disclosure_type == "remediation":
                profile.total_remediation_reserves += d.dollar_amount
            elif d.disclosure_type == "consent_decree":
                profile.active_consent_decrees += 1
            elif d.disclosure_type == "superfund":
                profile.superfund_sites += 1
            elif d.disclosure_type == "litigation":
                profile.pending_litigation += 1
            elif d.disclosure_type == "penalty":
                profile.epa_penalties_disclosed += d.dollar_amount

    def _mock_profile(self, ticker: str) -> CorporateEnvironmentalProfile:
        return CorporateEnvironmentalProfile(
            company="National Chemical Holdings Inc",
            ticker=ticker,
            cik="0001234567",
            disclosures=[
                EnvironmentalDisclosure(
                    company="National Chemical Holdings Inc",
                    ticker=ticker,
                    filing_type="10-K",
                    filing_date="2025-12-15",
                    section="Environmental Matters",
                    excerpt=(
                        "The Company has established environmental remediation reserves "
                        "of approximately $4.2 million related to groundwater contamination "
                        "at our Springfield, Illinois facility. Remediation activities are "
                        "expected to continue for approximately 8-12 years."
                    ),
                    disclosure_type="remediation",
                    dollar_amount=4_200_000,
                    facilities_mentioned=["Springfield, Illinois"],
                    chemicals_mentioned=["groundwater contamination"],
                    severity="medium",
                ),
                EnvironmentalDisclosure(
                    company="National Chemical Holdings Inc",
                    ticker=ticker,
                    filing_type="10-K",
                    filing_date="2025-12-15",
                    section="Legal Proceedings",
                    excerpt=(
                        "In March 2025, the Company entered into a consent decree with the "
                        "U.S. EPA regarding alleged Clean Air Act violations at the Springfield "
                        "facility. Under the terms of the decree, the Company will install "
                        "additional emission controls and pay a civil penalty of $1.8 million."
                    ),
                    disclosure_type="consent_decree",
                    dollar_amount=1_800_000,
                    regulatory_actions=["consent decree", "Clean Air Act"],
                    severity="high",
                ),
                EnvironmentalDisclosure(
                    company="National Chemical Holdings Inc",
                    ticker=ticker,
                    filing_type="10-Q",
                    filing_date="2026-03-10",
                    section="Environmental Matters",
                    excerpt=(
                        "The Company is currently named as a potentially responsible party "
                        "at two Superfund sites in connection with historical waste disposal "
                        "activities. Management estimates the Company's share of remediation "
                        "costs at these sites to be between $8 million and $12 million."
                    ),
                    disclosure_type="superfund",
                    dollar_amount=10_000_000,
                    severity="high",
                ),
            ],
            total_remediation_reserves=4_200_000,
            active_consent_decrees=1,
            superfund_sites=2,
            pending_litigation=0,
            epa_penalties_disclosed=1_800_000,
        )
