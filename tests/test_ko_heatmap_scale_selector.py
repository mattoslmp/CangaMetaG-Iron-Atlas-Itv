from __future__ import annotations

# Pull-request validation entrypoint for the final Figure 4/5 and KO UI contract.

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_ko_heatmap_scale_selector_transform.py"


def _apply(source: str) -> str:
  return runpy.run_path(
    str(TRANSFORM),
    init_globals={"source": source},
  )["source"]


def test_transform_installs_one_scale_selector_after_plot_renderer() -> None:
  source = '''from __future__ import annotations
import hashlib
import re

def render_plotly_downloadable(fig, *args, **kwargs):
  return fig

page_handler = page_handlers.get(selected_page)
'''
  transformed = _apply(source)
  compile(transformed, "synthetic_ko_heatmap_selector.py", "exec")
  assert "CANGAMETAG_KO_HEATMAP_SCALE_SELECTOR_V2" in transformed
  assert "Raw data" in transformed
  assert "Z-score" in transformed
  assert "KO heatmap visualization" in transformed
  assert "mode != selected_mode" in transformed
  assert "_APP_RENDER_BEFORE_KO_SCALE_SELECTOR" in transformed


def test_selector_recognises_all_requested_ko_heatmap_families() -> None:
  transformed = _apply('''from __future__ import annotations

def render_plotly_downloadable(fig, *args, **kwargs):
  return fig

page_handler = page_handlers.get(selected_page)
''')
  for token in [
    "all_ko",
    "ko_biomarker",
    "ko_marker",
    "biogeochemical",
    "iron_st8",
    "st8_iron",
    "iron_ko",
    "other_metals",
    "metatranscriptome_ko",
  ]:
    assert f'"{token}"' in transformed
  assert 'if "functional" in identity:' in transformed


def test_functional_annotation_selector_uses_the_same_visible_labels() -> None:
  source = '''from __future__ import annotations

view_mode = st.radio(
  txt("Escala", "Scale"),
  [txt("Contagem absoluta", "Absolute counts"), txt("Z-score por função", "Row z-score")],
)
zscore_rows = view_mode == txt("Z-score por função", "Row z-score")

def render_plotly_downloadable(fig, *args, **kwargs):
  return fig

page_handler = page_handlers.get(selected_page)
'''
  transformed = _apply(source)
  assert '["Raw data", "Z-score"]' in transformed
  assert 'zscore_rows = view_mode == "Z-score"' in transformed
  assert "Contagem absoluta" not in transformed
  assert "Z-score por função" not in transformed


def test_selected_view_keeps_scientific_data_metadata() -> None:
  transformed = _apply('''from __future__ import annotations

def render_plotly_downloadable(fig, *args, **kwargs):
  return fig

page_handler = page_handlers.get(selected_page)
''')
  assert '"audit_input_source"' in transformed
  assert '"audit_script"' in transformed
  assert '"audit_method"' in transformed
  assert "exact KO source matrix" in transformed
  assert "no value is imputed" in transformed
  assert "no replacement of source values" in transformed


def test_selector_is_last_transform_in_application_chain() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  selector = app.index("app_ko_heatmap_scale_selector_transform.py")
  figure45 = app.index("app_figure45_legend_below_final_transform.py")
  assert figure45 < selector
  assert selector == app.rindex("app_ko_heatmap_scale_selector_transform.py")
