# Makefile for ChronoRetrace project

.PHONY: help test-backend

help:
	@echo "Available commands:"
	@echo "  make test-backend   - Run backend unit tests and linter checks."
	@echo "                      (Note: Please activate your backend virtual environment first!)"

test-backend:
	@echo "--- Running backend unit tests (using your activated virtual environment) ---"
	@cd backend && /usr/local/bin/python3.10 -m pytest
	@echo "\n--- Running backend linter (using your activated virtual environment) ---"
	@cd backend && /usr/local/bin/python3.10 -m ruff check .
	@echo "\n--- Backend checks complete ---"


