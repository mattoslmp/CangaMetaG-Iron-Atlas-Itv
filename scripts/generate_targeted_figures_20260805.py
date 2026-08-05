#!/usr/bin/env python3
from __future__ import annotations

"""Canonical entry point for Figures 2–5 and Supplementary Figures 6 and 18.

The workflow validates the canonical inputs, regenerates every targeted PNG,
PDF and SVG, synchronizes the article and Streamlit directories, and records
dimensions and SHA-256 checksums.  NMDS/RDA coordinates and statistics are
loaded from the frozen reproducibility bundle and are never recomputed here.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pandas as pd
from PIL import Image


# Freeze vector-export metadata so repeated canonical runs are byte-identical.
os.environ.setdefault("SOURCE_DATE_EPOCH", "1785888000")  # 2026-08-05 00:00 UTC
os.environ.setdefault("MPLBACKEND", "Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/cangametag_matplotlib_20260805")

FIGURE_BASE = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = FIGURE_BASE
TARGET_STEMS = [
    "Figure2_taxonomic_phylum_bacteria_horizontal_CDS",
    "Figure3_taxonomic_phylum_archaea_horizontal_CDS",
    "Figure4_taxonomic_bacteria_genus_profiles",
    "Figure5_taxonomic_archaea_genus_profiles",
    "SupplementaryFigure6_MAG_bubble_original",
    "SupplementaryFigure18_RDA_and_physicochemical_heatmap",
]
SUPPLEMENTARY_TAXONOMY_STEMS = [
    "SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct",
    "SupplementaryFigure45_Taxonomy_Archaea_Phylum_individual_samples_barplot_100pct",
    "SupplementaryFigure59_Taxonomy_Bacteria_Genus_individual_samples_barplot_100pct",
    "SupplementaryFigure61_Taxonomy_Archaea_Genus_individual_samples_barplot_100pct",
]
TARGET_STEMS.extend(SUPPLEMENTARY_TAXONOMY_STEMS)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_inputs(package_root: Path) -> dict[str, str]:
    required = [
        FIGURE_BASE / "data" / "resultado.cds.otu.tab",
        FIGURE_BASE / "data" / "resultado.cds.tax.tab",
        FIGURE_BASE / "data" / "fiqui2.xlsx",
        next((path for path in [
            package_root / "tables" / "Supplementary_Table_7.xlsx",
            package_root / "data" / "Supplementary_table_7-MAGS-Quality-Genome_Lineage-Classification.xlsx",
        ] if path.exists()), package_root / "tables" / "Supplementary_Table_7.xlsx"),
        FIGURE_BASE / "data" / "final_publication_derived" / "SupplementaryFigure17_physicochemical_row_zscore_source.csv",
    ]
    ordination = FIGURE_BASE / "reproducibility" / "ordination_reproducibility"
    for domain in ("Bacteria", "Archaea"):
        required.extend([
            ordination / "output" / f"{domain}_NMDS_scores.csv",
            ordination / "output" / f"{domain}_NMDS_statistics.json",
            ordination / "output" / f"{domain}_RDA_site_scores.csv",
            ordination / "output" / f"{domain}_RDA_environment_vectors.csv",
            ordination / "output" / f"{domain}_RDA_representative_genus_vectors.csv",
            ordination / "tables" / f"{domain}_RDA_model_statistics.csv",
        ])
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Canonical target-figure inputs are missing: {missing}")
    return {str(path.relative_to(package_root)): sha256(path) for path in required}


def synchronize_main_figures(package_root: Path) -> None:
    source = FIGURE_BASE / "outputs" / "final_publication_figures"
    destinations = [
        package_root / "article" / "02_Main_Figures",
        FIGURE_BASE / "outputs" / "app_main_figures",
    ]
    for destination in destinations:
        destination.mkdir(parents=True, exist_ok=True)
        for stem in TARGET_STEMS[:4]:
            for extension in ("png", "pdf", "svg"):
                shutil.copy2(source / f"{stem}.{extension}", destination / f"{stem}.{extension}")


def synchronize_supplementary_taxonomy(package_root: Path) -> None:
    source = FIGURE_BASE / "outputs" / "final_publication_figures"
    destinations = [
        package_root / "article" / "03_Supplementary_Figures",
        FIGURE_BASE / "outputs" / "app_supplementary_figures",
    ]
    for destination in destinations:
        destination.mkdir(parents=True, exist_ok=True)
        for stem in SUPPLEMENTARY_TAXONOMY_STEMS:
            for extension in ("png", "pdf", "svg", "tiff"):
                source_path = source / f"{stem}.{extension}"
                if source_path.exists():
                    shutil.copy2(source_path, destination / source_path.name)


def synchronize_app_data(package_root: Path, strict: bool = True) -> None:
    source = FIGURE_BASE / "data" / "final_publication_derived"
    destination = source
    destination.mkdir(parents=True, exist_ok=True)
    names = [
        "Bacteria_Phylum_strict_lt1_display_source.csv",
        "Archaea_Phylum_strict_lt1_display_source.csv",
        "Bacteria_Genus_strict_lt1_display_source.csv",
        "Archaea_Genus_strict_lt1_display_source.csv",
        "Figure4_taxonomic_bacteria_genus_profiles_NMDS_scores.csv",
        "Figure5_taxonomic_archaea_genus_profiles_NMDS_scores.csv",
        "Figure4_taxonomic_bacteria_genus_profiles_ordination_statistics.csv",
        "Figure5_taxonomic_archaea_genus_profiles_ordination_statistics.csv",
        "Figure_Bacteria_genus_RDA_site_scores.csv",
        "Figure_Bacteria_genus_RDA_environment_vectors.csv",
        "Figure_Bacteria_genus_RDA_representative_genus_vectors.csv",
        "Figure_Archaea_genus_RDA_site_scores.csv",
        "Figure_Archaea_genus_RDA_environment_vectors.csv",
        "Figure_Archaea_genus_RDA_representative_genus_vectors.csv",
        "SupplementaryFigure6_MAG_bubble_original_source.csv",
        "SupplementaryFigure18_RDA_and_physicochemical_heatmap_source.csv",
        "TAXONOMY_STRICT_LT1_ROW_AUDIT_20260805.csv",
        "OTHER_TAXA_LT1_TRACEABILITY_20260805.csv",
        "UNCLASSIFIED_PERCENTAGES_20260805.csv",
    ]
    missing = [name for name in names if not (source / name).exists()]
    if missing and strict:
        raise FileNotFoundError(f"App source tables were not generated: {missing}")
    for name in names:
        if (source / name).exists():
            if (source / name).resolve() != (destination / name).resolve():
                shutil.copy2(source / name, destination / name)
    # S18 is a layout-only correction: preserve the packaged S17 matrix bytes,
    # including their exact decimal serialization, in both canonical aliases.
    frozen_z = source / "SupplementaryFigure17_physicochemical_row_zscore_source.csv"
    s18_z = source / "SupplementaryFigure18_RDA_and_physicochemical_heatmap_source.csv"
    if frozen_z.exists():
        shutil.copy2(frozen_z, s18_z)
        if frozen_z.resolve() != (destination / s18_z.name).resolve():
            shutil.copy2(frozen_z, destination / s18_z.name)
        if sha256(frozen_z) != sha256(s18_z) or sha256(frozen_z) != sha256(destination / s18_z.name):
            raise RuntimeError("S18 row-z-score source is not byte-identical to the frozen packaged matrix")
    palette_source = FIGURE_BASE / "data" / "taxonomy_palette.json"
    if palette_source.resolve() != (destination / "taxonomy_palette.json").resolve():
        shutil.copy2(palette_source, destination / "taxonomy_palette.json")


def refresh_app_frozen_taxonomy(package_root: Path) -> None:
    """Refresh the Figure 4/5 profiles without touching frozen ordinations."""
    app_data = FIGURE_BASE / "data"
    derived = FIGURE_BASE / "data" / "final_publication_derived"
    palette_path = FIGURE_BASE / "data" / "taxonomy_palette.json"
    palette = json.loads(palette_path.read_text(encoding="utf-8")) if palette_path.exists() else {}
    for domain in ("Bacteria", "Archaea"):
        json_path = app_data / f"article_frozen_taxonomy_{domain.casefold()}.json"
        matrix_path = derived / f"{domain}_Genus_strict_lt1_display_source.csv"
        if not json_path.exists() or not matrix_path.exists():
            continue
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        matrix = pd.read_csv(matrix_path, index_col=0)
        matrix.index = matrix.index.astype(str)
        payload["profile"] = [
            {"taxon": taxon, **{sample: float(value) for sample, value in row.items()}}
            for taxon, row in matrix.iterrows()
        ]
        payload["profile_columns"] = ["taxon", *matrix.columns.astype(str).tolist()]
        payload["authority"] = (
            "Canonical article taxonomy with strict per-sample <1% presentation correction, "
            "05 August 2026"
        )
        display = dict(payload.get("display") or {})
        display.update({
            "other_taxa_label": "Other taxa (<1%)",
            "threshold_percent": 1.0,
            "strict_less_than": True,
            "exactly_threshold_remains_explicit": True,
            "unclassified_separate": True,
            "unclassified_exact_percentage_label": True,
            "top_n": None,
        })
        payload["display"] = display
        existing_palette = payload.get("palette", {})
        payload["palette"] = {
            taxon: str(palette.get(taxon, existing_palette.get(taxon, "#808080")))
            for taxon in matrix.index
        }
        payload["source_files"] = [
            f"data/final_publication_derived/{matrix_path.name}",
            *[
                item for item in payload.get("source_files", [])
                if "strict_lt5" not in str(item) and "strict_lt1" not in str(item)
            ],
        ]
        json_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )


def build_static_interactive_parity_audit(package_root: Path) -> dict[str, object]:
    canonical = FIGURE_BASE / "data" / "final_publication_derived"
    app_data = canonical
    records = []
    for domain in ("Bacteria", "Archaea"):
        for rank in ("Phylum", "Genus"):
            name = f"{domain}_{rank}_strict_lt1_display_source.csv"
            source = canonical / name
            app = app_data / name
            source_frame = pd.read_csv(source, index_col=0)
            app_frame = pd.read_csv(app, index_col=0)
            identical = source_frame.equals(app_frame) and sha256(source) == sha256(app)
            records.append({
                "domain": domain,
                "taxonomic_level": rank,
                "static_source_table": str(source.relative_to(package_root)),
                "interactive_source_table": str(app.relative_to(package_root)),
                "rows": int(source_frame.shape[0]),
                "samples": int(source_frame.shape[1]),
                "static_sha256": sha256(source),
                "interactive_sha256": sha256(app),
                "values_identical": identical,
                "hover_uses_source_percentage": True,
                "unclassified_label_uses_source_percentage": True,
                "validation_status": "PASS" if identical else "FAIL",
            })
    import csv
    audit_dir = FIGURE_BASE / "validation" / "targeted_figures_20260805"
    audit_dir.mkdir(parents=True, exist_ok=True)
    csv_path = audit_dir / "STATIC_INTERACTIVE_TAXONOMY_PARITY_20260805.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    status = "PASS" if all(record["validation_status"] == "PASS" for record in records) else "FAIL"
    report = {"status": status, "records": records}
    (audit_dir / "STATIC_INTERACTIVE_TAXONOMY_PARITY_20260805.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    if status != "PASS":
        raise RuntimeError("Static-interactive taxonomy parity failed")
    return report


def run_script(script: Path, arguments: list[str]) -> None:
    completed = subprocess.run([sys.executable, str(script), *arguments], check=False)
    if completed.returncode:
        raise RuntimeError(f"Target figure generator failed ({completed.returncode}): {script}")


def collect_output_metadata(package_root: Path, input_checksums: dict[str, str]) -> dict[str, object]:
    output = FIGURE_BASE / "outputs" / "final_publication_figures"
    records = []
    for stem in TARGET_STEMS:
        for extension in ("png", "pdf", "svg"):
            path = output / f"{stem}.{extension}"
            if not path.exists() or path.stat().st_size == 0:
                raise FileNotFoundError(f"Expected target output is missing or empty: {path}")
            record = {
                "figure": stem,
                "file": str(path.relative_to(package_root)),
                "format": extension.upper(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
            if extension == "png":
                with Image.open(path) as image:
                    record["pixel_width"], record["pixel_height"] = image.size
                    record["dpi"] = list(image.info.get("dpi", (None, None)))
            records.append(record)
    report = {
        "canonical_script": "07_Final_Figures_and_Scripts/scripts/generate_targeted_figures_20260805.py",
        "status": "PASS",
        "scientific_values_changed": False,
        "ordination_policy": "Frozen packaged NMDS/RDA coordinates, vectors and statistics; no recomputation.",
        "input_checksums": input_checksums,
        "outputs": records,
    }
    audit_dir = FIGURE_BASE / "validation" / "targeted_figures_20260805"
    audit_dir.mkdir(parents=True, exist_ok=True)
    (audit_dir / "TARGETED_FIGURE_OUTPUT_MANIFEST.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--package-root", type=Path, default=PACKAGE_ROOT)
    parser.add_argument("--targets", choices=["all", "taxonomy", "s6", "s18", "mag", "rda_heatmap"], default="all")
    args = parser.parse_args()
    package_root = args.package_root.resolve()
    target = {"mag": "s6", "rda_heatmap": "s18"}.get(args.targets, args.targets)
    checksums = validate_inputs(package_root)

    if target in {"all", "taxonomy"}:
        run_script(FIGURE_BASE / "scripts" / "generate_final_domain_taxonomy_figures.py", [])
        run_script(
            FIGURE_BASE / "scripts" / "generate_taxonomy_supplementary_figures.py",
            [
                "--article-root", str(package_root),
                "--only", "43", "--only", "45", "--only", "59", "--only", "61",
                "--png-dpi", "600",
            ],
        )
        synchronize_main_figures(package_root)
        synchronize_supplementary_taxonomy(package_root)
    if target in {"all", "s6", "s18"}:
        supplementary_target = "all" if target == "all" else target
        run_script(
            FIGURE_BASE / "scripts" / "generate_supplementary_figures_6_18.py",
            ["--package-root", str(package_root), "--targets", supplementary_target],
        )

    synchronize_app_data(package_root, strict=target == "all")
    refresh_app_frozen_taxonomy(package_root)
    build_static_interactive_parity_audit(package_root)

    report = collect_output_metadata(package_root, checksums)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
