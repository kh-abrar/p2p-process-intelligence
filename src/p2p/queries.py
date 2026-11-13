"""Query layer for the dashboard (app/app.py). Every function takes a DuckDB connection to the
warehouse (data/warehouse/p2p.duckdb) and returns plain values or polars DataFrames.

Rules from requirements/dashboard_requirements.md:
- DR-1: time, clearing and rework measures use cohort items only (POs created Jan-Jul 2018).
- DR-2: compliance measures can switch to all items.
- DR-4: groups with fewer than MIN_N items are left out of rankings.
- DR-5: with default filters, every KPI equals the v_kpi view (checked by tests).
"""

from dataclasses import dataclass, field

import duckdb
import polars as pl

MIN_N = 30
MAIN = "3-way match, invoice before GR"
COHORT_MONTHS = tuple(f"2018-{m:02d}" for m in range(1, 8))

# id: (label, unit, better, target) -- targets are the assumed ones in kpis/catalogue.md
KPI_META = {
    "K1a": ("Cycle time, median", "days", "lower", 73.0),
    "K1b": ("Cycle time, P90", "days", "lower", 122.0),
    "K2": ("Invoice receipt to clearing, median", "days", "lower", 41.0),
    "K3": ("Clearing rate", "share", "higher", 0.945),
    "K4": ("Invoice booked before goods receipt", "share", "lower", 0.055),
    "K5": ("Vendor invoice before PO", "share", "lower", 0.015),
    "K6": ("Touchless rate", "share", "higher", 0.66),
    "K7": ("Rework events per 100 items", "per 100", "lower", 43.0),
    "K8": ("Payment-block removal rate", "share", "lower", 0.25),
}


@dataclass(frozen=True)
class Filters:
    months: tuple[str, str] = (COHORT_MONTHS[0], COHORT_MONTHS[-1])
    category: str | None = None  # None = all categories
    spend_areas: tuple[str, ...] = field(default_factory=tuple)
    vendors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def focus_category(self) -> str:
        """Category for single-category measures (K1 to K4, phases, variants): the selected one, else main."""
        return self.category or MAIN


def _where(f: Filters, cohort: bool = True, alias: str = "") -> tuple[str, list]:
    """SQL condition and parameters for the filters on v_item."""
    a = f"{alias}." if alias else ""
    conds, params = ["TRUE"], []
    if cohort:
        conds.append(f"{a}in_cohort AND {a}po_month BETWEEN ? AND ?")
        params += list(f.months)
    if f.category:
        conds.append(f"{a}item_category = ?")
        params.append(f.category)
    if f.spend_areas:
        conds.append(f"list_contains(?, {a}spend_area)")
        params.append(list(f.spend_areas))
    if f.vendors:
        conds.append(f"list_contains(?, {a}vendor_id)")
        params.append(list(f.vendors))
    return " AND ".join(conds), params


def _grp(by: str) -> str:
    """Group column with blank values labelled, for spend area / vendor breakdowns."""
    assert by in ("spend_area", "vendor_id")
    return f"coalesce(nullif(trim({by}), ''), '(blank)')"


def _df(con: duckdb.DuckDBPyConnection, sql: str, params: list | None = None) -> pl.DataFrame:
    return con.sql(sql, params=params or None).pl()


# ---------- options and metadata ----------


def options(con) -> dict[str, list[str]]:
    rows = lambda sql: [r[0] for r in con.execute(sql).fetchall()]
    return {
        "categories": rows("SELECT DISTINCT item_category FROM v_item WHERE in_cohort ORDER BY 1"),
        "spend_areas": rows("SELECT DISTINCT spend_area FROM v_item WHERE in_cohort ORDER BY 1"),
        "vendors": rows(
            f"SELECT vendor_id FROM v_item WHERE in_cohort GROUP BY 1 HAVING count(*) >= {MIN_N} ORDER BY 1"
        ),
    }


def build_info(con) -> dict:
    built_at, source, conf = con.execute("SELECT * FROM build_info").fetchall()[0]
    counts = {
        t: con.execute(f"SELECT count(*) FROM {t}").fetchall()[0][0]
        for t in ("fact_event", "fact_item", "dim_vendor", "conformance_variant")
    }
    return {"built_at": built_at, "source": source, "conformance_source": conf, "counts": counts}


