#!/usr/bin/env python3
"""Generate final Supplementary Figures 40 and 67 with readable x labels.

The source matrices, status mapping, row order, column order, colours, and
scientific-equivalence checks are delegated to the canonical environmental-group
generator. This final renderer changes only figure geometry: 45-degree x labels,
dynamic width, larger bottom margin, and unclipped publication exports.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from scripts.figures import generate_environmental_group_heatmaps as canonical


def plot_panel_final(
  matrix,
  columns: list[str],
  column_meta,
  title: str,
  panel_index: int,
  panel_count: int,
  grouped: bool,
):
  values = matrix.apply(
    lambda column: column.map(canonical.STATUS_TO_VALUE)
  ).astype(float).to_numpy()
  cmap = ListedColormap([
    canonical.COLORS["Incomplete"],
    canonical.COLORS["1 block missing"],
    canonical.COLORS["Complete"],
  ])
  cmap.set_bad(canonical.COLORS["Missing"])
  norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N)

  xlabels = canonical.display_labels(columns, column_meta)
  longest_label = max(
    (len(str(label).replace("\n", " ")) for label in xlabels),
    default=12,
  )
  figure_width = max(16.54, min(32.0, 8.5 + 0.27 * max(len(columns), 1)))
  bottom_margin = min(0.38, max(0.24, 0.20 + 0.0022 * longest_label))

  fig, ax = plt.subplots(figsize=(figure_width, 11.20), dpi=300)
  ax.imshow(
    np.ma.masked_invalid(values),
    cmap=cmap,
    norm=norm,
    aspect="auto",
    interpolation="nearest",
  )
  full_title = f"{title} - Panel P{panel_index:03d} of P{panel_count:03d}"
  fig.text(
    0.02,
    0.975,
    full_title,
    ha="left",
    va="top",
    fontsize=15.5 if grouped else 16.5,
    fontweight="bold",
  )
  ax.set_ylabel(
    "KEGG/KEMET module and metabolic pathway",
    fontsize=13,
    fontweight="bold",
    labelpad=22,
  )
  ax.set_xlabel("")

  ax.set_xticks(np.arange(len(columns)))
  ax.set_xticklabels(
    xlabels,
    rotation=45,
    ha="right",
    va="top",
    rotation_mode="anchor",
    fontsize=7.8 if len(columns) <= 70 else 7.2,
  )
  ax.set_yticks(np.arange(matrix.shape[0]))
  ax.set_yticklabels(
    [canonical.wrapped_module_label(value) for value in matrix.index],
    fontsize=8.6,
  )
  ax.set_xticks(np.arange(-0.5, len(columns), 1), minor=True)
  ax.set_yticks(np.arange(-0.5, matrix.shape[0], 1), minor=True)
  ax.grid(which="minor", color="#FFFFFF", linewidth=0.45)
  ax.tick_params(which="minor", bottom=False, left=False)
  ax.tick_params(axis="both", which="major", length=0)
  for spine in ax.spines.values():
    spine.set_visible(False)

  if grouped:
    runs = canonical.contiguous_group_runs(columns, column_meta)
    for run_index, (group, start, end) in enumerate(runs):
      centre = (start + end) / 2
      ax.text(
        centre,
        1.035,
        canonical.DISPLAY_GROUP.get(group, group.replace("-", " ")),
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="bottom",
        fontsize=6.6 if len(runs) > 8 else 8.0,
        fontweight="bold",
        clip_on=False,
      )
      if run_index:
        ax.axvline(start - 0.5, color="#222222", linewidth=1.05, zorder=5)

  legend = [
    Patch(
      facecolor=canonical.COLORS["Complete"],
      edgecolor="none",
      label="Complete",
    ),
    Patch(
      facecolor=canonical.COLORS["1 block missing"],
      edgecolor="none",
      label="1 block missing",
    ),
    Patch(
      facecolor=canonical.COLORS["Incomplete"],
      edgecolor="none",
      label="Incomplete",
    ),
  ]
  fig.legend(
    handles=legend,
    loc="lower center",
    bbox_to_anchor=(0.5, 0.025),
    ncol=3,
    frameon=False,
    title="KEMET module status",
    fontsize=9.5,
    title_fontsize=10.5,
  )
  fig.subplots_adjust(
    left=0.25,
    right=0.992,
    top=0.82 if grouped else 0.90,
    bottom=bottom_margin,
  )
  return fig


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument(
    "--root",
    type=Path,
    default=ROOT,
    help="Application or article-package root.",
  )
  args = parser.parse_args()

  canonical.plot_panel = plot_panel_final
  report = canonical.run(args.root.resolve())
  report["final_renderer"] = str(Path(__file__).relative_to(ROOT))
  report["x_tick_angle_degrees"] = 45
  report["scientific_values_changed"] = False
  print(json.dumps({
    "status": report["status"],
    "root": report["root"],
    "x_tick_angle_degrees": 45,
    "scientific_values_changed": False,
    "comparison_files": report["comparison_files"],
  }, indent=2, ensure_ascii=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
