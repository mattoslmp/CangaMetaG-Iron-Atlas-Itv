from __future__ import annotations

from pathlib import Path

import pandas as pd

from scripts.figures.generate_st8_ko_mtx_final_figures import (
  metatranscriptome_value_diagnostics,
)
from src.st8_final_contract import resolve_metatranscriptome_columns


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "tables" / "Supplementary_Table_8.xlsx"


def test_all_189_kos_are_classified_across_all_12_mtx_samples() -> None:
  all_ko = pd.read_excel(WORKBOOK, sheet_name="ST8 — all KO biomarkers")
  metadata = pd.read_excel(WORKBOOK, sheet_name="metadata", dtype=str)
  _, mtx_columns = resolve_metatranscriptome_columns(
    metadata,
    all_ko.columns,
    expected_count=12,
  )
  ko_status, source_issues, sample_status = metatranscriptome_value_diagnostics(
    all_ko,
    mtx_columns,
  )

  assert len(all_ko) == 189
  assert len(mtx_columns) == 12
  assert len(ko_status) == 189
  assert len(sample_status) == 12
  assert source_issues.empty
  assert int(ko_status["missing_or_non_numeric_cells"].sum()) == 0
  assert int(sample_status["missing_or_non_numeric_cells"].sum()) == 0
  assert ko_status["values_imputed"].eq(False).all()
  assert sample_status["values_imputed"].eq(False).all()
  assert set(ko_status["display_explanation"]).issubset({
    "measured_zero_in_all_12_mtx_samples",
    "constant_across_mtx_row_zscore_is_zero",
    "observed_values_present",
  })
  assert (
    ko_status["zero_cells"] + ko_status["nonzero_cells"]
  ).eq(12).all()
