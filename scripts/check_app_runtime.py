#!/usr/bin/env python3
"""Validate the packaged CangaMetaG Streamlit app before launch.

This check is intentionally offline. It verifies the complete ``src`` package,
all symbols imported by ``app.py``, Python syntax, and representative local data
workflows without contacting external APIs.
"""
from __future__ import annotations

import ast
import importlib
import importlib.util
import py_compile
import sys

import pandas as pd
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))


def fail(message: str) -> None:
  raise RuntimeError(message)


def main() -> int:
  app_path = ROOT / "app.py"
  if not app_path.exists():
    fail(f"Missing app.py: {app_path}")

  python_files = [app_path, *sorted((ROOT / "src").glob("*.py"))]
  for path in python_files:
    py_compile.compile(str(path), doraise=True)
  print(f"[PASS] Python syntax: {len(python_files)} files")

  tree = ast.parse(app_path.read_text(encoding="utf-8"))
  checked_modules = 0
  checked_symbols = 0
  for node in ast.walk(tree):
    if not isinstance(node, ast.ImportFrom) or not node.module or not node.module.startswith("src"):
      continue
    module = importlib.import_module(node.module)
    checked_modules += 1
    for alias in node.names:
      if alias.name == "*":
        continue
      if not hasattr(module, alias.name):
        fail(f"Missing symbol {node.module}.{alias.name}")
      checked_symbols += 1
  print(f"[PASS] app.py imports: {checked_modules} src imports, {checked_symbols} symbols")

  from src.runtime_paths import ensure_runtime_layout, runtime_summary
  from src.supplementary_database import (
    ST8_ALL_KO_SHEET,
    amazonia_vs_iron_marker_summary,
    counts_table,
    figure11_environment_metadata,
    iron_fe_marker_summary,
    marker_table,
    taxonomy_profile_table,
  )
  from src.functional_annotations import build_annotation_dataset
  from src.kegg_modules import load_module_matrices
  from src.publication_rda import publication_nmds_figure, publication_rda_figure
  from src.integrated_omics import pca_integrated, pcoa_bray_curtis, nmds_bray_curtis

  ensure_runtime_layout()
  summary = runtime_summary()
  if not summary:
    fail("Runtime directory summary is empty")

  markers = marker_table()
  required_marker_cols = {"KO", "Study", "General metabolism", "KO description", "Marker for:", "KEGG MODULE"}
  if markers.empty or not required_marker_cols.issubset(markers.columns):
    fail("KO marker catalogue failed schema validation")

  counts, numeric_cols = counts_table("table8", ST8_ALL_KO_SHEET, ["KO", "Metabolism", "KO description"])
  if counts.empty or len(numeric_cols) < 20:
    fail("Supplementary Table 8 count matrix is unavailable")

  taxonomy = taxonomy_profile_table("Phylum — Bacteria", view_mode="Individual samples")
  if taxonomy.empty or not {"group", "taxon", "abundance"}.issubset(taxonomy.columns):
    fail("Taxonomy profile failed")

  if amazonia_vs_iron_marker_summary().empty:
    fail("Amazonia versus external KO summary failed")
  if iron_fe_marker_summary().empty:
    fail("Iron-marker summary failed")
  if figure11_environment_metadata().empty:
    fail("Environmental metadata integration failed")

  _rda_fig, rda_scores, rda_env, rda_taxa = publication_rda_figure(ROOT)
  if rda_scores.empty or rda_env.empty or rda_taxa.empty:
    fail("Canonical RDA data failed")
  _nmds_fig, nmds_scores = publication_nmds_figure(ROOT)
  if nmds_scores.empty:
    fail("Canonical NMDS data failed")

  # Integrated ordinations use the same NMDS transformation/optimiser and
  # return the tuple signatures expected by the Streamlit interface.
  toy_integrated = pd.DataFrame({
    "group": [f"G{i}" for i in range(8)],
    "KO::A": [5, 0, 3, 0, 4, 1, 2, 5],
    "KO::B": [0, 4, 1, 1, 0, 3, 2, 1],
    "taxon::X": [1, 0, 0, 5, 2, 1, 4, 0],
    "taxon::Y": [0, 1, 2, 1, 1, 4, 0, 3],
  })
  pca_scores, pca_loadings, pca_variance = pca_integrated(toy_integrated)
  pcoa_scores, pcoa_variance = pcoa_bray_curtis(toy_integrated)
  integrated_nmds = nmds_bray_curtis(toy_integrated)
  if any(frame.empty for frame in [pca_scores, pca_loadings, pca_variance, pcoa_scores, pcoa_variance, integrated_nmds]):
    fail("Integrated ordination workflows failed")
  if int(integrated_nmds["n_init"].iloc[0]) != 20 or int(integrated_nmds["max_iter"].iloc[0]) != 1000:
    fail("Integrated NMDS is not using the article optimiser settings")

  annotation, annotation_meta, _id_col, _name_col = build_annotation_dataset("table8", "KO")
  if annotation.empty or annotation_meta.empty:
    fail("Functional annotation data failed")

  status_matrix, score_matrix = load_module_matrices("Metagenomes")
  if status_matrix.empty or score_matrix.empty:
    fail("KEGG/KEMET module matrices failed")

  print("[PASS] Representative local scientific workflows")
  if importlib.util.find_spec("streamlit") is None:
    print("[WARN] Streamlit is not installed in this Python environment.")
    print("       Install dependencies with: python -m pip install -r requirements.txt")
  else:
    print("[PASS] Streamlit is installed")
  print("APP_RUNTIME_CHECK_PASS")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
