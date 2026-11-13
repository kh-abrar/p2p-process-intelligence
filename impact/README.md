# Impact: to-be process and what-if simulation

Date: 2026-11-13. Answers brief question 5: *which process change would cut cycle time or rework most, and by how much?*
Model: `src/p2p/simulation.py` (SimPy), run with `make simulate` after `make warehouse`; outputs in `impact/outputs/` (git-ignored). To-be BPMN: [`bpmn/tobe_3way_invoice_before_gr.bpmn`](../bpmn/tobe_3way_invoice_before_gr.bpmn) (preview `bpmn/tobe_3way_invoice_before_gr_preview.png`).

## Short answer

- **Preventing payment blocks helps most.** Avoiding half of them would cut the median order-to-payment time by **1.3 days (95% interval 1.0 to 1.9)** and raise the touchless share by **11.2 points**.
- Avoiding half of order-side rework (price and quantity changes, receipt cancellations) cuts **0.9 days (0.3 to 1.6)** and adds 4.0 touchless points.
- Both together: **2.4 days (2.0 to 3.0)** off the median, 3.6 days off the P90, and touchless from 64% to about 81%.
- **The time gains are small**, much smaller than the 18-day gap between rework and touchless items (note 04). The reason is in the data: 91% of items are cleared more than two weeks after both receipts are in (median 45 days later). Payment follows a due date counted from the vendor invoice, so most delay on the order side is absorbed by that wait. Cycle time is mainly set by payment timing. Rework mostly costs effort and control, not elapsed days.
- The compliance change (book the invoice only after the goods receipt) is modelled as time-neutral. It removes the 9.1% invoice-before-goods-receipt leak (K4) by design.

## To-be process

Same lanes and scope as the as-is model (main category). Three changes, marked in the diagram:

| # | Change | Targets | Simulated as |
| --- | --- | --- | --- |
| 1 | Order confirmation becomes mandatory, and price or quantity is corrected before goods and invoice arrive | Change Price / Change Quantity after the fact (K7) | S1: share of order-rework items that become right first time |
| 2 | The invoice is booked only after the goods receipt (AND join before Record Invoice Receipt) | Invoice booked before goods receipt (K4, 9.1%) | Not simulated: assumed time-neutral |
| 3 | Automatic three-way match with tolerance; only real mismatches are blocked; payment on the due date | Payment-block removals (K8, 27.8%) | S2: share of blocked items that are no longer blocked |

The 50% reduction in S1 and S2 is an assumption, not a measured effect. The sensitivity runs use 25% and 75%.

## Model

One SimPy process per item ("3-way match, invoice before GR", POs created January to July 2018, cleared, with a vendor invoice and both receipts: 127,830 items). After PO creation, three things run in parallel: the goods receipt, the vendor invoice followed by its booking, and the payment due date (vendor invoice date plus a wait). The item clears when all three are done, which mirrors the three-way match plus payment terms.

Each item draws two flags from the observed mix: **order rework** (Change Price, Change Quantity, Cancel Goods Receipt, Cancel Invoice Receipt) and **payment block** (Remove or Set Payment Block). Times come from observed items with the same flags:

| Order rework | Block | Items | Median days until both receipts | Median days vendor invoice to clearing | Median PO to clearing |
| --- | --- | --- | --- | --- | --- |
| no | no | 81,685 | 21.2 | 62.8 | 73.3 |
| no | yes | 28,526 | 20.3 | 71.6 | 87.2 |
| yes | no | 10,191 | 38.2 | 68.6 | 92.8 |
| yes | yes | 7,428 | 31.6 | 75.5 | 94.2 |

Order rework stretches the order side (21 to 38 days); blocks stretch the payment side (63 to 72 days). The model keeps that split:
- the order-side times (vendor invoice, goods receipt and invoice booking) come together from one observed item;
- the payment wait comes from another item with the same flags and a similar invoice-booking delay (quintiles of booking date minus vendor invoice date), because late booking goes with late payment.

A scenario switches a share of flagged items to "not flagged"; those items then take their times from items without that rework.

