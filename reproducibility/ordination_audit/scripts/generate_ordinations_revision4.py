#!/usr/bin/env python3
"""Regenerate Figures 4, 5 and Supplementary Figure 17 from real study data.

The script uses ``src.publication_ordination`` as the single scientific
implementation shared with the Streamlit application. It calculates true
non-metric MDS (Bray-Curtis, two dimensions, 20 starts, seed 42) and the
position-level physicochemical RDA, exports complete audit tables, and writes
native PNG, PDF and SVG files without post-render image editing.
"""
from __future__ import annotations

import argparse
import json
import sys
import math
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
import matplotlib.patheffects as pe
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT))

from src.publication_ordination import (
  SAMPLE_ORDER, POSITION_ORDER, compute_nmds, compute_rda, domain_genus_matrix,
  library_versions, SEED, N_PERMUTATIONS,
)
from src.taxonomy_palette import build_palette, load_palette, save_palette

LAKE_COLORS = {"AM": "#0072B2", "TIA": "#E69F00", "TI": "#009E73", "VI": "#CC79A7"}
SEASON_MARKERS = {"Dry": "o", "Rainy": "s"}


def save_native(fig: plt.Figure, stem: Path, destinations: list[Path], dpi: int = 300) -> None:
  stem.parent.mkdir(parents=True, exist_ok=True)
  fig.savefig(stem.with_suffix(".png"), dpi=dpi, bbox_inches="tight", facecolor="white")
  fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight", facecolor="white")
  fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight", facecolor="white")
  plt.close(fig)
  for destination in destinations:
    destination.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf", "svg"):
      shutil.copy2(stem.with_suffix(f".{ext}"), destination / f"{stem.name}.{ext}")


def stacked_bar(ax: plt.Axes, rel: pd.DataFrame, samples: list[str], palette: dict[str, str], panel: str, label: str) -> None:
  y = np.arange(len(samples))
  left = np.zeros(len(samples), dtype=float)
  for taxon in rel.index:
    values = rel.loc[taxon, samples].to_numpy(float)
    ax.barh(y, values, left=left, height=0.82, color=palette[taxon], edgecolor="white", linewidth=0.35)
    left += values
  ax.set_yticks(y, samples, fontsize=15)
  ax.invert_yaxis()
  ax.set_xlim(0, 100)
  ax.set_xlabel("Relative abundance (%)", fontsize=20, fontweight="bold", labelpad=8)
  ax.tick_params(axis="x", labelsize=14, pad=5)
  ax.set_title(f"{panel}  {label}", loc="left", fontsize=20, fontweight="bold", pad=10)
  ax.spines[["top", "right"]].set_visible(False)


def _repelled_point_labels(ax: plt.Axes, frame: pd.DataFrame, xcol: str, ycol: str, label_col: str, fontsize: float = 13.0) -> None:
  """Place all point labels inside the panel using deterministic side columns."""
  x = frame[xcol].to_numpy(float)
  y = frame[ycol].to_numpy(float)
  xmin, xmax = ax.get_xlim(); ymin, ymax = ax.get_ylim()
  xr = xmax - xmin; yr = ymax - ymin
  center_x = float(np.median(x))
  min_gap = max(yr * 0.045, 1e-8)
  for side in (-1, 1):
    idx = np.where(x < center_x)[0] if side < 0 else np.where(x >= center_x)[0]
    if len(idx) == 0:
      continue
    ordered = idx[np.argsort(y[idx])]
    target_y = []
    previous = ymin + yr * 0.06 - min_gap
    for i in ordered:
      value = float(np.clip(y[i], ymin + yr * 0.06, ymax - yr * 0.06))
      value = max(value, previous + min_gap)
      target_y.append(value)
      previous = value
    overflow = target_y[-1] - (ymax - yr * 0.06)
    if overflow > 0:
      target_y = [v - overflow for v in target_y]
    label_x = xmin + xr * 0.035 if side < 0 else xmax - xr * 0.035
    for i, ly in zip(ordered, target_y):
      label = str(frame.iloc[i][label_col])
      ax.annotate(
        label, xy=(x[i], y[i]), xytext=(label_x, ly), textcoords="data",
        ha="left" if side < 0 else "right", va="center",
        fontsize=fontsize, fontweight="bold", color="black", annotation_clip=True,
        arrowprops=dict(arrowstyle="-", color="#606060", lw=0.65, alpha=0.75),
        bbox=dict(boxstyle="round,pad=0.11", fc="white", ec="none", alpha=0.83), zorder=7,
      )