# ---------- KPIs ----------

_KPI_SELECT = """
    median(po_to_clear_days) FILTER (WHERE is_focus AND cleared) AS K1a,
    quantile_cont(po_to_clear_days, 0.9) FILTER (WHERE is_focus AND cleared) AS K1b,
    median(ir_to_clear_days) FILTER (WHERE is_focus AND cleared) AS K2,
    avg(cleared::INT) FILTER (WHERE is_focus) AS K3,
    avg(ir_before_gr::INT) FILTER (WHERE is_focus) AS K4,
    avg(vi_before_po::INT) AS K5,
    avg((n_rework = 0)::INT) FILTER (WHERE is_three_way AND cleared) AS K6,
    100 * avg(n_rework) FILTER (WHERE is_three_way AND cleared) AS K7,
    avg(payment_block::INT) FILTER (WHERE is_three_way AND cleared) AS K8,
    count(*) AS items
"""


def _kpi_from(f: Filters) -> tuple[str, list]:
    where, params = _where(f)
    sql = f"""FROM (SELECT *, item_category = ? AS is_focus, item_category LIKE '3-way match%' AS is_three_way
                    FROM v_item WHERE {where})"""
    return sql, [f.focus_category, *params]


def kpis(con, f: Filters) -> dict[str, float | None]:
    """KPI values under the filters. K1-K4 use the focus category; K6-K8 the 3-way items."""
    src, params = _kpi_from(f)
    row = _df(con, f"SELECT {_KPI_SELECT} {src}", params)
    return row.to_dicts()[0]


def kpis_monthly(con, f: Filters) -> pl.DataFrame:
    src, params = _kpi_from(f)
    return _df(con, f"SELECT po_month, {_KPI_SELECT} {src} GROUP BY po_month ORDER BY po_month", params)


# ---------- cycle time ----------


def phases(con, f: Filters) -> pl.DataFrame:
    """Median and P90 days per phase for cleared items of the focus category (FR-6)."""
    where, params = _where(f)
    parts = {
        "PO to goods receipt": "epoch(gr_ts - po_ts) / 86400",
        "Goods receipt to invoice receipt": "epoch(ir_ts - gr_ts) / 86400",
        "Invoice receipt to clearing": "ir_to_clear_days",
        "PO to clearing (total)": "po_to_clear_days",
    }
    sel = ", ".join(
        f"median({e}) AS \"{k}|median\", quantile_cont({e}, 0.9) AS \"{k}|p90\", count({e}) AS \"{k}|items\""
        for k, e in parts.items()
    )
    row = _df(con, f"SELECT {sel} FROM v_item WHERE {where} AND cleared AND item_category = ?", [
        *params, f.focus_category
    ]).to_dicts()[0]
    return pl.DataFrame(
        [
            {"phase": k, "median_days": row[f"{k}|median"], "p90_days": row[f"{k}|p90"], "items": row[f"{k}|items"]}
            for k in parts
        ]
    )


def cycle_quantiles(con, f: Filters, by: str = "item_category") -> pl.DataFrame:
    """P10/P25/median/P75/P90 of PO-to-clearing days for cleared items, per group (FR-7, FR-17)."""
    where, params = _where(f)
    group = {
        "item_category": "item_category",
        "rework": "CASE WHEN n_rework = 0 THEN 'Touchless' ELSE 'With rework' END",
    }[by]
    extra = " AND item_category LIKE '3-way match%'" if by == "rework" else ""
    return _df(
        con,
        f"""SELECT {group} AS grp, count(*) AS items,
                   quantile_cont(po_to_clear_days, [0.1, 0.25, 0.5, 0.75, 0.9]) AS q
            FROM v_item WHERE {where} AND cleared{extra}
            GROUP BY 1 HAVING count(*) >= {MIN_N} ORDER BY items DESC""",
        params,
    ).with_columns(
        *[pl.col("q").list.get(i).alias(n) for i, n in enumerate(["p10", "p25", "median", "p75", "p90"])]
    ).drop("q")