### Why this structure

Two simpler structures were tried first and rejected because they overstated the P90 by about 12 days (141 against 129 observed):
- payment wait counted from the moment both receipts are in;
- payment wait counted from the invoice booking.

The payment wait is negatively correlated with the order side (r = -0.31), which is what a due date counted from an earlier date produces. Counting from the vendor invoice date and conditioning on the booking delay removes most of that bias.

### Validation (simulated baseline against the observed items)

| Measure | Observed | Simulated | Difference |
| --- | --- | --- | --- |
| Median days | 79.3 | 80.8 | +1.5 |
| P90 days | 129.1 | 129.1 | +0.1 |
| Mean days | 83.6 | 84.9 | +1.3 |
| Touchless share | 63.9% | 64.0% | +0.1 pt |

The median is about 1.5 days high; differences between scenarios are paired against this same baseline, so the bias largely cancels in them.

### Uncertainty

50 replications of 10,000 items each. Every replication bootstraps the 127,830 observed items (uncertainty in the inputs) and simulates a new sample (simulation noise). All scenarios in a replication use the same random numbers, so their differences to the baseline are paired. Intervals are the 2.5th to 97.5th percentiles of the 50 paired differences. Simulating 10,000 items rather than all 127,830 per replication makes the intervals somewhat wider than necessary (conservative).

## Results

Differences to the simulated baseline (80.8 days median, 129.1 P90, 84.9 mean, 64.0% touchless), with 95% intervals.

| Scenario | Median (days) | P90 (days) | Mean (days) | Touchless (points) |
| --- | --- | --- | --- | --- |
| S1 right-first-time PO (50%) | -0.9 [-1.6, -0.3] | -1.5 [-2.5, -0.8] | -1.1 [-1.3, -0.7] | +4.0 [3.7, 4.4] |
| S2 block prevention (50%) | -1.3 [-1.9, -1.0] | -1.9 [-2.9, -1.2] | -1.4 [-1.7, -1.1] | +11.2 [10.6, 11.8] |
| S3 both (50% each) | -2.4 [-3.0, -2.0] | -3.6 [-4.8, -2.8] | -2.6 [-3.0, -2.2] | +16.6 [15.9, 17.2] |

Sensitivity to the size of the reduction:

| Scenario | Median (days) | P90 (days) | Touchless (points) |
| --- | --- | --- | --- |
| S1 at 25% | -0.5 [-0.9, -0.1] | -0.8 [-1.5, -0.2] | +2.0 [1.7, 2.3] |
| S1 at 75% | -1.4 [-2.0, -1.0] | -2.1 [-3.0, -1.2] | +6.0 [5.5, 6.5] |
| S2 at 25% | -0.7 [-1.0, -0.2] | -1.0 [-1.7, -0.4] | +5.6 [5.2, 6.0] |
| S2 at 75% | -2.0 [-2.7, -1.3] | -2.8 [-3.8, -2.1] | +16.7 [15.9, 17.4] |

The ranking holds at every reduction level: block prevention gives more per unit of effort than order-side rework prevention, mainly because blocks touch more items (28% against 14%).

## Limits and assumptions

- **Association treated as effect.** The model assumes that an item which avoids rework behaves like observed items without it. Harder orders may attract both rework and delay, so the gains are an upper bound for a given reduction.
- **The reductions (25/50/75%) are assumptions.** The log cannot say how many changes or blocks a mandatory confirmation or a tolerance check would prevent.
- **No capacity.** The log has no staffing or workload data, so there are no queues: fewer blocks free AP effort but do not speed anyone else up in the model. With capacity data, `simulate` could add an AP resource.
- **Payment timing is kept as observed.** Changing payment terms or payment runs would move cycle time far more than any rework change, but that is a finance policy choice, not a process fix, and it is outside the brief.
- **Main category only**, cleared cohort items with a vendor invoice and both receipts (99.7% of cleared main-category cohort items).
- **Change 2 (book invoice after goods receipt)** is not simulated. Its value is control, not speed.