def draw_nmds(ax: plt.Axes, result: dict, panel: str = "C") -> None:
  scores = result["scores"]
  for lake in ["AM", "TIA", "TI", "VI"]:
    for season in ["Dry", "Rainy"]:
      subset = scores[(scores["Lake"] == lake) & (scores["Season"] == season)]
      ax.scatter(
        subset["NMDS1"], subset["NMDS2"], s=100,
        color=LAKE_COLORS[lake], marker=SEASON_MARKERS[season],
        edgecolor="black", linewidth=0.9, zorder=4,
      )
  ax.axhline(0, color="#AAAAAA", lw=0.8)
  ax.axvline(0, color="#AAAAAA", lw=0.8)
  xr = float(np.ptp(scores["NMDS1"])); yr = float(np.ptp(scores["NMDS2"]))
  ax.set_xlim(float(scores["NMDS1"].min() - max(xr * 0.30, 0.03)), float(scores["NMDS1"].max() + max(xr * 0.30, 0.03)))
  ax.set_ylim(float(scores["NMDS2"].min() - max(yr * 0.20, 0.02)), float(scores["NMDS2"].max() + max(yr * 0.20, 0.02)))
  _repelled_point_labels(ax, scores, "NMDS1", "NMDS2", "Sample", fontsize=12.4)
  ax.set_xlabel("NMDS1", fontsize=17, fontweight="bold")
  ax.set_ylabel("NMDS2", fontsize=17, fontweight="bold")
  ax.tick_params(labelsize=14)
  ax.set_title(
    f"{panel}  Bray-Curtis non-metric MDS (Stress-1 = {result['stress']:.3f})",
    loc="left", fontsize=19, fontweight="bold", pad=10,
  )
  handles = [Line2D([0], [0], marker="o", linestyle="None", markerfacecolor=LAKE_COLORS[l], markeredgecolor="black", label=l, markersize=9) for l in ["AM", "TIA", "TI", "VI"]]
  handles += [Line2D([0], [0], marker=SEASON_MARKERS[s], linestyle="None", color="black", label=s, markersize=9) for s in ["Dry", "Rainy"]]
  ax.legend(handles=handles, loc="upper left", bbox_to_anchor=(1.005, 1.0), frameon=False, fontsize=13.5, title="Lake / season", title_fontsize=14.5)


def _bounded_environment_labels(ax: plt.Axes, vectors: pd.DataFrame, scale: float, xlim: tuple[float, float], ylim: tuple[float, float]) -> None:
  xmin, xmax = xlim; ymin, ymax = ylim; xr = xmax - xmin; yr = ymax - ymin
  for name, row in vectors.iterrows():
    x, y = float(row["RDA1"] * scale), float(row["RDA2"] * scale)
    ax.annotate("", xy=(x, y), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color="#333333", lw=1.6), zorder=2)
    lx = float(np.clip(x * 1.12, xmin + xr * 0.07, xmax - xr * 0.07))
    ly = float(np.clip(y * 1.12, ymin + yr * 0.07, ymax - yr * 0.07))
    ax.text(lx, ly, str(name), fontsize=14.5, fontweight="bold", ha="center", va="center", bbox=dict(fc="white", ec="none", alpha=0.78, pad=0.16), clip_on=True, zorder=8)


