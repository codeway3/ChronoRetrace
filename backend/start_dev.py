#!/usr/bin/env python3
"""
Development server startup script for ChronoRetrace backend.
This script configures uvicorn to only watch the backend directory for changes,
avoiding issues with frontend node_modules directory.
"""

import uvicorn
from pathlib import Path

if __name__ == "__main__":
    # Get the backend directory path
    backend_dir = Path(__file__).parent.absolute()

    # Configure uvicorn to only reload based on changes in the backend directory
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=[str(backend_dir)],  # Only watch the backend directory
        log_level="info"
    )
