# FABLE_AUDIT.md — Project Raíz Codebase & Integration Audit

**Auditor:** CC (Coalition Code)
**Date:** 2026-07-07
**Scope:** Full codebase read (`raiz/`, `tests/`, `config/`), live verification of every external API integration, dependency/version currency check, test-suite execution.
**Method:** Read every source file. Ran the 163-test suite. Hit the real EPA ECHO, Envirofacts/TRI, Census, AirNow, and PurpleAir endpoints directly with `curl` (not just docs) to confirm what they actually return today, not what the code assumes they return. Checked `edgartools` current API against GitHub/PyPI. Checked whether EJSCREEN/CEJST are still gone.

## Bottom line

Raíz is well-architected — clean dataclasses, sensible dry-run/live split, a coherent Kintsugi BDI/EFE scaffold, 163 passing tests. But **the test suite only ever exercises dry-run mode**, and that mask hides the fact that **two of the four "Tier 1 — Ready Now" data sources are broken against the real APIs today**: EPA TRI queries the wrong table with the wrong field names, and the ECHO violation-detail call uses a service name and calling convention that doesn't correspond to how ECHO's REST services actually work. Neither would raise an exception — both would silently return empty/zero data, which for an environmental-justice tool is the worst failure mode: a community queries their zip code, gets a clean report with "0 toxic releases," and never learns their air monitor doesn't work either.

Also: the founding premise ("Raíz rebuilds what EJSCREEN/CEJST took away") is now half-overtaken by events — a third-party coalition (PEDP) already restored both tools in 2025–2026. That's not a reason to stop building Raíz, but the README/pitch should reposition around what Raíz uniquely adds (cross-source synthesis, permit watchdog, FOIA automation, corporate accountability linking) rather than "rebuilding what was removed."

---

## 1. Data source integrations — verified against live APIs

### 🔴 EPA TRI (`raiz/sources/epa_tri.py`) — broken in live mode

The code queries:
```
https://enviro.epa.gov/enviro/efservice/tri_facility/zip_code/=/{zip}/reporting_year/=/{year}/JSON
```
and parses uppercase fields: `CHEMICAL_NAME`, `FACILITY_NAME`, `LATITUDE`, `FUGITIVE_AIR`, `STACK_AIR`, `WATER`, `TOTAL_RELEASES`, `PARENT_CO_NAME`, `INDUSTRY_SECTOR`.

I hit this table live. Two independent problems:

1. **Wrong table.** `tri_facility` is a facility-directory table — it has no chemical or release-quantity fields at all. Confirmed via live query (real facility, Chicago zip 60609):
   ```json
   {"tri_facility_id": "60608NGNRD929WE", "facility_name": "EUROPTEC USA LLC",
    "fac_latitude": 414905, "fac_longitude": 873859,
    "parent_co_name": "EUROPTEC USA INC", ...}
   ```
   No `chemical_name`, no `fugitive_air`, no `total_releases` — anywhere in this table. Release quantities live in a separate table (`tri_reporting_form` plus its child release-quantity tables), which the code never queries.
2. **Wrong field-name casing even for the fields that do exist.** Real Envirofacts fields are lowercase snake_case (`facility_name`, `fac_latitude`, `parent_co_name`), not the uppercase (`FACILITY_NAME`, `LATITUDE`, `PARENT_CO_NAME`) the code looks up. Every `.get(...)` silently falls through to its default (`""`/`0`).
3. **Bonus:** `fac_latitude`/`fac_longitude` aren't decimal degrees — `873859` is DMS-as-integer (87°38'59"), not `87.3859`. The code's `float(row.get(...))` cast would produce a wildly wrong coordinate even if the field name were fixed.
4. **Endpoint itself moved.** `enviro.epa.gov/enviro/efservice/...` now returns `301 → https://data.epa.gov/efservice/...`. It still works (redirect is followed by `aiohttp` by default), but you're one deprecation cycle away from that redirect disappearing. Point `TRI_BASE` at `https://data.epa.gov/efservice` directly.

