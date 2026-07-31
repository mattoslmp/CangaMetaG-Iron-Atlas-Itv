#!/usr/bin/env python3
from __future__ import annotations

"""Validate all ST8 MTX KO values and write internal diagnostic tables only."""

import argparse
import json
from pathlib import Path
import sys

import pandas as pd


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from scripts.figures.generate_st8_ko_mtx_final_figures import (
  metatranscriptome_value_diagnostics,
  resolve_workbook,
)
from src.st8_final_contract import (
  resolve_metatranscriptome_columns,
  validate_all_ko_contract,
)


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--root", type=Path, default=ROOT)
  parser.add_argument("--workbook", type=Path, default=None)
  args = parser.parse_args()

  root = args.root.resolve()
  workbook = resolve_workbook(root, args.workbook.resolve() if args.workbook else None)
  derived = root / "data" / "final_publication_derived"
  derived.mkdir(parents=True, exist_ok=True)

  all_ko = pd.read_excel(workbook, sheet_name="ST8 — all KO biomarkers")
  metadata = pd.read_excel(workbook, sheet_name="metadata", dtype=str)
  resolved_metadata, mtx_columns = resolve_metatranscriptome_columns(
    metadata,
    all_ko.columns,
    expected_count=12,
  )
  ko_status, source_issues, sample_status = metatranscriptome_value_diagnostics(
    all_ko,
    mtx_columns,
  )
  contract = validate_all_ko_contract(all_ko, metadata)
  status = "PASS" if contract["status"] == "PASS" and source_issues.empty else "FAIL"

  resolved_metadata.to_csv(
    derived / "ST8_metatranscriptome_12_sample_resolution.csv",
    index=False,
  )
  ko_status.to_csv(derived / "ST8_MTX_KO_value_status.csv", index=False)
  source_issues.to_csv(derived / "ST8_MTX_source_cell_issues.csv", index=False)
  sample_status.to_csv(derived / "ST8_MTX_sample_value_summary.csv", index=False)

  report = {
    "status": status,
    "workbook": str(workbook),
    "contract": contract,
    "resolved_mtx_columns": mtx_columns,
    "resolved_mtx_column_count": len(mtx_columns),
    "KO_rows_classified": int(len(ko_status)),
    "source_issue_cells": int(len(source_issues)),
    "all_zero_across_mtx_rows": int(ko_status["all_zero_across_mtx"].sum()),
    "constant_across_mtx_rows": int(ko_status["constant_across_mtx"].sum()),
    "observed_value_rows": int(
      ko_status["display_explanation"].eq("observed_values_present").sum()
    ),
    "values_imputed": False,
    "public_interface_exposure": False,
  }
  report_path = derived / "ST8_MTX_value_validation.json"
  report_path.write_text(
    json.dumps(report, ensure_ascii=False, indent=2),
    encoding="utf-8",
  )
  print(json.dumps(report, ensure_ascii=False, indent=2))
  if status != "PASS":
    raise RuntimeError(
      "ST8 MTX validation failed; inspect data/final_publication_derived/"
      "ST8_MTX_source_cell_issues.csv"
    )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
