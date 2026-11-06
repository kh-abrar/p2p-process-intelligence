# 02 – Variants and the first as-is model

Date: 2026-11-06. Script: `mining/variants.py` (events with `ts_suspect = true` excluded, because their dates would misplace them in the trace). Full table written to `mining/outputs/variants.csv` (git-ignored, rebuildable).

## 1. How regular is each category?

| Category | Cases | Variants | Variants to cover 80% of cases |
| --- | --- | --- | --- |
| Consignment | 14,498 | 281 | 5 |
| 3-way match, invoice before GR | 221,010 | 7,830 | 36 |
| 2-way match | 1,044 | 150 | 21 |
| 3-way match, invoice after GR | 15,182 | 4,230 | 1,194 |

- "Invoice before GR" is dominated by a few variants (36 cover 80% of its cases). It is the right first model.
- "Invoice after GR" is very scattered (1,194 variants for 80%). Variants are the wrong lens there. Use a filtered directly-follows graph or the inductive miner with a noise threshold, and expect loops (repeated receipts, service entry sheets).

## 2. Top variants, "3-way match, invoice before GR" (221,010 cases)

The top 10 cover about 61.7% of the category's cases.

| # | Cases | Share | Variant |
| --- | --- | --- | --- |
| 1 | 47,959 | 21.7% | Create PO Item > Vendor creates invoice > Record Goods Receipt > Record Invoice Receipt > Clear Invoice |
| 2 | 29,410 | 13.3% | Create PO Item > Record Goods Receipt > Vendor creates invoice > Record Invoice Receipt > Clear Invoice |
| 3 | 10,854 | 4.9% | Create PO Item > Vendor creates invoice > Record Goods Receipt > Record Invoice Receipt > Remove Payment Block > Clear Invoice |
| 4 | 9,694 | 4.4% | Create PO Item > Receive Order Confirmation > Record Goods Receipt > Vendor creates invoice > Record Invoice Receipt > Clear Invoice |
| 5 | 8,835 | 4.0% | Create PO Item > Vendor creates invoice > Record Invoice Receipt > Record Goods Receipt > Remove Payment Block > Clear Invoice |
| 6 | 8,673 | 3.9% | Create Purchase Requisition Item > Create PO Item > Vendor creates invoice > Record Goods Receipt > Record Invoice Receipt > Clear Invoice |
| 7 | 7,694 | 3.5% | Create PO Item > Record Goods Receipt > Vendor creates invoice > Record Invoice Receipt > Remove Payment Block > Clear Invoice |
| 8 | 4,807 | 2.2% | Create PO Item > Delete Purchase Order Item |
| 9 | 4,222 | 1.9% | Create PO Item > Receive Order Confirmation > Vendor creates invoice > Record Goods Receipt > Record Invoice Receipt > Clear Invoice |
| 10 | 4,155 | 1.9% | Create Purchase Requisition Item > Create PO Item > Vendor creates invoice > Record Goods Receipt > Record Invoice Receipt (no clearing) |

## 3. Observations

1. **The category label is about item set-up, not behaviour.** Variant 2 has the goods receipt before the vendor invoice even though the category is "invoice before GR". Do not read the category name as "the invoice came first".
2. **Order of "Vendor creates invoice" vs other events is partly a timestamp artefact.** That activity is always stamped 23:59:00 (date-only). On the same calendar day it is always sorted after events with real times such as Goods Receipt. So variants 1 and 2 differ only if the vendor invoice date and the goods receipt date differ. Treat the ordering of the vendor invoice relative to other events as day-level. This is the reason to model it in parallel with the goods receipt.
3. **"Record Invoice Receipt" always comes after "Vendor creates invoice" in the top variants,** while the goods receipt can come before or after the invoice receipt (variant 5 has the invoice receipt before the goods receipt). That is the pattern the 3-way-match control is meant to prevent, so it is a candidate compliance finding to quantify in Week 2.
4. **Payment-block removal sits immediately before clearing** in variants 3, 5 and 7 (about 12.4% of the category's cases among the top 10 alone).
5. **Dead ends:** variant 8 (2.2%) is a PO item that is created and then deleted. Variant 10 (1.9%) has an invoice receipt but no clearing event.

## 4. Cases with no clearing event

| Category | Cases | No "Clear Invoice" | Share |
| --- | --- | --- | --- |
| 3-way match, invoice before GR | 221,010 | 47,312 | 21.4% |
| 3-way match, invoice after GR | 15,182 | 5,506 | 36.3% |
| Consignment | 14,498 | 14,498 | 100% |
| 2-way match | 1,044 | 741 | 71.0% |

- Consignment never clears an invoice in this log (no invoice flow), which is expected by design.
- For the others, "no clearing" mixes several causes: deleted items, still open at the end of the log, or paid outside the log. Separate these before reporting throughput times or a completion rate.

## 5. Backbone for the first as-is BPMN ("3-way match, invoice before GR")

Covers variants 1 to 7 and 9 (about 56% of cases plus the optional steps), with two exception paths:

1. Optional start: Create Purchase Requisition Item
2. Create Purchase Order Item
3. Optional: Receive Order Confirmation
4. Parallel split:
   - Branch A: Vendor creates invoice, then Record Invoice Receipt
   - Branch B: Record Goods Receipt
5. Parallel join
6. Exclusive gateway: payment blocked? If yes, Remove Payment Block
7. Clear Invoice, then end event "Paid"
8. Exception path: Delete Purchase Order Item, then end event "Item deleted"

Compliance deviations (invoice receipt before goods receipt, invoice before PO) are not drawn in the as-is model. They are measured against it in conformance checking.

## 6. Next steps

1. Draw the model above in Camunda Modeler. Save as `bpmn/asis_3way_invoice_before_gr.bpmn` and export a PNG.
2. Count how many cases follow the backbone, with and without the optional steps and the block removal.
3. Quantify "invoice receipt before goods receipt" and "vendor invoice before PO" per category.
4. Split cases with no clearing event into deleted, open at log end, and other.