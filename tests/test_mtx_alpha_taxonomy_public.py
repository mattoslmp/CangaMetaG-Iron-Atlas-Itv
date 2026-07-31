from __future__ import annotations

from pathlib import Path
import runpy

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_mtx_alpha_taxonomy_public_transform.py"


def _synthetic_source() -> str:
  return '''from __future__ import annotations
import pandas as pd
import numpy as np


def taxonomy_tab():
  st.markdown("### " + txt("Visualização taxonômica interativa", "Interactive taxonomic visualization"))


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


page_handler = page_handlers.get(selected_page)
'''


def _transformed() -> str:
  transformed = runpy.run_path(
    str(TRANSFORM),
    init_globals={"source": _synthetic_source()},
  )["source"]
  compile(transformed, "synthetic_mtx_alpha_taxonomy.py", "exec")
  return transformed


def test_alpha_diversity_accepts_categorical_group_with_missing_value() -> None:
  transformed = _transformed()
  prefix = transformed.split("def _article_overlap_broad_group", 1)[0]
  namespace: dict[str, object] = {"pd": pd, "np": np}
  exec(prefix, namespace, namespace)

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


def test_complete_metatranscriptome_panel_is_installed() -> None:
  transformed = _transformed()
  assert "Metatranscriptomas — todas as amostras, estudos e identificadores" in transformed
  assert "metatranscriptomics_all_samples" in transformed
  assert "all_12_metatranscriptomes_metadata.csv" in transformed
  assert "amostras de metatranscriptoma" in transformed
  assert "todos os {len(df)} KOs/marcadores estão selecionados por padrão" in transformed


def test_taxonomy_page_contains_article_venn_and_heatmap() -> None:
  transformed = _transformed()
  call = transformed.index("_taxonomy_article_overlap_panel()")
  interactive = transformed.index("Visualização taxonômica interativa")
  assert call < interactive
  assert "scripts/generate_core_taxonomy_overlap_figure.py" in transformed
  assert "scripts/figures/generate_s31_taxonomic_levels_revision3.py" in transformed
  assert 'data_layer"].astype(str).str.casefold().eq("metagenomics")' in transformed
  assert '["Phylum", "Order", "Family"]' in transformed


def test_public_audit_prose_is_removed() -> None:
  source = _synthetic_source().replace(
    "page_handler = page_handlers.get(selected_page)",
    '''st.caption(txt(
  "O visualizador interativo incorpora o mesmo SVG corrigido exibido como figura estática.",
  "The interactive viewer embeds the same corrected SVG displayed as the static figure.",
))
page_handler = page_handlers.get(selected_page)''',
  )
  transformed = runpy.run_path(str(TRANSFORM), init_globals={"source": source})["source"]
  assert "O visualizador interativo incorpora" not in transformed
  assert "The interactive viewer embeds" not in transformed


def test_transform_is_loaded_before_runtime_guard() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  correction = app.index("app_mtx_alpha_taxonomy_public_transform.py")
  guard = app.index("app_runtime_name_guard_transform.py")
  assert correction < guard
