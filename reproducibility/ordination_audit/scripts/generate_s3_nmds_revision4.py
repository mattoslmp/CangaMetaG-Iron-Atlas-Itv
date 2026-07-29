#!/usr/bin/env python3
"""Regenerate Supplementary Figure 3 with true non-metric MDS.

The script reads the packaged CDS abundance table, retains all 20 samples,
converts each sample to relative proportions, applies a square-root transform,
calculates Bray-Curtis dissimilarities and fits two-dimensional non-metric MDS
with normalized Stress-1. No rendered image is edited after generation.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from scipy.stats import spearmanr



def repelled_point_labels(ax, frame, fontsize=12.0):
  x = frame["NMDS1"].to_numpy(float); y = frame["NMDS2"].to_numpy(float)
  xmin, xmax = ax.get_xlim(); ymin, ymax = ax.get_ylim()
  xr = xmax - xmin; yr = ymax - ymin; center_x = float(np.median(x))
  min_gap = max(yr * 0.047, 1e-8)
  for side in (-1, 1):
    idx = np.where(x < center_x)[0] if side < 0 else np.where(x >= center_x)[0]
    if len(idx) == 0: continue
    ordered = idx[np.argsort(y[idx])]
    target_y=[]; previous=ymin + yr*0.06 - min_gap
    for i in ordered:
      value=float(np.clip(y[i], ymin+yr*0.06, ymax-yr*0.06))
      value=max(value, previous+min_gap); target_y.append(value); previous=value
    overflow=target_y[-1]-(ymax-yr*0.06)
    if overflow>0: target_y=[v-overflow for v in target_y]
    label_x=xmin+xr*0.035 if side<0 else xmax-xr*0.035
    for i,ly in zip(ordered,target_y):
      ax.annotate(str(frame.iloc[i]["Sample"]), xy=(x[i],y[i]), xytext=(label_x,ly), textcoords="data",
        ha="left" if side<0 else "right", va="center", fontsize=fontsize, fontweight="bold", color="black",
        annotation_clip=True, arrowprops=dict(arrowstyle="-", color="#606060", lw=0.7, alpha=0.78),
        bbox=dict(boxstyle="round,pad=0.10", fc="white", ec="none", alpha=0.84), zorder=7)

def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[2])
  parser.add_argument("--article-root", type=Path)
  args = parser.parse_args()
  root = args.base_dir.resolve()
  import sys
  sys.path.insert(0, str(root))
  from src.publication_ordination import (
    SAMPLE_MAP, SAMPLE_ORDER, SEED, N_PERMUTATIONS,
    _new_nonmetric_mds, _orient_axes, permanova, betadisper_test,
  )

  data = root / "data"
  out = root / "outputs/final_publication_figures"
  derived = data / "final_publication_derived"
  audit = root / "reproducibility/ordination_reproducibility"
  for directory in (out, derived, audit / "output", audit / "tables", audit / "figures", audit / "validation"):
    directory.mkdir(parents=True, exist_ok=True)

  otu = pd.read_csv(data / "resultado.cds.otu.tab", sep="\t", index_col=0)
  otu.columns = [SAMPLE_MAP.get(str(c).split("_")[0].strip("."), str(c).split("_")[0].strip(".")) for c in otu.columns]
  samples = [s for s in SAMPLE_ORDER if s in otu.columns]
  if len(samples) != 20:
    raise RuntimeError(f"Expected 20 CDS samples; found {len(samples)}: {samples}")
  x = otu[samples].T.apply(pd.to_numeric, errors="coerce").fillna(0.0)
  rel = x.div(x.sum(axis=1).replace(0, np.nan), axis=0).fillna(0.0)
  transformed = np.sqrt(rel)
  distance = squareform(pdist(transformed.to_numpy(float), metric="braycurtis"))
  distance = np.nan_to_num(distance, nan=0.0, posinf=1.0, neginf=0.0)
  model = _new_nonmetric_mds(random_state=SEED, n_init=20, max_iter=1000)
  coords = _orient_axes(model.fit_transform(distance))
  scores = pd.DataFrame(coords, columns=["NMDS1", "NMDS2"])
  scores["Sample"] = samples
  scores["Lake"] = scores["Sample"].str.split(".").str[0]
  scores["Season"] = np.where(scores["Sample"].str.endswith(".D"), "Dry", "Rainy")
  scores["LakeSeason"] = scores["Lake"] + "-" + scores["Season"].str[0]
  ord_dist = squareform(pdist(coords, metric="euclidean"))
  upper = np.triu_indices_from(distance, k=1)
  rho = float(spearmanr(distance[upper], ord_dist[upper]).statistic)

  tests = []
  for factor in ("Lake", "Season", "LakeSeason"):
    pm = permanova(distance, scores[factor], permutations=N_PERMUTATIONS, seed=SEED)
    bd = betadisper_test(distance, scores[factor], permutations=N_PERMUTATIONS, seed=SEED)
    tests.append({"analysis": "CDS_all_OTUs", "factor": factor,
      **{f"PERMANOVA_{k}": v for k, v in pm.items()},
      **{f"dispersion_{k}": v for k, v in bd.items()}})
  test_df = pd.DataFrame(tests)
  sample_audit = scores[["Sample", "Lake", "Season", "NMDS1", "NMDS2"]].copy()
  sample_audit.insert(1, "present_in_abundance", True)
  sample_audit.insert(2, "included_in_NMDS", True)
  sample_audit["exclusion_reason"] = ""
  sample_audit["point_drawn"] = True

  scores.to_csv(derived / "CDS_NMDS_coordinates.csv", index=False)
  transformed.to_csv(audit / "intermediate/CDS_square_root_relative_abundance.csv")
  pd.DataFrame(distance, index=samples, columns=samples).to_csv(audit / "intermediate/CDS_Bray_Curtis_distance.csv")
  scores.to_csv(audit / "output/CDS_true_nonmetric_NMDS_scores.csv", index=False)
  test_df.to_csv(audit / "tables/CDS_NMDS_PERMANOVA_and_dispersion_tests.csv", index=False)
  sample_audit.to_csv(audit / "tables/CDS_NMDS_sample_audit.csv", index=False)
  parameters = {
    "analysis": "Supplementary Figure 3 CDS-based NMDS",
    "raw_samples": len(samples), "included_samples": len(samples), "excluded_samples": 0,
    "transformation": "square root of sample-wise relative CDS proportions",
    "dissimilarity": "Bray-Curtis", "dimensions": 2, "nonmetric": True,
    "n_init": 20, "max_iter": 1000, "seed": SEED, "normalized_stress": True,
    "stress_1": float(model.stress_), "iterations": int(getattr(model, "n_iter_", -1)),
    "converged": bool(getattr(model, "n_iter_", 1000) < 1000),
    "distance_rank_correlation": rho,
  }
  (derived / "CDS_NMDS_parameters.json").write_text(json.dumps(parameters, indent=2), encoding="utf-8")
  (audit / "output/CDS_true_nonmetric_NMDS_parameters.json").write_text(json.dumps(parameters, indent=2), encoding="utf-8")

  colours = {"AM": "#2E86AB", "TIA": "#F18F01", "TI": "#6A994E", "VI": "#9B5DE5"}
  markers = {"Dry": "o", "Rainy": "s"}
  fig, ax = plt.subplots(figsize=(12.2, 9.1))
  for lake in ("AM", "TIA", "TI", "VI"):
    for season in ("Dry", "Rainy"):
      d = scores[(scores.Lake == lake) & (scores.Season == season)]
      ax.scatter(d.NMDS1, d.NMDS2, s=145, marker=markers[season], color=colours[lake],
                 edgecolor="black", linewidth=1.0, zorder=3)
  handles = [Line2D([0], [0], marker="o", color="w", markerfacecolor=colours[g], markeredgecolor="black", label=g, markersize=11) for g in ("AM", "TIA", "TI", "VI")]
  handles += [Line2D([0], [0], marker=markers[s], color="black", linestyle="None", label=s, markersize=10) for s in ("Dry", "Rainy")]
  ax.legend(handles=handles, bbox_to_anchor=(1.01, 1.0), loc="upper left", frameon=False, fontsize=12, title="Lake / season", title_fontsize=13)
  xr=float(np.ptp(scores["NMDS1"])); yr=float(np.ptp(scores["NMDS2"]))
  ax.set_xlim(float(scores["NMDS1"].min()-max(xr*0.32,0.04)), float(scores["NMDS1"].max()+max(xr*0.32,0.04)))
  ax.set_ylim(float(scores["NMDS2"].min()-max(yr*0.20,0.04)), float(scores["NMDS2"].max()+max(yr*0.20,0.04)))
  repelled_point_labels(ax, scores, fontsize=11.8)
  ax.axhline(0, color="grey", lw=0.7); ax.axvline(0, color="grey", lw=0.7)
  ax.set_xlabel("NMDS1", fontsize=15, fontweight="bold")
  ax.set_ylabel("NMDS2", fontsize=15, fontweight="bold")
  ax.tick_params(labelsize=12)
  ax.set_title(f"CDS-based Bray-Curtis NMDS (normalized Stress-1 = {model.stress_:.3f})", fontsize=17, fontweight="bold", pad=12)
  fig.subplots_adjust(left=0.10, right=0.78, bottom=0.11, top=0.91)
  stem = "SupplementaryFigure3_NMDS_CDS_taxonomy"
  for ext in ("png", "pdf", "svg"):
    kwargs = {"dpi": 300} if ext == "png" else {}
    fig.savefig(out / f"{stem}.{ext}", bbox_inches="tight", facecolor="white", **kwargs)
  plt.close(fig)
  for ext in ("png", "pdf", "svg"):
    shutil.copy2(out / f"{stem}.{ext}", audit / "figures" / f"{stem}.{ext}")
    if args.article_root:
      art = args.article_root.resolve() / "03_Supplementary_Figures"
      art.mkdir(parents=True, exist_ok=True)
      shutil.copy2(out / f"{stem}.{ext}", art / f"{stem}.{ext}")
  print(json.dumps(parameters, indent=2))
  return 0

if __name__ == "__main__":
  raise SystemExit(main())
