# Development Guide (Python 3.10 Standard)

This document describes the standardized development environment for ChronoRetrace pinned to Python 3.10.

## Python Version Requirement

- Required: Python 3.10 (exact)
- Reason: The codebase uses Python 3.10 syntax (e.g., `X | None` unions) and is validated in CI/CD with Python 3.10.

## Setup Steps

1. Install Python 3.10
   - macOS: `brew install python@3.10`
   - Ubuntu/Debian: `sudo apt-get install -y python3.10 python3.10-venv`
   - Verify: `python3.10 --version`

2. Create virtual environment
   - Run: `make create-venv`
   - Verify version: `make python-version-check`

3. Install dependencies
   - Dev deps: `make install-dev`
   - Prod deps: `make install`

4. Run tests and checks
   - Unit tests: `make test-backend`
   - Coverage: `make test-backend-cov`
   - Lint: `make lint`
   - Format: `make format`

## CI/CD Standardization

- GitHub Actions pins `PYTHON_VERSION=3.10` and verifies at runtime.
- All Python commands use `python -m <tool>` to avoid PATH issues.

## Upgrade Guide (from Python 3.9/3.11 to 3.10)

1. Remove existing venv (if wrong version)
   - `rm -rf venv`

2. Install Python 3.10 and recreate venv
   - `python3.10 -m venv venv`
   - Or: `make create-venv`

3. Reinstall dependencies
   - `make install-dev`

4. Validate environment
   - `make python-version-check`
   - `make test-backend`

## Compatibility Notes

- Pydantic models use Python 3.10 union syntax (`str | None`).
- Async features and type hints assume Python 3.10 behavior.
- If third-party packages drop 3.10 support, pin versions in `requirements*.txt` and open an issue.

## Troubleshooting

- If `python3.10` is not found:
  - macOS: `brew update && brew install python@3.10`
  - Ubuntu: enable `deadsnakes` PPA, then `sudo apt install python3.10`
- If Make targets fail version check:
  - Run `make create-venv` then `make python-version-check`.