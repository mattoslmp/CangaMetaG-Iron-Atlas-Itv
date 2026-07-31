from __future__ import annotations

"""Canonical ST8 contracts shared by the app, tests, and figure generators.

The functions in this module never impute scientific values. They resolve sample
identifiers, preserve metadata-defined order, and derive raw/z-score matrices
from the exact Supplementary Table 8 values.
"""

from collections.abc import Iterable, Sequence
import re

import numpy as np
import pandas as pd


EXPECTED_ALL_KO_MARKERS = 189
EXPECTED_AMAZONIAN_SAMPLES = 20
EXPECTED_MTX_SAMPLES = 12
EXPECTED_DETECTED_AMAZONIAN_KOS = 172
EXPECTED_ZERO_AMAZONIAN_KOS = 17

METADATA_COLUMNS = ("KO", "Metabolism", "KO description")
MTX_MATRIX_FIELDS = (
  "ST8_matrix_column",
  "matrix_column_all_KO",
  "matrix_column_iron_KO",
  "matrix_column_selected",
  "matrix_column",
)
MTX_IDENTIFIER_FIELDS = (
  "taxon_oid",
  "IMG Genome ID",
  "sample_id_created_this_study",
  "sample_id",
  "SRA Run",
  "SRA ID",
)


def normalize_identifier(value: object) -> str:
  return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def amazonian_sample_columns(columns: Iterable[object]) -> list[str]:
  pattern = re.compile(r"^(?:AM|TIA|TI|VI)\.P\d+\.(?:D|R)$", re.IGNORECASE)
  return [str(column) for column in columns if pattern.fullmatch(str(column).strip())]


def metatranscriptome_metadata(metadata: pd.DataFrame) -> pd.DataFrame:
  if metadata is None or metadata.empty:
    return pd.DataFrame()
  layer = metadata.get("data_layer", pd.Series("", index=metadata.index)).astype(str)
  abbrev = metadata.get("data_layer_abbrev", pd.Series("", index=metadata.index)).astype(str)
  mask = layer.str.casefold().str.contains("metatranscript", na=False) | abbrev.str.upper().eq("MTX")
  return metadata.loc[mask].copy()


def _candidate_values(row: pd.Series, fields: Sequence[str]) -> list[str]:
  values: list[str] = []
  for field in fields:
    if field not in row.index:
      continue
    value = str(row.get(field, "") or "").strip()
    if value and value.casefold() not in {"nan", "none", "na", "n/a"} and value not in values:
      values.append(value)
  return values


def resolve_metatranscriptome_columns(
  metadata: pd.DataFrame,
  matrix_columns: Sequence[object],
  *,
  expected_count: int | None = EXPECTED_MTX_SAMPLES,
) -> tuple[pd.DataFrame, list[str]]:
  """Resolve every MTX row to exactly one source matrix column.

  Resolution order is exact matrix-field match, normalized matrix-field match,
  and finally a unique identifier match. Output order follows the metadata.
  """
  mtx = metatranscriptome_metadata(metadata)
  available = [str(column) for column in matrix_columns]
  available_set = set(available)
  normalized_available: dict[str, list[str]] = {}
  for column in available:
    normalized_available.setdefault(normalize_identifier(column), []).append(column)

  resolved_rows: list[dict[str, object]] = []
  used: set[str] = set()
  for metadata_index, row in mtx.iterrows():
    matrix_values = _candidate_values(row, MTX_MATRIX_FIELDS)
    identifiers = _candidate_values(row, MTX_IDENTIFIER_FIELDS)
    match = ""
    method = ""

    for candidate in matrix_values:
      if candidate in available_set and candidate not in used:
        match = candidate
        method = "exact metadata matrix column"
        break

    if not match:
      for candidate in matrix_values:
        candidates = [
          column for column in normalized_available.get(normalize_identifier(candidate), [])
          if column not in used
        ]
        if len(candidates) == 1:
          match = candidates[0]
          method = "normalized metadata matrix column"
          break

    if not match:
      identifier_tokens = [normalize_identifier(value) for value in identifiers]
      candidates = []
      for column in available:
        if column in used:
          continue
        normalized_column = normalize_identifier(column)
        if any(len(token) >= 6 and token in normalized_column for token in identifier_tokens):
          candidates.append(column)
      if len(candidates) == 1:
        match = candidates[0]
        method = "unique identifier contained in matrix column"

    resolved = row.to_dict()
    resolved.update({
      "metadata_index": metadata_index,
      "resolved_matrix_column": match,
      "resolution_method": method or "unresolved",
      "resolution_status": "resolved" if match else "unresolved",
    })
    resolved_rows.append(resolved)
    if match:
      used.add(match)

  resolved_metadata = pd.DataFrame(resolved_rows)
  columns = (
    resolved_metadata.loc[
      resolved_metadata.get("resolution_status", pd.Series(dtype=str)).eq("resolved"),
      "resolved_matrix_column",
    ].astype(str).tolist()
    if not resolved_metadata.empty else []
  )
  columns = list(dict.fromkeys(columns))
  if expected_count is not None and len(columns) != int(expected_count):
    unresolved_columns = [
      column for column in ("taxon_oid", "sample_id_created_this_study", "Study Name")
      if column in resolved_metadata.columns
    ]
    unresolved = (
      resolved_metadata.loc[
        resolved_metadata.get("resolution_status", pd.Series(dtype=str)).ne("resolved"),
        unresolved_columns,
      ].to_dict("records")
      if not resolved_metadata.empty else []
    )
    raise ValueError(
      f"Expected {expected_count} metatranscriptome columns, resolved {len(columns)}. "
      f"Unresolved metadata rows: {unresolved}"
    )
  return resolved_metadata, columns