def _bounded_taxon_labels(ax: plt.Axes, taxa: pd.DataFrame, scale: float, palette: dict[str, str], xlim: tuple[float, float], ylim: tuple[float, float]) -> None:
  xmin, xmax = xlim; ymin, ymax = ylim; xr = xmax - xmin; yr = ymax - ymin
  entries = []
  for name, row in taxa.iterrows():
    x, y = float(row["RDA1"] * scale), float(row["RDA2"] * scale)
    color = palette.get(str(name), "#111111")
    ax.annotate("", xy=(x, y), xytext=(0, 0), arrowprops=dict(arrowstyle="-|>", color=color, lw=1.6, linestyle="--"), zorder=3)
    entries.append((str(name), x, y, color))
  gap = yr * 0.075
  for side in (-1, 1):
    side_entries = [entry for entry in entries if (entry[1] < 0) == (side < 0)]
    side_entries.sort(key=lambda item: item[2])
    previous = ymin + yr * 0.08 - gap
    assigned = []
    for entry in side_entries:
      ly = float(np.clip(entry[2], ymin + yr * 0.08, ymax - yr * 0.08))
      ly = max(ly, previous + gap)
      assigned.append(ly); previous = ly
    if assigned and assigned[-1] > ymax - yr * 0.08:
      shift = assigned[-1] - (ymax - yr * 0.08)
      assigned = [v - shift for v in assigned]
    lx = xmin + xr * 0.025 if side < 0 else xmax - xr * 0.025
    for (name, x, y, color), ly in zip(side_entries, assigned):
      ax.annotate(
        name, xy=(x, y), xytext=(lx, ly), textcoords="data",
        ha="left" if side < 0 else "right", va="center", fontsize=12.2,
        fontweight="bold", color=color, annotation_clip=True,
        arrowprops=dict(arrowstyle="-", color=color, lw=0.75, alpha=0.8),
        bbox=dict(boxstyle="round,pad=0.13", fc="white", ec="none", alpha=0.86), zorder=9,
      )


def draw_rda(ax: plt.Axes, result: dict, palette: dict[str, str], panel: str = "D", title: str | None = None) -> None:
  scores = result["scores"].reset_index()
  for lake, subset in scores.groupby("Lake"):
    ax.scatter(subset["RDA1"], subset["RDA2"], s=125, color=LAKE_COLORS.get(lake, "#777777"), edgecolor="black", linewidth=0.9, zorder=5)
  extent = max(float(np.max(np.abs(scores[["RDA1", "RDA2"]].to_numpy(float)))), 1e-6)
  env_scale = extent * 0.82; tax_scale = extent * 0.70
  arrow_x = [0.0] + [float(x * env_scale) for x in result["vectors"]["RDA1"]] + [float(x * tax_scale) for x in result["taxon_vectors"]["RDA1"]]
  arrow_y = [0.0] + [float(y * env_scale) for y in result["vectors"]["RDA2"]] + [float(y * tax_scale) for y in result["taxon_vectors"]["RDA2"]]
  xmin = min(float(scores["RDA1"].min()), min(arrow_x)); xmax = max(float(scores["RDA1"].max()), max(arrow_x))
  ymin = min(float(scores["RDA2"].min()), min(arrow_y)); ymax = max(float(scores["RDA2"].max()), max(arrow_y))
  xr = max(xmax - xmin, extent); yr = max(ymax - ymin, extent)
  xlim = (xmin - xr * 0.48, xmax + xr * 0.48)
  ylim = (ymin - yr * 0.33, ymax + yr * 0.33)
  ax.set_xlim(*xlim); ax.set_ylim(*ylim)
  _bounded_environment_labels(ax, result["vectors"], env_scale, xlim, ylim)
  _bounded_taxon_labels(ax, result["taxon_vectors"], tax_scale, palette, xlim, ylim)
  _repelled_point_labels(ax, scores, "RDA1", "RDA2", "Sample", fontsize=12.5)
  ax.axhline(0, color="#AAAAAA", lw=0.8); ax.axvline(0, color="#AAAAAA", lw=0.8)
  ax.set_xlabel(f"RDA1 ({result['pct'][0]:.1f}% constrained variation)", fontsize=16.5, fontweight="bold")
  ax.set_ylabel(f"RDA2 ({result['pct'][1]:.1f}% constrained variation)", fontsize=16.5, fontweight="bold")
  ax.tick_params(labelsize=13.5)
  heading = title or "RDA biplot"
  ax.set_title(f"{panel}  {heading} (R² = {result['r2']:.3f}; P = {result['p']:.3f})", loc="left", fontsize=18.5, fontweight="bold", pad=10)
  ax.legend(
    handles=[Line2D([0], [0], color="#333333", lw=1.8, label="Environmental variable"), Line2D([0], [0], color="#666666", lw=1.8, linestyle="--", label="Representative genus vector")],
    loc="lower center", bbox_to_anchor=(0.5, -0.01), ncol=2, frameon=False, fontsize=11.8,
  )


