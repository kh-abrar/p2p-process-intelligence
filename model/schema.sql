-- Star schema for the BPI Challenge 2019 purchase-to-pay log (DuckDB).
-- Grain: fact_event = one logged event; fact_item = one PO line item (accumulating snapshot).
-- Built by src/p2p/warehouse.py, which runs this file, then model/load.sql.

CREATE TABLE dim_date (
    date_key      INTEGER PRIMARY KEY,          -- YYYYMMDD
    date          DATE NOT NULL UNIQUE,
    year          SMALLINT NOT NULL,
    quarter       TINYINT NOT NULL,
    month         TINYINT NOT NULL,
    year_month    VARCHAR NOT NULL,             -- e.g. 2018-03
    iso_week      TINYINT NOT NULL,
    weekday       VARCHAR NOT NULL,
    is_weekend    BOOLEAN NOT NULL
);

CREATE TABLE dim_activity (
    activity_key  SMALLINT PRIMARY KEY,
    activity      VARCHAR NOT NULL UNIQUE,
    lane          VARCHAR NOT NULL,             -- Purchasing, Vendor, Warehouse, Accounts Payable, SRM system
    stage         VARCHAR NOT NULL,             -- requisition, order, change, receipt, invoice, payment
    is_rework     BOOLEAN NOT NULL,             -- counts towards the rework / touchless KPIs
    is_modelled   BOOLEAN NOT NULL,             -- in bpmn/asis_3way_invoice_before_gr.bpmn
    is_date_only  BOOLEAN NOT NULL              -- timestamp is a date with a placeholder time
);

CREATE TABLE dim_vendor (
    vendor_key    INTEGER PRIMARY KEY,
    vendor_id     VARCHAR NOT NULL UNIQUE,      -- anonymised, e.g. vendorID_0000
    vendor_name   VARCHAR NOT NULL              -- anonymised, e.g. vendor_0000
);

CREATE TABLE dim_company (
    company_key   SMALLINT PRIMARY KEY,
    company_id    VARCHAR NOT NULL UNIQUE
);

CREATE TABLE dim_user (
    user_key      INTEGER PRIMARY KEY,
    user_name     VARCHAR NOT NULL UNIQUE,      -- anonymised; same as the log's resource
    user_type     VARCHAR NOT NULL              -- human, batch, none
);

CREATE TABLE dim_item (
    item_key              INTEGER PRIMARY KEY,
    case_id               VARCHAR NOT NULL UNIQUE,  -- PO number _ item number
    po_number             VARCHAR NOT NULL,
    po_item               VARCHAR NOT NULL,
    item_category         VARCHAR NOT NULL,
    item_type             VARCHAR NOT NULL,
    document_type         VARCHAR NOT NULL,
    spend_area            VARCHAR NOT NULL,
    sub_spend_area        VARCHAR NOT NULL,
    spend_classification  VARCHAR NOT NULL,
    gr_based_iv           BOOLEAN NOT NULL,
    goods_receipt_flag    BOOLEAN NOT NULL
);

CREATE TABLE fact_event (
    event_key       BIGINT PRIMARY KEY,         -- event_id from the log
    item_key        INTEGER NOT NULL REFERENCES dim_item (item_key),
    activity_key    SMALLINT NOT NULL REFERENCES dim_activity (activity_key),
    user_key        INTEGER NOT NULL REFERENCES dim_user (user_key),
    vendor_key      INTEGER NOT NULL REFERENCES dim_vendor (vendor_key),
    company_key     SMALLINT NOT NULL REFERENCES dim_company (company_key),
    date_key        INTEGER NOT NULL REFERENCES dim_date (date_key),
    event_ts        TIMESTAMP NOT NULL,
    seq_in_item     INTEGER NOT NULL,           -- order within the item (timestamp, then event_id)
    net_worth_eur   DOUBLE NOT NULL,            -- cumulative net worth at this event (indicative)
    ts_suspect      BOOLEAN NOT NULL            -- impossible date; excluded from durations
);

