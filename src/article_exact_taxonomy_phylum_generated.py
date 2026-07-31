from __future__ import annotations

"""Bilingual Figure 2/3 assets generated from the same corrected source table."""

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
  OTHER_TAXA_THRESHOLD_PERCENT,
  aggregate_taxon_display_label,
  generate_article_svg_with_other_percentage,
)
from .figure_language_localization import normalize_language


CACHE_VERSION = "exact_article_taxonomy_phylum_generated_bilingual_v4"


@lru_cache(maxsize=4)
def exact_article_phylum_svg_bytes(
  domain: str,
  language: object = "en",
) -> bytes:
  """Generate the same Figure 2/3 values with localized presentation text."""
  canonical = _domain(domain)
  lang = normalize_language(language)
  return generate_article_svg_with_other_percentage(canonical, language=lang)


def materialize_exact_article_phylum_static(
  domain: str,
  runtime_root: Path | str,
  language: object = "en",
) -> Path:
  canonical = _domain(domain)
  lang = normalize_language(language)
  output_dir = Path(runtime_root) / CACHE_VERSION / lang
  output_dir.mkdir(parents=True, exist_ok=True)
  suffix = "_pt" if lang == "pt" else ""
  output = output_dir / f"{FIGURES[canonical]['stem']}{suffix}.svg"
  payload = exact_article_phylum_svg_bytes(canonical, lang)
  if not output.exists() or output.read_bytes() != payload:
    output.write_bytes(payload)
  return output


def exact_article_phylum_interactive(
  domain: str,
  language: object = "en",
):
  """Show the language-matched SVG in a zoomable Plotly viewer."""
  canonical = _domain(domain)
  lang = normalize_language(language)
  table = load_exact_article_phylum_table(canonical).copy()
  svg = exact_article_phylum_svg_bytes(canonical, lang)
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
    name="Figura exata do artigo" if lang == "pt" else "Exact article figure",
  ))
  figure.update_xaxes(range=[0, 1], visible=False, fixedrange=False)
  figure.update_yaxes(range=[0, 1], visible=False, fixedrange=False)
  localized_aggregate = aggregate_taxon_display_label(
    "Other taxa",
    language=lang,
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
      "article_figure": (
        ("Figura 2" if canonical == "Bacteria" else "Figura 3")
        if lang == "pt"
        else ("Figure 2" if canonical == "Bacteria" else "Figure 3")
      ),
      "display_language": lang,
      "static_and_interactive_same_svg": True,
      "generated_from_corrected_frozen_table": True,
      "allow_taxonomy_missing_literals": True,
      "recomputed": False,
      "source_table": table.attrs.get("source_path", ""),
      "canonical_script": "scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py",
      "other_taxa_threshold_percent": OTHER_TAXA_THRESHOLD_PERCENT,
      "other_taxa_label": localized_aggregate,
      "other_taxa_label_meaning": (
        "5% indica o corte por táxon; as barras agregadas preservam a soma exata da tabela-fonte"
        if lang == "pt"
        else "5% is the per-taxon cutoff; aggregate bar values preserve the exact source-table sum"
      ),
    },
  )
  return figure, table, svg
