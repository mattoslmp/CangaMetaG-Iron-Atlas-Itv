from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go

from src.figure45_large_legend_runtime import (
  LARGE_LEGEND_CACHE_VERSION,
  apply_figure45_plotly_layout_large,
  materialize_article_figure45_static_large,
)


def test_plotly_large_bottom_legend_layout_preserves_values() -> None:
  figure = go.Figure(go.Bar(
    x=[1.0, 2.0, 3.0],
    y=["A", "B", "C"],
    name="Genus example",
  ))
  before_x = np.asarray(figure.data[0].x, dtype=float).copy()
  before_y = list(figure.data[0].y)
  apply_figure45_plotly_layout_large(figure, language="en")
  np.testing.assert_array_equal(before_x, np.asarray(figure.data[0].x, dtype=float))
  assert before_y == list(figure.data[0].y)
  assert figure.layout.margin.b == 790
  assert figure.layout.legend.orientation == "h"
  assert figure.layout.legend.y == -0.245
  assert figure.layout.legend.font.size >= 15
  assert figure.layout.legend.title.font.size >= 18
  assert figure.layout.meta["legend_below_entire_figure"] is True
  assert figure.layout.meta["legend_overlaps_scientific_panels"] is False
  assert figure.layout.meta["large_legend_layout"] is True
  assert figure.layout.meta["scientific_values_changed"] is False


def test_static_figure4_is_generated_from_packaged_article_inputs(tmp_path) -> None:
  target = materialize_article_figure45_static_large("Bacteria", tmp_path, language="en")
  assert target.is_file()
  assert target.stat().st_size > 10000
  assert LARGE_LEGEND_CACHE_VERSION in str(target)
  metadata_path = target.with_suffix(".generation.json")
  assert metadata_path.is_file()
  metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
  assert metadata["domain"] == "Bacteria"
  assert metadata["profile_samples"] > 0
  assert metadata["profile_rows"] > 0
  assert metadata["nmds_rows"] > 0
  assert metadata["rda_site_rows"] > 0
  assert metadata["source_files"]
  assert metadata["legend_below_entire_figure"] is True
  assert metadata["legend_overlaps_scientific_panels"] is False
  assert metadata["scientific_values_recomputed"] is False


def test_static_figure5_uses_archaea_input_bundle(tmp_path) -> None:
  target = materialize_article_figure45_static_large("Archaea", tmp_path, language="en")
  assert target.is_file()
  assert target.stat().st_size > 10000
  assert LARGE_LEGEND_CACHE_VERSION in str(target)
  metadata = json.loads(target.with_suffix(".generation.json").read_text(encoding="utf-8"))
  assert metadata["domain"] == "Archaea"
  assert metadata["profile_samples"] > 0
  assert metadata["profile_rows"] > 0
  assert metadata["legend_below_entire_figure"] is True
  assert metadata["scientific_values_recomputed"] is False
