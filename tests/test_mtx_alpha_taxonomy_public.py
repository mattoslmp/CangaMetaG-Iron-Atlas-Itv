from __future__ import annotations

from pathlib import Path
import runpy

import numpy as np
import pandas as pd

from src.app_mtx_alpha_taxonomy_runtime import (
  install_categorical_group_guard,
  metatranscriptome_matrix_columns,
)


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_mtx_alpha_taxonomy_public_transform.py"


def _synthetic_source(*, include_optional_anchors: bool = True) -> str:
  taxonomy = '''
def taxonomy_tab():
  st.markdown("### " + txt("Visualização taxonômica interativa", "Interactive taxonomic visualization"))
'''
  heatmaps = '''
def render_st8_heatmap_scope_controls(df, numeric_cols, label_col, title_prefix, base_key, x_label_map=None, boxplot_spec=None):
  meta = pd.DataFrame()
  lake_cols = []
  external_cols = []
  combined_cols = []
  def render_pair(scope_name_pt, scope_name_en, cols, scope_key, caption_pt, caption_en, require_all_lakes=False):
    pair_lakes = []
    pair_external = []
    st.caption(txt(
      f"Composição exibida: {len(pair_lakes)}/20 amostras das lagoas + {len(pair_external)} colunas externas; {len(cols)} colunas no total.",
      f"Displayed composition: {len(pair_lakes)}/20 lake samples + {len(pair_external)} external columns; {len(cols)} columns in total.",
    ))
  render_pair(
    "2B. Lagoas amazônicas + todos os ambientes externos",
    "2B. Amazonian lakes + all external environments",
    combined_cols,
    "combined_all",
    "pt",
    "en",
  )
'''
  optional = taxonomy + heatmaps if include_optional_anchors else "\ndef unrelated():\n  return 1\n"
  return (
    "from __future__ import annotations\n"
    "import pandas as pd\n"
    "import numpy as np\n"
    + optional
    + "\npage_handler = page_handlers.get(selected_page)\n"
  )


def _transformed(*, include_optional_anchors: bool = True) -> str:
  transformed = runpy.run_path(
    str(TRANSFORM),
    init_globals={"source": _synthetic_source(include_optional_anchors=include_optional_anchors)},
  )["source"]
  compile(transformed, "synthetic_mtx_alpha_taxonomy.py", "exec")
  return transformed


def test_alpha_diversity_accepts_categorical_group_with_missing_value() -> None:
  install_categorical_group_guard()
  from src import article_inference_statistics as statistics

  source = pd.DataFrame({
    "Lake_season": pd.Categorical(["AM-D", "AM-D", "TI-R", "TI-R", np.nan]),
    "Observed_OTUs": [100, 110, 90, 95, 105],
    "Chao1": [120, 125, 100, 103, 121],
    "Shannon": [3.1, 3.0, 2.7, 2.8, 3.05],
  })
  result = statistics.alpha_diversity_group_tests(source)
  assert isinstance(result, pd.DataFrame)
  assert not result.empty
  assert {"anova_pvalue", "kruskal_pvalue"}.issubset(result.columns)
  assert source["Lake_season"].dtype.name == "category"


def test_all_twelve_metatranscriptome_columns_are_selected() -> None:
  columns = [f"MTX-S{i:02d}" for i in range(1, 13)]
  metadata = pd.DataFrame({
    "data_layer": ["Metatranscriptomics"] * 12,
    "ST8_matrix_column": columns,
    "Study Name": [f"Study {i}" for i in range(1, 13)],
  })
  data = pd.DataFrame(np.arange(189 * 12).reshape(189, 12), columns=columns)
  selected_metadata, selected_columns = metatranscriptome_matrix_columns(
    metadata,
    columns,
    data.columns,
  )
  assert len(selected_metadata) == 12
  assert selected_columns == columns
  assert data[selected_columns].shape == (189, 12)


def test_transform_compiles_with_all_optional_anchors() -> None:
  transformed = _transformed()
  assert "CANGAMETAG_MTX_ALPHA_TAXONOMY_PUBLIC_V4" in transformed
  assert "render_complete_metatranscriptome_panel(" in transformed
  assert "render_taxonomy_article_overlap_panel(globals())" in transformed
  assert "amostras de metatranscriptoma" in transformed
  assert "todos os {len(df)} KOs/marcadores estão selecionados por padrão" in transformed


def test_optional_source_anchors_never_break_compilation() -> None:
  transformed = _transformed(include_optional_anchors=False)
  assert "install_categorical_group_guard()" in transformed
  assert "CANGAMETAG_MTX_ALPHA_TAXONOMY_PUBLIC_V4" in transformed


def test_transform_never_orphans_indented_continuation_lines() -> None:
  transformed = _transformed()
  compile(transformed, "indentation_regression.py", "exec")
  assert "    if pair_lakes:" in transformed
  assert "    elif \"metatranscript\" in" in transformed
  assert "  render_complete_metatranscriptome_panel(" in transformed


def test_app_validates_each_transform_before_execution() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  assert "_compile_transformed_source(candidate, transform_path.name)" in app
  assert "Transform {transform_name} generated invalid Python" in app


def test_transform_is_loaded_before_runtime_guard() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  correction = app.index("app_mtx_alpha_taxonomy_public_transform.py")
  guard = app.index("app_runtime_name_guard_transform.py")
  assert correction < guard
