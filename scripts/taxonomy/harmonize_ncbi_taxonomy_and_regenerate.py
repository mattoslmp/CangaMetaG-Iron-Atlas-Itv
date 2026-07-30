#!/usr/bin/env python3
from __future__ import annotations

"""Refresh every observed taxon label against current NCBI taxonomy.

Only Phylum, Order, Family and Genus labels are replaced. Identifiers, OTU
matrix geometry and every numeric count are verified unchanged. The generated
current-taxonomy table is consumed by all application taxonomy loaders, while
the shared Plotly renderer also harmonizes legacy labels in every interactive
figure and in its Source/Processed/Output/Plotted-values audit tables.
"""

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.ncbi_taxonomy_refresh import run_refresh  # noqa: E402


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description="Update all observed Phylum/Order/Family/Genus labels from current NCBI taxonomy without changing numeric values.",
  )
  parser.add_argument("--base-dir", type=Path, default=ROOT)
  parser.add_argument("--taxdump", type=Path, default=None, help="Existing taxdump.tar.gz or extracted NCBI directory")
  parser.add_argument("--download-taxdump", action="store_true", help="Download the current NCBI taxonomy dump")
  parser.add_argument("--skip-regeneration", action="store_true", help="Update taxonomy labels without rebuilding main and supplementary taxonomy figures")
  parser.add_argument("--keep-cache", action="store_true", help="Keep the downloaded/extracted taxdump cache")
  return parser.parse_args()


def main() -> int:
  args = parse_args()
  report = run_refresh(
    root=args.base_dir,
    taxdump=args.taxdump,
    download=args.download_taxdump,
    skip_regeneration=args.skip_regeneration,
    keep_cache=args.keep_cache,
  )
  print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
