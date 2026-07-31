from __future__ import annotations

"""Figure 2/3 source that always regenerates the corrected article SVG.

The module invokes the canonical Matplotlib layout against the frozen corrected
source CSV. Aggregate taxonomy labels include the exact mean percentage shown
by the figure, while all source values and bar lengths remain unchanged.
"""

import base64
from functools import lru_cache
from pathlib import Path

import plotly.graph_objects as go

from .article_exact_taxonomy_phylum import (
  AUTHORITY,
  FIGURES,
  _domain,
  _svg_aspect_ratio,
  load_exact_article_phylum_table,
)
from .article_exact_taxonomy_phylum_other_percentage import (
  generate_article_svg_with_other_percentage,
  other_taxa_percentages,
)


CACHE_VERSION = "exact_article_taxonomy_phylum_generated_other_percentage_v2"


@lru_cache(maxsize=2)
def exact_article_phylum_svg_bytes(domain: str) -> bytes:
  """Generate the corrected SVG with the exact Other taxa percentage."""
  return generate_article_svg_with_other_percentage(_domain(domain))


def materialize_exact_article_phylum_static(
  domain: str,
  runtime_root: Path | str,
) -> Path:
  canonical = _domain(domain)
  output_dir = Path(runtime_root) / CACHE_VERSION
  output_dir.mkdir(parents=True, exist_ok=True)
  output = output_dir / f"{FIGURES[canonical]['stem']}.svg"
  payload = exact_article_phylum_svg_bytes(canonical)
  if not output.exists() or output.read_bytes() != payload:
    output.write_bytes(payload)
  return output


def exact_article_phylum_interactive(domain: str):
  """Show the generated article SVG unchanged in a zoomable Plotly viewer."""
  canonical = _domain(domain)
  table = load_exact_article_phylum_table(canonical).copy()
  percentages = other_taxa_percentages(canonical)
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
  figure.update_yaxes(range=[0, 1], visible=False, fixedrange=False)
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
      "generated_from_corrected_frozen_table": True,
      "allow_taxonomy_missing_literals": True,
      "recomputed": False,
      "source_table": table.attrs.get("source_path", ""),
      "canonical_script": "scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py",
      "other_taxa_mean_percent": percentages["overall"],
      "other_taxa_dry_mean_percent": percentages["dry"],
      "other_taxa_rainy_mean_percent": percentages["rainy"],
      "other_taxa_label_rule": "mean relative abundance across displayed samples",
    },
  )
  return figure, table, svg
