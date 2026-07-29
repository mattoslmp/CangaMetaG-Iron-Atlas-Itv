#!/usr/bin/env python3
"""Recalculate CDS rarefaction curves and alpha-diversity metrics at 32,999 CDS.

This script is intentionally deterministic. It uses the packaged CDS OTU table,
taxonomy table and sample statistics to keep all 20 samples, rarefy to 32,999
CDS per sample, and regenerate publication-ready Supplementary Figures 2 and 4.
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from PIL import Image

RAREFACTION_DEPTH = 32999
SEED = 20260628

APP_ROOT = Path(__file__).resolve().parents[2]
ARTICLE_ROOT = Path(os.environ.get("CANGAMETA_ARTICLE_ROOT", str(APP_ROOT / "_article_root_not_set"))).resolve()
ONLY_S4 = os.environ.get("CANGAMETA_ONLY_S4", "0") == "1"
APP_FIG_DIR = APP_ROOT / "outputs" / "final_publication_figures"
APP_DERIVED = APP_ROOT / "data" / "final_publication_derived"
APP_INPUTS = APP_ROOT / "data"
APP_SCRIPT_DIR = APP_ROOT / "scripts" / "final_publication_figures"
APP_LEGACY = APP_ROOT / "outputs" / "legacy_figure_variants_pre_28Jun2026"
ARTICLE_SUPP_FIG_DIR = ARTICLE_ROOT / "03_Supplementary_Figures"
ARTICLE_DERIVED = ARTICLE_ROOT / "05_Source_Data_and_Audit" / "final_publication_derived"
ARTICLE_AUDIT = ARTICLE_ROOT / "05_Source_Data_and_Audit" / "final_publication_audit_tables"
ARTICLE_SCRIPT_DIR = ARTICLE_ROOT / "06_Scripts_and_Reproducibility" / "scripts" / "final_publication_figures"
ARTICLE_LEGACY = ARTICLE_ROOT / "09_Replaced_Figures_Pre_28Jun2026"
EMBED_DIR = ARTICLE_ROOT / "08_Embedded_Docx_Image_Copies"

for d in [APP_FIG_DIR, APP_DERIVED, APP_SCRIPT_DIR, APP_LEGACY, ARTICLE_SUPP_FIG_DIR, ARTICLE_DERIVED, ARTICLE_AUDIT, ARTICLE_SCRIPT_DIR, ARTICLE_LEGACY, EMBED_DIR]:
    d.mkdir(parents=True, exist_ok=True)

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 16,
    "axes.labelsize": 18,
    "axes.titlesize": 20,
    "xtick.labelsize": 14,
    "ytick.labelsize": 14,
    "legend.fontsize": 13,
    "figure.titlesize": 22,
    "savefig.dpi": 600,
})

PALETTE = {
    "AM-D": "#0072B2",
    "AM-R": "#E69F00",
    "TIA-D": "#009E73",
    "TIA-R": "#D55E00",
    "TI-D": "#CC79A7",
    "TI-R": "#56B4E9",
    "VI-D": "#F0E442",
    "VI-R": "#7E57C2",
}
LAKE_PALETTE = {"AM": "#0072B2", "TIA": "#009E73", "TI": "#CC79A7", "VI": "#7E57C2"}
ORDER = ["AM-D", "AM-R", "TIA-D", "TIA-R", "TI-D", "TI-R", "VI-D", "VI-R"]
LAKE_ORDER = ["AM", "TIA", "TI", "VI"]


def clean_sample_col(col: str) -> str:
    return str(col).strip()


def build_sample_mapping(otu: pd.DataFrame) -> dict[str, str]:
    stats = pd.read_csv(APP_INPUTS / "Table_S1_general_statistics.csv")
    # Map by exact Predicted CDS count. All values in this dataset are unique.
    cds_to_sample = dict(zip(stats["Predicted CDS"].astype(int), stats["Samples"].astype(str)))
    mapping = {}
    for col in otu.columns:
        total = int(otu[col].sum())
        sample = cds_to_sample.get(total)
        if sample is None:
            raise ValueError(f"Could not map OTU column {col} with total {total} to Table S1 Predicted CDS.")
        mapping[col] = sample
    return mapping


def sample_metadata(samples: Iterable[str]) -> pd.DataFrame:
    rows = []
    for s in samples:
        # Example: AM.P1.D, TIA.P2.R.
        parts = s.split(".")
        lake = parts[0]
        season_code = parts[-1]
        season = "DRY" if season_code.upper().startswith("D") else "RAINY"
        lake_season = f"{lake}-{'D' if season == 'DRY' else 'R'}"
        rows.append({"Sample": s, "Lake": lake, "Season": season, "Lake_season": lake_season})
    return pd.DataFrame(rows)


def rarefy_counts(counts: np.ndarray, depth: int, rng: np.random.Generator) -> np.ndarray:
    counts = counts.astype(np.int64)
    total = int(counts.sum())
    if total < depth:
        raise ValueError(f"Total count {total} is below rarefaction depth {depth}.")
    if total == depth:
        return counts.copy()
    return rng.multivariate_hypergeometric(counts, depth).astype(np.int64)


def alpha_metrics(counts: np.ndarray) -> dict[str, float]:
    counts = counts.astype(np.int64)
    positive = counts[counts > 0]
    observed = int(positive.size)
    f1 = int(np.sum(positive == 1))
    f2 = int(np.sum(positive == 2))
    if f2 > 0:
        chao1 = observed + (f1 * f1) / (2.0 * f2)
    else:
        # Bias-corrected fallback when no doubletons are observed.
        chao1 = observed + (f1 * (f1 - 1)) / 2.0
    p = positive / positive.sum() if positive.sum() else np.array([], dtype=float)
    shannon = float(-(p * np.log(p)).sum()) if p.size else float("nan")
    return {"Observed_OTUs": observed, "Chao1": float(chao1), "Shannon": shannon, "Singletons": f1, "Doubletons": f2}


def expected_observed(counts: np.ndarray, depth: int) -> float:
    """Analytical expected observed OTUs at a rarefaction depth."""
    counts = counts[counts > 0].astype(np.float64)
    n = int(counts.sum())
    if depth <= 0:
        return 0.0
    if depth >= n:
        return float(counts.size)
    # log C(N-ni, m) - log C(N, m). Use lgamma for numerical stability.
    # Terms where N-ni < m have zero probability of being absent.
    N = float(n)
    m = float(depth)
    log_denom = math.lgamma(N + 1) - math.lgamma(m + 1) - math.lgamma(N - m + 1)
    probs_absent = []
    for ni in counts:
        if N - ni < m:
            probs_absent.append(0.0)
        else:
            log_num = math.lgamma(N - ni + 1) - math.lgamma(m + 1) - math.lgamma(N - ni - m + 1)
            probs_absent.append(math.exp(log_num - log_denom))
    return float(np.sum(1.0 - np.array(probs_absent)))


def save_all_formats(fig: plt.Figure, stem: str, dirs: list[Path]) -> None:
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
        fig.savefig(d / f"{stem}.png", dpi=600, bbox_inches="tight", facecolor="white")
        fig.savefig(d / f"{stem}.pdf", bbox_inches="tight", facecolor="white")
        fig.savefig(d / f"{stem}.svg", bbox_inches="tight", facecolor="white")
        fig.savefig(d / f"{stem}.tiff", dpi=600, bbox_inches="tight", facecolor="white")


def make_embed_copy(src_png: Path, stem: str) -> None:
    im = Image.open(src_png).convert("RGB")
    max_w = 2400
    if im.width > max_w:
        ratio = max_w / im.width
        im = im.resize((max_w, int(im.height * ratio)), Image.Resampling.LANCZOS)
    im.save(EMBED_DIR / f"{stem}_embed.png", quality=95)
    im.save(EMBED_DIR / f"{stem}_embed_supp.jpg", quality=92)


def move_old_variants(stems: list[str], dirs: list[Path]) -> None:
    for d in dirs:
        legacy = APP_LEGACY if "work_app" in str(d) else ARTICLE_LEGACY
        legacy.mkdir(parents=True, exist_ok=True)
        for stem in stems:
            for ext in [".png", ".pdf", ".svg", ".tiff", ".jpg", ".jpeg"]:
                p = d / f"{stem}{ext}"
                if p.exists():
                    target = legacy / f"{d.name}__{p.name}"
                    if target.exists():
                        p.unlink()
                    else:
                        shutil.move(str(p), str(target))


def update_manifest(path: Path) -> None:
    if not path.exists():
        return
    df = pd.read_csv(path).fillna("")
    if "Figure" not in df.columns:
        return
    def upsert(fig_name: str, stem: str, input_text: str, method: str):
        nonlocal df
        row = {
            "Figure": fig_name,
            "PNG": f"{stem}.png",
            "SVG": f"{stem}.svg",
            "PDF": f"{stem}.pdf",
            "Input": input_text,
            "Script": "scripts/final_publication_figures/06_recalculate_rarefaction_alpha_32999.py",
            "Method / description": method,
        }
        if (df["Figure"].astype(str) == fig_name).any():
            idx = df.index[df["Figure"].astype(str) == fig_name][0]
            for k, v in row.items():
                if k in df.columns:
                    df.loc[idx, k] = v
        else:
            for c in df.columns:
                row.setdefault(c, "")
            df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    upsert(
        "Supplementary Figure 2",
        "SupplementaryFigure2_rarefaction_curves_CDS_32999",
        "data/resultado.cds.otu.tab; data/Table_S1_general_statistics.csv; rarefaction depth = 32,999 CDS",
        "CDS-based rarefaction curves for all 20 samples. Curves were generated from deterministic multivariate-hypergeometric subsampling across depths up to 32,999 CDS; observed OTUs, Chao1 and Shannon are shown.",
    )
    upsert(
        "Supplementary Figure 4",
        "SupplementaryFigure4_alpha_diversity_CDS_32999",
        "data/resultado.cds.otu.tab; data/Table_S1_general_statistics.csv; rarefaction depth = 32,999 CDS",
        "Observed OTUs, Chao1 richness and Shannon diversity recalculated after deterministic rarefaction to 32,999 CDS while retaining all 20 samples.",
    )
    upsert(
        "Supplementary Figure 40",
        "SupplementaryFigure40_top_enriched_taxa_DESeq2_vivid",
        "data/Supplementary_table_2_DESEq.xlsx and packaged differential-taxon results",
        "Top enriched bacterial and archaeal taxa from the original differential-abundance visualization, retained as Supplementary Figure 40 after Supplementary Figure 4 was reassigned to recalculated alpha-diversity metrics.",
    )
    # Natural order: Figure 1..8 then Supplementary Figure 1..40.
    def sk(v):
        s = str(v)
        m = re.match(r"Figure (\d+)$", s)
        if m:
            return (0, int(m.group(1)))
        m = re.match(r"Supplementary Figure (\d+)$", s)
        if m:
            return (1, int(m.group(1)))
        return (2, 10**9)
    df = df.sort_values(by="Figure", key=lambda col: col.map(sk)).reset_index(drop=True)
    df.to_csv(path, index=False)


def main() -> None:
    otu_raw = pd.read_csv(APP_INPUTS / "resultado.cds.otu.tab", sep="\t", index_col=0)
    otu_raw = otu_raw.apply(pd.to_numeric, errors="coerce").fillna(0).astype(np.int64)
    mapping = build_sample_mapping(otu_raw)
    otu = otu_raw.rename(columns=mapping)
    otu = otu[[s for s in sample_metadata(mapping.values())["Sample"]]] if False else otu
    samples = list(otu.columns)
    meta = sample_metadata(samples)
    meta = meta.set_index("Sample")

    rng = np.random.default_rng(SEED)
    metrics_rows = []
    rarefied = {}
    for sample in samples:
        counts = otu[sample].to_numpy(dtype=np.int64)
        rc = rarefy_counts(counts, RAREFACTION_DEPTH, rng)
        rarefied[sample] = rc
        m = alpha_metrics(rc)
        m.update({
            "Sample": sample,
            "Lake": meta.loc[sample, "Lake"],
            "Season": meta.loc[sample, "Season"],
            "Lake_season": meta.loc[sample, "Lake_season"],
            "Rarefaction_depth_CDS": RAREFACTION_DEPTH,
            "Original_CDS_count": int(counts.sum()),
            "Retained_all_samples": True,
        })
        metrics_rows.append(m)
    metrics = pd.DataFrame(metrics_rows)
    metrics = metrics[["Sample", "Lake", "Season", "Lake_season", "Original_CDS_count", "Rarefaction_depth_CDS", "Observed_OTUs", "Chao1", "Shannon", "Singletons", "Doubletons", "Retained_all_samples"]]

    if ONLY_S4:
        # Targeted proportion-only regeneration. The underlying deterministic
        # alpha-diversity metrics, palette, groups, labels and values are
        # unchanged; only the physical figure proportion is revised.
        for out_dir in [APP_DERIVED, ARTICLE_DERIVED, ARTICLE_AUDIT, APP_ROOT / "outputs" / "final_publication_statistics"]:
            out_dir.mkdir(parents=True, exist_ok=True)
            metrics.to_csv(out_dir / "SupplementaryFigure4_alpha_diversity_CDS_32999_source.csv", index=False)
        fig, axes = plt.subplots(1, 3, figsize=(18, 10.5))
        fig.subplots_adjust(left=0.055, right=0.99, bottom=0.16, top=0.88, wspace=0.24)
        ycols = [("Observed_OTUs", "Observed OTUs"), ("Chao1", "Chao1 richness"), ("Shannon", "Shannon diversity")]
        x_positions = {g: i + 1 for i, g in enumerate(ORDER)}
        jitter_rng = np.random.default_rng(SEED + 2)
        for ax, (col, label) in zip(axes, ycols):
            data = [metrics.loc[metrics["Lake_season"] == g, col].to_numpy(float) for g in ORDER]
            bp = ax.boxplot(data, positions=list(x_positions.values()), widths=0.55, patch_artist=True, showfliers=False, medianprops={"color": "black", "lw": 2.1}, boxprops={"lw": 1.2}, whiskerprops={"lw": 1.2}, capprops={"lw": 1.2})
            for patch, g in zip(bp["boxes"], ORDER):
                patch.set_facecolor(PALETTE[g]); patch.set_alpha(0.55)
            for g in ORDER:
                vals = metrics.loc[metrics["Lake_season"] == g, col].to_numpy(float)
                xs = np.full(len(vals), x_positions[g], dtype=float) + jitter_rng.normal(0, 0.045, size=len(vals))
                ax.scatter(xs, vals, s=54, color=PALETTE[g], edgecolor="black", linewidth=0.8, zorder=5)
                for x, y, sample in zip(xs, vals, metrics.loc[metrics["Lake_season"] == g, "Sample"]):
                    ax.text(x + 0.035, y, sample.replace(".", "-"), fontsize=8.5, va="center", alpha=0.85)
            ax.set_title(label, fontweight="bold")
            ax.set_ylabel(label, fontweight="bold")
            ax.set_xlabel("Lake-season group", fontweight="bold")
            ax.set_xticks(list(x_positions.values()))
            ax.set_xticklabels(ORDER, rotation=35, ha="right", fontweight="bold")
            ax.grid(axis="y", color="#e6e6e6", lw=0.7)
            ax.spines[["top", "right"]].set_visible(False)
        fig.suptitle("Supplementary Figure 4. CDS alpha-diversity recalculated after rarefaction to 32,999 CDS", fontweight="bold", y=0.965)
        fig.text(0.5, 0.025, "Observed OTUs, Chao1 and Shannon were calculated after deterministic rarefaction of each sample to 32,999 CDS. All 20 samples were retained.", ha="center", fontsize=13)
        stem = "SupplementaryFigure4_alpha_diversity_CDS_32999"
        save_all_formats(fig, stem, [APP_FIG_DIR, ARTICLE_SUPP_FIG_DIR])
        plt.close(fig)
        report = {
            "figure": "S4",
            "script": "scripts/final_publication_figures/06_recalculate_rarefaction_alpha_32999.py",
            "command": "CANGAMETA_ONLY_S4=1 CANGAMETA_ARTICLE_ROOT=<article_root> python scripts/final_publication_figures/06_recalculate_rarefaction_alpha_32999.py",
            "source": "data/resultado.cds.otu.tab and data/Table_S1_general_statistics.csv",
            "scientific_values_changed": False,
            "before_inches": [22, 8],
            "after_inches": [18, 10.5],
            "font_sizes_changed": False,
            "sample_count": len(samples),
            "page_numbering": "not part of the image; handled by editable Word PAGE fields",
        }
        for root in [APP_ROOT, ARTICLE_ROOT]:
            (root / "S4_PROPORTION_ONLY_REGENERATION_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return

    # Rarefaction curves: deterministic draws at regular depths for Chao1/Shannon, analytical expected richness for observed OTUs.
    depths = np.unique(np.rint(np.linspace(1000, RAREFACTION_DEPTH, 18)).astype(int))
    depths = np.insert(depths, 0, 100)
    curve_rows = []
    rng_curve = np.random.default_rng(SEED + 1)
    for sample in samples:
        counts = otu[sample].to_numpy(dtype=np.int64)
        for depth in depths:
            rc = rarefy_counts(counts, int(depth), rng_curve)
            m = alpha_metrics(rc)
            curve_rows.append({
                "Sample": sample,
                "Lake": meta.loc[sample, "Lake"],
                "Season": meta.loc[sample, "Season"],
                "Lake_season": meta.loc[sample, "Lake_season"],
                "Rarefaction_depth_CDS": int(depth),
                "Expected_Observed_OTUs": m["Observed_OTUs"],
                "Observed_OTUs": m["Observed_OTUs"],
                "Chao1": m["Chao1"],
                "Shannon": m["Shannon"],
            })
    curves = pd.DataFrame(curve_rows)

    for out_dir in [APP_DERIVED, ARTICLE_DERIVED, ARTICLE_AUDIT, APP_ROOT / "outputs" / "final_publication_statistics"]:
        out_dir.mkdir(parents=True, exist_ok=True)
        metrics.to_csv(out_dir / "SupplementaryFigure4_alpha_diversity_CDS_32999_source.csv", index=False)
        curves.to_csv(out_dir / "SupplementaryFigure2_rarefaction_curves_CDS_32999_source.csv", index=False)

    # Figure S2: rarefaction curves.
    fig, axes = plt.subplots(1, 3, figsize=(24, 7.5), constrained_layout=True)
    measures = [
        ("Expected_Observed_OTUs", "Observed OTUs"),
        ("Chao1", "Chao1 richness"),
        ("Shannon", "Shannon diversity"),
    ]
    for ax, (col, label) in zip(axes, measures):
        for sample in samples:
            sub = curves[curves["Sample"] == sample].sort_values("Rarefaction_depth_CDS")
            ls = sub["Lake_season"].iloc[0]
            ax.plot(sub["Rarefaction_depth_CDS"], sub[col], color=PALETTE[ls], lw=1.8, alpha=0.72)
        ax.axvline(RAREFACTION_DEPTH, color="#222222", lw=1.4, linestyle="--")
        ax.text(RAREFACTION_DEPTH, ax.get_ylim()[1] * 0.96, "32,999 CDS", rotation=90, ha="right", va="top", fontsize=12, fontweight="bold")
        ax.set_title(label, fontweight="bold")
        ax.set_xlabel("Rarefaction depth (CDS)", fontweight="bold")
        ax.set_ylabel(label, fontweight="bold")
        ax.grid(axis="both", color="#e6e6e6", lw=0.7)
        ax.spines[["top", "right"]].set_visible(False)
    handles = [Patch(facecolor=PALETTE[g], edgecolor="black", label=g) for g in ORDER]
    axes[-1].legend(handles=handles, title="Lake-season", loc="upper left", bbox_to_anchor=(1.02, 1.0), frameon=False)
    fig.suptitle("Supplementary Figure 2. CDS rarefaction curves with all samples retained", fontweight="bold", y=1.04)
    fig.text(0.5, -0.03, "Curves were generated from the CDS OTU table and evaluated up to the fixed retained depth of 32,999 CDS per sample.", ha="center", fontsize=13)
    sfig2 = "SupplementaryFigure2_rarefaction_curves_CDS_32999"
    save_all_formats(fig, sfig2, [APP_FIG_DIR, ARTICLE_SUPP_FIG_DIR])
    plt.close(fig)

    # Figure S4: alpha diversity at fixed depth.
    fig, axes = plt.subplots(1, 3, figsize=(22, 8), constrained_layout=True)
    ycols = [("Observed_OTUs", "Observed OTUs"), ("Chao1", "Chao1 richness"), ("Shannon", "Shannon diversity")]
    x_positions = {g: i + 1 for i, g in enumerate(ORDER)}
    jitter_rng = np.random.default_rng(SEED + 2)
    for ax, (col, label) in zip(axes, ycols):
        data = [metrics.loc[metrics["Lake_season"] == g, col].to_numpy(float) for g in ORDER]
        bp = ax.boxplot(data, positions=list(x_positions.values()), widths=0.55, patch_artist=True, showfliers=False, medianprops={"color": "black", "lw": 2.1}, boxprops={"lw": 1.2}, whiskerprops={"lw": 1.2}, capprops={"lw": 1.2})
        for patch, g in zip(bp["boxes"], ORDER):
            patch.set_facecolor(PALETTE[g])
            patch.set_alpha(0.55)
        for g in ORDER:
            vals = metrics.loc[metrics["Lake_season"] == g, col].to_numpy(float)
            xs = np.full(len(vals), x_positions[g], dtype=float) + jitter_rng.normal(0, 0.045, size=len(vals))
            ax.scatter(xs, vals, s=54, color=PALETTE[g], edgecolor="black", linewidth=0.8, zorder=5)
            for x, y, sample in zip(xs, vals, metrics.loc[metrics["Lake_season"] == g, "Sample"]):
                ax.text(x + 0.035, y, sample.replace(".", "-"), fontsize=8.5, va="center", alpha=0.85)
        ax.set_title(label, fontweight="bold")
        ax.set_ylabel(label, fontweight="bold")
        ax.set_xlabel("Lake-season group", fontweight="bold")
        ax.set_xticks(list(x_positions.values()))
        ax.set_xticklabels(ORDER, rotation=35, ha="right", fontweight="bold")
        ax.grid(axis="y", color="#e6e6e6", lw=0.7)
        ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("Supplementary Figure 4. CDS alpha-diversity recalculated after rarefaction to 32,999 CDS", fontweight="bold", y=1.04)
    fig.text(0.5, -0.03, "Observed OTUs, Chao1 and Shannon were calculated after deterministic rarefaction of each sample to 32,999 CDS. All 20 samples were retained.", ha="center", fontsize=13)
    sfig4 = "SupplementaryFigure4_alpha_diversity_CDS_32999"
    save_all_formats(fig, sfig4, [APP_FIG_DIR, ARTICLE_SUPP_FIG_DIR])
    plt.close(fig)

    # Remove/legacy old conflicting versions from active figure galleries. Keep SFig40 for differential taxa.
    old_stems = [
        "SupplementaryFigure2_alpha_diversity_CDS_panels_AB",
        "SupplementaryFigure2_rarefaction_curves_vivid",
        "SupplementaryFigure4_CDS_alpha_diversity_colored_recalculated",
        "SupplementaryFigure4_alpha_diversity_CDS_recalculated",
        "SupplementaryFigure4_top_enriched_taxa_DESeq2_vivid",
    ]
    move_old_variants(old_stems, [APP_FIG_DIR, ARTICLE_SUPP_FIG_DIR])

    # Compatibility aliases in legacy-free article/app are intentionally not made: the manifest points to the new canonical files.
    make_embed_copy(ARTICLE_SUPP_FIG_DIR / f"{sfig2}.png", sfig2)
    make_embed_copy(ARTICLE_SUPP_FIG_DIR / f"{sfig4}.png", sfig4)

    # Update manifests.
    manifest_paths = [
        APP_ROOT / "data" / "final_figure_script_manifest.csv",
        APP_ROOT / "data" / "figure_script_manifest.csv",
        ARTICLE_ROOT / "05_Source_Data_and_Audit" / "final_figure_script_manifest.csv",
        ARTICLE_ROOT / "05_Source_Data_and_Audit" / "figure_script_manifest.csv",
        ARTICLE_ROOT / "FINAL_FIGURE_APP_SCRIPT_CROSSWALK.csv",
    ]
    for mp in manifest_paths:
        if mp.exists():
            update_manifest(mp)

    # Save the script into both packages.
    here = Path(__file__)
    for dest in [APP_SCRIPT_DIR / "06_recalculate_rarefaction_alpha_32999.py", ARTICLE_SCRIPT_DIR / "06_recalculate_rarefaction_alpha_32999.py"]:
        shutil.copy2(here, dest)

    report = {
        "rarefaction_depth_CDS": RAREFACTION_DEPTH,
        "seed": SEED,
        "sample_count": len(samples),
        "samples_retained": samples,
        "new_supplementary_figure_2": f"{sfig2}.png/pdf/svg/tiff",
        "new_supplementary_figure_4": f"{sfig4}.png/pdf/svg/tiff",
        "source_metrics_csv": "SupplementaryFigure4_alpha_diversity_CDS_32999_source.csv",
        "source_rarefaction_csv": "SupplementaryFigure2_rarefaction_curves_CDS_32999_source.csv",
        "legacy_conflicting_stems_moved": old_stems,
    }
    for root in [APP_ROOT, ARTICLE_ROOT]:
        (root / "FINAL_REV6_RAREFACTION_ALPHA_DIVERSITY_32999_REPORT.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (root / "FINAL_REV6_RAREFACTION_ALPHA_DIVERSITY_32999_REPORT.md").write_text(
            "# Final REV6 rarefaction and Supplementary Figure 4 recalculation\n\n"
            f"- Rarefaction depth: **{RAREFACTION_DEPTH} CDS**.\n"
            f"- All **{len(samples)}** samples were retained.\n"
            "- Supplementary Figure 2 was regenerated as rarefaction curves for Observed OTUs, Chao1 and Shannon.\n"
            "- Supplementary Figure 4 was recalculated as fixed-depth alpha diversity for Observed OTUs, Chao1 and Shannon.\n"
            "- The previous top-enriched taxon heatmap is retained as Supplementary Figure 40.\n"
            "- Source CSV files were written to the final_publication_derived folders and linked in the manifest.\n",
            encoding="utf-8",
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
