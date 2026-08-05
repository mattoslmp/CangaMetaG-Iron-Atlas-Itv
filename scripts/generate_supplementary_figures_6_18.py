#!/usr/bin/env python3
from __future__ import annotations

"""Generate Supplementary Figures 6 and 18 from canonical frozen inputs.

Supplementary Figure 6 uses the complete unique MAG catalogue and the
individual-sample abundance matrix stored in Supplementary Table 7.  The
individual samples are averaged within the eight documented lake-season
groups; no MAG, including zero-abundance MAGs, is filtered.

Supplementary Figure 18 uses the packaged, frozen RDA scores, environmental
vectors, representative-genus vectors, statistics, and physicochemical
row-z-score matrix.  No ordination or statistical model is recomputed.
"""

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import sys
from pathlib import Path

os.environ.setdefault("SOURCE_DATE_EPOCH", "1785888000")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/cangametag_matplotlib_20260805")
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "cangametag-targeted-20260805"
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd


FIGURE_BASE = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = FIGURE_BASE
if str(FIGURE_BASE) not in sys.path:
    sys.path.insert(0, str(FIGURE_BASE))
if str(FIGURE_BASE / "scripts") not in sys.path:
    sys.path.insert(0, str(FIGURE_BASE / "scripts"))
if str(FIGURE_BASE / "scripts" / "figures") not in sys.path:
    sys.path.insert(0, str(FIGURE_BASE / "scripts" / "figures"))

from generate_ordinations_revision4 import draw_rda  # noqa: E402
from src.taxonomy_palette import load_palette  # noqa: E402


