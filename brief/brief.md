# Brief: Purchase-to-Pay Process Intelligence

## Process owner
The Head of Procurement Operations of a large multinational in coatings and paints, based in the Netherlands, responsible for purchase-order handling across some 60 subsidiaries. The process owner's concern, as stated with the BPI Challenge 2019 dataset, is compliance, so questions about control breaches sit beside questions about speed.

## Problem
Purchase orders should flow in a line: order, goods receipt, invoice, payment. In practice items are changed, invoices arrive early, payments are blocked and items are cancelled. Each deviation costs time or weakens the three-way-match control. The owner cannot see where time is lost or how often rules are broken, nor which change would help most.

## Questions
1. **Time.** How long does an item take from PO creation to cleared invoice, for each of the four item categories (median and 90th percentile), and where does the longest waiting happen?
2. **Compliance.** How often is an invoice received before the goods receipt, or created before the PO exists, and in which categories?
3. **Rework.** How many items are changed after ordering (price, quantity), cancelled, or held by a payment block, and how much time does each add?
4. **Touchless flow.** What share of items run from order to payment with no change, cancellation or block?
5. **Redesign.** Which process change would cut cycle time or rework most, and by how much (with an interval, from simulation)?

## Scope
- **Data:** BPI Challenge 2019 event log (van Dongen, 2019, 4TU.ResearchData, doi:10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1): 1,595,923 events, 251,734 cases, 42 activities. Purchase orders dated 2018; events run to April 2020.
- **Unit of analysis:** one purchase-order line item, not a whole PO.
- **In scope:** all four item categories (3-way match with invoice before GR, 3-way match with invoice after GR, 2-way match, consignment). The main as-is model covers "invoice before GR" (88% of cases).
- **Out of scope:** prices, spend and vendor negotiation; real costs and financial value of delays; anything outside the log.

## Known limits
- Three activities carry date-only timestamps (vendor invoice, vendor debit memo, purchase requisition), so durations touching them are in days.
- Setting a payment block is rarely logged (124 events versus 57,136 removals), so block rates rest on removals.
- Some cases have no clearing event: consignment by design, others deleted, still open or paid outside the log.
- Data is anonymised and there is no written policy to test against. The compliance rules used are the ones named in this brief.
- 100 events with impossible dates are flagged and excluded from duration calculations.

## How success is measured
Each question maps to a KPI with a formula, owner and target in the KPI catalogue (cycle time, three-way-match compliance, invoice-before-PO rate, rework rate, touchless rate, payment-block rate). The redesign is judged by a simulated before/after difference with a 95% interval.