from __future__ import annotations

"""Final data-driven generator for article Figures 4 and 5.

The generator reads the frozen article input JSON files through
``frozen_taxonomy_domain_data``. It does not recompute abundance, NMDS or RDA
values. The only changes are presentation geometry and export formatting.
Every legend is placed in a dedicated band below the four scientific panels.
"""

from pathlib import Path
import json
import math
import shutil

import numpy as np
import pandas as pd

from .article_frozen_taxonomy_panels import (
  LAKE_COLORS,
  frozen_taxonomy_domain_data,
)
from .figure_language_localization import normalize_language


CACHE_VERSION = "article_figure45_final_bottom_legends_v1"


def _labels(domain: str, language: object) -> dict[str, str]:
  lang = normalize_language(language)
  if lang == "pt":
    return {
      "dry_profile": "Perfis de gêneros — estação seca",
      "rainy_profile": "Perfis de gêneros — estação chuvosa",
      "relative": "Abundância relativa (%)",
      "nmds": "NMDS de Bray–Curtis",
      "rda": "Biplot de RDA",
      "constrained": "variação restrita",
      "lake_season": "Lagoa / estação",
      "dry": "Seca",
      "rainy": "Chuvosa",
      "rda_vectors": "Vetores da RDA",
      "environment": "Variável ambiental",
      "genus_vector": "Vetor de gênero representativo",
      "genus": "Gênero",
      "title": (
        "Perfis taxonômicos de Bacteria em nível de gênero e ordenação"
        if domain == "Bacteria"
        else "Perfis taxonômicos de Archaea em nível de gênero e ordenação"
      ),
    }
  return {
    "dry_profile": "Dry-season genus profiles",
    "rainy_profile": "Rainy-season genus profiles",
    "relative": "Relative abundance (%)",
    "nmds": "Bray-Curtis NMDS",
    "rda": "RDA biplot",
    "constrained": "constrained variation",
    "lake_season": "Lake / season",
    "dry": "Dry",
    "rainy": "Rainy",
    "rda_vectors": "RDA vectors",
    "environment": "Environmental variable",
    "genus_vector": "Representative genus vector",
    "genus": "Genus",
    "title": f"{domain} genus-level taxonomic profiles and ordination",
  }


def apply_figure45_plotly_layout(fig, *, language: object = "en"):
  """Place Plotly legends below Figure 4/5 without changing trace values."""
  if fig is None:
    return fig
  lang = normalize_language(language)
  legend_title = "Gênero" if lang == "pt" else "Genus"
  fig.update_layout(
    height=max(int(getattr(fig.layout, "height", 0) or 0), 1900),
    width=max(int(getattr(fig.layout, "width", 0) or 0), 1750),
    margin={"l": 115, "r": 110, "t": 105, "b": 690},
    legend={
      "title": {"text": legend_title},
      "orientation": "h",
      "x": 0.5,
      "xanchor": "center",
      "y": -0.285,
      "yanchor": "top",
      "font": {"size": 11},
      "itemsizing": "constant",
      "tracegroupgap": 5,
      "bgcolor": "rgba(255,255,255,0.98)",
      "bordercolor": "#D1D5DB",
      "borderwidth": 1,
    },
  )
  for annotation in list(fig.layout.annotations or []):
    text = str(getattr(annotation, "text", "") or "").casefold()
    if "nmds symbols:" in text or "símbolos do nmds:" in text:
      annotation.update(
        x=0.04,
        y=-0.105,
        xref="paper",
        yref="paper",
        xanchor="left",
        yanchor="top",
      )
    elif "rda vectors:" in text or "vetores da rda:" in text:
      annotation.update(
        x=0.96,
        y=-0.105,
        xref="paper",
        yref="paper",
        xanchor="right",
        yanchor="top",
      )
  meta = dict(fig.layout.meta) if isinstance(fig.layout.meta, dict) else {}
  meta.update({
    "legend_layout": "dedicated-band-below-entire-figure",
    "legend_below_entire_figure": True,
    "legend_overlaps_scientific_panels": False,
    "preserve_legend_position": True,
    "bottom_margin_px": 690,
    "scientific_values_changed": False,
  })
  fig.update_layout(meta=meta)
  return fig


