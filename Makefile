# Makefile for ChronoRetrace project

.PHONY: help install install-dev test-backend test-backend-cov lint format clean dev-setup check-all python-version-check create-venv

# Python interpreter inside the project venv
PY := venv/bin/python

# Default target
help:
	@echo "Available commands:"
	@echo "  install      - Install production dependencies"
	@echo "  install-dev  - Install development dependencies"
	@echo "  test-backend - Run backend tests"
	@echo "  test-backend-cov - Run backend tests with coverage"
	@echo "  lint         - Run linting checks"
	@echo "  format       - Format code"
	@echo "  check-all    - Run all checks (lint + test)"
	@echo "  dev-setup    - Setup development environment"
	@echo "  clean        - Clean cache and temporary files"
	@echo "  python-version-check - Verify venv is Python 3.10"
	@echo "  create-venv  - Create venv using python3.10"

install: python-version-check
	@echo "Installing production dependencies..."
	cd backend && ../venv/bin/python -m pip install -r requirements.txt

install-dev: python-version-check
	@echo "Installing development dependencies..."
	cd backend && ../venv/bin/python -m pip install -r requirements-dev.txt

test-backend: python-version-check
	@echo "Running backend unit tests..."
	cd backend && ../venv/bin/python -m pytest -v

test-backend-cov: python-version-check
	@echo "Running backend tests with coverage..."
	cd backend && ../venv/bin/python -m pytest --cov=app --cov-report=html --cov-report=term-missing

lint: python-version-check
	@echo "Running backend linter..."
	cd backend && ../venv/bin/python -m black --check .
	cd backend && ../venv/bin/python -m ruff check .

format: python-version-check
	@echo "Formatting backend code..."
	cd backend && ../venv/bin/python -m black .
	cd backend && ../venv/bin/python -m ruff check . --fix
	@echo "Code formatting completed."

check-all: lint test-backend
	@echo "All checks completed successfully!"

dev-setup:
	@echo "Setting up development environment..."
	$(MAKE) create-venv
	$(MAKE) python-version-check
	@$(PY) -m pip install --upgrade pip
	@$(MAKE) install-dev
	@echo "Development environment setup completed!"

python-version-check:
	@test -x venv/bin/python || (echo "Virtualenv not found. Run 'make create-venv' first."; exit 1)
	@$(PY) -c 'import sys; assert sys.version_info[:2]==(3,10), f"Python 3.10 required, found {sys.version}"'
	@echo "Python version verified: 3.10"

create-venv:
	@if ! command -v python3.10 >/dev/null 2>&1; then echo "python3.10 not found. Please install Python 3.10 (e.g., brew install python@3.10 or apt-get install python3.10)."; exit 1; fi
	@test -d venv || python3.10 -m venv venv
	@echo "Virtual environment created with Python 3.10."

clean:
	@echo "Cleaning cache and temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "Cleanup completed!"
