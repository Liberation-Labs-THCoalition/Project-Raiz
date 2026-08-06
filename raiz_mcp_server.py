"""Raiz MCP Server -- environmental justice intelligence via MCP.

Exposes Raiz capabilities as MCP tools for Claude Code, Claude
Desktop, or any MCP-compatible client.

Tools:
  raiz_ask      -- Core environmental justice query for a zip code
  raiz_monitor  -- Check environmental conditions for a location
  raiz_permits  -- Search and analyze environmental permits
  raiz_foia     -- Generate a FOIA request targeting environmental data
  raiz_health   -- Agent status and configuration

Resources:
  raiz://config  -- Current configuration and data source status
  raiz://values  -- VALUES.json ethics and mission

Usage:
  python raiz_mcp_server.py
  python raiz_mcp_server.py --config /path/to/config.json
  python raiz_mcp_server.py --dry-run

  # In Claude Code .claude/mcp.json:
  {
    "mcpServers": {
      "raiz": {
        "command": "python",
        "args": ["raiz_mcp_server.py", "--dry-run"]
      }
    }
  }

Liberation Labs / TH Coalition -- proprietary.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("raiz.mcp")

try:
    from mcp.server import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import (
        Tool,
        TextContent,
        Resource,
    )
    HAS_MCP = True
except ImportError:
    HAS_MCP = False

SERVER_VERSION = "0.1.0"
CONFIG_DIR = Path(__file__).parent / "config"


def _load_config(config_path: str = "") -> dict[str, Any]:
    cfg: dict[str, Any] = {
        "airnow_key": os.environ.get("RAIZ_AIRNOW_KEY", ""),
        "purpleair_key": os.environ.get("RAIZ_PURPLEAIR_KEY", ""),
        "census_key": os.environ.get("RAIZ_CENSUS_KEY", ""),
        "dry_run": False,
    }
    if config_path:
        try:
            with open(config_path) as f:
                user_cfg = json.load(f)
            cfg.update(user_cfg)
        except Exception as e:
            logger.warning("Could not load config %s: %s", config_path, e)
    return cfg


def create_server(config_path: str = "", dry_run: bool = False) -> "Server":
    if not HAS_MCP:
        raise ImportError(
            "MCP SDK not installed. Install with: pip install mcp"
        )

    server = Server("raiz")
    cfg = _load_config(config_path)
    if dry_run:
        cfg["dry_run"] = True

    _engine = None
    _foia = None
    _watchdog = None
    _started = datetime.now(timezone.utc)

    def _get_engine():
        nonlocal _engine
        if _engine is None:
            from raiz.community.query import CommunityQueryEngine
            _engine = CommunityQueryEngine(
                airnow_key=cfg.get("airnow_key", ""),
                purpleair_key=cfg.get("purpleair_key", ""),
                census_key=cfg.get("census_key", ""),
                dry_run=cfg.get("dry_run", False),
            )
        return _engine

    def _get_foia():
        nonlocal _foia
        if _foia is None:
            from raiz.investigation.foia import FoiaGenerator
            _foia = FoiaGenerator()
        return _foia

    def _get_watchdog():
        nonlocal _watchdog
        if _watchdog is None:
            from raiz.pulse.watchdog import PermitWatchdog
            _watchdog = PermitWatchdog()
        return _watchdog

    # -- Tools --

    @server.list_tools()
    async def list_tools():
        return [
            Tool(
                name="raiz_ask",
                description=(
                    "Query all environmental data sources for a US zip code. "
                    "Returns regulated facilities, violations, toxic releases, "
                    "air quality, demographics, corporate accountability, "
                    "risk score, and suggested actions."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "zip_code": {
                            "type": "string",
                            "description": "US zip code to investigate (e.g. '62701')",
                        },
                        "include_actions": {
                            "type": "boolean",
                            "description": "Include suggested community actions",
                            "default": True,
                        },
                        "include_corporate": {
                            "type": "boolean",
                            "description": "Search SEC filings for facility owners",
                            "default": True,
                        },
                    },
                    "required": ["zip_code"],
                },
            ),
            Tool(
                name="raiz_monitor",
                description=(
                    "Check current environmental conditions for a location. "
                    "Returns air quality from EPA monitors and community "
                    "sensors, nearby facilities and their compliance status, "
                    "and identifies monitoring gaps."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "zip_code": {
                            "type": "string",
                            "description": "US zip code to check",
                        },
                        "include_air": {
                            "type": "boolean",
                            "description": "Include air quality data",
                            "default": True,
                        },
                        "include_facilities": {
                            "type": "boolean",
                            "description": "Include nearby regulated facilities",
                            "default": True,
                        },
                        "include_tri": {
                            "type": "boolean",
                            "description": "Include toxic release inventory data",
                            "default": True,
                        },
                    },
                    "required": ["zip_code"],
                },
            ),
            Tool(
                name="raiz_permits",
                description=(
                    "Search and analyze environmental permits for a facility "
                    "or area. Returns permit applications, compliance history, "
                    "violation records, and watch zone status."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "zip_code": {
                            "type": "string",
                            "description": "US zip code to search for permits",
                            "default": "",
                        },
                        "facility_id": {
                            "type": "string",
                            "description": "EPA registry ID for a specific facility",
                            "default": "",
                        },
                        "facility_name": {
                            "type": "string",
                            "description": "Facility name to search for",
                            "default": "",
                        },
                        "state": {
                            "type": "string",
                            "description": "Two-letter state code (e.g. 'IL')",
                            "default": "",
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="raiz_foia",
                description=(
                    "Generate a FOIA request letter targeting environmental "
                    "data for a facility. Returns a ready-to-send letter with "
                    "the correct agency, address, and records requested."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "facility_name": {
                            "type": "string",
                            "description": "Name of the facility to investigate",
                        },
                        "facility_id": {
                            "type": "string",
                            "description": "EPA registry ID or permit ID",
                            "default": "",
                        },
                        "state": {
                            "type": "string",
                            "description": "Two-letter state code (e.g. 'IL')",
                        },
                        "request_type": {
                            "type": "string",
                            "description": "Type of FOIA request: 'inspection' or 'permit'",
                            "default": "inspection",
                            "enum": ["inspection", "permit"],
                        },
                        "requester_name": {
                            "type": "string",
                            "description": "Name of the person filing the request",
                            "default": "[YOUR NAME]",
                        },
                        "requester_address": {
                            "type": "string",
                            "description": "Address of the person filing",
                            "default": "[YOUR ADDRESS]",
                        },
                    },
                    "required": ["facility_name", "state"],
                },
            ),
            Tool(
                name="raiz_health",
                description=(
                    "Agent health check. Returns server status, uptime, "
                    "data source availability, active watch zones, and "
                    "tracked FOIA requests."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {},
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "raiz_ask":
                return await _handle_ask(arguments)
            elif name == "raiz_monitor":
                return await _handle_monitor(arguments)
            elif name == "raiz_permits":
                return await _handle_permits(arguments)
            elif name == "raiz_foia":
                return await _handle_foia(arguments)
            elif name == "raiz_health":
                return await _handle_health(arguments)
            else:
                return [TextContent(type="text", text=json.dumps(
                    {"error": f"Unknown tool: {name}"}
                ))]
        except Exception as e:
            logger.exception("Tool %s failed", name)
            return [TextContent(type="text", text=json.dumps(
                {"error": str(e), "tool": name}
            ))]

    async def _handle_ask(args: dict) -> list[TextContent]:
        zip_code = args.get("zip_code", "")
        if not zip_code:
            return [TextContent(type="text", text=json.dumps(
                {"error": "zip_code is required"}
            ))]

        engine = _get_engine()
        report = await engine.query(zip_code)

        result: dict[str, Any] = {
            "zip_code": zip_code,
            "timestamp": report.timestamp.isoformat(),
            "risk_score": report.risk_score,
            "risk_factors": report.risk_factors,
        }

        if report.echo:
            result["facilities"] = {
                "total": report.echo.total_facilities,
                "in_violation": report.echo.facilities_in_violation,
                "violations_3yr": report.echo.total_violations_3yr,
                "penalties_3yr": report.echo.total_penalties_3yr,
                "list": [
                    {
                        "name": f.name,
                        "registry_id": f.registry_id,
                        "address": f"{f.street}, {f.city}, {f.state} {f.zip_code}",
                        "programs": f.programs,
                        "parent_company": f.parent_company,
                    }
                    for f in report.echo.facilities[:20]
                ],
            }

        if report.toxic_profile:
            tp = report.toxic_profile
            result["toxic_releases"] = {
                "total_air_lbs": tp.total_air_lbs,
                "total_water_lbs": tp.total_water_lbs,
                "total_land_lbs": tp.total_land_lbs,
                "unique_chemicals": tp.unique_chemicals,
                "carcinogen_count": tp.carcinogen_count,
                "top_polluters": tp.top_polluters[:5],
                "releases": [
                    {
                        "facility": r.facility_name,
                        "chemical": r.chemical,
                        "total_lbs": r.total_releases_lbs,
                        "air_lbs": r.total_air_lbs,
                        "carcinogen": r.carcinogen,
                    }
                    for r in tp.releases[:20]
                ],
            }

        if report.air_quality:
            aq = report.air_quality
            result["air_quality"] = {
                "monitoring_gap": aq.monitoring_gap,
                "readings_count": len(aq.readings),
                "summary": aq.summarize(),
            }
            if aq.nearest_epa_monitor:
                m = aq.nearest_epa_monitor
                result["air_quality"]["nearest_epa"] = {
                    "station": m.station_name,
                    "aqi": m.aqi,
                    "category": m.category,
                    "distance_miles": m.distance_miles,
                }
            if aq.nearest_community_sensor:
                s = aq.nearest_community_sensor
                result["air_quality"]["nearest_community"] = {
                    "station": s.station_name,
                    "pm25": s.pm25,
                    "distance_miles": s.distance_miles,
                }

        if report.demographics:
            d = report.demographics
            result["demographics"] = {
                "population": d.total_population,
                "median_income": d.median_household_income,
                "pct_below_poverty": d.pct_below_poverty,
                "majority_minority": d.majority_minority,
                "low_income": d.low_income,
                "ej_indicators": d.ej_indicators,
                "race": {
                    "white": d.pct_white,
                    "black": d.pct_black,
                    "hispanic": d.pct_hispanic,
                    "asian": d.pct_asian,
                    "indigenous": d.pct_indigenous,
                },
            }

        if args.get("include_corporate", True) and report.corporate_profiles:
            result["corporate_profiles"] = [
                {
                    "company": cp.company,
                    "ticker": cp.ticker,
                    "remediation_reserves": cp.total_remediation_reserves,
                    "consent_decrees": cp.active_consent_decrees,
                    "superfund_sites": cp.superfund_sites,
                    "pending_litigation": cp.pending_litigation,
                    "penalties_disclosed": cp.epa_penalties_disclosed,
                    "disclosures_count": len(cp.disclosures),
                }
                for cp in report.corporate_profiles
            ]

        if args.get("include_actions", True):
            result["actions"] = report.action_items()

        result["summary"] = report.summarize()

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _handle_monitor(args: dict) -> list[TextContent]:
        zip_code = args.get("zip_code", "")
        if not zip_code:
            return [TextContent(type="text", text=json.dumps(
                {"error": "zip_code is required"}
            ))]

        engine = _get_engine()
        result: dict[str, Any] = {
            "zip_code": zip_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if args.get("include_air", True):
            readings = await engine.airnow.current_by_zip(zip_code)
            result["air_quality"] = {
                "epa_readings": [
                    {
                        "station": r.station_name,
                        "aqi": r.aqi,
                        "pm25": r.pm25,
                        "category": r.category,
                        "distance_miles": r.distance_miles,
                    }
                    for r in readings
                ],
            }

            if readings and readings[0].latitude:
                pa = await engine.purpleair.sensors_near(
                    readings[0].latitude, readings[0].longitude,
                )
                result["air_quality"]["community_sensors"] = [
                    {
                        "station": s.station_name,
                        "pm25": s.pm25,
                        "distance_miles": s.distance_miles,
                    }
                    for s in pa
                ]

            has_epa = any(r.distance_miles <= 5.0 for r in readings) if readings else False
            result["air_quality"]["monitoring_gap"] = not has_epa

        if args.get("include_facilities", True):
            facilities = await engine.echo.facilities_by_zip(zip_code)
            violations_by_facility: dict[str, int] = {}
            for f in facilities[:10]:
                v = await engine.echo.violations_for_facility(f.registry_id)
                violations_by_facility[f.registry_id] = len(v)

            result["facilities"] = [
                {
                    "name": f.name,
                    "registry_id": f.registry_id,
                    "address": f"{f.street}, {f.city}, {f.state}",
                    "programs": f.programs,
                    "parent_company": f.parent_company,
                    "violations_count": violations_by_facility.get(f.registry_id, 0),
                }
                for f in facilities[:20]
            ]

        if args.get("include_tri", True):
            profile = await engine.tri.community_profile(zip_code)
            result["toxic_releases"] = {
                "summary": profile.summarize(),
                "total_air_lbs": profile.total_air_lbs,
                "carcinogen_count": profile.carcinogen_count,
                "top_polluters": profile.top_polluters[:5],
            }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _handle_permits(args: dict) -> list[TextContent]:
        zip_code = args.get("zip_code", "")
        facility_id = args.get("facility_id", "")
        facility_name = args.get("facility_name", "")
        state = args.get("state", "")

        engine = _get_engine()
        result: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if facility_id:
            violations = await engine.echo.violations_for_facility(facility_id)
            result["facility_id"] = facility_id
            result["violations"] = [
                {
                    "program": v.program,
                    "type": v.violation_type,
                    "date": v.violation_date,
                    "status": v.compliance_status,
                    "pollutant": v.pollutant,
                    "severity": v.severity,
                }
                for v in violations
            ]
            result["violation_count"] = len(violations)

        if zip_code:
            facilities = await engine.echo.facilities_by_zip(zip_code)
            if facility_name:
                name_lower = facility_name.lower()
                facilities = [
                    f for f in facilities
                    if name_lower in f.name.lower()
                ]

            result["zip_code"] = zip_code
            result["facilities"] = [
                {
                    "name": f.name,
                    "registry_id": f.registry_id,
                    "address": f"{f.street}, {f.city}, {f.state} {f.zip_code}",
                    "programs": f.programs,
                    "parent_company": f.parent_company,
                    "lat": f.latitude,
                    "lon": f.longitude,
                }
                for f in facilities[:20]
            ]
            result["facility_count"] = len(facilities)

        elif state and not facility_id:
            facilities = await engine.echo.facilities_by_state(state)
            if facility_name:
                name_lower = facility_name.lower()
                facilities = [
                    f for f in facilities
                    if name_lower in f.name.lower()
                ]
            result["state"] = state
            result["facilities"] = [
                {
                    "name": f.name,
                    "registry_id": f.registry_id,
                    "city": f.city,
                    "programs": f.programs,
                    "parent_company": f.parent_company,
                }
                for f in facilities[:20]
            ]
            result["facility_count"] = len(facilities)

        watchdog = _get_watchdog()
        result["watch_zones"] = [
            {
                "zone_id": z.zone_id,
                "name": z.name,
                "zip_codes": z.zip_codes,
                "radius_miles": z.radius_miles,
            }
            for z in watchdog.watch_zones
        ]
        result["recent_alerts"] = [
            {
                "permit_id": a.permit.permit_id,
                "facility": a.permit.facility_name,
                "distance_miles": a.distance_miles,
                "risk": a.risk_assessment,
                "comment_days": a.comment_deadline_days,
            }
            for a in watchdog.alerts[-10:]
        ]

        if not zip_code and not facility_id and not state:
            result["note"] = (
                "Provide zip_code, facility_id, or state to search. "
                "Without parameters, only watch zone status is returned."
            )

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _handle_foia(args: dict) -> list[TextContent]:
        facility_name = args.get("facility_name", "")
        facility_id = args.get("facility_id", "")
        state = args.get("state", "")
        request_type = args.get("request_type", "inspection")
        requester_name = args.get("requester_name", "[YOUR NAME]")
        requester_address = args.get("requester_address", "[YOUR ADDRESS]")

        if not facility_name:
            return [TextContent(type="text", text=json.dumps(
                {"error": "facility_name is required"}
            ))]
        if not state:
            return [TextContent(type="text", text=json.dumps(
                {"error": "state is required (two-letter code)"}
            ))]

        generator = _get_foia()

        if request_type == "permit":
            request = generator.generate_permit_request(
                permit_id=facility_id or "UNKNOWN",
                facility_name=facility_name,
                state=state.upper(),
            )
        else:
            request = generator.generate_inspection_request(
                facility_name=facility_name,
                facility_id=facility_id or "UNKNOWN",
                state=state.upper(),
                requester_name=requester_name,
                requester_address=requester_address,
            )

        letter = generator.format_letter(
            request,
            requester_name=requester_name,
            requester_address=requester_address,
        )

        result = {
            "request_id": request.request_id,
            "target_agency": request.target_agency,
            "target_address": request.target_address,
            "target_email": request.target_email,
            "subject": request.subject,
            "records_requested": request.records_requested,
            "response_deadline": request.response_deadline,
            "status": request.status,
            "letter": letter,
            "instructions": (
                "1. Replace [YOUR NAME] and [YOUR ADDRESS] with your details. "
                "2. Send via email to the listed address, or print and mail. "
                "3. Keep a copy for your records. "
                "4. The agency must respond within the deadline shown."
            ),
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    async def _handle_health(args: dict) -> list[TextContent]:
        now = datetime.now(timezone.utc)
        uptime_seconds = (now - _started).total_seconds()

        sources: dict[str, str] = {}
        try:
            _get_engine()
            sources["epa_echo"] = "available"
            sources["epa_tri"] = "available"
        except Exception:
            sources["epa_echo"] = "unavailable"
            sources["epa_tri"] = "unavailable"

        sources["airnow"] = "configured" if cfg.get("airnow_key") else "no_api_key"
        sources["purpleair"] = "configured" if cfg.get("purpleair_key") else "no_api_key"
        sources["census"] = "configured" if cfg.get("census_key") else "no_api_key"
        sources["sec_edgar"] = "available"

        foia = _get_foia()
        watchdog = _get_watchdog()

        values_path = CONFIG_DIR / "VALUES.json"
        values_loaded = values_path.exists()

        result = {
            "status": "healthy",
            "version": SERVER_VERSION,
            "uptime_seconds": round(uptime_seconds),
            "dry_run": cfg.get("dry_run", False),
            "data_sources": sources,
            "foia_requests_tracked": len(foia.requests),
            "foia_overdue": len(foia.check_overdue()),
            "watch_zones": len(watchdog.watch_zones),
            "alerts_generated": len(watchdog.alerts),
            "last_permit_check": (
                watchdog.last_check.isoformat() if watchdog.last_check else None
            ),
            "values_loaded": values_loaded,
        }

        return [TextContent(type="text", text=json.dumps(result, indent=2))]

    # -- Resources --

    @server.list_resources()
    async def list_resources():
        return [
            Resource(
                uri="raiz://config",
                name="Raiz Configuration",
                description="Current configuration and data source status",
                mimeType="application/json",
            ),
            Resource(
                uri="raiz://values",
                name="Raiz Values",
                description="Ethics, mission, and EFE weight configuration",
                mimeType="application/json",
            ),
        ]

    @server.read_resource()
    async def read_resource(uri: str):
        if uri.endswith("/config") or uri == "raiz://config":
            safe_cfg = {k: v for k, v in cfg.items() if "key" not in k.lower()}
            safe_cfg["has_airnow_key"] = bool(cfg.get("airnow_key"))
            safe_cfg["has_purpleair_key"] = bool(cfg.get("purpleair_key"))
            safe_cfg["has_census_key"] = bool(cfg.get("census_key"))
            return json.dumps(safe_cfg, indent=2)
        elif uri.endswith("/values") or uri == "raiz://values":
            values_path = CONFIG_DIR / "VALUES.json"
            if values_path.exists():
                return values_path.read_text()
            return json.dumps({"error": "VALUES.json not found"})
        else:
            return json.dumps({"error": f"Unknown resource: {uri}"})

    return server


async def main(config_path: str = "", dry_run: bool = False):
    server = create_server(config_path=config_path, dry_run=dry_run)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream)


if __name__ == "__main__":
    import asyncio

    parser = argparse.ArgumentParser(description="Raiz MCP Server")
    parser.add_argument(
        "--config", default="", help="Path to config JSON file",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Use mock data instead of real API calls",
    )
    args = parser.parse_args()

    asyncio.run(main(config_path=args.config, dry_run=args.dry_run))
