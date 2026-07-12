PYTHON ?= .venv/bin/python

.PHONY: help test freeze-check compile check

help:
	@echo "test         Run the deterministic test suite"
	@echo "freeze-check Verify the frozen evaluation manifest"
	@echo "compile      Compile Python sources as a syntax check"
	@echo "check        Run all contributor checks"

test:
	$(PYTHON) -m unittest discover -s tests -v

freeze-check:
	$(PYTHON) scripts/freeze_eval.py check --version v1

compile:
	$(PYTHON) -m compileall -q scripts tests

check: compile test freeze-check
