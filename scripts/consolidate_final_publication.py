#!/usr/bin/env python3
"""Regenerate the canonical article/app figures from packaged source tables.

Inputs
------
- data/resultado.cds.otu.tab
- data/resultado.cds.tax.tab
- data/Top6-members-LFC_gmpr.txt
- data/Supplementary_table_5-Differential-abundance-pathways-KOs.xlsx
- data/Supplementary_table_7-MAGS-Quality-Genome_Lineage-Classification.xlsx
- data/Supplementary_table_8_final_restructured_filled.xlsx
- data/fiqui2.xlsx

Outputs
-------
All canonical figures are exported to outputs/final_publication_figures as PNG,
SVG and PDF whenever the graphic backend supports those formats. Derived source
CSVs are written to data/final_publication_derived.

Run
---
python scripts/consolidate_final_publication.py
"""
from __future__ import annotations

from pathlib import Path
import math
import re
import textwrap
import warnings

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon, Ellipse, FancyArrowPatch
from matplotlib.lines import Line2D
from sklearn.manifold import MDS
from scipy.spatial.distance import pdist, squareform
from scipy.stats import entropy

warnings.filterwarnings("ignore", category=UserWarning)

BASE = Path(__file__).resolve().parents[1]
DATA = BASE / "data"
OUT = BASE / "outputs" / "final_publication_figures"
DERIVED = DATA / "final_publication_derived"
OUT.mkdir(parents=True, exist_ok=True)
DERIVED.mkdir(parents=True, exist_ok=True)

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
LAKE_COLORS = {"AM": "#2E86AB", "TIA": "#F18F01", "TI": "#6A994E", "VI": "#9B5DE5"}
DIRECTION_COLORS = {"Up": "#1565C0", "Down": "#C62828"}


