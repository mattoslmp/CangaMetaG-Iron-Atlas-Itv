from __future__ import annotations

"""Compatibility entry point for the complete no-satellite CangaMetaG app.

Keep this file inside the project root beside ``app.py`` and the ``src``
directory. Run with:

    python -m streamlit run app_no_satellite_final.py

The wrapper executes the canonical ``app.py`` from the same directory, so only
one active implementation of the application is maintained.
"""

from pathlib import Path
import runpy
import sys

PROJECT_ROOT = Path(__file__).resolve().parent
SRC_DIR = PROJECT_ROOT / "src"
CANONICAL_APP = PROJECT_ROOT / "app.py"

if not SRC_DIR.is_dir() or not (SRC_DIR / "runtime_preflight.py").is_file():
  raise RuntimeError(
    "Incomplete CangaMetaG package: src/runtime_preflight.py was not found. "
    "Do not copy this launcher alone. Extract the complete ZIP and run it from "
    "the project folder that contains app.py, src/, data/, tables/, outputs/ "
    "and scripts/."
  )
if not CANONICAL_APP.is_file():
  raise RuntimeError(f"Canonical app.py was not found at: {CANONICAL_APP}")
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

runpy.run_path(str(CANONICAL_APP), run_name="__main__")
