from __future__ import annotations

"""Generate static Figure 4/5 SVGs from frozen article values and layout."""

from pathlib import Path
import math

import numpy as np

from .article_frozen_taxonomy_panels import (
  LAKE_COLORS,
  frozen_taxonomy_domain_data,
)


def materialize_frozen_article_static(
  domain: str,
  runtime_root: Path | str,
) -> Path:
  import matplotlib

  matplotlib.use("Agg")
  import matplotlib.pyplot as plt
  from matplotlib.lines import Line2D
  from matplotlib.patches import Patch

  data = frozen_taxonomy_domain_data(domain)
  canonical = str(data["domain"])
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

  target_dir = Path(runtime_root) / "frozen_article_taxonomy_static_v2"
  target_dir.mkdir(parents=True, exist_ok=True)
  stem = (
    "Figure4_taxonomic_bacteria_genus_profiles"
    if canonical == "Bacteria"
    else "Figure5_taxonomic_archaea_genus_profiles"
  )
  target = target_dir / f"{stem}.svg"
  if target.exists() and target.stat().st_size > 10000:
    return target

  def stacked(ax, selected_samples, panel, label):
    y = np.arange(len(selected_samples))
    left = np.zeros(len(selected_samples))
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
    ax.set_xlabel(
      "Relative abundance (%)",
      fontsize=20,
      fontweight="bold",
      labelpad=8,
    )
    ax.tick_params(axis="x", labelsize=14, pad=5)
    ax.set_title(
      f"{panel}  {label}",
      loc="left",
      fontsize=20,
      fontweight="bold",
      pad=10,
    )
    ax.spines[["top", "right"]].set_visible(False)

  fig = plt.figure(figsize=(27, 22.5))
  grid = fig.add_gridspec(
    2,
    2,
    height_ratios=[1.05, 1],
    hspace=0.35,
    wspace=0.28,
  )
  ax_a, ax_b, ax_c, ax_d = [
    fig.add_subplot(grid[i, j])
    for i, j in [(0, 0), (0, 1), (1, 0), (1, 1)]
  ]
  stacked(ax_a, dry, "A", "Dry-season genus profiles")
  stacked(ax_b, rainy, "B", "Rainy-season genus profiles")

  for lake in ["AM", "TIA", "TI", "VI"]:
    for season in ["Dry", "Rainy"]:
      subset = scores[
        (scores["Lake"] == lake) & (scores["Season"] == season)
      ]
      ax_c.scatter(
        subset.NMDS1,
        subset.NMDS2,
        s=105,
        color=LAKE_COLORS[lake],
        marker="o" if season == "Dry" else "s",
        edgecolor="black",
        linewidth=0.8,
        zorder=3,
      )
      for _, row in subset.iterrows():
        ax_c.annotate(
          row.Sample,
          (row.NMDS1, row.NMDS2),
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
    (
      "C  Bray-Curtis NMDS "
      f"(stress = {float(stats['NMDS_stress']):.3f})"
    ),
    loc="left",
    fontsize=20,
    fontweight="bold",
    pad=10,
  )
  ax_c.margins(x=0.20, y=0.20)
  ord_handles = [
    Line2D(
      [0],
      [0],
      marker="o",
      linestyle="None",
      markerfacecolor=LAKE_COLORS[lake],
      markeredgecolor="black",
      label=lake,
      markersize=9,
    )
    for lake in ["AM", "TIA", "TI", "VI"]
  ]
  ord_handles += [
    Line2D(
      [0],
      [0],
      marker="o" if season == "Dry" else "s",
      linestyle="None",
      color="black",
      label=season,
      markersize=9,
    )
    for season in ["Dry", "Rainy"]
  ]
  ax_c.legend(
    handles=ord_handles,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.18),
    ncol=3,
    frameon=False,
    fontsize=14.5,
    title="Lake / season",
    title_fontsize=16,
    borderaxespad=0,
  )

  for lake, subset in sites.groupby("Lake"):
    ax_d.scatter(
      subset.RDA1,
      subset.RDA2,
      s=120,
      color=LAKE_COLORS.get(lake, "#777777"),
      edgecolor="black",
      linewidth=0.8,
      zorder=4,
    )
    for label, row in subset.iterrows():
      ax_d.annotate(
        label,
        (row.RDA1, row.RDA2),
        xytext=(7, 6),
        textcoords="offset points",
        fontsize=14.5,
        fontweight="bold",
        annotation_clip=False,
      )
  extent = max(
    float(np.max(np.abs(sites[["RDA1", "RDA2"]].to_numpy()))),
    1e-6,
  )
  env_scale, tax_scale = extent * 0.80, extent * 0.68
  xvals = list(sites.RDA1.astype(float)) + [0.0]
  yvals = list(sites.RDA2.astype(float)) + [0.0]
  for name, row in env.iterrows():
    x = row.RDA1 * env_scale
    y = row.RDA2 * env_scale
    ax_d.annotate(
      "",
      xy=(x, y),
      xytext=(0, 0),
      arrowprops=dict(
        arrowstyle="-|>",
        color="#333333",
        lw=1.6,
      ),
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
      bbox=dict(
        fc="white",
        ec="none",
        alpha=0.75,
        pad=0.15,
      ),
      clip_on=False,
    )
    xvals.append(float(x * 1.28))
    yvals.append(float(y * 1.28))
  items = []
  for name, row in taxa.iterrows():
    x = row.RDA1 * tax_scale
    y = row.RDA2 * tax_scale
    color = palette.get(str(name), "#111111")
    ax_d.annotate(
      "",
      xy=(x, y),
      xytext=(0, 0),
      arrowprops=dict(
        arrowstyle="-|>",
        color=color,
        lw=1.8,
        linestyle="--",
      ),
      zorder=3,
    )
    items.append((str(name), x, y, color))
  gap = max(extent * 0.14, 0.010)
  positions = []
  for side in (-1, 1):
    part = sorted(
      [
        item
        for item in items
        if (item[1] < 0) == (side < 0)
      ],
      key=lambda item: item[2],
    )
    previous = None
    for name, x, y, color in part:
      label_y = y * 1.18
      if previous is not None and label_y - previous < gap:
        label_y = previous + gap
      previous = label_y
      label_x = x * 1.22 + side * extent * 0.05
      positions.append(
        (
          name,
          x,
          y,
          color,
          label_x,
          label_y,
        )
      )
  for name, x, y, color, label_x, label_y in positions:
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
      arrowprops=dict(
        arrowstyle="-",
        color=color,
        lw=0.7,
        alpha=0.7,
      ),
      bbox=dict(
        fc="white",
        ec="none",
        alpha=0.84,
        pad=0.18,
      ),
    )
    xvals.extend([x, label_x])
    yvals.extend([y, label_y])
  ax_d.axhline(0, color="#AAAAAA", lw=0.8)
  ax_d.axvline(0, color="#AAAAAA", lw=0.8)
  ax_d.set_xlabel(
    (
      f"RDA1 ({float(display['rda1_percent']):.1f}% "
      "constrained variation)"
    ),
    fontsize=17,
    fontweight="bold",
  )
  ax_d.set_ylabel(
    (
      f"RDA2 ({float(display['rda2_percent']):.1f}% "
      "constrained variation)"
    ),
    fontsize=17,
    fontweight="bold",
  )
  ax_d.tick_params(labelsize=13)
  ax_d.set_title(
    (
      f"D  RDA biplot (R² = {float(stats['RDA_R2']):.2f}; "
      f"P = {float(stats['RDA_p']):.3f})"
    ),
    loc="left",
    fontsize=20,
    fontweight="bold",
    pad=10,
  )
  rda_handles = [
    Line2D(
      [0],
      [0],
      color="#333333",
      lw=1.8,
      label="Environmental variable",
    ),
    Line2D(
      [0],
      [0],
      color="#666666",
      lw=1.8,
      linestyle="--",
      label="Representative genus vector",
    ),
  ]
  ax_d.legend(
    handles=rda_handles,
    loc="upper center",
    bbox_to_anchor=(0.5, -0.18),
    ncol=2,
    frameon=False,
    fontsize=14.5,
    borderaxespad=0,
  )
  xmin, xmax = min(xvals), max(xvals)
  ymin, ymax = min(yvals), max(yvals)
  ax_d.set_xlim(
    xmin - max((xmax - xmin) * 0.16, extent * 0.22),
    xmax + max((xmax - xmin) * 0.16, extent * 0.22),
  )
  ax_d.set_ylim(
    ymin - max((ymax - ymin) * 0.18, extent * 0.22),
    ymax + max((ymax - ymin) * 0.18, extent * 0.22),
  )

  handles = [
    Patch(
      facecolor=palette.get(str(taxon), "#666666"),
      edgecolor="none",
      label=str(taxon),
    )
    for taxon in profile.index
  ]
  fig.legend(
    handles=handles,
    title="Genus",
    loc="lower center",
    bbox_to_anchor=(0.5, 0.012),
    ncol=min(
      6,
      max(
        3,
        math.ceil(len(profile.index) / 3),
      ),
    ),
    frameon=False,
    fontsize=15,
    title_fontsize=17,
    columnspacing=1.5,
    handletextpad=0.5,
  )
  fig.subplots_adjust(
    left=0.075,
    right=0.96,
    top=0.94,
    bottom=0.31,
  )
  fig.savefig(
    target,
    format="svg",
    bbox_inches="tight",
    facecolor="white",
  )
  plt.close(fig)
  return target
