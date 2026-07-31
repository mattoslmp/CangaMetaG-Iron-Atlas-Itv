from __future__ import annotations

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_ko_heatmap_scale_selector_transform.py"


def _apply(source: str) -> str:
  return runpy.run_path(
    str(TRANSFORM),
    init_globals={"source": source},
  )["source"]


def _synthetic_source(extra: str = "") -> str:
  return f'''from __future__ import annotations
import hashlib
import re
import pandas as pd

def render_figure_audit_expander(fig, chart_key, **kwargs):
  return None

def render_plotly_downloadable(fig, *args, **kwargs):
  return fig

{extra}
page_handler = page_handlers.get(selected_page)
'''


def test_transform_installs_one_selector_for_all_explicit_heatmap_pairs() -> None:
  transformed = _apply(_synthetic_source())
  compile(transformed, "synthetic_all_heatmap_selector.py", "exec")
  assert "CANGAMETAG_ALL_HEATMAP_SCALE_SELECTOR_V5" in transformed
  assert "Raw data" in transformed
  assert "Z-score" in transformed
  assert "Heatmap visualization" in transformed
  assert "mode != selected_mode" in transformed
  assert "_APP_RENDER_BEFORE_ALL_HEATMAP_SELECTOR" in transformed
  assert "_final_is_plotly_heatmap" in transformed


def test_pair_detection_is_generic_and_not_limited_to_ko_heatmaps() -> None:
  transformed = _apply(_synthetic_source())
  for token in [
    "raw_counts",
    "raw data",
    "raw_values",
    "raw_matrix",
    "absolute_counts",
    "zscore",
    "z-score",
    "row_zscore",
  ]:
    assert f'"{token}"' in transformed
  assert 'if not _final_is_plotly_heatmap(fig):' in transformed
  assert "environmental_heatmap" in transformed
  assert "taxonomy" in transformed
  assert "functional" in transformed
  assert "kegg" in transformed
  assert "metatranscriptome" in transformed


def test_functional_annotation_selector_uses_standard_labels_across_lines() -> None:
  source = _synthetic_source('''view_mode = st.radio(
  txt("Escala", "Scale"),
  [
    txt("Contagem absoluta", "Absolute counts"),
    txt("Z-score por função", "Row z-score"),
  ],
)
zscore_rows = view_mode == txt(
  "Z-score por função",
  "Row z-score",
)''')
  transformed = _apply(source)
  assert '["Raw data", "Z-score"]' in transformed
  assert 'zscore_rows = view_mode == "Z-score"' in transformed
  assert "Contagem absoluta" not in transformed
  assert "Z-score por função" not in transformed


def test_taxonomy_and_generic_single_heatmaps_use_standard_selector() -> None:
  source = _synthetic_source('''zscore = st.checkbox(
  txt("Z-score por táxon no heatmap", "Row z-score in heatmap"),
  value=False,
  key=f"taxonomy_z_{level}_{hmode}",
)
zscore = st.checkbox(
  "Z-score por linha",
  value=False,
  key=f"{key_prefix}_z",
)''')
  transformed = _apply(source)
  assert transformed.count('["Raw data", "Z-score"]') >= 2
  assert transformed.count('zscore = heatmap_scale == "Z-score"') >= 2
  assert "Z-score por táxon no heatmap" not in transformed
  assert 'st.checkbox(\n  "Z-score por linha"' not in transformed


def test_selected_heatmap_keeps_specific_scientific_metadata() -> None:
  transformed = _apply(_synthetic_source())
  assert '"audit_input_source"' in transformed
  assert '"audit_script"' in transformed
  assert '"audit_method"' in transformed
  assert "Supplementary_Table_8.xlsx" in transformed
  assert "Supplementary_Table_1.xlsx" in transformed
  assert "Supplementary_Table_6.xlsx" in transformed
  assert "Column-wise z-score" in transformed
  assert "Per-KO row z-score" in transformed
  assert "scientific_output_files" in transformed
  assert "scientific_plotted_values_description" in transformed
  assert "output_table is None" in transformed


def test_plotted_values_tab_receives_view_specific_description() -> None:
  source = _synthetic_source('''def scientific_panel_fixture():
    with tabs[3]:
      _scientific_render_tables(groups["plotted"], key_text, "plotted")''')
  transformed = _apply(source)
  compile(transformed, "synthetic_plotted_values_panel.py", "exec")
  assert "plotted_description" in transformed
  assert "scientific_plotted_values_description" in transformed
  assert "_scientific_render_tables(groups[\"plotted\"]" in transformed


def test_selector_is_last_transform_in_application_chain() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  selector = app.index("app_ko_heatmap_scale_selector_transform.py")
  figure45 = app.index("app_figure45_legend_below_final_transform.py")
  assert figure45 < selector
  assert selector == app.rindex("app_ko_heatmap_scale_selector_transform.py")


# Final integrated validation marker; production implementation is already on main.
