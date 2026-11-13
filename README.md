# Purchase-to-Pay Process Intelligence

Where does a large company's purchase-to-payment process lose time and break its own rules, and what redesign would fix it, by how much? This project answers that with process mining on a real purchase-order event log, from as-is models to a simulated to-be process.

## Findings

All figures use POs created January to July 2018 (see data limits below). Findings 1 and 3 cover the main category, "3-way match, invoice before GR"; finding 2 covers cleared items in both 3-way categories.

1. **Invoices recorded before the goods arrive: 9.1%.** 11,815 of 129,244 items had the invoice receipt booked before the goods receipt, which weakens the three-way-match control.
2. **Rework adds about 18 days.** Cleared items with any rework take a median of 91.0 days from PO to clearing, against 73.4 days for touchless items (+17.6 days). 36% of cleared items need some rework. Quantity changes go with +21.8 days; payment-block removal, on about a quarter of items, with +14.0 days. These are associations, not proven causes.
3. **Order to payment takes a median of 79.3 days (P90 129.1).** 46.1 of those days (58%) come after the invoice receipt is recorded. Payment terms are a likely reason, but the log has no payment-term field, so this is a hypothesis.

**Redesign (simulated):** preventing half of the payment blocks would cut the median by about 1.3 days (95% interval 1.0 to 1.9) and raise touchless items by 11 points. Preventing half of the order-side rework as well cuts 2.4 days (2.0 to 3.0). The time gains are small because payment follows a due date counted from the vendor invoice; the main benefit is less rework and a closed control gap. Details: [`impact/README.md`](impact/README.md).

Details: [`mining/notes/04-cohort-findings.md`](mining/notes/04-cohort-findings.md) and [`mining/notes/05-conformance.md`](mining/notes/05-conformance.md).

**Status: complete (November 2026).** Executive summary for the process owner: [`memo.pdf`](memo.pdf). Comparison with the published challenge reports: [note 06](mining/notes/06-comparison-with-published-reports.md).

## Data

