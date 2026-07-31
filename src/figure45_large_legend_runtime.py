from __future__ import annotations

"""Large, publication-readable legends for article Figures 4 and 5.

The functions in this module only alter presentation geometry. Abundance
values, NMDS coordinates, RDA scores, vectors and statistical results continue
to come from the packaged frozen article inputs used by the canonical Figure
4/5 generator.
"""

from contextlib import contextmanager
from pathlib import Path

import pandas as pd

from .article_figure45_final_generator import (
  _render_static,
  apply_figure45_plotly_layout,
  generate_article_figure45_outputs,
)
from .figure_language_localization import normalize_language


LARGE_LEGEND_CACHE_VERSION = "article_figure45_final_bottom_legends_v2_large"
STATIC_LEGEND_FONT_SIZE = 18.0
STATIC_LEGEND_TITLE_SIZE = 21.0
PLOTLY_LEGEND_FONT_SIZE = 15
PLOTLY_LEGEND_TITLE_SIZE = 18


def _numeric_font_size(value: object, fallback: float) -> float:
  try:
    return float(value)
  except (TypeError, ValueError):
    return float(fallback)


@contextmanager
def large_static_legend_style():
  """Temporarily enlarge Matplotlib figure legends during Figure 4/5 export."""
  from matplotlib.figure import Figure

  original_legend = Figure.legend

  def _large_legend(self, *args, **kwargs):
    options = dict(kwargs)
    options["fontsize"] = max(
      _numeric_font_size(options.get("fontsize"), STATIC_LEGEND_FONT_SIZE),
      STATIC_LEGEND_FONT_SIZE,
    )
    options["title_fontsize"] = max(
      _numeric_font_size(options.get("title_fontsize"), STATIC_LEGEND_TITLE_SIZE),
      STATIC_LEGEND_TITLE_SIZE,
    )
    options["markerscale"] = max(float(options.get("markerscale", 1.0)), 1.45)
    options["labelspacing"] = max(float(options.get("labelspacing", 0.5)), 0.95)
    options["columnspacing"] = max(float(options.get("columnspacing", 1.0)), 1.75)
    options["handletextpad"] = max(float(options.get("handletextpad", 0.5)), 0.72)
    options["borderaxespad"] = max(float(options.get("borderaxespad", 0.5)), 0.75)
    return original_legend(self, *args, **options)

  Figure.legend = _large_legend
  try:
    yield
  finally:
    Figure.legend = original_legend


def apply_figure45_plotly_layout_large(fig, *, language: object = "en"):
  """Apply the canonical layout and enlarge every interactive legend entry."""
  fig = apply_figure45_plotly_layout(fig, language=language)
  if fig is None:
    return fig
  lang = normalize_language(language)
  legend_title = "Gênero" if lang == "pt" else "Genus"
  fig.update_layout(
    height=max(int(getattr(fig.layout, "height", 0) or 0), 2080),
    width=max(int(getattr(fig.layout, "width", 0) or 0), 1820),
    margin={"l": 120, "r": 120, "t": 110, "b": 790},
    legend={
      "title": {
        "text": legend_title,
        "font": {"size": PLOTLY_LEGEND_TITLE_SIZE},
      },
      "orientation": "h",
      "x": 0.5,
      "xanchor": "center",
      "y": -0.245,
      "yanchor": "top",
      "font": {"size": PLOTLY_LEGEND_FONT_SIZE},
      "itemsizing": "constant",
      "tracegroupgap": 10,
      "bgcolor": "rgba(255,255,255,0.99)",
      "bordercolor": "#CBD5E1",
      "borderwidth": 1,
    },
  )
  for annotation in list(fig.layout.annotations or []):
    text = str(getattr(annotation, "text", "") or "").casefold()
    if (
      "nmds symbols:" in text
      or "símbolos do nmds:" in text
      or "rda vectors:" in text
      or "vetores da rda:" in text
    ):
      current_font = getattr(annotation, "font", None)
      current_size = getattr(current_font, "size", None) if current_font else None
      annotation.update(
        font={"size": max(int(current_size or 0), 15)},
        bgcolor="rgba(255,255,255,0.99)",
        bordercolor="#CBD5E1",
        borderwidth=1,
        borderpad=7,
      )
  meta = dict(fig.layout.meta) if isinstance(fig.layout.meta, dict) else {}
  meta.update({
    "legend_font_size": PLOTLY_LEGEND_FONT_SIZE,
    "legend_title_font_size": PLOTLY_LEGEND_TITLE_SIZE,
    "bottom_margin_px": 790,
    "large_legend_layout": True,
    "scientific_values_changed": False,
  })
  fig.update_layout(meta=meta)
  return fig


def materialize_article_figure45_static_large(
  domain: str,
  runtime_root: Path | str,
  language: object = "en",
) -> Path:
  """Generate a new-cache static SVG with larger legends from real inputs."""
  canonical = "Archaea" if str(domain).casefold().startswith("arch") else "Bacteria"
  lang = normalize_language(language)
  target_dir = Path(runtime_root) / LARGE_LEGEND_CACHE_VERSION / lang
  stem = (
    "Figure4_taxonomic_bacteria_genus_profiles"
    if canonical == "Bacteria"
    else "Figure5_taxonomic_archaea_genus_profiles"
  )
  suffix = "_pt" if lang == "pt" else ""
  target = target_dir / f"{stem}{suffix}.svg"
  if not target.exists() or target.stat().st_size <= 10000:
    with large_static_legend_style():
      _render_static(canonical, lang, target)
  return target


def generate_article_figure45_outputs_large(root: Path | str) -> pd.DataFrame:
  """Regenerate SVG, PNG and PDF outputs with enlarged bottom legends."""
  with large_static_legend_style():
    manifest = generate_article_figure45_outputs(root)
  manifest = manifest.copy()
  manifest["legend_font_size_pt"] = STATIC_LEGEND_FONT_SIZE
  manifest["legend_title_font_size_pt"] = STATIC_LEGEND_TITLE_SIZE
  manifest["large_legend_layout"] = True
  manifest["scientific_values_changed"] = False
  root_path = Path(root).resolve()
  manifest_path = root_path / "data" / "final_publication_derived" / "Figure45_final_generation_manifest.csv"
  manifest_path.parent.mkdir(parents=True, exist_ok=True)
  manifest.to_csv(manifest_path, index=False)
  return manifest
