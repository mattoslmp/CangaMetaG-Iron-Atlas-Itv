#!/usr/bin/env python3
from __future__ import annotations

"""Update only the 2026-08-05 targeted figure records in repository manifests."""

import argparse
import csv
import hashlib
import json
from pathlib import Path


TARGETS = {
    "Figure 2": "Figure2_taxonomic_phylum_bacteria_horizontal_CDS",
    "Figure 3": "Figure3_taxonomic_phylum_archaea_horizontal_CDS",
    "Figure 4": "Figure4_taxonomic_bacteria_genus_profiles",
    "Figure 5": "Figure5_taxonomic_archaea_genus_profiles",
    "Supplementary Figure 6": "SupplementaryFigure6_MAG_bubble_original",
    "Supplementary Figure 18": "SupplementaryFigure18_RDA_and_physicochemical_heatmap",
    "Supplementary Figure 43": "SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct",
    "Supplementary Figure 45": "SupplementaryFigure45_Taxonomy_Archaea_Phylum_individual_samples_barplot_100pct",
    "Supplementary Figure 59": "SupplementaryFigure59_Taxonomy_Bacteria_Genus_individual_samples_barplot_100pct",
    "Supplementary Figure 61": "SupplementaryFigure61_Taxonomy_Archaea_Genus_individual_samples_barplot_100pct",
}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def update_csv(root: Path, asset_root: Path) -> None:
    path = root / "data" / "final_figure_script_manifest.csv"
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = list(reader)
    by_figure = {row["Figure"]: row for row in rows}
    missing = sorted(set(TARGETS) - set(by_figure))
    if missing:
        raise ValueError(f"Target manifest records not found: {missing}")
    for figure, stem in TARGETS.items():
        row = by_figure[figure]
        is_main = figure.startswith("Figure ")
        is_taxonomy = figure in {"Figure 2", "Figure 3", "Figure 4", "Figure 5", "Supplementary Figure 43", "Supplementary Figure 45", "Supplementary Figure 59", "Supplementary Figure 61"}
        row.update({
            "Description": stem,
            "PNG": f"{stem}.png", "PDF": f"{stem}.pdf", "SVG": f"{stem}.svg",
            "Script": "scripts/generate_targeted_figures_20260805.py",
            "Command": "python scripts/generate_targeted_figures_20260805.py --package-root . --targets all",
            "Usage": "article; application",
            "Panel_count": "1",
            "Title": stem,
            "Panel": "Complete figure",
            "Data_origin": "Canonical packaged study inputs; scientific matrices and frozen ordination results preserved.",
            "Validation_status": "PASS — regenerated, audited and static–interactive parity verified (20260805).",
            "Last_generated_UTC": "2026-08-05T00:00:00+00:00",
            "Notes": "Targeted correction only; no unrelated figure, application module or scientific inference changed.",
        })
        if is_taxonomy:
            row.update({
                "Inputs": "data/resultado.cds.otu.tab; data/resultado.cds.tax.display_current.tab; data/mapeamento_taxonomico.csv; reproducibility/ordination_reproducibility",
                "Purpose": "Apply the strict per-sample <1% display rule and exact Unclassified labels while preserving all source counts and frozen ordinations.",
                "Intermediate_files": "data/final_publication_derived/TAXONOMY_STRICT_LT1_ROW_AUDIT_20260805.csv; data/final_publication_derived/OTHER_TAXA_LT1_TRACEABILITY_20260805.csv; data/final_publication_derived/UNCLASSIFIED_PERCENTAGES_20260805.csv",
                "Parameters": "Classified values strictly <1% per sample -> Other taxa (<1%); exactly 1% explicit; Unclassified independent with exact percentage label; no Top-N.",
                "Filters": "No sample, taxon reaching 1%, Unclassified record or frozen ordination coordinate removed.",
                "Statistical_methods": "No new statistical analysis for taxonomy bars; frozen NMDS/RDA coordinates and statistics are reused for Figures 4 and 5.",
            })
        elif figure == "Supplementary Figure 6":
            row.update({
                "Inputs": "tables/Supplementary_Table_7.xlsx; data/Supplementary_table_7-MAGS-Quality-Genome_Lineage-Classification.xlsx",
                "Purpose": "Display all 49 canonical MAG IDs and all eight lake–season groups with non-empty labels.",
                "Intermediate_files": "data/final_publication_derived/SupplementaryFigure6_MAG_bubble_original_source.csv; validation/targeted_figures_20260805/SupplementaryFigure6_MAG_audit.csv",
                "Parameters": "MAG ID primary key; numeric order; zero-abundance records retained; group means without renormalization.",
                "Filters": "No MAG or lake-season group removed; all 49 unique MAG IDs and all eight canonical groups retained.",
                "Statistical_methods": "Descriptive group means only; no renormalization and no inferential test.",
            })
        else:
            row.update({
                "Inputs": "reproducibility/ordination_reproducibility; data/final_publication_derived/SupplementaryFigure17_physicochemical_row_zscore_source.csv",
                "Purpose": "Plot the frozen RDA results and unchanged physicochemical row-z-score matrix with an external colorbar axis.",
                "Intermediate_files": "data/final_publication_derived/SupplementaryFigure18_RDA_and_physicochemical_heatmap_source.csv; validation/targeted_figures_20260805/SupplementaryFigure18_frozen_data_audit.json",
                "Parameters": "GridSpec colorbar axis outside the heatmap; matrix, limits, order, coordinates, vectors and statistics unchanged.",
                "Filters": "No coordinate, vector, statistic, heatmap row or heatmap column changed.",
                "Statistical_methods": "Frozen RDA/NMDS results and packaged permutation statistics are plotted without recomputation.",
            })
        row["Random_seed"] = "42 (frozen NMDS/RDA; 999 RDA permutations)" if figure in {"Figure 4", "Figure 5", "Supplementary Figure 18"} else "Not applicable — deterministic."
        row["Libraries_and_versions"] = "Python; pandas; NumPy; Matplotlib; Plotly; Pillow; versions in requirements.txt."
        row["Article_location"] = f"article/{'02_Main_Figures' if is_main else '03_Supplementary_Figures'}/{stem}.png"
        row["App_location"] = f"outputs/{'app_main_figures' if is_main else 'app_supplementary_figures'}/{stem}.png"
        for extension, field in (("png", "SHA256_PNG"), ("pdf", "SHA256_PDF"), ("svg", "SHA256_SVG")):
            asset = asset_root / f"{stem}.{extension}"
            if not asset.exists():
                raise FileNotFoundError(asset)
            row[field] = digest(asset)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def update_json(root: Path) -> None:
    path = root / "scripts" / "FINAL_SCRIPT_MANIFEST.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    entry = payload["canonical_scripts"][0]
    entry.update({
        "figure_scope": "Figures 2–5, Supplementary Figures 6/18 and affected supplementary taxonomy barplots",
        "path": "scripts/generate_targeted_figures_20260805.py",
        "status": "canonical_final",
        "app_shared_modules": ["src/article_taxonomy.py", "src/taxonomy_normalization.py", "src/article_frozen_taxonomy_panels.py"],
        "inputs": ["data/resultado.cds.otu.tab", "data/resultado.cds.tax.display_current.tab", "data/mapeamento_taxonomico.csv", "tables/Supplementary_Table_7.xlsx", "reproducibility/ordination_reproducibility"],
        "outputs": [f"outputs/final_publication_figures/{stem}.*" for stem in TARGETS.values()],
        "command": "python scripts/generate_targeted_figures_20260805.py --package-root . --targets all",
        "taxonomy_display_rule": "strictly below 1% per sample -> Other taxa (<1%); exactly 1% explicit; Unclassified separate with exact labels; no Top-N",
        "static_interactive_parity": True,
    })
    payload["manifest_version"] = "2026-08-05-targeted-final"
    payload["compatibility_entry_points"] = [{"path": "scripts/generate_final_domain_taxonomy_figures.py", "delegates_to": "scripts/generate_targeted_figures_20260805.py --targets taxonomy"}]
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def update_commands(root: Path) -> None:
    path = root / "FIGURE_REPRODUCTION_COMMANDS.md"
    lines = path.read_text(encoding="utf-8").splitlines()
    replacements = {}
    for figure, stem in TARGETS.items():
        inputs = "canonical inputs listed in the targeted audit manifest"
        replacements[f"| {figure} |"] = f"| {figure} | `{stem}` | Complete figure | `scripts/generate_targeted_figures_20260805.py` | `python scripts/generate_targeted_figures_20260805.py --package-root . --targets all` | {inputs} |"
    output = []
    for line in lines:
        replacement = next((value for prefix, value in replacements.items() if line.startswith(prefix)), None)
        output.append(replacement or line)
    rule = "Targeted taxonomy rule (2026-08-05): per sample, classified taxa strictly below 1% are grouped as `Other taxa (<1%)`; exactly 1% remains explicit; `Unclassified` is separate with exact percentage labels; no Top-N is applied."
    if rule not in output:
        output.insert(2, rule)
    path.write_text("\n".join(output) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--asset-root", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    assets = (args.asset_root or root / "outputs" / "final_publication_figures").resolve()
    update_csv(root, assets); update_json(root); update_commands(root)
    print("PASS: updated 10 targeted manifest records")


if __name__ == "__main__":
    main()
