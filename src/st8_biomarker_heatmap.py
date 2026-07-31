from __future__ import annotations

"""Canonical validation and display filtering for Supplementary Table 8 KOs.

The workbook remains the immutable scientific source. Heatmaps exclude rows
whose exact count is zero in every selected sample by default, because an
all-zero row does not encode an observed heatmap signal. Every source row is
retained in the audit and downloadable source tables.
"""

from dataclasses import dataclass
import re
from typing import Iterable

import numpy as np
import pandas as pd


ST8_KO_METADATA_COLUMNS = ("KO", "Metabolism", "KO description")
EXPECTED_ST8_KO_MARKERS = 189
EXPECTED_ST8_NUMERIC_COLUMNS = 87
ARTICLE_LAKE_PATTERN = re.compile(r"^(?:AM|TIA|TI|VI)\.P\d+\.(?:D|R)$")


@dataclass(frozen=True)
class ST8HeatmapScope:
  name: str
  selected_columns: tuple[str, ...]


def numeric_sample_columns(
  frame: pd.DataFrame,
  metadata_columns: Iterable[str] = ST8_KO_METADATA_COLUMNS,
) -> list[str]:
  """Return columns containing at least one numeric source value."""
  if frame is None or frame.empty:
    return []
  metadata = {str(column).strip() for column in metadata_columns}
  result: list[str] = []
  for column in frame.columns:
    name = str(column).strip()
    if name in metadata:
      continue
    values = pd.to_numeric(frame[column], errors="coerce")
    if values.notna().any():
      result.append(str(column))
  return result


def article_lake_columns(columns: Iterable[str]) -> list[str]:
  return [str(column) for column in columns if ARTICLE_LAKE_PATTERN.match(str(column))]


