from __future__ import annotations

import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
CORE = ROOT / "app_core.py"


def generated_source() -> str:
  app_text = APP.read_text(encoding="utf-8")
  transforms = re.findall(r'with_name\("src"\) / "([^"]+\.py)"', app_text)
  source = CORE.read_text(encoding="utf-8")
  for transform_name in transforms:
    namespace = runpy.run_path(
      str(ROOT / "src" / transform_name),
      init_globals={"source": source},
    )
    source = namespace["source"]
  return source


def test_generated_application_compiles() -> None:
  source = generated_source()
  compile(source, str(CORE), "exec")


def test_public_tables_are_retractable_and_visible_by_default() -> None:
  source = generated_source()
  assert "def _retractable_dataframe(" in source
  assert 'txt("Mostrar/ocultar tabela", "Show/hide table")' in source
  assert "value=True" in source
  assert "_ORIGINAL_ST_DATAFRAME" in source


def test_article_taxonomy_panels_use_shared_source_and_separate_seasons() -> None:
  source = generated_source()
  assert "article_static_source_validation" in source
  assert 'for article_domain in ["Bacteria", "Archaea"]' in source
  assert 'for season_name, column in [("Dry", dry_column), ("Rainy", rainy_column)]' in source
  assert "data/resultado.cds.otu.tab + data/resultado.cds.tax.tab" in source
  assert "SupplementaryFigure4_alpha_diversity_CDS_32999_source.csv" in source
  assert "Harmonização reprodutível da taxonomia NCBI" in source


def test_workflow_fits_page_without_geometry_changes() -> None:
  source = generated_source()
  overview = source[source.index("def overview_tab():"):source.index("def mags_tab():")]
  assert 'st.image(' in overview
  assert 'width="stretch"' in overview
  assert "whole image is fitted to the page width without changing its geometry" in overview
  assert "max-width:none" not in overview


def test_s67_uses_compact_non_overlapping_axis_labels() -> None:
  source = generated_source()
  assert "CANGAMETAG_KEGG_S67_AXIS_READABILITY_V1" in source
  assert "def _kegg_s67_compact_label(" in source
  assert 'key_prefix.startswith("kegg_combined_lagoon_external")' in source
  assert 'tickangle=-65' in source
  assert 'b=500 if key_prefix.startswith("kegg_combined_lagoon_external")' in source
  assert "Original identifiers and complete names remain in the hover and source table" in source
