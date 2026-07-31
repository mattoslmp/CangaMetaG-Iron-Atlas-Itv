from __future__ import annotations

"""Exact article Figure 2/3 assets and source tables for the Streamlit app.

The interactive viewer embeds the same corrected SVG used by the static article
figure. It therefore does not redraw, aggregate, reorder or recompute any
scientific value. The packaged source CSV remains available for audit/download.
"""

import base64
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .article_taxonomy import SAMPLE_ORDER, _article_palette
from .corrected_taxonomy_static_assets import corrected_taxonomy_static_bytes


BASE_DIR = Path(__file__).resolve().parents[1]
AUTHORITY = "ARTICLE_FINAL_ISME_SUBMISSION_Leandrov27-julho FINAL_SUBMISSION_FILES"

FIGURES = {
  "Bacteria": {
    "stem": "Figure2_taxonomic_phylum_bacteria_horizontal_CDS",
    "title": "Bacteria phylum-level taxonomic profiles",
  },
  "Archaea": {
    "stem": "Figure3_taxonomic_phylum_archaea_horizontal_CDS",
    "title": "Archaea phylum-level taxonomic profiles",
  },
}


def _domain(domain: str) -> str:
  return "Archaea" if str(domain).casefold().startswith("arch") else "Bacteria"


def _source_path(domain: str) -> Path:
  canonical = _domain(domain)
  return (
    BASE_DIR
    / "data"
    / "final_publication_derived"
    / f"{FIGURES[canonical]['stem']}_source.csv"
  )


@lru_cache(maxsize=2)
def load_exact_article_phylum_table(domain: str) -> pd.DataFrame:
  """Load and validate the exact corrected source matrix used by Figure 2/3."""
  canonical = _domain(domain)
  path = _source_path(canonical)
  frame = pd.read_csv(path, keep_default_na=False)
  if frame.empty or "taxon" not in frame.columns:
    raise RuntimeError(f"Invalid frozen article taxonomy source: {path}")
  expected_samples = [sample for sample in SAMPLE_ORDER if sample in frame.columns]
  if not expected_samples:
    raise RuntimeError(f"No article sample columns were found in {path}")
  numeric = frame[expected_samples].apply(pd.to_numeric, errors="raise")
  if not np.isfinite(numeric.to_numpy(float)).all():
    raise RuntimeError(f"Non-finite abundance value found in {path}")
  totals = numeric.sum(axis=0).to_numpy(float)
  if not np.allclose(totals, 100.0, atol=1e-8, rtol=0.0):
    raise RuntimeError(
      f"Frozen Figure 2/3 source columns do not total 100%: {path}"
    )
  output = frame.copy()
  output[expected_samples] = numeric
  output.attrs.update({
    "authority": AUTHORITY,
    "domain": canonical,
    "source_path": str(path.relative_to(BASE_DIR)),
    "recomputed": False,
  })
  return output


def _valid_svg(payload: bytes | None) -> bool:
  return bool(payload and b"<svg" in payload[:8192].lstrip().lower())


