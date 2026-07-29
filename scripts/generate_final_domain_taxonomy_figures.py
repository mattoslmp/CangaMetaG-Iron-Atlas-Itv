#!/usr/bin/env python3
"""Generate publication-ready Bacteria/Archaea taxonomy figures.

This script is the canonical source for Main Figures 2-5 and the combined
Supplementary Figure 17. It uses only packaged relative paths and writes
source tables for every panel.
"""
from __future__ import annotations

from pathlib import Path
import json
import math
import re
import textwrap

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from matplotlib.colors import to_hex
from scipy.spatial.distance import pdist, squareform
from sklearn.manifold import MDS
from PIL import Image
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.taxonomy_palette import build_palette, load_palette, save_palette
from src.publication_ordination import compute_nmds as canonical_compute_nmds, compute_rda as canonical_compute_rda

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
OUT = BASE / "outputs" / "final_publication_figures"
DER = DATA / "final_publication_derived"
OUT.mkdir(parents=True, exist_ok=True)
DER.mkdir(parents=True, exist_ok=True)

SAMPLE_MAP = {
  "Ga0540489": "AM.P1.D", "Ga0541010": "AM.P1.R", "Ga0541011": "AM.P2.D", "Ga0541012": "AM.P2.R",
  "Ga0541013": "TIA.P1.D", "Ga0541014": "TIA.P1.R", "Ga0541015": "TIA.P2.D", "Ga0541016": "TIA.P2.R",
  "Ga0541017": "TI.P1.D", "Ga0541018": "TI.P1.R", "Ga0541019": "TI.P2.D", "Ga0541020": "TI.P2.R",
  "Ga0541021": "TI.P3.D", "Ga0541022": "TI.P3.R", "Ga0541023": "TI.P4.D", "Ga0541024": "TI.P4.R",
  "Ga0541025": "VI.P1.D", "Ga0541026": "VI.P1.R", "Ga0541027": "VI.P2.D", "Ga0541028": "VI.P2.R",
}
SAMPLE_ORDER = [
  "AM.P1.D", "AM.P1.R", "AM.P2.D", "AM.P2.R",
  "TIA.P1.D", "TIA.P1.R", "TIA.P2.D", "TIA.P2.R",
  "TI.P1.D", "TI.P1.R", "TI.P2.D", "TI.P2.R", "TI.P3.D", "TI.P3.R", "TI.P4.D", "TI.P4.R",
  "VI.P1.D", "VI.P1.R", "VI.P2.D", "VI.P2.R",
]
LAKE_COLORS = {"AM": "#0072B2", "TIA": "#E69F00", "TI": "#009E73", "VI": "#CC79A7"}
SEASON_MARKERS = {"Dry": "o", "Rainy": "s"}

# Vivid, high-contrast categorical sequence inspired by the current individual-sample barplot.
# It is centralized here and exported to data/taxonomy_palette.json for app-wide reuse.
BASE_COLORS = [
  "#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD", "#8C564B", "#E377C2", "#17BECF",
  "#BCBD22", "#393B79", "#637939", "#8C6D31", "#843C39", "#7B4173", "#3182BD", "#E6550D",
  "#31A354", "#756BB1", "#636363", "#6BAED6", "#FD8D3C", "#74C476", "#9E9AC8", "#969696",
  "#9C9EDE", "#CEDB9C", "#E7BA52", "#E7969C", "#DE9ED6", "#A55194", "#6B6ECF", "#B5CF6B",
  "#E7CB94", "#AD494A", "#D6616B", "#7F7F7F", "#1B9E77", "#D95F02", "#7570B3", "#E7298A",
  "#66A61E", "#E6AB02", "#A6761D", "#1F9E89", "#F46D43", "#3288BD", "#5E4FA2", "#FEE08B",
]
SPECIAL_COLORS = {
  "Chloroflexi": "#9467BD",
  "Candidatus Rokubacteria": "#17BECF",
  "Other taxa": "#D4A373",
  "Other genera": "#8D6A9F",
  "Unclassified": "#5B7C99",
  "Unclassified taxa": "#4C6E91",
  "Unassigned": "#7B5E57",
}