def savefig(fig: plt.Figure, stem: str, dpi: int = 300) -> None:
  fig.savefig(OUT / f"{stem}.png", dpi=dpi, bbox_inches="tight", facecolor="white")
  fig.savefig(OUT / f"{stem}.svg", bbox_inches="tight", facecolor="white")
  fig.savefig(OUT / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
  plt.close(fig)


def unique_colors(n: int) -> list:
  if n <= 20:
    cmap = plt.get_cmap("tab20", n)
  else:
    cmap = plt.get_cmap("turbo", n)
  return [cmap(i) for i in range(n)]


def clean_sample_name(col: str) -> str:
  token = str(col).split("_")[0]
  return SAMPLE_MAP.get(token, token)


def load_cds() -> tuple[pd.DataFrame, pd.DataFrame]:
  otu = pd.read_csv(DATA / "resultado.cds.otu.tab", sep="\t", index_col=0)
  otu.columns = [clean_sample_name(c) for c in otu.columns]
  otu = otu.reindex(columns=[c for c in SAMPLE_ORDER if c in otu.columns])
  otu = otu.apply(pd.to_numeric, errors="coerce").fillna(0)
  tax = pd.read_csv(DATA / "resultado.cds.tax.tab", sep="\t", index_col=0)
  tax.columns = [str(c).strip() for c in tax.columns]
  for c in tax.columns:
    tax[c] = tax[c].astype(str).str.strip().replace({"nan": "Unclassified", "NA": "Unclassified", "": "Unclassified"})
  return otu, tax


def aggregate_taxonomy(otu: pd.DataFrame, tax: pd.DataFrame, level: str, top_n: int) -> pd.DataFrame:
  shared = otu.index.intersection(tax.index)
  labels = tax.loc[shared, level].fillna("Unclassified").astype(str).str.strip()
  labels = labels.replace({"": "Unclassified", "NA": "Unclassified", "nan": "Unclassified", "Unknown": "Unclassified"})
  classified = ~labels.str.lower().isin({"unclassified", "unknown", "na", "nan", "none"})
  shared = shared[classified.to_numpy()]
  labels = labels.loc[shared]
  mat = otu.loc[shared].copy()
  mat["taxon"] = labels
  agg = mat.groupby("taxon", dropna=False).sum(numeric_only=True)
  rel = agg.div(agg.sum(axis=0).replace(0, np.nan), axis=1).fillna(0) * 100
  top = rel.sum(axis=1).nlargest(top_n).index
  out = rel.loc[top].copy()
  other = rel.drop(index=top, errors="ignore").sum(axis=0)
  if float(other.sum()) > 0:
    out.loc["Other taxa"] = other
  return out


def horizontal_taxonomy_figure(rel: pd.DataFrame, level: str, stem: str) -> None:
  taxa = list(rel.index)
  cols = unique_colors(len(taxa))
  color_map = dict(zip(taxa, cols))
  fig, axes = plt.subplots(1, 2, figsize=(17, 9), sharex=True)
  for ax, season, panel in zip(axes, ["D", "R"], ["A", "B"]):
    samples = [s for s in SAMPLE_ORDER if s.endswith(f".{season}") and s in rel.columns]
    y = np.arange(len(samples))
    left = np.zeros(len(samples))
    for taxon in taxa:
      vals = rel.loc[taxon, samples].to_numpy(float)
      ax.barh(y, vals, left=left, color=color_map[taxon], edgecolor="white", linewidth=0.25, label=taxon)
      left += vals
    ax.set_yticks(y, samples, fontsize=10, color="black")
    ax.invert_yaxis()
    ax.set_xlim(0, 100)
    ax.set_xlabel("Relative abundance (%)", fontsize=12, fontweight="bold", color="black")
    ax.set_title(f"{panel}  {'Dry' if season == 'D' else 'Rainy'} season", loc="left", fontsize=15, fontweight="bold")
    ax.grid(False)
    ax.tick_params(axis="x", colors="black")
  axes[0].set_ylabel("CDS-classified sediment sample", fontsize=12, fontweight="bold", color="black")
  handles = [plt.Rectangle((0, 0), 1, 1, color=color_map[t]) for t in taxa]
  fig.legend(handles, taxa, title=level, bbox_to_anchor=(1.005, 0.5), loc="center left", fontsize=9, title_fontsize=10, frameon=False)
  fig.suptitle(f"CDS-based {level.lower()} taxonomic profiles", fontsize=18, fontweight="bold", y=0.995)
  fig.subplots_adjust(right=0.79, bottom=0.09, wspace=0.28)
  savefig(fig, stem)
  rel.to_csv(DERIVED / f"{stem}_source.csv")


def alpha_nmds_figures(otu: pd.DataFrame) -> None:
  sample_counts = otu.T
  vals = []
  for sample, row in sample_counts.iterrows():
    x = row.to_numpy(float)
    x = x[x > 0]
    p = x / x.sum() if x.sum() else x
    vals.append({
      "Sample": sample,
      "Lake": sample.split(".")[0],
      "Season": "Dry" if sample.endswith(".D") else "Rainy",
      "Observed OTUs": len(x),
      "Shannon": float(entropy(p)) if len(p) else 0,
      "Simpson": float(1 - np.sum(p ** 2)) if len(p) else 0,
    })
  ad = pd.DataFrame(vals)
  ad.to_csv(DERIVED / "CDS_alpha_diversity_metrics.csv", index=False)
  fig, axes = plt.subplots(1, 3, figsize=(15, 5.8))
  metrics = ["Observed OTUs", "Shannon", "Simpson"]
  groups = ["AM", "TIA", "TI", "VI"]
  for ax, metric, panel in zip(axes, metrics, ["A", "B", "C"]):
    data = [ad.loc[ad.Lake.eq(g), metric].to_numpy() for g in groups]
    bp = ax.boxplot(data, patch_artist=True, labels=groups, widths=0.6)
    for patch, g in zip(bp["boxes"], groups):
      patch.set_facecolor(LAKE_COLORS[g]); patch.set_alpha(0.72)
    for i, g in enumerate(groups, start=1):
      yy = ad.loc[ad.Lake.eq(g), metric].to_numpy()
      jitter = np.linspace(-0.08, 0.08, len(yy)) if len(yy) > 1 else [0]
      ax.scatter(i + np.array(jitter), yy, s=34, edgecolor="black", linewidth=0.4, color=LAKE_COLORS[g], zorder=4)
    ax.set_title(f"{panel}  {metric}", loc="left", fontweight="bold")
    ax.set_xlabel("Lake"); ax.set_ylabel(metric); ax.grid(axis="y", alpha=0.2)
  fig.suptitle("Alpha diversity from CDS-classified OTU counts", fontsize=16, fontweight="bold")
  fig.tight_layout(rect=[0, 0.04, 1, 0.94])
  savefig(fig, "SupplementaryFigure2_alpha_diversity_CDS")

  # Bray-Curtis NMDS on relative abundance with square-root transform.
  X = sample_counts.to_numpy(float)
  X = X / np.maximum(X.sum(axis=1, keepdims=True), 1)
  X = np.sqrt(X)
  dist = squareform(pdist(X, metric="braycurtis"))
  
  try:
    model = MDS(n_components=2, metric_mds=False, metric="precomputed", random_state=42, n_init=20, init="random", max_iter=1000, normalized_stress=True)
  except TypeError:
    model = MDS(n_components=2, metric=False, dissimilarity="precomputed", random_state=42, n_init=20, max_iter=1000, normalized_stress=True)
  coords = model.fit_transform(dist)
  nmds = pd.DataFrame(coords, columns=["NMDS1", "NMDS2"])
  nmds["Sample"] = sample_counts.index
  nmds["Lake"] = nmds.Sample.str.split(".").str[0]
  nmds["Season"] = np.where(nmds.Sample.str.endswith(".D"), "Dry", "Rainy")
  nmds.to_csv(DERIVED / "CDS_NMDS_coordinates.csv", index=False)
  fig, ax = plt.subplots(figsize=(9.5, 7.2))
  markers = {"Dry": "o", "Rainy": "s"}
  for lake in groups:
    for season in ["Dry", "Rainy"]:
      d = nmds[(nmds.Lake == lake) & (nmds.Season == season)]
      ax.scatter(d.NMDS1, d.NMDS2, s=95, marker=markers[season], color=LAKE_COLORS[lake], edgecolor="black", linewidth=0.7)
      for _, r in d.iterrows():
        ax.annotate(r.Sample, (r.NMDS1, r.NMDS2), xytext=(5, 5), textcoords="offset points", fontsize=8, color="black")
  handles = [Line2D([0],[0], marker="o", color="w", markerfacecolor=LAKE_COLORS[g], markeredgecolor="black", label=g, markersize=9) for g in groups]
  handles += [Line2D([0],[0], marker=markers[s], color="black", linestyle="None", label=s, markersize=8) for s in markers]
  ax.legend(handles=handles, bbox_to_anchor=(1.02,1), loc="upper left", frameon=False)
  ax.axhline(0, color="grey", lw=0.6); ax.axvline(0, color="grey", lw=0.6)
  ax.set_xlabel("NMDS1", fontsize=12, fontweight="bold"); ax.set_ylabel("NMDS2", fontsize=12, fontweight="bold")
  ax.set_title(f"CDS-based Bray–Curtis NMDS (normalized Stress-1 = {model.stress_:.3f})", fontsize=15, fontweight="bold")
  fig.tight_layout(rect=[0,0.04,0.86,1])
  savefig(fig, "SupplementaryFigure3_NMDS_CDS_taxonomy")


def figure4_lfc() -> None:
  df = pd.read_csv(DATA / "Top6-members-LFC_gmpr.txt", sep="\t")
  df.columns = [str(c).strip() for c in df.columns]
  df["LFC"] = pd.to_numeric(df["LFC"], errors="coerce")
  df = df.dropna(subset=["LFC"]).copy()
  # Keep strongest entries while retaining comparison diversity.
  parts = []
  for comp, g in df.groupby("Comparasion", sort=False):
    parts.append(g.assign(abs_lfc=g.LFC.abs()).nlargest(4, "abs_lfc"))
  work = pd.concat(parts, ignore_index=True).assign(abs_lfc=lambda x: x.LFC.abs()).nlargest(28, "abs_lfc")
  work = work.sort_values("LFC")
  work["Direction"] = np.where(work.LFC >= 0, "Up", "Down")
  work["Taxon"] = work["Species/Genus/Phylum"].astype(str).str.replace(r"\s+", " ", regex=True)
  fig_h = max(8, 0.37 * len(work) + 2.5)
  fig, ax = plt.subplots(figsize=(14.5, fig_h))
  y = np.arange(len(work))
  bars = ax.barh(y, work.LFC, color=[DIRECTION_COLORS[x] for x in work.Direction], edgecolor="white")
  ax.set_yticks(y, [textwrap.shorten(x, width=62, placeholder="…") for x in work.Taxon], fontsize=9, color="black")
  ax.axvline(0, color="black", lw=0.8, ls="--")
  ax.set_xlabel("log2 fold change", fontsize=13, fontweight="bold", color="black")
  ax.set_ylabel("Differentially abundant taxon", fontsize=13, fontweight="bold", color="black")
  ax.set_title("Differential taxon abundance with explicit comparison direction", fontsize=17, fontweight="bold")
  max_abs = max(1, work.LFC.abs().max())
  ax.set_xlim(work.LFC.min() - 0.24*max_abs, work.LFC.max() + 0.42*max_abs)
  for rect, (_, r) in zip(bars, work.iterrows()):
    x = rect.get_width()
    xpos = x + 0.12*max_abs if x >= 0 else x - 0.12*max_abs
    ha = "left" if x >= 0 else "right"
    ax.text(xpos, rect.get_y()+rect.get_height()/2, f"{r['Comparasion']}  |  {x:.2f}", va="center", ha=ha, fontsize=8.5, color="black", clip_on=True)
  legend_handles=[]
  if (work.Direction == "Up").any(): legend_handles.append(plt.Rectangle((0,0),1,1,color=DIRECTION_COLORS['Up'],label='Up / enriched in first group'))
  if (work.Direction == "Down").any(): legend_handles.append(plt.Rectangle((0,0),1,1,color=DIRECTION_COLORS['Down'],label='Down / enriched in second group'))
  if legend_handles: ax.legend(handles=legend_handles, loc="lower right", frameon=False)
  ax.grid(False)
  fig.tight_layout(rect=[0,0.03,1,1])
  savefig(fig, "Figure4_taxon_log2FC_comparison_labeled")
  work.to_csv(DERIVED / "Figure4_taxon_log2FC_source.csv", index=False)


def figure5_mags() -> None:
  p = DATA / "Supplementary_table_7-MAGS-Quality-Genome_Lineage-Classification.xlsx"
  # The classification table has three title/header rows; row 4 contains the real fields.
  cls = pd.read_excel(p, sheet_name="bin.classification", header=3)
  cls.columns = [str(c).strip() for c in cls.columns]
  mag_col = next((c for c in cls.columns if c == "MAG" or c.startswith("MAG")), cls.columns[0])
  gtdb_col = next((c for c in cls.columns if "Gtdbtk" in c), None)
  species_col = next((c for c in cls.columns if "Species definition" in c), None)
  clean = cls[[mag_col] + ([gtdb_col] if gtdb_col else []) + ([species_col] if species_col else [])].copy()
  clean = clean.dropna(subset=[mag_col])
  clean[mag_col] = clean[mag_col].astype(str).str.replace(r"\.(strict|orig|permissive)$", "", regex=True).str.strip()
  clean = clean[clean[mag_col].str.match(r"MAG\.\d+$", na=False)].drop_duplicates(subset=[mag_col], keep="first")
  def phylum_from_lineage(x: str) -> str:
    m = re.search(r"p__([^;]+)", str(x))
    return m.group(1).strip() if m and m.group(1).strip() else "Unclassified"
  clean["Phylum"] = clean[gtdb_col].map(phylum_from_lineage) if gtdb_col else "Unclassified"
  counts = clean.Phylum.value_counts().rename_axis("Phylum").reset_index(name="Identified bins")
  counts["Percent"] = 100 * counts["Identified bins"] / counts["Identified bins"].sum()

  bq = pd.read_excel(p, sheet_name="Bins-quant", usecols="A:C", dtype=str)
  bq.columns = ["Sample", "Species", "Abundance"]
  bq = bq.dropna(subset=["Sample", "Species", "Abundance"]).copy()
  bq["Abundance"] = pd.to_numeric(bq["Abundance"].astype(str).str.replace(",", ".", regex=False), errors="coerce")
  bq = bq.dropna(subset=["Abundance"])
  bq["Sample"] = bq.Sample.astype(str).str.strip()
  bq["Species"] = bq.Species.astype(str).str.strip().replace({"nan":"Unclassified MAG"})
  top_species = bq.groupby("Species").Abundance.sum().nlargest(20).index
  bub = bq[bq.Species.isin(top_species)].copy()
  sample_order = ["AM-D","AM-R","TIA-D","TIA-R","TI-D","TI-R","VI-D","VI-R"]
  samples = [s for s in sample_order if s in set(bub.Sample)] + [s for s in dict.fromkeys(bub.Sample) if s not in sample_order]
  species = list(top_species[::-1])

  fig = plt.figure(figsize=(18, 10.5))
  gs = fig.add_gridspec(1, 2, width_ratios=[0.85, 1.65], wspace=0.32)
  ax1 = fig.add_subplot(gs[0,0])
  cc = counts.sort_values("Percent")
  colors = unique_colors(len(cc))
  bars = ax1.barh(np.arange(len(cc)), cc.Percent, color=colors, edgecolor="white")
  ax1.set_yticks(np.arange(len(cc)), cc.Phylum, fontsize=10, color="black")
  ax1.set_xlabel("Identified bins (%)", fontweight="bold", color="black")
  ax1.set_ylabel("GTDB phylum", fontweight="bold", color="black")
  ax1.set_title("A  Identified MAG/bin distribution", loc="left", fontsize=14, fontweight="bold")
  for bar, n, pct in zip(bars, cc["Identified bins"], cc.Percent):
    ax1.text(bar.get_width()+0.5, bar.get_y()+bar.get_height()/2, f"{int(n)} ({pct:.1f}%)", va="center", fontsize=9, color="black")
  ax1.set_xlim(0, max(cc.Percent.max()*1.35, 10)); ax1.grid(axis="x", alpha=0.2)

  ax2 = fig.add_subplot(gs[0,1])
  xmap={s:i for i,s in enumerate(samples)}; ymap={s:i for i,s in enumerate(species)}
  vmax=max(float(bub.Abundance.max()),1e-12)
  sizes=20 + 520*np.sqrt(np.maximum(bub.Abundance.to_numpy(float),0)/vmax)
  sc=ax2.scatter([xmap[x] for x in bub.Sample], [ymap[x] for x in bub.Species], s=sizes, c=bub.Abundance, cmap="viridis", edgecolor="black", linewidth=0.35, alpha=0.9)
  ax2.set_xticks(range(len(samples)), samples, rotation=45, ha="right", fontsize=10, color="black")
  ax2.set_yticks(range(len(species)), [textwrap.shorten(s,width=52,placeholder='…') for s in species], fontsize=8.5, color="black")
  ax2.set_xlabel("Lake/season group", fontweight="bold", color="black"); ax2.set_ylabel("MAG taxonomic assignment", fontweight="bold", color="black")
  ax2.set_title("B  MAG abundance from Bins-quant", loc="left", fontsize=14, fontweight="bold")
  ax2.grid(False); cbar=fig.colorbar(sc, ax=ax2, fraction=0.035, pad=0.02); cbar.set_label("Exact abundance", fontweight="bold")
  fig.suptitle("Identified genomic bins and their abundance across lateritic-lake sediments", fontsize=17, fontweight="bold", y=0.995)
  fig.subplots_adjust(bottom=0.14, top=0.93)
  savefig(fig, "Figure6_MAG_bins_percentage_abundance")
  counts.to_csv(DERIVED / "Figure5_identified_bins_percent.csv", index=False)
  bub.to_csv(DERIVED / "Figure5_MAG_abundance_source.csv", index=False)

def parse_comparison(comp: str) -> tuple[str, str]:
  s = re.sub(r"\s+", "", str(comp))
  if "vs" in s:
    a,b=s.split("vs",1); return a,b
  if "-" in s:
    a,b=s.split("-",1); return a,b
  return s, "comparison"


def figure6_ko() -> None:
  p = DATA / "Supplementary_table_5-Differential-abundance-pathways-KOs.xlsx"
  sheets = [("Top-differential-abundance_Dry","Dry"),("Top-differential-abundance-Rain","Rainy")]
  fig, axes = plt.subplots(1,2,figsize=(18,11),sharex=False)
  source=[]
  for ax,(sh,season),panel in zip(axes,sheets,["A","B"]):
    df=pd.read_excel(p,sheet_name=sh)
    df.columns=[str(c).strip() for c in df.columns]
    df["log2FoldChange"]=pd.to_numeric(df["log2FoldChange"],errors="coerce")
    df=df.dropna(subset=["log2FoldChange"]).copy()
    # Publication panel intentionally displays enriched/up KOs only, as requested.
    up=df[df.log2FoldChange>0].copy()
    up["abs_lfc"]=up.log2FoldChange.abs()
    up=up.nlargest(18,"abs_lfc").sort_values("log2FoldChange")
    up["label"]=up.OTU.astype(str).str.replace(r"\s+"," ",regex=True)
    source.append(up.assign(Season=season))
    y=np.arange(len(up)); bars=ax.barh(y,up.log2FoldChange,color=DIRECTION_COLORS["Up"],edgecolor="white")
    ax.set_yticks(y,[textwrap.shorten(x,width=44,placeholder='…') for x in up.label],fontsize=9,color="black")
    ax.set_xlabel("Positive log2 fold change",fontsize=12,fontweight="bold",color="black")
    ax.set_ylabel("KO marker",fontsize=12,fontweight="bold",color="black")
    ax.set_title(f"{panel}  {season} season — up/enriched KOs",loc="left",fontsize=14,fontweight="bold")
    xmax=max(up.log2FoldChange.max(),1); ax.set_xlim(0,xmax*1.48)
    for bar,(_,r) in zip(bars,up.iterrows()):
      a,b=parse_comparison(r.get("Comparasion",""))
      lab=f"{a} vs {b} | {r.log2FoldChange:.2f}"
      ax.text(bar.get_width()+0.03*xmax,bar.get_y()+bar.get_height()/2,lab,va="center",ha="left",fontsize=8.2,color="black",clip_on=True)
    ax.grid(False)
  fig.suptitle("Top enriched KO biomarkers in dry and rainy comparisons",fontsize=18,fontweight="bold",y=0.995)
  fig.subplots_adjust(bottom=0.07,top=0.94,wspace=0.42)
  savefig(fig,"Figure7_top_enriched_KO_dry_rain_comparisons")
  pd.concat(source,ignore_index=True).to_csv(DERIVED/"Figure7_top_enriched_KO_source.csv",index=False)


def proportional_heatmap(df: pd.DataFrame, meta_cols: list[str], label_col: str, title: str, stem: str, top_n: int, zscore: bool=False) -> None:
  numeric=[c for c in df.columns if c not in meta_cols and pd.to_numeric(df[c],errors="coerce").notna().sum()>0]
  mat=df[numeric].apply(pd.to_numeric,errors="coerce").fillna(0)
  idx=mat.abs().sum(axis=1).nlargest(top_n).index
  mat=mat.loc[idx]; labels=df.loc[idx,label_col].astype(str).map(lambda x:textwrap.shorten(x,width=72,placeholder='…'))
  if zscore:
    mat=mat.sub(mat.mean(axis=1),axis=0).div(mat.std(axis=1).replace(0,np.nan),axis=0).fillna(0)
  nrow,ncol=mat.shape
  cell_w=0.27 if ncol>45 else 0.42
  cell_h=0.30
  fig_w=max(13,min(28,4.2+ncol*cell_w)); fig_h=max(8,min(24,2.7+nrow*cell_h))
  fig,ax=plt.subplots(figsize=(fig_w,fig_h))
  im=ax.imshow(mat.to_numpy(),aspect="auto",interpolation="nearest",cmap="RdBu_r" if zscore else "viridis", rasterized=True)
  ax.set_xticks(np.arange(ncol),[textwrap.shorten(str(c),width=30,placeholder='…') for c in numeric],rotation=55,ha="right",fontsize=7.5,color="black")
  ax.set_yticks(np.arange(nrow),labels,fontsize=8,color="black")
  ax.set_xlabel("Samples/environments (Amazonian metagenomes and external metagenomic, metatranscriptomic or combined-assembly layers)",fontsize=11,fontweight="bold",color="black")
  ax.set_ylabel(label_col,fontsize=11,fontweight="bold",color="black")
  ax.set_title(title,fontsize=16,fontweight="bold",pad=14)
  cbar=fig.colorbar(im,ax=ax,fraction=0.018,pad=0.015); cbar.set_label("Row z-score" if zscore else "Exact count / abundance",fontweight="bold")
  ax.set_xticks(np.arange(-.5,ncol,1),minor=True); ax.set_yticks(np.arange(-.5,nrow,1),minor=True)
  ax.grid(which="minor",color="white",linewidth=0.22); ax.tick_params(which="minor",bottom=False,left=False)
  fig.tight_layout(rect=[0,0.025,1,1])
  savefig(fig,stem,dpi=200)
  out=df.loc[idx,meta_cols+numeric].copy(); out.to_csv(DERIVED/f"{stem}_source.csv",index=False)


def figures7_8_heatmaps() -> None:
  p=DATA/"Supplementary_table_8_final_restructured_filled.xlsx"
  allko=pd.read_excel(p,sheet_name="ST8 — all KO biomarkers")
  iron=pd.read_excel(p,sheet_name="ST8- Iron metabolism KO -marker")
  proportional_heatmap(allko,["KO","Metabolism","KO description"],"KO","All KO biomarkers across Amazonian lateritic lakes and iron-rich environments","Figure7_all_KO_biomarker_heatmap_proportional",45,False)
  proportional_heatmap(iron,["Function Id","Biologic Role","Function Name"],"Function Id","Iron-metabolism KO/function markers across environments","Figure8_iron_metabolism_heatmap_proportional",45,False)
  sel=pd.read_excel(p,sheet_name="ST8 — selected sediments")
  isel=pd.read_excel(p,sheet_name="ST8-Iron metabolism - selected")
  proportional_heatmap(sel,["KO","Metabolism","KO description"],"KO","ST8 selected sediments — all KO biomarkers (row z-score)","SupplementaryFigure6_ST8_selected_sediments_all_KO_zscore_proportional",50,True)
  proportional_heatmap(isel,["Function Id","Biologic Role","Function Name"],"Function Id","ST8 selected sediments — iron-metabolism markers (row z-score)","SupplementaryFigure7_ST8_iron_selected_zscore_proportional",50,True)


def rda_analysis(otu: pd.DataFrame,tax:pd.DataFrame) -> dict:
  shared=otu.index.intersection(tax.index)
  genera=tax.loc[shared,"Genus"].fillna("Unclassified").astype(str).str.strip().replace({"":"Unclassified","NA":"Unclassified","nan":"Unclassified"})
  mat=otu.loc[shared].copy(); mat["Genus"]=genera
  g=mat.groupby("Genus").sum(numeric_only=True)
  # Aggregate dry/rainy pairs to the 10 physicochemical sampling positions.
  pos={c:".".join(c.split(".")[:2]) for c in g.columns}
  gpos=pd.DataFrame({p:g[[c for c,v in pos.items() if v==p]].sum(axis=1) for p in sorted(set(pos.values()))}).T
  gpos=gpos.loc[:,gpos.sum(axis=0).nlargest(80).index]
  row_sums=gpos.sum(axis=1).replace(0,np.nan)
  Y=np.sqrt(gpos.div(row_sums,axis=0).fillna(0))

  env=pd.read_excel(DATA/"fiqui2.xlsx")
  env.columns=[str(c).strip() for c in env.columns]
  env["SampleMM"]=env["SampleMM"].astype(str).str.strip().replace({"V1.P1":"VI.P1"})
  for c in env.columns[3:]: env[c]=pd.to_numeric(env[c],errors="coerce")
  envagg=env.groupby("SampleMM").mean(numeric_only=True)
  common=[x for x in gpos.index if x in envagg.index]
  Y=Y.loc[common]; envagg=envagg.loc[common]
  preferred=["Fe2O3","SiO2","Al2O3","TOT/C","TOT/S","LOI","V","Cu","Pb","Zr","Ce"]
  available=[c for c in preferred if c in envagg.columns and envagg[c].notna().sum()==len(common)]
  Z=envagg[available].copy()
  # Remove near-zero variance and highly redundant predictors, cap at 6 for n=10.
  Z=Z.loc[:,Z.std()>1e-10]
  selected=[]
  for c in Z.columns:
    if not selected or all(abs(Z[c].corr(Z[s]))<0.92 for s in selected): selected.append(c)
    if len(selected)>=6: break
  Z=Z[selected]
  Zs=(Z-Z.mean())/Z.std(ddof=0).replace(0,1)
  X=np.column_stack([np.ones(len(Zs)),Zs.to_numpy()])
  H=X@np.linalg.pinv(X.T@X)@X.T
  Yc=Y.to_numpy()-Y.to_numpy().mean(axis=0,keepdims=True)
  Yhat=H@Yc
  u,s,vt=np.linalg.svd(Yhat,full_matrices=False)
  site=u[:,:2]*s[:2]
  species=vt[:2,:].T*s[:2]
  eig=s**2
  pct=100*eig[:2]/max(eig.sum(),1e-12)
  # Environmental vector correlations with site axes.
  vec=np.array([[np.corrcoef(Zs[c],site[:,k])[0,1] for k in range(2)] for c in Zs.columns])
  # Overall constrained fraction and permutation test.
  ss_fit=np.sum(Yhat**2); ss_tot=np.sum(Yc**2); r2=ss_fit/ss_tot if ss_tot else np.nan
  p=len(Zs.columns); n=len(Zs); df1=max(p,1); df2=max(n-p-1,1)
  ss_res=max(ss_tot-ss_fit,1e-12); F=(ss_fit/df1)/(ss_res/df2)
  rng=np.random.default_rng(42); fperm=[]
  for _ in range(999):
    yp=Yc[rng.permutation(n),:]
    yh=H@yp; sf=np.sum(yh**2); sr=max(np.sum(yp**2)-sf,1e-12)
    fperm.append((sf/df1)/(sr/df2))
  pval=(1+sum(x>=F for x in fperm))/(1+len(fperm))
  scores=pd.DataFrame(site,columns=["RDA1","RDA2"],index=common)
  scores["Lake"]=[x.split(".")[0] for x in common]
  scores.to_csv(DERIVED/"RDA_site_scores.csv")
  pd.DataFrame(vec,index=Zs.columns,columns=["RDA1","RDA2"]).to_csv(DERIVED/"RDA_environment_vectors.csv")
  envagg.reset_index().to_csv(DERIVED/"fiqui2_physicochemical_sample_means.csv",index=False)
  return {"scores":scores,"vectors":pd.DataFrame(vec,index=Zs.columns,columns=["RDA1","RDA2"]),"pct":pct,"r2":r2,"F":F,"p":pval,"variables":selected,"n":n}


def rda_figure(result:dict) -> None:
  sc=result["scores"]; vec=result["vectors"]
  fig,ax=plt.subplots(figsize=(11,8.5))
  for lake,g in sc.groupby("Lake"):
    ax.scatter(g.RDA1,g.RDA2,s=110,color=LAKE_COLORS.get(lake,"grey"),edgecolor="black",linewidth=0.7,label=lake,zorder=3)
    for idx,r in g.iterrows(): ax.annotate(idx,(r.RDA1,r.RDA2),xytext=(5,5),textcoords="offset points",fontsize=9,color="black")
  scale=max(np.max(np.abs(sc[["RDA1","RDA2"]].to_numpy())),1e-6)*0.88
  for name,r in vec.iterrows():
    x,y=r.RDA1*scale,r.RDA2*scale
    ax.arrow(0,0,x,y,width=0.002*scale,head_width=0.045*scale,length_includes_head=True,color="#444444",alpha=0.85)
    ax.text(x*1.08,y*1.08,name,fontsize=9,fontweight="bold",ha="center",va="center",color="black")
  ax.axhline(0,color="grey",lw=0.7); ax.axvline(0,color="grey",lw=0.7)
  ax.set_xlabel(f"RDA1 ({result['pct'][0]:.1f}% of constrained variation)",fontsize=12,fontweight="bold",color="black")
  ax.set_ylabel(f"RDA2 ({result['pct'][1]:.1f}% of constrained variation)",fontsize=12,fontweight="bold",color="black")
  ax.set_title("RDA of CDS-derived genus composition and sediment physicochemistry",fontsize=16,fontweight="bold")
  ax.legend(title="Lake",bbox_to_anchor=(1.02,1),loc="upper left",frameon=False)
  fig.tight_layout(rect=[0,0.04,0.88,1])
  savefig(fig,"SupplementaryFigure17_RDA_CDS_genus_fiqui2_physicochemical")


def workflow_figure() -> None:
  fig,ax=plt.subplots(figsize=(18,12)); ax.set_xlim(0,18); ax.set_ylim(0,12); ax.axis("off")
  def box(x,y,w,h,text,kind="process",fc="#E8F1F8"):
    if kind=="database":
      ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.02",facecolor=fc,edgecolor="#1F4E79",lw=1.7))
      ax.add_patch(Ellipse((x+w/2,y+h),w,h*0.28,facecolor=fc,edgecolor="#1F4E79",lw=1.7))
      ax.add_patch(Ellipse((x+w/2,y),w,h*0.28,facecolor=fc,edgecolor="#1F4E79",lw=1.2))
    elif kind=="input":
      pts=[(x+0.3,y),(x+w,y),(x+w-0.3,y+h),(x,y+h)]
      ax.add_patch(Polygon(pts,closed=True,facecolor=fc,edgecolor="#1F4E79",lw=1.7))
    elif kind=="decision":
      pts=[(x+w/2,y+h),(x+w,y+h/2),(x+w/2,y),(x,y+h/2)]
      ax.add_patch(Polygon(pts,closed=True,facecolor=fc,edgecolor="#1F4E79",lw=1.7))
    elif kind=="output":
      ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.12,rounding_size=0.12",facecolor=fc,edgecolor="#1F4E79",lw=2.0))
    else:
      ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle="round,pad=0.08,rounding_size=0.08",facecolor=fc,edgecolor="#1F4E79",lw=1.7))
    ax.text(x+w/2,y+h/2,text,ha="center",va="center",fontsize=9.5,fontweight="bold",wrap=True,color="#111111")
    return (x,y,w,h)
  def arrow(a,b,label=None):
    x1=a[0]+a[2]/2; y1=a[1]; x2=b[0]+b[2]/2; y2=b[1]+b[3]
    ar=FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=14,lw=1.7,color="#34495E",connectionstyle="arc3,rad=0.0")
    ax.add_patch(ar)
    if label: ax.text((x1+x2)/2+0.1,(y1+y2)/2,label,fontsize=8,color="#333333")
  # Four-row complete computing workflow.
  s1=box(0.5,10.3,3.5,1.0,"CDS OTU + taxonomy tables\nresultado.cds.otu/tax.tab","input","#EAF4E3")
  s2=box(5.0,10.3,3.5,1.0,"Supplementary Tables 1, 4, 5, 7 and 8","database","#FFF1CC")
  s3=box(9.5,10.3,3.5,1.0,"Physicochemical table\nfiqui2.xlsx","input","#FCE8E6")
  s4=box(14.0,10.3,3.5,1.0,"Public environmental APIs\nclimate, soil, NDVI/SAR","database","#E8EAF6")
  p1=box(0.6,8.1,3.3,1.0,"Validate IDs, sample mapping, numeric fields and metadata","process")
  p2=box(5.1,8.1,3.3,1.0,"Build taxonomic, KO, iron and MAG matrices","process")
  p3=box(9.6,8.1,3.3,1.0,"Aggregate geochemical replicates by sampling position","process")
  p4=box(14.1,8.1,3.3,1.0,"Cache and harmonize environmental layers by coordinates/date","process")
  d1=box(7.4,6.1,3.2,1.45,"Do taxonomy and metadata share valid sample IDs?","decision","#FDEBD0")
  q1=box(1.0,4.0,3.7,1.0,"Taxonomic profiles, alpha diversity and Bray–Curtis NMDS/PCoA","process","#E8F6F3")
  q2=box(5.2,4.0,3.7,1.0,"DESeq2/ALDEx2 direction plots and KO/iron heatmaps","process","#E8F6F3")
  q3=box(9.4,4.0,3.7,1.0,"Hellinger RDA: taxonomy × physicochemistry/environment","process","#E8F6F3")
  q4=box(13.6,4.0,3.7,1.0,"Atlas comparison by environment and omics layer","process","#E8F6F3")
  o1=box(1.0,1.4,4.8,1.1,"Interactive bilingual Streamlit app\nfilters, tables, downloads, methods","output","#D6EAF8")
  o2=box(6.6,1.4,4.8,1.1,"Publication figures\nPNG + SVG + PDF and source CSVs","output","#D6EAF8")
  o3=box(12.2,1.4,4.8,1.1,"Synchronized manuscript\nMethods, Results, Discussion and captions","output","#D6EAF8")
  for a,b in [(s1,p1),(s2,p2),(s3,p3),(s4,p4)]: arrow(a,b)
  for a in [p1,p2,p3,p4]: arrow(a,d1)
  for b in [q1,q2,q3,q4]: arrow(d1,b,"yes")
  for a in [q1,q2,q3,q4]:
    for b in [o1,o2,o3]:
      x1=a[0]+a[2]/2; y1=a[1]; x2=b[0]+b[2]/2; y2=b[1]+b[3]
      ax.add_patch(FancyArrowPatch((x1,y1),(x2,y2),arrowstyle="-|>",mutation_scale=11,lw=0.9,color="#7F8C8D",alpha=0.55,connectionstyle="arc3,rad=0.08"))
  ax.text(9,11.75,"Complete computational workflow of the Iron-Rich Environment Metagenomic Atlas",ha="center",fontsize=18,fontweight="bold")
  ax.text(9,0.45,"Standard flowchart notation: cylinders = databases; parallelograms = input; rectangles = processing; diamond = validation decision; rounded boxes = outputs. Arrows indicate implemented data flow.",ha="center",fontsize=9.5)
  savefig(fig,"SupplementaryFigure30_complete_computational_workflow")