def _generate_article_svg(domain: str) -> bytes:
  """Fallback using the exact phylum_figure layout from the canonical script."""
  import matplotlib
  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  from matplotlib.patches import Patch

  canonical = _domain(domain)
  source = load_exact_article_phylum_table(canonical)
  samples = [sample for sample in SAMPLE_ORDER if sample in source.columns]
  rel = source.set_index("taxon")[samples].copy()
  taxa = [str(value) for value in rel.index]
  palette = _article_palette(taxa, BASE_DIR)

  fig, axes = plt.subplots(1, 2, figsize=(17.5, 8.8), sharex=True)
  for ax, suffix, panel, label in zip(
    axes,
    ["D", "R"],
    ["A", "B"],
    ["Dry season", "Rainy season"],
  ):
    panel_samples = [
      sample for sample in SAMPLE_ORDER
      if sample.endswith(f".{suffix}") and sample in rel.columns
    ]
    y = np.arange(len(panel_samples))
    left = np.zeros(len(panel_samples), dtype=float)
    for taxon in taxa:
      values = rel.loc[taxon, panel_samples].to_numpy(float)
      ax.barh(
        y,
        values,
        left=left,
        color=palette[taxon],
        edgecolor="white",
        linewidth=0.25,
      )
      left += values
    ax.set_yticks(y, panel_samples, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Relative abundance (%)", fontsize=12, fontweight="bold")
    ax.set_title(f"{panel}  {label}", loc="left", fontsize=14, fontweight="bold")
    ax.tick_params(axis="both", labelsize=10)
    ax.grid(False)
  axes[0].set_ylabel(
    "CDS-classified sediment sample",
    fontsize=12,
    fontweight="bold",
  )
  handles = [
    Patch(facecolor=palette[taxon], edgecolor="none", label=taxon)
    for taxon in taxa
  ]
  fig.legend(
    handles=handles,
    title="Phylum",
    loc="center left",
    bbox_to_anchor=(0.82, 0.5),
    frameon=False,
    fontsize=9,
    title_fontsize=10,
  )
  fig.suptitle(
    str(FIGURES[canonical]["title"]),
    fontsize=18,
    fontweight="bold",
    y=0.985,
  )
  fig.subplots_adjust(
    left=0.09,
    right=0.80,
    bottom=0.10,
    top=0.90,
    wspace=0.28,
  )
  buffer = BytesIO()
  fig.savefig(buffer, format="svg", bbox_inches="tight", facecolor="white")
  plt.close(fig)
  payload = buffer.getvalue()
  if not _valid_svg(payload):
    raise RuntimeError(f"Could not generate valid exact article SVG for {canonical}")
  return payload


@lru_cache(maxsize=2)
def exact_article_phylum_svg_bytes(domain: str) -> bytes:
  canonical = _domain(domain)
  filename = f"{FIGURES[canonical]['stem']}.svg"
  payload = corrected_taxonomy_static_bytes(filename)
  if _valid_svg(payload):
    return bytes(payload)
  return _generate_article_svg(canonical)


def materialize_exact_article_phylum_static(
  domain: str,
  runtime_root: Path | str,
) -> Path:
  canonical = _domain(domain)
  output_dir = Path(runtime_root) / "exact_article_taxonomy_phylum"
  output_dir.mkdir(parents=True, exist_ok=True)
  output = output_dir / f"{FIGURES[canonical]['stem']}.svg"
  payload = exact_article_phylum_svg_bytes(canonical)
  if not output.exists() or output.read_bytes() != payload:
    output.write_bytes(payload)
  return output


def _svg_aspect_ratio(payload: bytes) -> float:
  text = payload[:20000].decode("utf-8", errors="ignore")
  viewbox = re.search(
    r"viewBox\s*=\s*[\"']\s*[-+0-9.eE]+\s+[-+0-9.eE]+\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)",
    text,
    flags=re.IGNORECASE,
  )
  if viewbox:
    width, height = float(viewbox.group(1)), float(viewbox.group(2))
    if width > 0 and height > 0:
      return width / height
  width_match = re.search(r"width\s*=\s*[\"']([0-9.]+)", text, flags=re.IGNORECASE)
  height_match = re.search(r"height\s*=\s*[\"']([0-9.]+)", text, flags=re.IGNORECASE)
  if width_match and height_match:
    width, height = float(width_match.group(1)), float(height_match.group(1))
    if width > 0 and height > 0:
      return width / height
  return 17.5 / 8.8


def exact_article_phylum_interactive(
  domain: str,
) -> tuple[go.Figure, pd.DataFrame, bytes]:
  """Embed the exact static SVG in a zoomable/pannable Plotly viewer."""
  canonical = _domain(domain)
  table = load_exact_article_phylum_table(canonical).copy()
  svg = exact_article_phylum_svg_bytes(canonical)
  encoded = base64.b64encode(svg).decode("ascii")
  ratio = _svg_aspect_ratio(svg)
  width = 1650
  height = max(650, int(round(width / max(ratio, 0.2))))

  figure = go.Figure()
  figure.add_layout_image(
    source=f"data:image/svg+xml;base64,{encoded}",
    xref="x",
    yref="y",
    x=0,
    y=1,
    sizex=1,
    sizey=1,
    sizing="contain",
    opacity=1,
    layer="below",
  )
  # Transparent anchors keep Plotly zoom/pan active without redrawing the data.
  figure.add_trace(go.Scatter(
    x=[0, 1],
    y=[0, 1],
    mode="markers",
    marker={"opacity": 0, "size": 1},
    hoverinfo="skip",
    showlegend=False,
    name="Exact article figure",
  ))
  figure.update_xaxes(range=[0, 1], visible=False, fixedrange=False)
  figure.update_yaxes(
    range=[0, 1],
    visible=False,
    fixedrange=False,
    scaleanchor="x",
    scaleratio=1,
  )
  figure.update_layout(
    width=width,
    height=height,
    autosize=True,
    dragmode="pan",
    margin={"l": 0, "r": 0, "t": 0, "b": 0},
    paper_bgcolor="white",
    plot_bgcolor="white",
    meta={
      "authority": AUTHORITY,
      "domain": canonical,
      "article_figure": "Figure 2" if canonical == "Bacteria" else "Figure 3",
      "static_and_interactive_same_svg": True,
      "allow_taxonomy_missing_literals": True,
      "recomputed": False,
      "source_table": table.attrs.get("source_path", ""),
    },
  )
  return figure, table, svg