def clean_sample_name(col: str) -> str:
  token = str(col).split("_")[0].strip()
  return SAMPLE_MAP.get(token, token)


def load_cds() -> tuple[pd.DataFrame, pd.DataFrame]:
  otu = pd.read_csv(DATA / "resultado.cds.otu.tab", sep="\t", index_col=0)
  tax = pd.read_csv(DATA / "resultado.cds.tax.tab", sep="\t", index_col=0)
  otu.columns = [clean_sample_name(c) for c in otu.columns]
  otu = otu.reindex(columns=[c for c in SAMPLE_ORDER if c in otu.columns])
  otu = otu.apply(pd.to_numeric, errors="coerce").fillna(0)
  tax.columns = [str(c).strip() for c in tax.columns]
  for c in tax.columns:
    tax[c] = tax[c].fillna("Unclassified").astype(str).str.strip().replace({"": "Unclassified", "NA": "Unclassified", "nan": "Unclassified", "None": "Unclassified"})
  return otu, tax


def taxon_color_map(taxa: list[str], existing: dict[str, str] | None = None) -> dict[str, str]:
  mapping = dict(existing or {})
  used = set(mapping.values())
  cursor = 0
  for taxon in taxa:
    if taxon in mapping:
      continue
    if taxon in SPECIAL_COLORS:
      mapping[taxon] = SPECIAL_COLORS[taxon]
      used.add(mapping[taxon])
      continue
    while cursor < len(BASE_COLORS) and BASE_COLORS[cursor] in used:
      cursor += 1
    if cursor < len(BASE_COLORS):
      mapping[taxon] = BASE_COLORS[cursor]
      used.add(BASE_COLORS[cursor])
      cursor += 1
    else:
      # deterministic fallback if more taxa are ever requested
      hue = ((len(mapping) * 0.61803398875) % 1.0)
      rgb = plt.get_cmap("hsv")(hue)
      color = to_hex(rgb, keep_alpha=False)
      while color in used:
        hue = (hue + 0.071) % 1.0
        color = to_hex(plt.get_cmap("hsv")(hue), keep_alpha=False)
      mapping[taxon] = color
      used.add(color)
  # mandatory distinctness check
  if mapping.get("Chloroflexi") == mapping.get("Candidatus Rokubacteria"):
    mapping["Candidatus Rokubacteria"] = "#17BECF"
  return mapping


def aggregate_domain(otu: pd.DataFrame, tax: pd.DataFrame, domain: str, level: str, top_n: int) -> pd.DataFrame:
  shared = otu.index.intersection(tax.index)
  domain_mask = tax.loc[shared, "Domain"].astype(str).str.casefold().eq(domain.casefold())
  ids = shared[domain_mask.to_numpy()]
  labels = tax.loc[ids, level].fillna("Unclassified").astype(str).str.strip()
  labels = labels.replace({"": "Unclassified", "NA": "Unclassified", "nan": "Unclassified", "Unknown": "Unclassified"})
  labels = labels.map(lambda x: "Unclassified" if str(x).strip().casefold() in {"", "unknown", "na", "nan", "none", "undefined", "null"} else str(x).strip())
  mat = otu.loc[ids].copy()
  mat["taxon"] = labels
  agg = mat.groupby("taxon", dropna=False).sum(numeric_only=True)
  rel = agg.div(agg.sum(axis=0).replace(0, np.nan), axis=1).fillna(0) * 100.0
  top = rel.sum(axis=1).sort_values(ascending=False).head(top_n).index
  out = rel.loc[top].copy()
  other = rel.drop(index=top, errors="ignore").sum(axis=0)
  label = "Other taxa" if level == "Phylum" else "Other genera"
  if float(other.sum()) > 0:
    out.loc[label] = other
  return out