MAG_STEM = "SupplementaryFigure6_MAG_bubble_original"
RDA_STEM = "SupplementaryFigure18_RDA_and_physicochemical_heatmap"
GROUP_ORDER = ["AM-D", "AM-R", "TI-D", "TI-R", "TIA-D", "TIA-R", "VI-D", "VI-R"]
SAMPLE_GROUPS = {
    "AM-D": ["AM11", "AM21"],
    "AM-R": ["AM12", "AM22"],
    "TI-D": ["TI111", "TI121", "TI211", "TI331"],
    "TI-R": ["TI112", "TI122", "TI212", "TI332"],
    "TIA-D": ["TI311", "TI321"],
    "TIA-R": ["TI312", "TI322"],
    "VI-D": ["V11", "V21"],
    "VI-R": ["V12", "V22"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def numeric_mag_id(value: object) -> str | None:
    match = re.search(r"MAG\.\s*([0-9]+)", str(value))
    return f"MAG.{int(match.group(1))}" if match else None


def numeric_bin_id(value: object) -> str | None:
    match = re.search(r"bin\.\s*([0-9]+)", str(value), flags=re.IGNORECASE)
    return f"MAG.{int(match.group(1))}" if match else None


def clean_taxonomy(value: object) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "Unclassified"
    text = re.sub(r"\s+", " ", str(value)).strip(" ;—-")
    return text if text and text.casefold() not in {"nan", "none", "not classified"} else "Unclassified"


def save_native(fig: plt.Figure, output_dir: Path, stem: str, dpi: int = 600) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = {}
    for extension in ("png", "pdf", "svg"):
        path = output_dir / f"{stem}.{extension}"
        fig.savefig(
            path,
            dpi=dpi if extension == "png" else None,
            bbox_inches="tight",
            pad_inches=0.08,
            facecolor="white",
        )
        generated[path.name] = sha256(path)
    plt.close(fig)
    return generated


def copy_outputs(stem: str, package_root: Path) -> None:
    source = FIGURE_BASE / "outputs" / "final_publication_figures"
    destinations = [
        FIGURE_BASE / "outputs" / "app_supplementary_figures",
        package_root / "article" / "03_Supplementary_Figures",
    ]
    for destination in destinations:
        destination.mkdir(parents=True, exist_ok=True)
        for extension in ("png", "pdf", "svg"):
            shutil.copy2(source / f"{stem}.{extension}", destination / f"{stem}.{extension}")


def load_mag_data(package_root: Path) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    candidates = [
        package_root / "tables" / "Supplementary_Table_7.xlsx",
        package_root / "data" / "Supplementary_table_7-MAGS-Quality-Genome_Lineage-Classification.xlsx",
        package_root / "06_Supplementary_Tables" / "Supplementary_Table_7.xlsx",
    ]
    table_path = next((path for path in candidates if path.exists()), candidates[0])
    if not table_path.exists():
        raise FileNotFoundError(f"Required Supplementary Table 7 input not found; checked: {candidates}")

    classification = pd.read_excel(table_path, sheet_name="bin.classification", header=3)
    required_classification = {"MAG", "Species definition"}
    missing_columns = required_classification - set(classification.columns)
    if missing_columns:
        raise ValueError(f"Supplementary Table 7 classification sheet is missing columns: {sorted(missing_columns)}")
    classification = classification.loc[classification["MAG"].notna(), ["MAG", "Species definition"]].copy()
    classification["MAG_ID"] = classification["MAG"].map(numeric_mag_id)
    if classification["MAG_ID"].isna().any():
        bad = classification.loc[classification["MAG_ID"].isna(), "MAG"].astype(str).tolist()
        raise ValueError(f"Invalid MAG identifiers in Supplementary Table 7: {bad}")
    classification["taxonomy_label"] = classification["Species definition"].map(clean_taxonomy)
    source_duplicates = sorted(classification.loc[classification["MAG_ID"].duplicated(keep=False), "MAG_ID"].unique())
    taxonomy = classification.drop_duplicates("MAG_ID", keep="first").set_index("MAG_ID")["taxonomy_label"]

    abundance = pd.read_excel(table_path, sheet_name="Bins-quant", usecols="J:AD")
    if "Genomic bins" not in abundance.columns:
        raise ValueError("Supplementary Table 7 abundance sheet lacks the 'Genomic bins' column")
    abundance = abundance.loc[abundance["Genomic bins"].notna()].copy()
    abundance["MAG_ID"] = abundance["Genomic bins"].map(numeric_bin_id)
    if abundance["MAG_ID"].isna().any():
        bad = abundance.loc[abundance["MAG_ID"].isna(), "Genomic bins"].astype(str).tolist()
        raise ValueError(f"Invalid bin identifiers in Supplementary Table 7: {bad}")
    if abundance["MAG_ID"].duplicated().any():
        duplicates = abundance.loc[abundance["MAG_ID"].duplicated(keep=False), "MAG_ID"].tolist()
        raise ValueError(f"Duplicated MAG identifiers in the abundance matrix: {duplicates}")

    sample_columns = [sample for samples in SAMPLE_GROUPS.values() for sample in samples]
    missing_samples = sorted(set(sample_columns) - set(abundance.columns))
    unexpected_samples = sorted(set(abundance.columns) - {"Genomic bins", "MAG_ID"} - set(sample_columns))
    if missing_samples or unexpected_samples:
        raise ValueError(
            f"Lake-season sample mapping mismatch; missing={missing_samples}, unexpected={unexpected_samples}"
        )
    abundance[sample_columns] = abundance[sample_columns].apply(pd.to_numeric, errors="coerce")
    if abundance[sample_columns].isna().any().any():
        raise ValueError("Non-numeric or missing abundance values found in Supplementary Table 7")
    if (abundance[sample_columns].to_numpy(float) < 0).any():
        raise ValueError("Negative abundance values found in Supplementary Table 7")
    abundance = abundance.set_index("MAG_ID")[sample_columns]

    matrix_ids = set(abundance.index)
    table_ids = set(taxonomy.index)
    if matrix_ids != table_ids:
        raise ValueError(
            "MAG identifier mismatch between Supplementary Table 7 sheets: "
            f"classification_only={sorted(table_ids - matrix_ids)}, abundance_only={sorted(matrix_ids - table_ids)}"
        )

    ordered_ids = sorted(matrix_ids, key=lambda value: int(value.split(".")[1]))
    grouped = pd.DataFrame(index=ordered_ids, columns=GROUP_ORDER, dtype=float)
    for group in GROUP_ORDER:
        grouped[group] = abundance.loc[ordered_ids, SAMPLE_GROUPS[group]].mean(axis=1)
    labels = pd.DataFrame({
        "MAG_ID": ordered_ids,
        "taxonomy_label": [clean_taxonomy(taxonomy.loc[mag]) for mag in ordered_ids],
    })
    labels["display_label"] = labels["MAG_ID"] + " — " + labels["taxonomy_label"]
    if labels["display_label"].str.strip().eq("").any() or labels["taxonomy_label"].str.strip().eq("").any():
        raise ValueError("Empty MAG labels remain after taxonomy normalization")
    if labels["MAG_ID"].duplicated().any():
        raise ValueError("Duplicated MAG identifiers remain in the figure label table")

    source_summary = {
        "supplementary_table_7_rows": int(len(classification)),
        "supplementary_table_7_unique_mag_ids": int(len(table_ids)),
        "source_duplicate_mag_ids_resolved_by_primary_key": source_duplicates,
        "source_matrix_mag_ids": int(len(matrix_ids)),
        "catalogue_ids": ordered_ids,
        "missing_numeric_identifiers_between_1_and_50": [
            f"MAG.{index}" for index in range(1, 51) if f"MAG.{index}" not in matrix_ids
        ],
        "aggregation": "Arithmetic mean of the packaged individual-sample abundances within each documented lake-season group; no renormalization.",
        "sample_groups": SAMPLE_GROUPS,
    }
    return grouped, labels, source_summary


def make_supplementary_figure_6(package_root: Path) -> dict[str, object]:
    grouped, labels, source_summary = load_mag_data(package_root)
    output_dir = FIGURE_BASE / "outputs" / "final_publication_figures"
    derived_dir = FIGURE_BASE / "data" / "final_publication_derived"
    audit_dir = FIGURE_BASE / "validation" / "targeted_figures_20260805"
    derived_dir.mkdir(parents=True, exist_ok=True)
    audit_dir.mkdir(parents=True, exist_ok=True)

    long = grouped.rename_axis("MAG_ID").reset_index().melt(
        id_vars="MAG_ID", var_name="lake_season_group", value_name="abundance"
    )
    long = long.merge(labels, on="MAG_ID", how="left", validate="many_to_one")
    long["lake_season_group"] = pd.Categorical(long["lake_season_group"], GROUP_ORDER, ordered=True)
    long = long.sort_values(["MAG_ID", "lake_season_group"], key=lambda series: (
        series.map(lambda value: int(str(value).split(".")[1])) if series.name == "MAG_ID" else series
    )).reset_index(drop=True)
    source_path = derived_dir / f"{MAG_STEM}_source.csv"
    long.to_csv(source_path, index=False)

    maximum = float(grouped.to_numpy(float).max())
    if maximum <= 0:
        maximum = 1.0
    x_values = np.tile(np.arange(len(GROUP_ORDER)), len(grouped))
    y_values = np.repeat(np.arange(len(grouped)), len(GROUP_ORDER))
    values = grouped.to_numpy(float).reshape(-1)
    sizes = 14.0 + 430.0 * np.sqrt(np.clip(values / maximum, 0, 1))

    fig = plt.figure(figsize=(17.5, 24.0), constrained_layout=False)
    grid = fig.add_gridspec(1, 2, width_ratios=[1.0, 0.035], wspace=0.055)
    ax = fig.add_subplot(grid[0, 0])
    cax = fig.add_subplot(grid[0, 1])
    scatter = ax.scatter(
        x_values,
        y_values,
        s=sizes,
        c=values,
        cmap="viridis",
        vmin=0.0,
        vmax=maximum,
        edgecolors="#2F2F2F",
        linewidths=0.30,
    )
    ax.set_xticks(np.arange(len(GROUP_ORDER)), GROUP_ORDER, fontsize=12.5, fontweight="bold")
    ax.set_yticks(np.arange(len(labels)), labels["display_label"], fontsize=8.7)
    ax.invert_yaxis()
    ax.set_xlim(-0.6, len(GROUP_ORDER) - 0.4)
    ax.set_ylim(len(labels) - 0.35, -0.65)
    ax.set_xlabel("Lake-season group", fontsize=15, fontweight="bold", labelpad=10)
    ax.set_ylabel("Metagenome-assembled genome and taxonomy", fontsize=15, fontweight="bold", labelpad=12)
    ax.set_title(
        "Relative abundance of all recovered metagenome-assembled genomes",
        fontsize=19,
        fontweight="bold",
        pad=16,
    )
    ax.set_axisbelow(True)
    ax.grid(axis="both", color="#E5E7EB", linewidth=0.55)
    ax.spines[["top", "right"]].set_visible(False)
    colorbar = fig.colorbar(scatter, cax=cax)
    colorbar.set_label("Mean relative abundance", fontsize=13.5, fontweight="bold", labelpad=10)
    colorbar.ax.tick_params(labelsize=11.5)

    positive = values[values > 0]
    if positive.size:
        legend_values = np.unique(np.quantile(positive, [0.25, 0.50, 0.75, 1.0]).round(4))
        handles = [
            Line2D(
                [0], [0], marker="o", linestyle="None", color="#2F2F2F",
                markerfacecolor="#BDBDBD",
                markersize=math.sqrt(14.0 + 430.0 * math.sqrt(float(value) / maximum)) / 1.7,
                label=f"{value:g}",
            )
            for value in legend_values
        ]
        ax.legend(
            handles=handles,
            title="Bubble size: mean abundance",
            loc="upper center",
            bbox_to_anchor=(0.5, -0.058),
            ncol=min(4, len(handles)),
            frameon=False,
            fontsize=10.5,
            title_fontsize=11.5,
        )
    fig.subplots_adjust(left=0.45, right=0.93, bottom=0.115, top=0.955)
    generated = save_native(fig, output_dir, MAG_STEM, dpi=600)
    copy_outputs(MAG_STEM, package_root)

    audit_rows = []
    figure_ids = set(long["MAG_ID"])
    table_ids = set(labels["MAG_ID"])
    for mag_id in grouped.index:
        before = float(grouped.loc[mag_id].sum())
        after = float(long.loc[long["MAG_ID"].eq(mag_id), "abundance"].sum())
        row = {
            "MAG_ID": mag_id,
            "taxonomy_label": labels.set_index("MAG_ID").at[mag_id, "taxonomy_label"],
            "present_in_Supplementary_Table_7": mag_id in table_ids,
            "present_in_source_matrix": mag_id in grouped.index,
            "present_in_figure": mag_id in figure_ids,
            "duplicated_MAG_ID": bool(long.loc[long["MAG_ID"].eq(mag_id), "lake_season_group"].duplicated().any()),
            "missing_label": not bool(labels.set_index("MAG_ID").at[mag_id, "taxonomy_label"].strip()),
            "number_of_lake_season_groups": int(long.loc[long["MAG_ID"].eq(mag_id), "lake_season_group"].nunique()),
            "abundance_sum_before": before,
            "abundance_sum_after": after,
        }
        row["validation_status"] = "PASS" if (
            row["present_in_Supplementary_Table_7"]
            and row["present_in_source_matrix"]
            and row["present_in_figure"]
            and not row["duplicated_MAG_ID"]
            and not row["missing_label"]
            and row["number_of_lake_season_groups"] == len(GROUP_ORDER)
            and math.isclose(before, after, rel_tol=0.0, abs_tol=1e-12)
        ) else "FAIL"
        audit_rows.append(row)
    audit = pd.DataFrame(audit_rows)
    audit_path = audit_dir / "SupplementaryFigure6_MAG_audit.csv"
    audit.to_csv(audit_path, index=False)
    if not audit["validation_status"].eq("PASS").all():
        raise RuntimeError("Supplementary Figure 6 MAG audit contains FAIL rows")

    report = {
        "figure": MAG_STEM,
        "status": "PASS",
        "scientific_values_changed": False,
        "catalogue": source_summary,
        "source_table": str(source_path.relative_to(FIGURE_BASE)),
        "audit_table": str(audit_path.relative_to(FIGURE_BASE)),
        "generated_files": generated,
    }
    (audit_dir / "SupplementaryFigure6_MAG_audit_summary.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def load_frozen_rda(domain: str) -> dict[str, object]:
    root = FIGURE_BASE / "reproducibility" / "ordination_reproducibility"
    output = root / "output"
    tables = root / "tables"
    required = [
        output / f"{domain}_RDA_site_scores.csv",
        output / f"{domain}_RDA_environment_vectors.csv",
        output / f"{domain}_RDA_representative_genus_vectors.csv",
        tables / f"{domain}_RDA_model_statistics.csv",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Frozen RDA inputs are missing: {missing}")
    scores = pd.read_csv(required[0]).set_index("Sample")
    vectors = pd.read_csv(required[1]).set_index("Variable")[["RDA1", "RDA2"]]
    taxa = pd.read_csv(required[2]).set_index("Genus")[["RDA1", "RDA2"]]
    stats = pd.read_csv(required[3]).iloc[0]
    return {
        "scores": scores,
        "vectors": vectors,
        "taxon_vectors": taxa,
        "pct": (
            float(stats["RDA1_constrained_variance_percent"]),
            float(stats["RDA2_constrained_variance_percent"]),
        ),
        "r2": float(stats["R2"]),
        "adjusted_r2": float(stats["adjusted_R2"]),
        "F": float(stats["pseudo_F"]),
        "p": float(stats["global_permutation_p"]),
        "permutations": int(stats["permutations"]),
        "seed": int(stats["seed"]),
        "source_checksums": {path.name: sha256(path) for path in required},
    }


def make_supplementary_figure_18(package_root: Path) -> dict[str, object]:
    bacterial = load_frozen_rda("Bacteria")
    archaeal = load_frozen_rda("Archaea")
    z_source = FIGURE_BASE / "data" / "final_publication_derived" / "SupplementaryFigure17_physicochemical_row_zscore_source.csv"
    if not z_source.exists():
        raise FileNotFoundError(f"Frozen physicochemical matrix is missing: {z_source}")
    z = pd.read_csv(z_source, index_col=0)
    if (z.index.astype(str).str.strip() == "").any() or (z.columns.astype(str).str.strip() == "").any():
        raise ValueError("Frozen physicochemical matrix contains empty row or column identifiers")
    if z.isna().any().any():
        raise ValueError("Frozen physicochemical row-z-score matrix contains missing values")

    palette = load_palette(FIGURE_BASE / "data" / "taxonomy_palette.json")
    fig = plt.figure(figsize=(20.0, 14.5), constrained_layout=False)
    grid = fig.add_gridspec(
        2,
        3,
        width_ratios=[1.0, 1.0, 0.035],
        height_ratios=[1.28, 0.74],
        wspace=0.20,
        hspace=0.31,
    )
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, :2])
    cax = fig.add_subplot(grid[1, 2])
    draw_rda(ax_a, bacterial, palette, "A", "Bacterial genus-level RDA")
    draw_rda(ax_b, archaeal, palette, "B", "Archaeal genus-level RDA")
    ax_a.set_title(
        f"A  Bacterial genus-level RDA\nR² = {bacterial['r2']:.3f}; adjusted R² = {bacterial['adjusted_r2']:.3f}; P = {bacterial['p']:.3f}",
        loc="left", fontsize=15.5, fontweight="bold", pad=9,
    )
    ax_b.set_title(
        f"B  Archaeal genus-level RDA\nR² = {archaeal['r2']:.3f}; adjusted R² = {archaeal['adjusted_r2']:.3f}; P = {archaeal['p']:.3f}",
        loc="left", fontsize=15.5, fontweight="bold", pad=9,
    )

    values = z.to_numpy(float)
    vmax = max(abs(float(np.min(values))), abs(float(np.max(values))))
    image = ax_c.imshow(values, aspect="auto", cmap="coolwarm_r", vmin=-vmax, vmax=vmax, interpolation="nearest")
    ax_c.set_xticks(np.arange(z.shape[1]), z.columns, rotation=42, ha="right", rotation_mode="anchor", fontsize=13)
    ax_c.set_yticks(np.arange(z.shape[0]), z.index, fontsize=13)
    ax_c.set_xlabel("Sampling position", fontsize=15, fontweight="bold", labelpad=10)
    ax_c.set_ylabel("Physicochemical variable", fontsize=15, fontweight="bold")
    ax_c.set_title("C  Descriptive physicochemical row-z-score heatmap", loc="left", fontsize=17, fontweight="bold", pad=10)
    ax_c.set_xticks(np.arange(-0.5, z.shape[1], 1), minor=True)
    ax_c.set_yticks(np.arange(-0.5, z.shape[0], 1), minor=True)
    ax_c.grid(which="minor", color="white", linewidth=0.8)
    ax_c.tick_params(which="minor", bottom=False, left=False)
    ax_c.tick_params(length=0, pad=5)
    colorbar = fig.colorbar(image, cax=cax)
    colorbar.set_label("Row z-score", fontsize=14, fontweight="bold", labelpad=10)
    colorbar.ax.tick_params(labelsize=12)
    fig.subplots_adjust(left=0.055, right=0.965, bottom=0.08, top=0.965)

    output_dir = FIGURE_BASE / "outputs" / "final_publication_figures"
    generated = save_native(fig, output_dir, RDA_STEM, dpi=600)
    copy_outputs(RDA_STEM, package_root)
    derived_dir = FIGURE_BASE / "data" / "final_publication_derived"
    new_z_source = derived_dir / f"{RDA_STEM}_source.csv"
    shutil.copy2(z_source, new_z_source)
    if sha256(z_source) != sha256(new_z_source):
        raise RuntimeError("Supplementary Figure 18 frozen z-score matrix changed during the layout-only regeneration")

    audit_dir = FIGURE_BASE / "validation" / "targeted_figures_20260805"
    audit_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "figure": RDA_STEM,
        "status": "PASS",
        "scientific_values_changed": False,
        "heatmap_source_checksum_before": sha256(z_source),
        "heatmap_source_checksum_after": sha256(new_z_source),
        "heatmap_shape": [int(z.shape[0]), int(z.shape[1])],
        "heatmap_rows": z.index.astype(str).tolist(),
        "heatmap_columns": z.columns.astype(str).tolist(),
        "heatmap_limits": [-vmax, vmax],
        "Bacteria": {
            "R2": bacterial["r2"],
            "adjusted_R2": bacterial["adjusted_r2"],
            "pseudo_F": bacterial["F"],
            "P": bacterial["p"],
            "permutations": bacterial["permutations"],
            "seed": bacterial["seed"],
            "source_checksums": bacterial["source_checksums"],
        },
        "Archaea": {
            "R2": archaeal["r2"],
            "adjusted_R2": archaeal["adjusted_r2"],
            "pseudo_F": archaeal["F"],
            "P": archaeal["p"],
            "permutations": archaeal["permutations"],
            "seed": archaeal["seed"],
            "source_checksums": archaeal["source_checksums"],
        },
        "layout_validation": {
            "dedicated_colorbar_axis": True,
            "colorbar_outside_heatmap": True,
            "heatmap_axis_grid": "GridSpec[1,0:2]",
            "colorbar_axis_grid": "GridSpec[1,2]",
        },
        "generated_files": generated,
    }
    (audit_dir / "SupplementaryFigure18_frozen_data_audit.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, default=PACKAGE_ROOT)
    parser.add_argument("--targets", choices=["all", "s6", "s18"], default="all")
    args = parser.parse_args()
    package_root = args.package_root.resolve()
    reports = {}
    if args.targets in {"all", "s6"}:
        reports["Supplementary Figure 6"] = make_supplementary_figure_6(package_root)
    if args.targets in {"all", "s18"}:
        reports["Supplementary Figure 18"] = make_supplementary_figure_18(package_root)
    print(json.dumps(reports, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
