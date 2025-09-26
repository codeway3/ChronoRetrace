# Makefile for ChronoRetrace project

.PHONY: help install install-dev test-backend test-backend-cov lint format clean dev-setup check-all

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

install:
	@echo "Installing production dependencies..."
	cd backend && source ../venv/bin/activate && pip install -r requirements.txt

install-dev:
	@echo "Installing development dependencies..."
	cd backend && source ../venv/bin/activate && pip install -r requirements-dev.txt

test-backend:
	@echo "Running backend unit tests..."
	cd backend && source ../venv/bin/activate && python -m pytest -v

test-backend-cov:
	@echo "Running backend tests with coverage..."
	cd backend && source ../venv/bin/activate && python -m pytest --cov=app --cov-report=html --cov-report=term-missing

lint:
	@echo "Running backend linter..."
	cd backend && source ../venv/bin/activate && python -m black --check .
	cd backend && source ../venv/bin/activate && python -m ruff check .

format:
	@echo "Formatting backend code..."
	cd backend && source ../venv/bin/activate && python -m black .
	cd backend && source ../venv/bin/activate && python -m ruff check . --fix
	@echo "Code formatting completed."

check-all: lint test-backend
	@echo "All checks completed successfully!"

dev-setup:
	@echo "Setting up development environment..."
	@echo "Creating virtual environment if it doesn't exist..."
	@test -d venv || python3 -m venv venv
	@echo "Installing development dependencies..."
	@. venv/bin/activate && $(MAKE) install-dev
	@echo "Development environment setup completed!"

clean:
	@echo "Cleaning cache and temporary files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "htmlcov" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true
	@echo "Cleanup completed!"