[BPI Challenge 2019](https://icpmconference.org/2019/?p=302): purchase-order handling data from a Dutch multinational in coatings and paints. 1,595,923 events, 251,734 cases, 42 activities. A case is one purchase-order line item. Items follow one of four flows: 3-way match with invoice before goods receipt (88% of cases), 3-way match with invoice after goods receipt, 2-way match, and consignment.

- Original dataset: van Dongen, B.F. (2019). BPI Challenge 2019. 4TU.ResearchData. [doi:10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1](https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1)
- Copy used here: a third-party CSV conversion of the log, obtained from the `jadzoghaib/processlens` GitHub release `dataset-v1` because data.4tu.nl timed out during setup. Checksum and details are in [`data/SOURCE.md`](data/SOURCE.md). The data itself is not in this repository.

Known data limits (details in [`mining/notes/`](mining/notes/)):

- **Clearing is cut off.** Clearing and invoice-receipt events stop in January 2019, although other events run to April 2020. Items ordered late in 2018 had no time to clear, so cycle-time, clearing and rework figures use a cohort of POs created January to July 2018 (155,761 items). Compliance measures that do not need clearing use all items.
- Three activities (vendor invoice, vendor debit memo, purchase requisition) carry date-only timestamps, so durations touching them are in days and same-day ordering needs a tie-break.
- 100 events have impossible dates (e.g. 1948) and are flagged and excluded from durations.
- Setting a payment block is rarely logged, so block rates rest on removals.
- In "invoice after GR", 14.1% of cohort items were received but never invoiced in the log. The share rises for later months (12.2% to 19.3%), so it is partly truncation and is not counted as a finding.

## Questions

1. How long does an item take from PO creation to cleared invoice, per category (median and 90th percentile), and where does the waiting happen?
2. How often is an invoice received before the goods receipt, or created before the PO exists?
3. How much rework (price and quantity changes, cancellations, payment blocks) occurs, and how much time does it add?
4. What share of items run from order to payment untouched?
5. Which process change would help most, and by how much (simulated, with an interval)?

The full problem statement is in [`brief/brief.md`](brief/brief.md).

## Project layout and status

| Folder | Content | Status |
| --- | --- | --- |
| `brief/` | One-page problem statement | Done |
| `bpmn/` | As-is and to-be BPMN models of the main category (Camunda Modeler), with PNG previews | Done |
| `mining/` | Exploration, variants, censoring, cohort metrics, conformance; findings in [`mining/notes/`](mining/notes/) | Done |
| `model/` | ER diagram and DuckDB star schema, with tests | Done ([`model/README.md`](model/README.md)) |
| `kpis/` | Catalogue of 8 KPIs with baselines, owners and targets | Done ([`kpis/catalogue.md`](kpis/catalogue.md)) |
| `requirements/` | Dashboard requirements spec and user stories | Done ([spec](requirements/dashboard_requirements.md), [stories](requirements/user_stories.md)) |
| `app/` | Streamlit dashboard on the warehouse | Done: 7 pages (`make app`) |
| `src/p2p/` | Ingest, cleaning, KPIs, warehouse build, dashboard queries, simulation | Done, tested in `tests/` |
| `impact/` | To-be BPMN and SimPy what-if simulation | Done ([`impact/README.md`](impact/README.md)) |
| `memo.pdf` | Two-page executive memo (source: `memo/memo.html`) | Done ([`memo.pdf`](memo.pdf)) |

## Progress

- **Week 1 (done):** ingest and cleaning with data tests, exploration, variant analysis, first as-is BPMN for the main category.
- **Week 2 (done):** found the January 2019 clearing cut-off and moved time metrics to a January to July 2018 cohort; cycle time per category, invoice-before-goods-receipt rate, rework gaps and touchless share; conformance checking of the as-is model (91.6% of finished cases fit after a same-day tie-break fix and allowing deletion after order confirmation).
- **Week 3 (done):**
  - KPI catalogue done: 8 KPIs with formulas, owners, cohort baselines, monthly ranges and assumed targets, computed by `src/p2p/kpis.py` and pinned by tests.
  - DuckDB star schema done: 2 fact tables (events, items) and 6 dimensions, KPI views in SQL that match the Python baselines, ER diagram in `model/README.md`.
  - Dashboard requirements done: users, data rules, 24 functional and 7 non-functional requirements, 14 user stories with acceptance criteria.
  - Streamlit dashboard done: Overview, Cycle time, Compliance, Rework, Process, Item detail and Data notes pages on the warehouse, with the query layer and every page tested.
  - To-be BPMN and SimPy simulation done: preventing half of payment blocks cuts the median by 1.3 days (95% interval 1.0 to 1.9) and lifts touchless items by 11 points; both changes together cut 2.4 days (2.0 to 3.0). Gains are small because payment follows a due date counted from the vendor invoice.
  - Executive memo done: two pages for the process owner with findings, three recommended changes with simulated effects, limits and four decisions requested.
  - Compared with five published challenge reports (both winners): headline numbers agree; this project differs in handling the January 2019 clearing cut-off with a cohort and in simulating the redesign (note 06).
- **Possible extensions:** compliance per item type and amount matching between invoice and goods receipt (as in two of the published reports); payment-term data to test the payment-timing explanation; staffing data to add Accounts Payable capacity to the simulation.

## Reproduce

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
# download BPI_Challenge_2019.csv.gz from the release named in data/SOURCE.md
# and place it in data/raw/ (check its SHA-256 against data/SOURCE.md)
make all        # the whole pipeline below, in order (about 6 minutes)
make app        # dashboard at http://localhost:8501
make test lint  # 54 tests (data tests skip without the data) and ruff
```

The pipeline steps can also be run one by one:

| Target | Does | Output (git-ignored) |
| --- | --- | --- |
| `make ingest` | CSV to parquet, cleaning and flags | `data/interim/` |
| `make mining` | Analysis scripts, including conformance | `mining/outputs/` |
| `make kpis` | KPI baselines | `kpis/outputs/` |
| `make warehouse` | DuckDB star schema (needs `make mining` for conformance results) | `data/warehouse/p2p.duckdb` |
| `make simulate` | To-be what-if simulation (about 3 minutes) | `impact/outputs/` |

The memo PDF is printed from `memo/memo.html` with headless Chrome (A4, no header or footer); in Git Bash on Windows:

```bash
"/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --no-pdf-header-footer --print-to-pdf="$(pwd -W)/memo.pdf" "file:///$(pwd -W)/memo/memo.html"
```

## Stack

Python 3.12, uv, pm4py, polars, DuckDB, SimPy, Streamlit, Plotly, Camunda Modeler / bpmn-js, pytest, ruff.

## References

- van Dongen, B.F. (2019). BPI Challenge 2019. 4TU.ResearchData. doi:10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1 (data used here from a third-party CSV mirror because data.4tu.nl timed out; see [`data/SOURCE.md`](data/SOURCE.md))
- BPI Challenge 2019 page: https://icpmconference.org/2019/?p=302
- Gutermuth, Lahann, Rehse, Scheid, Schuhmann, Stephan, Fettke. *Efficient and Compliant Purchase Order Handling: A Contribution to BPI Challenge 2019.* doi:10.22028/D291-34142
- Diba, Remy, Pufahl. *Compliance and Performance Analysis of Procurement Processes Using Process Mining.* BPI Challenge 2019 (overall winner).
- Meyer zu Wickern, Juluru, Roy, Nguyen, Vu. *Analysis and prediction of purchasing compliance using process mining.* BPI Challenge 2019 (student winner).
- van Dyk, Aklecha, Kennes, Ramezani. *Dissecting the Purchase-to-Pay Process: An exercise in Process Mining.* BPI Challenge 2019.
- Porter, Masse, Visatemongkolchai, Seneviratne, Deokule, Hartman. *Balancing Efficiency and Risk in Procure to Pay.* BPI Challenge 2019.

The challenge reports are linked from the challenge page. My findings agree with them within a few days or points; the comparison and what this project adds (a censoring-aware cohort and a what-if simulation) are in [`mining/notes/06-comparison-with-published-reports.md`](mining/notes/06-comparison-with-published-reports.md).

## Licence

See [`LICENSE`](LICENSE) for this repository's own code. It depends on [pm4py](https://pm4py.fit.fraunhofer.de/), which is licensed under the GNU AGPL v3. The pm4py package is not included here; it is installed by `uv sync`. Anyone redistributing or offering this project as a network service together with pm4py should check the AGPL v3 terms.