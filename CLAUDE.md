# CLAUDE.md — Project Raíz

## What Is Raíz

Raíz (*raíz* — Spanish for root) is an AI environmental justice agent built on the Kintsugi Engine. It connects fragmented environmental data sources into a unified intelligence layer that serves communities, activists, and environmental lawyers.

The roots see what the surface hides.

In February 2025, the federal government removed EJSCREEN and CEJST — the two primary environmental justice screening tools. Communities that relied on these tools for permit fights and regulatory comments are flying blind. Raíz rebuilds that capability from raw data sources and adds investigation, prediction, and alerting that never existed.

## Architecture

Built on Kintsugi Engine primitives:
- **Pulse** — watchdog heartbeat: permit monitoring, violation checks, air quality alerts
- **BDI** — beliefs about environmental conditions, desires for justice, active investigation intentions
- **EFE** — risk-weighted decisions (which leads to pursue, when to alert, confidence thresholds)
- **VALUES.json** — community sovereignty, data transparency, no greenwashing
- **Comms Dispatcher** — alerts to orgs, community dashboards, media summaries
- **Shield Module** — protect community data, responsible disclosure

```
Data Sources                    Intelligence              Action
├─ EPA ECHO (violations)  ──┐                          ┌── Community Alerts
├─ EPA TRI (toxic releases) ─┤                          ├── Public Comment Drafts
├─ AirNow + PurpleAir  ─────┼── Raíz Pulse Engine ────┼── Investigation Reports
├─ State Permit DBs  ────────┤   (Kintsugi BDI+EFE)    ├── Legal Brief Data
├─ SEC EDGAR (10-K/10-Q) ───┤                          ├── Media Summaries
├─ OpenAQ (global air) ─────┤                          └── Org Dashboards
├─ Census/Demographics  ─────┘
└─ FOIA Automation  ─────────┘
```

## Key Directories

```
raiz/
  sources/       Data source connectors (EPA, SEC, AirNow, state permits)
  analysis/      Environmental justice analysis, violation prediction
  community/     Community-facing outputs (alerts, fact sheets, comments)
  investigation/ Lead scoring, corporate accountability, FOIA automation
  mapping/       GIS integration, demographic overlay, facility mapping
  pulse/         Watchdog configuration, monitoring schedules
config/          VALUES.json, data source credentials
tests/           Test suite
docs/            Architecture, regulatory notes, org onboarding
```

## Data Sources

### Tier 1 — Ready Now (Python packages exist)
- EPA ECHO via `ECHO_modules` (EDGI) — violations, inspections, enforcement
- EPA TRI via EnviroFacts REST API — toxic chemical releases
- AirNow via `pyairnow` — real-time air quality
- EPA AQS via `pyaqsapi` — historical air monitoring
- OpenAQ via `openaq` SDK — global community sensors
- PurpleAir via `purpleair-api` — hyperlocal PM2.5
- SEC EDGAR via `edgartools` — corporate environmental disclosures

### Tier 2 — Needs Integration Work
- State environmental permit databases (50 states, no unified API)
- FOIA automation via `foiamachine` / EPA FOIAOnline scraper
- CalEnviroScreen 5.0 (California EJ data, CSV/shapefile)
- Safecast (radiation monitoring, public API)

### Tier 3 — Future
- Satellite imagery for illegal dumping / emissions
- Court records for environmental litigation
- ML violation prediction from ECHO history

## Phase 1 MVP: Community Query Engine

One question, one answer: "What is affecting my community?"

Enter a zip code. Get back:
- Facilities with recent violations (ECHO)
- Toxic releases in the area (TRI)
- Current air quality (AirNow + PurpleAir)
- Demographic overlay (who lives here)
- Recent permit activity (state DB)
- Corporate owners and their SEC disclosure history

No app needed. CLI or web interface.

## Ethics (Non-Negotiable)

- Community sovereignty — affected communities lead, Raíz supports
- Data transparency — all findings public, all methods auditable
- No corporate greenwashing partnerships
- Environmental racism must be named explicitly
- Open source — the tools to defend your air and water should be free
- Verify before alerting — false alarms erode trust

## Team

- **CC (Coalition Code)** — Architecture, Kintsugi integration
- **Thomas Edrington** — Project direction
- **Liberation Labs / TH Coalition** — Parent organization
- Environmental org advisors: TBD
- Community beta testers: essential before any public launch

## Running Tests

```bash
cd /home/asdf/Project-Raiz
python -m pytest tests/ -x -q
```
