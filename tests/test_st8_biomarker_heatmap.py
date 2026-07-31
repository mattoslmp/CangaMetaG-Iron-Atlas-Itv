from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.st8_biomarker_heatmap import (
  article_lake_columns,
  assert_no_undetected_heatmap_rows,
  filter_detected_markers,
  numeric_sample_columns,
  validate_st8_all_ko_table,
)


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "tables" / "Supplementary_Table_8.xlsx"
SHEET = "ST8 — all KO biomarkers"


def source_table() -> pd.DataFrame:
  assert WORKBOOK.exists(), f"Missing source workbook: {WORKBOOK}"
  return pd.read_excel(WORKBOOK, sheet_name=SHEET)


def test_st8_all_ko_source_contract() -> None:
  frame = source_table()
  numeric = numeric_sample_columns(frame)
  integrity = validate_st8_all_ko_table(frame, numeric).iloc[0]
  assert integrity["status"] == "PASS"
  assert int(integrity["source_rows"]) == 189
  assert int(integrity["unique_KOs"]) == 189
  assert int(integrity["numeric_sample_columns"]) == 87
  assert int(integrity["blank_numeric_cells"]) == 0
  assert int(integrity["negative_numeric_cells"]) == 0


def test_amazonian_heatmap_excludes_only_17_undetected_rows() -> None:
  frame = source_table()
  numeric = numeric_sample_columns(frame)
  lake = article_lake_columns(numeric)
  display, summary, audit = filter_detected_markers(
    frame,
    lake,
    include_undetected=False,
    scope_name="20 Amazonian lake samples",
  )
  result = summary.iloc[0]
  assert len(lake) == 20
  assert int(result["source_marker_count"]) == 189
  assert int(result["detected_marker_count"]) == 172
  assert int(result["undetected_marker_count"]) == 17
  assert len(display) == 172
  assert len(audit) == 189
  assert int((audit["heatmap_status"] == "not detected in selected scope").sum()) == 17
  assert_no_undetected_heatmap_rows(display, lake)


def test_complete_st8_scope_has_one_all_zero_ko() -> None:
  frame = source_table()
  numeric = numeric_sample_columns(frame)
  display, summary, audit = filter_detected_markers(
    frame,
    numeric,
    include_undetected=False,
    scope_name="all 87 Supplementary Table 8 columns",
  )
  result = summary.iloc[0]
  assert int(result["detected_marker_count"]) == 188
  assert int(result["undetected_marker_count"]) == 1
  excluded = audit.loc[~audit["included_by_default"]]
  assert excluded["KO"].tolist() == ["K17877: NIT-6"]
  assert np.isclose(float(excluded.iloc[0]["scope_total_count"]), 0.0)
  assert len(display) == 188
  assert_no_undetected_heatmap_rows(display, numeric)


def test_include_undetected_option_preserves_all_source_rows() -> None:
  frame = source_table()
  lake = article_lake_columns(numeric_sample_columns(frame))
  display, _, _ = filter_detected_markers(
    frame,
    lake,
    include_undetected=True,
    scope_name="20 Amazonian lake samples",
  )
  assert len(display) == 189
  assert display.attrs.get("st8_include_undetected") is True
