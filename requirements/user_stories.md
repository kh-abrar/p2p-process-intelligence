# User stories: Purchase-to-Pay dashboard

Version 1.0, 2026-11-13. Requirements and IDs (FR, DR, NFR): [`dashboard_requirements.md`](dashboard_requirements.md). Priority uses MoSCoW. Acceptance criteria use Given / When / Then. Example numbers are cohort baselines (POs created January to July 2018, main category unless stated) and serve as test values.

## Epic A: See performance at a glance

### US-1 KPI overview (M)
**As** the Head of Procurement Operations, **I want** all eight KPIs on one page with their targets, **so that** I can see in a minute where we miss.
- Given no filters, when I open Overview, then I see tiles K1a to K8 with value, target and gap, and K1a shows 79.3 days against a target of 73 days, marked as missed. (FR-2)
- Given any tile, when I look at it, then it shows a 7-month trend line. (FR-3)
- Given any tile, when I hover or click, then its definition and caveat from the KPI catalogue appear. (FR-4)

### US-2 Filter everything once (M)
**As** any user, **I want** to set PO month, category, spend area and vendor once, **so that** every page shows the same population.
- Given I set spend area to "Packaging", when I switch pages, then the filter stays and the filter summary line shows it. (FR-1)
- Given a filter that leaves fewer than 30 items in a group, when that group would appear in a ranking, then it shows "n < 30" and is not ranked. (DR-4)

## Epic B: Understand where time goes

### US-3 Phase breakdown (M)
**As** the Accounts Payable lead, **I want** to see how long each phase takes, **so that** I know whether the wait is before or after the invoice is recorded.
- Given the main category, when I open Cycle time, then I see median days for PO to goods receipt (about 10), goods receipt to invoice receipt (about 8) and invoice receipt to clearing (46.1), each with P90, and a note that phase medians do not sum to the total. (FR-6)

### US-4 Slowest spend areas and vendors (M)
**As** the Head of Procurement Operations, **I want** spend areas and vendors ranked by cycle time, **so that** I know where to start.
- Given the main category and cleared items, when I view the ranking, then each row shows item count, median and P90, and groups under 30 items are excluded. (FR-8, DR-4)
- Given the ranking, when I switch the measure to P90, then the order updates. (FR-9)

## Epic C: Find control breaches

### US-5 Invoice booked before goods receipt (M)
**As** the Accounts Payable lead, **I want** to see how often invoices are booked before the goods are received, and where, **so that** I can tighten the three-way match.
- Given the main category, when I open Compliance, then K4 shows 9.1% (11,815 of 129,244) with its monthly trend (5.5% to 13.2%). (FR-10)
- Given the K4 breakdown, when I sort vendors by item count, then I see the vendors contributing most early bookings. (FR-11)

### US-6 Vendor invoice before the order (M)
**As** the Purchasing lead, **I want** to see items where the vendor invoiced before the PO existed, **so that** I can address maverick buying.
- Given all categories, when I view K5, then it shows 1.7% for the cohort, and switching to "all items" shows 3,618 of 209,888. (FR-10, DR-2)

### US-7 Item lists for follow-up (M)
**As** the Purchasing or Accounts Payable lead, **I want** the list of items behind any compliance figure, **so that** my team can follow them up.
- Given a bar or row in the Compliance page, when I click it, then I see the items with case ID, vendor, spend area, PO date, both event dates and the gap in days. (FR-12)
- Given that list, when I press Download, then I get a CSV with the same rows and columns.

## Epic D: Measure rework

### US-8 Touchless and rework rate (M)
**As** the Head of Procurement Operations, **I want** to see the share of items that run untouched and how much rework happens, **so that** I can track simplification.
- Given cleared 3-way items, when I open Rework, then K6 shows 63.7% and K7 shows 48.5 rework events per 100 items, each with a monthly trend. (FR-14)

### US-9 Which rework goes with delay (M)
**As** the Purchasing lead, **I want** each rework type with its item count and the cycle-time gap, **so that** I can see which changes matter most.
- Given cleared 3-way items, when I view the rework table, then Change Quantity shows 10,035 items and +21.8 days, and Remove Payment Block shows 37,667 items and +14.0 days. (FR-15)
- Given the table, when I read the gap column, then its header says "associated gap (days)" and a note says the gap is not a proven effect. (FR-15)

### US-10 Payment blocks by vendor (S)
**As** the Accounts Payable lead, **I want** payment-block removals by vendor and spend area, **so that** I can find where blocks cluster.
- Given cleared 3-way items, when I open the breakdown, then each group shows item count and K8 rate, excluding groups under 30 items. (FR-16, DR-4)

## Epic E: Trust the data

### US-11 One item's story (M)
**As** the process analyst, **I want** to open any item and see its events in order, **so that** I can check what a number means on a real case.
- Given case ID `4507004931_00020`, when I search for it, then I see its attributes, its events in order with timestamp, lane and user type, and its milestones and status. (FR-21, FR-22)
- Given an item with a date-only or suspect event, when I view the timeline, then that event is marked. (FR-21)

### US-12 Process variants and conformance (S)
**As** the process analyst, **I want** to see the top variants and how well the as-is model fits, **so that** I can explain the standard flow and its exceptions.
- Given the main category, when I open Process, then I see the top 20 variants with counts and cumulative share, the fitness of finished cases (91.6%) and the deviation groups. (FR-18, FR-19, DR-6)

### US-13 Data limits visible (M)
**As** any user, **I want** the data limits stated in the app, **so that** I do not over-read the numbers.
- Given any page, when it loads, then a banner states the cohort, the January 2019 clearing cut-off and "associations, not causes". (section 5)
- Given the Data notes page, when I open it, then I see each limit with a link to its note, the dataset citation, and the warehouse build time and row counts. (FR-23, FR-24)

## Epic F: Decide on a change

### US-14 Link to redesign results (C)
**As** the Head of Procurement Operations, **I want** to jump from the dashboard to the simulated redesign results, **so that** I can compare the options with their intervals.
- Given the Overview page, when the simulation in `impact/` exists, then a link leads to its results; until then the link is hidden.

## Definition of done (all stories)

- The numbers match `v_kpi` or the mining notes for the same filters (DR-5), checked by a pytest test per page.
- The page meets NFR-2 (under 3 seconds) and NFR-4 (readable without relying on colour alone).
- `make lint` and `make test` pass.
