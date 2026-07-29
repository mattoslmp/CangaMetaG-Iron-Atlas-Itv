#!/usr/bin/env python3
"""Backward-compatible entry point for the canonical ordination generator.

Deprecated name retained so older reproduction commands continue to work.
All NMDS and RDA calculations are delegated to generate_ordinations_revision4,
which imports the same src.publication_ordination module used by the app.
"""
from __future__ import annotations
import runpy
from pathlib import Path

if __name__ == "__main__":
  target = Path(__file__).with_name("generate_ordinations_revision4.py")
  runpy.run_path(str(target), run_name="__main__")