def ranking(con, f: Filters, by: str = "spend_area", measure: str = "median") -> pl.DataFrame:
    """Cleared focus-category items per spend area or vendor, ranked by cycle time (FR-8, FR-9)."""
    assert measure in ("median", "p90")
    where, params = _where(f)
    return _df(
        con,
        f"""SELECT {_grp(by)} AS grp, count(*) AS items,
                   median(po_to_clear_days) AS median_days,
                   quantile_cont(po_to_clear_days, 0.9) AS p90_days,
                   avg((n_rework = 0)::INT) AS touchless
            FROM v_item WHERE {where} AND cleared AND item_category = ?
            GROUP BY 1 HAVING count(*) >= {MIN_N}
            ORDER BY {measure}_days DESC""",
        [*params, f.focus_category],
    )


# ---------- compliance ----------

_BREACH = {
    # kpi: (population condition, breach condition, first date, second date)
    "K4": ("item_category = ? AND ir_ts IS NOT NULL AND gr_ts IS NOT NULL", "ir_before_gr", "ir_ts", "gr_ts"),
    "K5": ("vendor_invoice_ts IS NOT NULL", "vi_before_po", "vendor_invoice_ts", "po_ts"),
}


def _breach_src(f: Filters, kpi: str, all_items: bool) -> tuple[str, list]:
    pop, *_ = _BREACH[kpi]
    where, params = _where(f, cohort=not all_items)
    if kpi == "K4":
        params = [*params, f.focus_category]
    return f"FROM v_item WHERE {where} AND {pop}", params


def compliance_breakdown(con, f: Filters, kpi: str, by: str, all_items: bool = False) -> pl.DataFrame:
    """Breach rate per spend area or vendor (FR-11)."""
    assert by in ("spend_area", "vendor_id")
    _, breach, *_ = _BREACH[kpi]
    src, params = _breach_src(f, kpi, all_items)
    return _df(
        con,
        f"""SELECT {_grp(by)} AS grp, count(*) AS items, sum({breach}::INT)::BIGINT AS breaches,
                   avg({breach}::INT) AS rate
            {src} GROUP BY 1 HAVING count(*) >= {MIN_N} ORDER BY breaches DESC""",
        params,
    )


def compliance_rate(con, f: Filters, kpi: str, all_items: bool = False) -> tuple[float | None, int, int]:
    _, breach, *_ = _BREACH[kpi]
    src, params = _breach_src(f, kpi, all_items)
    rate, n, b = con.execute(f"SELECT avg({breach}::INT), count(*), sum({breach}::INT) {src}", params).fetchall()[0]
    return rate, n, int(b or 0)


def compliance_items(
    con, f: Filters, kpi: str, by: str | None = None, group: str | None = None, all_items: bool = False
) -> pl.DataFrame:
    """Items breaching K4 or K5, optionally for one spend area or vendor (FR-12)."""
    _, breach, first, second = _BREACH[kpi]
    src, params = _breach_src(f, kpi, all_items)
    extra = ""
    if by and group is not None:
        assert by in ("spend_area", "vendor_id")
        extra, params = f" AND {_grp(by)} = ?", [*params, group]
    return _df(
        con,
        f"""SELECT case_id, vendor_id, spend_area, item_category, po_ts::DATE AS po_date,
                   {first} AS first_event, {second} AS second_event,
                   round(epoch({second} - {first}) / 86400, 1) AS gap_days
            {src} AND {breach}{extra} ORDER BY gap_days DESC""",
        params,
    )


def ir_gr_gap_bins(con, f: Filters, all_items: bool = False) -> pl.DataFrame:
    """How many days the invoice receipt came before the goods receipt, binned (FR-13)."""
    src, params = _breach_src(f, "K4", all_items)
    return _df(
        con,
        f"""WITH g AS (SELECT epoch(gr_ts - ir_ts) / 86400 AS d {src} AND ir_before_gr)
            SELECT CASE WHEN d < 1 THEN '1: under 1 day' WHEN d < 7 THEN '2: 1-7 days'
                        WHEN d < 30 THEN '3: 7-30 days' WHEN d < 90 THEN '4: 30-90 days'
                        ELSE '5: 90 days or more' END AS bin,
                   count(*) AS items
            FROM g GROUP BY 1 ORDER BY 1""",
        params,
    ).with_columns(pl.col("bin").str.slice(3))


# ---------- rework ----------


