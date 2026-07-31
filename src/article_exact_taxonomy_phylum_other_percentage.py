from __future__ import annotations

"""Generate bilingual Figures 2/3 with the declared 5% aggregate cutoff.

``Other taxa`` is an aggregate category. Its bar length is the sum of the
underlying source-table values, whereas the value written in the legend denotes
the per-taxon cutoff used to describe that aggregate. Language changes display
text only; source values and bar lengths are never changed.
"""

from io import BytesIO

import numpy as np

from .article_exact_taxonomy_phylum import (
  BASE_DIR,
  FIGURES,
  _domain,
  _valid_svg,
  load_exact_article_phylum_table,
)
from .article_taxonomy import SAMPLE_ORDER, _article_palette
from .figure_language_localization import normalize_language


AGGREGATE_LABELS = {"Other taxa", "Other genera"}
OTHER_TAXA_THRESHOLD_PERCENT = 5.0


def other_taxa_percentages(domain: str) -> dict[str, float]:
  """Return diagnostic aggregate means without using them in the legend."""
  canonical = _domain(domain)
  source = load_exact_article_phylum_table(canonical)
  samples = [sample for sample in SAMPLE_ORDER if sample in source.columns]
  relative = source.set_index("taxon")[samples]
  aggregate = next(
    (label for label in relative.index.astype(str) if label in AGGREGATE_LABELS),
    "",
  )
  if not aggregate:
    return {"overall": 0.0, "dry": 0.0, "rainy": 0.0}
  values = relative.loc[aggregate].astype(float)
  dry = [sample for sample in samples if sample.endswith(".D")]
  rainy = [sample for sample in samples if sample.endswith(".R")]
  return {
    "overall": float(values.mean()),
    "dry": float(values[dry].mean()) if dry else 0.0,
    "rainy": float(values[rainy].mean()) if rainy else 0.0,
  }


def aggregate_taxon_display_label(
  taxon: object,
  values: object | None = None,
  *,
  language: object = "en",
) -> str:
  """Label aggregate taxa with the 5% per-taxon cutoff."""
  name = str(taxon)
  if name not in AGGREGATE_LABELS:
    return name
  threshold = f"{OTHER_TAXA_THRESHOLD_PERCENT:g}%"
  if normalize_language(language) == "pt":
    base = "Outros gêneros" if name == "Other genera" else "Outros táxons"
    return f"{base} (<{threshold} cada)"
  return f"{name} (<{threshold} each)"


def _labels(domain: str, language: object) -> dict[str, str]:
  canonical = _domain(domain)
  if normalize_language(language) == "pt":
    return {
      "dry": "Estação seca",
      "rainy": "Estação chuvosa",
      "x": "Abundância relativa (%)",
      "y": "Amostra de sedimento classificada por CDS",
      "legend": "Filo",
      "title": (
        "Perfis taxonômicos de Bacteria em nível de filo"
        if canonical == "Bacteria"
        else "Perfis taxonômicos de Archaea em nível de filo"
      ),
    }
  return {
    "dry": "Dry season",
    "rainy": "Rainy season",
    "x": "Relative abundance (%)",
    "y": "CDS-classified sediment sample",
    "legend": "Phylum",
    "title": str(FIGURES[canonical]["title"]),
  }


def generate_article_svg_with_other_percentage(
  domain: str,
  language: object = "en",
) -> bytes:
  """Regenerate the canonical Figure 2/3 SVG in the selected language."""
  import matplotlib

  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  from matplotlib.patches import Patch

  lang = normalize_language(language)
  canonical = _domain(domain)
  labels = _labels(canonical, lang)
  source = load_exact_article_phylum_table(canonical)
  samples = [sample for sample in SAMPLE_ORDER if sample in source.columns]
  relative = source.set_index("taxon")[samples].copy()
  taxa = [str(value) for value in relative.index]
  palette = _article_palette(taxa, BASE_DIR)

  fig, axes = plt.subplots(1, 2, figsize=(17.5, 8.8), sharex=True)
  for axis, suffix, panel, season_label in zip(
    axes,
    ["D", "R"],
    ["A", "B"],
    [labels["dry"], labels["rainy"]],
  ):
    panel_samples = [
      sample for sample in SAMPLE_ORDER
      if sample.endswith(f".{suffix}") and sample in relative.columns
    ]
    y = np.arange(len(panel_samples))
    left = np.zeros(len(panel_samples), dtype=float)
    for taxon in taxa:
      values = relative.loc[taxon, panel_samples].to_numpy(float)
      axis.barh(
        y,
        values,
        left=left,
        color=palette[taxon],
        edgecolor="white",
        linewidth=0.25,
      )
      left += values
    axis.set_yticks(y, panel_samples, fontsize=10)
    axis.invert_yaxis()
    axis.set_xlim(0, 100)
    axis.set_xlabel(labels["x"], fontsize=12, fontweight="bold")
    axis.set_title(
      f"{panel}  {season_label}",
      loc="left",
      fontsize=14,
      fontweight="bold",
    )
    axis.tick_params(axis="both", labelsize=10)
    axis.grid(False)

  axes[0].set_ylabel(
    labels["y"],
    fontsize=12,
    fontweight="bold",
  )
  handles = [
    Patch(
      facecolor=palette[taxon],
      edgecolor="none",
      label=aggregate_taxon_display_label(taxon, language=lang),
    )
    for taxon in taxa
  ]
  fig.legend(
    handles=handles,
    title=labels["legend"],
    loc="center left",
    bbox_to_anchor=(0.82, 0.5),
    frameon=False,
    fontsize=9,
    title_fontsize=10,
  )
  fig.suptitle(
    labels["title"],
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
    raise RuntimeError(
      f"Could not generate valid exact article SVG for {canonical}"
    )
  return payload
