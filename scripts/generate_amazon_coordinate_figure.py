#!/usr/bin/env python3
"""Generate the canonical verified-coordinate plot used as Supplementary Figure 30.

The figure number is intentionally absent from the image title. Numbering remains
in the editable Word caption, preventing discrepancies between image, filename,
manifest and document.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from PIL import Image


def sha256(path: Path) -> str:
  h = hashlib.sha256()
  with path.open("rb") as handle:
    for block in iter(lambda: handle.read(1024 * 1024), b""):
      h.update(block)
  return h.hexdigest()


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[1])
  parser.add_argument("--article-root", type=Path)
  parser.add_argument("--dpi", type=int, default=300)
  args = parser.parse_args()
  base = args.base_dir.resolve()
  article = args.article_root.resolve() if args.article_root else None
  data = [
    ('AM.P1', 'Amendoim', -(6 + 23/60 + 54.1/3600), -(50 + 22/60 + 17.6/3600)),
    ('AM.P2', 'Amendoim', -(6 + 24/60 + 3.0/3600),  -(50 + 22/60 + 18.8/3600)),
    ('V1.P1', 'Violão',   -(6 + 24/60 + 2.5/3600),  -(50 + 21/60 + 6.7/3600)),
    ('V2.P2', 'Violão',   -(6 + 23/60 + 52.3/3600), -(50 + 21/60 + 14.0/3600)),
    ('TIA.P1', 'Três Irmãs - Adjacent', -(6 + 20/60 + 51.7/3600), -(50 + 26/60 + 52.3/3600)),
    ('TIA.P2', 'Três Irmãs - Adjacent', -(6 + 20/60 + 47.7/3600), -(50 + 26/60 + 48.2/3600)),
    ('TI.P1', 'Três Irmãs Lake 2',      -(6 + 21/60 + 9.6/3600),  -(50 + 27/60 + 1.9/3600)),
    ('TI.P2', 'Três Irmãs Lake 3',      -(6 + 21/60 + 12.7/3600), -(50 + 26/60 + 39.5/3600)),
    ('TI.P3', 'Três Irmãs Lake 4',      -(6 + 21/60 + 19.4/3600), -(50 + 26/60 + 44.2/3600)),
    ('TI.P4', 'Três Irmãs Lake 5',      -(6 + 21/60 + 23.5/3600), -(50 + 26/60 + 53.6/3600)),
  ]
  df = pd.DataFrame(data, columns=['Site','Lake','Latitude','Longitude'])
  color_map = {'Amendoim':'#2E86DE', 'Violão':'#E67E22', 'Três Irmãs - Adjacent':'#8E44AD', 'Três Irmãs Lake 2':'#27AE60', 'Três Irmãs Lake 3':'#16A085', 'Três Irmãs Lake 4':'#C0392B', 'Três Irmãs Lake 5':'#7F8C8D'}
  fig, ax = plt.subplots(figsize=(10.0, 7.6), dpi=args.dpi)
  for _, row in df.iterrows():
    ax.scatter(row['Longitude'], row['Latitude'], s=120, color=color_map.get(row['Lake'], '#1f77b4'), edgecolor='white', linewidth=1.2)
    ax.text(row['Longitude'] + 0.0012, row['Latitude'] + 0.0010, f"{row['Site']} | {row['Lake']}", fontsize=9)
  ax.set_title('Verified sampling-point coordinates used in the Amazonian lake atlas maps', fontsize=13, fontweight='bold')
  ax.set_xlabel('Longitude (decimal degrees)')
  ax.set_ylabel('Latitude (decimal degrees)')
  ax.grid(True, alpha=0.25)
  ax.invert_xaxis()
  for spine in ['top','right']:
    ax.spines[spine].set_visible(False)
  fig.tight_layout()
  stem = 'SupplementaryFigure30_verified_coordinates_original'
  output_dirs = [base / 'outputs/final_publication_figures', base / 'outputs/app_supplementary_figures']
  if article:
    output_dirs.append(article / '03_Supplementary_Figures')
  outputs = {}
  for directory in output_dirs:
    directory.mkdir(parents=True, exist_ok=True)
  canonical = output_dirs[0]
  png = canonical / f'{stem}.png'
  pdf = canonical / f'{stem}.pdf'
  svg = canonical / f'{stem}.svg'
  fig.savefig(png, dpi=args.dpi, facecolor='white')
  fig.savefig(pdf, dpi=args.dpi, facecolor='white')
  fig.savefig(svg, facecolor='white')
  plt.close(fig)
  df.to_csv(base / 'data/final_publication_derived/SupplementaryFigure30_verified_coordinates_source.csv', index=False)
  for directory in output_dirs[1:]:
    for source in (png, pdf, svg):
      (directory / source.name).write_bytes(source.read_bytes())
  report = {
    'figure': 'S30',
    'script': 'scripts/generate_amazon_coordinate_figure.py',
    'command': 'python scripts/generate_amazon_coordinate_figure.py --base-dir . --article-root <article_root>',
    'internal_figure_number': None,
    'word_caption_number': 30,
    'scientific_values_changed': False,
    'outputs': {p.suffix.lstrip('.'): {'path': str(p), 'sha256': sha256(p)} for p in (png,pdf,svg)},
  }
  validation = base / 'validation'
  validation.mkdir(parents=True, exist_ok=True)
  (validation / 'SupplementaryFigure30_numbering_audit.json').write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding='utf-8')
  print(json.dumps(report, indent=2, ensure_ascii=False))
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
