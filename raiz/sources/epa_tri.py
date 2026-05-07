"""EPA TRI — Toxic Release Inventory.

Every pound of toxic chemicals released into air, water, or land
by facilities that meet reporting thresholds. Self-reported annually.

API: https://enviro.epa.gov/enviro/efservice/
No API key required.

This is where you learn that the plant next door released
47,000 pounds of toluene into the air last year, and nobody told you.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

TRI_BASE = "https://enviro.epa.gov/enviro/efservice"


@dataclass
class ToxicRelease:
    """A single toxic release report from TRI."""
    facility_name: str
    facility_id: str
    chemical: str
    year: int
    city: str
    state: str
    zip_code: str
    latitude: float = 0.0
    longitude: float = 0.0
    fugitive_air_lbs: float = 0.0
    stack_air_lbs: float = 0.0
    water_lbs: float = 0.0
    land_lbs: float = 0.0
    total_releases_lbs: float = 0.0
    carcinogen: bool = False
    parent_company: str = ""
    industry: str = ""

    @property
    def total_air_lbs(self) -> float:
        return self.fugitive_air_lbs + self.stack_air_lbs


@dataclass
class CommunityToxicProfile:
    """Toxic release summary for a community."""
    zip_code: str
    releases: list[ToxicRelease]
    total_air_lbs: float = 0.0
    total_water_lbs: float = 0.0
    total_land_lbs: float = 0.0
    unique_chemicals: int = 0
    carcinogen_count: int = 0
    top_polluters: list[dict[str, Any]] = field(default_factory=list)

    def summarize(self) -> str:
        if not self.releases:
            return f"No TRI-reported releases found for zip code {self.zip_code}."

        parts = [f"Toxic Release Inventory for {self.zip_code}:"]
        parts.append(f"  {len(self.releases)} release reports from {len(self.top_polluters)} facilities")
        parts.append(f"  Total air releases: {self.total_air_lbs:,.0f} lbs")
        parts.append(f"  Total water releases: {self.total_water_lbs:,.0f} lbs")
        parts.append(f"  {self.unique_chemicals} different chemicals, {self.carcinogen_count} known carcinogens")

        if self.top_polluters:
            parts.append("  Top polluters:")
            for p in self.top_polluters[:5]:
                parts.append(f"    - {p['name']}: {p['total_lbs']:,.0f} lbs")

        return "\n".join(parts)


class TriSource:
    """Query EPA Toxic Release Inventory."""

    KNOWN_CARCINOGENS = {
        "benzene", "formaldehyde", "vinyl chloride", "asbestos",
        "chromium compounds", "arsenic compounds", "cadmium compounds",
        "nickel compounds", "lead compounds", "ethylene oxide",
        "1,3-butadiene", "trichloroethylene", "perchloroethylene",
        "polycyclic aromatic compounds",
    }

    def __init__(self, dry_run: bool = False) -> None:
        self._dry_run = dry_run

    async def releases_by_zip(self, zip_code: str, year: int = 2023) -> list[ToxicRelease]:
        if self._dry_run:
            return self._mock_releases(zip_code, year)

        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required")
            return []

        url = (
            f"{TRI_BASE}/tri_facility/zip_code/=/{zip_code}"
            f"/reporting_year/=/{year}/JSON"
        )

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as resp:
                    data = await resp.json()

            releases = []
            for row in data if isinstance(data, list) else []:
                chemical = row.get("CHEMICAL_NAME", "").lower()
                releases.append(ToxicRelease(
                    facility_name=row.get("FACILITY_NAME", ""),
                    facility_id=row.get("TRI_FACILITY_ID", ""),
                    chemical=row.get("CHEMICAL_NAME", ""),
                    year=int(row.get("REPORTING_YEAR", year)),
                    city=row.get("CITY_NAME", ""),
                    state=row.get("STATE_ABBR", ""),
                    zip_code=zip_code,
                    latitude=float(row.get("LATITUDE", 0) or 0),
                    longitude=float(row.get("LONGITUDE", 0) or 0),
                    fugitive_air_lbs=float(row.get("FUGITIVE_AIR", 0) or 0),
                    stack_air_lbs=float(row.get("STACK_AIR", 0) or 0),
                    water_lbs=float(row.get("WATER", 0) or 0),
                    land_lbs=float(row.get("LAND_TREATMENT", 0) or 0),
                    total_releases_lbs=float(row.get("TOTAL_RELEASES", 0) or 0),
                    carcinogen=any(c in chemical for c in self.KNOWN_CARCINOGENS),
                    parent_company=row.get("PARENT_CO_NAME", ""),
                    industry=row.get("INDUSTRY_SECTOR", ""),
                ))
            return releases
        except Exception as e:
            logger.error("TRI query failed: %s", e)
            return []

    async def community_profile(self, zip_code: str, year: int = 2023) -> CommunityToxicProfile:
        releases = await self.releases_by_zip(zip_code, year)

        facility_totals: dict[str, float] = {}
        chemicals: set[str] = set()
        carcinogens = 0

        for r in releases:
            facility_totals[r.facility_name] = (
                facility_totals.get(r.facility_name, 0) + r.total_releases_lbs
            )
            chemicals.add(r.chemical)
            if r.carcinogen:
                carcinogens += 1

        top = sorted(facility_totals.items(), key=lambda x: -x[1])
        top_polluters = [{"name": n, "total_lbs": t} for n, t in top[:10]]

        return CommunityToxicProfile(
            zip_code=zip_code,
            releases=releases,
            total_air_lbs=sum(r.total_air_lbs for r in releases),
            total_water_lbs=sum(r.water_lbs for r in releases),
            total_land_lbs=sum(r.land_lbs for r in releases),
            unique_chemicals=len(chemicals),
            carcinogen_count=carcinogens,
            top_polluters=top_polluters,
        )

    def _mock_releases(self, zip_code: str, year: int) -> list[ToxicRelease]:
        return [
            ToxicRelease(
                facility_name="Springfield Chemical Corp",
                facility_id="62701SPRNG400IN",
                chemical="Toluene",
                year=year, city="Springfield", state="IL",
                zip_code=zip_code, latitude=39.78, longitude=-89.65,
                fugitive_air_lbs=12000, stack_air_lbs=35000,
                water_lbs=500, total_releases_lbs=47500,
                parent_company="National Chemical Holdings Inc",
                industry="Chemical Manufacturing",
            ),
            ToxicRelease(
                facility_name="Springfield Chemical Corp",
                facility_id="62701SPRNG400IN",
                chemical="Benzene",
                year=year, city="Springfield", state="IL",
                zip_code=zip_code, latitude=39.78, longitude=-89.65,
                fugitive_air_lbs=800, stack_air_lbs=2200,
                total_releases_lbs=3000, carcinogen=True,
                parent_company="National Chemical Holdings Inc",
                industry="Chemical Manufacturing",
            ),
        ]
