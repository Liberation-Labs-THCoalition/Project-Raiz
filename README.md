# Raíz — The Roots See What the Surface Hides

Raíz is an AI environmental justice agent. It connects fragmented environmental data into one picture and puts it in the hands of the communities that need it most.

One zip code. One command. Everything you need to fight back.

---

## Why Raíz Exists

In February 2025, the federal government removed EJSCREEN and CEJST — the two primary environmental justice screening tools. Communities that relied on these tools for permit fights and regulatory comments lost their data overnight.

Meanwhile:
- EPA enforcement actions continue to decline
- Self-reporting is the norm — polluters grade their own homework
- New facility permits are filed in state databases with minimal public notice
- Corporate environmental liabilities are buried in SEC filings nobody reads
- EPA air quality monitors are sparse in low-income neighborhoods
- The communities breathing the worst air have the least data

Raíz rebuilds what was taken and adds what never existed: investigation, prediction, and action — all in one tool.

---

## Try It Right Now

```bash
git clone https://github.com/Liberation-Labs-THCoalition/Project-Raiz.git
cd Project-Raiz
python -m raiz query 62701 --demo --actions
```

You'll see a complete environmental report: facilities, violations, toxic releases, air quality, demographics, corporate accountability, and suggested actions. All from one zip code.

---

## What Raíz Finds

When you query a zip code, Raíz pulls from six data sources simultaneously:

### Facilities and Violations (EPA ECHO)
Every regulated facility — Clean Air Act, Clean Water Act, RCRA. Every inspection, violation, and enforcement action. Whether anyone was actually penalized.

### Toxic Chemical Releases (EPA TRI)
Every pound of toxic chemicals released into air, water, or land. Which ones are known carcinogens. Who's releasing them.

### Air Quality (AirNow + PurpleAir)
Official EPA monitors *and* community sensors. When the nearest EPA monitor is 10 miles away but a PurpleAir sensor is on the next block, Raíz tells you — and flags the monitoring gap.

### Demographics (US Census)
Race, income, poverty rate, children under 5, adults over 65, health insurance coverage. Environmental justice indicators auto-detected: majority-minority, low-income, high child population.

### Corporate Accountability (SEC EDGAR)
The parent company's 10-K and 10-Q filings. Remediation reserves ("we know we're contaminating and set aside $4.2 million for cleanup"). Consent decrees. Superfund designations. Disclosed penalties.

### Risk Score
All of the above combined into a 0-10 community environmental risk score. Violations + zero penalties = enforcement gap. Carcinogens + majority-minority community + children = the number that makes legislators uncomfortable.

---

## The Disparity Analysis

Raíz doesn't just report what's happening in one community. It compares two communities side by side:

```
Community A: 62701
  74% people of color | Median income: $28,400

Community B: 62704
  12% people of color | Median income: $78,500

Environmental Burden Comparison:
  Violations (3yr)         : A=       47  B=        2  ratio=23.5x  DISPARITY
  Toxic air releases (lbs) : A=   50,000  B=    1,200  ratio=41.7x  DISPARITY
  Carcinogens released     : A=        5  B=        0  ratio=inf    DISPARITY

FINDING: The community with 74% people of color bears 41.6x the
environmental burden of the community with 12% people of color.
This pattern is consistent with environmental racism.
```

Numbers that make the invisible visible.

---

## The Permit Watchdog

Raíz watches for new environmental permits near communities you care about. When one appears:

1. **Catches it** — new permit application detected within 3 miles
2. **Investigates** — pulls the applicant's violation history across all their facilities
3. **Maps the impact** — demographics, existing burden, nearby schools
4. **Follows the money** — checks the parent company's SEC filings
5. **Generates the response** — a ready-to-submit public comment with every damning fact cited
6. **Tracks the clock** — comment deadline countdown

The community doesn't have to find the permit. The permit finds the community.

---

## FOIA Automation

When Raíz finds violations without inspection records, or permits without public documentation, it generates Freedom of Information Act requests:

- Ready-to-sign letter with all legally required elements
- Targets the correct agency (state or federal)
- Requests fee waiver (public interest standard)
- Tracks the legal response deadline
- Flags stonewalling when agencies don't respond on time

The human signs the letter. Raíz remembers the deadline.

---

## Getting Started

### For Community Organizations

```bash
# Install
git clone https://github.com/Liberation-Labs-THCoalition/Project-Raiz.git
cd Project-Raiz
pip install aiohttp

# Query your community (demo mode — no API keys needed)
python -m raiz query YOUR_ZIP_CODE --demo --actions

# With real data (free API keys)
python -m raiz query YOUR_ZIP_CODE --airnow-key YOUR_KEY --actions
```

### API Keys (all free)

| Source | Key Required? | Where to Get It |
|--------|:------------:|-----------------|
| EPA ECHO | No | Open API |
| EPA TRI | No | Open API |
| AirNow | Yes (free) | [docs.airnowapi.org](https://docs.airnowapi.org) |
| PurpleAir | Yes (free) | [community.purpleair.com](https://community.purpleair.com) |
| Census | Optional | [api.census.gov](https://api.census.gov/data/key_signup.html) |
| SEC EDGAR | No | Open API (install `edgartools`) |

### Optional Dependencies

```bash
pip install edgartools    # SEC corporate filing search
pip install geopandas     # Geographic analysis and mapping
pip install folium        # Interactive maps
```

---

## What's Next

Raíz Phase 1 is a query tool — you ask, it answers. Phase 2 makes it an agent that watches while you sleep:

- **State permit scrapers** — automated monitoring of all 50 state environmental permit databases
- **Violation prediction** — ML model trained on ECHO history to predict which facilities will violate next
- **Alert network** — push notifications to subscribed organizations when something changes
- **Temporal tracking** — trend analysis for legal arguments ("3 consecutive years of escalating violations")
- **Web dashboard** — browser-based interface for non-technical users
- **Satellite integration** — illegal dumping and emission detection from imagery

---

## Privacy and Ethics

- **Community sovereignty** — affected communities lead, Raíz supports
- **Data transparency** — all findings are public, all methods are auditable
- **No corporate greenwashing partnerships** — Raíz serves communities, not polluters
- **Environmental racism is real and must be named explicitly**
- **Open source** — the tools to defend your air and water should be free
- **Verify before alerting** — false alarms erode trust

---

## Built With

Raíz stands on the shoulders of [EDGI](https://github.com/edgi-govdata-archiving) (Environmental Data & Governance Initiative), whose open source tools for EPA data access made this possible. Built on the [Kintsugi Engine](https://github.com/Liberation-Labs-THCoalition/Project-Kintsugi) by [Liberation Labs / TH Coalition](https://github.com/Liberation-Labs-THCoalition).

---

## About the Name

*Raíz* is Spanish for *root*. Roots hold the soil together, connect to underground networks, and draw up what's hidden below the surface. Environmental justice requires getting to the root — systemic, structural, underground. The name honors the Latino communities disproportionately affected by environmental injustice.

*The roots see what the surface hides.*
