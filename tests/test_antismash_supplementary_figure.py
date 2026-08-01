from __future__ import annotations

import pandas as pd

from src.antismash_supplementary_figure import (
  INPUT_PATHS,
  OUTPUT_FIGURE,
  OUTPUT_TABLE,
  SCRIPT_PATH,
  bgc_supplementary_figure_svg,
)


def test_antismash_supplementary_svg_contains_provenance_and_no_ai_claim() -> None:
  table = pd.DataFrame([{
    "MAG": "MAG1",
    "BGC": "region 1",
    "antiSMASH product class": "siderophore; T1PKS",
    "Cluster figure": "",
    "iron / metal relevance": "Direct siderophore prediction.",
    "metal evidence": "direct BGC-class evidence",
    "carbon relevance": "Specialized carbon-skeleton biosynthesis class: t1pks.",
    "carbon evidence": "BGC-class chemistry",
    "literature information": "antiSMASH 7.0",
    "source region file": "MAG1.region001.gbk",
    "source values changed": False,
  }])
  svg = bgc_supplementary_figure_svg(table)
  assert b"<svg" in svg[:8192].lower()
  text = svg.decode("utf-8")
  assert "Supplementary Figure 68" in text
  assert SCRIPT_PATH in text
  assert OUTPUT_FIGURE in text
  assert OUTPUT_TABLE in text
  assert all(path in text for path in INPUT_PATHS)
  assert "No generative image model was used" in text
  assert "MAG1" in text


def test_empty_antismash_inventory_still_produces_valid_figure() -> None:
  svg = bgc_supplementary_figure_svg(pd.DataFrame())
  assert b"<svg" in svg[:8192].lower()
  assert b"No qualifying BGC" in svg
