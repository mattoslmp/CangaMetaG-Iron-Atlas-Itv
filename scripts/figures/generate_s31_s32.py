#!/usr/bin/env python3
"""Generate canonical Supplementary Figures 31 and 32.

Only the presentation of Supplementary Figure 32 is revised here. All KO rows
and all 20 samples are preserved in the scientifically correct orientation:
sediment metagenome samples are columns (x-axis) and KO markers with associated
metabolic pathways are rows (y-axis). Pagination is computed from the available
page height and label lengths. No values, sample order, KO order, filters, or
colour scale are changed.
"""
from __future__ import annotations

from pathlib import Path
import argparse
import base64
import math
import json
import re
import shutil
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
import numpy as np
import pandas as pd
from PIL import Image

from revision_common import wrap

KO_Y_AXIS_TITLE = "KO marker and associated metabolic pathway in biogeochemical cycles"
SAMPLE_X_AXIS_TITLE = "Sediment metagenome sample"
MIN_KO_FONT_PT = 9.0
DPI = 300


def _save_svg_from_png(png: Path, svg: Path) -> None:
  with Image.open(png) as opened:
    width, height = opened.size
  payload = base64.b64encode(png.read_bytes()).decode("ascii")
  svg.write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    f'<image href="data:image/png;base64,{payload}" width="{width}" height="{height}"/></svg>',
    encoding="utf-8",
  )


def _contact_sheet(panel_pngs: list[Path], target: Path, gap: int = 24, max_width: int = 1200) -> None:
  images = [Image.open(path).convert("RGB") for path in panel_pngs]
  try:
    width = min(max_width, max(image.width for image in images))
    scaled = []
    for image in images:
      if image.width == width:
        scaled.append(image)
      else:
        height = round(image.height * width / image.width)
        scaled.append(image.resize((width, height), Image.Resampling.LANCZOS))
    total_height = sum(image.height for image in scaled) + gap * (len(scaled) - 1)
    canvas = Image.new("RGB", (width, total_height), "white")
    y = 0
    for image in scaled:
      canvas.paste(image, (0, y))
      y += image.height + gap
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, "PNG", dpi=(DPI, DPI), compress_level=6)
  finally:
    for image in images:
      image.close()


def generic_heatmap_fig(mat: pd.DataFrame, title: str, cbar_label: str, cell_w: float=.62, cell_h: float=.52,
                        row_font: float=11, col_font: float=11, cmap: str='RdBu_r', center_zero: bool=True):
  nr, nc = mat.shape
  fw = max(12, 4.8 + nc * cell_w)
  fh = max(7, 2.3 + nr * cell_h)
  fig, ax = plt.subplots(figsize=(fw, fh))
  vals = mat.to_numpy(float)
  if center_zero:
    vmax = np.nanmax(np.abs(vals)) or 1
    im = ax.imshow(vals, aspect='auto', cmap=cmap, vmin=-vmax, vmax=vmax, interpolation='nearest')
  else:
    im = ax.imshow(vals, aspect='auto', cmap=cmap, interpolation='nearest')
  ax.set_xticks(np.arange(nc))
  ax.set_xticklabels([wrap(x, 22) for x in mat.columns], rotation=55, ha='right', fontsize=col_font)
  ax.set_yticks(np.arange(nr))
  ax.set_yticklabels([wrap(str(x).replace(':', ': '), 38) for x in mat.index], fontsize=row_font)
  ax.tick_params(axis='both', length=0, pad=5)
  ax.set_xlabel('Environmental group / sample', fontsize=14, fontweight='bold', labelpad=12)
  ax.set_ylabel('Taxon or functional marker', fontsize=14, fontweight='bold')
  ax.set_title(title.split('—')[-1].strip(), loc='left', fontsize=16, fontweight='bold', pad=8)
  cb = fig.colorbar(im, ax=ax, pad=.015, fraction=.028)
  cb.set_label(cbar_label, fontsize=13, fontweight='bold')
  cb.ax.tick_params(labelsize=11)
  ax.set_xticks(np.arange(-.5, nc, 1), minor=True)
  ax.set_yticks(np.arange(-.5, nr, 1), minor=True)
  ax.grid(which='minor', color='white', lw=.6)
  ax.tick_params(which='minor', bottom=False, left=False)
  fig.subplots_adjust(left=.43, right=.93, bottom=.30, top=.90)
  return fig


