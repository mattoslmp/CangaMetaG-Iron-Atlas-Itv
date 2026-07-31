from __future__ import annotations

"""Generate Figures 2/3 with the declared 5% aggregate cutoff.

``Other taxa`` is an aggregate category. Its bar length is the sum of the
underlying source-table values, whereas the value written in the legend denotes
the per-taxon cutoff used to describe that aggregate. The source values and bar
lengths are never replaced by 5%.
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
) -> str:
  """Label aggregate taxa with the 5% per-taxon cutoff."""
  name = str(taxon)
  if name not in AGGREGATE_LABELS:
    return name
  threshold = f"{OTHER_TAXA_THRESHOLD_PERCENT:g}%"
  return f"{name} (<{threshold} each)"


def generate_article_svg_with_other_percentage(domain: str) -> bytes:
  """Regenerate the canonical Figure 2/3 SVG with the 5% cutoff label."""
  import matplotlib

  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  from matplotlib.patches import Patch

  canonical = _domain(domain)
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
    ["Dry season", "Rainy season"],
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
    axis.set_xlabel("Relative abundance (%)", fontsize=12, fontweight="bold")
    axis.set_title(
      f"{panel}  {season_label}",
      loc="left",
      fontsize=14,
      fontweight="bold",
    )
    axis.tick_params(axis="both", labelsize=10)
    axis.grid(False)

  axes[0].set_ylabel(
    "CDS-classified sediment sample",
    fontsize=12,
    fontweight="bold",
  )
  handles = [
    Patch(
      facecolor=palette[taxon],
      edgecolor="none",
      label=aggregate_taxon_display_label(taxon),
    )
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
    raise RuntimeError(
      f"Could not generate valid exact article SVG for {canonical}"
    )
  return payload