def export_analysis_tables(base: Path, audit_root: Path, domain: str, rel: pd.DataFrame, nmds: dict, rda: dict) -> None:
  derived = base / "data/final_publication_derived"
  derived.mkdir(parents=True, exist_ok=True)
  tables = audit_root / "tables"; intermediate = audit_root / "intermediate"; output = audit_root / "output"; validation = audit_root / "validation"
  for path in (tables, intermediate, output, validation): path.mkdir(parents=True, exist_ok=True)
  nmds["scores"].to_csv(derived / f"Figure{4 if domain == 'Bacteria' else 5}_taxonomic_{domain.lower()}_genus_profiles_NMDS_scores.csv", index=False)
  nmds["scores"].to_csv(output / f"{domain}_NMDS_scores.csv", index=False)
  nmds["transformed"].to_csv(intermediate / f"{domain}_NMDS_square_root_relative_proportions.csv")
  nmds["distance"].to_csv(intermediate / f"{domain}_NMDS_Bray_Curtis_distance_matrix.csv")
  nmds["sample_audit"].to_csv(tables / f"{domain}_NMDS_sample_audit.csv", index=False)
  nmds["tests"].to_csv(tables / f"{domain}_NMDS_PERMANOVA_and_dispersion_tests.csv", index=False)
  nmds["near_overlap_pairs"].to_csv(validation / f"{domain}_NMDS_near_overlap_pairs.csv", index=False)
  (output / f"{domain}_NMDS_statistics.json").write_text(json.dumps({
    "stress_1": nmds["stress"], "iterations": nmds["n_iter"], "converged": nmds["converged"],
    "rank_correlation_observed_vs_ordination_distances": nmds["rank_correlation"], **nmds["parameters"],
  }, indent=2), encoding="utf-8")

  rda["scores"].to_csv(derived / f"Figure_{domain}_genus_RDA_site_scores.csv")
  rda["vectors"].to_csv(derived / f"Figure_{domain}_genus_RDA_environment_vectors.csv")
  rda["taxon_vectors_all"].to_csv(derived / f"Figure_{domain}_genus_RDA_all_genus_vectors.csv")
  rda["taxon_vectors"].to_csv(derived / f"Figure_{domain}_genus_RDA_representative_genus_vectors.csv")
  rda["scores"].to_csv(output / f"{domain}_RDA_site_scores.csv")
  rda["vectors"].to_csv(output / f"{domain}_RDA_environment_vectors.csv")
  rda["taxon_vectors"].to_csv(output / f"{domain}_RDA_representative_genus_vectors.csv")
  rda["transformed_community"].to_csv(intermediate / f"{domain}_RDA_Hellinger_community_matrix.csv")
  rda["standardized_environment"].to_csv(intermediate / f"{domain}_RDA_standardized_environment.csv")
  rda["pooled_abundance"].to_csv(intermediate / f"{domain}_RDA_pooled_position_abundance.csv")
  rda["sample_audit"].to_csv(tables / f"{domain}_RDA_sample_audit.csv", index=False)
  rda["vif"].to_csv(tables / f"{domain}_RDA_VIF.csv", index=False)
  rda["model_stats"].to_csv(tables / f"{domain}_RDA_model_statistics.csv", index=False)
  rda["near_overlap_pairs"].to_csv(validation / f"{domain}_RDA_near_overlap_pairs.csv", index=False)


