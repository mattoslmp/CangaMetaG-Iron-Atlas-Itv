from __future__ import annotations

# Validation branch: run the complete workflow against the current main state.
from pathlib import Path
import runpy

import pandas as pd

from src.antismash_metabolism_runtime import _classify, _cluster_svg_data_uri
from src.st8_final_contract import resolve_metatranscriptome_columns


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_st8_scope_guard_antismash_bgc_transform.py"


MTX_IDS = ["S2", "S9", "S14", "S18", "S21", "S22", "S23", "S30", "S35", "S47", "S53", "S61"]
MTX_OIDS = [
  3300055056, 3300061576, 3300055062, 3300008723,
  3300055061, 3300008567, 3300055069, 3300046014,
  3300046013, 3300008566, 3300008721, 3300055057,
]


def _metadata() -> pd.DataFrame:
  return pd.DataFrame({
    "data_layer": ["Metatranscriptomics"] * 12,
    "data_layer_abbrev": ["MTX"] * 12,
    "sample_id_created_this_study": MTX_IDS,
    "taxon_oid": MTX_OIDS,
    "Study Name": ["external study"] * 12,
  })


def test_st8_resolver_accepts_short_ids_oids_excel_oids_and_composite_headers() -> None:
  metadata = _metadata()
  column_sets = [
    MTX_IDS,
    [str(value) for value in MTX_OIDS],
    [f"{value}.0" for value in MTX_OIDS],
    [f"count_{value}_MTX" for value in MTX_IDS],
  ]
  for columns in column_sets:
    resolved, selected = resolve_metatranscriptome_columns(metadata, columns, expected_count=12)
    assert len(selected) == 12
    assert resolved["resolution_status"].eq("resolved").all()
  _, selected = resolve_metatranscriptome_columns(metadata, ["S21"], expected_count=None)
  assert selected == ["S21"]


def test_sediment_projection_with_no_mtx_columns_is_not_an_error() -> None:
  resolved, selected = resolve_metatranscriptome_columns(
    _metadata(),
    ["AM.P1.D", "AM.P1.R", "sediment_external_1"],
    expected_count=None,
  )
  assert selected == []
  assert resolved["resolution_status"].eq("unresolved").all()


def test_final_scope_transform_compiles_and_installs_both_features() -> None:
  source = '''from __future__ import annotations

def render_complete_metatranscriptome_panel(namespace, *, metadata, numeric_columns, data, render_pair, base_key):
  return None

def antismash_inventory():
  return None

def page():
  inventory = antismash_inventory()
  return inventory

page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(str(TRANSFORM), init_globals={"source": source})["source"]
  compile(transformed, "synthetic_st8_scope_bgc.py", "exec")
  assert "expected_count=None" in transformed
  assert "if not available_mtx_columns" in transformed
  assert "render_bgc_metabolism_panel(globals())" in transformed


def test_bgc_evidence_language_is_conservative_and_cluster_svg_is_embeddable() -> None:
  direct = _classify(["siderophore", "T1PKS"], ' /product="ferric siderophore transporter"')
  assert direct["metal evidence"] == "direct BGC-class evidence"
  assert "not, by itself, evidence of central carbon cycling" in direct["carbon relevance"]
  candidate = _classify(["terpene"], ' /product="hypothetical protein"')
  assert candidate["carbon evidence"] == "BGC-class chemistry"
  uri = _cluster_svg_data_uri([
    {"start": 1, "end": 500, "strand": 1, "gene_kind": "biosynthetic", "product": "enzyme", "locus_tag": "gene1"},
    {"start": 550, "end": 900, "strand": -1, "gene_kind": "transport", "product": "transporter", "locus_tag": "gene2"},
  ], "MAG1 region 1")
  assert uri.startswith("data:image/svg+xml;base64,")
