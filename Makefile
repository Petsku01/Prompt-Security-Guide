PYTHON ?= python3

.PHONY: help install dev test cli-help automation-help daily clean

help:
	@echo "Targets:"
	@echo "  make install         Install package"
	@echo "  make dev             Install with dev extras"
	@echo "  make test            Run pytest suite"
	@echo "  make cli-help        Show PSG CLI help"
	@echo "  make automation-help Show automation CLI help"
	@echo "  make daily           Run daily automation pipeline script"
	@echo "  make clean           Remove pytest/mypy/ruff caches + __pycache__"

install:
	$(PYTHON) -m pip install .

dev:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	$(PYTHON) -m pytest

cli-help:
	$(PYTHON) -m psg --help

automation-help:
	$(PYTHON) -m psg.automation --help

daily:
	bash scripts/run_daily_pipeline.sh

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache
	find . -path ./.git -prune -o -name "__pycache__" -type d -print -exec rm -rf {} + 2>/dev/null; true
