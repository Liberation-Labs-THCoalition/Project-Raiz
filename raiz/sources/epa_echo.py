"""EPA ECHO — Enforcement and Compliance History Online.

The backbone of environmental enforcement data. Every facility
regulated under the Clean Air Act, Clean Water Act, or RCRA.
Every inspection, violation, and enforcement action.

API docs: https://echo.epa.gov/tools/web-services
No API key required. Rate limit: be reasonable.

This is where you find out that the plant upwind of the school
has had 47 violations in the last 3 years and zero penalties.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

ECHO_BASE = "https://echodata.epa.gov/echo"


@dataclass
class Facility:
    """An EPA-regulated facility."""
    registry_id: str
    name: str
    street: str
    city: str
    state: str
    zip_code: str
    latitude: float = 0.0
    longitude: float = 0.0
    programs: list[str] = field(default_factory=list)
    naics_codes: list[str] = field(default_factory=list)
    sic_codes: list[str] = field(default_factory=list)
    parent_company: str = ""


@dataclass
class Violation:
    """A compliance violation."""
    facility_id: str
    program: str
    violation_type: str
    violation_date: str
    compliance_status: str
    pollutant: str = ""
    severity: str = ""
    resolved: bool = False
    resolution_date: str = ""


@dataclass
class Enforcement:
    """An enforcement action taken against a facility."""
    facility_id: str
    action_type: str
    action_date: str
    penalty_amount: float = 0.0
    complying_action: str = ""
    federal_or_state: str = ""


@dataclass
class EchoReport:
    """Complete ECHO report for a geographic area."""
    query: str
    timestamp: datetime
    facilities: list[Facility]
    violations: list[Violation]
    enforcements: list[Enforcement]
    total_facilities: int = 0
    facilities_in_violation: int = 0
    total_violations_3yr: int = 0
    total_penalties_3yr: float = 0.0


class EchoSource:
    """Query EPA ECHO for facility compliance data.

    Supports queries by:
    - Zip code
    - City/state
    - Latitude/longitude + radius
    - Facility registry ID
    """

    def __init__(self, dry_run: bool = False) -> None:
        self._dry_run = dry_run

    async def facilities_by_zip(self, zip_code: str, **kwargs) -> list[Facility]:
        params = {"p_zip": zip_code, "output": "JSON", **kwargs}
        return await self._query_facilities(params)

    async def facilities_by_location(
        self, lat: float, lon: float, radius_miles: float = 3.0, **kwargs,
    ) -> list[Facility]:
        params = {
            "p_lat": lat, "p_long": lon,
            "p_radius": radius_miles,
            "output": "JSON", **kwargs,
        }
        return await self._query_facilities(params)

    async def facilities_by_state(self, state: str, **kwargs) -> list[Facility]:
        params = {"p_st": state, "output": "JSON", **kwargs}
        return await self._query_facilities(params)

    async def violations_for_facility(self, registry_id: str) -> list[Violation]:
        if self._dry_run:
            return self._mock_violations(registry_id)

        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required — pip install aiohttp")
            return []

        url = f"{ECHO_BASE}/cwa_rest_services.get_qid"
        params = {"p_id": registry_id, "output": "JSON"}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()

            violations = []
            for row in data.get("Results", {}).get("Violations", []):
                violations.append(Violation(
                    facility_id=registry_id,
                    program=row.get("ProgramArea", ""),
                    violation_type=row.get("ViolationType", ""),
                    violation_date=row.get("ViolationDate", ""),
                    compliance_status=row.get("ComplianceStatus", ""),
                    pollutant=row.get("Pollutant", ""),
                    severity=row.get("Severity", ""),
                ))
            return violations
        except Exception as e:
            logger.error("ECHO violation query failed: %s", e)
            return []

    async def community_report(self, zip_code: str) -> EchoReport:
        """Generate a complete ECHO report for a zip code."""
        facilities = await self.facilities_by_zip(zip_code)

        all_violations: list[Violation] = []
        all_enforcements: list[Enforcement] = []
        in_violation = 0

        for f in facilities[:50]:
            violations = await self.violations_for_facility(f.registry_id)
            if violations:
                in_violation += 1
                all_violations.extend(violations)

        total_penalties = sum(e.penalty_amount for e in all_enforcements)

        return EchoReport(
            query=f"zip:{zip_code}",
            timestamp=datetime.now(timezone.utc),
            facilities=facilities,
            violations=all_violations,
            enforcements=all_enforcements,
            total_facilities=len(facilities),
            facilities_in_violation=in_violation,
            total_violations_3yr=len(all_violations),
            total_penalties_3yr=total_penalties,
        )

    async def _query_facilities(self, params: dict) -> list[Facility]:
        if self._dry_run:
            return self._mock_facilities()

        try:
            import aiohttp
        except ImportError:
            logger.error("aiohttp required — pip install aiohttp")
            return []

        url = f"{ECHO_BASE}/echo_rest_services.get_facilities"

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    data = await resp.json()

            facilities = []
            for row in data.get("Results", {}).get("Facilities", []):
                facilities.append(Facility(
                    registry_id=row.get("RegistryId", row.get("FacilityId", "")),
                    name=row.get("FacilityName", ""),
                    street=row.get("Street", ""),
                    city=row.get("City", ""),
                    state=row.get("State", ""),
                    zip_code=row.get("Zip", ""),
                    latitude=float(row.get("Latitude", 0) or 0),
                    longitude=float(row.get("Longitude", 0) or 0),
                    programs=row.get("Programs", "").split(",") if row.get("Programs") else [],
                    parent_company=row.get("ParentCompany", ""),
                ))
            return facilities
        except Exception as e:
            logger.error("ECHO facility query failed: %s", e)
            return []

    def _mock_facilities(self) -> list[Facility]:
        return [
            Facility(
                registry_id="110000000001",
                name="Springfield Chemical Corp",
                street="400 Industrial Blvd",
                city="Springfield", state="IL", zip_code="62701",
                latitude=39.78, longitude=-89.65,
                programs=["CAA", "CWA", "RCRA"],
                parent_company="National Chemical Holdings Inc",
            ),
            Facility(
                registry_id="110000000002",
                name="Metro Waste Processing",
                street="1200 River Road",
                city="Springfield", state="IL", zip_code="62701",
                latitude=39.77, longitude=-89.64,
                programs=["RCRA"],
            ),
        ]

    def _mock_violations(self, registry_id: str) -> list[Violation]:
        return [
            Violation(
                facility_id=registry_id,
                program="CAA",
                violation_type="Emissions Exceedance",
                violation_date="2025-11-15",
                compliance_status="In Violation",
                pollutant="Particulate Matter (PM2.5)",
                severity="High Priority",
            ),
            Violation(
                facility_id=registry_id,
                program="CWA",
                violation_type="Effluent Limit Exceedance",
                violation_date="2026-01-20",
                compliance_status="In Violation",
                pollutant="Mercury",
                severity="Significant",
            ),
        ]
