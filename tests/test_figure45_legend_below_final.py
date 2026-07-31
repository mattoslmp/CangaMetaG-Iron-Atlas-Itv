from __future__ import annotations

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_figure45_legend_below_final_transform.py"


def test_final_figure45_legend_transform_compiles_and_is_last_guard() -> None:
  source = '''from __future__ import annotations

def article_frozen_taxonomy_figure(domain: str):
  return object(), {}

page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(
    str(TRANSFORM),
    init_globals={"source": source},
  )["source"]
  compile(transformed, "synthetic_figure45_final_legend.py", "exec")
  assert "dedicated-band-below-entire-figure" in transformed
  assert '"y": -0.285' in transformed
  assert '"b": 690' in transformed
  assert '"legend_below_entire_figure": True' in transformed
  assert '"legend_overlaps_scientific_panels": False' in transformed
  assert '"scientific_values_changed": False' in transformed


def test_transform_is_loaded_after_language_and_st8_wrappers() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  language = app.index("app_full_figure_language_transform.py")
  st8 = app.index("app_final_st8_ko_mtx_revision_transform.py")
  final_legend = app.index("app_figure45_legend_below_final_transform.py")
  visitor = app.index("app_visitor_map_city_final_transform.py")
  assert language < st8 < final_legend < visitor
