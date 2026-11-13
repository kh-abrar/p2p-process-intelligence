# 03 – Right-censoring of clearing events

Date: 2026-11-07. Script: `mining/censoring.py` (events with `ts_suspect = true` excluded).

## Question
Earlier analysis showed 47,312 "invoice before GR" items (21.4%) with no "Clear Invoice" event, of which 26,203 had an invoice recorded, were not cancelled, and never cleared (about €129M by the indicative `net_worth_eur` measure, versus about €1.18bn for cleared items). Are these genuinely unpaid, or is the log cut off?

## Result: the log is cut off for clearing

Clearing events per month (all categories):

| Month | Clear Invoice events |
| --- | --- |
| 2018-01 | 258 |
| 2018-02 | 2,864 |
| 2018-03 | 9,991 |
| 2018-04 | 15,244 |
| 2018-05 | 19,196 |
| 2018-06 | 19,914 |
| 2018-07 | 20,253 |
| 2018-08 | 21,878 |
| 2018-09 | 19,231 |
| 2018-10 | 19,408 |
| 2018-11 | 19,273 |
| 2018-12 | 9,245 |
| 2019-01 | 17,638 |

No clearing events after January 2019, although other events run to April 2020.

Share of items cleared, by month the PO was created ("3-way match, invoice before GR"):

| PO month | Cases | Share cleared | Median days to clear |
| --- | --- | --- | --- |
| 2018-01 | 18,325 | 93.2% | 79.3 |
| 2018-02 | 18,358 | 94.5% | 77.3 |
| 2018-03 | 21,915 | 92.9% | 79.1 |
| 2018-04 | 19,754 | 94.4% | 79.2 |
| 2018-05 | 20,048 | 94.4% | 78.3 |
| 2018-06 | 19,695 | 94.6% | 83.2 |
| 2018-07 | 18,682 | 92.3% | 81.0 |
| 2018-08 | 18,042 | 89.8% | 78.3 |
| 2018-09 | 15,826 | 77.3% | 73.9 |
| 2018-10 | 19,473 | 55.8% | 64.7 |
| 2018-11 | 18,595 | 29.7% | 52.3 |
| 2018-12 | 12,235 | 5.2% | 29.4 |
| 2019-01 | 62 | 0.0% | n/a |

Share cleared among items with an invoice receipt, by month of the last invoice receipt (all categories):

| Invoice month | Cases | Share cleared |
| --- | --- | --- |
| 2018-01 to 2018-09 | 6,062 to 21,260 per month | 98.1% to 100% |
| 2018-10 | 17,328 | 84.4% |
| 2018-11 | 16,671 | 65.9% |
| 2018-12 | 17,144 | 44.8% |
| 2019-01 | 9,941 | 8.2% |

## Interpretation
- Clearing is right-censored at about the end of January 2019. Items ordered or invoiced late in 2018 cannot show clearing that happened after the cut.
- The median time to clear falls from about 79 to 29 days for later PO months because only the fastest items had time to clear. Durations measured on all cleared items are therefore biased low, mostly in the upper percentiles.
- For invoices recorded January to September 2018, 98 to 100% cleared, so genuinely unpaid invoices are under about 1%.
- "Invoice recorded, never cleared" is **not a finding**. It is a data-truncation artefact.

## Decisions
1. Headline cycle-time and rework figures use the **cohort of POs created January to July 2018** (share cleared 92.3 to 94.6%, at least about six months of follow-up before the cut). Later POs are reported only for compliance measures that do not depend on clearing.
2. State the truncation in the brief and README limits.
3. The control-leak measure (invoice receipt before goods receipt) does not depend on clearing and is reported on all items.
4. Earlier figures (median 77 days, P90 126.8, rework gap about +14 days, uncleared shares) are provisional until recomputed for the cohort.

## Correction
Earlier I assumed that, because events run to April 2020, uncleared items were probably not still open. That was wrong for clearing events, which stop in January 2019.

## Next

*Update 2026-11-13: done; see notes 04 to 06, `kpis/catalogue.md` and `impact/README.md`.*
- Recompute throughput, rework gaps, touchless share and the invoice-before-goods-receipt rate for the January to July 2018 cohort (`mining/cohort_metrics.py`).
- Update `brief/brief.md` and README limits.
- Refine the as-is BPMN (delete after order confirmation) and fix the same-day tie-break in conformance.