def numeric_matrix(frame: pd.DataFrame, columns: Sequence[str]) -> pd.DataFrame:
  selected = [str(column) for column in columns if str(column) in frame.columns]
  return frame.loc[:, selected].apply(pd.to_numeric, errors="coerce")


def validate_all_ko_contract(
  all_ko: pd.DataFrame,
  metadata: pd.DataFrame,
) -> dict[str, object]:
  lake_columns = amazonian_sample_columns(all_ko.columns)
  resolved_metadata, mtx_columns = resolve_metatranscriptome_columns(
    metadata,
    all_ko.columns,
    expected_count=EXPECTED_MTX_SAMPLES,
  )
  lake_matrix = numeric_matrix(all_ko, lake_columns)
  row_totals = lake_matrix.fillna(0.0).abs().sum(axis=1)
  all_numeric = all_ko.drop(
    columns=[column for column in METADATA_COLUMNS if column in all_ko.columns]
  ).apply(pd.to_numeric, errors="coerce")
  result = {
    "source_ko_count": int(len(all_ko)),
    "unique_ko_count": int(all_ko["KO"].astype(str).nunique()) if "KO" in all_ko else 0,
    "amazonian_sample_count": len(lake_columns),
    "metatranscriptome_sample_count": len(mtx_columns),
    "amazonian_detected_ko_count": int(row_totals.gt(0).sum()),
    "amazonian_zero_total_ko_count": int(row_totals.eq(0).sum()),
    "blank_numeric_cells": int(all_numeric.isna().sum().sum()),
    "negative_numeric_cells": int(all_numeric.lt(0).sum().sum()),
    "zero_values_preserved": True,
    "values_imputed": False,
    "source": "tables/Supplementary_Table_8.xlsx — ST8 — all KO biomarkers",
    "resolved_mtx_columns": mtx_columns,
    "resolution_rows": int(len(resolved_metadata)),
  }
  result["status"] = "PASS" if (
    result["source_ko_count"] == EXPECTED_ALL_KO_MARKERS
    and result["unique_ko_count"] == EXPECTED_ALL_KO_MARKERS
    and result["amazonian_sample_count"] == EXPECTED_AMAZONIAN_SAMPLES
    and result["metatranscriptome_sample_count"] == EXPECTED_MTX_SAMPLES
    and result["amazonian_detected_ko_count"] == EXPECTED_DETECTED_AMAZONIAN_KOS
    and result["amazonian_zero_total_ko_count"] == EXPECTED_ZERO_AMAZONIAN_KOS
    and result["blank_numeric_cells"] == 0
    and result["negative_numeric_cells"] == 0
  ) else "FAIL"
  return result


def row_zscore(matrix: pd.DataFrame) -> pd.DataFrame:
  numeric = matrix.apply(pd.to_numeric, errors="coerce")
  means = numeric.mean(axis=1)
  standard = numeric.std(axis=1, ddof=0).replace(0.0, np.nan)
  return numeric.sub(means, axis=0).div(standard, axis=0).fillna(0.0)


