# 06 – Comparison with published BPI Challenge 2019 reports

Date: 2026-11-13. Sources: the report PDFs linked from the ICPM 2019 challenge page (https://icpmconference.org/2019/?p=302), read from extracted text. Five of the fifteen submissions listed there were read: both winners and three non-student reports with clear numbers. Their figures are quoted as reported; definitions differ, so differences of a few days or points are expected.

## Reports read

| Short name | Report | Category |
| --- | --- | --- |
| HPI | Diba, Remy, Pufahl. *Compliance and Performance Analysis of Procurement Processes Using Process Mining* (BPI-Challenge-Submission-6) | Overall winner |
| Rhine-Waal | Meyer zu Wickern, Juluru, Roy, Nguyen, Vu. *Analysis and prediction of purchasing compliance using process mining* (Student-Submission-4) | Student winner |
| DFKI | Gutermuth, Lahann, Rehse, Scheid, Schuhmann, Stephan, Fettke. *Efficient and Compliant Purchase Order Handling* (Submission-7) | Non-student |
| KPMG | van Dyk, Aklecha, Kennes, Ramezani. *Dissecting the Purchase-to-Pay Process: An exercise in Process Mining* (Submission-3) | Non-student |
| CKM | Porter, Masse, Visatemongkolchai, Seneviratne, Deokule, Hartman. *Balancing Efficiency and Risk in Procure to Pay* (Submission-8) | Non-student |

## Side by side

| Topic | This project | Published reports | Verdict |
| --- | --- | --- | --- |
| Order to payment, main category | Median 79.3 d, mean 83.6 d (cleared items, POs Jan-Jul 2018) | KPMG: mean 81 d over all completed items. CKM: median 72 d for items without a block removal, 91 d with one | Consistent |
| Effect of payment blocks | Remove Payment Block on 27.8% of cleared 3-way items; associated with +14.0 d (91.0 vs 77.0 median) | CKM: block removal in 21% of goods-first items, median 72 → 91 d. KPMG: blocks on 20% of items, on average 22 d from invoice receipt to block removal | Consistent; CKM's 72 → 91 d is almost the same contrast as our touchless 73.4 vs rework 91.0 |
| Invoice receipt to clearing | Median 46.1 d | HPI: median 42 d (mean 49 d). KPMG: about 44 d for 77% of cases | Consistent; all point to payment timing as the largest wait |
| PO to goods receipt | Median 10.0 d | HPI: median 10 d (mean 15 d) | Same |
| Invoice booked before goods receipt (main category) | 9.1% (11,815 of 129,244 cohort items) | HPI: 8% (16,168 cases, whole log). CKM: goods receipt first or same time in 91% | Consistent |
| Quantity changes | 7.4% of cleared 3-way items, associated with +21.8 d to clearing | HPI: 6.9% (13,140 cases), roughly doubling time to goods receipt | Consistent; different end points |
| Set vs remove payment block | 124 vs 57,136 events: setting is rarely logged | HPI notes the same 124 vs 57,136 | Same |
| Impossible dates | 100 events flagged (e.g. 1948), excluded from durations | HPI, KPMG and DFKI note the 1948 dates; HPI also excludes them from performance | Same treatment |
| Conformance of the main-category model | 91.6% of finished cases fit (token replay, 9 activities) | KPMG: 92% conformance for its invoice-before-GR model. HPI: 83-97% trace fitness depending on model and filtering. Rhine-Waal: 93% weighted fitness | Consistent |
| Open / incomplete cases | Clearing (and invoice receipt) events stop in January 2019, so time measures use a fixed cohort of POs created Jan-Jul 2018 | KPMG and CKM drop incomplete cases (about 25-27%) and measure the rest. HPI and CKM call open cases a snapshot effect | **Different** (see below) |

## Where this project differs

1. **Censoring handled with a cohort, not by dropping open cases.** The reports read either exclude incomplete cases or note them as still open. Excluding open cases keeps only the items that cleared quickly among late-2018 POs, which biases durations low (note 03: the median for November 2018 POs is 52 days against 79 for January to July). In the text of the five reports I found no explicit statement that clearing events stop in January 2019, nor a cohort-based correction. This is the main methodological difference, and it may partly explain why our median is a little higher than the figures from complete cases only.
2. **A simulated "what if".** The reports quantify associations (blocks and changes go with longer times) and recommend fewer blocks, more automation or retraining. None of the five estimates how much a given reduction would save. Our simulation suggests the saving is small (1.3 days at the median for half the blocks), because payment follows a due date. That puts the strong associations in all reports, including ours, into perspective.
3. **Payment timing as the main lever.** HPI and KPMG both observe the long wait after invoice receipt (42-44 days) and suspect batch payment runs or terms. Our model makes this explicit: 91% of items are paid more than two weeks after both receipts are in.

## What the reports cover that this project does not

- **Many-to-many matching** of invoices and goods receipts within a PO (DFKI, CKM), and checks that EUR amounts match between events (CKM). This project works at item level and does not match amounts.
- **Rules per item type** (CKM: "Service" items in 3-way-after are far less compliant). Our compliance work is per category, not per item type.
- **Batch and automation analysis** (CKM: share of events done by batch users, automation potential).
- **Predictive models** of non-compliance (Rhine-Waal decision trees).
- **Document-level events copied into each item** (HPI), which can misplace PO-level changes in item traces. This project treats every event as item-level; that may add noise to variants.

## Takeaways for the README and memo

- Our headline numbers agree with the published reports within a few days or points, which supports the cleaning and the cohort choices.
- The cohort approach and the simulation are the two things this project adds.
- Item-type compliance and amount matching would be the next analyses if the work continued.
