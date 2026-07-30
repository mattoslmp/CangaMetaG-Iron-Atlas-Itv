from __future__ import annotations

from pathlib import Path
import re
import runpy

import numpy as np
import pandas as pd

from src.article_taxonomy import (
  ARTICLE_ALPHA_ORDER,
  article_static_source_validation,
  article_taxonomy_profile_table,
  domain_rank_matrices,
  load_article_alpha_source,
)
from src.ncbi_taxonomy_harmonization import harmonize_taxonomy_frame, load_name_updates


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
CORE = ROOT / "app_core.py"


def generated_source() -> str:
  app_text = APP.read_text(encoding="utf-8")
  transform_names = re.findall(r'with_name\("src"\) / "([^"]+\.py)"', app_text)
  assert transform_names
  source = CORE.read_text(encoding="utf-8")
  for transform_name in transform_names:
    namespace = runpy.run_path(
      str(ROOT / "src" / transform_name),
      init_globals={"source": source},
    )
    source = namespace["source"]
  return source


def test_generated_app_compiles_and_all_tables_are_retractable() -> None:
  source = generated_source()
  compile(source, str(CORE), "exec")
  assert "CANGAMETAG_TAXONOMY_ARTICLE_ALIGNMENT_V1" in source
  assert "def _retractable_dataframe(" in source
  assert 'txt("Mostrar/ocultar tabela", "Show/hide table")' in source
  assert "value=True" in source[source.index("def _retractable_dataframe("):source.index("def runtime_setting(")]
  # The only remaining raw calls are the saved original Streamlit methods.
  assert source.count("st.dataframe(") == 0
  assert source.count("st.table(") == 0


def test_workflow_fits_page_and_seasonal_panels_are_separate() -> None:
  source = generated_source()
  overview = source[source.index("def overview_tab():"):source.index("def taxonomy_tab_legacy_redundant_removed():")]
  assert "whole image is fitted to the page width" in overview
  assert 'width="stretch"' in overview
  assert "display_width = max(1900" not in overview
  taxonomy = source[source.index("def taxonomy_tab():"):source.index("def site_access_gate")]
  assert 'for article_domain in ["Bacteria", "Archaea"]' in taxonomy
  assert '[("Dry", dry_column), ("Rainy", rainy_column)]' in taxonomy
  assert "article_static_source_validation" in taxonomy
  assert "same Top-14 selection" in taxonomy


def test_domain_separation_and_percentages_are_preserved() -> None:
  for domain in ("Bacteria", "Archaea"):
    counts, relative = domain_rank_matrices(domain, "Phylum", top_n=14, base_dir=ROOT)
    assert not counts.empty
    assert not relative.empty
    totals = relative.sum(axis=0)
    assert np.allclose(totals.to_numpy(float), 100.0, atol=1e-8)
    profile = article_taxonomy_profile_table(domain, "Phylum", "Individual samples", 14, ROOT)
    assert set(profile["domain"].astype(str)) == {domain}
    source_file = ROOT / "data" / "final_publication_derived" / (
      "Figure2_taxonomic_phylum_bacteria_horizontal_CDS_source.csv"
      if domain == "Bacteria"
      else "Figure3_taxonomic_phylum_archaea_horizontal_CDS_source.csv"
    )
    validation = article_static_source_validation(domain, "Phylum", 14, ROOT)
    if source_file.exists():
      assert validation.iloc[0]["status"] == "PASS", validation.to_dict("records")
      assert float(validation.iloc[0]["max_absolute_difference"]) <= 1e-8


def test_ncbi_harmonisation_changes_labels_only() -> None:
  frame = pd.DataFrame({
    "Phylum": ["Proteobacteria", "Firmicutes", "Bacteroidetes"],
    "Order": ["Order A", "Order B", "Order C"],
    "count": [10, 20, 30],
  }, index=["a", "b", "c"])
  updated = harmonize_taxonomy_frame(frame, load_name_updates(ROOT / "data" / "ncbi_taxonomy_name_updates.csv"))
  assert updated.index.equals(frame.index)
  assert updated["count"].equals(frame["count"])
  assert updated["Phylum"].tolist() == ["Pseudomonadota", "Bacillota", "Bacteroidota"]


def test_article_alpha_boxplot_uses_exact_supplementary_source() -> None:
  source = load_article_alpha_source(ROOT)
  if source.empty:
    return
  assert {"Sample", "Lake_season", "Observed_OTUs", "Chao1", "Shannon"}.issubset(source.columns)
  observed_order = [value for value in ARTICLE_ALPHA_ORDER if value in set(source["Lake_season"].astype(str))]
  first_occurrence = source["Lake_season"].astype(str).drop_duplicates().tolist()
  assert first_occurrence == observed_order
  assert int(source["Rarefaction_depth_CDS"].nunique()) == 1
  assert int(source["Rarefaction_depth_CDS"].iloc[0]) == 32999
