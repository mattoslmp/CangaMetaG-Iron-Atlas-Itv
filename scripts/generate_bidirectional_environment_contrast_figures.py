#!/usr/bin/env python3
"""Generate bidirectional Amazonian-vs-external KO contrast figures.

The analysis is descriptive and intended for cross-study context. For each marker,
counts are converted to within-sample relative abundance within the corresponding
marker panel (189 biogeochemical KOs or 131 curated iron-associated KOs). The
contrast is then calculated as:

  log2((mean Amazonian relative abundance + pseudocount) /
       (mean external relative abundance + pseudocount))

The pseudocount is one half of the smallest positive group mean in the analysed
panel. Positive values indicate a larger mean marker-panel relative abundance in
the 20 Amazonian lateritic-lake metagenomes; negative values indicate a larger
mean among the 67 external iron-rich records. Markers are retained for ranking
when detected in at least 20% of samples in the favoured group and the favoured
group mean is at least 0.005% of the marker panel.

This is not an inferential cross-study test because datasets differ in study
design, sequencing depth, processing, habitat and omics layer.
"""
from __future__ import annotations

import json
import re
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / "tables" / "Supplementary_table_8_final_restructured_filled.xlsx"
FIGDIR = ROOT / "outputs" / "final_publication_figures"
DERIVED = ROOT / "data" / "final_publication_derived"

LAKE_PATTERN = re.compile(r"^(AM|TIA|TI|VI)\.P\d+\.(D|R)$")


def _clean(text: object, width: int = 44) -> str:
  value = re.sub(r"\s+", " ", str(text or "").strip())
  value = value.replace("Carbon Fixation: ", "").replace("Nitrogen: ", "N: ")
  value = value.replace("Methanogenesis (methanol; acetate; methylamine; dimethylamine; trimethylamine; CO2)", "Methanogenesis: mixed substrates")
  value = value.replace("Oxygenic photosynthesis (Plants and Cyanobacteria)", "Oxygenic photosynthesis")
  if len(value) <= width:
    return value
  return value[: width - 1].rstrip() + "…"


