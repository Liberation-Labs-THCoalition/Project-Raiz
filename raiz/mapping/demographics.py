"""Demographics — naming the injustice with numbers.

Without demographics, Raíz reports chemistry.
With demographics, Raíz reports environmental racism.

"This community is 78% Black, median income $28,000.
The community 4 miles away is 89% white, median income $72,000.
The Black community has 47 violations and 50,000 lbs of toxic air.
The white community has zero."

Data source: US Census Bureau American Community Survey (ACS).
Free, public, no API key for basic data.
Census API key available free at api.census.gov/data/key_signup.html

Available at zip code and census tract granularity.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

CENSUS_BASE = "https://api.census.gov/data"


@dataclass
class CommunityDemographics:
    """Demographic profile of a community."""
    zip_code: str
    total_population: int = 0

    # Race/ethnicity (percentages)
    pct_white: float = 0.0
    pct_black: float = 0.0
    pct_hispanic: float = 0.0
    pct_asian: float = 0.0
    pct_indigenous: float = 0.0
    pct_other: float = 0.0

    # Economics
    median_household_income: float = 0.0
    pct_below_poverty: float = 0.0
    pct_unemployed: float = 0.0

    # Vulnerability
    pct_under_5: float = 0.0
    pct_over_65: float = 0.0
    pct_no_health_insurance: float = 0.0
    pct_limited_english: float = 0.0
    pct_disability: float = 0.0

    # Housing
    pct_renter_occupied: float = 0.0
    pct_mobile_homes: float = 0.0

    @property
    def majority_minority(self) -> bool:
        return self.pct_white < 50.0

    @property
    def low_income(self) -> bool:
        return self.median_household_income < 40000 or self.pct_below_poverty > 20

    @property
    def vulnerable_population_pct(self) -> float:
        return self.pct_under_5 + self.pct_over_65

    @property
    def ej_indicators(self) -> list[str]:
        """Environmental justice indicators present in this community."""
        indicators = []
        if self.majority_minority:
            indicators.append("Majority-minority community")
        if self.low_income:
            indicators.append("Low-income community")
        if self.pct_below_poverty > 25:
            indicators.append(f"High poverty rate ({self.pct_below_poverty:.0f}%)")
        if self.pct_no_health_insurance > 15:
            indicators.append(f"Low health insurance coverage ({self.pct_no_health_insurance:.0f}% uninsured)")
        if self.pct_under_5 > 8:
            indicators.append(f"High child population ({self.pct_under_5:.0f}% under 5)")
        if self.pct_over_65 > 20:
            indicators.append(f"High elderly population ({self.pct_over_65:.0f}% over 65)")
        if self.pct_limited_english > 10:
            indicators.append(f"Limited English proficiency ({self.pct_limited_english:.0f}%)")
        return indicators

    def summarize(self) -> str:
        parts = [f"Community Demographics for {self.zip_code}:"]
        parts.append(f"  Population: {self.total_population:,}")
        parts.append(f"  Race/Ethnicity:")
        parts.append(f"    White: {self.pct_white:.0f}%  |  Black: {self.pct_black:.0f}%  |  Hispanic: {self.pct_hispanic:.0f}%")
        parts.append(f"    Asian: {self.pct_asian:.0f}%  |  Indigenous: {self.pct_indigenous:.0f}%  |  Other: {self.pct_other:.0f}%")
        parts.append(f"  Median household income: ${self.median_household_income:,.0f}")
        parts.append(f"  Below poverty line: {self.pct_below_poverty:.0f}%")
        parts.append(f"  Children under 5: {self.pct_under_5:.0f}%  |  Adults over 65: {self.pct_over_65:.0f}%")
        parts.append(f"  Without health insurance: {self.pct_no_health_insurance:.0f}%")

        indicators = self.ej_indicators
        if indicators:
            parts.append(f"\n  ENVIRONMENTAL JUSTICE INDICATORS:")
            for ind in indicators:
                parts.append(f"    ▸ {ind}")

        return "\n".join(parts)


@dataclass
class DisparityAnalysis:
    """Compares environmental burden between two communities."""
    community_a: CommunityDemographics
    community_b: CommunityDemographics
    burden_a: dict[str, float] = field(default_factory=dict)
    burden_b: dict[str, float] = field(default_factory=dict)

    def summarize(self) -> str:
        a = self.community_a
        b = self.community_b
        parts = [
            "ENVIRONMENTAL JUSTICE DISPARITY ANALYSIS",
            "=" * 60,
            "",
            f"Community A: {a.zip_code}",
            f"  {a.pct_black + a.pct_hispanic + a.pct_indigenous:.0f}% people of color | "
            f"Median income: ${a.median_household_income:,.0f}",
            f"",
            f"Community B: {b.zip_code}",
            f"  {b.pct_black + b.pct_hispanic + b.pct_indigenous:.0f}% people of color | "
            f"Median income: ${b.median_household_income:,.0f}",
            "",
        ]

        if self.burden_a and self.burden_b:
            parts.append("Environmental Burden Comparison:")
            for key in self.burden_a:
                val_a = self.burden_a[key]
                val_b = self.burden_b.get(key, 0)
                if val_a > 0 or val_b > 0:
                    ratio = val_a / val_b if val_b > 0 else float('inf')
                    marker = " ◀ DISPARITY" if ratio > 2.0 else ""
                    parts.append(
                        f"  {key:30s}: A={val_a:>10,.0f}  B={val_b:>10,.0f}  "
                        f"ratio={ratio:.1f}x{marker}"
                    )

        poc_a = a.pct_black + a.pct_hispanic + a.pct_indigenous
        poc_b = b.pct_black + b.pct_hispanic + b.pct_indigenous
        total_burden_a = sum(self.burden_a.values())
        total_burden_b = sum(self.burden_b.values())

        if poc_a > poc_b and total_burden_a > total_burden_b:
            parts.append("")
            parts.append(
                f"FINDING: The community with {poc_a:.0f}% people of color bears "
                f"{total_burden_a / max(total_burden_b, 1):.1f}x the environmental burden "
                f"of the community with {poc_b:.0f}% people of color."
            )
            parts.append("This pattern is consistent with environmental racism.")

        return "\n".join(parts)


class CensusSource:
    """Query US Census American Community Survey data.

    Uses the Census Bureau API. Free API key recommended but not
    required for low-volume queries.
    """

    ACS_YEAR = "2022"
    ACS_DATASET = "acs/acs5"

    # ACS variable codes
    VARIABLES = {
        "total_pop": "B01003_001E",
        "white_alone": "B02001_002E",
        "black_alone": "B02001_003E",
        "indigenous_alone": "B02001_004E",
        "asian_alone": "B02001_005E",
        "hispanic": "B03003_003E",
        "median_income": "B19013_001E",
        "poverty_pop": "B17001_002E",
        "under_5": "B01001_003E",
        "over_65_male": "B01001_020E",
        "over_65_female": "B01001_044E",
        "no_insurance": "B27010_017E",
        "limited_english": "B16005_007E",
    }

    def __init__(self, api_key: str = "", dry_run: bool = False) -> None:
        self._api_key = api_key
        self._dry_run = dry_run

    async def get_demographics(self, zip_code: str) -> CommunityDemographics:
        if self._dry_run:
            return self._mock_demographics(zip_code)

        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required")
            return CommunityDemographics(zip_code=zip_code)

        variables = ",".join(self.VARIABLES.values())
        url = (
            f"{CENSUS_BASE}/{self.ACS_YEAR}/{self.ACS_DATASET}"
            f"?get={variables}&for=zip%20code%20tabulation%20area:{zip_code}"
        )
        if self._api_key:
            url += f"&key={self._api_key}"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()

            if len(data) < 2:
                return CommunityDemographics(zip_code=zip_code)

            headers = data[0]
            values = data[1]
            row = dict(zip(headers, values))

            total_pop = int(row.get(self.VARIABLES["total_pop"], 0) or 0)
            if total_pop == 0:
                return CommunityDemographics(zip_code=zip_code)

            white = int(row.get(self.VARIABLES["white_alone"], 0) or 0)
            black = int(row.get(self.VARIABLES["black_alone"], 0) or 0)
            indigenous = int(row.get(self.VARIABLES["indigenous_alone"], 0) or 0)
            asian = int(row.get(self.VARIABLES["asian_alone"], 0) or 0)
            hispanic = int(row.get(self.VARIABLES["hispanic"], 0) or 0)

            return CommunityDemographics(
                zip_code=zip_code,
                total_population=total_pop,
                pct_white=white / total_pop * 100,
                pct_black=black / total_pop * 100,
                pct_hispanic=hispanic / total_pop * 100,
                pct_asian=asian / total_pop * 100,
                pct_indigenous=indigenous / total_pop * 100,
                pct_other=max(0, (total_pop - white - black - asian - indigenous) / total_pop * 100),
                median_household_income=float(row.get(self.VARIABLES["median_income"], 0) or 0),
                pct_below_poverty=int(row.get(self.VARIABLES["poverty_pop"], 0) or 0) / total_pop * 100,
                pct_under_5=int(row.get(self.VARIABLES["under_5"], 0) or 0) / total_pop * 100,
                pct_over_65=(
                    int(row.get(self.VARIABLES["over_65_male"], 0) or 0) +
                    int(row.get(self.VARIABLES["over_65_female"], 0) or 0)
                ) / total_pop * 100,
                pct_no_health_insurance=int(row.get(self.VARIABLES["no_insurance"], 0) or 0) / total_pop * 100,
                pct_limited_english=int(row.get(self.VARIABLES["limited_english"], 0) or 0) / total_pop * 100,
            )
        except Exception as e:
            logger.error("Census API query failed: %s", e)
            return CommunityDemographics(zip_code=zip_code)

    async def disparity_analysis(
        self,
        zip_a: str, zip_b: str,
        burden_a: dict[str, float] | None = None,
        burden_b: dict[str, float] | None = None,
    ) -> DisparityAnalysis:
        demo_a = await self.get_demographics(zip_a)
        demo_b = await self.get_demographics(zip_b)
        return DisparityAnalysis(
            community_a=demo_a,
            community_b=demo_b,
            burden_a=burden_a or {},
            burden_b=burden_b or {},
        )

    def _mock_demographics(self, zip_code: str) -> CommunityDemographics:
        if zip_code == "62701":
            return CommunityDemographics(
                zip_code="62701",
                total_population=14200,
                pct_white=22.0, pct_black=61.0, pct_hispanic=12.0,
                pct_asian=2.0, pct_indigenous=1.0, pct_other=2.0,
                median_household_income=28400,
                pct_below_poverty=34.0, pct_unemployed=12.0,
                pct_under_5=9.0, pct_over_65=16.0,
                pct_no_health_insurance=18.0,
                pct_limited_english=8.0,
                pct_renter_occupied=72.0,
            )
        else:
            return CommunityDemographics(
                zip_code=zip_code,
                total_population=22800,
                pct_white=82.0, pct_black=5.0, pct_hispanic=6.0,
                pct_asian=4.0, pct_indigenous=0.5, pct_other=2.5,
                median_household_income=78500,
                pct_below_poverty=6.0, pct_unemployed=3.0,
                pct_under_5=6.0, pct_over_65=14.0,
                pct_no_health_insurance=4.0,
                pct_limited_english=3.0,
                pct_renter_occupied=28.0,
            )
