.PHONY: all ingest test lint mining kpis warehouse simulate app

# full pipeline: data -> analysis -> KPIs -> warehouse -> simulation
all: ingest mining kpis warehouse simulate

ingest:
	uv run python src/p2p/ingest.py
	uv run python src/p2p/clean.py

# analysis scripts in order; console output kept under mining/outputs/ (git-ignored)
MINING = variants censoring throughput deviations open_and_rework uncleared_invoices cohort_metrics conformance

mining:
	mkdir -p mining/outputs
	@for s in $(MINING); do \
		echo "== $$s"; \
		PYTHONIOENCODING=utf-8 uv run python mining/$$s.py > mining/outputs/$$s.txt || exit 1; \
	done

kpis:
	PYTHONIOENCODING=utf-8 uv run python src/p2p/kpis.py

warehouse:
	uv run python src/p2p/warehouse.py

simulate:
	PYTHONIOENCODING=utf-8 uv run python src/p2p/simulation.py

app:
	uv run streamlit run app/app.py

test:
	uv run pytest

lint:
	uv run ruff check .