-- One row per item. Timestamps are the first occurrence of each activity, from events with
-- ts_suspect = false. Durations in days.
CREATE TABLE fact_item (
    item_key            INTEGER PRIMARY KEY REFERENCES dim_item (item_key),
    vendor_key          INTEGER NOT NULL REFERENCES dim_vendor (vendor_key),
    company_key         SMALLINT NOT NULL REFERENCES dim_company (company_key),
    po_date_key         INTEGER REFERENCES dim_date (date_key),
    po_month            VARCHAR,
    in_cohort           BOOLEAN NOT NULL,       -- PO created Jan-Jul 2018 (see mining/notes/03)
    po_ts               TIMESTAMP,
    vendor_invoice_ts   TIMESTAMP,              -- date-only
    gr_ts               TIMESTAMP,
    ir_ts               TIMESTAMP,
    clear_ts            TIMESTAMP,
    delete_ts           TIMESTAMP,
    po_to_clear_days    DOUBLE,
    ir_to_clear_days    DOUBLE,
    n_events            INTEGER NOT NULL,
    n_goods_receipts    INTEGER NOT NULL,
    n_invoice_receipts  INTEGER NOT NULL,
    n_rework            INTEGER NOT NULL,       -- events of dim_activity.is_rework activities
    n_price_changes     INTEGER NOT NULL,
    n_quantity_changes  INTEGER NOT NULL,
    payment_block       BOOLEAN NOT NULL,       -- any Remove Payment Block
    cleared             BOOLEAN NOT NULL,
    deleted             BOOLEAN NOT NULL,
    ir_before_gr        BOOLEAN,                -- null unless both events exist
    vi_before_po        BOOLEAN,                -- calendar day; null without a vendor invoice
    status              VARCHAR NOT NULL,       -- cleared, deleted, invoice not cleared, received not invoiced, ordered only
    po_net_worth_eur    DOUBLE,                 -- net worth at PO creation (indicative)
    variant             VARCHAR NOT NULL        -- activity sequence, ' > ' separated (non-suspect events)
);

-- Token-replay results per variant of the as-is model (main category, 9 modelled activities),
-- loaded from mining/outputs/conformance_invoice_before_gr.csv when present (see mining/notes/05).
CREATE TABLE conformance_variant (
    variant     VARCHAR PRIMARY KEY,           -- sequence of modelled activities only
    cases       INTEGER NOT NULL,
    fit         BOOLEAN NOT NULL,
    fitness     DOUBLE NOT NULL,
    missing     INTEGER NOT NULL,
    remaining   INTEGER NOT NULL,
    ended       BOOLEAN NOT NULL,              -- reaches Clear Invoice or Delete Purchase Order Item
    reason      VARCHAR NOT NULL               -- fits, not finished, or a deviation group
);

CREATE TABLE build_info (
    built_at              TIMESTAMP NOT NULL,
    source                VARCHAR NOT NULL,
    conformance_source    VARCHAR             -- null when the conformance results were not found
);

-- Convenience view: item facts with their descriptive attributes.
CREATE VIEW v_item AS
SELECT f.*, i.case_id, i.item_category, i.item_type, i.spend_area, i.sub_spend_area,
       v.vendor_id, c.company_id
FROM fact_item f
JOIN dim_item i USING (item_key)
JOIN dim_vendor v USING (vendor_key)
JOIN dim_company c USING (company_key);

-- KPI catalogue (kpis/catalogue.md) on the Jan-Jul 2018 cohort.
-- One row per PO month plus one row with po_month = 'all'. Shares are 0-1.
CREATE VIEW v_kpi AS
WITH c AS (
    SELECT *,
           item_category = '3-way match, invoice before GR' AS is_main,
           item_category LIKE '3-way match%' AS is_three_way
    FROM v_item
    WHERE in_cohort
)
SELECT
    coalesce(po_month, 'all') AS po_month,
    median(po_to_clear_days) FILTER (WHERE is_main AND cleared) AS k1a_cycle_median_days,
    quantile_cont(po_to_clear_days, 0.9) FILTER (WHERE is_main AND cleared) AS k1b_cycle_p90_days,
    median(ir_to_clear_days) FILTER (WHERE is_main AND cleared) AS k2_ir_to_clear_median_days,
    avg(cleared::INT) FILTER (WHERE is_main) AS k3_clearing_rate,
    avg(ir_before_gr::INT) FILTER (WHERE is_main) AS k4_ir_before_gr_rate,
    avg(vi_before_po::INT) AS k5_vi_before_po_rate,
    avg((n_rework = 0)::INT) FILTER (WHERE is_three_way AND cleared) AS k6_touchless_rate,
    100 * avg(n_rework) FILTER (WHERE is_three_way AND cleared) AS k7_rework_per_100,
    avg(payment_block::INT) FILTER (WHERE is_three_way AND cleared) AS k8_payment_block_rate,
    count(*) AS cohort_items
FROM c
GROUP BY GROUPING SETS ((po_month), ())
ORDER BY po_month;
