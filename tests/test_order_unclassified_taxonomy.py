from __future__ import annotations

from pathlib import Path
import runpy

import numpy as np
import pandas as pd

from src.taxonomy_order_unclassified import (
  normalize_order_label,
  normalize_order_taxonomy_frame,
  patch_taxonomy_modules,
)


ROOT = Path(__file__).resolve().parents[1]
MISSING = {"", "na", "n/a", "nan", "none", "null", "<na>"}


def test_order_missing_literals_become_unclassified_only_in_order_column() -> None:
  frame = pd.DataFrame(
    {
      "Order": ["NA", "N/A", "", "Unclassified", "Burkholderiales"],
      "Family": ["NA", "N/A", "", "Unclassified", "Burkholderiaceae"],
    },
    index=["otu1", "otu2", "otu3", "otu4", "otu5"],
  )
  normalized = normalize_order_taxonomy_frame(frame)

  assert normalized.index.equals(frame.index)
  assert normalized.shape == frame.shape
  assert normalized["Order"].tolist() == [
    "Unclassified",
    "Unclassified",
    "Unclassified",
    "Unclassified",
    "Burkholderiales",
  ]
  assert normalized["Family"].tolist() == frame["Family"].tolist()


def test_order_normalization_merges_counts_without_changing_totals() -> None:
  taxonomy = pd.DataFrame(
    {"Order": ["NA", "Unclassified", "Burkholderiales"]},
    index=["otu1", "otu2", "otu3"],
  )
  counts = pd.DataFrame(
    {"AM.P1.D": [3, 5, 7], "AM.P1.R": [2, 4, 8]},
    index=taxonomy.index,
  )
  normalized = normalize_order_taxonomy_frame(taxonomy)
  work = counts.copy()
  work["taxon"] = normalized["Order"]
  grouped = work.groupby("taxon", sort=False).sum(numeric_only=True)

  assert grouped.loc["Unclassified", "AM.P1.D"] == 8
  assert grouped.loc["Unclassified", "AM.P1.R"] == 6
  assert np.array_equal(
    grouped.sum(axis=0).to_numpy(float),
    counts.sum(axis=0).to_numpy(float),
  )


def test_shared_article_order_matrices_have_no_na_labels() -> None:
  status = patch_taxonomy_modules()
  assert status["article_taxonomy"] is True
  assert status["supplementary_database"] is True

  from src import article_taxonomy

  for domain in ("Bacteria", "Archaea"):
    counts, relative = article_taxonomy.domain_rank_matrices(
      domain,
      "Order",
      top_n=None,
      base_dir=ROOT,
    )
    labels = {str(value).strip().casefold() for value in counts.index}
    assert not labels.intersection(MISSING)
    assert np.allclose(
      relative.sum(axis=0).to_numpy(float),
      100.0,
      atol=1e-10,
      rtol=0.0,
    )


def test_app_transform_loads_order_patch_before_runtime_functions() -> None:
  source = '''from __future__ import annotations


def runtime_setting(key: str, default: str = "") -> str:
  return default
'''
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_order_unclassified_transform.py"),
    init_globals={"source": source},
  )["source"]
  assert "_patch_order_taxonomy_modules" in transformed
  assert transformed.index("_patch_order_taxonomy_modules()") < transformed.index("def runtime_setting")
  compile(transformed, "synthetic_order_unclassified_app.py", "exec")


def test_static_regeneration_scripts_preserve_unclassified_rule() -> None:
  refresh_script = (
    ROOT / "scripts" / "taxonomy" /
    "harmonize_ncbi_taxonomy_and_regenerate.py"
  ).read_text(encoding="utf-8")
  supplementary_script = (
    ROOT / "scripts" / "generate_taxonomy_supplementary_figures.py"
  ).read_text(encoding="utf-8")

  assert "normalize_order_taxonomy_frame" in refresh_script
  assert "normalize_current_taxonomy_file" in refresh_script
  assert "skip_regeneration=True" in refresh_script
  assert "regenerate_figures(root, current)" in refresh_script
  assert 'return "Unclassified"' in supplementary_script
  assert '"na"' in supplementary_script
  assert '"n/a"' in supplementary_script


def test_label_function_keeps_valid_order_names() -> None:
  assert normalize_order_label("NA") == "Unclassified"
  assert normalize_order_label(" N/A ") == "Unclassified"
  assert normalize_order_label("Burkholderiales") == "Burkholderiales"