def _render_static(
  domain: str,
  language: object,
  svg_path: Path,
  png_path: Path | None = None,
  pdf_path: Path | None = None,
) -> dict[str, object]:
  import matplotlib

  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  from matplotlib.lines import Line2D
  from matplotlib.patches import Patch

  data = frozen_taxonomy_domain_data(domain)
  canonical = str(data["domain"])
  labels = _labels(canonical, language)
  profile = data["profile"].set_index("taxon")
  scores = data["nmds"]
  sites = data["rda_sites"].set_index("Sample")
  env = data["rda_environment_vectors"].set_index("Variable")
  taxa = data["rda_taxon_vectors"].set_index("Genus")
  stats = data["statistics"].iloc[0]
  display = data["display"]
  palette = data["palette"]

  samples = list(profile.columns)
  dry = [sample for sample in samples if sample.endswith(".D")]
  rainy = [sample for sample in samples if sample.endswith(".R")]

  def stacked(ax, selected_samples: list[str], panel: str, title: str) -> None:
    y = np.arange(len(selected_samples))
    left = np.zeros(len(selected_samples), dtype=float)
    for taxon in profile.index:
      values = profile.loc[taxon, selected_samples].to_numpy(float)
      ax.barh(
        y,
        values,
        left=left,
        color=palette.get(str(taxon), "#666666"),
        edgecolor="white",
        linewidth=0.35,
      )
      left += values
    ax.set_yticks(y)
    ax.set_yticklabels(selected_samples, fontsize=15)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel(labels["relative"], fontsize=20, fontweight="bold", labelpad=8)
    ax.tick_params(axis="x", labelsize=14, pad=5)
    ax.set_title(f"{panel}  {title}", loc="left", fontsize=20, fontweight="bold", pad=10)
    ax.spines[["top", "right"]].set_visible(False)

  fig = plt.figure(figsize=(29, 29))
  grid = fig.add_gridspec(
    2,
    2,
    height_ratios=[1.05, 1.0],
    hspace=0.34,
    wspace=0.32,
  )
  ax_a = fig.add_subplot(grid[0, 0])
  ax_b = fig.add_subplot(grid[0, 1])
  ax_c = fig.add_subplot(grid[1, 0])
  ax_d = fig.add_subplot(grid[1, 1])

  stacked(ax_a, dry, "A", labels["dry_profile"])
  stacked(ax_b, rainy, "B", labels["rainy_profile"])

  for lake in ["AM", "TIA", "TI", "VI"]:
    for season in ["Dry", "Rainy"]:
      subset = scores[(scores["Lake"] == lake) & (scores["Season"] == season)]
      ax_c.scatter(
        subset["NMDS1"],
        subset["NMDS2"],
        s=105,
        color=LAKE_COLORS[lake],
        marker="o" if season == "Dry" else "s",
        edgecolor="black",
        linewidth=0.8,
        zorder=3,
      )
      for _, row in subset.iterrows():
        ax_c.annotate(
          str(row["Sample"]),
          (float(row["NMDS1"]), float(row["NMDS2"])),
          xytext=(6, 6),
          textcoords="offset points",
          fontsize=14.5,
          fontweight="bold",
          annotation_clip=False,
        )
  ax_c.axhline(0, color="#AAAAAA", lw=0.8)
  ax_c.axvline(0, color="#AAAAAA", lw=0.8)
  ax_c.set_xlabel("NMDS1", fontsize=17, fontweight="bold")
  ax_c.set_ylabel("NMDS2", fontsize=17, fontweight="bold")
  ax_c.tick_params(labelsize=15)
  ax_c.set_title(
    f"C  {labels['nmds']} (stress = {float(stats['NMDS_stress']):.3f})",
    loc="left",
    fontsize=20,
    fontweight="bold",
    pad=10,
  )
  ax_c.margins(x=0.20, y=0.20)

  for lake, subset in sites.groupby("Lake"):
    ax_d.scatter(
      subset["RDA1"],
      subset["RDA2"],
      s=120,
      color=LAKE_COLORS.get(str(lake), "#777777"),
      edgecolor="black",
      linewidth=0.8,
      zorder=4,
    )
    for sample_label, row in subset.iterrows():
      ax_d.annotate(
        str(sample_label),
        (float(row["RDA1"]), float(row["RDA2"])),
        xytext=(7, 6),
        textcoords="offset points",
        fontsize=14.5,
        fontweight="bold",
        annotation_clip=False,
      )

  extent = max(float(np.max(np.abs(sites[["RDA1", "RDA2"]].to_numpy(float)))), 1e-6)
  env_scale = extent * 0.80
  tax_scale = extent * 0.68
  x_values = list(sites["RDA1"].astype(float)) + [0.0]
  y_values = list(sites["RDA2"].astype(float)) + [0.0]

  for name, row in env.iterrows():
    x = float(row["RDA1"]) * env_scale
    y = float(row["RDA2"]) * env_scale
    ax_d.annotate(
      "",
      xy=(x, y),
      xytext=(0, 0),
      arrowprops={"arrowstyle": "-|>", "color": "#333333", "lw": 1.6},
      zorder=2,
    )
    ax_d.text(
      x * 1.14,
      y * 1.14,
      str(name),
      fontsize=17,
      fontweight="bold",
      ha="center",
      va="center",
      bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.75, "pad": 0.15},
      clip_on=False,
    )
    x_values.append(x * 1.28)
    y_values.append(y * 1.28)

  vector_items: list[tuple[str, float, float, str]] = []
  for name, row in taxa.iterrows():
    x = float(row["RDA1"]) * tax_scale
    y = float(row["RDA2"]) * tax_scale
    color = palette.get(str(name), "#111111")
    ax_d.annotate(
      "",
      xy=(x, y),
      xytext=(0, 0),
      arrowprops={"arrowstyle": "-|>", "color": color, "lw": 1.8, "linestyle": "--"},
      zorder=3,
    )
    vector_items.append((str(name), x, y, color))

  minimum_gap = max(extent * 0.14, 0.010)
  label_positions: list[tuple[str, float, float, str, float, float]] = []
  for side in (-1, 1):
    side_items = sorted(
      [item for item in vector_items if (item[1] < 0) == (side < 0)],
      key=lambda item: item[2],
    )
    previous = None
    for name, x, y, color in side_items:
      label_y = y * 1.18
      if previous is not None and label_y - previous < minimum_gap:
        label_y = previous + minimum_gap
      previous = label_y
      label_x = x * 1.22 + side * extent * 0.05
      label_positions.append((name, x, y, color, label_x, label_y))

  for name, x, y, color, label_x, label_y in label_positions:
    ax_d.annotate(
      name,
      xy=(x, y),
      xytext=(label_x, label_y),
      textcoords="data",
      fontsize=14.5,
      fontweight="bold",
      color=color,
      ha="left" if label_x >= 0 else "right",
      va="center",
      annotation_clip=False,
      arrowprops={"arrowstyle": "-", "color": color, "lw": 0.7, "alpha": 0.7},
      bbox={"facecolor": "white", "edgecolor": "none", "alpha": 0.84, "pad": 0.18},
    )
    x_values.extend([x, label_x])
    y_values.extend([y, label_y])

  ax_d.axhline(0, color="#AAAAAA", lw=0.8)
  ax_d.axvline(0, color="#AAAAAA", lw=0.8)
  ax_d.set_xlabel(
    f"RDA1 ({float(display['rda1_percent']):.1f}% {labels['constrained']})",
    fontsize=17,
    fontweight="bold",
  )
  ax_d.set_ylabel(
    f"RDA2 ({float(display['rda2_percent']):.1f}% {labels['constrained']})",
    fontsize=17,
    fontweight="bold",
  )
  ax_d.tick_params(labelsize=13)
  ax_d.set_title(
    f"D  {labels['rda']} (R² = {float(stats['RDA_R2']):.2f}; P = {float(stats['RDA_p']):.3f})",
    loc="left",
    fontsize=20,
    fontweight="bold",
    pad=10,
  )
  x_min, x_max = min(x_values), max(x_values)
  y_min, y_max = min(y_values), max(y_values)
  x_span = max(x_max - x_min, extent)
  y_span = max(y_max - y_min, extent)
  ax_d.set_xlim(
    x_min - max(x_span * 0.18, extent * 0.24),
    x_max + max(x_span * 0.34, extent * 0.42),
  )
  ax_d.set_ylim(
    y_min - max(y_span * 0.18, extent * 0.22),
    y_max + max(y_span * 0.20, extent * 0.24),
  )

  lake_season_handles = [
    Line2D(
      [0], [0], marker="o", linestyle="None",
      markerfacecolor=LAKE_COLORS[lake], markeredgecolor="black",
      label=lake, markersize=9,
    )
    for lake in ["AM", "TIA", "TI", "VI"]
  ] + [
    Line2D(
      [0], [0], marker="o" if season == "Dry" else "s",
      linestyle="None", color="black",
      label=labels["dry"] if season == "Dry" else labels["rainy"],
      markersize=9,
    )
    for season in ["Dry", "Rainy"]
  ]
  rda_handles = [
    Line2D([0], [0], color="#333333", lw=1.8, label=labels["environment"]),
    Line2D([0], [0], color="#666666", lw=1.8, linestyle="--", label=labels["genus_vector"]),
  ]
  genus_handles = [
    Patch(
      facecolor=palette.get(str(taxon), "#666666"),
      edgecolor="none",
      label=str(taxon),
    )
    for taxon in profile.index
  ]

  lake_legend = fig.legend(
    handles=lake_season_handles,
    title=labels["lake_season"],
    loc="lower left",
    bbox_to_anchor=(0.070, 0.205),
    ncol=3,
    frameon=False,
    fontsize=14.5,
    title_fontsize=16,
  )
  fig.add_artist(lake_legend)
  vector_legend = fig.legend(
    handles=rda_handles,
    title=labels["rda_vectors"],
    loc="lower right",
    bbox_to_anchor=(0.930, 0.205),
    ncol=2,
    frameon=False,
    fontsize=14.5,
    title_fontsize=16,
  )
  fig.add_artist(vector_legend)
  fig.legend(
    handles=genus_handles,
    title=labels["genus"],
    loc="lower center",
    bbox_to_anchor=(0.50, 0.035),
    ncol=min(6, max(3, math.ceil(len(profile.index) / 3))),
    frameon=False,
    fontsize=15,
    title_fontsize=17,
    columnspacing=1.5,
    handletextpad=0.5,
  )

  fig.suptitle(labels["title"], fontsize=25, fontweight="bold", y=0.985)
  fig.subplots_adjust(left=0.070, right=0.900, top=0.94, bottom=0.34)

  svg_path.parent.mkdir(parents=True, exist_ok=True)
  fig.savefig(svg_path, format="svg", facecolor="white", bbox_inches=None)
  if png_path is not None:
    png_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(png_path, format="png", dpi=300, facecolor="white", bbox_inches=None)
  if pdf_path is not None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(pdf_path, format="pdf", facecolor="white", bbox_inches=None)
  plt.close(fig)

  metadata = {
    "domain": canonical,
    "language": normalize_language(language),
    "source_files": list(data["source_files"]),
    "profile_rows": int(len(profile)),
    "profile_samples": int(len(samples)),
    "nmds_rows": int(len(scores)),
    "rda_site_rows": int(len(sites)),
    "rda_environment_vectors": int(len(env)),
    "rda_taxon_vectors": int(len(taxa)),
    "legend_below_entire_figure": True,
    "legend_overlaps_scientific_panels": False,
    "scientific_values_recomputed": False,
  }
  svg_path.with_suffix(".generation.json").write_text(
    json.dumps(metadata, ensure_ascii=False, indent=2),
    encoding="utf-8",
  )
  return metadata


