from pathlib import Path

import duckdb
import pytest

from p2p.warehouse import CLEAN, build

needs_data = pytest.mark.skipif(not Path(CLEAN).exists(), reason="run `make ingest` first")


@pytest.fixture(scope="session")
def warehouse_db(tmp_path_factory) -> Path:
    """A fresh warehouse built once per test session (about 15 s)."""
    db = tmp_path_factory.mktemp("wh") / "p2p.duckdb"
    build(db)
    return db


@pytest.fixture(scope="session")
def con(warehouse_db):
    c = duckdb.connect(str(warehouse_db), read_only=True)
    yield c
    c.close()