def calculate_contrasts(sheet: str, id_col: str, pathway_col: str, desc_col: str) -> tuple[pd.DataFrame, dict]:
  df = pd.read_excel(TABLE, sheet_name=sheet)
  lake_cols = [c for c in df.columns if LAKE_PATTERN.match(str(c))]
  metadata_cols = [id_col, pathway_col, desc_col]
  external_cols = [c for c in df.columns if c not in metadata_cols and c not in lake_cols]
  values = df[lake_cols + external_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
  totals = values.sum(axis=0).replace(0, np.nan)
  relative = values.div(totals, axis=1).fillna(0.0)

  lake_mean = relative[lake_cols].mean(axis=1)
  external_mean = relative[external_cols].mean(axis=1)
  positive_means = pd.concat([lake_mean[lake_mean > 0], external_mean[external_mean > 0]])
  pseudocount = float(0.5 * positive_means.min()) if len(positive_means) else 1e-12

  out = df[metadata_cols].copy()
  out["amazonian_mean_relative_abundance"] = lake_mean
  out["external_mean_relative_abundance"] = external_mean
  out["amazonian_mean_percent"] = lake_mean * 100.0
  out["external_mean_percent"] = external_mean * 100.0
  out["amazonian_detection_fraction"] = (values[lake_cols] > 0).mean(axis=1)
  out["external_detection_fraction"] = (values[external_cols] > 0).mean(axis=1)
  out["log2_amazonian_over_external"] = np.log2((lake_mean + pseudocount) / (external_mean + pseudocount))
  out["absolute_log2_contrast"] = out["log2_amazonian_over_external"].abs()
  out["favoured_group"] = np.where(out["log2_amazonian_over_external"] >= 0, "Amazonian lakes", "External iron-rich records")
  out["display_label"] = out[id_col].astype(str).str.strip() + " | " + out[pathway_col].map(_clean)
  out["comparison_method"] = "Within-sample marker-panel relative abundance; group means; descriptive log2 ratio"
  out["pseudocount_relative_abundance"] = pseudocount
  out["n_amazonian_samples"] = len(lake_cols)
  out["n_external_records"] = len(external_cols)

  meta = {
    "sheet": sheet,
    "marker_rows": int(len(out)),
    "amazonian_samples": len(lake_cols),
    "external_records": len(external_cols),
    "pseudocount_relative_abundance": pseudocount,
    "minimum_detection_fraction_in_favoured_group": 0.20,
    "minimum_favoured_group_mean_percent": 0.005,
  }
  return out, meta


def select_direction(df: pd.DataFrame, direction: str, n: int) -> pd.DataFrame:
  if direction == "amazonian":
    eligible = df[
      (df["log2_amazonian_over_external"] > 0)
      & (df["amazonian_detection_fraction"] >= 0.20)
      & (df["amazonian_mean_percent"] >= 0.005)
    ].copy()
    return eligible.nlargest(n, "log2_amazonian_over_external").sort_values("log2_amazonian_over_external")
  eligible = df[
    (df["log2_amazonian_over_external"] < 0)
    & (df["external_detection_fraction"] >= 0.20)
    & (df["external_mean_percent"] >= 0.005)
  ].copy()
  eligible["external_contrast_magnitude"] = -eligible["log2_amazonian_over_external"]
  return eligible.nlargest(n, "external_contrast_magnitude").sort_values("external_contrast_magnitude")


def _panel(ax, data: pd.DataFrame, magnitude_col: str, title: str, color: str, mean_a: str, mean_b: str) -> None:
  y = np.arange(len(data))
  vals = data[magnitude_col].to_numpy(float)
  ax.barh(y, vals, color=color, alpha=0.90, edgecolor="white", linewidth=0.5)
  labels = data["display_label"].tolist()
  ax.set_yticks(y)
  ax.set_yticklabels(labels, fontsize=7.8)
  ax.set_xlabel("Absolute descriptive log2 contrast", fontsize=9.5, fontweight="bold")
  ax.set_title(title, fontsize=12.5, fontweight="bold", pad=10)
  ax.grid(axis="x", color="#D1D5DB", linewidth=0.55, alpha=0.8)
  ax.spines[["top", "right", "left"]].set_visible(False)
  ax.tick_params(axis="y", length=0)
  ax.set_xlim(0, max(vals.max() * 1.08, 1.0))


def plot_bidirectional(df: pd.DataFrame, n: int, title: str, stem: str, figure_label: str) -> tuple[pd.DataFrame, pd.DataFrame]:
  amazonian = select_direction(df, "amazonian", n)
  external = select_direction(df, "external", n)
  height = max(8.0, n * 0.34 + 3.6)
  fig, axes = plt.subplots(1, 2, figsize=(18.5, height), constrained_layout=False)
  _panel(
    axes[0], amazonian, "log2_amazonian_over_external",
    "A  Higher in Amazonian lateritic lakes", "#2166AC", "Lakes", "External",
  )
  _panel(
    axes[1], external, "external_contrast_magnitude",
    "B  Higher in external iron-rich records", "#B35806", "Lakes", "External",
  )
  max_x = max(axes[0].get_xlim()[1], axes[1].get_xlim()[1])
  axes[0].set_xlim(0, max_x)
  axes[1].set_xlim(0, max_x)
  fig.suptitle(f"{figure_label}. {title}", fontsize=16, fontweight="bold", y=0.988)
  fig.text(
    0.5, 0.012,
    "Counts were converted to within-sample marker-panel relative abundance before averaging the 20 Amazonian and 67 external records. "
    "Bars rank the largest directional log2 mean ratios after prevalence and abundance filters. Cross-study descriptive comparison; not an inferential significance test.",
    ha="center", va="bottom", fontsize=8.4, wrap=True,
  )
  fig.subplots_adjust(left=0.23, right=0.985, top=0.91, bottom=0.085, wspace=0.52)
  for ext in ("png", "svg", "pdf"):
    kwargs = {"dpi": 450} if ext == "png" else {}
    fig.savefig(FIGDIR / f"{stem}.{ext}", bbox_inches="tight", facecolor="white", **kwargs)
  plt.close(fig)
  return amazonian, external


def export_source(full: pd.DataFrame, amazonian: pd.DataFrame, external: pd.DataFrame, prefix: str) -> None:
  full.to_csv(DERIVED / f"{prefix}_complete_contrast_table.csv", index=False)
  amazonian.assign(panel="Higher in Amazonian lakes").to_csv(DERIVED / f"{prefix}_amazonian_higher_selected.csv", index=False)
  external.assign(panel="Higher in external records").to_csv(DERIVED / f"{prefix}_external_higher_selected.csv", index=False)
  pd.concat([
    amazonian.assign(panel="Higher in Amazonian lakes"),
    external.assign(panel="Higher in external records"),
  ], ignore_index=True).to_csv(DERIVED / f"{prefix}_figure_source.csv", index=False)


def main() -> None:
  FIGDIR.mkdir(parents=True, exist_ok=True)
  DERIVED.mkdir(parents=True, exist_ok=True)

  all_ko, all_meta = calculate_contrasts("ST8 — all KO biomarkers", "KO", "Metabolism", "KO description")
  iron, iron_meta = calculate_contrasts("ST8- Iron metabolism KO -marker", "Function Id", "Biologic Role", "Function Name")

  a12, e12 = plot_bidirectional(
    all_ko, 12,
    "Biogeochemical KOs with the strongest directional contrast",
    "SupplementaryFigure68_biogeochemical_KO_directional_contrast",
    "Supplementary Figure 68",
  )
  ia12, ie12 = plot_bidirectional(
    iron, 12,
    "Iron-associated KOs with the strongest directional contrast",
    "SupplementaryFigure69_iron_KO_directional_contrast",
    "Supplementary Figure 69",
  )
  a25, e25 = plot_bidirectional(
    all_ko, 25,
    "Expanded bidirectional contrast of biogeochemical KOs",
    "SupplementaryFigure6_ST8_selected_sediments_all_KO_zscore_proportional",
    "Supplementary Figure 6",
  )
  ia25, ie25 = plot_bidirectional(
    iron, 25,
    "Expanded bidirectional contrast of iron-associated KOs",
    "SupplementaryFigure7_ST8_iron_selected_zscore_proportional",
    "Supplementary Figure 7",
  )

  export_source(all_ko, a12, e12, "SupplementaryFigure68_bidirectional_all_KO")
  export_source(iron, ia12, ie12, "SupplementaryFigure69_bidirectional_iron_KO")
  export_source(all_ko, a25, e25, "SupplementaryFigure6_bidirectional_all_KO")
  export_source(iron, ia25, ie25, "SupplementaryFigure7_bidirectional_iron_KO")

  summary = {
    "method": "within-sample marker-panel relative abundance followed by descriptive log2 ratio of Amazonian and external group means",
    "all_KO": all_meta,
    "iron_KO": iron_meta,
    "directional_contrast_rows_per_direction": 12,
    "supplementary_figure_rows_per_direction": 25,
    "all_KO_top_amazonian": a12[["KO", "Metabolism", "log2_amazonian_over_external"]].to_dict("records"),
    "all_KO_top_external": e12[["KO", "Metabolism", "log2_amazonian_over_external"]].to_dict("records"),
    "iron_top_amazonian": ia12[["Function Id", "Biologic Role", "log2_amazonian_over_external"]].to_dict("records"),
    "iron_top_external": ie12[["Function Id", "Biologic Role", "log2_amazonian_over_external"]].to_dict("records"),
    "interpretation": "descriptive cross-study context; not inferential significance",
  }
  (DERIVED / "Bidirectional_environment_contrast_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
  print(json.dumps(summary, indent=2))


if __name__ == "__main__":
  main()
