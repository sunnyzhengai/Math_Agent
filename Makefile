.PHONY: test test-verbose test-approve clean help

help:
	@echo "Available targets:"
	@echo "  make test              Run all tests"
	@echo "  make test-verbose      Run tests with verbose output"
	@echo "  make test-approve      Run tests and approve snapshot changes"
	@echo "  make test-fast         Run tests without coverage"
	@echo "  make clean             Remove test artifacts"

test:
	pytest -q

test-verbose:
	pytest -v

test-approve:
	APPROVE=1 pytest -v

test-fast:
	pytest tests/ -q --tb=short

clean:
	rm -rf .pytest_cache __pycache__ tests/__pycache__ tests/goldens/__pycache__
	find . -name "*.pyc" -delete
	find . -name ".pytest_cache" -type d -exec rm -rf {} +

.DEFAULT_GOAL := help
