# Dashboard requirements: Purchase-to-Pay Process Intelligence

Version 1.0, 2026-11-13. Status: draft for build. User stories: [`user_stories.md`](user_stories.md). KPI definitions: [`kpis/catalogue.md`](../kpis/catalogue.md). Data model: [`model/README.md`](../model/README.md).

## 1. Purpose

Give the procurement and accounts-payable owners one place to see how long purchase-order items take from order to payment, where the time goes, how often the three-way-match control is broken, and how much rework occurs, so that they can pick the process change to make first. The dashboard answers brief questions 1 to 4; question 5 (redesign impact) is answered by the simulation in `impact/` and only linked from here.

## 2. Users

| Role | Main question | Uses mostly |
| --- | --- | --- |
| Head of Procurement Operations (process owner) | Are we getting faster and more compliant, and what should change first? | Overview, Cycle time |
| Accounts Payable lead | Why do invoices wait after receipt; how many are blocked or booked early? | Cycle time, Compliance, Rework |
| Purchasing lead | Which vendors and spend areas cause changes and early invoices? | Compliance, Rework |
| Warehouse lead | Are goods receipts booked late, so invoices arrive first? | Compliance |
| Process analyst (me, the builder) | Is the data trustworthy; what does a single item look like? | Process, Item detail, Data notes |

## 3. Scope

**In scope:** the 8 KPIs of the catalogue with trends and breakdowns; phase durations; compliance and rework drill-downs to item lists; process variants and conformance results; a single-item timeline; data limitations shown in the app.

**Out of scope:** writing back to any system; alerts or e-mail; user accounts and row-level security; live data (the log is a fixed extract); financial value of delays; the to-be simulation itself (linked only).

## 4. Data

- **Source:** `data/warehouse/p2p.duckdb`, built by `make warehouse`, opened read-only. Main objects: `v_kpi`, `v_item`, `fact_event`, `dim_*`.
- **Refresh:** none at run time. The data is a fixed 2018-2020 extract; rebuilding the warehouse is the refresh.
- **Missing today:** variant and conformance results live in `mining/outputs/conformance_invoice_before_gr.csv`, not in the warehouse. They must be loaded as a table (e.g. `fact_variant`) before the Process page is built (see DR-6).

### Data rules

| ID | Rule |
| --- | --- |
| DR-1 | Time and clearing KPIs (K1 to K3, K6 to K8) use only items in the cohort (`in_cohort`, POs created January to July 2018). Clearing is cut off in January 2019, so later POs would look faster than they are. |
| DR-2 | Compliance KPIs (K4, K5) default to the cohort for consistency, with an option to show all items, because they do not depend on clearing. |
| DR-3 | Events with `ts_suspect = true` are excluded from all durations (already applied in `fact_item`). |
| DR-4 | Any group (vendor, spend area, month) with fewer than 30 items in the current population shows "n < 30" instead of a value and is left out of rankings. (459 of 1,728 cohort vendors have 30 or more items; they cover 94.6% of items.) |
| DR-5 | Every number shown matches `v_kpi` or a query on `v_item` with the same filters; nothing is computed in the front end from different rules. |
| DR-6 | Variant and conformance figures come from the conformance run on the main category (91.6% of finished cases fit), loaded into the warehouse with the date of the run. |

## 5. Global layout and filters

- Left sidebar: page navigation and filters. The main area holds the page.
- **Filters (FR-1):** PO month (range within January to July 2018), item category (default: all categories, where K1 to K4, phases and variants use the main category "3-way match, invoice before GR"), spend area, vendor (searchable, vendors with 30 or more cohort items). Filters apply to every page and are shown as a one-line summary at the top of each page. *Changed during the build: the default was the main category, but then K5 to K8 would no longer match the catalogue baselines (DR-5).*
- Company is not offered as a filter: one company code holds 99.8% of cohort items.
- A fixed banner on every page: "POs created Jan-Jul 2018. Clearing data ends January 2019. Associations, not causes." with a link to the Data notes page.

## 6. Pages and functional requirements

Priority uses MoSCoW: **M**ust, **S**hould, **C**ould.

### 6.1 Overview

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-2 | Show a tile for each KPI K1a to K8 with the current value under the filters, the target from the catalogue, and the gap to target, coloured by whether the target is met. | M |
| FR-3 | Each tile shows the monthly values as a small trend line (7 months). | M |
| FR-4 | Hovering or clicking a tile shows its definition, population and caveat from the catalogue. | S |
| FR-5 | Show the three headline findings from the README as text with their numbers, recomputed under the current filters. | C |

### 6.2 Cycle time

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-6 | Show the phases of a cleared item (PO to goods receipt, goods receipt to invoice receipt, invoice receipt to clearing) as medians in days, with P90, so the user sees that most time is after invoice receipt (main category: about 10, 8 and 46 days). Note that phase medians do not add up to the total median. | M |
| FR-7 | Show the distribution of PO-to-clearing days (histogram or box plot) per item category. | M |
| FR-8 | Rank spend areas and vendors by median cycle time with item counts, applying DR-4. | M |
| FR-9 | Allow switching the measure between median and P90. | S |