def materialize_article_figure45_static(
  domain: str,
  runtime_root: Path | str,
  language: object = "en",
) -> Path:
  canonical = "Archaea" if str(domain).casefold().startswith("arch") else "Bacteria"
  lang = normalize_language(language)
  target_dir = Path(runtime_root) / CACHE_VERSION / lang
  stem = (
    "Figure4_taxonomic_bacteria_genus_profiles"
    if canonical == "Bacteria"
    else "Figure5_taxonomic_archaea_genus_profiles"
  )
  suffix = "_pt" if lang == "pt" else ""
  target = target_dir / f"{stem}{suffix}.svg"
  if not target.exists() or target.stat().st_size <= 10000:
    _render_static(canonical, lang, target)
  return target


def generate_article_figure45_outputs(root: Path | str) -> pd.DataFrame:
  root_path = Path(root).resolve()
  output_dirs = [
    root_path / "outputs" / "final_publication_figures",
    root_path / "outputs" / "app_supplementary_figures",
  ]
  records: list[dict[str, object]] = []
  for domain, figure_number in (("Bacteria", 4), ("Archaea", 5)):
    stem = (
      "Figure4_taxonomic_bacteria_genus_profiles"
      if domain == "Bacteria"
      else "Figure5_taxonomic_archaea_genus_profiles"
    )
    primary = output_dirs[0]
    svg = primary / f"{stem}.svg"
    png = primary / f"{stem}.png"
    pdf = primary / f"{stem}.pdf"
    metadata = _render_static(domain, "en", svg, png, pdf)
    for destination in output_dirs[1:]:
      destination.mkdir(parents=True, exist_ok=True)
      for path in (svg, png, pdf, svg.with_suffix(".generation.json")):
        shutil.copy2(path, destination / path.name)
    records.append({
      "figure": figure_number,
      "domain": domain,
      "svg": str(svg.relative_to(root_path)),
      "png": str(png.relative_to(root_path)),
      "pdf": str(pdf.relative_to(root_path)),
      **metadata,
    })
  derived = root_path / "data" / "final_publication_derived"
  derived.mkdir(parents=True, exist_ok=True)
  manifest = pd.DataFrame(records)
  manifest.to_csv(derived / "Figure45_final_generation_manifest.csv", index=False)
  return manifest
