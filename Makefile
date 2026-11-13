.PHONY: all ingest test lint mining

all: ingest

ingest:
	uv run python src/p2p/ingest.py
	uv run python src/p2p/clean.py

# analysis scripts in order; console output kept under mining/outputs/ (git-ignored)
MINING = variants censoring throughput deviations open_and_rework uncleared_invoices cohort_metrics conformance

mining:
	mkdir -p mining/outputs
	@for s in $(MINING); do 		echo "== $$s"; 		PYTHONIOENCODING=utf-8 uv run python mining/$$s.py > mining/outputs/$$s.txt || exit 1; 	done

test:
	uv run pytest

lint:
	uv run ruff check .
