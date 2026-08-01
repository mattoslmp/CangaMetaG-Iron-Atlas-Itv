from __future__ import annotations

from pathlib import Path
import runpy

import pandas as pd

from src.st8_mtx_identifier_resolution import resolve_metatranscriptome_columns


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_st8_mtx_identifier_resolution_transform.py"
APP = ROOT / "app.py"

SAMPLE_IDS = ["S2", "S9", "S14", "S18", "S21", "S22", "S23", "S30", "S35", "S47", "S53", "S61"]
TAXON_OIDS = [
  3300055056,
  3300061576,
  3300055062,
  3300008723,
  3300055061,
  3300008567,
  3300055069,
  3300046014,
  3300046013,
  3300008566,
  3300008721,
  3300055057,
]


def _metadata() -> pd.DataFrame:
  return pd.DataFrame({
    "data_layer": ["Metatranscriptome"] * 12,
    "data_layer_abbrev": ["MTX"] * 12,
    "sample_id_created_this_study": SAMPLE_IDS,
    "taxon_oid": TAXON_OIDS,
    "Study Name": [f"Study {sample_id}" for sample_id in SAMPLE_IDS],
  })


def test_resolves_all_short_study_ids_exactly_in_metadata_order() -> None:
  resolved, columns = resolve_metatranscriptome_columns(
    _metadata(),
    ["KO", "Metabolism", "KO description", *SAMPLE_IDS],
    expected_count=12,
  )
  assert columns == SAMPLE_IDS
  assert resolved["resolution_status"].eq("resolved").all()
  assert set(resolved["resolution_method"]).issubset({
    "exact metadata identifier",
    "case-insensitive metadata identifier",
    "normalized metadata identifier",
  })


def test_resolves_excel_float_taxon_oids_without_altering_column_names() -> None:
  float_headers = [f"{taxon_oid}.0" for taxon_oid in TAXON_OIDS]
  resolved, columns = resolve_metatranscriptome_columns(
    _metadata(),
    float_headers,
    expected_count=12,
  )
  assert columns == float_headers
  assert resolved["resolved_matrix_column"].astype(str).tolist() == float_headers


def test_resolves_composite_headers_by_unique_identifier() -> None:
  composite = [
    f"MTX | {sample_id} | IMG {taxon_oid}"
    for sample_id, taxon_oid in zip(SAMPLE_IDS, TAXON_OIDS)
  ]
  resolved, columns = resolve_metatranscriptome_columns(
    _metadata(),
    composite,
    expected_count=12,
  )
  assert columns == composite
  assert resolved["resolution_method"].eq(
    "unique identifier embedded in matrix column"
  ).all()


def test_short_identifier_boundary_does_not_confuse_s2_and_s21() -> None:
  metadata = _metadata().iloc[[0, 4]].copy()
  resolved, columns = resolve_metatranscriptome_columns(
    metadata,
    ["MTX-S21-counts", "MTX-S2-counts"],
    expected_count=2,
  )
  assert columns == ["MTX-S2-counts", "MTX-S21-counts"]
  assert resolved["resolution_status"].eq("resolved").all()


def test_runtime_transform_replaces_both_st8_resolver_entry_points() -> None:
  source = '''from __future__ import annotations

class RuntimeModule:
  pass

_final_st8_runtime_module = RuntimeModule()
_resolve_final_st8_mtx_columns = object()
page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(
    str(TRANSFORM),
    init_globals={"source": source},
  )["source"]
  compile(transformed, "synthetic_st8_mtx_identifier_transform.py", "exec")
  assert "_resolve_final_st8_mtx_columns = _resolve_st8_mtx_columns_by_identifier" in transformed
  assert "_final_st8_runtime_module.metatranscriptome_matrix_columns" in transformed
  assert "expected_count=12" in transformed


def test_identifier_transform_is_loaded_immediately_after_final_st8_layer() -> None:
  app = APP.read_text(encoding="utf-8")
  final_st8 = app.index("app_final_st8_ko_mtx_revision_transform.py")
  identifier_fix = app.index("app_st8_mtx_identifier_resolution_transform.py")
  visitor = app.index("app_visitor_map_city_final_transform.py")
  assert final_st8 < identifier_fix < visitor
