from __future__ import annotations

import base64
from pathlib import Path

import numpy as np

from src.article_exact_taxonomy_phylum_generated import (
  exact_article_phylum_interactive,
  exact_article_phylum_svg_bytes,
  load_exact_article_phylum_table,
  materialize_exact_article_phylum_static,
)


def test_corrected_figure2_and_3_sources_are_numeric_and_total_100_percent() -> None:
  expected_current_names = {
    "Bacteria": {"Pseudomonadota", "Acidobacteriota", "Actinomycetota"},
    "Archaea": {"Methanobacteriota", "Thermoplasmatota", "Nitrososphaerota"},
  }
  prohibited_legacy_names = {
    "Bacteria": {"Proteobacteria", "Acidobacteria", "Actinobacteria"},
    "Archaea": {"Euryarchaeota", "Thaumarchaeota"},
  }
  for domain in ("Bacteria", "Archaea"):
    table = load_exact_article_phylum_table(domain)
    taxa = set(table["taxon"].astype(str))
    assert expected_current_names[domain].issubset(taxa)
    assert not taxa.intersection(prohibited_legacy_names[domain])
    numeric = table.drop(columns=["taxon"]).to_numpy(float)
    assert np.isfinite(numeric).all()
    assert np.allclose(numeric.sum(axis=0), 100.0, atol=1e-8, rtol=0.0)


def test_static_and_interactive_use_identical_corrected_svg(tmp_path: Path) -> None:
  for domain in ("Bacteria", "Archaea"):
    expected_svg = exact_article_phylum_svg_bytes(domain)
    static_path = materialize_exact_article_phylum_static(domain, tmp_path)
    figure, _, interactive_svg = exact_article_phylum_interactive(domain)
    assert expected_svg == static_path.read_bytes()
    assert expected_svg == interactive_svg
    assert b"<svg" in expected_svg[:8192].lower()
    image_source = str(figure.layout.images[0].source)
    prefix = "data:image/svg+xml;base64,"
    assert image_source.startswith(prefix)
    assert base64.b64decode(image_source[len(prefix):]) == expected_svg
    assert figure.layout.meta["static_and_interactive_same_svg"] is True
    assert figure.layout.meta["generated_from_corrected_frozen_table"] is True
    assert figure.layout.meta["recomputed"] is False


def test_generated_svg_contains_current_names_not_legacy_names() -> None:
  checks = {
    "Bacteria": (
      ["Pseudomonadota", "Acidobacteriota", "Actinomycetota"],
      ["Proteobacteria", "Acidobacteria", "Actinobacteria"],
    ),
    "Archaea": (
      ["Methanobacteriota", "Thermoplasmatota", "Nitrososphaerota"],
      ["Euryarchaeota", "Thaumarchaeota"],
    ),
  }
  for domain, (current_names, legacy_names) in checks.items():
    text = exact_article_phylum_svg_bytes(domain).decode("utf-8", errors="ignore")
    for name in current_names:
      assert name in text
    for name in legacy_names:
      assert name not in text


def test_exact_figure2_and_3_viewer_has_no_invalid_taxon_trace_names() -> None:
  for domain in ("Bacteria", "Archaea"):
    figure, _, _ = exact_article_phylum_interactive(domain)
    names = [str(getattr(trace, "name", "") or "") for trace in figure.data]
    assert "NA" not in names
    assert "N/A" not in names
    assert figure.layout.meta["allow_taxonomy_missing_literals"] is True
