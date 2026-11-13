"""Purchase-to-Pay Process Intelligence dashboard.

Run from the repository root:  uv run streamlit run app/app.py   (or `make app`)
Needs the warehouse first:     make warehouse
Spec: requirements/dashboard_requirements.md (FR/DR/NFR ids below refer to it).
"""

import os
from pathlib import Path

import duckdb
import plotly.graph_objects as go
import polars as pl
import streamlit as st

from p2p import queries as q

DB = Path(os.environ.get("P2P_DB", "data/warehouse/p2p.duckdb"))
BPMN_PNG = Path("bpmn/asis_3way_invoice_before_gr_preview.png")
IMPACT = Path("impact/README.md")
DEFAULT_CASE = "4507004931_00020"

# reference palette (dataviz skill): categorical slots 1-2; status colours only with icon + label
BLUE, ORANGE = "#2a78d6", "#eb6834"
BANNER = (
    "POs created January to July 2018. Clearing data ends January 2019, so later POs are left out. "
    "Differences between groups are associations, not proven causes."
)

st.set_page_config(page_title="P2P Process Intelligence", page_icon=":material/receipt_long:", layout="wide")


# ---------- data access (NFR-2: cached per filter set; NFR-3: read-only) ----------


@st.cache_resource
def _connection() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB), read_only=True)


@st.cache_data(show_spinner=False)
def run(fn: str, *args):
    return getattr(q, fn)(_connection().cursor(), *args)


if not DB.exists():
    st.error(f"Warehouse not found at `{DB}`. Run `make ingest`, `make mining` and `make warehouse` first.")
    st.stop()


# ---------- formatting and chart helpers ----------


def fmt(kid: str, v: float | None) -> str:
    if v is None:
        return "n/a"
    unit = q.KPI_META[kid][1]
    return f"{v:.1%}" if unit == "share" else f"{v:.1f} d" if unit == "days" else f"{v:.1f}"


def fmt_gap(kid: str, gap: float) -> str:
    unit = q.KPI_META[kid][1]
    return f"{gap * 100:+.1f} pp" if unit == "share" else f"{gap:+.1f} d" if unit == "days" else f"{gap:+.1f}"


def target_met(kid: str, v: float) -> bool:
    _, _, better, target = q.KPI_META[kid]
    return v <= target if better == "lower" else v >= target


def kpi_tile(kid: str, value: float | None, trend: list | None, help_text: str) -> None:
    label, _, better, target = q.KPI_META[kid]
    if value is None:
        st.metric(f"{kid} · {label}", "n/a", border=True, help="No items in this population under the filters.")
        return
    st.metric(
        f"{kid} · {label}",
        fmt(kid, value),
        delta=f"{fmt_gap(kid, value - target)} vs target {fmt(kid, target)}",
        delta_color="inverse" if better == "lower" else "normal",
        help=help_text,
        chart_data=[x for x in (trend or []) if x is not None] or None,
        chart_type="line",
        border=True,
    )
    st.caption(":material/check_circle: Target met" if target_met(kid, value) else ":material/cancel: Target missed")


def bar_h(df: pl.DataFrame, x: str, y: str, x_title: str, hover: str, color: str = BLUE, height: int | None = None):
    """Horizontal single-series bar chart; largest at the top."""
    fig = go.Figure(
        go.Bar(
            x=df[x].to_list(),
            y=df[y].to_list(),
            orientation="h",
            marker={"color": color, "cornerradius": 4},
            customdata=df.to_dicts(),
            hovertemplate=hover + "<extra></extra>",
        )
    )
    fig.update_layout(
        height=height or max(220, 28 * df.height + 80),
        margin={"l": 10, "r": 10, "t": 10, "b": 40},
        xaxis_title=x_title,
        yaxis={"autorange": "reversed"},
        bargap=0.35,
    )
    return fig


def box_from_quantiles(df: pl.DataFrame, x_title: str):
    """Box per group from precomputed quantiles (whiskers P10-P90), so no raw points are shipped."""
    fig = go.Figure()
    for r in df.iter_rows(named=True):
        fig.add_trace(
            go.Box(
                y=[r["grp"]],
                q1=[r["p25"]],
                median=[r["median"]],
                q3=[r["p75"]],
                lowerfence=[r["p10"]],
                upperfence=[r["p90"]],
                orientation="h",
                name=r["grp"],
                marker_color=BLUE,
                line_width=2,
                hovertemplate=(
                    f"<b>{r['grp']}</b><br>items {r['items']:,}<br>P10 {r['p10']:.1f} · P25 {r['p25']:.1f} · "
                    f"median {r['median']:.1f} · P75 {r['p75']:.1f} · P90 {r['p90']:.1f} days<extra></extra>"
                ),
            )
        )
    fig.update_layout(
        height=110 + 70 * df.height, margin={"l": 10, "r": 10, "t": 10, "b": 40}, showlegend=False, xaxis_title=x_title
    )
    return fig


