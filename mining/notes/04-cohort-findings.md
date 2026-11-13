# 04 – Cohort findings: cycle time, control leak, rework

Date: 2026-11-07. Script: `mining/cohort_metrics.py` (events with `ts_suspect = true` excluded). Output saved to `mining/outputs/cohort_metrics.txt` (git-ignored, rebuildable with `make mining`).

## Why a cohort

Clearing events stop in January 2019 although other events run to April 2020 (see [03-censoring.md](03-censoring.md)). Items ordered late in 2018 had no time to show clearing, so cycle times and clearing rates measured on all items are biased low. All time and rework figures here use the **cohort of POs created January to July 2018**: 155,761 items, each with at least about six months of follow-up before the cut. In the main category 92.3 to 94.6% of items in each cohort month cleared.

## 1. PO creation to clearing, per category

| Category | Items | Cleared | Median days | P90 days | Invoice receipt to clearing, median |
| --- | --- | --- | --- | --- | --- |
| 3-way match, invoice before GR | 136,777 | 93.8% | 79.3 | 129.1 | 46.1 |
| 3-way match, invoice after GR | 9,549 | 78.2% | 79.1 | 120.2 | 24.1 |
| Consignment | 9,095 | 0% | n/a | n/a | n/a |
| 2-way match | 340 | 33.8% | 8.3 | 96.9 | 5.5 |

- In the main category, 46.1 of the 79.3 median days (58%) fall after the invoice receipt is recorded. Where the time goes after receipt is not visible in the log; standard payment terms are a plausible explanation (hypothesis, not tested: the log has no payment-term field).
- Consignment has no invoice flow by design.
- 2-way match: 340 items, too few for conclusions.

## 2. Control leak: invoice receipt before goods receipt

Main category, cohort items with both events: **11,815 of 129,244 (9.1%)** had the invoice receipt recorded before the first goods receipt. In this category the invoice is expected before the goods receipt from the vendor's side, but recording it in AP before the goods arrive weakens the three-way match.

Related (all cases, not cohort): the vendor invoice is dated on an earlier calendar day than the PO in 3,618 cases (1.7% of 209,888 cases with a vendor invoice).

## 3. Rework and time (cleared 3-way items)

135,721 cleared 3-way items (both 3-way categories).

| Group | Items | Median days | P90 days |
| --- | --- | --- | --- |
| Touchless (no rework) | 86,505 (63.7%) | 73.4 | 122.0 |
| Any rework | 49,216 (36.3%) | 91.0 | 140.2 |

Gap: **+17.6 days (+24%)** at the median.

| Rework activity | Items with it | Median with | Median without | Gap (days) |
| --- | --- | --- | --- | --- |
| Change Quantity | 10,035 | 100.0 | 78.2 | +21.8 |
| Change Price | 7,010 | 93.2 | 79.0 | +14.2 |
| Remove Payment Block | 37,667 | 91.0 | 77.0 | +14.0 |
| Cancel Goods Receipt | 907 | 83.1 | 79.2 | +3.9 |
| Cancel Invoice Receipt | 4,838 | 80.7 | 79.2 | +1.5 |
| Set Payment Block | 19 | 148.2 | 79.2 | too few |

- Payment-block removal touches about a quarter of cleared items (37,667 of 135,721, 27.8%), so its total effect is the largest even though quantity changes have the bigger gap per item.
- Setting a payment block is rarely logged (19 cleared cohort items), so block rates rest on removals.

## 4. Uncleared cohort items

| Category | Deleted | Invoice recorded, never cleared | Goods received, no invoice | Ordered only | Total uncleared |
| --- | --- | --- | --- | --- | --- |
| Invoice before GR (136,777) | 4,993 (3.7%) | 1,375 (1.0%) | 1,135 (0.8%) | 1,023 (0.7%) | 6.2% |
| Invoice after GR (9,549) | about 2% | 476 (5.0%) | 1,347 (14.1%) | 66 (0.7%) | 21.8% |

2-way match (340 items) is left out: too few items.

## 5. Check: is "goods received, no invoice" a truncation artefact?

Invoice-after-GR cohort items with a goods receipt, share with no invoice receipt, by PO creation month:

| PO month | Items with GR | Share with no invoice |
| --- | --- | --- |
| 2018-01 | 1,520 | 12.2% |
| 2018-02 | 1,248 | 13.7% |
| 2018-03 | 1,341 | 13.9% |
| 2018-04 | 1,181 | 14.6% |
| 2018-05 | 1,406 | 13.9% |
| 2018-06 | 1,437 | 15.2% |
| 2018-07 | 1,168 | 19.3% |

Last "Record Invoice Receipt" in the log: **2019-01-18**. Invoice receipts stop at the same cut as clearing.

**Decision: the "rises toward July" case applies.** The share drifts up from 12.2% to 15.2% over January to June and jumps to 19.3% for July, and invoice receipts themselves are truncated in January 2019. So the 14.1% is partly a truncation effect and is reported only as a limit, not as a finding. The flat level of about 12 to 14% in the earliest months suggests that a real gap remains, but this log cannot separate it cleanly from late invoicing.

## Caveats

- **Association, not causation.** Rework items may be slower because they are harder orders (larger, unusual, problem vendors), not because of the rework itself. The gaps are differences in medians between groups, with no controls.
- Rework activities are counted as present or absent per item, not by count or timing.
- 2-way match is too small for conclusions.
- The payment-terms explanation for the post-invoice wait is a hypothesis.
- Durations touching date-only activities (vendor invoice, requisition) are only accurate to the day. The figures above use PO creation, goods receipt, invoice receipt and clearing, which carry real times.
- The cohort is POs created January to July 2018; results may not hold for later months.
