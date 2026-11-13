"""Token-based replay of the as-is BPMN ("3-way match, invoice before GR") on a variant-level log."""

from datetime import timedelta
from pathlib import Path

import pm4py
import polars as pl
from pm4py.objects.log.obj import Event, EventLog, Trace

CATEGORY = "3-way match, invoice before GR"
BPMN = "bpmn/asis_3way_invoice_before_gr.bpmn"
OUT = Path("mining/outputs/conformance_invoice_before_gr.csv")
SEP = " > "
VI, IR, PO = "Vendor creates invoice", "Record Invoice Receipt", "Create Purchase Order Item"
MODELLED = [
    "Create Purchase Requisition Item",
    PO,
    "Delete Purchase Order Item",
    "Receive Order Confirmation",
    VI,
    "Record Goods Receipt",
    IR,
    "Remove Payment Block",
    "Clear Invoice",
]

# keep only this category, non-suspect events, and the activities the model contains
df = pl.read_parquet("data/interim/events_clean.parquet").filter(
    ~pl.col("ts_suspect"),
    pl.col("item_category") == CATEGORY,
    pl.col("activity").is_in(MODELLED),
)

# Same-day tie-break: "Vendor creates invoice" is date-only (placeholder 23:59 or 00:00), so on a day
# that also has a "Record Invoice Receipt" it can sort after the receipt it caused. Move it to just
# before the first same-day invoice receipt. Other orderings are left as logged.
ir_day = (
    df.filter(pl.col("activity") == IR)
    .group_by("case_id", pl.col("timestamp").dt.date().alias("day"))
    .agg(pl.col("timestamp").min().alias("ir_first"))
)
df = (
    df.with_columns(pl.col("timestamp").dt.date().alias("day"))
    .join(ir_day, on=["case_id", "day"], how="left")
    .with_columns(
        (
            (pl.col("activity") == VI) & pl.col("ir_first").is_not_null() & (pl.col("timestamp") > pl.col("ir_first"))
        ).alias("moved")
    )
    .with_columns(
        pl.when(pl.col("moved"))
        .then(pl.col("ir_first") - timedelta(microseconds=1))
        .otherwise(pl.col("timestamp"))
        .alias("sort_ts")
    )
    .sort("case_id", "sort_ts", "event_id_int")
)
moved = df.filter(pl.col("moved"))
print(f"tie-break: {moved.height:,} vendor-invoice events moved before a same-day invoice receipt "
      f"({moved['case_id'].n_unique():,} cases)")

variants = (
    df.group_by("case_id", maintain_order=True)
    .agg(pl.col("activity"))
    .with_columns(pl.col("activity").list.join(SEP).alias("variant"))
    .group_by("variant")
    .agg(pl.len().alias("cases"))
    .sort("cases", descending=True)
)

# one trace per variant (the counts carry the weight)
log = EventLog()
for variant, _ in variants.iter_rows():
    trace = Trace()
    for act in variant.split(SEP):
        trace.append(Event({"concept:name": act}))
    log.append(trace)

net, im, fm = pm4py.convert_to_petri_net(pm4py.read_bpmn(BPMN))
res = pm4py.conformance_diagnostics_token_based_replay(log, net, im, fm)

out = variants.with_columns(
    pl.Series("fit", [r["trace_is_fit"] for r in res]),
    pl.Series("fitness", [r["trace_fitness"] for r in res]),
    pl.Series("missing", [r["missing_tokens"] for r in res]),
    pl.Series("remaining", [r["remaining_tokens"] for r in res]),
    pl.col("variant").str.contains("Clear Invoice|Delete Purchase Order Item").alias("ended"),
)


def summary(d: pl.DataFrame, label: str) -> None:
    total = d["cases"].sum()
    fit = d.filter(pl.col("fit"))["cases"].sum()
    wfit = (d["fitness"] * d["cases"]).sum() / total
    print(f"{label}: {total} cases | fitting {fit} ({fit / total:.1%}) | weighted fitness {wfit:.3f}")


summary(out, "all cases")
summary(out.filter(pl.col("ended")), "cases that reach clearing or deletion")

# rough classification of each variant (first matching rule wins); saved with the results
acts = pl.col("variant").str.split(SEP)
first_pos = lambda act: acts.list.eval(pl.element().index_of(act)).list.first()
out = out.with_columns(
    pl.when(pl.col("fit"))
    .then(pl.lit("fits"))
    .when(~pl.col("ended"))
    .then(pl.lit("not finished"))
    .when(acts.list.len() > acts.list.unique().list.len())
    .then(pl.lit("repeated activity (GR, IR, clearing or block removal)"))
    .when(first_pos(VI).is_not_null() & (first_pos(VI) < first_pos(PO)))
    .then(pl.lit("vendor invoice before PO"))
    .when(first_pos(IR).is_not_null() & (first_pos(VI).is_null() | (first_pos(IR) < first_pos(VI))))
    .then(pl.lit("invoice receipt without preceding vendor invoice"))
    .otherwise(pl.lit("other ordering or missing step"))
    .alias("reason")
)

pl.Config.set_fmt_str_lengths(160)
pl.Config.set_tbl_width_chars(260)
print(out.filter(~pl.col("fit")).head(15).select("cases", "fitness", "missing", "remaining", "variant"))
OUT.parent.mkdir(parents=True, exist_ok=True)
out.write_csv(OUT)

finished_bad = out.filter(~pl.col("fit"), pl.col("ended"))
print("finished but not fitting:", finished_bad["cases"].sum(), "cases,", finished_bad.height, "variants")
print(finished_bad.head(20).select("cases", "fitness", "missing", "remaining", "variant"))

print("\n== Remaining deviations, finished cases ==")
print(
    finished_bad.group_by("reason")
    .agg(pl.col("cases").sum(), pl.len().alias("variants"))
    .with_columns((pl.col("cases") / out.filter(pl.col("ended"))["cases"].sum()).round(4).alias("share_of_finished"))
    .sort("cases", descending=True)
)