def show(fig) -> None:
    st.plotly_chart(fig, theme="streamlit", use_container_width=True, config={"displaylogo": False})


def header(title: str, f: q.Filters, note: str | None = None) -> None:
    st.title(title)
    st.info(BANNER, icon=":material/info:")
    parts = [f"PO months {f.months[0]} to {f.months[1]}", f.category or "all categories"]
    if f.spend_areas:
        parts.append("spend area: " + ", ".join(s or "(blank)" for s in f.spend_areas))
    if f.vendors:
        parts.append(f"{len(f.vendors)} vendor(s)")
    st.caption("Filters: " + " · ".join(parts) + (f"  \n{note}" if note else ""))


def item_list(df: pl.DataFrame, key: str, file_name: str) -> None:
    """Item table with row selection to open Item detail, plus CSV download (FR-12)."""
    if df.is_empty():
        st.write("No items.")
        return
    event = st.dataframe(df, key=key, on_select="rerun", selection_mode="single-row", hide_index=True, height=300)
    c1, c2 = st.columns([1, 1])
    rows = event.selection.rows
    if c1.button("Open selected item", key=f"{key}_open", disabled=not rows, icon=":material/open_in_new:"):
        st.session_state["case_id"] = df["case_id"][rows[0]]
        st.switch_page(PAGES["item"])
    c2.download_button(
        "Download CSV", df.write_csv(), file_name=file_name, mime="text/csv", key=f"{key}_csv",
        icon=":material/download:",
    )


# ---------- sidebar filters (FR-1) ----------

opts = run("options")
with st.sidebar:
    st.header("Filters")
    months = st.select_slider("PO month", options=list(q.COHORT_MONTHS), value=(q.COHORT_MONTHS[0], q.COHORT_MONTHS[-1]))
    category = st.selectbox(
        "Item category",
        ["All categories", *opts["categories"]],
        help="KPIs K1-K4, phases and variants use this category; with 'All categories' they use the main one, "
        "'3-way match, invoice before GR'.",
    )
    spend = st.multiselect("Spend area", opts["spend_areas"], format_func=lambda s: s or "(blank)")
    vendors = st.multiselect("Vendor", opts["vendors"], help=f"Vendors with at least {q.MIN_N} items in the cohort.")
F = q.Filters(
    months=tuple(months),
    category=None if category == "All categories" else category,
    spend_areas=tuple(spend),
    vendors=tuple(vendors),
)


# ---------- pages ----------

KPI_HELP = {
    "K1a": "Median days from PO creation to clearing, cleared items of the focus category.",
    "K1b": "90th percentile of days from PO creation to clearing, cleared items of the focus category.",
    "K2": "Median days from invoice receipt to clearing. Probably reflects payment terms (not testable in the log).",
    "K3": "Share of focus-category items with a clearing event. Deleted items count as not cleared.",
    "K4": "Share of focus-category items with both events where the invoice receipt is booked before the goods receipt.",
    "K5": "Share of items with a vendor invoice dated on an earlier calendar day than the PO.",
    "K6": "Share of cleared 3-way items with no price/quantity change, cancellation or payment block.",
    "K7": "Rework events per 100 cleared 3-way items (repeats counted).",
    "K8": "Share of cleared 3-way items with at least one payment-block removal.",
}