**Net effect:** in live mode, `TriSource.releases_by_zip()` will return a list of empty-ish `ToxicRelease` objects (blank chemical name, zero pounds) for any facility that happens to appear in `tri_facility`, and the carcinogen/top-polluter/summary logic downstream will just report "no releases found" — indistinguishable from a genuinely clean zip code. This is not tested anywhere: `tests/test_sources.py` runs every TRI test with `dry_run=True`, so the mock data (which hand-codes correct-looking fields) has never been checked against a live response.

**Fix:** rewrite `_query_facilities`/`releases_by_zip` to (a) hit `data.epa.gov/efservice/tri_reporting_form` (or the appropriate joined release-quantity table — confirm exact table name via `enviro.epa.gov/envirofacts/metadata/api-viewer`), (b) use lowercase field names, (c) convert `fac_latitude`/`fac_longitude` from DMS-integer to decimal degrees (`degrees = int(str(v)[:len-4]) + ...` — needs care, or just drop coordinate use from TRI and rely on ECHO's facility coordinates, which are already plain decimal).

### 🔴 EPA ECHO violation detail (`raiz/sources/epa_echo.py::violations_for_facility`) — likely broken in live mode

The code calls:
```
https://echodata.epa.gov/echo/cwa_rest_services.get_qid?p_id={registry_id}&output=JSON
```
`get_qid` is a real ECHO concept, but it belongs to **CASE Rest Services**, not a `cwa_rest_services` family, and it isn't a facility-lookup call — it's step 2 of a 4-step workflow (`get_cases` → returns a QID → `get_qid` paginates results *for that QID* → `get_map`/`get_download`). Passing a facility registry ID directly as `p_id` to `get_qid` doesn't match documented usage. I could not fully confirm the exact failure mode live (ECHO's own rate limiter kicked in after a handful of test requests — confirmed real and unforgiving: "exceed 300 per hour or 1,500 per day" — see §2), but the calling convention in the code doesn't match anything EPA documents, and there is no `cwa_rest_services` prefix in any current ECHO documentation I found.

**What actually gets facility-level violation history in ECHO today** is the Detailed Facility Report REST service (`dfr_rest_services`), which takes a facility ID (`p_id`) directly and returns full compliance/violation history for that single facility — this is the correct replacement call.

**`facilities_by_zip`/`facilities_by_location`/`facilities_by_state`** (which hit `echo_rest_services.get_facilities`) are confirmed correct and live — I got a real (rate-limited) response from that exact URL, confirming the base URL, service name, and `output=JSON` param are current.

**Fix:** replace `violations_for_facility` with a `dfr_rest_services.get_dfr` call (or `get_cases` + `get_qid` if you specifically want enforcement *case* data rather than inspection/violation history — these are different ECHO datasets with different intended uses).

### 🟡 AirNow (`raiz/sources/air_quality.py`) — correct but incomplete

Verified: `Category` is genuinely a nested `{Number, Name}` object as the code assumes, `AQI`/`Latitude`/`Longitude`/`ReportingArea` field names are correct, endpoint returned `401` (auth required) rather than any error about wrong URL/params — this is the expected response shape without a key. The integration is sound.

Gap (not a bug): AirNow returns one row **per pollutant parameter** (O3, PM2.5, PM10, etc.) per call, but the code only ever reads `AQI`/`Category`/`ReportingArea` into an `AirReading` and leaves `pm25`, `pm10`, `ozone`, `no2`, `so2`, `co` at their `0.0` defaults for real (non-mock) data — even though those fields exist on the dataclass and the mock data populates `pm25`. Worth mapping `ParameterName` → the matching field.

### 🟢 PurpleAir, Census, EPA ECHO facility search — sound, currency gaps only

- **PurpleAir v1**: field names (`pm2.5`, `latitude`, `longitude`, `name`) match the documented v1 sensor schema. Endpoint reachable, returned `403` (expected without key).
- **Census ACS**: endpoint/format correct (confirmed live — `missing_key.html` redirect is the standard no-key response for any vintage). But `ACS_YEAR = "2022"` (`config/`... actually `raiz/mapping/demographics.py:172`) is now **two vintages stale**. The Census Bureau released the 2020–2024 ACS 5-year estimates on 2026-01-29 — that's the current vintage. Bump `ACS_YEAR` to `"2024"`.
- **ECHO facility search**: confirmed live and correctly rate-limited (300/hr, 1,500/day — see §2 for why this matters operationally).

