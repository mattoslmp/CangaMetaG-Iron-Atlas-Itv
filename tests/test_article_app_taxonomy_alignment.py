from __future__ import annotations

import numpy as np

from src.article_taxonomy import article_static_source_validation, domain_rank_matrices


def test_static_and_interactive_phylum_values_are_identical() -> None:
  for domain in ("Bacteria", "Archaea"):
    validation = article_static_source_validation(domain, "Phylum", 14)
    assert not validation.empty
    row = validation.iloc[0]
    assert row["status"] == "PASS"
    assert float(row["max_absolute_difference"]) <= 1e-8
    assert bool(row.get("values_modified", False)) is False


def test_each_interactive_phylum_sample_remains_100_percent() -> None:
  for domain in ("Bacteria", "Archaea"):
    _, relative = domain_rank_matrices(domain, "Phylum", top_n=14)
    totals = relative.sum(axis=0).to_numpy(float)
    assert np.allclose(totals, 100.0, atol=1e-8, rtol=0.0)