def page_overview() -> None:
    header(
        "Overview",
        F,
        f"K1-K4: {F.focus_category} · K5: all selected items · K6-K8: cleared 3-way items. "
        "Targets are assumptions (kpis/catalogue.md).",
    )
    k = run("kpis", F)
    m = run("kpis_monthly", F)
    ids = list(q.KPI_META)
    for row in range(0, len(ids), 3):
        cols = st.columns(3)
        for col, kid in zip(cols, ids[row : row + 3], strict=False):
            with col:
                kpi_tile(kid, k[kid], m[kid].to_list(), KPI_HELP[kid])
    st.caption("Small lines: monthly values, January to July 2018 (PO month).")
    if IMPACT.exists():  # US-14
        st.caption(
            ":material/science: Redesign options and their simulated effect (with 95% intervals): `impact/README.md`."
        )

    st.subheader("Headline findings under the current filters")
    rw = run("cycle_quantiles", F, "rework")
    by = {r["grp"]: r for r in rw.iter_rows(named=True)}
    lines = []
    if k["K4"] is not None:
        lines.append(f"- **{k['K4']:.1%}** of items had the invoice booked before the goods receipt (K4).")
    if "Touchless" in by and "With rework" in by:
        t, r = by["Touchless"]["median"], by["With rework"]["median"]
        lines.append(
            f"- Items with rework took a median **{r:.1f} days** against **{t:.1f}** for touchless items "
            f"({r - t:+.1f} days; association, not cause)."
        )
    if k["K1a"] is not None and k["K2"] is not None:
        lines.append(
            f"- Order to payment: median **{k['K1a']:.1f} days** (P90 {k['K1b']:.1f}); "
            f"{k['K2']:.1f} days of it come after the invoice receipt."
        )
    st.markdown("\n".join(lines) or "Too few items under these filters.")


def page_cycle_time() -> None:
    header("Cycle time", F, f"Phases and rankings: cleared items of {F.focus_category}.")
    ph = run("phases", F)
    st.subheader("Where the time goes")
    parts = ph.filter(pl.col("phase") != "PO to clearing (total)")
    total = ph.filter(pl.col("phase") == "PO to clearing (total)").to_dicts()[0]
    c1, c2 = st.columns([3, 2])
    with c1:
        show(
            bar_h(
                parts,
                "median_days",
                "phase",
                "Median days",
                "<b>%{y}</b><br>median %{x:.1f} days<br>P90 %{customdata.p90_days:.1f} days"
                "<br>items %{customdata.items:,}",
            )
        )
    with c2:
        if total["median_days"] is not None:
            st.metric("PO to clearing, median", f"{total['median_days']:.1f} d", border=True)
            st.metric("PO to clearing, P90", f"{total['p90_days']:.1f} d", border=True)
        st.caption(
            "Phase medians do not add up to the total median. Goods receipt to invoice receipt is negative "
            "when the invoice was booked first."
        )
    st.dataframe(ph, hide_index=True, column_config={
        "phase": "Phase",
        "median_days": st.column_config.NumberColumn("Median (days)", format="%.1f"),
        "p90_days": st.column_config.NumberColumn("P90 (days)", format="%.1f"),
        "items": st.column_config.NumberColumn("Items", format="localized"),
    })

    st.subheader("Distribution by item category")
    qd = run("cycle_quantiles", F, "item_category")
    if qd.is_empty():
        st.write("Too few cleared items.")
    else:
        show(box_from_quantiles(qd, "Days from PO creation to clearing (box: P25-P75, whiskers: P10-P90)"))

    st.subheader("Slowest spend areas and vendors")
    c1, c2 = st.columns(2)
    by = c1.radio("Group by", ["Spend area", "Vendor"], horizontal=True, key="ct_by")
    measure = c2.radio("Measure", ["Median", "P90"], horizontal=True, key="ct_measure")
    rk = run("ranking", F, "spend_area" if by == "Spend area" else "vendor_id", measure.lower())
    if rk.is_empty():
        st.write(f"No group has {q.MIN_N} or more items.")
        return
    col = f"{measure.lower()}_days"
    show(
        bar_h(
            rk.head(15),
            col,
            "grp",
            f"{measure} days, PO to clearing",
            "<b>%{y}</b><br>" + measure + " %{x:.1f} days<br>items %{customdata.items:,}"
            "<br>touchless %{customdata.touchless:.0%}",
        )
    )
    st.caption(f"Top 15 shown; groups with fewer than {q.MIN_N} items are left out. Full list below.")
    st.dataframe(rk, hide_index=True, column_config={
        "grp": by,
        "median_days": st.column_config.NumberColumn("Median (days)", format="%.1f"),
        "p90_days": st.column_config.NumberColumn("P90 (days)", format="%.1f"),
        "touchless": st.column_config.NumberColumn("Touchless", format="percent"),
    })


