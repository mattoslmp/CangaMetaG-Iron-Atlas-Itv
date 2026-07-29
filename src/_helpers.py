from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import zipfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go

BASE_DIR = Path(__file__).resolve().parents[1]


def empty_frame(columns: list[str] | tuple[str, ...] = ()) -> pd.DataFrame:
  return pd.DataFrame(columns=list(columns))


def read_table(path: Path, sheet_name: str | int | None = None) -> pd.DataFrame:
  try:
    suffix = path.suffix.lower()
    if suffix in {'.xlsx', '.xls'}:
      return pd.read_excel(path, sheet_name=0 if sheet_name is None else sheet_name)
    if suffix in {'.tsv', '.tab'}:
      return pd.read_csv(path, sep='\t')
    if suffix == '.csv':
      return pd.read_csv(path)
  except Exception:
    return pd.DataFrame()
  return pd.DataFrame()


def find_first(patterns: list[str], roots: list[Path] | None = None) -> Path | None:
  roots = roots or [BASE_DIR]
  for root in roots:
    for pattern in patterns:
      try:
        matches = sorted(root.glob(pattern))
      except Exception:
        matches = []
      for match in matches:
        if match.is_file():
          return match
  return None


def numeric_columns(frame: pd.DataFrame, excluded: list[str] | None = None) -> list[str]:
  excluded = set(excluded or [])
  cols: list[str] = []
  for col in frame.columns:
    if str(col) in excluded:
      continue
    series = pd.to_numeric(frame[col], errors='coerce')
    if series.notna().sum() > 0:
      cols.append(str(col))
  return cols


def row_zscore(frame: pd.DataFrame) -> pd.DataFrame:
  if frame is None or frame.empty:
    return pd.DataFrame(index=getattr(frame, 'index', None))
  numeric = frame.apply(pd.to_numeric, errors='coerce').fillna(0.0)
  means = numeric.mean(axis=1)
  stds = numeric.std(axis=1, ddof=0).replace(0, np.nan)
  return numeric.sub(means, axis=0).div(stds, axis=0).fillna(0.0)


def heatmap(matrix: pd.DataFrame, title: str = '', x_title: str = '', y_title: str = '') -> go.Figure:
  """Create a scrollable heatmap with stable, readable cell geometry."""
  if matrix is None or matrix.empty:
    fig = go.Figure()
    fig.add_annotation(text='No data available', x=0.5, y=0.5, showarrow=False)
    fig.update_layout(title=title)
    return fig
  work = matrix.apply(pd.to_numeric, errors='coerce').fillna(0.0)
  n_rows, n_cols = work.shape
  # Slightly larger cells preserve the article-like proportions in the
  # interactive viewport and avoid horizontally/vertically squashed panels.
  cell_w = 42 if n_cols <= 30 else 38 if n_cols <= 60 else 32 if n_cols <= 120 else 28
  cell_h = 34 if n_rows <= 120 else 30 if n_rows <= 240 else 26
  x_values = [str(c) for c in work.columns]
  y_values = [str(i) for i in work.index]
  custom = np.empty((n_rows, n_cols), dtype=object)
  for i, y in enumerate(y_values):
    for j, x in enumerate(x_values):
      custom[i, j] = f'<b>{y}</b><br>{x}'
  fig = go.Figure(data=go.Heatmap(
    z=work.to_numpy(dtype=float),
    x=x_values,
    y=y_values,
    customdata=custom,
    colorscale='Viridis',
    colorbar={'title': 'Value', 'thickness': 18, 'len': 0.8},
    hovertemplate='%{customdata}<br>Value: %{z:.4g}<extra></extra>',
    xgap=0.35,
    ygap=0.35,
  ))
  fig.update_layout(
    title=title,
    xaxis_title=x_title,
    yaxis_title=y_title,
    width=max(1150, min(16000, 620 + cell_w * n_cols)),
    height=max(680, min(26000, 280 + cell_h * n_rows)),
    margin={'l': 500, 'r': 170, 't': 95, 'b': 330},
    font={'family': 'Arial, Helvetica, sans-serif', 'size': 13, 'color': '#111827'},
    meta={
      'preserve_cell_geometry': True,
      'force_all_y_ticks': True,
      'all_y_labels_visible': True,
      'cell_width_px': cell_w,
      'cell_height_px': cell_h,
    },
  )
  fig.update_xaxes(tickangle=-55, tickfont={'size': 11}, automargin=True)
  fig.update_yaxes(tickfont={'size': 11}, automargin=True, tickmode='array', tickvals=y_values, ticktext=y_values)
  return fig


def zip_directory(path: Path) -> bytes:
  buffer = BytesIO()
  with zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
    if path.exists():
      for file_path in sorted(path.rglob('*')):
        if file_path.is_file():
          archive.write(file_path, file_path.relative_to(path.parent))
  return buffer.getvalue()


def canonical_mag(value: object) -> str:
  text = str(value or '').strip()
  match = re.search(r'(?:MAG|bin[._-]?)(\d+)', text, flags=re.I)
  if match:
    return f'MAG{int(match.group(1))}'
  digits = re.search(r'\d+', text)
  if digits:
    return f'MAG{int(digits.group(0))}'
  return text or 'MAG'
