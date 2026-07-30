from __future__ import annotations

import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
CORE = ROOT / "app_core.py"


def generated_source() -> str:
  app_text = APP.read_text(encoding="utf-8")
  transform_names = re.findall(r'with_name\("src"\) / "([^"]+\.py)"', app_text)
  assert transform_names
  source = CORE.read_text(encoding="utf-8")
  for transform_name in transform_names:
    transform_path = ROOT / "src" / transform_name
    namespace = runpy.run_path(str(transform_path), init_globals={"source": source})
    source = namespace["source"]
  return source


def test_generated_source_compiles() -> None:
  source = generated_source()
  compile(source, str(CORE), "exec")


def test_public_release_version_footer_and_typography() -> None:
  source = generated_source()
  assert 'APP_VERSION = "1.0"' in source
  assert 'APP_RELEASE_LABEL = "30 July 2026"' in source
  assert "cangametag-public-release-v1-typography" in source
  assert source.count('visitor_counter_public_footer("bottom_public_counter")') == 1
  page_header = source[source.index("def page_header():"):source.index("def overview_tab():")]
  assert "visitor_counter_compact()" not in page_header
  assert "Download geographic details" not in source


def test_scripts_are_centralized_and_references_are_current() -> None:
  source = generated_source()
  assert '"code_reproducibility"' not in source[source.index("base_page_specs = ["):source.index("article_atlas_label =")]
  section_inventory = source[source.index("def render_section_script_inventory("):source.index("def taxonomy_tab():")]
  assert "return" in section_inventory
  methods = source[source.index("def references_methods_tab():"):source.index("def contact_recipients_from_settings")]
  assert "Final figures & scripts" in methods
  assert "Streamlit Community and Community Cloud" in methods
  assert "NASA POWER" not in methods
  assert "CHIRPS" not in methods
  assert "SoilGrids / ISRIC" not in methods
  assert "Download methods index" not in methods
  assert "Download execution manifest" not in methods
  assert "Harmonização reprodutível da taxonomia NCBI" in methods


def test_workflow_traceability_heatmaps_and_integrity_repairs() -> None:
  source = generated_source()
  overview = source[source.index("def overview_tab():"):source.index("def taxonomy_tab_legacy_redundant_removed():")]
  assert "whole image is fitted to the page width" in overview
  assert 'width="stretch"' in overview
  assert "display_width = max(1900" not in overview
  assert "max-width:none" not in overview
  assert "CANGAMETAG_TRACEABILITY_HEATMAP_REPAIR_V1" in source
  assert "Traceable source table" in source
  assert "Exact figure values" in source
  assert "Heatmaps remain visible" in source
  assert "_manifest_asset_present" in source
  assert 'st.warning(txt(\n      f"O painel combinado contém' in source


def test_s67_external_environment_labels_do_not_overlap() -> None:
  source = generated_source()
  assert "CANGAMETAG_KEGG_S67_AXIS_READABILITY_V2" in source
  helper = source[
    source.index("def _kegg_s67_compact_label("):
    source.index("def _kegg_scope_rows(")
  ]
  assert 'width=16' in helper
  assert 'return "<br>".join(lines)' in helper
  assert '"Hydrotherm Fe rich": "Hydrothermal Fe-rich"' in helper
  assert '"Freshwater microbial communitie": "Freshwater microbial community"' in helper
  assert "def _kegg_reorder_full_matrix_like_grouped_source(" in helper
  assert 'key_prefix.endswith("_environmental_group")' in helper
  assert 'reordered.sort_index(axis=1).equals(full_status.sort_index(axis=1))' in helper

  panel = source[
    source.index("def _display_kegg_completeness_panel("):
    source.index("def kegg_modules_tab():")
  ]
  assert 'cell_w = 104 if n_cols <= 50 else 94 if n_cols <= 90 else 86' in panel
  assert 'tickangle=0' in panel
  assert 'tickmode="array"' in panel
  assert 'title="Lake metagenomes and external iron-rich environments"' in panel
  assert "cada ambiente externo aparece em linhas curtas" in panel
  assert "tickangle=-65" not in panel


def test_s67_compact_label_keeps_name_and_identifier_on_separate_lines() -> None:
  minimal_source = '''from pathlib import Path
import re
import textwrap
import pandas as pd


def _prepare_kegg_status_frame(raw):
  return raw, "module"


def _kegg_scope_rows():
  pass
'''
  transform_path = ROOT / "src" / "app_kegg_s67_axis_readability_transform.py"
  transformed = runpy.run_path(
    str(transform_path),
    init_globals={"source": minimal_source},
  )["source"]
  namespace: dict[str, object] = {}
  exec(compile(transformed, str(transform_path), "exec"), namespace, namespace)
  compact = namespace["_kegg_s67_compact_label"]

  assert compact("AM.P1.D", 1) == "AM.P1.D"
  assert compact("Acid mine drainage 3300038494", 2) == (
    "Acid mine<br>drainage<br>3300038494"
  )
  assert compact("Freshwater microbial communitie 3300024300", 3) == (
    "Freshwater<br>microbial<br>community<br>3300024300"
  )
  assert compact("Hydrotherm Fe rich 3300023310", 4) == (
    "Hydrothermal<br>Fe-rich<br>3300023310"
  )
