#!/usr/bin/env python3
"""Launcher for the Tkinter desktop app (ui_app/app.py)."""
from pathlib import Path
import sys

# Ensure project root on sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from ui_app.app import main


if __name__ == "__main__":
    main()
