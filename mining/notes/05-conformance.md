# 05 – Conformance of the as-is model

Date: 2026-11-07. Script: `mining/conformance.py`. Model: `bpmn/asis_3way_invoice_before_gr.bpmn` (preview `bpmn/asis_3way_invoice_before_gr_preview.png`). Per-variant results in `mining/outputs/conformance_invoice_before_gr.csv`, console output in `mining/outputs/conformance.txt` (both git-ignored).

## Model scope

- Category: "3-way match, invoice before GR" only (221,010 cases, 88% of the log).
- One pool with four lanes: Purchasing, Vendor, Warehouse, Accounts Payable.
- 9 modelled activities: Create Purchase Requisition Item (optional), Create Purchase Order Item, Receive Order Confirmation (optional), Delete Purchase Order Item (exception end), Vendor creates invoice, Record Invoice Receipt, Record Goods Receipt, Remove Payment Block (optional), Clear Invoice.
- Structure: optional requisition, PO, optional order confirmation, then either deletion or a parallel split into the invoice branch (vendor invoice, then invoice receipt) and the goods-receipt branch, a join, optional block removal, clearing.

## Method

1. Keep events of this category, drop `ts_suspect` events, keep only the 9 modelled activities (all other activities are projected out, not treated as deviations).
2. Order events per case by timestamp, with the same-day tie-break below.
3. Build a variant-level log: one trace per distinct sequence, weighted by its case count (2,915 variants before the fix).
4. Convert the BPMN to a Petri net with pm4py and run token-based replay. A case is "fit" when its trace replays with no missing or remaining tokens.
5. Report on all cases and on **finished cases** (those reaching Clear Invoice or Delete Purchase Order Item). Unfinished cases fail by construction (missing end), and many are cut off by the January 2019 censoring.

## Changes in this round

1. **Same-day tie-break.** "Vendor creates invoice" has a date-only timestamp (placeholder 23:59 or 00:00). When it falls on the same day as a "Record Invoice Receipt", a 23:59 placeholder sorts after the receipt it caused. The script now moves such vendor-invoice events to just before the first same-day invoice receipt. This affected 2,321 events in 2,303 cases. No other orderings are changed.
2. **Delete after order confirmation.** The old model allowed deletion only straight after PO creation. The refined model places the "Item deleted?" decision after the optional order confirmation, so both "PO > Delete" and "PO > Order Confirmation > Delete" fit. Lanes, IDs and layout style are unchanged; the file keeps its name. It imports in bpmn-js 17 with no warnings.

## Fitness, finished cases (181,507)

| Run | Fitting cases | Share | Weighted fitness |
| --- | --- | --- | --- |
| Before (old model, no tie-break) | 163,525 | 90.1% | 0.989 |
| Tie-break only | 165,064 | 90.9% | 0.989 |
| Tie-break + refined model | 166,228 | **91.6%** | 0.990 |

All cases (221,010): 74.0% fit before, 75.2% after.

## Remaining deviations (finished cases that do not fit: 15,279)

Rough classification by script rule (first rule that matches):

| Deviation | Cases | Share of finished |
| --- | --- | --- |
| Repeated activity (more than one goods receipt, invoice receipt, vendor invoice, clearing or block removal) | 11,603 | 6.4% |
| Vendor invoice dated before the PO | 2,455 | 1.4% |
| Other ordering or missing step (e.g. PO then clearing with no receipts, 336 cases) | 1,146 | 0.6% |
| Invoice receipt without a preceding vendor invoice | 75 | 0.04% |

- Repeated activities are the largest group: partial deliveries and repeat invoices. The model has no loops, by choice, to keep it readable.
- Vendor invoice before the PO is a compliance finding (see 04), not a modelling error. None of these cases have the invoice on the same calendar day as the PO, so this is not the date-only sorting artefact.
- Invoice receipt before goods receipt **fits** the model, because the two branches run in parallel. The control leak (9.1% of cohort items) is measured separately in `mining/cohort_metrics.py`.

## Not modelled

- The other three categories (invoice after GR, 2-way match, consignment).
- Rework activities: Change Price, Change Quantity, Cancel Goods Receipt, Cancel Invoice Receipt, Set Payment Block, and all other activities (33 of 42). They are projected out before replay.
- Loops (repeated receipts and invoices), deletion after goods or invoice receipt, debit memos, service entry sheets.
- Precision and generalisation are not measured; only fitness. A model with these parallel and optional parts will allow some behaviour the log never shows.
- Timing: the replay ignores durations.