def page_compliance() -> None:
    header("Compliance", F)
    pop = st.radio(
        "Population",
        ["Cohort (POs Jan-Jul 2018)", "All items"],
        horizontal=True,
        help="Compliance does not depend on clearing, so it can use all items. The month filter is ignored then.",
    )
    all_items = pop == "All items"

    c1, c2 = st.columns(2)
    for col, kid, txt in (
        (c1, "K4", f"Invoice booked before goods receipt ({F.focus_category})"),
        (c2, "K5", "Vendor invoice dated before the PO (all selected categories)"),
    ):
        rate, n, b = run("compliance_rate", F, kid, all_items)
        with col:
            st.metric(f"{kid} · {txt}", "n/a" if rate is None else f"{rate:.1%}", border=True)
            st.caption(f"{b:,} of {n:,} items")

    if not all_items:
        m = run("kpis_monthly", F)
        fig = go.Figure()
        for kid, color, name in (("K4", BLUE, "K4 invoice before goods receipt"), ("K5", ORANGE, "K5 invoice before PO")):
            fig.add_trace(
                go.Scatter(
                    x=m["po_month"].to_list(), y=m[kid].to_list(), name=name, mode="lines+markers",
                    line={"color": color, "width": 2}, marker={"size": 8},
                    hovertemplate="%{x}: %{y:.1%}<extra>" + kid + "</extra>",
                )
            )
        fig.update_layout(
            height=280, margin={"l": 10, "r": 10, "t": 10, "b": 40}, yaxis_tickformat=".0%", yaxis_title="Share of items",
            xaxis_title="PO month", legend={"orientation": "h", "y": 1.15}, hovermode="x unified",
        )
        show(fig)

    st.subheader("How early was the invoice booked?")
    bins = run("ir_gr_gap_bins", F, all_items)
    if not bins.is_empty():
        show(bar_h(bins, "items", "bin", "Items (K4 breaches)", "<b>%{y}</b> before the goods receipt<br>%{x:,} items",
                   height=260))

    st.subheader("Where do breaches come from?")
    c1, c2 = st.columns(2)
    kid = c1.radio("Measure", ["K4", "K5"], horizontal=True, key="cp_kpi",
                   format_func=lambda k: "K4 invoice before goods receipt" if k == "K4" else "K5 invoice before PO")
    by_label = c2.radio("Group by", ["Vendor", "Spend area"], horizontal=True, key="cp_by")
    by = "vendor_id" if by_label == "Vendor" else "spend_area"
    br = run("compliance_breakdown", F, kid, by, all_items)
    if br.is_empty():
        st.write(f"No group has {q.MIN_N} or more items.")
        return
    show(bar_h(br.head(15), "breaches", "grp", "Items breaching",
               "<b>%{y}</b><br>%{x:,} of %{customdata.items:,} items (%{customdata.rate:.1%})"))
    st.caption(f"Top 15 by number of breaching items; groups under {q.MIN_N} items left out. "
               "Select a row to list its items.")
    sel = st.dataframe(br, key=f"cp_groups_{kid}_{by}", on_select="rerun", selection_mode="single-row",
                       hide_index=True, height=250, column_config={
                           "grp": by_label, "rate": st.column_config.NumberColumn("Rate", format="percent")})
    rows = sel.selection.rows
    group = br["grp"][rows[0]] if rows else None
    st.markdown(f"**Items breaching {kid}**" + (f" for {by_label.lower()} `{group}`" if group else " (all groups)"))
    items = run("compliance_items", F, kid, by if group else None, group, all_items)
    item_list(items, key=f"cp_items_{kid}", file_name=f"{kid.lower()}_items.csv")


