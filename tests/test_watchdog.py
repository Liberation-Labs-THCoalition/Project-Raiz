"""Tests for the permit watchdog and SEC integration."""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from raiz.sources.sec_edgar import SecEdgarSource, EnvironmentalDisclosure
from raiz.pulse.watchdog import (
    PermitWatchdog, PermitApplication, WatchZone, PermitAlert,
)


@pytest.mark.asyncio
class TestSecEdgar:
    async def test_search_company(self):
        source = SecEdgarSource(dry_run=True)
        profile = await source.search_company("CHEM")
        assert profile.company == "National Chemical Holdings Inc"
        assert profile.total_remediation_reserves > 0
        assert profile.active_consent_decrees > 0
        assert profile.superfund_sites > 0

    async def test_disclosure_severity(self):
        source = SecEdgarSource(dry_run=True)
        profile = await source.search_company("CHEM")
        high_severity = [d for d in profile.disclosures if d.severity in ("high", "critical")]
        assert len(high_severity) > 0

    async def test_profile_summary(self):
        source = SecEdgarSource(dry_run=True)
        profile = await source.search_company("CHEM")
        summary = profile.summarize()
        assert "National Chemical" in summary
        assert "remediation" in summary.lower()
        assert "$" in summary

    async def test_search_by_facility_owner(self):
        source = SecEdgarSource(dry_run=True)
        profile = await source.search_by_facility_owner("National Chemical Holdings")
        assert profile is not None
        assert profile.company != ""


@pytest.mark.asyncio
class TestPermitWatchdog:
    async def test_alert_on_nearby_permit(self):
        watchdog = PermitWatchdog()
        watchdog.add_watch_zone(WatchZone(
            zone_id="z1", zip_codes=["62701"],
            name="Lincoln Elementary neighborhood",
            latitude=39.78, longitude=-89.65, radius_miles=3.0,
        ))

        permit = PermitApplication(
            permit_id="IL-2026-001",
            state="IL", applicant="Toxic Corp",
            facility_name="Toxic Corp Springfield",
            facility_address="500 Industrial Way, Springfield, IL",
            latitude=39.785, longitude=-89.645,
            permit_type="air",
            description="Chemical storage and distribution facility",
            comment_deadline=(datetime.now() + timedelta(days=25)).strftime("%Y-%m-%d"),
        )

        alerts = await watchdog.check([permit])
        assert len(alerts) == 1
        assert alerts[0].zone.name == "Lincoln Elementary neighborhood"
        assert alerts[0].distance_miles < 3.0

    async def test_no_alert_for_distant_permit(self):
        watchdog = PermitWatchdog()
        watchdog.add_watch_zone(WatchZone(
            zone_id="z1", zip_codes=["62701"],
            name="Test zone",
            latitude=39.78, longitude=-89.65, radius_miles=3.0,
        ))

        permit = PermitApplication(
            permit_id="IL-2026-002",
            state="IL", applicant="Far Away Inc",
            facility_name="Distant Facility",
            facility_address="999 Remote Road",
            latitude=40.5, longitude=-90.5,
        )

        alerts = await watchdog.check([permit])
        assert len(alerts) == 0

    async def test_dedup_permits(self):
        watchdog = PermitWatchdog()
        watchdog.add_watch_zone(WatchZone(
            zone_id="z1", zip_codes=["62701"],
            name="Test zone",
            latitude=39.78, longitude=-89.65, radius_miles=5.0,
        ))

        permit = PermitApplication(
            permit_id="IL-2026-003",
            state="IL", applicant="Repeat Corp",
            facility_name="Repeat Facility",
            facility_address="100 Same St",
            latitude=39.79, longitude=-89.64,
        )

        alerts1 = await watchdog.check([permit])
        alerts2 = await watchdog.check([permit])
        assert len(alerts1) == 1
        assert len(alerts2) == 0

    async def test_alert_summary(self):
        watchdog = PermitWatchdog()
        watchdog.add_watch_zone(WatchZone(
            zone_id="z1", zip_codes=["62701"],
            name="Elm Street neighborhood",
            latitude=39.78, longitude=-89.65, radius_miles=5.0,
        ))

        permit = PermitApplication(
            permit_id="IL-2026-004",
            state="IL", applicant="Bad Actor LLC",
            facility_name="Bad Actor Springfield Plant",
            facility_address="666 Pollution Ave, Springfield, IL",
            latitude=39.782, longitude=-89.648,
            permit_type="air",
            description="Volatile organic compound processing",
            comment_deadline=(datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
        )

        alerts = await watchdog.check([permit])
        summary = alerts[0].summarize()
        assert "PERMIT ALERT" in summary
        assert "Bad Actor" in summary
        assert "Elm Street" in summary

    async def test_comment_draft_generation(self):
        watchdog = PermitWatchdog()
        watchdog.add_watch_zone(WatchZone(
            zone_id="z1", zip_codes=["62701"],
            name="Test community",
            latitude=39.78, longitude=-89.65, radius_miles=5.0,
        ))

        permit = PermitApplication(
            permit_id="IL-2026-005",
            state="IL", applicant="Polluter Inc",
            facility_name="Polluter Plant",
            facility_address="123 Smoke St",
            latitude=39.781, longitude=-89.649,
            permit_type="air",
            description="coal ash storage facility",
        )

        alerts = await watchdog.check([permit])
        alert = alerts[0]
        alert.applicant_violations = 12
        alert.applicant_penalties = 3_500_000
        alert.community_existing_burden = 7.2
        alert.nearby_schools = 2

        comment = alert.generate_comment_draft()
        assert "12 environmental violations" in comment
        assert "$3,500,000" in comment
        assert "disproportionate environmental burden" in comment
        assert "school" in comment.lower()
        assert "public hearing" in comment

    async def test_callback_fires(self):
        fired = []

        async def on_alert(alert: PermitAlert):
            fired.append(alert)

        watchdog = PermitWatchdog(on_alert=on_alert)
        watchdog.add_watch_zone(WatchZone(
            zone_id="z1", zip_codes=["62701"],
            name="Callback test",
            latitude=39.78, longitude=-89.65, radius_miles=5.0,
        ))

        permit = PermitApplication(
            permit_id="IL-2026-006",
            state="IL", applicant="Test",
            facility_name="Test",
            facility_address="Test",
            latitude=39.781, longitude=-89.649,
        )

        await watchdog.check([permit])
        assert len(fired) == 1