def make_main_figure(base: Path, article: Path, domain: str, rel: pd.DataFrame, palette: dict[str, str], nmds: dict, rda: dict) -> None:
  number = 4 if domain == "Bacteria" else 5
  stem_name = f"Figure{number}_taxonomic_{domain.lower()}_genus_profiles"
  fig = plt.figure(figsize=(29, 20.5))
  grid = fig.add_gridspec(2, 2, height_ratios=[1.0, 1.13], hspace=0.31, wspace=0.28)
  axes = [fig.add_subplot(grid[0, 0]), fig.add_subplot(grid[0, 1]), fig.add_subplot(grid[1, 0]), fig.add_subplot(grid[1, 1])]
  dry = [s for s in SAMPLE_ORDER if s.endswith(".D") and s in rel.columns]
  rainy = [s for s in SAMPLE_ORDER if s.endswith(".R") and s in rel.columns]
  stacked_bar(axes[0], rel, dry, palette, "A", "Dry-season genus profiles")
  stacked_bar(axes[1], rel, rainy, palette, "B", "Rainy-season genus profiles")
  draw_nmds(axes[2], nmds, "C")
  draw_rda(axes[3], rda, palette, "D", "RDA biplot")
  handles = [Patch(facecolor=palette[t], edgecolor="none", label=t) for t in rel.index]
  fig.legend(handles=handles, title="Genus", loc="lower center", bbox_to_anchor=(0.5, 0.012), ncol=min(6, max(3, math.ceil(len(rel.index) / 3))), frameon=False, fontsize=14.5, title_fontsize=16)
  fig.subplots_adjust(left=0.065, right=0.95, top=0.96, bottom=0.18)
  stem = base / "outputs/final_publication_figures" / stem_name
  save_native(fig, stem, [article / "02_Main_Figures_title_free"])
  rel.to_csv(base / "data/final_publication_derived" / f"{stem_name}_source.csv")
  pd.DataFrame([{
    "domain": domain, "NMDS_Stress_1": nmds["stress"], "NMDS_iterations": nmds["n_iter"],
    "RDA_R2": rda["r2"], "RDA_adjusted_R2": rda["adjusted_r2"], "RDA_F": rda["F"], "RDA_p": rda["p"],
    "RDA_axis1_p": rda["axis_p"][0], "RDA_axis2_p": rda["axis_p"][1], "RDA_variables": "; ".join(rda["variables"]), "RDA_n_positions": rda["n"],
  }]).to_csv(base / "data/final_publication_derived" / f"{stem_name}_ordination_statistics.csv", index=False)


