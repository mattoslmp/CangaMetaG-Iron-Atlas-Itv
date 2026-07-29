#!/usr/bin/env python3
"""Portable launcher that always runs Streamlit from the project root."""
from pathlib import Path
import subprocess
import sys

root = Path(__file__).resolve().parent
check = subprocess.run([sys.executable, str(root / "scripts" / "check_app_runtime.py")], cwd=root)
if check.returncode:
  raise SystemExit(check.returncode)
raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", "app.py"], cwd=root))
