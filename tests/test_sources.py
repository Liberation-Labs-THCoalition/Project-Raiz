"""Tests for Raíz data sources — all run in dry-run mode."""
from __future__ import annotations

import pytest
from raiz.sources.epa_echo import EchoSource, Facility, Violation
from raiz.sources.epa_tri import TriSource, ToxicRelease
from raiz.sources.air_quality import AirNowSource, PurpleAirSource, AirReading


@pytest.mark.asyncio
class TestEchoSource:
    async def test_facilities_by_zip(self):
        source = EchoSource(dry_run=True)
        facilities = await source.facilities_by_zip("62701")
        assert len(facilities) > 0
        assert facilities[0].name == "Springfield Chemical Corp"
        assert "CAA" in facilities[0].programs

    async def test_violations_for_facility(self):
        source = EchoSource(dry_run=True)
        violations = await source.violations_for_facility("110000000001")
        assert len(violations) > 0
        assert violations[0].program == "CAA"
        assert violations[0].severity == "High Priority"

    async def test_community_report(self):
        source = EchoSource(dry_run=True)
        report = await source.community_report("62701")
        assert report.total_facilities > 0
        assert report.facilities_in_violation > 0
        assert report.query == "zip:62701"


@pytest.mark.asyncio
class TestTriSource:
    async def test_releases_by_zip(self):
        source = TriSource(dry_run=True)
        releases = await source.releases_by_zip("62701")
        assert len(releases) > 0
        assert releases[0].chemical == "Toluene"
        assert releases[0].total_releases_lbs > 0

    async def test_carcinogen_detection(self):
        source = TriSource(dry_run=True)
        releases = await source.releases_by_zip("62701")
        benzene = [r for r in releases if r.chemical == "Benzene"]
        assert len(benzene) > 0
        assert benzene[0].carcinogen is True

    async def test_community_profile(self):
        source = TriSource(dry_run=True)
        profile = await source.community_profile("62701")
        assert profile.total_air_lbs > 0
        assert profile.carcinogen_count > 0
        assert len(profile.top_polluters) > 0

    async def test_community_profile_summary(self):
        source = TriSource(dry_run=True)
        profile = await source.community_profile("62701")
        summary = profile.summarize()
        assert "62701" in summary
        assert "carcinogen" in summary.lower()


@pytest.mark.asyncio
class TestAirNow:
    async def test_current_by_zip(self):
        source = AirNowSource(dry_run=True)
        readings = await source.current_by_zip("62701")
        assert len(readings) > 0
        assert readings[0].source == "airnow"
        assert readings[0].aqi > 0


@pytest.mark.asyncio
class TestPurpleAir:
    async def test_sensors_near(self):
        source = PurpleAirSource(dry_run=True)
        readings = await source.sensors_near(39.78, -89.65)
        assert len(readings) > 0
        assert readings[0].source == "purpleair"
        assert readings[0].pm25 > 0


class TestAirReading:
    def test_unhealthy_threshold(self):
        reading = AirReading(
            timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            source="test", latitude=0, longitude=0,
            aqi=150,
        )
        assert reading.is_unhealthy
        assert not reading.is_hazardous

    def test_hazardous_threshold(self):
        reading = AirReading(
            timestamp=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
            source="test", latitude=0, longitude=0,
            aqi=350,
        )
        assert reading.is_unhealthy
        assert reading.is_hazardous


class TestToxicRelease:
    def test_total_air(self):
        release = ToxicRelease(
            facility_name="Test", facility_id="1",
            chemical="X", year=2023, city="Test", state="IL",
            zip_code="62701",
            fugitive_air_lbs=1000, stack_air_lbs=2000,
        )
        assert release.total_air_lbs == 3000
