"""Tests for FOIA automation."""
from __future__ import annotations

from raiz.investigation.foia import FoiaGenerator, FoiaRequest


class TestFoiaGenerator:
    def test_generate_inspection_request(self):
        gen = FoiaGenerator()
        request = gen.generate_inspection_request(
            "Springfield Chemical Corp", "110000000001", "IL",
        )
        assert request.request_id == "RAIZ-FOIA-0001"
        assert "Illinois" in request.target_agency
        assert request.status == "draft"
        assert len(request.records_requested) >= 5
        assert "Springfield Chemical" in request.subject

    def test_generate_permit_request(self):
        gen = FoiaGenerator()
        request = gen.generate_permit_request(
            "IL-AIR-2026-0847", "NatChem Springfield", "IL",
        )
        assert "IL-AIR-2026-0847" in request.subject
        assert request.status == "draft"

    def test_format_letter(self):
        gen = FoiaGenerator()
        request = gen.generate_inspection_request(
            "Springfield Chemical Corp", "110000000001", "IL",
        )
        letter = gen.format_letter(request, "Jane Doe", "123 Elm St, Springfield, IL")
        assert "Jane Doe" in letter
        assert "Freedom of Information Act" in letter
        assert "Springfield Chemical" in letter
        assert "fee waiver" in letter.lower()
        assert "RAIZ-FOIA" in letter

    def test_mark_filed(self):
        gen = FoiaGenerator()
        request = gen.generate_inspection_request("Test", "1", "IL")
        gen.mark_filed(request.request_id)
        assert gen.requests[0].status == "filed"

    def test_overdue_detection(self):
        gen = FoiaGenerator()
        request = gen.generate_inspection_request("Test", "1", "IL")
        request.status = "filed"
        request.response_deadline = "2020-01-01"
        overdue = gen.check_overdue()
        assert len(overdue) == 1

    def test_not_overdue_when_responded(self):
        gen = FoiaGenerator()
        request = gen.generate_inspection_request("Test", "1", "IL")
        request.status = "responded"
        request.response_deadline = "2020-01-01"
        overdue = gen.check_overdue()
        assert len(overdue) == 0

    def test_status_summary(self):
        gen = FoiaGenerator()
        gen.generate_inspection_request("Facility A", "1", "IL")
        gen.generate_permit_request("P-001", "Facility B", "CA")
        summary = gen.status_summary()
        assert "2 tracked" in summary
        assert "Facility A" in summary
        assert "Facility B" in summary

    def test_federal_fallback(self):
        gen = FoiaGenerator()
        request = gen.generate_inspection_request("Test", "1", "ZZ")
        assert "U.S. Environmental Protection Agency" in request.target_agency

    def test_counter_increments(self):
        gen = FoiaGenerator()
        r1 = gen.generate_inspection_request("A", "1", "IL")
        r2 = gen.generate_inspection_request("B", "2", "IL")
        assert r1.request_id == "RAIZ-FOIA-0001"
        assert r2.request_id == "RAIZ-FOIA-0002"

    def test_days_until_deadline(self):
        gen = FoiaGenerator()
        request = gen.generate_inspection_request("Test", "1", "IL")
        assert request.days_until_deadline > 0
