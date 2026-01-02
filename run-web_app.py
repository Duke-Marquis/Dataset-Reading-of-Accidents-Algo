#!/usr/bin/env python3
"""Entry point to run the Flask web application.

Usage:
    python3 run-web_app.py
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from web_app.web_app import app, load_initial_data

if __name__ == "__main__":
    print("Loading initial data...")
    load_initial_data()
    print("Starting web server...")
    print("Open your browser to: http://localhost:5001")
    app.run(debug=True, host="0.0.0.0", port=5001)
