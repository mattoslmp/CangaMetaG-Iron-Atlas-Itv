#!/usr/bin/env python3
from __future__ import annotations

"""Regenerate final article Figures 4 and 5 with large bottom legends."""

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.figure45_large_legend_runtime import generate_article_figure45_outputs_large


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--root", type=Path, default=ROOT)
  args = parser.parse_args()
  manifest = generate_article_figure45_outputs_large(args.root)
  print(manifest.to_string(index=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