def make_s17(base: Path, article: Path, palette: dict[str, str], bacterial_rda: dict, archaeal_rda: dict) -> None:
  env = pd.read_excel(base / "data/fiqui2.xlsx")
  env.columns = [str(c).strip() for c in env.columns]
  env["SampleMM"] = env["SampleMM"].astype(str).str.strip().replace({"V1.P1": "VI.P1"})
  for col in env.columns[3:]: env[col] = pd.to_numeric(env[col], errors="coerce")
  envagg = env.groupby("SampleMM").mean(numeric_only=True)
  columns = [c for c in ["LOI", "Fe2O3", "SiO2", "Al2O3", "TOT/C", "TOT/S", "Cu", "Pb", "V"] if c in envagg.columns]
  z = envagg.loc[[p for p in POSITION_ORDER if p in envagg.index], columns].T
  z = z.sub(z.mean(axis=1), axis=0).div(z.std(axis=1, ddof=0).replace(0, 1), axis=0)
  fig = plt.figure(figsize=(30, 18.5))
  grid = fig.add_gridspec(2, 2, height_ratios=[1.18, 0.72], hspace=0.28, wspace=0.21)
  ax_a = fig.add_subplot(grid[0, 0]); ax_b = fig.add_subplot(grid[0, 1]); ax_c = fig.add_subplot(grid[1, :])
  draw_rda(ax_a, bacterial_rda, palette, "A", "Bacterial genus-level RDA")
  draw_rda(ax_b, archaeal_rda, palette, "B", "Archaeal genus-level RDA")
  values = z.to_numpy(float); vmax = max(abs(float(np.nanmin(values))), abs(float(np.nanmax(values))))
  image = ax_c.imshow(values, aspect="auto", cmap="coolwarm_r", vmin=-vmax, vmax=vmax, interpolation="nearest")
  ax_c.set_xticks(np.arange(z.shape[1]), z.columns, rotation=45, ha="right", rotation_mode="anchor", fontsize=14.5)
  ax_c.set_yticks(np.arange(z.shape[0]), z.index, fontsize=14.5)
  ax_c.tick_params(length=0, pad=5)
  ax_c.set_xlabel("Sampling position", fontsize=16.5, fontweight="bold", labelpad=12)
  ax_c.set_ylabel("Physicochemical variable", fontsize=16.5, fontweight="bold")
  ax_c.set_title("C  Descriptive physicochemical row-z-score heatmap", loc="left", fontsize=18.5, fontweight="bold", pad=10)
  ax_c.set_xticks(np.arange(-0.5, z.shape[1], 1), minor=True); ax_c.set_yticks(np.arange(-0.5, z.shape[0], 1), minor=True)
  ax_c.grid(which="minor", color="white", lw=0.8); ax_c.tick_params(which="minor", bottom=False, left=False)
  colorbar = fig.colorbar(image, ax=ax_c, pad=0.012, fraction=0.022)
  colorbar.set_label("Row z-score", fontsize=15.5, fontweight="bold"); colorbar.ax.tick_params(labelsize=13.5)
  fig.subplots_adjust(left=0.055, right=0.975, bottom=0.09, top=0.98)
  stem = base / "outputs/final_publication_figures/SupplementaryFigure17_RDA_and_physicochemical_heatmap"
  save_native(fig, stem, [base / "outputs/app_supplementary_figures", article / "03_Supplementary_Figures"])
  z.to_csv(base / "data/final_publication_derived/SupplementaryFigure17_physicochemical_row_zscore_source.csv")


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[2])
  parser.add_argument("--article-root", type=Path, required=True)
  args = parser.parse_args()
  base = args.base_dir.resolve(); article = args.article_root.resolve()
  audit_root = base / "reproducibility/ordination_reproducibility"
  for sub in ["input", "intermediate", "output", "tables", "figures", "logs", "validation", "scripts"]:
    (audit_root / sub).mkdir(parents=True, exist_ok=True)
  taxa = []
  results = {}
  for domain in ["Bacteria", "Archaea"]:
    rel = domain_genus_matrix(base, domain, top_n=18)
    taxa.extend(rel.index.astype(str))
    results[domain] = {"rel": rel, "nmds": compute_nmds(rel, domain), "rda": compute_rda(base, rel, domain)}
  palette = build_palette(taxa, load_palette(base / "data/taxonomy_palette.json"))
  save_palette(palette, base / "data/taxonomy_palette.json")
  for domain in ["Bacteria", "Archaea"]:
    export_analysis_tables(base, audit_root, domain, **results[domain])
    make_main_figure(base, article, domain, results[domain]["rel"], palette, results[domain]["nmds"], results[domain]["rda"])
  make_s17(base, article, palette, results["Bacteria"]["rda"], results["Archaea"]["rda"])
  # Copy exact inputs and final figures into the audit directory.
  for name in ["resultado.cds.otu.tab", "resultado.cds.tax.tab", "fiqui2.xlsx"]:
    shutil.copy2(base / "data" / name, audit_root / "input" / name)
  for name in ["Figure4_taxonomic_bacteria_genus_profiles", "Figure5_taxonomic_archaea_genus_profiles", "SupplementaryFigure17_RDA_and_physicochemical_heatmap"]:
    for ext in ["png", "pdf", "svg"]:
      shutil.copy2(base / "outputs/final_publication_figures" / f"{name}.{ext}", audit_root / "figures" / f"{name}.{ext}")
  summary = {
    "status": "success",
    "seed": SEED,
    "permutations": N_PERMUTATIONS,
    "libraries": library_versions(),
    "Bacteria": {"NMDS_stress_1": results["Bacteria"]["nmds"]["stress"], "NMDS_iterations": results["Bacteria"]["nmds"]["n_iter"], **results["Bacteria"]["rda"]["model_stats"].iloc[0].to_dict()},
    "Archaea": {"NMDS_stress_1": results["Archaea"]["nmds"]["stress"], "NMDS_iterations": results["Archaea"]["nmds"]["n_iter"], **results["Archaea"]["rda"]["model_stats"].iloc[0].to_dict()},
  }
  (audit_root / "validation/ordination_execution_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
  print(json.dumps(summary, indent=2, default=str))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