def page_rework() -> None:
    header("Rework", F, "Cleared 3-way items (both 3-way categories).")
    k = run("kpis", F)
    m = run("kpis_monthly", F)
    cols = st.columns(3)
    for col, kid in zip(cols, ["K6", "K7", "K8"], strict=True):
        with col:
            kpi_tile(kid, k[kid], m[kid].to_list(), KPI_HELP[kid])

    st.subheader("Which rework goes with longer cycle times")
    rt = run("rework_types", F)
    plot = rt.filter(pl.col("gap_days").is_not_null()).sort("gap_days", descending=True)
    if not plot.is_empty():
        show(bar_h(plot, "gap_days", "activity", "Associated gap in median days (with minus without)",
                   "<b>%{y}</b><br>%{x:+.1f} days<br>%{customdata.items_with:,} items "
                   "(%{customdata.share:.1%})<br>median with %{customdata.median_with:.1f} · "
                   "without %{customdata.median_without:.1f}"))
    st.caption(
        "The gap compares medians of items with and without each activity. It is an association: harder orders "
        f"may attract both rework and delay. Activities with fewer than {q.MIN_N} items show no gap."
    )
    gap_text = rt.with_columns(  # DR-4: say why there is no gap instead of showing None
        pl.col("gap_days")
        .map_elements(lambda g: f"{g:+.1f}", return_dtype=pl.String)
        .fill_null(f"n < {q.MIN_N}")
    )
    st.dataframe(gap_text, hide_index=True, column_config={
        "activity": "Rework activity",
        "items_with": st.column_config.NumberColumn("Items with it", format="localized"),
        "share": st.column_config.NumberColumn("Share of items", format="percent"),
        "median_with": st.column_config.NumberColumn("Median with (days)", format="%.1f"),
        "median_without": st.column_config.NumberColumn("Median without (days)", format="%.1f"),
        "gap_days": st.column_config.TextColumn("Associated gap (days)"),
    })

    st.subheader("Touchless against rework items")
    qd = run("cycle_quantiles", F, "rework")
    if not qd.is_empty():
        show(box_from_quantiles(qd, "Days from PO creation to clearing (box: P25-P75, whiskers: P10-P90)"))

    st.subheader("Payment-block removals by group (K8)")
    by_label = st.radio("Group by", ["Spend area", "Vendor"], horizontal=True, key="rw_by")
    bb = run("block_breakdown", F, "spend_area" if by_label == "Spend area" else "vendor_id")
    if bb.is_empty():
        st.write(f"No group has {q.MIN_N} or more items.")
        return
    show(bar_h(bb.head(15), "rate", "grp", "Share of items with a block removal",
               "<b>%{y}</b><br>%{x:.1%} of %{customdata.items:,} items").update_xaxes(tickformat=".0%"))
    st.dataframe(bb, hide_index=True, column_config={
        "grp": by_label, "rate": st.column_config.NumberColumn("Block removal rate", format="percent")})


def page_process() -> None:
    header("Process", F, f"Variants: {F.focus_category}, all 42 activities.")
    st.subheader("Most frequent variants")
    tv = run("top_variants", F, 20)
    st.dataframe(tv, hide_index=True, column_config={
        "variant": st.column_config.TextColumn("Variant (activity sequence)", width="large"),
        "items": st.column_config.NumberColumn("Items", format="localized"),
        "share": st.column_config.NumberColumn("Share", format="percent"),
        "cumulative_share": st.column_config.ProgressColumn("Cumulative share", min_value=0.0, max_value=1.0,
                                                            format="percent"),
    })

    st.subheader("Conformance of the as-is model")
    s, groups = run("conformance")
    if not s["finished"]:
        st.warning("Conformance results not loaded. Run `make mining` and then `make warehouse`.")
        return
    st.caption(
        "One run of token-based replay on the main category, 9 modelled activities, all months "
        "(not affected by the filters). Method in mining/notes/05-conformance.md."
    )
    c1, c2, c3 = st.columns(3)
    c1.metric("Finished cases", f"{s['finished']:,}", border=True)
    c2.metric("Fitting the model", f"{s['fitting'] / s['finished']:.1%}", border=True)
    c3.metric("Weighted fitness", f"{s['weighted_fitness']:.3f}", border=True)
    show(bar_h(groups, "cases", "reason", "Finished cases not fitting",
               "<b>%{y}</b><br>%{x:,} cases (%{customdata.share_of_finished:.1%} of finished)<br>"
               "%{customdata.variants:,} variants", height=240))
    if BPMN_PNG.exists():
        st.image(str(BPMN_PNG), caption="As-is model: 3-way match, invoice before GR")


