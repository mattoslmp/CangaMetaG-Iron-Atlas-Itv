#!/usr/bin/env python3
"""Canonical generator for Supplementary Figure 37 only.

The packaged thematic MAG module-status matrix is read without recalculation.
This script cannot generate S40, S67 or environmental-group alternatives.
"""
from __future__ import annotations

import argparse
import math
import re
import shutil
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

STATUS_ORDER = ("Incomplete", "1 block missing", "Complete")
STATUS_COLORS = {"Incomplete": "#D73027", "1 block missing": "#4575B4", "Complete": "#2E7D32"}
STATUS_CODE = {status: index for index, status in enumerate(STATUS_ORDER)}
CMAP = ListedColormap([STATUS_COLORS[s] for s in STATUS_ORDER])
NORM = BoundaryNorm(np.arange(-0.5, len(STATUS_ORDER) + 0.5, 1), CMAP.N)
S37_STEM = "SupplementaryFigure37_MAG_KEGG_module_completeness_heatmap_species_MAGnumber_KEMET_style_3state"
META_COLUMNS = {"__module_id__", "Module_name", "Biogeochemical_cycle", "Relation_to_iron", "Table_S8_biomarker_KOs", "Reason_for_inclusion"}

def normalize_status(value):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return "Missing data"
    text = " ".join(str(value).strip().split()).casefold()
    if not text or text in {"nan", "none", "null", "missing", "no data"}:
        return "Missing data"
    if text == "complete":
        return "Complete"
    if "1 block" in text:
        return "1 block missing"
    return "Incomplete"


def load_matrix(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"__module_id__", "Module_name"}
    if not required.issubset(df.columns):
        raise ValueError(f"Missing required columns in {path}: {sorted(required - set(df.columns))}")
    df["Module"] = df["__module_id__"].astype(str).str.strip() + " | " + df["Module_name"].astype(str).str.strip()
    cols = [c for c in df.columns if c not in META_COLUMNS and c != "Module"]
    out = df[["Module", *cols]].copy()
    for c in cols:
        out[c] = out[c].map(normalize_status)
    if out["Module"].duplicated().any():
        raise ValueError(f"Duplicated modules in {path}")
    if len(cols) != len(set(cols)):
        raise ValueError(f"Duplicated record columns in {path}")
    return out


def module_label(value, width):
    text = " ".join(str(value).split())
    module_id, description = text.split("|", 1)
    return module_id.strip() + " |\n" + textwrap.fill(description.strip(), width=width, break_long_words=False)


def mag_identifier(value):
    match = re.search(r"\bMAG\d+\b", str(value))
    if not match:
        raise ValueError(f"MAG identifier not found: {value}")
    return match.group(0)


def source_taxonomy(value):
    text = " ".join(str(value).strip().split())
    mag = mag_identifier(text)
    tax = re.sub(r"\s*-\s*" + re.escape(mag) + r"\s*$", "", text).strip(" -")
    return tax or "Unclassified"


def abbreviated_taxonomy(value):
    tax = source_taxonomy(value)
    replacements = (
        ("Candidatus ", "Ca. "),
        (" bacterium", " bact."),
        (" archaeon", " arch."),
        ("Unclassified MAG", "Unclassified"),
    )
    for old, new in replacements:
        tax = tax.replace(old, new)
    return tax


def mag_display_label(value):
    return f"{mag_identifier(value)} | {abbreviated_taxonomy(value)}"


def build_mag_key(columns):
    rows = []
    for position, original in enumerate(columns, start=1):
        rows.append({
            "Column order": position,
            "MAG identifier": mag_identifier(original),
            "Taxonomic label used in figure": abbreviated_taxonomy(original),
            "Full source taxonomic classification": source_taxonomy(original),
            "Original matrix column": str(original),
        })
    result = pd.DataFrame(rows)
    if len(result) != len(columns) or result["MAG identifier"].duplicated().any():
        raise ValueError("MAG label mapping does not match the matrix columns")
    return result


def panel_figure(matrix, x_labels, title, panel_index, panel_count, y_wrap, y_font, x_font, left_margin, bottom=0.205, figure_width=16.54):
    if len(x_labels) != matrix.shape[1] - 1:
        raise ValueError("The number of x-axis labels differs from the number of matrix columns")
    fig = plt.figure(figsize=(figure_width, 11.20), facecolor="white")
    ax = fig.add_axes([left_margin, bottom, 0.985-left_margin, 0.925-bottom])
    numeric = matrix.iloc[:, 1:].replace({**STATUS_CODE, "Missing data": np.nan})
    array = numeric.to_numpy(float)
    nrows, ncols = array.shape
    masked = np.ma.masked_invalid(array)
    cmap = CMAP.copy()
    cmap.set_bad("white")
    ax.pcolormesh(np.arange(ncols+1), np.arange(nrows+1), masked, cmap=cmap, norm=NORM, shading="flat", edgecolors="white", linewidth=0.45, rasterized=True)
    ax.set_xlim(0, ncols)
    ax.set_ylim(nrows, 0)
    ax.set_xticks(np.arange(ncols)+0.5)
    ax.set_xticklabels(x_labels, rotation=45, ha="right", va="top", rotation_mode="anchor", fontsize=x_font)
    ax.set_yticks(np.arange(nrows)+0.5)
    ax.set_yticklabels([module_label(v, y_wrap) for v in matrix["Module"]], fontsize=y_font, ha="right", va="center", linespacing=1.04)
    ax.tick_params(axis="x", length=0, pad=5)
    ax.tick_params(axis="y", length=0, pad=6)
    ax.set_xlabel("")
    ax.set_ylabel("KEGG/KEMET module and metabolic pathway", fontsize=12.5, fontweight="bold", labelpad=12)
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.text(0.02, 0.985, f"{title} - Panel P{panel_index:03d} of P{panel_count:03d}", ha="left", va="top", fontsize=16, fontweight="bold")
    handles = [Patch(facecolor=STATUS_COLORS[s], edgecolor="none", label=s) for s in ("Complete", "1 block missing", "Incomplete")]
    fig.legend(handles=handles, title="KEMET module status", loc="lower center", bbox_to_anchor=(0.5, 0.012), ncol=3, frameon=False, fontsize=10.5, title_fontsize=11.5, handlelength=1.5, columnspacing=1.8)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    ax_box = ax.get_window_extent(renderer)
    if any(label.get_window_extent(renderer).y1 > ax_box.y0+2 for label in ax.get_xticklabels()):
        raise RuntimeError("x-axis labels overlap the heatmap")
    y_boxes = [label.get_window_extent(renderer) for label in ax.get_yticklabels()]
    for previous, current in zip(y_boxes, y_boxes[1:]):
        if previous.y0 < current.y1-1:
            raise RuntimeError("adjacent y-axis labels overlap")
    return fig