def save_generic_paginated(base: Path, stem: str, mat: pd.DataFrame, title: str, cbar_label: str,
                            rows_per: int, article_root: Path | None, cmap: str='RdBu_r', center_zero: bool=True) -> int:
  outdir = base / 'outputs/final_publication_figures'
  copies = [base / 'outputs/app_supplementary_figures']
  if article_root:
    copies.append(article_root / '03_Supplementary_Figures')
  for directory in [outdir, *copies]:
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob(stem + '*'):
      if old.is_file():
        old.unlink()
  panels = []
  for i, start in enumerate(range(0, len(mat), rows_per), 1):
    sub = mat.iloc[start:start + rows_per]
    fig = generic_heatmap_fig(sub, f'{title} — P{i:02d}', cbar_label, cmap=cmap, center_zero=center_zero)
    png = outdir / f'{stem}_P{i:02d}.png'
    fig.savefig(png, dpi=DPI, facecolor='white', bbox_inches='tight')
    plt.close(fig)
    _save_svg_from_png(png, outdir / f'{stem}_P{i:02d}.svg')
    panels.append(png)
  with PdfPages(outdir / f'{stem}.pdf') as pdf:
    for i, start in enumerate(range(0, len(mat), rows_per), 1):
      fig = generic_heatmap_fig(mat.iloc[start:start + rows_per], f'{title} — P{i:02d}', cbar_label, cmap=cmap, center_zero=center_zero)
      pdf.savefig(fig, bbox_inches='tight')
      plt.close(fig)
  _contact_sheet(panels, outdir / f'{stem}.png')
  _save_svg_from_png(outdir / f'{stem}.png', outdir / f'{stem}.svg')
  for directory in copies:
    for source in outdir.glob(stem + '*'):
      shutil.copy2(source, directory / source.name)
  return len(panels)


def _ko_label(value: object, width: int = 58) -> str:
  text = ' '.join(str(value).split())
  return '\n'.join(textwrap.wrap(text, width=width, break_long_words=False, break_on_hyphens=False))


