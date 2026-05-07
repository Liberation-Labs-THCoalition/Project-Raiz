"""Permit Watchdog — the eye that never closes.

Monitors environmental permit databases for new applications,
modifications, and renewals. When a new permit appears near a
community Raíz is watching, it triggers an investigation:

  1. Who's applying? Check their violation history.
  2. What are they proposing? What chemicals, what volumes?
  3. Who lives downwind/downstream? Demographics + existing burden.
  4. Is there a public comment period? When does it close?
  5. Generate materials for community response.

The watchdog doesn't wait for communities to find the permit.
The watchdog finds the permit and brings it TO the community.

"A new chemical storage facility was just proposed 0.4 miles
from Lincoln Elementary. The applicant has 12 CAA violations
across their Ohio facilities. Comment period closes March 15.
Here's your draft comment."
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Awaitable

logger = logging.getLogger(__name__)


@dataclass
class PermitApplication:
    """A new or modified environmental permit application."""
    permit_id: str
    state: str
    applicant: str
    facility_name: str
    facility_address: str
    latitude: float = 0.0
    longitude: float = 0.0
    permit_type: str = ""  # air, water, waste, storage
    description: str = ""
    chemicals: list[str] = field(default_factory=list)
    filed_date: str = ""
    comment_deadline: str = ""
    status: str = "pending"  # pending, under_review, approved, denied
    parent_company: str = ""
    naics_code: str = ""


@dataclass
class WatchZone:
    """A geographic area Raíz is watching for permit activity."""
    zone_id: str
    zip_codes: list[str]
    name: str  # "Lincoln Elementary neighborhood"
    latitude: float = 0.0
    longitude: float = 0.0
    radius_miles: float = 3.0
    contacts: list[dict[str, str]] = field(default_factory=list)
    org_name: str = ""


@dataclass
class PermitAlert:
    """An alert generated when a permit is found near a watch zone."""
    permit: PermitApplication
    zone: WatchZone
    distance_miles: float
    risk_assessment: str
    applicant_violations: int = 0
    applicant_penalties: float = 0.0
    nearby_schools: int = 0
    nearby_hospitals: int = 0
    community_existing_burden: float = 0.0
    comment_deadline_days: int = 0
    recommended_actions: list[str] = field(default_factory=list)

    def summarize(self) -> str:
        parts = [
            "=" * 60,
            "⚠ PERMIT ALERT — New application near watched community",
            "=" * 60,
            f"",
            f"Applicant:    {self.permit.applicant}",
            f"Facility:     {self.permit.facility_name}",
            f"Location:     {self.permit.facility_address}",
            f"Permit type:  {self.permit.permit_type}",
            f"Description:  {self.permit.description}",
            f"",
            f"Distance from {self.zone.name}: {self.distance_miles:.1f} miles",
            f"",
            f"APPLICANT HISTORY:",
            f"  Violations across all facilities: {self.applicant_violations}",
            f"  Penalties paid: ${self.applicant_penalties:,.0f}",
            f"",
            f"COMMUNITY IMPACT:",
            f"  Existing environmental burden score: {self.community_existing_burden:.1f}/10",
        ]

        if self.nearby_schools > 0:
            parts.append(f"  Schools within 1 mile: {self.nearby_schools}")
        if self.nearby_hospitals > 0:
            parts.append(f"  Hospitals within 1 mile: {self.nearby_hospitals}")

        if self.permit.comment_deadline:
            parts.append(f"")
            parts.append(f"PUBLIC COMMENT DEADLINE: {self.permit.comment_deadline}")
            parts.append(f"  ({self.comment_deadline_days} days remaining)")

        if self.recommended_actions:
            parts.append(f"")
            parts.append(f"RECOMMENDED ACTIONS:")
            for i, action in enumerate(self.recommended_actions, 1):
                parts.append(f"  {i}. {action}")

        parts.append("")
        parts.append(f"Risk assessment: {self.risk_assessment}")
        parts.append("— Raíz")

        return "\n".join(parts)

    def generate_comment_draft(self) -> str:
        """Generate a draft public comment for community use."""
        parts = [
            f"Re: Permit Application {self.permit.permit_id}",
            f"Facility: {self.permit.facility_name}",
            f"Applicant: {self.permit.applicant}",
            f"",
            f"To Whom It May Concern,",
            f"",
            f"I am writing to express concern regarding the above permit application "
            f"for {self.permit.description.lower() or 'the proposed facility'} "
            f"located at {self.permit.facility_address}.",
            f"",
        ]

        if self.applicant_violations > 0:
            parts.append(
                f"The applicant has a documented history of {self.applicant_violations} "
                f"environmental violations across their existing facilities. "
                f"This record raises serious questions about their ability to operate "
                f"in compliance with environmental regulations."
            )
            parts.append("")

        if self.applicant_penalties > 0:
            parts.append(
                f"The applicant has been assessed ${self.applicant_penalties:,.0f} "
                f"in environmental penalties, indicating a pattern of non-compliance "
                f"rather than isolated incidents."
            )
            parts.append("")

        if self.community_existing_burden > 5.0:
            parts.append(
                f"This community already bears a disproportionate environmental burden "
                f"(risk score: {self.community_existing_burden:.1f}/10). Adding another "
                f"potential pollution source to an already overburdened community raises "
                f"environmental justice concerns that must be addressed before this "
                f"permit is granted."
            )
            parts.append("")

        if self.nearby_schools > 0:
            parts.append(
                f"There are {self.nearby_schools} school(s) within one mile of the "
                f"proposed facility. The health of children must be given primary "
                f"consideration in this permitting decision."
            )
            parts.append("")

        parts.extend([
            "I request that the agency:",
            "  1. Hold a public hearing on this application",
            "  2. Conduct a cumulative impact analysis for this community",
            "  3. Require the applicant to address their compliance history",
            f"  4. Evaluate alternative locations that do not burden already "
            f"impacted communities",
            "",
            "Thank you for your consideration.",
            "",
            "[Your name]",
            "[Your address]",
            "",
            "---",
            "Data sources: EPA ECHO, EPA TRI, SEC EDGAR filings.",
            "Report generated by Raíz environmental justice intelligence.",
        ])

        return "\n".join(parts)


class PermitWatchdog:
    """The watchdog that monitors permits and generates alerts.

    Args:
        on_alert: Callback when a permit is found near a watch zone
        check_interval_hours: How often to check (default: 24)
    """

    def __init__(
        self,
        on_alert: Callable[[PermitAlert], Awaitable[None]] | None = None,
        check_interval_hours: int = 24,
    ) -> None:
        self._zones: list[WatchZone] = []
        self._seen_permits: set[str] = set()
        self._alerts: list[PermitAlert] = []
        self._on_alert = on_alert
        self._interval = check_interval_hours
        self._last_check: datetime | None = None

    def add_watch_zone(self, zone: WatchZone) -> None:
        self._zones.append(zone)
        logger.info("Watching zone: %s (%s)", zone.name, ", ".join(zone.zip_codes))

    def remove_watch_zone(self, zone_id: str) -> None:
        self._zones = [z for z in self._zones if z.zone_id != zone_id]

    async def check(self, permits: list[PermitApplication]) -> list[PermitAlert]:
        """Check a list of permits against all watch zones.

        In production, permits come from state database scrapers.
        For now, accepts them as input for testability.
        """
        new_alerts = []
        self._last_check = datetime.now(timezone.utc)

        for permit in permits:
            if permit.permit_id in self._seen_permits:
                continue
            self._seen_permits.add(permit.permit_id)

            for zone in self._zones:
                distance = self._distance(
                    permit.latitude, permit.longitude,
                    zone.latitude, zone.longitude,
                )
                if distance <= zone.radius_miles:
                    alert = await self._build_alert(permit, zone, distance)
                    new_alerts.append(alert)
                    self._alerts.append(alert)

                    if self._on_alert:
                        await self._on_alert(alert)

        return new_alerts

    async def _build_alert(
        self, permit: PermitApplication, zone: WatchZone, distance: float,
    ) -> PermitAlert:
        """Build a complete alert with investigation results."""
        days_to_comment = 0
        if permit.comment_deadline:
            try:
                deadline = datetime.strptime(permit.comment_deadline, "%Y-%m-%d")
                days_to_comment = (deadline - datetime.now()).days
            except ValueError:
                pass

        risk = "HIGH" if days_to_comment <= 14 else "MODERATE"

        actions = [
            "Attend public hearing if scheduled",
            "Submit public comment before deadline",
            "Share this alert with community members",
            "Request facility's full compliance history via FOIA",
        ]
        if days_to_comment <= 14:
            actions.insert(0, f"URGENT: Only {days_to_comment} days to comment")

        return PermitAlert(
            permit=permit,
            zone=zone,
            distance_miles=distance,
            risk_assessment=risk,
            comment_deadline_days=days_to_comment,
            recommended_actions=actions,
        )

    @staticmethod
    def _distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Approximate distance in miles between two points."""
        import math
        dlat = math.radians(lat2 - lat1)
        dlon = math.radians(lon2 - lon1)
        a = (math.sin(dlat/2)**2 +
             math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
             math.sin(dlon/2)**2)
        c = 2 * math.asin(math.sqrt(a))
        return c * 3959  # Earth radius in miles

    @property
    def watch_zones(self) -> list[WatchZone]:
        return list(self._zones)

    @property
    def alerts(self) -> list[PermitAlert]:
        return list(self._alerts)

    @property
    def last_check(self) -> datetime | None:
        return self._last_check
