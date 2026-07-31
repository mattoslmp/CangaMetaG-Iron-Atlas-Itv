from __future__ import annotations

from pathlib import Path
import runpy

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from src.st8_final_contract import (
  EXPECTED_ALL_KO_MARKERS,
  EXPECTED_AMAZONIAN_SAMPLES,
  EXPECTED_DETECTED_AMAZONIAN_KOS,
  EXPECTED_MTX_SAMPLES,
  EXPECTED_ZERO_AMAZONIAN_KOS,
  amazonian_sample_columns,
  apply_final_heatmap_layout,
  prepare_ko_scope,
  resolve_metatranscriptome_columns,
  validate_all_ko_contract,
)


ROOT = Path(__file__).resolve().parents[1]
WORKBOOK = ROOT / "tables" / "Supplementary_Table_8.xlsx"
FINAL_TRANSFORM = ROOT / "src" / "app_final_st8_ko_mtx_revision_transform.py"
FINAL_GENERATOR = ROOT / "scripts" / "figures" / "generate_st8_ko_mtx_final_figures.py"


def _source_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
  assert WORKBOOK.is_file(), f"Missing canonical workbook: {WORKBOOK}"
  all_ko = pd.read_excel(WORKBOOK, sheet_name="ST8 — all KO biomarkers")
  metadata = pd.read_excel(WORKBOOK, sheet_name="metadata", dtype=str)
  return all_ko, metadata


def test_exact_st8_scientific_contract() -> None:
  all_ko, metadata = _source_tables()
  report = validate_all_ko_contract(all_ko, metadata)
  assert report["status"] == "PASS", report
  assert report["source_ko_count"] == EXPECTED_ALL_KO_MARKERS == 189
  assert report["unique_ko_count"] == 189
  assert report["amazonian_sample_count"] == EXPECTED_AMAZONIAN_SAMPLES == 20
  assert report["metatranscriptome_sample_count"] == EXPECTED_MTX_SAMPLES == 12
  assert report["amazonian_detected_ko_count"] == EXPECTED_DETECTED_AMAZONIAN_KOS == 172
  assert report["amazonian_zero_total_ko_count"] == EXPECTED_ZERO_AMAZONIAN_KOS == 17
  assert report["blank_numeric_cells"] == 0
  assert report["negative_numeric_cells"] == 0
  assert report["values_imputed"] is False
  assert report["zero_values_preserved"] is True


def test_all_twelve_mtx_samples_are_resolved_in_metadata_order() -> None:
  all_ko, metadata = _source_tables()
  resolved, columns = resolve_metatranscriptome_columns(
    metadata,
    all_ko.columns,
    expected_count=12,
  )
  assert len(columns) == 12
  assert len(set(columns)) == 12
  assert all(column in all_ko.columns for column in columns)
  assert resolved["resolution_status"].eq("resolved").sum() == 12
  assert resolved.loc[
    resolved["resolution_status"].eq("resolved"),
    "resolved_matrix_column",
  ].astype(str).tolist() == columns


def test_raw_and_zscore_mtx_matrices_use_identical_rows_and_columns() -> None:
  all_ko, metadata = _source_tables()
  _, mtx_columns = resolve_metatranscriptome_columns(
    metadata,
    all_ko.columns,
    expected_count=12,
  )
  displayed, raw, zscore = prepare_ko_scope(
    all_ko,
    mtx_columns,
    include_zero_rows=True,
    show_pathway=True,
  )
  assert len(displayed) == 189
  assert raw.shape == (189, 12)
  assert zscore.shape == (189, 12)
  assert raw.columns.tolist() == mtx_columns
  assert zscore.columns.tolist() == mtx_columns
  assert raw.index.tolist() == zscore.index.tolist()
  assert np.isfinite(zscore.to_numpy(float)).all()