### 6.3 Compliance

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-10 | Show K4 (invoice receipt before goods receipt) and K5 (vendor invoice before PO) with monthly trend. | M |
| FR-11 | Break K4 and K5 down by vendor and spend area, ranked by rate and by item count, applying DR-4. | M |
| FR-12 | Show the list of items behind any bar or table row (case ID, vendor, spend area, PO date, the two event dates, gap in days), downloadable as CSV. | M |
| FR-13 | Show how many days the invoice receipt came before the goods receipt (distribution), to separate same-week bookings from long gaps. | S |

### 6.4 Rework

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-14 | Show K6 (touchless) and K7 (rework per 100 items) with monthly trend. | M |
| FR-15 | Show each rework type (Change Price, Change Quantity, Cancel Goods Receipt, Cancel Invoice Receipt, Remove Payment Block, Set Payment Block): items affected, share, median cycle time with and without, and the gap in days. Label the gap "associated with", never "caused". | M |
| FR-16 | Show K8 (payment-block removal) by vendor and spend area, applying DR-4. | S |
| FR-17 | Compare touchless and rework items on the cycle-time distribution in one chart. | S |

### 6.5 Process

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-18 | Show the top 20 variants of the selected category with case count, share and cumulative share. | S |
| FR-19 | Show conformance results of the as-is model: fitness on finished cases, the deviation groups (repeated activity, invoice before PO, other) and the as-is BPMN preview image. | S |
| FR-20 | Show a directly-follows graph of the selected population with a frequency threshold. | C |

### 6.6 Item detail

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-21 | Given a case ID (typed or clicked from any item list), show its attributes and an ordered event timeline (activity, timestamp, user type, lane), with suspect and date-only events marked. | M |
| FR-22 | Show the item's milestone dates, durations, flags and status from `fact_item`. | M |

### 6.7 Data notes

| ID | Requirement | Priority |
| --- | --- | --- |
| FR-23 | List the data limits (clearing cut-off, cohort, date-only timestamps, suspect dates, rarely logged payment-block setting, anonymised data, third-party copy of the data) with links to the notes, and the dataset citation. | M |
| FR-24 | Show the warehouse build time and row counts so the user knows which build is shown. | S |

## 7. Non-functional requirements

| ID | Requirement |
| --- | --- |
| NFR-1 | Runs locally with `uv run streamlit run app/app.py` after `make ingest warehouse`; no internet connection or external service needed. |
| NFR-2 | Any page with any filter combination renders in under 3 seconds on a normal laptop (the warehouse is about 1.6 million events). Queries are cached per filter set. |
| NFR-3 | Read-only: the app opens the DuckDB file read-only and never writes to `data/`. |
| NFR-4 | Charts use one consistent palette, are readable in light and dark themes, and do not use colour as the only signal (target met / missed also shown by an icon or text). |
| NFR-5 | Every chart has a title that states what it shows and an axis or label with units (days, share, per 100 items). |
| NFR-6 | Code is tested: query functions for each page have pytest tests that check their numbers against `v_kpi` or the notes (DR-5). `make lint` and `make test` pass. |
| NFR-7 | Built with Streamlit and DuckDB as in the project stack; pm4py is used only offline (AGPL v3 note in the README). |

## 8. Traceability

| Brief question | KPIs | Pages | Stories |
| --- | --- | --- | --- |
| 1 Time | K1a, K1b, K2, K3 | Overview, Cycle time | US-1, US-2, US-3, US-4 |
| 2 Compliance | K4, K5 | Overview, Compliance | US-5, US-6, US-7 |
| 3 Rework | K7, K8 | Rework | US-8, US-9, US-10 |
| 4 Touchless | K6 | Overview, Rework | US-8 |
| 5 Redesign | (simulation) | link to `impact/` | US-14 |
| Trust in data | none | Process, Item detail, Data notes | US-11, US-12, US-13 |

## 9. Assumptions and open points

- The roles and their questions are inferred from the brief; there is no real stakeholder to interview. The targets are the catalogue's assumed targets.
- Vendor and user names are anonymised, so the dashboard can show IDs only.
- The data is a one-off extract, so "monthly trend" covers seven months only.
- The Process page depends on loading conformance results into the warehouse first (DR-6).
- Spend area looks like a strong driver of cycle time (cleared main-category items: median about 100 days for Packaging against 56 for Sales). This is not analysed yet; FR-8 makes it visible.

## 10. Build status (2026-11-13)

Built in `app/app.py` on the query layer `src/p2p/queries.py`; run with `make app`. Tests: `tests/test_queries.py` (numbers against `v_kpi` and the notes) and `tests/test_app.py` (every page renders, KPI tiles, category filter).

- Done: FR-1 to FR-19, FR-21 to FR-24, DR-1 to DR-6, NFR-1 to NFR-7, and US-14 (Overview points to `impact/README.md` once the simulation exists).
- Not done: FR-20 (directly-follows graph, Could).
- Deviations: FR-1 default category (see section 5); compliance and rework item lists open Item detail through row selection and a button rather than a click on a chart bar (FR-12).