def save_figure_set(matrix, x_labels, output_dirs, stem, title, panel_count, y_wrap, y_font, x_font, left_margin, bottom=0.205, figure_width=16.54):
    """Paginate MAG columns, never rows, so every module remains visible per page."""
    value_columns = list(matrix.columns[1:])
    if len(value_columns) != len(x_labels):
        raise ValueError("MAG column/label count mismatch")
    column_chunks = np.array_split(np.arange(len(value_columns)), panel_count)
    pdf_handles = [PdfPages(str(directory/f"{stem}.pdf")) for directory in output_dirs]
    try:
        for i, indices in enumerate(column_chunks, start=1):
            selected_columns = [value_columns[j] for j in indices]
            selected_labels = [x_labels[j] for j in indices]
            sub = pd.concat([matrix[["Module"]], matrix[selected_columns]], axis=1).reset_index(drop=True)
            fig = panel_figure(sub, selected_labels, title, i, panel_count, y_wrap, y_font, x_font, left_margin, bottom=bottom, figure_width=figure_width)
            for directory, pdf in zip(output_dirs, pdf_handles):
                directory.mkdir(parents=True, exist_ok=True)
                base = directory/f"{stem}_P{i:03d}"
                fig.savefig(base.with_suffix(".png"), dpi=300, facecolor="white")
                fig.savefig(base.with_suffix(".pdf"), facecolor="white")
                fig.savefig(base.with_suffix(".svg"), facecolor="white")
                pdf.savefig(fig, facecolor="white")
            plt.close(fig)
    finally:
        for handle in pdf_handles:
            handle.close()
    # Keep the historical base-name assets for manifest compatibility.  The app
    # intentionally displays the full-resolution P001/P002 pages instead.
    for directory in output_dirs:
        shutil.copy2(directory/f"{stem}_P001.png", directory/f"{stem}.png")
        shutil.copy2(directory/f"{stem}_P001.svg", directory/f"{stem}.svg")


def resolve(root):
    input_dir = root/"data"/"module_figure_inputs"
    if (root/"outputs").exists():
        outputs = [root/"outputs"/"final_publication_figures", root/"outputs"/"app_supplementary_figures"]
        table_dir = root/"tables"
        derived_dir = root/"data"/"final_publication_derived"
        validation_dir = root/"validation"
    else:
        outputs = [root/"03_Supplementary_Figures"]
        table_dir = root/"04_Supplementary_Tables"
        derived_dir = root/"05_Source_Data_and_Audit"/"final_publication_derived"
        validation_dir = root/"07_Validation_and_Manifests"
    return input_dir, outputs, table_dir, derived_dir, validation_dir


def main():
    parser = argparse.ArgumentParser(description="Generate only the final Supplementary Figure 37 MAG module-completeness heatmap.")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    root = args.root.resolve()
    inputs, outputs, table_dir, derived_dir, _validation_dir = resolve(root)
    s37_path = inputs / f"{S37_STEM}_thematic_status.csv"
    s37 = load_matrix(s37_path)
    for directory in outputs:
        directory.mkdir(parents=True, exist_ok=True)
        for path in directory.glob(S37_STEM + "*"):
            if path.is_file():
                path.unlink()
    mag_labels = [mag_display_label(c) for c in s37.columns[1:]]
    save_figure_set(
        s37, mag_labels, outputs, S37_STEM,
        "Thematic MAG KEGG/KEMET module completeness",
        2, 42, 10.0, 8.5, 0.27, bottom=0.285, figure_width=18.50,
    )
    table_dir.mkdir(parents=True, exist_ok=True)
    mag_key = build_mag_key(list(s37.columns[1:]))
    mag_key.to_csv(table_dir / "MAG_taxonomic_label_key_for_Supplementary_Figure_37.csv", index=False)
    derived_dir.mkdir(parents=True, exist_ok=True)
    mag_key.to_csv(derived_dir / "MAG_taxonomic_label_key_for_Supplementary_Figure_37.csv", index=False)


if __name__ == "__main__":
    main()