def test_amazonian_default_and_full_catalogue_controls() -> None:
  all_ko, _ = _source_tables()
  lake_columns = amazonian_sample_columns(all_ko.columns)
  displayed, raw, _ = prepare_ko_scope(
    all_ko,
    lake_columns,
    include_zero_rows=False,
    show_pathway=True,
  )
  full_displayed, full_raw, _ = prepare_ko_scope(
    all_ko,
    lake_columns,
    include_zero_rows=True,
    show_pathway=False,
  )
  assert len(lake_columns) == 20
  assert len(displayed) == 172
  assert raw.shape == (172, 20)
  assert len(full_displayed) == 189
  assert full_raw.shape == (189, 20)
  assert full_raw.index.str.match(r"^K\d{5}$").all()
  zero_rows = full_raw.fillna(0.0).abs().sum(axis=1).eq(0)
  assert int(zero_rows.sum()) == 17
  assert (full_raw.fillna(0.0).to_numpy(float) == 0).any()


def test_final_generator_preserves_all_189_kos_in_every_scope() -> None:
  assert FINAL_GENERATOR.is_file(), f"Missing final generator: {FINAL_GENERATOR}"
  source = FINAL_GENERATOR.read_text(encoding="utf-8")
  required = [
    "validate_all_ko_contract(all_ko, metadata)",
    'if validation["status"] != "PASS"',
    "resolve_metatranscriptome_columns(",
    "expected_count=12",
    '"ST8_MTX_all_12_samples": mtx_columns',
    '"ST8_Amazonian_20_plus_MTX_12": lake_columns + mtx_columns',
    '("raw", "Raw count", "viridis")',
    '("relative", "Relative abundance within sample (%)", "viridis")',
    '("zscore", "Row z-score", "RdBu_r")',
    "numeric = all_ko.loc[:, columns].apply(pd.to_numeric, errors=\"raise\")",
    '"KO_rows": int(matrix.shape[0])',
    '"zero_values_preserved": True',
    '"values_imputed": False',
  ]
  for token in required:
    assert token in source
  assert "filter_detected_markers" not in source
  assert ".dropna(" not in source


def test_final_heatmap_layout_preserves_values_and_uses_45_degrees() -> None:
  values = np.arange(36, dtype=float).reshape(3, 12)
  figure = go.Figure(go.Heatmap(
    z=values,
    x=[f"MTX-{index:02d}" for index in range(12)],
    y=["K00001", "K00002", "K00003"],
  ))
  before = np.asarray(figure.data[0].z, dtype=float).copy()
  apply_final_heatmap_layout(
    figure,
    chart_key="SupplementaryFigure67 metatranscriptome ST8 KO heatmap",
  )
  after = np.asarray(figure.data[0].z, dtype=float)
  np.testing.assert_array_equal(before, after)
  assert figure.layout.xaxis.tickangle == -45
  assert figure.layout.width >= 1500
  assert figure.layout.height >= 820
  assert figure.layout.meta["values_changed_by_layout"] is False


def test_final_transform_compiles_and_removes_public_audit_wording() -> None:
  source = '''from __future__ import annotations
import pandas as pd

def render_plotly_downloadable(fig, *args, **kwargs):
  return fig

def page():
    mtx_cols = [str(col) for col in numeric_cols if str(col) in matrix_to_row]
    text = "Auditoria de detecção dos 189 KOs"
    label = "Detection audit for all 189 KOs"
    return text, label

page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(
    str(FINAL_TRANSFORM),
    init_globals={"source": source},
  )["source"]
  compile(transformed, "synthetic_final_st8_transform.py", "exec")
  assert "Resumo de detecção dos 189 KOs" in transformed
  assert "Detection summary for all 189 KOs" in transformed
  assert "_resolve_final_st8_mtx_columns" in transformed
  assert "[str(column) for column in df.columns]" in transformed
  assert "del numeric_columns" in transformed
  assert "available = list(dict.fromkeys(str(value) for value in data_columns))" in transformed
  assert "if str(column) in data_column_set" not in transformed
  assert "tickangle=-45" in transformed or "tickangle=0" not in transformed


def test_final_transform_is_loaded_after_runtime_guard() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  runtime_guard = app.index("app_runtime_name_guard_transform.py")
  final_contract = app.index("app_final_st8_ko_mtx_revision_transform.py")
  visitor_footer = app.index("app_visitor_map_city_final_transform.py")
  figure45_guard = app.index("app_figure45_legend_below_final_transform.py")
  assert runtime_guard < final_contract < visitor_footer < figure45_guard