def save_all(fig: plt.Figure, stem: str, dpi: int = 350) -> None:
  fig.savefig(OUT / f"{stem}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
  fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
  fig.savefig(OUT / f"{stem}.svg", bbox_inches="tight", facecolor="white")
  plt.close(fig)


def phylum_figure(rel: pd.DataFrame, domain: str, stem: str, palette: dict[str, str]) -> None:
  taxa = list(rel.index)
  fig, axes = plt.subplots(1, 2, figsize=(17.5, 8.8), sharex=True)
  for ax, suffix, panel, label in zip(axes, ["D", "R"], ["A", "B"], ["Dry season", "Rainy season"]):
    samples = [s for s in SAMPLE_ORDER if s.endswith(f".{suffix}") and s in rel.columns]
    y = np.arange(len(samples))
    left = np.zeros(len(samples), dtype=float)
    for taxon in taxa:
      vals = rel.loc[taxon, samples].to_numpy(float)
      ax.barh(y, vals, left=left, color=palette[taxon], edgecolor="white", linewidth=0.25)
      left += vals
    ax.set_yticks(y, samples, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Relative abundance (%)", fontsize=12, fontweight="bold")
    ax.set_title(f"{panel}  {label}", loc="left", fontsize=14, fontweight="bold")
    ax.tick_params(axis="both", labelsize=10)
    ax.grid(False)
  axes[0].set_ylabel("CDS-classified sediment sample", fontsize=12, fontweight="bold")
  handles = [Patch(facecolor=palette[t], edgecolor="none", label=t) for t in taxa]
  fig.legend(handles=handles, title="Phylum", loc="center left", bbox_to_anchor=(0.82, 0.5), frameon=False, fontsize=9, title_fontsize=10)
  fig.suptitle(f"{domain} phylum-level taxonomic profiles", fontsize=18, fontweight="bold", y=0.985)
  fig.subplots_adjust(left=0.09, right=0.80, bottom=0.10, top=0.90, wspace=0.28)
  save_all(fig, stem)
  rel.to_csv(DER / f"{stem}_source.csv")


def domain_genus_matrix(otu: pd.DataFrame, tax: pd.DataFrame, domain: str, top_n: int = 18) -> pd.DataFrame:
  return aggregate_domain(otu, tax, domain, "Genus", top_n)


def nmds_scores(rel: pd.DataFrame) -> tuple[pd.DataFrame, float]:
  """Compatibility wrapper: article and app use src.publication_ordination."""
  result = canonical_compute_nmds(rel, domain="Taxonomy")
  scores = result["scores"].copy()
  return scores, float(result["stress"])


def rda_domain(rel: pd.DataFrame, domain: str) -> dict:
  """Compatibility wrapper: article and app use src.publication_ordination."""
  result = canonical_compute_rda(BASE, rel, domain)
  result["scores"].to_csv(DER / f"Figure_{domain}_genus_RDA_site_scores.csv")
  result["vectors"].to_csv(DER / f"Figure_{domain}_genus_RDA_environment_vectors.csv")
  result["taxon_vectors_all"].to_csv(DER / f"Figure_{domain}_genus_RDA_all_genus_vectors.csv")
  result["taxon_vectors"].to_csv(DER / f"Figure_{domain}_genus_RDA_representative_genus_vectors.csv")
  return result


def draw_stacked_panel(ax, rel: pd.DataFrame, samples: list[str], palette: dict[str, str], panel: str, title: str) -> None:
  taxa = list(rel.index)
  y = np.arange(len(samples))
  left = np.zeros(len(samples), dtype=float)
  for taxon in taxa:
    vals = rel.loc[taxon, samples].to_numpy(float)
    ax.barh(y, vals, left=left, color=palette[taxon], edgecolor="white", linewidth=0.20)
    left += vals
  ax.set_yticks(y, samples, fontsize=8.5)
  ax.invert_yaxis()
  ax.set_xlim(0, 100)
  ax.set_xlabel("Relative abundance (%)", fontsize=10, fontweight="bold")
  ax.set_title(f"{panel}  {title}", loc="left", fontsize=13, fontweight="bold")
  ax.grid(False)


def genus_multipanel(rel: pd.DataFrame, domain: str, stem: str, palette: dict[str, str]) -> dict:
  scores, stress = nmds_scores(rel)
  rda = rda_domain(rel, domain)
  fig = plt.figure(figsize=(20.5, 14.5))
  gs = fig.add_gridspec(2, 2, height_ratios=[1.08, 1.0], width_ratios=[1.0, 1.0], hspace=0.30, wspace=0.26)
  axA = fig.add_subplot(gs[0, 0])
  axB = fig.add_subplot(gs[0, 1])
  axC = fig.add_subplot(gs[1, 0])
  axD = fig.add_subplot(gs[1, 1])
  dry = [s for s in SAMPLE_ORDER if s.endswith(".D") and s in rel.columns]
  rainy = [s for s in SAMPLE_ORDER if s.endswith(".R") and s in rel.columns]
  draw_stacked_panel(axA, rel, dry, palette, "A", "Dry-season genus profiles")
  draw_stacked_panel(axB, rel, rainy, palette, "B", "Rainy-season genus profiles")

  for lake in ["AM", "TIA", "TI", "VI"]:
    for season in ["Dry", "Rainy"]:
      d = scores[(scores["Lake"] == lake) & (scores["Season"] == season)]
      axC.scatter(d["NMDS1"], d["NMDS2"], s=75, color=LAKE_COLORS[lake], marker=SEASON_MARKERS[season], edgecolor="black", linewidth=0.6, zorder=3)
      for _, row in d.iterrows():
        axC.annotate(row["Sample"], (row["NMDS1"], row["NMDS2"]), xytext=(4, 4), textcoords="offset points", fontsize=7.5, annotation_clip=False)
  axC.axhline(0, color="#AAAAAA", lw=0.6)
  axC.axvline(0, color="#AAAAAA", lw=0.6)
  axC.set_xlabel("NMDS1", fontsize=10, fontweight="bold")
  axC.set_ylabel("NMDS2", fontsize=10, fontweight="bold")
  axC.set_title(f"C  Bray-Curtis NMDS (stress = {stress:.3f})", loc="left", fontsize=13, fontweight="bold")
  axC.margins(x=0.16, y=0.16)

  sc, vec, tax_vec = rda["scores"], rda["vectors"], rda["taxon_vectors"]
  for lake, d in sc.groupby("Lake"):
    axD.scatter(d["RDA1"], d["RDA2"], s=85, color=LAKE_COLORS.get(lake, "#777777"), edgecolor="black", linewidth=0.6, zorder=4)
    for idx, row in d.iterrows():
      axD.annotate(idx, (row["RDA1"], row["RDA2"]), xytext=(4, 4), textcoords="offset points", fontsize=7.5, annotation_clip=False, zorder=6)

  site_extent = max(float(np.max(np.abs(sc[["RDA1", "RDA2"]].to_numpy()))), 1e-6)
  env_scale = site_extent * 0.82
  genus_scale = site_extent * 0.70

  # Environmental vectors: solid dark-grey arrows.
  for name, row in vec.iterrows():
    x, y = row["RDA1"] * env_scale, row["RDA2"] * env_scale
    axD.annotate(
      "", xy=(x, y), xytext=(0, 0),
      arrowprops=dict(arrowstyle="-|>", color="#3F3F46", lw=1.25, alpha=0.88, shrinkA=0, shrinkB=0),
      zorder=2,
    )
    axD.text(
      x * 1.12, y * 1.12, str(name), fontsize=7.8, fontweight="bold", color="#27272A",
      ha="center", va="center", zorder=7,
      bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none", alpha=0.72),
    )

  # Representative genus vectors: dashed arrows coloured with the same
  # canonical taxonomy palette used in panels A/B and throughout the app.
  genus_items = []
  for name, row in tax_vec.iterrows():
    x, y = row["RDA1"] * genus_scale, row["RDA2"] * genus_scale
    colour = palette.get(str(name), "#111827")
    axD.annotate(
      "", xy=(x, y), xytext=(0, 0),
      arrowprops=dict(arrowstyle="-|>", color=colour, lw=1.45, linestyle="--", alpha=0.96, shrinkA=0, shrinkB=0),
      zorder=3,
    )
    genus_items.append({"name": str(name), "x": x, "y": y, "colour": colour})

  # Spread labels vertically within each side of the biplot. This keeps the
  # vector endpoints exact while avoiding label collisions in dense quadrants.
  label_positions = []
  min_gap = max(site_extent * 0.13, 0.008)
  for side in (-1, 1):
    items = [item for item in genus_items if (item["x"] < 0) == (side < 0)]
    items.sort(key=lambda item: item["y"] )
    previous = None
    for item in items:
      ly = item["y"] * 1.16
      if previous is not None and ly - previous < min_gap:
        ly = previous + min_gap
      previous = ly
      lx = item["x"] * 1.20 + side * site_extent * 0.035
      label_positions.append((item, lx, ly))
  for item, lx, ly in label_positions:
    ha = "left" if lx >= 0 else "right"
    axD.annotate(
      item["name"], xy=(item["x"], item["y"]), xytext=(lx, ly), textcoords="data",
      fontsize=7.2, fontweight="bold", color=item["colour"], ha=ha, va="center",
      annotation_clip=False, zorder=8,
      arrowprops=dict(arrowstyle="-", color=item["colour"], lw=0.55, alpha=0.65),
      bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none", alpha=0.82),
    )

  axD.axhline(0, color="#AAAAAA", lw=0.6)
  axD.axvline(0, color="#AAAAAA", lw=0.6)
  axD.set_xlabel(f"RDA1 ({rda['pct'][0]:.1f}% constrained variation)", fontsize=10, fontweight="bold")
  axD.set_ylabel(f"RDA2 ({rda['pct'][1]:.1f}% constrained variation)", fontsize=10, fontweight="bold")
  axD.set_title(f"D  RDA biplot (R² = {rda['r2']:.2f}; P = {rda['p']:.3f})", loc="left", fontsize=13, fontweight="bold")
  biplot_handles = [
    Line2D([0], [0], color="#3F3F46", lw=1.5, linestyle="-", label="Environmental variable"),
    Line2D([0], [0], color="#555555", lw=1.5, linestyle="--", label="Representative genus vector"),
  ]
  axD.legend(handles=biplot_handles, loc="lower right", frameon=False, fontsize=7.5)
  # Explicit limits include the text anchor positions; Matplotlib margins do
  # not account for annotations and previously clipped the lowest genus label.
  x_values = list(sc["RDA1"].astype(float)) + [0.0]
  y_values = list(sc["RDA2"].astype(float)) + [0.0]
  for _, row in vec.iterrows():
    x_values.append(float(row["RDA1"] * env_scale * 1.20))
    y_values.append(float(row["RDA2"] * env_scale * 1.20))
  for item, lx, ly in label_positions:
    x_values.extend([float(item["x"]), float(lx)])
    y_values.extend([float(item["y"]), float(ly)])
  xmin, xmax = min(x_values), max(x_values)
  ymin, ymax = min(y_values), max(y_values)
  xpad = max((xmax - xmin) * 0.12, site_extent * 0.20)
  ypad = max((ymax - ymin) * 0.14, site_extent * 0.20)
  axD.set_xlim(xmin - xpad, xmax + xpad)
  axD.set_ylim(ymin - ypad, ymax + ypad)

  taxa = list(rel.index)
  tax_handles = [Patch(facecolor=palette[t], edgecolor="none", label=t) for t in taxa]
  legend1 = fig.legend(handles=tax_handles, title="Genus", loc="lower center", bbox_to_anchor=(0.5, 0.015), ncol=min(7, max(3, math.ceil(len(taxa) / 3))), frameon=False, fontsize=8, title_fontsize=9)
  ord_handles = [Line2D([0], [0], marker="o", linestyle="None", markerfacecolor=LAKE_COLORS[l], markeredgecolor="black", label=l, markersize=7) for l in ["AM", "TIA", "TI", "VI"]]
  ord_handles += [Line2D([0], [0], marker=SEASON_MARKERS[s], linestyle="None", color="black", label=s, markersize=7) for s in ["Dry", "Rainy"]]
  axC.legend(handles=ord_handles, loc="upper left", bbox_to_anchor=(1.00, 1.0), frameon=False, fontsize=8, title="Lake / season")
  fig.suptitle(f"{domain} genus-level taxonomic profiles and ordination", fontsize=19, fontweight="bold", y=0.985)
  fig.subplots_adjust(left=0.07, right=0.93, top=0.92, bottom=0.15)
  save_all(fig, stem)
  rel.to_csv(DER / f"{stem}_source.csv")
  scores.to_csv(DER / f"{stem}_NMDS_scores.csv", index=False)
  pd.DataFrame([{"domain": domain, "NMDS_stress": stress, "RDA_R2": rda["r2"], "RDA_F": rda["F"], "RDA_p": rda["p"], "RDA_variables": "; ".join(rda["variables"]), "RDA_n": rda["n"]}]).to_csv(DER / f"{stem}_ordination_statistics.csv", index=False)
  return {"domain": domain, "stress": stress, "rda": rda}


def combine_supplementary_17() -> None:
  rda_png = OUT / "SupplementaryFigure17_RDA_CDS_genus_fiqui2_physicochemical.png"
  heat_png = OUT / "SupplementaryFigure18_fiqui2_physicochemical_heatmap.png"
  if not (rda_png.exists() and heat_png.exists()):
    return
  im1 = Image.open(rda_png).convert("RGB")
  im2 = Image.open(heat_png).convert("RGB")
  fig, axes = plt.subplots(1, 2, figsize=(18.5, 8.8), gridspec_kw={"width_ratios": [1.08, 1.0]})
  for ax, im, panel, title in zip(axes, [im1, im2], ["A", "B"], ["Genus-level RDA and physicochemistry", "Physicochemical row-z-score heatmap"]):
    ax.imshow(im)
    ax.axis("off")
    ax.set_title(f"{panel}  {title}", loc="left", fontsize=13, fontweight="bold", pad=10)
  fig.subplots_adjust(left=0.015, right=0.985, top=0.92, bottom=0.02, wspace=0.06)
  save_all(fig, "SupplementaryFigure17_RDA_and_physicochemical_heatmap")


def main() -> None:
  otu, tax = load_cds()
  ph_b = aggregate_domain(otu, tax, "Bacteria", "Phylum", 14)
  ph_a = aggregate_domain(otu, tax, "Archaea", "Phylum", 14)
  ge_b = domain_genus_matrix(otu, tax, "Bacteria", 18)
  ge_a = domain_genus_matrix(otu, tax, "Archaea", 18)
  all_taxa = list(dict.fromkeys(list(ph_b.index) + list(ph_a.index) + list(ge_b.index) + list(ge_a.index)))
  # Load and extend the one canonical palette shared with the app and all supplementary figures.
  palette = build_palette(all_taxa, load_palette(DATA / "taxonomy_palette.json"))
  save_palette(palette, DATA / "taxonomy_palette.json")
  if palette.get("Chloroflexi") == palette.get("Candidatus Rokubacteria"):
    raise RuntimeError("Chloroflexi and Candidatus Rokubacteria must have different colors")

  phylum_figure(ph_b, "Bacteria", "Figure2_taxonomic_phylum_bacteria_horizontal_CDS", palette)
  phylum_figure(ph_a, "Archaea", "Figure3_taxonomic_phylum_archaea_horizontal_CDS", palette)
  bres = genus_multipanel(ge_b, "Bacteria", "Figure4_taxonomic_bacteria_genus_profiles", palette)
  ares = genus_multipanel(ge_a, "Archaea", "Figure5_taxonomic_archaea_genus_profiles", palette)
  combine_supplementary_17()

  report = {
    "palette_file": "data/taxonomy_palette.json",
    "chloroflexi": palette.get("Chloroflexi"),
    "candidatus_rokubacteria": palette.get("Candidatus Rokubacteria"),
    "figures": [
      "Figure2_taxonomic_phylum_bacteria_horizontal_CDS",
      "Figure3_taxonomic_phylum_archaea_horizontal_CDS",
      "Figure4_taxonomic_bacteria_genus_profiles",
      "Figure5_taxonomic_archaea_genus_profiles",
      "SupplementaryFigure17_RDA_and_physicochemical_heatmap",
    ],
    "bacteria": {"phylum_taxa": len(ph_b), "genus_taxa": len(ge_b), "nmds_stress": bres["stress"], "rda_p": bres["rda"]["p"]},
    "archaea": {"phylum_taxa": len(ph_a), "genus_taxa": len(ge_a), "nmds_stress": ares["stress"], "rda_p": ares["rda"]["p"]},
  }
  (BASE / "reports").mkdir(exist_ok=True)
  (BASE / "reports" / "FINAL_DOMAIN_TAXONOMY_GENERATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
  print(json.dumps(report, indent=2))


if __name__ == "__main__":
  main()
