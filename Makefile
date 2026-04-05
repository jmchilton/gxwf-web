VENV?=.venv
IN_VENV=if [ -f $(VENV)/bin/activate ]; then . $(VENV)/bin/activate; fi;
SOURCE_DIR?=src/galaxy_workflow_dev_webapp
TEST_DIR?=tests
DOCS_DIR?=docs

.PHONY: clean-pyc clean-build docs clean

help: ## show this help
	@egrep '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

clean: clean-build clean-pyc clean-test ## remove all build, test, coverage and Python artifacts

clean-build: ## remove build artifacts
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info
	rm -fr src/*.egg-info

clean-pyc: ## remove Python file artifacts
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test: ## remove test and coverage artifacts
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/

setup-venv: ## setup a development virtualenv in current directory
	if command -v uv > /dev/null 2>&1; then \
		uv sync --group test --group lint --group mypy; \
	else \
		if [ ! -d $(VENV) ]; then \
			python3 -m venv $(VENV); \
		fi; \
		$(IN_VENV) pip install -e ".[dev]"; \
	fi

setup-git-hook-lint: ## setup precommit hook for linting
	cp scripts/pre-commit-lint .git/hooks/pre-commit

lint: ## check style with ruff, isort, and black
	uv run --group lint isort --check --diff .
	uv run --group lint ruff check
	uv run --group lint black --check --diff .

format: ## auto-format with isort and black
	uv run --group lint isort .
	uv run --group lint black .

mypy: ## run type checking
	uv run --group mypy mypy $(SOURCE_DIR)

test: ## run tests with pytest
	uv run --group test pytest $(TEST_DIR)/

tox: ## run tests with tox in the specified ENV
	$(IN_VENV) tox -e $(ENV) -- $(ARGS)

coverage: ## check code coverage
	uv run --group test coverage run --source $(SOURCE_DIR) -m pytest $(TEST_DIR)
	uv run --group test coverage report -m
	uv run --group test coverage html
	open htmlcov/index.html || xdg-open htmlcov/index.html

docs-openapi: ## regenerate committed OpenAPI schema dump
	uv run --group docs galaxy-workflow-dev --output-schema $(DOCS_DIR)/_static/openapi.json

docs-clean: ## remove built docs
	rm -rf $(DOCS_DIR)/_build

docs: docs-openapi ## generate Sphinx HTML documentation (warnings as errors)
	uv run --group docs sphinx-build -W -b html $(DOCS_DIR) $(DOCS_DIR)/_build/html

docs-serve: docs ## serve built docs on http://127.0.0.1:8001
	cd $(DOCS_DIR)/_build/html && python3 -m http.server 8001

open-docs: docs ## generate Sphinx HTML documentation and open in browser
	open $(DOCS_DIR)/_build/html/index.html || xdg-open $(DOCS_DIR)/_build/html/index.html

dist: clean ## package
	$(IN_VENV) python -m build
	$(IN_VENV) twine check dist/*
	ls -l dist