def determine_ko_rows_per_panel(labels: list[str], usable_height_inches: float = 8.25,
                                minimum_font_pt: float = MIN_KO_FONT_PT) -> int:
  """Choose a reproducible row count from label length and physical page height."""
  longest = max((len(str(x)) for x in labels), default=0)
  wrapped_lines = 3 if longest > 125 else (2 if longest > 58 else 1)
  line_height_inches = minimum_font_pt * 1.10 / 72.0
  row_height_inches = max(0.245, wrapped_lines * line_height_inches)
  calculated = int(usable_height_inches // row_height_inches)
  return max(24, min(32, calculated))


def _bbox_overlap(a, b, pad: float = 2.0) -> bool:
  return not (a.x1 + pad <= b.x0 or b.x1 + pad <= a.x0 or a.y1 + pad <= b.y0 or b.y1 + pad <= a.y0)


def _validate_ko_orientation(mat: pd.DataFrame) -> dict[str, object]:
  rows = [str(x) for x in mat.index]
  cols = [str(x) for x in mat.columns]
  sample_pattern = re.compile(r'^(?:AM|TIA|TI|VI)\.P\d+\.[DR]$')
  ko_pattern = re.compile(r'^K\d{5}\b')
  sample_columns = sum(bool(sample_pattern.match(x)) for x in cols)
  ko_rows = sum(bool(ko_pattern.match(x)) for x in rows)
  wrong_sample_rows = [x for x in rows if sample_pattern.match(x)]
  wrong_ko_columns = [x for x in cols if ko_pattern.match(x)]
  passed = sample_columns == len(cols) and ko_rows == len(rows) and not wrong_sample_rows and not wrong_ko_columns
  if not passed:
    raise RuntimeError({
      'error': 'KO heatmap orientation validation failed',
      'sample_columns': sample_columns,
      'column_count': len(cols),
      'ko_rows': ko_rows,
      'row_count': len(rows),
      'wrong_sample_rows': wrong_sample_rows[:10],
      'wrong_ko_columns': wrong_ko_columns[:10],
    })
  return {
    'row_semantics': 'KO marker and associated metabolic pathway',
    'column_semantics': 'sediment metagenome sample',
    'row_count': len(rows),
    'column_count': len(cols),
    'first_row_identifier': rows[0] if rows else '',
    'last_row_identifier': rows[-1] if rows else '',
    'first_column_identifier': cols[0] if cols else '',
    'last_column_identifier': cols[-1] if cols else '',
    'orientation': 'samples on x-axis; KO markers/pathways on y-axis',
    'validation': 'PASS',
  }


def ko_panel_figure(sub: pd.DataFrame, panel: int, total: int, cbar_label: str, cmap: str, center_zero: bool):
  # sub is KO x sample and remains KO x sample in the final display.
  nr, nc = sub.shape
  fig = plt.figure(figsize=(16.0, 11.6), facecolor='white')
  grid = fig.add_gridspec(
    nrows=1, ncols=2, width_ratios=[32, 1.2],
    left=0.375, right=0.935, bottom=0.165, top=0.875, wspace=0.065,
  )
  ax = fig.add_subplot(grid[0, 0])
  cax = fig.add_subplot(grid[0, 1])
  values = sub.to_numpy(float)
  if center_zero:
    vmax = max(float(np.nanmax(np.abs(values))), 1e-12)
    image = ax.imshow(values, aspect='auto', cmap=cmap, vmin=-vmax, vmax=vmax, interpolation='nearest')
  else:
    image = ax.imshow(values, aspect='auto', cmap=cmap, interpolation='nearest')
  ax.set_xticks(np.arange(nc))
  ax.set_xticklabels([str(x) for x in sub.columns], rotation=45, ha='right', rotation_mode='anchor', fontsize=10.5)
  ax.set_yticks(np.arange(nr))
  ax.set_yticklabels([_ko_label(x, 58) for x in sub.index], fontsize=MIN_KO_FONT_PT, linespacing=0.95)
  ax.tick_params(axis='both', length=0, pad=4)
  ax.set_xlabel(SAMPLE_X_AXIS_TITLE, fontsize=14.5, fontweight='bold', labelpad=12)
  ax.set_ylabel(KO_Y_AXIS_TITLE, fontsize=14.5, fontweight='bold', labelpad=12)
  title_artist = fig.text(0.035, 0.970, f'Biogeochemical KO-marker heatmap - Panel P{panel:03d} of P{total:03d}', fontsize=17.0, fontweight='bold', ha='left', va='top')
  ax.set_xticks(np.arange(-.5, nc, 1), minor=True)
  ax.set_yticks(np.arange(-.5, nr, 1), minor=True)
  ax.grid(which='minor', color='white', lw=.65)
  ax.tick_params(which='minor', bottom=False, left=False)
  colorbar = fig.colorbar(image, cax=cax)
  colorbar.set_label(cbar_label, fontsize=12.5, fontweight='bold', labelpad=4)
  colorbar.ax.tick_params(labelsize=11.5)
  fig.canvas.draw()
  renderer = fig.canvas.get_renderer()
  figbox = fig.bbox
  axbox = ax.get_window_extent(renderer)
  cbox = cax.get_window_extent(renderer)
  outside = []
  artists = [title_artist, *ax.get_xticklabels(), *ax.get_yticklabels(), ax.xaxis.label, ax.yaxis.label, *colorbar.ax.get_yticklabels(), colorbar.ax.yaxis.label]
  for artist in artists:
    if not artist.get_visible() or not artist.get_text():
      continue
    box = artist.get_window_extent(renderer)
    if box.x0 < figbox.x0 - 2 or box.y0 < figbox.y0 - 2 or box.x1 > figbox.x1 + 2 or box.y1 > figbox.y1 + 2:
      outside.append({'text': artist.get_text().replace('\n', ' | ')[:140], 'bbox': [box.x0, box.y0, box.x1, box.y1]})
  if _bbox_overlap(axbox, cbox, pad=4):
    raise RuntimeError('S32/S33 colorbar overlaps heatmap matrix')
  if outside:
    raise RuntimeError(f'S32/S33 layout clipping: {outside[:8]}')
  layout = {
    'figure_inches': [16.0, 11.6],
    'rows': nr,
    'columns': nc,
    'x_tick_font_pt': 10.5,
    'y_tick_font_pt': MIN_KO_FONT_PT,
    'axis_title_font_pt': 14.5,
    'title_font_pt': 17.0,
    'colorbar_tick_font_pt': 11.5,
    'colorbar_dedicated_axis': True,
    'all_text_inside_figure': True,
    'orientation': 'samples on x-axis; KO markers/pathways on y-axis',
  }
  return fig, layout


def save_ko_paginated(base: Path, stem: str, mat: pd.DataFrame, article_root: Path | None,
                      cbar_label: str, cmap: str, center_zero: bool) -> int:
  orientation = _validate_ko_orientation(mat)
  rows_per_panel = determine_ko_rows_per_panel([str(x) for x in mat.index])
  out = base / 'outputs/final_publication_figures'
  destinations = [base / 'outputs/app_supplementary_figures']
  if article_root:
    destinations.append(article_root / '03_Supplementary_Figures')
  for directory in [out, *destinations]:
    directory.mkdir(parents=True, exist_ok=True)
    for old in directory.glob(stem + '*'):
      if old.is_file():
        old.unlink()
  total = math.ceil(len(mat) / rows_per_panel)
  panel_pngs: list[Path] = []
  panel_records: list[dict[str, object]] = []
  with PdfPages(out / f'{stem}.pdf') as pdf:
    for i, start in enumerate(range(0, len(mat), rows_per_panel), 1):
      sub = mat.iloc[start:start + rows_per_panel]
      fig, layout = ko_panel_figure(sub, i, total, cbar_label, cmap, center_zero)
      png = out / f'{stem}_P{i:03d}.png'
      fig.savefig(png, dpi=DPI, facecolor='white')
      pdf.savefig(fig, facecolor='white')
      plt.close(fig)
      _save_svg_from_png(png, out / f'{stem}_P{i:03d}.svg')
      panel_pngs.append(png)
      panel_records.append({'panel': f'P{i:03d}', 'row_start': start + 1, 'row_end': start + len(sub), 'layout': layout})
  _contact_sheet(panel_pngs, out / f'{stem}.png')
  _save_svg_from_png(out / f'{stem}.png', out / f'{stem}.svg')
  for destination in destinations:
    for source in out.glob(stem + '*'):
      shutil.copy2(source, destination / source.name)
  validation_dir = base / 'validation'
  validation_dir.mkdir(parents=True, exist_ok=True)
  audit = {
    'figure_stem': stem,
    'input_rows': len(mat),
    'input_columns': len(mat.columns),
    'rows_per_panel': rows_per_panel,
    'panel_count': total,
    'orientation': orientation,
    'panels': panel_records,
    'data_changed': False,
  }
  (validation_dir / f'{stem}_orientation_layout_audit.json').write_text(json.dumps(audit, indent=2), encoding='utf-8')
  return total


def make_s31(base: Path, article_root: Path | None) -> int:
  audit = base / 'outputs/final_publication_source_tables'
  parts = []
  for n in (14, 20, 23):
    f = next(audit.glob(f'source_SupplementaryFigure{n}_*.csv'))
    d = pd.read_csv(f)
    parts.append(d[['display_group', 'taxon', 'relative_abundance_percent', 'taxonomy_level']])
  df = pd.concat(parts, ignore_index=True)
  piv = df.pivot_table(index=['taxonomy_level', 'taxon'], columns='display_group', values='relative_abundance_percent', aggfunc='sum', fill_value=0)
  keep = piv.gt(0).sum(axis=1) >= 3
  piv = piv[keep]
  totals = piv.sum(axis=1)
  piv = piv.loc[totals.sort_values(ascending=False).head(60).index]
  labels = [f'{rank}: {str(taxon).split(":")[-1]}' for rank, taxon in piv.index]
  piv.index = labels
  def short_group(x):
    layer = 'MGX' if 'Metagenomics' in x else ('MTX' if 'Metatranscriptomics' in x else '')
    for key, name in [('Richmond Mine', 'Richmond AMD'), ('Akron', 'Akron AMD'), ('Lake Towuti', 'Lake Towuti'), ('Lake Matano', 'Lake Matano'), ('Lake Superior', 'Lake Superior'), ('Burr Oak', 'Burr Oak control'), ('Hydrothermal', 'Hydrothermal mats')]:
      if key in x:
        return f'{name} | {layer}'
    return x[:28]
  piv.columns = [short_group(x) for x in piv.columns]
  z = piv.sub(piv.mean(axis=1), axis=0).div(piv.std(axis=1).replace(0, 1), axis=0)
  derived = base / 'data/final_publication_derived'
  derived.mkdir(parents=True, exist_ok=True)
  z.to_csv(derived / 'SupplementaryFigure31_common_taxa_heatmap_source_zscore.csv')
  return save_generic_paginated(base, 'SupplementaryFigure31_common_taxa_heatmap', z, 'PANEL', 'Row z-score', 15, article_root)


def make_s32(base: Path, article_root: Path | None, table: Path) -> int:
  df = pd.read_excel(table, sheet_name='ResBiomarker-Biochemical-cycles')
  df = df[df['KO'].notna()].copy()
  sample_cols = [c for c in df.columns[3:] if not str(c).startswith('Unnamed')]
  for column in sample_cols:
    df[column] = pd.to_numeric(df[column], errors='coerce').fillna(0)
  labels = [f"{ko} | {' '.join(str(m).split())}" for ko, m in zip(df['KO'], df['Metabolism'].fillna(''))]
  df.index = labels
  matrix = df[sample_cols].copy()
  matrix.columns = [str(c).strip() for c in matrix.columns]
  derived = base / 'data/final_publication_derived'
  derived.mkdir(parents=True, exist_ok=True)
  matrix.to_csv(derived / 'SupplementaryFigure32_biogeochemical_markers_raw_source.csv')
  return save_ko_paginated(base, 'SupplementaryFigure32_ResBiomarker_Biogeochemical_cycles_raw_heatmap', matrix, article_root, 'Abundance', 'viridis', False)


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument('--base-dir', type=Path, default=Path(__file__).resolve().parents[2])
  parser.add_argument('--article-root', type=Path)
  parser.add_argument('--table4', type=Path)
  parser.add_argument('--only', choices=['31', '32'], action='append')
  args = parser.parse_args()
  base = args.base_dir.resolve()
  article_root = args.article_root.resolve() if args.article_root else None
  selected = set(args.only or ['31', '32'])
  table = args.table4 or base / 'data/publication_sources/Supplementary_Table_4.xlsx'
  if '32' in selected and not table.exists():
    raise FileNotFoundError(table)
  if '31' in selected:
    print('S31 panels', make_s31(base, article_root), flush=True)
  if '32' in selected:
    print('S32 panels', make_s32(base, article_root, table), flush=True)


if __name__ == '__main__':
  main()
