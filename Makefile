.PHONY: help install install-dev test test-unit test-integration lint format type-check clean run-dev docker-build docker-up docker-down gmail-analyze gmail-preview gmail-cleanup

help:
	@echo "Available commands:"
	@echo "  make install          - Install production dependencies"
	@echo "  make install-dev      - Install development dependencies"
	@echo "  make test             - Run all tests"
	@echo "  make test-unit        - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make lint             - Run linting (ruff)"
	@echo "  make format           - Format code (black + ruff)"
	@echo "  make type-check       - Run type checking (mypy)"
	@echo "  make clean            - Clean build artifacts"
	@echo "  make run-dev          - Run in development mode"
	@echo ""
	@echo "Gmail Cleanup commands:"
	@echo "  make gmail-analyze    - Analyze Gmail inbox"
	@echo "  make gmail-preview    - Preview cleanup actions"
	@echo "  make gmail-cleanup    - Execute cleanup"

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,openai,anthropic,vectordb,observability]"
	pre-commit install

test:
	pytest

test-unit:
	pytest -m unit

test-integration:
	pytest -m integration

lint:
	ruff check src tests

format:
	black src tests
	ruff check --fix src tests

type-check:
	mypy src

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache
	rm -rf .coverage htmlcov/

run-dev:
	python -m src.main

docker-build:
	docker-compose build

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

# Gmail Cleanup commands
gmail-analyze:
	python scripts/run_gmail_cleanup.py --user-id=default --analyze-only --verbose

gmail-preview:
	python scripts/run_gmail_cleanup.py --user-id=default --dry-run --verbose

gmail-cleanup:
	python scripts/run_gmail_cleanup.py --user-id=default --quick --verbose
