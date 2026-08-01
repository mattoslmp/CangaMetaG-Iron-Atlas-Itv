from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.final_taxonomy_static_figures import supplementary_taxonomy_assets
from src.taxonomy_final_contract import (
  OTHER_TAXA_THRESHOLD_PERCENT,
  aggregate_below_five_percent,
  current_taxonomy_label,
  final_domain_rank_matrices,
  install_final_taxonomy_contract,
  legacy_labels_present,
)


ROOT = Path(__file__).resolve().parents[1]


def test_strict_below_five_aggregation_preserves_totals_and_unclassified() -> None:
  counts = pd.DataFrame(
    {
      "S1": [60, 4, 3, 33],
      "S2": [50, 5, 2, 43],
    },
    index=["Pseudomonadota", "LowTaxon", "Unclassified", "ExactlyFive"],
    dtype=float,
  )
  relative = counts.copy()
  count_final, relative_final, aggregated = aggregate_below_five_percent(
    counts,
    relative,
    "Phylum",
  )
  assert aggregated == ["LowTaxon"]
  assert "Other taxa" in relative_final.index
  assert "Unclassified" in relative_final.index
  assert "ExactlyFive" in relative_final.index
  assert "LowTaxon" not in relative_final.index
  assert np.allclose(counts.sum(axis=0), count_final.sum(axis=0))
  assert np.allclose(relative.sum(axis=0), relative_final.sum(axis=0))


def test_packaged_current_name_mapping_contains_pseudomonadota() -> None:
  assert current_taxonomy_label("Proteobacteria", "Phylum", ROOT) == "Pseudomonadota"


def test_real_domain_matrices_use_current_names_and_strict_threshold() -> None:
  install_final_taxonomy_contract()
  for domain in ("Bacteria", "Archaea"):
    for rank in ("Phylum", "Genus"):
      _, relative = final_domain_rank_matrices(domain, rank, base_dir=ROOT)
      assert np.allclose(relative.sum(axis=0).to_numpy(float), 100.0, atol=1e-7)
      assert not legacy_labels_present(relative.index.astype(str).tolist(), rank, ROOT)
      aggregate = "Other genera" if rank == "Genus" else "Other taxa"
      assert float(relative.attrs["other_taxa_threshold_percent"]) == OTHER_TAXA_THRESHOLD_PERCENT
      for taxon in relative.attrs.get("aggregated_taxa", []):
        assert taxon not in relative.index
      assert "Unclassified" in relative.index or aggregate in relative.index


def test_all_supplementary_taxonomy_svgs_are_generated_from_contract() -> None:
  install_final_taxonomy_contract()
  assets = supplementary_taxonomy_assets("en")
  assert set(assets) == {
    "SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct.svg",
    "SupplementaryFigure44_Taxonomy_Bacteria_Phylum_individual_samples_heatmap_relative_abundance.svg",
    "SupplementaryFigure45_Taxonomy_Archaea_Phylum_individual_samples_barplot_100pct.svg",
    "SupplementaryFigure46_Taxonomy_Archaea_Phylum_individual_samples_heatmap_relative_abundance.svg",
  }
  for name, payload in assets.items():
    assert b"<svg" in payload[:8192].lower(), name
  assert b"Other taxa" in assets[
    "SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct.svg"
  ]
