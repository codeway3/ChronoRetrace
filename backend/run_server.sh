#!/bin/bash
# ChronoRetrace Backend Development Server
# This script starts uvicorn with proper reload directory configuration
# to avoid FileNotFoundError with frontend/node_modules/.cache

cd "$(dirname "$0")"

echo "Starting ChronoRetrace backend server..."
echo "Backend directory: $(pwd)"

# Start uvicorn with reload limited to backend directory only
uvicorn app.main:app \
    --host 127.0.0.1 \
    --port 8000 \
    --reload \
    --reload-dir . \
    --log-level info

echo "Server stopped."