def page_item() -> None:
    st.title("Item detail")
    case_id = st.text_input("Case ID (PO number _ item)", value=st.session_state.get("case_id", DEFAULT_CASE))
    item, events = run("item_detail", case_id.strip())
    if item is None:
        st.warning(f"No item with case ID `{case_id}`.")
        return
    st.session_state["case_id"] = case_id.strip()
    c = st.columns(4)
    c[0].metric("Status", item["status"], border=True)
    c[1].metric("PO to clearing", "n/a" if item["po_to_clear_days"] is None else f"{item['po_to_clear_days']:.1f} d",
                border=True)
    c[2].metric("Events", f"{item['n_events']}", border=True)
    c[3].metric("Rework events", f"{item['n_rework']}", border=True)
    st.caption(
        f"{item['item_category']} · {item['item_type']} · spend area {item['spend_area'] or '(blank)'} / "
        f"{item['sub_spend_area']} · vendor {item['vendor_id']} · company {item['company_id']} · "
        f"in cohort: {'yes' if item['in_cohort'] else 'no'}"
    )
    flags = {
        "Invoice before goods receipt": item["ir_before_gr"],
        "Vendor invoice before PO": item["vi_before_po"],
        "Payment block removed": item["payment_block"],
    }
    st.markdown(" · ".join(f"{k}: **{'n/a' if v is None else 'yes' if v else 'no'}**" for k, v in flags.items()))

    shown = events.filter(~pl.col("suspect"))
    fig = go.Figure(
        go.Scatter(
            x=shown["timestamp"].to_list(), y=shown["lane"].to_list(), mode="markers+lines",
            line={"color": BLUE, "width": 2}, marker={"size": 10, "color": BLUE, "line": {"width": 2, "color": "white"},
                                                        "symbol": ["diamond" if d else "circle" for d in shown["date_only"]]},
            text=shown["activity"].to_list(),
            hovertemplate="<b>%{text}</b><br>%{x|%Y-%m-%d %H:%M}<br>%{y}<extra></extra>",
        )
    )
    fig.update_layout(height=300, margin={"l": 10, "r": 10, "t": 10, "b": 40}, xaxis_title="Event time")
    show(fig)
    st.caption("Diamonds: date-only timestamps (the time is a placeholder). Suspect-date events are listed but not plotted.")
    st.dataframe(events, hide_index=True, column_config={
        "net_worth_eur": st.column_config.NumberColumn("Net worth (EUR, indicative)", format="%.2f")})


def page_notes() -> None:
    st.title("Data notes")
    st.markdown(
        """
**Limits to keep in mind**

- **Clearing is cut off.** Clearing and invoice-receipt events stop in January 2019, while other events run to
  April 2020. All time, clearing and rework figures use POs created January to July 2018
  (`mining/notes/03-censoring.md`).
- **Date-only timestamps.** Vendor invoice, vendor debit memo and purchase requisition carry a date with a
  placeholder time (23:59 or 00:00), so durations touching them are in days.
- **Impossible dates.** 100 events (e.g. 1948) are flagged as suspect and left out of durations.
- **Payment blocks.** Setting a block is rarely logged (124 events against 57,136 removals), so removals stand in.
- **"Received, never invoiced"** in the invoice-after-GR category is partly a truncation effect and is not a finding.
- **Associations, not causes.** Gaps between groups (for example rework against touchless) have no controls.
- **Anonymised data.** Vendors, users and companies are IDs; there is no written policy, so KPI targets are
  assumptions.
- **Data copy.** A third-party CSV conversion of the log was used because data.4tu.nl timed out (see `data/SOURCE.md`).

**Dataset:** van Dongen, B.F. (2019). BPI Challenge 2019. 4TU.ResearchData.
[doi:10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1](https://doi.org/10.4121/uuid:d06aff4b-79f0-45e6-8ec8-e19730c248f1)
"""
    )
    info = run("build_info")
    st.subheader("Warehouse build")
    st.markdown(
        f"Built **{info['built_at']:%Y-%m-%d %H:%M}** from `{info['source']}`. "
        f"Conformance results: `{info['conformance_source'] or 'not loaded'}`."
    )
    st.dataframe(pl.DataFrame({"table": list(info["counts"]), "rows": list(info["counts"].values())}),
                 hide_index=True)


# START_PAGE lets tests open a given page first (AppTest cannot switch to function pages)
START_PAGE = os.environ.get("P2P_START_PAGE", "overview")
_PAGE_SPECS = {
    "overview": (page_overview, "Overview", ":material/dashboard:", "overview"),
    "cycle": (page_cycle_time, "Cycle time", ":material/schedule:", "cycle-time"),
    "compliance": (page_compliance, "Compliance", ":material/rule:", "compliance"),
    "rework": (page_rework, "Rework", ":material/autorenew:", "rework"),
    "process": (page_process, "Process", ":material/account_tree:", "process"),
    "item": (page_item, "Item detail", ":material/search:", "item"),
    "notes": (page_notes, "Data notes", ":material/description:", "data-notes"),
}
PAGES = {
    key: st.Page(fn, title=title, icon=icon, url_path=path, default=key == START_PAGE)
    for key, (fn, title, icon, path) in _PAGE_SPECS.items()
}

st.navigation(list(PAGES.values())).run()
