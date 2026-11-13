# Purchase-to-Pay Process Intelligence

Where does a large company's purchase-to-payment process lose time and break its own rules, and what redesign would fix it, by how much? This project answers that with process mining on a real purchase-order event log, from as-is models to a simulated to-be process.

## Findings so far

All figures use POs created January to July 2018 (see data limits below). Findings 1 and 3 cover the main category, "3-way match, invoice before GR"; finding 2 covers cleared items in both 3-way categories.

1. **Invoices recorded before the goods arrive: 9.1%.** 11,815 of 129,244 items had the invoice receipt booked before the goods receipt, which weakens the three-way-match control.
2. **Rework adds about 18 days.** Cleared items with any rework take a median of 91.0 days from PO to clearing, against 73.4 days for touchless items (+17.6 days). 36% of cleared items need some rework. Quantity changes go with +21.8 days; payment-block removal, on about a quarter of items, with +14.0 days. These are associations, not proven causes.
3. **Order to payment takes a median of 79.3 days (P90 129.1).** 46.1 of those days (58%) come after the invoice receipt is recorded, Payment terms are a likely reason, but the log has no payment-term field, so this is a hypothesis.

Details: [`mining/notes/04-cohort-findings.md`](mining/notes/04-cohort-findings.md) and [`mining/notes/05-conformance.md`](mining/notes/05-conformance.md).

**Status: in progress (started November 2026).** See [Progress](#progress).

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
| `bpmn/` | As-is BPMN models (Camunda Modeler), then a to-be model | As-is for main category done, refined in week 2 |
| `mining/` | Discovery, conformance, variants, throughput, rework | Week 2 done: censoring, cohort metrics, conformance |
| `model/` | ER diagram and DuckDB star schema, with tests | Planned |
| `kpis/` | Catalogue of 8 KPIs | Planned |
| `requirements/` | Dashboard requirements spec and user stories | Planned |
| `app/` | Streamlit dashboard | Planned |
| `impact/` | SimPy what-if simulation | Planned |
| `memo.pdf` | Two-page executive memo | Planned |

## Progress

- **Week 1 (done):** ingest and cleaning with data tests, exploration, variant analysis, first as-is BPMN for the main category.
- **Week 2 (done):** found the January 2019 clearing cut-off and moved time metrics to a January to July 2018 cohort; cycle time per category, invoice-before-goods-receipt rate, rework gaps and touchless share; conformance checking of the as-is model (91.6% of finished cases fit after a same-day tie-break fix and allowing deletion after order confirmation).
- **Next:** KPI catalogue, DuckDB star schema, dashboard requirements, then the to-be simulation.

## Reproduce

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
# download BPI_Challenge_2019.csv.gz from the release named in data/SOURCE.md
# and place it in data/raw/ (check its SHA-256 against data/SOURCE.md)
make ingest   # CSV -> data/interim/events.parquet -> events_clean.parquet
make test
make mining   # analysis scripts; console output saved under mining/outputs/
```

## Stack

Python 3.12, uv, pm4py, polars, DuckDB, SimPy, Streamlit, Camunda Modeler, pytest, ruff.

## References

- van Dongen, B.F. (2019). BPI Challenge 2019. 4TU.ResearchData. doi:10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1 (data used here from a third-party CSV mirror because data.4tu.nl timed out; see [`data/SOURCE.md`](data/SOURCE.md))
- BPI Challenge 2019 page: https://icpmconference.org/2019/?p=302
- Gutermuth, Lahann, Rehse, Scheid, Schuhmann, Stephan, Fettke. *Efficient and Compliant Purchase Order Handling: A Contribution to BPI Challenge 2019.* doi:10.22028/D291-34142

Further published challenge reports will be added when my findings are compared against them.

## Licence

See [`LICENSE`](LICENSE) for this repository's own code. It depends on [pm4py](https://pm4py.fit.fraunhofer.de/), which is licensed under the GNU AGPL v3. The pm4py package is not included here; it is installed by `uv sync`. Anyone redistributing or offering this project as a network service together with pm4py should check the AGPL v3 terms.