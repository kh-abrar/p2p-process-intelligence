# KPI catalogue

Date: 2026-11-13. Baselines computed by `src/p2p/kpis.py` (`make kpis`), written to `kpis/outputs/kpi_baselines.csv` and `kpis/outputs/kpi_monthly.csv` (git-ignored, rebuildable). Tests in `tests/test_kpis.py` pin the baselines.

## Conventions

- **Population:** the cohort of POs created January to July 2018 (155,761 items). Clearing and invoice-receipt events stop in January 2019, so later POs would bias time and clearing KPIs (see [`mining/notes/03-censoring.md`](../mining/notes/03-censoring.md)).
- **Unit:** one PO line item (case). Events with `ts_suspect = true` are excluded.
- **Timestamps:** the first occurrence of each activity per item. Durations are in days.
- **Main category:** "3-way match, invoice before GR" (88% of cases). "3-way" means both 3-way categories.
- **Monthly values** are per PO creation month and feed the dashboard trend lines.
- **Owners** are roles, since the data is anonymised. The process owner is the Head of Procurement Operations (see the brief).
- **Targets are assumptions.** The log comes with no policy or agreed targets. Each target below is derived from the data (touchless items or the best cohort month) and is meant as a starting point to agree with the owner.

## Summary

| ID | KPI | Brief question | Baseline | Monthly range | Target (assumed) | Owner |
| --- | --- | --- | --- | --- | --- | --- |
| K1a | Cycle time PO to clearing, median | 1 Time | 79.3 d | 77.3 to 83.2 | ≤ 73 d | Head of Procurement Ops |
| K1b | Cycle time PO to clearing, P90 | 1 Time | 129.1 d | 123.0 to 136.1 | ≤ 122 d | Head of Procurement Ops |
| K2 | Wait from invoice receipt to clearing, median | 1 Time | 46.1 d | 41.2 to 50.1 | ≤ 41 d | Accounts Payable lead |
| K3 | Clearing rate | 1 Time | 93.8% | 92.3% to 94.6% | ≥ 94.5% | Accounts Payable lead |
| K4 | Invoice receipt before goods receipt rate | 2 Compliance | 9.1% | 5.5% to 13.2% | ≤ 5.5% | AP lead with Warehouse lead |
| K5 | Vendor invoice before PO rate | 2 Compliance | 1.7% | 1.5% to 1.9% | ≤ 1.5% (long run 0%) | Purchasing lead |
| K6 | Touchless rate | 4 Touchless | 63.7% | 60.8% to 66.4% | ≥ 66% | Head of Procurement Ops |
| K7 | Rework events per 100 items | 3 Rework | 48.5 | 42.6 to 53.3 | ≤ 43 | Purchasing lead |
| K8 | Payment-block removal rate | 3 Rework | 27.8% | 24.9% to 30.9% | ≤ 25% | Accounts Payable lead |

## Definitions

### K1 Cycle time, PO creation to clearing (K1a median, K1b P90)
- **Formula:** first `Clear Invoice` minus first `Create Purchase Order Item`, in days; median and 90th percentile.
- **Population:** main category, cleared cohort items (128,251).
- **Target:** the touchless items' own values (median 73.4 d, P90 122.0 d; see [04-cohort-findings](../mining/notes/04-cohort-findings.md)), that is, what the process achieves when nothing is changed, cancelled or blocked.
- **Caveat:** the best month is not used as the target, because later cohort months had less follow-up before the cut-off and look faster than they are.

### K2 Wait from invoice receipt to clearing
- **Formula:** first `Clear Invoice` minus first `Record Invoice Receipt`, in days; median.
- **Population:** main category, cleared cohort items with an invoice receipt (128,011).
- **Target:** best month (June 2018, 41.2 d).
- **Caveat:** this wait is 58% of the cycle. If it reflects agreed payment terms, it is a policy choice, not process waste, and the target should follow the terms. The log has no payment-term field to check this.

### K3 Clearing rate
- **Formula:** items with a `Clear Invoice` event divided by all items.
- **Population:** main category cohort items (136,777).
- **Target:** best month (June 2018, 94.6%).
- **Caveat:** about 3.7 points of the gap are deleted items, which are a legitimate outcome. Only usable on cohorts with at least about six months of follow-up before January 2019.

### K4 Invoice receipt before goods receipt rate (three-way-match control)
- **Formula:** items whose first `Record Invoice Receipt` is earlier than their first `Record Goods Receipt`, divided by items with both events.
- **Population:** main category cohort items with both events (129,244).
- **Target:** best month (July 2018, 5.5%). The monthly range is wide (5.5% to 13.2%) and falls in June and July; the reason is not yet known.
- **Caveat:** this does not depend on clearing. In this category the vendor invoice is expected before goods receipt, so the KPI is about AP *booking* the invoice before the goods are confirmed.

### K5 Vendor invoice before PO rate
- **Formula:** items whose `Vendor creates invoice` date is an earlier calendar day than the `Create Purchase Order Item` date, divided by items with a vendor invoice.
- **Population:** all categories, cohort items with a vendor invoice (136,164). On all cases (not just the cohort) the figure is 3,618 of 209,888 (1.7%).
- **Target:** best month as an interim step (1.5%). An invoice before the order is a compliance breach, so 0% is the long-run aim.
- **Caveat:** the vendor invoice is date-only, so the comparison is by calendar day. Same-day cases are not counted.

### K6 Touchless rate
- **Formula:** items with none of the rework activities (Change Price, Change Quantity, Cancel Invoice Receipt, Cancel Goods Receipt, Remove Payment Block, Set Payment Block), divided by items.
- **Population:** cleared 3-way cohort items (135,721).
- **Target:** best month (June 2018, 66.4%).

### K7 Rework events per 100 items
- **Formula:** count of rework-activity events, divided by items, times 100.
- **Population:** cleared 3-way cohort items (135,721).
- **Target:** best month (June 2018, 42.6).
- **Why both K6 and K7:** K6 counts items touched; K7 also counts repeats, so it shows whether items that are reworked are reworked more than once.

### K8 Payment-block removal rate
- **Formula:** items with at least one `Remove Payment Block`, divided by items.
- **Population:** cleared 3-way cohort items (135,721).
- **Target:** best month (February 2018, 24.9%).
- **Caveat:** setting a block is rarely logged (124 events against 57,136 removals), so removals stand in for blocks.

## Limits

- Associations only: a KPI moving does not show why it moved.
- The targets are assumptions derived from the data, not company policy.
- Seven months of cohort data give a short trend. Monthly values for items ordered after July 2018 are not comparable for K1 to K3.
