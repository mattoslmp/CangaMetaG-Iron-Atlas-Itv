from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go

from src.article_figure45_final_generator import (
  apply_figure45_plotly_layout,
  materialize_article_figure45_static,
)
from src.article_frozen_taxonomy_panels import frozen_taxonomy_domain_data


def test_plotly_bottom_legend_layout_preserves_values() -> None:
  figure = go.Figure(go.Bar(
    x=[1.0, 2.0, 3.0],
    y=["A", "B", "C"],
    name="Genus example",
  ))
  before_x = np.asarray(figure.data[0].x, dtype=float).copy()
  before_y = list(figure.data[0].y)
  apply_figure45_plotly_layout(figure, language="en")
  np.testing.assert_array_equal(before_x, np.asarray(figure.data[0].x, dtype=float))
  assert before_y == list(figure.data[0].y)
  assert figure.layout.margin.b == 690
  assert figure.layout.legend.orientation == "h"
  assert figure.layout.legend.y == -0.285
  assert figure.layout.meta["legend_below_entire_figure"] is True
  assert figure.layout.meta["legend_overlaps_scientific_panels"] is False
  assert figure.layout.meta["scientific_values_changed"] is False


def _assert_generated_metadata_matches_source(domain: str, metadata: dict) -> None:
  source = frozen_taxonomy_domain_data(domain)
  profile = source["profile"]
  profile_samples = [column for column in profile.columns if column != "taxon"]
  assert metadata["profile_samples"] == len(profile_samples)
  assert metadata["profile_rows"] == len(profile)
  assert metadata["nmds_rows"] == len(source["nmds"])
  assert metadata["rda_site_rows"] == len(source["rda_sites"])
  assert metadata["rda_environment_vectors"] == len(source["rda_environment_vectors"])
  assert metadata["rda_taxon_vectors"] == len(source["rda_taxon_vectors"])
  assert metadata["source_files"] == list(source["source_files"])
  assert metadata["legend_below_entire_figure"] is True
  assert metadata["legend_overlaps_scientific_panels"] is False
  assert metadata["scientific_values_recomputed"] is False


def test_static_figure4_is_generated_from_packaged_article_inputs(tmp_path) -> None:
  target = materialize_article_figure45_static("Bacteria", tmp_path, language="en")
  assert target.name == "Figure4_taxonomic_bacteria_genus_profiles.svg"
  assert target.is_file()
  assert target.stat().st_size > 10000
  metadata_path = target.with_suffix(".generation.json")
  assert metadata_path.is_file()
  metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
  assert metadata["domain"] == "Bacteria"
  assert metadata["language"] == "en"
  _assert_generated_metadata_matches_source("Bacteria", metadata)


def test_static_figure5_uses_archaea_input_bundle(tmp_path) -> None:
  target = materialize_article_figure45_static("Archaea", tmp_path, language="en")
  assert target.name == "Figure5_taxonomic_archaea_genus_profiles.svg"
  assert target.is_file()
  assert target.stat().st_size > 10000
  metadata = json.loads(target.with_suffix(".generation.json").read_text(encoding="utf-8"))
  assert metadata["domain"] == "Archaea"
  assert metadata["language"] == "en"
  _assert_generated_metadata_matches_source("Archaea", metadata)
