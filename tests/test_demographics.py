"""Tests for demographic overlay and disparity analysis."""
from __future__ import annotations

import pytest
from raiz.mapping.demographics import (
    CensusSource, CommunityDemographics, DisparityAnalysis,
)


@pytest.mark.asyncio
class TestCensusSource:
    async def test_get_demographics(self):
        source = CensusSource(dry_run=True)
        demo = await source.get_demographics("62701")
        assert demo.total_population == 14200
        assert demo.pct_black == 61.0
        assert demo.median_household_income == 28400

    async def test_different_zip(self):
        source = CensusSource(dry_run=True)
        demo = await source.get_demographics("62704")
        assert demo.pct_white == 82.0
        assert demo.median_household_income == 78500

    async def test_disparity_analysis(self):
        source = CensusSource(dry_run=True)
        analysis = await source.disparity_analysis(
            "62701", "62704",
            burden_a={"violations": 47, "toxic_air_lbs": 50000, "facilities": 3},
            burden_b={"violations": 2, "toxic_air_lbs": 1200, "facilities": 1},
        )
        assert analysis.community_a.pct_black > analysis.community_b.pct_black
        assert analysis.community_a.median_household_income < analysis.community_b.median_household_income


class TestCommunityDemographics:
    def test_majority_minority(self):
        demo = CommunityDemographics(
            zip_code="62701", pct_white=22.0, pct_black=61.0,
        )
        assert demo.majority_minority is True

    def test_not_majority_minority(self):
        demo = CommunityDemographics(
            zip_code="62704", pct_white=82.0, pct_black=5.0,
        )
        assert demo.majority_minority is False

    def test_low_income(self):
        demo = CommunityDemographics(
            zip_code="62701", median_household_income=28400,
        )
        assert demo.low_income is True

    def test_ej_indicators(self):
        demo = CommunityDemographics(
            zip_code="62701", total_population=14200,
            pct_white=22.0, pct_black=61.0,
            median_household_income=28400,
            pct_below_poverty=34.0,
            pct_no_health_insurance=18.0,
            pct_under_5=9.0,
        )
        indicators = demo.ej_indicators
        assert any("Majority-minority" in i for i in indicators)
        assert any("Low-income" in i for i in indicators)
        assert any("poverty" in i.lower() for i in indicators)

    def test_summary(self):
        demo = CommunityDemographics(
            zip_code="62701", total_population=14200,
            pct_white=22.0, pct_black=61.0, pct_hispanic=12.0,
            pct_asian=2.0, pct_indigenous=1.0, pct_other=2.0,
            median_household_income=28400,
            pct_below_poverty=34.0,
            pct_under_5=9.0, pct_over_65=16.0,
            pct_no_health_insurance=18.0,
        )
        summary = demo.summarize()
        assert "62701" in summary
        assert "14,200" in summary
        assert "61%" in summary or "Black: 61%" in summary
        assert "ENVIRONMENTAL JUSTICE" in summary


class TestDisparityAnalysis:
    def test_disparity_summary(self):
        a = CommunityDemographics(
            zip_code="62701", total_population=14200,
            pct_white=22.0, pct_black=61.0, pct_hispanic=12.0,
            pct_indigenous=1.0,
            median_household_income=28400,
        )
        b = CommunityDemographics(
            zip_code="62704", total_population=22800,
            pct_white=82.0, pct_black=5.0, pct_hispanic=6.0,
            pct_indigenous=0.5,
            median_household_income=78500,
        )
        analysis = DisparityAnalysis(
            community_a=a, community_b=b,
            burden_a={"violations": 47, "toxic_air_lbs": 50000},
            burden_b={"violations": 2, "toxic_air_lbs": 1200},
        )
        summary = analysis.summarize()
        assert "DISPARITY" in summary
        assert "environmental racism" in summary.lower()