def update_study_references() -> None:
  p=DATA/"st8_study_references.csv"
  if not p.exists(): return
  df=pd.read_csv(p)
  def context(group:str)->tuple[str,str]:
    g=str(group)
    if "Matano" in g:
      return ("Lake Matano is a stratified ferruginous, sulfate-poor tropical lake used as a modern analogue for iron-rich Precambrian waters; published studies describe photoferrotrophy and methane cycling.","Crowe et al. 2008, PNAS, doi:10.1073/pnas.0807560105; Crowe et al. 2011, Geobiology, doi:10.1111/j.1472-4669.2010.00257.x")
    if "Towuti" in g:
      return ("Lake Towuti contains anoxic, sulfate-poor ferruginous sediments with microbial potential for iron/sulfate reduction, fermentation and methanogenesis.","Vuillemin et al. 2016, Front Microbiol, doi:10.3389/fmicb.2016.01007; Friese et al. 2021, Nat Commun, doi:10.1038/s41467-021-22453-0")
    if "Richmond" in g:
      return ("Richmond Mine at Iron Mountain is an extreme pyrite-driven acid mine drainage system with iron- and sulfur-oxidizing biofilm communities studied by metagenomics and multi-omics.","Druschel et al. 2004, Appl Environ Microbiol, doi:10.1128/AEM.70.9.5515-5522.2004; Tyson et al. 2004, Nature, doi:10.1038/nature02340")
    if "Hydrothermal" in g:
      return ("Hydrothermal iron mats are produced by active Fe(II)-oxidizing communities, commonly enriched in Zetaproteobacteria, and provide a marine iron-cycling comparison.","Singer et al. 2013, PLoS ONE, doi:10.1371/journal.pone.0056099; McAllister et al. 2020, mBio, doi:10.1128/mBio.02053-19")
    if "Superior" in g:
      return ("Lake Superior datasets represent freshwater water-column or sediment communities; they serve as a freshwater comparison, while the ST8 layer identifies the exact omics source.","ST8 IMG/M/GOLD metadata; use record-specific study/BioProject links")
    if "Burr Oak" in g:
      return ("Burr Oak Reservoir is included as a sediment/control comparison linked to the laboratory enrichment study represented in IMG/M.","ST8 IMG/M/GOLD metadata; publication linkage should be confirmed at record level")
    if "Akron" in g or "Pennsylvania" in g:
      return ("These coal-mine drainage records represent acidic, metal- and iron-associated microbial communities, including metagenomic and metatranscriptomic layers.","ST8 IMG/M/GOLD metadata and linked BioProjects; publication linkage should be confirmed at record level")
    return ("Iron-associated environmental context is retained from the curated ST8 IMG/M/GOLD metadata; record-level habitat, location and omics layer are shown in the app.","ST8 IMG/M/GOLD metadata")
  vals=[context(x) for x in df["ST8_group"]]
  df["iron_environment_context"]=[x[0] for x in vals]
  df["context_reference"]=[x[1] for x in vals]
  df.to_csv(p,index=False)


def main() -> None:
  otu,tax=load_cds()
  ph=aggregate_taxonomy(otu,tax,"Phylum",14)
  ge=aggregate_taxonomy(otu,tax,"Genus",18)
  horizontal_taxonomy_figure(ph,"Phylum","Figure2_taxonomic_phylum_horizontal_CDS")
  horizontal_taxonomy_figure(ge,"Genus","Figure3_taxonomic_genus_horizontal_CDS")
  alpha_nmds_figures(otu)
  figure4_lfc()
  figure5_mags()
  figure6_ko()
  figures7_8_heatmaps()
  rda=rda_analysis(otu,tax); rda_figure(rda)
  workflow_figure()
  update_study_references()
  print("Generated canonical figures in",OUT)
  print("RDA summary:",{k:rda[k] for k in ["variables","n","r2","F","p","pct"]})

if __name__=="__main__": main()
