"""Smoke test: every dashboard page renders without an exception (AppTest, no browser)."""

import pytest
from conftest import needs_data
from streamlit.testing.v1 import AppTest

pytestmark = needs_data
PAGES = ["overview", "cycle", "compliance", "rework", "process", "item", "notes"]


@pytest.mark.parametrize("page", PAGES)
def test_page_renders(warehouse_db, monkeypatch, page):
    monkeypatch.setenv("P2P_DB", str(warehouse_db))
    monkeypatch.setenv("P2P_START_PAGE", page)
    at = AppTest.from_file("../app/app.py", default_timeout=120).run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.title, "page has no title"


def test_overview_shows_all_kpis(warehouse_db, monkeypatch):
    monkeypatch.setenv("P2P_DB", str(warehouse_db))
    at = AppTest.from_file("../app/app.py", default_timeout=120).run()
    labels = [m.label for m in at.metric]
    assert len(labels) == 9 and labels[0].startswith("K1a")
    assert at.metric[0].value == "79.3 d"


def test_category_filter_updates_kpis(warehouse_db, monkeypatch):
    monkeypatch.setenv("P2P_DB", str(warehouse_db))
    at = AppTest.from_file("../app/app.py", default_timeout=120).run()
    at.sidebar.selectbox[0].select("3-way match, invoice after GR").run()
    assert not at.exception
    assert at.metric[0].value == "79.1 d"  # note 04: invoice after GR median
