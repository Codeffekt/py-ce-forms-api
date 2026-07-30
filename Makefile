PYTHON ?= .venv/bin/python
PYTEST ?= .venv/bin/pytest

.PHONY: help venv test test-cov test-all clean-test

help:
	@echo "make venv      - create .venv and install the package + test dependencies"
	@echo "make test      - run the unit test suite"
	@echo "make test-cov  - run the suite with a coverage report"
	@echo "make test-all  - also run the tests marked 'integration' (needs CE_FORMS_* env)"

venv:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements-dev.txt
	$(PYTHON) -m pip install -e .

test:
	$(PYTEST)

test-cov:
	$(PYTEST) --cov=py_ce_forms_api --cov-report=term-missing --cov-report=html

test-all:
	$(PYTEST) -m ""

clean-test:
	rm -rf .pytest_cache .coverage htmlcov