def _numeric_matrix(frame: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
  selected = [str(column) for column in columns if str(column) in frame.columns]
  if not selected:
    return pd.DataFrame(index=frame.index)
  return frame[selected].apply(pd.to_numeric, errors="coerce")


def validate_st8_all_ko_table(
  frame: pd.DataFrame,
  numeric_columns: Iterable[str] | None = None,
) -> pd.DataFrame:
  """Return one-row integrity report for the all-KO ST8 worksheet."""
  if frame is None:
    frame = pd.DataFrame()
  numeric = list(numeric_columns or numeric_sample_columns(frame))
  matrix = _numeric_matrix(frame, numeric)
  ko = (
    frame.get("KO", pd.Series(dtype=str))
    .fillna("")
    .astype(str)
    .str.strip()
  )
  negative_cells = int(matrix.lt(0).sum().sum()) if not matrix.empty else 0
  blank_numeric_cells = int(matrix.isna().sum().sum()) if not matrix.empty else 0
  duplicate_ko_rows = int(ko.duplicated(keep=False).sum()) if len(ko) else 0
  unique_kos = int(ko[ko.ne("")].nunique()) if len(ko) else 0
  source_rows = int(len(frame))
  numeric_count = int(len(numeric))
  status = "PASS" if (
    source_rows == EXPECTED_ST8_KO_MARKERS
    and unique_kos == EXPECTED_ST8_KO_MARKERS
    and numeric_count == EXPECTED_ST8_NUMERIC_COLUMNS
    and blank_numeric_cells == 0
    and negative_cells == 0
    and duplicate_ko_rows == 0
  ) else "FAIL"
  return pd.DataFrame([{
    "status": status,
    "source_rows": source_rows,
    "unique_KOs": unique_kos,
    "numeric_sample_columns": numeric_count,
    "blank_numeric_cells": blank_numeric_cells,
    "negative_numeric_cells": negative_cells,
    "duplicate_KO_rows": duplicate_ko_rows,
    "expected_source_rows": EXPECTED_ST8_KO_MARKERS,
    "expected_numeric_sample_columns": EXPECTED_ST8_NUMERIC_COLUMNS,
    "source": "Supplementary Table 8 — ST8 — all KO biomarkers",
    "values_imputed": False,
  }])


def st8_detection_audit(
  frame: pd.DataFrame,
  selected_columns: Iterable[str],
  scope_name: str,
  id_column: str = "KO",
) -> tuple[pd.DataFrame, pd.DataFrame]:
  """Return scope summary and one audit row per ST8 marker."""
  if frame is None:
    frame = pd.DataFrame()
  columns = [str(column) for column in selected_columns if str(column) in frame.columns]
  matrix = _numeric_matrix(frame, columns)
  matrix_filled = matrix.fillna(0.0)
  total = matrix_filled.abs().sum(axis=1) if not matrix_filled.empty else pd.Series(0.0, index=frame.index)
  detected_samples = matrix_filled.gt(0).sum(axis=1) if not matrix_filled.empty else pd.Series(0, index=frame.index)
  negative_samples = matrix_filled.lt(0).sum(axis=1) if not matrix_filled.empty else pd.Series(0, index=frame.index)
  blank_cells = matrix.isna().sum(axis=1) if not matrix.empty else pd.Series(0, index=frame.index)
  detected = total.gt(0)

  row_audit = pd.DataFrame({
    "source_row": np.arange(1, len(frame) + 1, dtype=int),
    "KO": frame.get(id_column, pd.Series("", index=frame.index)).fillna("").astype(str).str.strip(),
    "Metabolism": frame.get("Metabolism", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip(),
    "KO description": frame.get("KO description", pd.Series("", index=frame.index)).fillna("").astype(str).str.strip(),
    "scope": str(scope_name),
    "selected_sample_count": len(columns),
    "scope_total_count": total.to_numpy(float),
    "scope_detected_sample_count": detected_samples.to_numpy(int),
    "scope_detection_fraction": (
      detected_samples.div(max(1, len(columns))).to_numpy(float)
    ),
    "scope_blank_numeric_cells": blank_cells.to_numpy(int),
    "scope_negative_numeric_cells": negative_samples.to_numpy(int),
    "heatmap_status": np.where(detected.to_numpy(bool), "displayed", "not detected in selected scope"),
    "included_by_default": detected.to_numpy(bool),
    "values_imputed": False,
  })

  summary = pd.DataFrame([{
    "scope": str(scope_name),
    "source_marker_count": int(len(frame)),
    "selected_sample_count": int(len(columns)),
    "detected_marker_count": int(detected.sum()),
    "undetected_marker_count": int((~detected).sum()),
    "blank_numeric_cells": int(matrix.isna().sum().sum()) if not matrix.empty else 0,
    "negative_numeric_cells": int(matrix.lt(0).sum().sum()) if not matrix.empty else 0,
    "heatmap_default_rule": "display rows with total count > 0 in selected scope",
    "source_rows_removed": 0,
    "values_imputed": False,
  }])
  return summary, row_audit


def filter_detected_markers(
  frame: pd.DataFrame,
  selected_columns: Iterable[str],
  include_undetected: bool = False,
  scope_name: str = "selected heatmap scope",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
  """Prepare the exact ST8 rows used by a heatmap.

  The returned display frame keeps original source order. Undetected rows are
  excluded only from the heatmap unless ``include_undetected`` is true.
  """
  if frame is None:
    frame = pd.DataFrame()
  summary, row_audit = st8_detection_audit(frame, selected_columns, scope_name)
  if include_undetected:
    display = frame.copy()
  else:
    mask = row_audit["included_by_default"].to_numpy(bool)
    display = frame.loc[mask].copy()
  display.attrs["st8_detection_summary"] = summary.to_dict("records")[0]
  display.attrs["st8_row_audit"] = row_audit
  display.attrs["st8_include_undetected"] = bool(include_undetected)
  return display.reset_index(drop=True), summary, row_audit


def assert_no_undetected_heatmap_rows(
  frame: pd.DataFrame,
  selected_columns: Iterable[str],
) -> None:
  """Raise when a display matrix still contains an all-zero selected row."""
  matrix = _numeric_matrix(frame, selected_columns).fillna(0.0)
  if matrix.empty:
    raise ValueError("The ST8 heatmap has no numeric sample columns.")
  zero_mask = matrix.abs().sum(axis=1).eq(0)
  if bool(zero_mask.any()):
    identifiers = frame.loc[zero_mask, "KO"].astype(str).tolist() if "KO" in frame else []
    raise ValueError(
      "Undetected ST8 rows remain in the heatmap display: "
      + ", ".join(identifiers[:20])
    )
