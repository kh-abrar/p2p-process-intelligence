# Purchase-to-Pay Process Intelligence

Where does a large company's purchase-to-payment process lose time and break its own rules, and what redesign would fix it, by how much? This project answers that with process mining on a real purchase-order event log, from as-is models to a simulated to-be process.

**Status: in progress (started November 2026).** Headline findings will be added here once the conformance and performance analysis is complete.

## Data

[BPI Challenge 2019](https://icpmconference.org/2019/?p=302): purchase-order handling data from a Dutch multinational in coatings and paints. 1,595,923 events, 251,734 cases, 42 activities. A case is one purchase-order line item. Items follow one of four flows: 3-way match with invoice before goods receipt (88% of cases), 3-way match with invoice after goods receipt, 2-way match, and consignment.

- Original dataset: van Dongen, B.F. (2019). BPI Challenge 2019. 4TU.ResearchData. [doi:10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1](https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1)
- Copy used here: a CSV conversion of the log, obtained from the `jadzoghaib/processlens` GitHub release `dataset-v1` because the 4TU site was unreachable during setup. Checksum and details are in [`data/SOURCE.md`](data/SOURCE.md). The data itself is not in this repository.

Known data limits (details in [`mining/notes/`](mining/notes/)): three activities carry date-only timestamps, 100 events have impossible dates and are flagged, setting a payment block is rarely logged, and some cases have no clearing event.

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
| `bpmn/` | As-is BPMN models (Camunda Modeler), then a to-be model | As-is for main category done |
| `mining/` | Discovery, conformance, variants, throughput, rework | Exploration and variants done |
| `model/` | ER diagram and DuckDB star schema, with tests | Planned |
| `kpis/` | Catalogue of 8 KPIs | Planned |
| `requirements/` | Dashboard requirements spec and user stories | Planned |
| `app/` | Streamlit dashboard | Planned |
| `impact/` | SimPy what-if simulation | Planned |
| `memo.pdf` | Two-page executive memo | Planned |

## Reproduce

Requires Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync
# download BPI_Challenge_2019.csv.gz from the release named in data/SOURCE.md
# and place it in data/raw/ (check its SHA-256 against data/SOURCE.md)
make ingest   # CSV -> data/interim/events.parquet -> events_clean.parquet
make test
```

## Stack

Python 3.12, uv, pm4py, polars, DuckDB, SimPy, Streamlit, Camunda Modeler, pytest, ruff.

## References

- BPI Challenge 2019 page: https://icpmconference.org/2019/?p=302
- Gutermuth, Lahann, Rehse, Scheid, Schuhmann, Stephan, Fettke. *Efficient and Compliant Purchase Order Handling: A Contribution to BPI Challenge 2019.* doi:10.22028/D291-34142

Further published challenge reports will be added when my findings are compared against them.

## Licence

See [`LICENSE`](LICENSE). Note that this project depends on [pm4py](https://pm4py.fit.fraunhofer.de/), which is licensed under AGPL-3.0.