#!/usr/bin/env python3
from __future__ import annotations

"""Compatibility entry point for the final Figures 2–5 generator.

The former standalone implementation was retired because it could regenerate
outdated taxonomy labels and place NMDS/RDA legends over scientific panels.
This command now executes the same final generator and source modules used by
the public application.
"""

from pathlib import Path
import runpy


FINAL_SCRIPT = (
  Path(__file__).resolve().parent
  / "final_publication_figures"
  / "02_05_generate_final_taxonomy_figures.py"
)

if not FINAL_SCRIPT.exists():
  raise FileNotFoundError(f"Final taxonomy generator not found: {FINAL_SCRIPT}")

runpy.run_path(str(FINAL_SCRIPT), run_name="__main__")