### 🟡 SEC EDGAR (`raiz/sources/sec_edgar.py`) — missing a required call, `find()` may not exist as imported

- **Missing `set_identity()`.** SEC EDGAR's fair-access policy requires every request to declare an identity via User-Agent, and `edgartools` enforces this: "the Edgar API will refuse to respond to your request without it." The code never calls `edgar.set_identity(...)` (or sets the `EDGAR_IDENTITY` env var) anywhere. In live mode, every `Company(ticker)` / `get_filings()` call will likely fail. This is a one-line fix but it's the difference between "works" and "403s on every real query."
- **`from edgar import find`** (used in `search_by_facility_owner`) — `find()` as a company-name search does exist in `edgartools`'s current docs, so this is probably fine, but it's worth a smoke test since the library has gone through 5 major version bumps (currently v5.40.x, June 2026) since whenever this integration was last checked against a real install. `edgartools` isn't in a `requirements.txt` (none exists — see §3), so there's no version pin to know what was actually tested.
- The keyword/regex-based disclosure extraction (`ENVIRONMENTAL_KEYWORDS`, `DISCLOSURE_TYPE_PATTERNS`) is a reasonable v1 heuristic given no LLM-extraction step exists yet, but it will produce noisy `dollar_amount` parsing on any filing where a dollar figure and an environmental keyword happen to co-occur in the same paragraph without being causally related (e.g., a paragraph about a facility's *insurance* costs that happens to mention "environmental" in a boilerplate risk-factor list). Not a currency issue, just a precision one worth flagging for Phase 2.

---

## 2. Operational gap the live tests surfaced: no rate-limit handling anywhere

Testing this audit, a handful of manual `curl` calls to ECHO's facility endpoint tripped its stated limit ("300 per hour or 1,500 per day"). `EchoSource.community_report()` calls `violations_for_facility()` **once per facility, sequentially, for up to 50 facilities per zip-code query** — a single community query for a dense industrial zip code could burn 50 requests, and a handful of organizers running queries in the same hour will trip ECHO's throttle. None of `epa_echo.py`, `epa_tri.py`, `air_quality.py`, or `sec_edgar.py` has:
- backoff/retry on 429
- a shared, reused `aiohttp.ClientSession` (currently opens/closes a new session per single HTTP call — works, just wasteful)
- any caching layer

For a tool whose entire value proposition is "community orgs query their zip code," getting throttled by EPA mid-investigation is a real failure mode, not a hypothetical one. Recommend: shared session with connection pooling, exponential backoff on 429/5xx, and a simple on-disk cache (facility lists and TRI releases don't change hour-to-hour).

---

## 3. Dependency & repo hygiene

- **No `requirements.txt`, `pyproject.toml`, or `setup.py` anywhere in the repo.** The README tells users to `pip install aiohttp`, `pip install edgartools`, `pip install geopandas`, `pip install folium` by hand, with no version pins. Given `edgartools` alone has shipped 5 major versions since this was likely written, an unpinned `pip install edgartools` today pulls v5.40+, and nothing in the repo has been checked against it beyond what this audit just did via docs. Add a `requirements.txt` (or `pyproject.toml`) pinning at least `edgartools>=5,<6` and `aiohttp>=3`.
- **`docs/` is an empty directory.** README and `CLAUDE.md` both reference it as containing "Architecture, regulatory notes, org onboarding" — it has zero files. Either populate it or stop referencing it.
- **`raiz/memory/dreamer.py` imports a package that doesn't exist in this environment**: `from kintsugi.cognition.proactive_advisor import ProactiveAdvisor, ActivityRecord, Suggestion`. There's no `kintsugi` package installed, none vendored in `raiz/`, and no test file exercises `dreamer.py` (it's the only module under `raiz/` with zero test coverage). This module is currently dead code that would `ImportError` the instant anything tried to import it. Either vendor/stub the Kintsugi memory dependency or move this file out of the shipped package until the dependency is real.
- **API keys are CLI-only, no `.env` support.** `python -m raiz query ZIP --airnow-key YOUR_KEY` puts secrets in shell history and `ps` output. Cheap fix: read `AIRNOW_API_KEY`/`PURPLEAIR_API_KEY`/`CENSUS_API_KEY` env vars as defaults in `__main__.py`.
- **`--census-key` isn't wired into the CLI at all** — `CommunityQueryEngine` accepts `census_key`, but `raiz/__main__.py`'s `query` subcommand never exposes an argument for it, so there is currently no way to run a non-demo query with a Census API key from the command line (you'd get unauthenticated, low-volume-only Census access).

---

## 4. Strategic positioning: the founding premise has partially been overtaken

`CLAUDE.md` and the README both open with: *"In February 2025, the federal government removed EJSCREEN and CEJST... Raíz rebuilds what was taken."* That was true when written (May 2026 per git log). It's no longer the whole story:

- **Public Environmental Data Partners (PEDP)** — a volunteer coalition of environmental/justice orgs, university researchers, and archivists — restored public access to EJScreen and CEJST within days of removal, and has kept building: **CEJST v2.1 shipped March 2026**, plus FEMA's Future Risk Index, HIFLD Next, EPA EJAM, and an EJ Grants Map. This is independent/unofficial (not a government restoration), but it means "the community has no EJ screening data" is no longer accurate — PEDP's screening.tools/`screening-tools.com` site now serves that role, and there's no indication (per their public site) that they expose a programmatic API for it.

This isn't a reason to abandon anything Raíz does — it's a reason to **reposition, not rebuild**. Raíz's actual differentiation was never "have a screening tool" (PEDP now covers that ground) — it's the things PEDP explicitly isn't doing: live cross-source synthesis into one community report, the permit watchdog, FOIA automation, and corporate-accountability linking (SEC filings → facility → neighborhood). Recommend reframing the README's opening pitch around that, and considering PEDP's restored CEJST/EJScreen data as an *additional* Tier-1 source Raíz pulls from (they preserve the government's original disadvantaged-community designations, which Raíz's own demographic analysis currently reconstructs from raw Census ACS instead) rather than a tool Raíz is racing to replace.

---

## 5. What's solid (worth saying explicitly, not just bugs)

- Test suite: 163/163 passing, well-organized by module, exercises the *domain logic* (risk scoring, disparity math, FOIA deadline tracking, drift detection, EFE weighting) thoroughly — the gap is entirely in "does the live-mode network code match the live API," not in application logic.
- `epa_echo.py` facility search, `air_quality.py`, `mapping/demographics.py` query construction, `investigation/foia.py`, and the Kintsugi engine layer (`efe.py`, `drift.py`, `evolution.py`, `staged_pipeline.py`, `security/skill_provenance.py`) are all clean, well-documented, and — where checked — correct against current specs/APIs.
- The dry-run/live split is a genuinely good design for a tool meant to be demoed to non-technical community organizers before they commit to getting API keys.
- `DisparityAnalysis` and the risk-scoring logic in `community/query.py` do exactly what the README's pitch promises — the "environmental racism" finding language is generated from real ratios, not canned copy.

---

## 6. Prioritized fix list

1. **Fix TRI table/field mapping** (§1) — currently the single biggest gap between promise and reality for this tool.
2. **Fix or replace the ECHO violation-detail call** (`dfr_rest_services` instead of the current `cwa_rest_services.get_qid`) (§1).
3. **Add `edgar.set_identity()`** — one line, currently blocks all live SEC EDGAR calls (§1).
4. **Add a `requirements.txt`** with pinned versions, including `edgartools` (§3).
5. **Add rate-limit backoff + a shared `aiohttp.ClientSession`** for ECHO especially (§2) — this is the one that will bite real users first, since it's not a "does the query return right," it's "does the tool stay usable after the third query this hour."
6. **Bump `ACS_YEAR` to `"2024"`** (§1) — one-line fix, five-minute confirmation.
7. **Wire `--census-key` into the CLI** and read all three API keys from env vars as fallback (§3).
8. **Decide dreamer.py's fate** — vendor the `kintsugi` dependency, stub it, or pull the file until it's real (§3).
9. **Reframe the README/CLAUDE.md pitch** away from "rebuilding what was removed" toward Raíz's actual differentiation, and evaluate PEDP's restored CEJST data as an additional source (§4).
