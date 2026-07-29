from __future__ import annotations

import math
import textwrap
import numpy as np
import pandas as pd


def adaptive_heatmap_geometry(n_rows: int, n_cols: int, cell_px: int = 28,
                              min_cell_px: int = 20, max_cell_px: int = 34,
                              left_margin: int = 260, bottom_margin: int = 220):
  cell = max(min_cell_px, min(max_cell_px, cell_px))
  width = max(700, left_margin + n_cols * cell + 100)
  height = max(500, n_rows * cell + bottom_margin + 100)
  return {
    'width': int(min(width, 16000)),
    'height': int(min(height, 30000)),
    'margin': {'l': int(left_margin), 'r': 70, 't': 90, 'b': int(bottom_margin)},
  }


def compact_heatmap_colorbars(fig, length=None, thickness=12, top=None):
  try:
    for trace in fig.data:
      if hasattr(trace, 'colorbar'):
        trace.colorbar.thickness = thickness
        if length is not None:
          trace.colorbar.len = length
        if top is not None:
          trace.colorbar.y = top
  except Exception:
    pass
  return fig


def polish_heatmap_layout(fig, min_column_px=22.0, title_chars=54):
  try:
    n_cols = max((len(getattr(trace, 'x', []) or []) for trace in fig.data), default=0)
    current = getattr(fig.layout, 'width', None) or 800
    fig.update_layout(width=max(current, int(260 + n_cols * min_column_px)))
    title = getattr(getattr(fig.layout, 'title', None), 'text', '') or ''
    if title:
      fig.update_layout(title='\n'.join(textwrap.wrap(title, width=title_chars)))
  except Exception:
    pass
  return fig


def sparsify_heatmap_y_ticks(fig, min_label_gap_px=16.0, max_visible_ticks=90):
  """Preserve every heatmap row label unless sparsification is explicitly requested.

  Publication and full-matrix views must never silently remove taxon, KO or
  module names. Dense matrices are rendered in a scrollable viewport with a
  fixed cell height. Exploratory callers may opt into sparse ticks only by
  setting ``layout.meta["allow_sparse_y_ticks"] = True``.
  """
  try:
    heatmap = next(
      (trace for trace in fig.data if str(getattr(trace, "type", "")).lower() in {"heatmap", "image"}),
      None,
    )
    labels = [str(value) for value in list(getattr(heatmap, "y", []) or [])] if heatmap is not None else []
    if not labels:
      return fig
    meta = getattr(fig.layout, "meta", None)
    meta = dict(meta) if isinstance(meta, dict) else {}
    allow_sparse = bool(meta.get("allow_sparse_y_ticks", False))
    if allow_sparse and len(labels) > max_visible_ticks:
      step = math.ceil(len(labels) / max_visible_ticks)
      visible = [label if i % step == 0 else "" for i, label in enumerate(labels)]
      fig.update_yaxes(tickmode="array", tickvals=labels, ticktext=visible, automargin=True)
      return fig

    tickfont_size = int(meta.get("y_tick_font_size", 10 if len(labels) > 250 else 11) or 11)
    cell_height = int(meta.get("cell_height_px", 20 if len(labels) > 300 else 24) or 24)
    meta.update({
      "preserve_cell_geometry": True,
      "force_all_y_ticks": True,
      "all_y_labels_visible": True,
      "cell_height_px": cell_height,
    })
    top = int(getattr(fig.layout.margin, "t", 80) or 80)
    bottom = int(getattr(fig.layout.margin, "b", 180) or 180)
    required_height = top + bottom + max(1, len(labels)) * cell_height + 80
    current_height = int(getattr(fig.layout, "height", 0) or 0)
    fig.update_layout(meta=meta, height=min(30000, max(current_height, required_height)))
    fig.update_yaxes(
      tickmode="array",
      tickvals=labels,
      ticktext=labels,
      tickfont={"size": tickfont_size},
      automargin=True,
    )
  except Exception:
    return fig
  return fig


def repel_label_positions(frame: pd.DataFrame, x_col: str, y_col: str,
                          min_distance: float = 0.2, radial_offset: float = 0.24) -> pd.DataFrame:
  """Add deterministic ``label_x``/``label_y`` columns without moving endpoints."""
  if frame is None or frame.empty or x_col not in frame or y_col not in frame:
    out = frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame()
    if isinstance(out, pd.DataFrame):
      out["label_x"] = pd.Series(dtype=float)
      out["label_y"] = pd.Series(dtype=float)
    return out
  out = frame.copy()
  xs = pd.to_numeric(out[x_col], errors="coerce").fillna(0.0).to_numpy(float)
  ys = pd.to_numeric(out[y_col], errors="coerce").fillna(0.0).to_numpy(float)
  label_x = xs.copy()
  label_y = ys.copy()
  for i in range(len(label_x)):
    for j in range(i):
      dx, dy = label_x[i] - label_x[j], label_y[i] - label_y[j]
      dist = float(np.hypot(dx, dy))
      if dist < min_distance:
        angle = (i + 1) * 2.399963229728653
        label_x[i] += radial_offset * np.cos(angle)
        label_y[i] += radial_offset * np.sin(angle)
  out["label_x"] = label_x
  out["label_y"] = label_y
  return out


def compact_significance_summary(frame: pd.DataFrame, max_items: int = 8) -> str:
  if frame is None or frame.empty:
    return 'No significant results available.'
  pcols = [c for c in frame.columns if str(c).lower() in {'p', 'pvalue', 'p_value', 'padj', 'qvalue', 'q_value'} or 'p-value' in str(c).lower()]
  work = frame.copy()
  if pcols:
    work[pcols[0]] = pd.to_numeric(work[pcols[0]], errors='coerce')
    work = work.sort_values(pcols[0], na_position='last')
  label_cols = [c for c in work.columns if str(c).lower() in {'taxon', 'feature', 'ko', 'pathway', 'group', 'comparison'}]
  label = label_cols[0] if label_cols else work.columns[0]
  values = work[label].astype(str).head(max_items).tolist()
  return '; '.join(values) if values else 'No significant results available.'
