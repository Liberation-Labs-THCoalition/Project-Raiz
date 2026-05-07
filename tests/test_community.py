"""Tests for community query engine."""
from __future__ import annotations

import pytest
from raiz.community.query import CommunityQueryEngine, CommunityReport


@pytest.mark.asyncio
class TestCommunityQuery:
    async def test_full_query(self):
        engine = CommunityQueryEngine(dry_run=True)
        report = await engine.query("62701")
        assert report.zip_code == "62701"
        assert report.echo is not None
        assert report.toxic_profile is not None
        assert report.air_quality is not None

    async def test_risk_score(self):
        engine = CommunityQueryEngine(dry_run=True)
        report = await engine.query("62701")
        assert report.risk_score > 0
        assert len(report.risk_factors) > 0

    async def test_summary_readable(self):
        engine = CommunityQueryEngine(dry_run=True)
        report = await engine.query("62701")
        summary = report.summarize()
        assert "62701" in summary
        assert "Raíz" in summary
        assert "REGULATED FACILITIES" in summary

    async def test_action_items(self):
        engine = CommunityQueryEngine(dry_run=True)
        report = await engine.query("62701")
        actions = report.action_items()
        assert len(actions) > 0

    async def test_carcinogen_action_item(self):
        engine = CommunityQueryEngine(dry_run=True)
        report = await engine.query("62701")
        actions = report.action_items()
        carcinogen_action = [a for a in actions if "carcinogen" in a.lower()]
        assert len(carcinogen_action) > 0
