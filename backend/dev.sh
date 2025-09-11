#!/bin/bash

# Development helper script for ChronoRetrace Backend
# Usage: ./dev.sh [command]
# Examples:
#   ./dev.sh test                    # Run all tests
#   ./dev.sh test tests/unit/        # Run unit tests
#   ./dev.sh server                  # Start development server
#   ./dev.sh shell                   # Start Python shell with proper environment
#   ./dev.sh lint                    # Run code linting
#   ./dev.sh format                  # Format code

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Set PYTHONPATH to include the backend directory
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# Load environment variables from .env file
if [ -f "$SCRIPT_DIR/.env" ]; then
    export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 [command]"
    echo "Commands:"
    echo "  test [path]     Run tests (optionally specify path)"
    echo "  server          Start development server"
    echo "  shell           Start Python shell"
    echo "  lint            Run ruff linting"
    echo "  format          Format code with ruff"
    echo "  migrate         Run database migrations"
    echo "  help            Show this help message"
}

# Main command handling
case "$1" in
    "test")
        if [ -n "$2" ]; then
            python -m pytest "$2" -v
        else
            python -m pytest tests/ -v
        fi
        ;;
    "server")
        python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
        ;;
    "shell")
        python -i -c "import sys; print('Python shell with ChronoRetrace environment loaded'); print(f'PYTHONPATH: {sys.path[0:3]}...')"
        ;;
    "lint")
        ruff check .
        ;;
    "format")
        ruff check . --fix
        ruff format .
        ;;
    "migrate")
        python run_migrations.py
        ;;
    "help"|"")
        show_usage
        ;;
    *)
        echo "Unknown command: $1"
        show_usage
        exit 1
        ;;
esac