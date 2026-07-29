#!/usr/bin/env python3
"""Generate Supplementary Figure 33 from the unchanged S32 KO matrix.

The KO order, sample order, and row-z-score values are unchanged. The display
uses the same scientifically correct orientation and dynamic pagination as Supplementary Figure 32: samples on the x-axis and KO markers/pathways on the y-axis.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import numpy as np
import pandas as pd

from generate_s31_s32 import save_ko_paginated

STEM = 'SupplementaryFigure33_ResBiomarker_Biogeochemical_cycles_zscore_heatmap'


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument('--base-dir', type=Path, default=Path(__file__).resolve().parents[2])
  parser.add_argument('--article-root', type=Path, required=True)
  args = parser.parse_args()
  base = args.base_dir.resolve()
  article = args.article_root.resolve()
  source = base / 'data/final_publication_derived/SupplementaryFigure32_biogeochemical_markers_raw_source.csv'
  raw = pd.read_csv(source, index_col=0).apply(pd.to_numeric, errors='coerce').fillna(0)
  zscore = raw.sub(raw.mean(axis=1), axis=0).div(raw.std(axis=1, ddof=0).replace(0, 1), axis=0).fillna(0)
  out_source = base / 'data/final_publication_derived/SupplementaryFigure33_biogeochemical_markers_row_zscore_source.csv'
  zscore.to_csv(out_source)
  panels = save_ko_paginated(base, STEM, zscore, article, 'Row z-score', 'RdBu_r', True)
  print({'rows': len(zscore), 'columns': len(zscore.columns), 'panels': panels, 'orientation': 'samples on x-axis; KO markers/pathways on y-axis', 'source': str(source)}, flush=True)


if __name__ == '__main__':
  main()
