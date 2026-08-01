from __future__ import annotations

"""Deterministic static taxonomy figures from the canonical data matrices."""

from io import BytesIO
from pathlib import Path

import numpy as np

from .taxonomy_final_contract import (
  OTHER_TAXA_THRESHOLD_PERCENT,
  final_domain_rank_matrices,
)


BASE_DIR = Path(__file__).resolve().parents[1]


def _labels(language: str) -> dict[str, str]:
  if str(language).casefold().startswith("pt"):
    return {
      "relative": "Abundância relativa (%)",
      "sample": "Amostra de sedimento classificada por CDS",
      "phylum": "Filo",
      "other": f"Outros táxons (<{OTHER_TAXA_THRESHOLD_PERCENT:g}% cada)",
      "unclassified": "Não classificado",
      "bar_title": "Perfis taxonômicos em nível de filo — amostras individuais",
      "heatmap_title": "Abundância relativa em nível de filo — amostras individuais",
    }
  return {
    "relative": "Relative abundance (%)",
    "sample": "CDS-classified sediment sample",
    "phylum": "Phylum",
    "other": f"Other taxa (<{OTHER_TAXA_THRESHOLD_PERCENT:g}% each)",
    "unclassified": "Unclassified",
    "bar_title": "Phylum-level taxonomic profiles — individual samples",
    "heatmap_title": "Phylum-level relative abundance — individual samples",
  }


def _display_taxon(taxon: object, language: str) -> str:
  labels = _labels(language)
  text = str(taxon)
  if text == "Other taxa":
    return labels["other"]
  if text == "Unclassified" and str(language).casefold().startswith("pt"):
    return labels["unclassified"]
  return text


def _palette(taxa: list[str]) -> dict[str, str]:
  from .article_taxonomy import _article_palette

  palette = _article_palette(taxa, BASE_DIR)
  palette["Other taxa"] = "#9CA3AF"
  palette["Other genera"] = "#9CA3AF"
  palette["Unclassified"] = palette.get("Unclassified", "#D1D5DB")
  return palette


def _configure_svg_text(matplotlib) -> None:
  matplotlib.use("Agg")
  matplotlib.rcParams["svg.fonttype"] = "none"
  matplotlib.rcParams["font.family"] = "DejaVu Sans"


def supplementary_taxonomy_barplot_svg(
  domain: str,
  *,
  language: str = "en",
) -> bytes:
  import matplotlib

  _configure_svg_text(matplotlib)
  import matplotlib.pyplot as plt
  from matplotlib.patches import Patch

  labels = _labels(language)
  _, relative = final_domain_rank_matrices(domain, "Phylum", base_dir=BASE_DIR)
  samples = list(relative.columns)
  taxa = list(relative.index.astype(str))
  palette = _palette(taxa)
  height = max(10.0, 0.48 * len(samples) + 4.2)
  fig, ax = plt.subplots(figsize=(18.5, height))
  y = np.arange(len(samples))
  left = np.zeros(len(samples), dtype=float)
  for taxon in taxa:
    values = relative.loc[taxon, samples].to_numpy(float)
    ax.barh(
      y,
      values,
      left=left,
      color=palette[taxon],
      edgecolor="white",
      linewidth=0.35,
    )
    left += values
  ax.set_yticks(y, samples, fontsize=10)
  ax.invert_yaxis()
  ax.set_xlim(0, 100)
  ax.set_xlabel(labels["relative"], fontsize=13, fontweight="bold")
  ax.set_ylabel(labels["sample"], fontsize=13, fontweight="bold")
  ax.set_title(
    f"{domain} — {labels['bar_title']}",
    fontsize=17,
    fontweight="bold",
    loc="left",
  )
  ax.spines[["top", "right"]].set_visible(False)
  handles = [
    Patch(
      facecolor=palette[taxon],
      edgecolor="none",
      label=_display_taxon(taxon, language),
    )
    for taxon in taxa
  ]
  fig.legend(
    handles=handles,
    title=labels["phylum"],
    loc="lower center",
    bbox_to_anchor=(0.5, 0.012),
    ncol=min(5, max(2, int(np.ceil(len(taxa) / 3)))),
    frameon=False,
    fontsize=9.5,
    title_fontsize=11,
  )
  fig.subplots_adjust(left=0.12, right=0.98, top=0.92, bottom=0.23)
  buffer = BytesIO()
  fig.savefig(buffer, format="svg", facecolor="white", bbox_inches="tight")
  plt.close(fig)
  return buffer.getvalue()


def supplementary_taxonomy_heatmap_svg(
  domain: str,
  *,
  language: str = "en",
) -> bytes:
  import matplotlib

  _configure_svg_text(matplotlib)
  import matplotlib.pyplot as plt

  labels = _labels(language)
  _, relative = final_domain_rank_matrices(domain, "Phylum", base_dir=BASE_DIR)
  matrix = relative.to_numpy(float)
  row_labels = [_display_taxon(taxon, language) for taxon in relative.index]
  col_labels = list(relative.columns)
  width = max(16.0, 0.62 * len(col_labels) + 7.0)
  height = max(7.5, 0.55 * len(row_labels) + 3.4)
  fig, ax = plt.subplots(figsize=(width, height))
  image = ax.imshow(matrix, aspect="auto", interpolation="nearest", cmap="viridis", vmin=0.0)
  ax.set_xticks(np.arange(len(col_labels)), col_labels, rotation=45, ha="right", fontsize=9)
  ax.set_yticks(np.arange(len(row_labels)), row_labels, fontsize=9.5)
  ax.set_xlabel(labels["sample"], fontsize=12, fontweight="bold")
  ax.set_ylabel(labels["phylum"], fontsize=12, fontweight="bold")
  ax.set_title(
    f"{domain} — {labels['heatmap_title']}",
    fontsize=17,
    fontweight="bold",
    loc="left",
  )
  colorbar = fig.colorbar(image, ax=ax, fraction=0.025, pad=0.018)
  colorbar.set_label(labels["relative"], fontsize=11, fontweight="bold")
  fig.subplots_adjust(left=0.22, right=0.95, top=0.90, bottom=0.22)
  buffer = BytesIO()
  fig.savefig(buffer, format="svg", facecolor="white", bbox_inches="tight")
  plt.close(fig)
  return buffer.getvalue()


def supplementary_taxonomy_assets(language: str = "en") -> dict[str, bytes]:
  suffix = "_pt" if str(language).casefold().startswith("pt") else ""
  return {
    f"SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct{suffix}.svg": supplementary_taxonomy_barplot_svg("Bacteria", language=language),
    f"SupplementaryFigure44_Taxonomy_Bacteria_Phylum_individual_samples_heatmap_relative_abundance{suffix}.svg": supplementary_taxonomy_heatmap_svg("Bacteria", language=language),
    f"SupplementaryFigure45_Taxonomy_Archaea_Phylum_individual_samples_barplot_100pct{suffix}.svg": supplementary_taxonomy_barplot_svg("Archaea", language=language),
    f"SupplementaryFigure46_Taxonomy_Archaea_Phylum_individual_samples_heatmap_relative_abundance{suffix}.svg": supplementary_taxonomy_heatmap_svg("Archaea", language=language),
  }
