-- Populate the star schema. Expects two views created by src/p2p/warehouse.py:
--   src_events        = data/interim/events_clean.parquet
--   src_activity_map  = model/activity_map.csv

INSERT INTO dim_date
SELECT
    CAST(strftime(d, '%Y%m%d') AS INTEGER),
    d,
    year(d), quarter(d), month(d),
    strftime(d, '%Y-%m'),
    weekofyear(d),
    dayname(d),
    isodow(d) >= 6
FROM (
    SELECT CAST(unnest(generate_series(min(timestamp)::DATE, max(timestamp)::DATE, INTERVAL 1 DAY)) AS DATE) AS d
    FROM src_events
);

INSERT INTO dim_activity
SELECT
    row_number() OVER (ORDER BY m.activity),
    m.activity, m.lane, m.stage, m.is_rework, m.is_modelled,
    coalesce(e.date_only, false)
FROM src_activity_map m
LEFT JOIN (SELECT activity, bool_or(date_only) AS date_only FROM src_events GROUP BY 1) e USING (activity);

INSERT INTO dim_vendor
SELECT row_number() OVER (ORDER BY vendor), vendor, vendor_name
FROM (SELECT vendor, any_value("case Name") AS vendor_name FROM src_events GROUP BY 1);

INSERT INTO dim_company
SELECT row_number() OVER (ORDER BY company), company
FROM (SELECT DISTINCT company FROM src_events);

INSERT INTO dim_user
SELECT
    row_number() OVER (ORDER BY "user"),
    "user",
    CASE WHEN "user" = 'NONE' THEN 'none' WHEN "user" LIKE 'batch%' THEN 'batch' ELSE 'human' END
FROM (SELECT DISTINCT "user" FROM src_events);

INSERT INTO dim_item
SELECT
    row_number() OVER (ORDER BY case_id),
    case_id, po_number, po_item, item_category, item_type, document_type,
    spend_area, sub_spend_area, spend_classification,
    gr_based_iv = 'true', goods_receipt_flag = 'true'
FROM (
    SELECT case_id,
           any_value(po_number) AS po_number, any_value(po_item) AS po_item,
           any_value(item_category) AS item_category, any_value(item_type) AS item_type,
           any_value(document_type) AS document_type, any_value(spend_area) AS spend_area,
           any_value(sub_spend_area) AS sub_spend_area,
           any_value("case Spend classification text") AS spend_classification,
           any_value(gr_based_iv) AS gr_based_iv, any_value(goods_receipt_flag) AS goods_receipt_flag
    FROM src_events
    GROUP BY case_id
);

INSERT INTO fact_event
SELECT
    e.event_id_int,
    i.item_key, a.activity_key, u.user_key, v.vendor_key, c.company_key,
    CAST(strftime(e.timestamp, '%Y%m%d') AS INTEGER),
    e.timestamp,
    row_number() OVER (PARTITION BY e.case_id ORDER BY e.timestamp, e.event_id_int),
    e.net_worth_eur,
    e.ts_suspect
FROM src_events e
JOIN dim_item i USING (case_id)
JOIN dim_activity a USING (activity)
JOIN dim_user u ON u.user_name = e."user"
JOIN dim_vendor v ON v.vendor_id = e.vendor
JOIN dim_company c ON c.company_id = e.company;

INSERT INTO fact_item
WITH ev AS (
    SELECT e.*, a.activity, a.is_rework
    FROM fact_event e JOIN dim_activity a USING (activity_key)
    WHERE NOT e.ts_suspect
),
agg AS (
    SELECT
        item_key,
        any_value(vendor_key) AS vendor_key,
        any_value(company_key) AS company_key,
        min(event_ts) FILTER (WHERE activity = 'Create Purchase Order Item') AS po_ts,
        min(event_ts) FILTER (WHERE activity = 'Vendor creates invoice') AS vendor_invoice_ts,
        min(event_ts) FILTER (WHERE activity = 'Record Goods Receipt') AS gr_ts,
        min(event_ts) FILTER (WHERE activity = 'Record Invoice Receipt') AS ir_ts,
        min(event_ts) FILTER (WHERE activity = 'Clear Invoice') AS clear_ts,
        min(event_ts) FILTER (WHERE activity = 'Delete Purchase Order Item') AS delete_ts,
        arg_min(net_worth_eur, event_ts) FILTER (WHERE activity = 'Create Purchase Order Item') AS po_net_worth_eur,
        count(*) AS n_events,
        count(*) FILTER (WHERE activity = 'Record Goods Receipt') AS n_goods_receipts,
        count(*) FILTER (WHERE activity = 'Record Invoice Receipt') AS n_invoice_receipts,
        count(*) FILTER (WHERE is_rework) AS n_rework,
        count(*) FILTER (WHERE activity = 'Change Price') AS n_price_changes,
        count(*) FILTER (WHERE activity = 'Change Quantity') AS n_quantity_changes,
        bool_or(activity = 'Remove Payment Block') AS payment_block,
        string_agg(activity, ' > ' ORDER BY seq_in_item) AS variant
    FROM ev
    GROUP BY item_key
)
SELECT
    item_key, vendor_key, company_key,
    CAST(strftime(po_ts, '%Y%m%d') AS INTEGER),
    strftime(po_ts, '%Y-%m'),
    coalesce(po_ts >= TIMESTAMP '2018-01-01' AND po_ts < TIMESTAMP '2018-08-01', false),
    po_ts, vendor_invoice_ts, gr_ts, ir_ts, clear_ts, delete_ts,
    (epoch_us(clear_ts) - epoch_us(po_ts)) / 86400e6,
    (epoch_us(clear_ts) - epoch_us(ir_ts)) / 86400e6,
    n_events, n_goods_receipts, n_invoice_receipts, n_rework, n_price_changes, n_quantity_changes,
    payment_block,
    clear_ts IS NOT NULL,
    delete_ts IS NOT NULL,
    ir_ts < gr_ts,
    vendor_invoice_ts::DATE < po_ts::DATE,
    CASE
        WHEN clear_ts IS NOT NULL THEN 'cleared'
        WHEN delete_ts IS NOT NULL THEN 'deleted'
        WHEN ir_ts IS NOT NULL THEN 'invoice not cleared'
        WHEN gr_ts IS NOT NULL THEN 'received not invoiced'
        ELSE 'ordered only'
    END,
    po_net_worth_eur,
    variant
FROM agg;