def rework_types(con, f: Filters) -> pl.DataFrame:
    """Per rework activity: items with it and the associated median cycle-time gap (FR-15).
    Cleared 3-way items, as in mining/cohort_metrics.py."""
    where, params = _where(f)
    return _df(
        con,
        f"""WITH items AS (
                SELECT item_key, po_to_clear_days FROM v_item
                WHERE {where} AND cleared AND item_category LIKE '3-way match%'
            ),
            flags AS (
                SELECT DISTINCT e.item_key, a.activity
                FROM fact_event e JOIN dim_activity a USING (activity_key) JOIN items USING (item_key)
                WHERE a.is_rework AND NOT e.ts_suspect
            )
            SELECT r.activity,
                   count(fl.item_key) AS items_with,
                   count(fl.item_key) / count(*) AS share,
                   median(i.po_to_clear_days) FILTER (WHERE fl.item_key IS NOT NULL) AS median_with,
                   median(i.po_to_clear_days) FILTER (WHERE fl.item_key IS NULL) AS median_without
            FROM items i
            CROSS JOIN (SELECT activity FROM dim_activity WHERE is_rework) r
            LEFT JOIN flags fl ON fl.item_key = i.item_key AND fl.activity = r.activity
            GROUP BY r.activity ORDER BY items_with DESC""",
        params,
    ).with_columns(
        pl.when(pl.col("items_with") >= MIN_N)
        .then(pl.col("median_with") - pl.col("median_without"))
        .alias("gap_days")
    )


def block_breakdown(con, f: Filters, by: str = "spend_area") -> pl.DataFrame:
    """Payment-block removal rate (K8) per spend area or vendor (FR-16)."""
    assert by in ("spend_area", "vendor_id")
    where, params = _where(f)
    return _df(
        con,
        f"""SELECT {_grp(by)} AS grp, count(*) AS items, avg(payment_block::INT) AS rate
            FROM v_item WHERE {where} AND cleared AND item_category LIKE '3-way match%'
            GROUP BY 1 HAVING count(*) >= {MIN_N} ORDER BY rate DESC""",
        params,
    )


# ---------- process ----------


def top_variants(con, f: Filters, n: int = 20) -> pl.DataFrame:
    """Most frequent variants of the focus category under the filters (FR-18)."""
    where, params = _where(f)
    return (
        _df(
            con,
            f"""SELECT variant, count(*) AS items FROM v_item
                WHERE {where} AND item_category = ? GROUP BY 1 ORDER BY items DESC""",
            [*params, f.focus_category],
        )
        .with_columns((pl.col("items") / pl.col("items").sum()).alias("share"))
        .with_columns(pl.col("share").cum_sum().alias("cumulative_share"))
        .head(n)
    )


def conformance(con) -> tuple[dict, pl.DataFrame]:
    """Fitness of finished cases and the deviation groups (FR-19). Not filtered: one model run."""
    s = _df(
        con,
        """SELECT sum(cases)::BIGINT AS finished, (sum(cases) FILTER (WHERE fit))::BIGINT AS fitting,
                  sum(cases * fitness) / sum(cases) AS weighted_fitness
           FROM conformance_variant WHERE ended""",
    ).to_dicts()[0]
    groups = _df(
        con,
        """SELECT reason, sum(cases)::BIGINT AS cases, count(*) AS variants,
                  sum(cases) / (SELECT sum(cases) FROM conformance_variant WHERE ended) AS share_of_finished
           FROM conformance_variant WHERE ended AND NOT fit GROUP BY 1 ORDER BY cases DESC""",
    )
    return s, groups


# ---------- item detail ----------


def item_detail(con, case_id: str) -> tuple[dict | None, pl.DataFrame]:
    """Attributes, milestones and ordered events of one item (FR-21, FR-22)."""
    item = _df(con, "SELECT * EXCLUDE (variant) FROM v_item WHERE case_id = ?", [case_id])
    if item.is_empty():
        return None, pl.DataFrame()
    events = _df(
        con,
        """SELECT e.seq_in_item AS seq, a.activity, e.event_ts AS timestamp, a.lane, u.user_type,
                  a.is_date_only AS date_only, e.ts_suspect AS suspect, e.net_worth_eur
           FROM fact_event e
           JOIN dim_item i USING (item_key) JOIN dim_activity a USING (activity_key) JOIN dim_user u USING (user_key)
           WHERE i.case_id = ? ORDER BY e.seq_in_item""",
        [case_id],
    )
    return item.to_dicts()[0], events
