from __future__ import annotations

import pandas as pd

from src.ncbi_taxonomy_harmonization import (
  clean_taxonomy_label,
  harmonize_taxonomy_frame,
  is_missing_taxonomy_literal,
  update_mapping_by_rank,
)


def updates() -> pd.DataFrame:
  return pd.DataFrame([
    {"rank": "Phylum", "original_name": "Proteobacteria", "current_name": "Pseudomonadota"},
    {"rank": "Phylum", "original_name": "Pseudomonadota", "current_name": "ExampleSecondRename"},
    {"rank": "Order", "original_name": "LegacyOrder", "current_name": "CurrentOrder"},
    {"rank": "Phylum", "original_name": "N/A", "current_name": "Invented"},
  ])


def test_missing_value_literals_remain_distinct() -> None:
  values = ["", "NA", "N/A", "Unknown", "Unclassified", "Unassigned", "nan", "None"]
  assert [clean_taxonomy_label(value) for value in values] == values
  assert all(is_missing_taxonomy_literal(value) for value in values)


def test_exact_rank_aware_replacement_preserves_missing_literals() -> None:
  frame = pd.DataFrame({
    "Phylum": ["Proteobacteria", "N/A", "Unknown", "Unclassified", "Unassigned"],
    "Order": ["LegacyOrder", "NA", "N/A", "Unknown", "Unclassified"],
    "count": [10, 20, 30, 40, 50],
  }, index=["a", "b", "c", "d", "e"])
  result = harmonize_taxonomy_frame(frame, updates())
  assert result["Phylum"].tolist() == [
    "Pseudomonadota", "N/A", "Unknown", "Unclassified", "Unassigned",
  ]
  assert result["Order"].tolist() == [
    "CurrentOrder", "NA", "N/A", "Unknown", "Unclassified",
  ]
  assert result["count"].tolist() == frame["count"].tolist()
  assert result.index.equals(frame.index)
  assert result.shape == frame.shape


def test_replacement_is_not_substring_based() -> None:
  frame = pd.DataFrame({
    "Phylum": ["Proteobacteria candidate", "Candidatus Proteobacteria", "Proteobacteria"],
  })
  result = harmonize_taxonomy_frame(frame, updates())
  assert result["Phylum"].tolist() == [
    "Proteobacteria candidate", "Candidatus Proteobacteria", "Pseudomonadota",
  ]


def test_single_pass_does_not_cascade() -> None:
  frame = pd.DataFrame({"Phylum": ["Proteobacteria", "Pseudomonadota"]})
  result = harmonize_taxonomy_frame(frame, updates())
  assert result["Phylum"].tolist() == ["Pseudomonadota", "ExampleSecondRename"]


def test_missing_literals_are_excluded_from_mapping() -> None:
  mapping = update_mapping_by_rank(updates())
  assert "n/a" not in mapping["Phylum"]
  assert mapping["Phylum"]["proteobacteria"] == "Pseudomonadota"
