from __future__ import annotations

import pandas as pd

from src.visitor_self_contained_map import CONTINENTS, visitor_world_map_figure


def _txt(portuguese: str, english: str) -> str:
  return english


def test_empty_visitor_map_always_contains_world_geometry() -> None:
  figure = visitor_world_map_figure(pd.DataFrame(), _txt)
  assert len(figure.data) >= len(CONTINENTS)
  assert figure.layout.meta["self_contained_vector_map"] is True
  assert figure.layout.meta["external_tiles_required"] is False
  assert figure.layout.meta["external_topojson_required"] is False
  assert figure.layout.xaxis.range == (-180, 180)
  assert figure.layout.yaxis.range == (-90, 90)


def test_real_coordinates_are_rendered_as_cartesian_markers() -> None:
  visits = pd.DataFrame([{
    "country_name": "Brazil",
    "country_code": "BR",
    "region": "Rio de Janeiro",
    "city": "Itaperuna",
    "latitude": -21.205,
    "longitude": -41.888,
    "visitor_id": "anonymous-1",
  }])
  figure = visitor_world_map_figure(visits, _txt)
  marker_traces = [trace for trace in figure.data if getattr(trace, "mode", "") == "markers"]
  assert len(marker_traces) == 1
  assert float(marker_traces[0].x[0]) == -41.888
  assert float(marker_traces[0].y[0]) == -21.205
  assert all(trace.type == "scatter" for trace in figure.data)
