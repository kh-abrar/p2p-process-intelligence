# 01 – Data exploration (BPI Challenge 2019)

Date: 2026-11-06. Reproduce with `uv run python src/p2p/ingest.py` then `uv run python src/p2p/clean.py`. Checks were run with scratch scripts and are summarised below.

## 1. Source and load

- Original dataset: van Dongen, B.F. (2019), BPI Challenge 2019, 4TU.ResearchData, https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1
- Copy used: `BPI_Challenge_2019.csv.gz` (40,896,616 bytes) from the `jadzoghaib/processlens` GitHub release `dataset-v1`. SHA-256 verified: `2a6fae0e5b8feffdb1117af024dd4ba93ad1b096d778ddb0306dd55778b238a7`. data.4tu.nl timed out from my network on 3 Nov 2026. A CSV conversion of the original XES log, so column names are CSV-style (e.g. `case concept:name`).
- Loaded to `data/interim/events.parquet` (all columns read as text first, then timestamp and net worth cast). Cleaned table: `data/interim/events_clean.parquet`.

## 2. Size

| Measure | Value |
| --- | --- |
| Events | 1,595,923 |
| Cases | 251,734 |
| Activities | 42 |

These match the figures published with the dataset copy.

**A case is one purchase-order line item** (`case concept:name` = PO number + item, e.g. `4507004931_00020`), not a whole PO. Every case has exactly one "Create Purchase Order Item" event.

## 3. Item categories (`case Item Category`)

| Category | Cases | Share of cases | Events |
| --- | --- | --- | --- |
| 3-way match, invoice before GR | 221,010 | 87.8% | 1,234,708 |
| 3-way match, invoice after GR | 15,182 | 6.0% | 319,233 |
| Consignment | 14,498 | 5.8% | 36,084 |
| 2-way match | 1,044 | 0.4% | 5,898 |

Consequence: model "invoice before GR" first. The 2-way match model will be small. `case GR-Based Inv. Verif.` is a separate true/false flag and is not the category.

## 4. Timestamps

- Format: `dd-mm-yyyy HH:MM:SS.fff`. Range in the raw data: 1948-01-26 to 2020-04-09.
- **Precision depends on the activity.** 235,032 events (14.7%) are stamped 23:59:00 and 47,742 (3.0%) are stamped 00:00:00. These are date-only placeholders.
- Three activities are 100% placeholder times, so durations touching them are **day-level only**:
  - Vendor creates invoice (219,919 events)
  - Vendor creates debit memo (6,255)
  - Create Purchase Requisition Item (46,592)
- Small placeholder shares elsewhere: Clear Invoice 4.1%, Record Service Entry Sheet 0.9%, Record Goods Receipt 0.1%. All other activities have real clock times and can be reported in hours.
- Same-day ordering is only a guess where times are placeholders. Sort by case, timestamp, then event ID, and do not claim finer precision than the data supports.

## 5. Bad and suspect dates

- 19 events dated before 2000 (1948 and 1993), in 14 cases. All are "Vendor creates invoice" or "Vendor creates debit memo".
- Earliest event per case falls in these years: 1948 (5 cases), 1993 (9), 2001 (17), 2008 (45), 2015 (2), 2016 (2), 2017 (184), 2018 (251,268), 2019 (202).
- PO creation year: 2018 for 251,352 cases and 2019 for 382. PO creation is therefore the reliable case start.

### Events before the PO exists

54,702 events in 51,866 cases (20.6%) are dated before their PO creation. Most are legitimate pre-PO steps:

| Activity | Events before PO |
| --- | --- |
| Create Purchase Requisition Item | 46,592 (all of them) |
| Vendor creates invoice | 3,815 |
| SRM: Created | 1,440 |
| Change Approval for Purchase Order | 1,298 |
| Release Purchase Requisition | 388 |
| Release Purchase Order | 201 |
| Vendor creates debit memo | 183 |
| Other SRM statuses and Change Currency | remainder |

Distribution of days before PO: median 0, 75th percentile 1, maximum 25,565 (the 1948 dates).

**The 3,815 "Vendor creates invoice" events before the PO are a candidate compliance finding** ("invoice before PO"). Vendor dates are date-only, so compare calendar dates, not timestamps, when defining the KPI in Week 3.

## 6. Cleaning decision

- Rule: an event is **suspect** (`ts_suspect = true`) if it is more than **365 days before its case's PO creation**. Rows are kept, not deleted.
- Result: **100 suspect events in 85 cases**: Vendor creates invoice 80, Vendor creates debit memo 18, Create Purchase Requisition Item 2. This covers the 19 pre-2000 events.
- Suspect events are excluded from duration calculations. Counts and variants can still include or exclude them explicitly.
- Threshold of 365 days is a judgement call. Revisit if the flagged set changes the findings.
- Added columns in `events_clean.parquet`: `po_ts`, `days_before_po`, `date_only`, `event_id_int`, `ts_suspect`. Rows sorted by `case_id`, `timestamp`, `event_id_int`.
- The `date_only` flag covers only the three always-placeholder activities. Small placeholder shares in other activities are not flagged.

## 7. Process observations to follow up

- **Payment blocks:** "Remove Payment Block" occurs 57,136 times but "Set Payment Block" only 124. Setting a block is mostly not logged, so define the payment-block KPI on removals and state this caveat.
- **Rework candidates:** Change Quantity 21,449, Change Price 12,423, Delete Purchase Order Item 8,875, Cancel Invoice Receipt 7,096, Cancel Goods Receipt 3,096.
- **Services:** Record Service Entry Sheet has 164,975 events, which suggests many service items. Check how it relates to the categories.
- **Truncation:** cases start in 2018 (a few in 2019) but events run to April 2020. Check how many cases have no clearing event, because open cases will distort throughput times.
- **Activity volumes** (top five): Record Goods Receipt 314,097; Create Purchase Order Item 251,734; Record Invoice Receipt 228,760; Vendor creates invoice 219,919; Clear Invoice 194,393.

## 8. Next steps

1. Build the variant table per category (top variants and their share of cases).
2. Draw the first as-is BPMN for "3-way match, invoice before GR" from the dominant variant.
3. Count cases with no clearing event (open or incomplete).
4. Add pytest checks: expected row and case counts, no null case IDs, one PO-creation event per case.