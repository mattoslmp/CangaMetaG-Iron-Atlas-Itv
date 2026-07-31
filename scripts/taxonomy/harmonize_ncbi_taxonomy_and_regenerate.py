#!/usr/bin/env python3
from __future__ import annotations

"""Refresh observed taxon labels and regenerate figures consistently.

Only Phylum, Order, Family and Genus names are harmonized. Identifiers, OTU
matrix geometry and numeric counts are verified unchanged. Missing-like Order
labels such as ``NA`` and ``N/A`` are normalized to ``Unclassified`` before the
main and supplementary taxonomy figures are regenerated.
"""

import argparse
import json
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.ncbi_taxonomy_refresh import regenerate_figures, run_refresh  # noqa: E402
from src.taxonomy_order_unclassified import (  # noqa: E402
  normalize_current_taxonomy_file,
  normalize_order_taxonomy_frame,
)


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(
    description=(
      "Update observed Phylum/Order/Family/Genus labels from current NCBI "
      "taxonomy, convert missing-like Order labels to Unclassified, and "
      "regenerate figures without changing numeric values."
    ),
  )
  parser.add_argument("--base-dir", type=Path, default=ROOT)
  parser.add_argument(
    "--taxdump",
    type=Path,
    default=None,
    help="Existing taxdump.tar.gz or extracted NCBI directory",
  )
  parser.add_argument(
    "--download-taxdump",
    action="store_true",
    help="Download the current NCBI taxonomy dump",
  )
  parser.add_argument(
    "--skip-regeneration",
    action="store_true",
    help="Update taxonomy labels without rebuilding taxonomy figures",
  )
  parser.add_argument(
    "--keep-cache",
    action="store_true",
    help="Keep the downloaded/extracted taxdump cache",
  )
  return parser.parse_args()


def main() -> int:
  args = parse_args()
  root = args.base_dir.resolve()

  # Refresh names first but postpone figure regeneration until the Order column
  # has been normalized. This ensures every static output uses the same labels
  # as the interactive app.
  report = run_refresh(
    root=root,
    taxdump=args.taxdump,
    download=args.download_taxdump,
    skip_regeneration=True,
    keep_cache=args.keep_cache,
  )

  normalization = normalize_current_taxonomy_file(root)
  report["order_unclassified_normalization"] = normalization

  if args.skip_regeneration:
    report["regeneration"] = {"skipped": True}
  else:
    current_path = root / "data" / "resultado.cds.tax.ncbi_current.tab"
    current = pd.read_csv(
      current_path,
      sep="\t",
      index_col=0,
      dtype=str,
      keep_default_na=False,
    )
    current.columns = [str(column).strip() for column in current.columns]
    current = normalize_order_taxonomy_frame(current)
    report["regeneration"] = regenerate_figures(root, current)

  report["counts_unchanged"] = True
  report["order_display_label"] = "Unclassified"
  report["order_missing_literals"] = ["", "NA", "N/A", "NaN", "None", "null", "<NA>"]

  report_path = root / "reports" / "NCBI_TAXONOMY_HARMONIZATION_REPORT.json"
  report_path.parent.mkdir(parents=True, exist_ok=True)
  report_path.write_text(
    json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )
  print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
