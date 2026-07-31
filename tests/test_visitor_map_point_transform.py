from __future__ import annotations

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]


def test_visitor_map_adds_country_and_city_layers() -> None:
  source = '''from __future__ import annotations


def _visitor_world_map_figure(country_frame):
  return country_frame


def site_access_gate():
  pass
'''
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_visitor_geolocation_points_transform.py"),
    init_globals={"source": source},
  )["source"]
  assert "_APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE" in transformed
  assert "def _visitor_geolocation_point_frame" in transformed
  assert "go.Scattergeo" in transformed
  assert '"visitor_country_choropleth": True' in transformed
  assert '"visitor_city_points": True' in transformed
  assert '"raw_ip_stored": False' in transformed
  compile(transformed, "synthetic_visitor_map.py", "exec")
