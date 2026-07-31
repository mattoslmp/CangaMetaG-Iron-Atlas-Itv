from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from src.article_taxonomy import article_alpha_boxplot
from src.ncbi_taxonomy_harmonization import transfer_palette_names
from src.taxonomy_palette import load_palette


ROOT = Path(__file__).resolve().parents[1]


def test_alpha_legend_stays_below_plot() -> None:
  figure, source = article_alpha_boxplot(ROOT)
  assert not source.empty
  assert figure.layout.meta["preserve_legend_position"] is True
  assert float(figure.layout.legend.y) < 0
  assert int(figure.layout.margin.b) >= 185


def test_packaged_taxonomy_palette_is_valid_unique_and_preserves_article_colours() -> None:
  palette = load_palette(ROOT / "data" / "taxonomy_palette.json")
  assert len(palette) == len({str(value).upper() for value in palette.values()})
  assert "Proteobacteria" not in palette
  assert palette["Pseudomonadota"] == "#4D87EF"
  assert palette["Bacillota"] == "#D69966"
  assert palette["Actinomycetota"] == "#1C36CE"
  assert palette["Chloroflexota"] == "#7B2CBF"


def test_palette_transfer_prefers_the_historical_colour() -> None:
  palette = {"Proteobacteria": "#4D87EF", "Pseudomonadota": "#123456", "Other": "#654321"}
  updates = pd.DataFrame([{
    "rank": "Phylum",
    "original_name": "Proteobacteria",
    "current_name": "Pseudomonadota",
  }])
  transferred = transfer_palette_names(palette, updates)
  assert "Proteobacteria" not in transferred
  assert transferred["Pseudomonadota"] == "#4D87EF"
  assert len(transferred) == len(set(transferred.values()))


def test_st8_raw_audit_uses_original_table_not_plotly_fallback() -> None:
  source = (ROOT / "app_core.py").read_text(encoding="utf-8")
  assert "audit_input_table=source_table" in source
  assert "Zero is a measured absence and is retained as numeric 0." in source
  assert "tables/Supplementary_Table_8.xlsx — ST8 — all KO biomarkers" in source


def test_final_script_inventory_excludes_directory_sweeps() -> None:
  source = (ROOT / "app_core.py").read_text(encoding="utf-8")
  assert "Final scripts and figures — canonical scripts in use only" in source
  assert "for folder in all_script_dirs" not in source
  assert "Old, archived or unused scripts are not displayed" in source
