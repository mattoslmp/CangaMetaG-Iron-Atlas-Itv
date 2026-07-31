from __future__ import annotations

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_name_guard_removes_startup_name_errors() -> None:
  source = '''from __future__ import annotations

class Figure:
  def add_annotation(self, **kwargs):
    return None

class Go:
  Figure = Figure

go = Go()

class Layout:
  meta = {}

class DummyFigure:
  layout = Layout()
  def update_layout(self, **kwargs):
    return None

class PD:
  class DataFrame:
    pass

pd = PD()

def txt(pt, en):
  return en

_APP_ORIGINAL_ST8_HEATMAP_FIGURE = heatmap_figure

def heatmap_figure(frame, numeric_cols, label_col, title, top_n=30, zscore_rows=False, x_label_map=None):
  title_text = str(title or "")
  return _APP_ORIGINAL_ST8_HEATMAP_FIGURE(frame, numeric_cols, label_col, title)

_APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE = _visitor_world_map_figure

def _visitor_world_map_figure(country_frame: pd.DataFrame):
  figure = _APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE(country_frame)
  return figure

_APP_ORIGINAL_VISITOR_COUNTER_PUBLIC_FOOTER_FINAL = visitor_counter_public_footer

def visitor_counter_public_footer(key: str = "public_footer"):
  _APP_ORIGINAL_VISITOR_COUNTER_PUBLIC_FOOTER_FINAL(key)
'''
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_runtime_name_guard_transform.py"),
    init_globals={"source": source},
  )["source"]
  namespace: dict[str, object] = {}
  exec(compile(transformed, "guarded_app.py", "exec"), namespace, namespace)
  assert namespace["heatmap_figure"](None, [], "", "") is None
  visitor_figure = namespace["_visitor_world_map_figure"](None)
  assert visitor_figure is not None
  namespace["visitor_counter_public_footer"]("test")
