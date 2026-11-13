"""Build the DuckDB star schema (model/schema.sql, model/load.sql) from the cleaned event log.

Run: uv run python src/p2p/warehouse.py   (or `make warehouse`)
Output: data/warehouse/p2p.duckdb (git-ignored, rebuilt from scratch each run).
Conformance results are loaded from mining/outputs/ when present (`make mining` writes them).
"""

from pathlib import Path

import duckdb

CLEAN = Path("data/interim/events_clean.parquet")
ACTIVITY_MAP = Path("model/activity_map.csv")
CONFORMANCE = Path("mining/outputs/conformance_invoice_before_gr.csv")
SCHEMA = Path("model/schema.sql")
LOAD = Path("model/load.sql")
DB = Path("data/warehouse/p2p.duckdb")
TABLES = [
    "dim_date",
    "dim_activity",
    "dim_vendor",
    "dim_company",
    "dim_user",
    "dim_item",
    "fact_event",
    "fact_item",
    "conformance_variant",
]


def build(db: Path = DB, conformance: Path = CONFORMANCE) -> None:
    db.parent.mkdir(parents=True, exist_ok=True)
    db.unlink(missing_ok=True)
    with duckdb.connect(str(db)) as con:
        con.execute(f"CREATE TEMP VIEW src_events AS SELECT * FROM read_parquet('{CLEAN.as_posix()}')")
        con.execute(
            f"""CREATE TEMP VIEW src_activity_map AS
                SELECT * FROM read_csv('{ACTIVITY_MAP.as_posix()}', header = true,
                    columns = {{'activity': 'VARCHAR', 'lane': 'VARCHAR', 'stage': 'VARCHAR',
                                'is_rework': 'BOOLEAN', 'is_modelled': 'BOOLEAN'}})"""
        )
        unmapped = con.sql(
            "SELECT DISTINCT activity FROM src_events EXCEPT SELECT activity FROM src_activity_map"
        ).fetchall()
        if unmapped:
            raise ValueError(f"activities missing from {ACTIVITY_MAP}: {unmapped}")
        con.execute(SCHEMA.read_text(encoding="utf-8"))
        con.execute(LOAD.read_text(encoding="utf-8"))

        if conformance.exists():
            con.execute(
                f"""INSERT INTO conformance_variant
                    SELECT variant, cases, fit, fitness, missing, remaining, ended, reason
                    FROM read_csv('{conformance.as_posix()}', header = true)"""
            )
            source = conformance.as_posix()
        else:
            print(f"warning: {conformance} not found, run `make mining` first; conformance table left empty")
            source = None
        con.execute("INSERT INTO build_info VALUES (now()::TIMESTAMP, ?, ?)", [CLEAN.as_posix(), source])

        for t in TABLES:
            print(f"{t:20s} {con.execute(f'SELECT count(*) FROM {t}').fetchall()[0][0]:>10,}")


if __name__ == "__main__":
    build()