def prepare_ko_scope(
  all_ko: pd.DataFrame,
  columns: Sequence[str],
  *,
  categories: Sequence[str] | None = None,
  include_zero_rows: bool = False,
  show_pathway: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
  work = all_ko.copy()
  if categories is not None:
    selected = {str(value) for value in categories}
    work = work[work["Metabolism"].astype(str).isin(selected)].copy()
  matrix = numeric_matrix(work, columns)
  totals = matrix.fillna(0.0).abs().sum(axis=1)
  if not include_zero_rows:
    keep = totals.gt(0)
    work = work.loc[keep].copy()
    matrix = matrix.loc[keep].copy()
  labels = work["KO"].astype(str)
  if show_pathway:
    labels = labels + " — " + work["Metabolism"].fillna("Unclassified").astype(str)
  matrix.index = labels
  matrix.index.name = "KO / pathway" if show_pathway else "KO"
  zscore = row_zscore(matrix)
  return work.reset_index(drop=True), matrix, zscore


def heatmap_geometry(row_count: int, column_count: int) -> dict[str, int]:
  cell_width = 108 if column_count <= 16 else 88 if column_count <= 40 else 72
  cell_height = 30 if row_count <= 80 else 25 if row_count <= 190 else 22
  return {
    "width": max(1500, min(16000, 760 + cell_width * max(column_count, 1))),
    "height": max(820, min(30000, 330 + cell_height * max(row_count, 1))),
    "left": 650 if row_count > 80 else 520,
    "right": 180,
    "top": 110,
    "bottom": max(360, 18 * max(1, min(column_count, 25))),
    "cell_width": cell_width,
    "cell_height": cell_height,
  }


def apply_final_heatmap_layout(fig, *, chart_key: str = ""):
  """Apply readable geometry without changing trace arrays or scientific values."""
  if fig is None:
    return fig
  traces = list(getattr(fig, "data", []) or [])
  matrix_trace = next((trace for trace in traces if getattr(trace, "z", None) is not None), None)
  if matrix_trace is None:
    return fig
  try:
    z = np.asarray(matrix_trace.z, dtype=object)
  except Exception:
    return fig
  if z.ndim != 2:
    return fig
  row_count, column_count = z.shape
  key = str(chart_key or "").casefold()
  relevant = any(token in key for token in (
    "supplementaryfigure40",
    "supplementaryfigure67",
    "s40",
    "s67",
    "metatranscript",
    "biogeochemical",
    "st8",
    "ko_",
  ))
  if not relevant:
    return fig
  geometry = heatmap_geometry(row_count, column_count)
  current_meta = getattr(fig.layout, "meta", None)
  meta = dict(current_meta) if isinstance(current_meta, dict) else {}
  meta.update({
    "preserve_cell_geometry": True,
    "horizontal_vertical_scroll_required": True,
    "x_tick_angle": -45,
    "source_rows": row_count,
    "source_columns": column_count,
    "values_changed_by_layout": False,
  })
  fig.update_layout(
    width=geometry["width"],
    height=geometry["height"],
    margin={
      "l": geometry["left"],
      "r": geometry["right"],
      "t": geometry["top"],
      "b": geometry["bottom"],
    },
    meta=meta,
  )
  fig.update_xaxes(tickangle=-45, automargin=True, tickfont={"size": 11})
  fig.update_yaxes(automargin=True, tickfont={"size": 10})
  return fig


def public_metatranscriptome_metadata_table(resolved_metadata: pd.DataFrame) -> pd.DataFrame:
  """Return one publication-facing metadata row for each resolved MTX column."""
  if resolved_metadata is None or resolved_metadata.empty:
    return pd.DataFrame()
  columns = [
    column for column in (
      "sample_id_created_this_study",
      "taxon_oid",
      "resolved_matrix_column",
      "Study Name",
      "Genome Name / Sample Name",
      "ST8_group",
      "data_layer",
      "NCBI Bioproject Accession",
      "SRA Run",
      "resolution_method",
    )
    if column in resolved_metadata.columns
  ]
  return resolved_metadata.loc[
    resolved_metadata["resolution_status"].eq("resolved"), columns
  ].reset_index(drop=True)
