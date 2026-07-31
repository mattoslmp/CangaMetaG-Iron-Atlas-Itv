from __future__ import annotations

from pathlib import Path
import runpy

import pandas as pd

from src.visitor_public_map import (
  visitor_city_frame,
  visitor_country_frame,
  visitor_world_map_figure,
)


ROOT = Path(__file__).resolve().parents[1]


def _txt(portuguese: str, english: str) -> str:
  return portuguese


def _visits() -> pd.DataFrame:
  return pd.DataFrame([
    {
      "visitor_id": "a",
      "country_name": "Brazil",
      "country_code": "BR",
      "region": "Rio de Janeiro",
      "city": "Itaperuna",
      "latitude": -21.205,
      "longitude": -41.887,
    },
    {
      "visitor_id": "b",
      "country_name": "Brazil",
      "country_code": "BR",
      "region": "Rio de Janeiro",
      "city": "Itaperuna",
      "latitude": -21.205,
      "longitude": -41.887,
    },
    {
      "visitor_id": "c",
      "country_name": "Portugal",
      "country_code": "PT",
      "region": "Porto",
      "city": "Porto",
      "latitude": 41.1579,
      "longitude": -8.6291,
    },
  ])


def test_country_and_city_frames_keep_all_recognized_locations() -> None:
  countries = visitor_country_frame(_visits())
  cities = visitor_city_frame(_visits())
  assert set(countries["Country code"]) == {"BR", "PT"}
  assert int(countries.loc[countries["Country code"].eq("BR"), "Visits"].iloc[0]) == 2
  assert set(cities["City"]) == {"Itaperuna", "Porto"}
  assert int(cities.loc[cities["City"].eq("Itaperuna"), "Visits"].iloc[0]) == 2
  assert cities[["Latitude", "Longitude"]].notna().all().all()


def test_world_map_contains_country_layer_and_city_points() -> None:
  figure = visitor_world_map_figure(_visits(), _txt)
  trace_types = [trace.type for trace in figure.data]
  assert "choropleth" in trace_types
  assert "scattergeo" in trace_types
  city_trace = next(trace for trace in figure.data if trace.type == "scattergeo")
  assert set(city_trace.customdata[:, 0]) == {"Itaperuna", "Porto"}


def test_final_transform_overrides_map_before_page_dispatch() -> None:
  transform = ROOT / "src" / "app_visitor_map_city_final_transform.py"
  source = '''from __future__ import annotations
import pandas as pd

def visitor_counter_public_footer(key="public_footer"):
  return None

page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(
    str(transform), init_globals={"source": source}
  )["source"]
  compile(transformed, "visitor_map_city_final.py", "exec")
  override = transformed.index("def visitor_counter_public_footer")
  dispatch = transformed.index("page_handler = page_handlers.get(selected_page)")
  assert override < dispatch
  assert "_render_public_visitor_footer_canonical" in transformed
  assert "CANGAMETAG_VISITOR_MAP_CITY_FINAL_V2" in transformed


def test_final_transform_is_last_in_app_chain() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  final_map = app.index("app_visitor_map_city_final_transform.py")
  runtime_guard = app.index("app_runtime_name_guard_transform.py")
  closing = app.index("]", final_map)
  assert runtime_guard < final_map < closing


def test_visitor_geolocation_supports_cloud_and_vercel_city_headers() -> None:
  source = (ROOT / "src" / "visitor_analytics.py").read_text(encoding="utf-8")
  for header in (
    "X-Vercel-IP-City",
    "X-Vercel-IP-Country",
    "CloudFront-Viewer-City",
    "CloudFront-Viewer-Latitude",
    "CloudFront-Viewer-Longitude",
  ):
    assert header in source
  assert "ipwho.is" in source
  assert "ipapi.co" in source
  assert "ipinfo.io" in source
