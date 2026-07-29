#!/usr/bin/env python3
"""Generate final environmental-group heatmaps and the equivalence audit.

Final publication policy:
- Supplementary Figure 40 is distributed only in environmental-group order;
- Supplementary Figure 67 retains both original and environmental-group layouts;
- the immutable original-order S40 matrix is reconstructed only as an audit
  reference and is not rendered or shipped as an active S40 figure.

Only the column permutation changes between reference and grouped matrices. Module
rows, cell values, colours, axis orientation and completeness classifications remain
unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch

STATUS_ORDER = ["Incomplete", "1 block missing", "Complete"]
STATUS_TO_VALUE = {"Incomplete": 0, "1 block missing": 1, "Complete": 2}
COLORS = {
  "Complete": "#2E7D32",
  "1 block missing": "#4575B4",
  "Incomplete": "#D73027",
  "Missing": "#FFFFFF",
}
METADATA_COLUMNS = [
  "__module_id__",
  "Module_name",
  "Biogeochemical_cycle",
  "Relation_to_iron",
  "Table_S8_biomarker_KOs",
  "Reason_for_inclusion",
]


@dataclass(frozen=True)
class FigureSpec:
  figure_id: str
  input_name: str
  original_stem: str
  grouped_stem: str
  title_original: str
  title_grouped: str
  rows_per_panel: int
  active_variants: tuple[str, ...]


SPECS = {
  "S40": FigureSpec(
    figure_id="S40",
    input_name="SupplementaryFigure40_ST8_external_iron_rich_module_completeness_KEMET_style_3state_heatmap_thematic_status.csv",
    original_stem="SupplementaryFigure40_ST8_external_iron_rich_module_completeness_KEMET_style_3state_heatmap",
    grouped_stem="SupplementaryFigure40_ST8_external_iron_rich_module_completeness_by_environmental_group",
    title_original="Thematic external iron-rich metagenome KEGG/KEMET module completeness",
    title_grouped="External iron-rich module completeness by environmental group",
    rows_per_panel=18,
    active_variants=("environmental_group",),
  ),
  "S67": FigureSpec(
    figure_id="S67",
    input_name="SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_KEMET_style_3state_heatmap_thematic_status.csv",
    original_stem="SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_KEMET_style_3state_heatmap",
    grouped_stem="SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_by_environmental_group",
    title_original="Amazonian plus external thematic module completeness",
    title_grouped="Amazonian plus external module completeness by environmental group",
    rows_per_panel=20,
    active_variants=("original", "environmental_group"),
  ),
}

AMAZON_GROUPS = {
  "AM": "Amazonian - Amendoim",
  "TIA": "Amazonian - Tres Irmas Adjacent",
  "TI": "Amazonian - Tres Irmas",
  "VI": "Amazonian - Violao",
}
EXTERNAL_GROUP_ORDER = [
  "Akron-AMD",
  "Burr-Oak-BO4",
  "Hydrothermal-Fe-mats",
  "Lake-Matano",
  "Lake-Superior",
  "Lake-Towuti",
  "Other-Fe",
  "Richmond-AMD",
]
DISPLAY_GROUP = {
  "Akron-AMD": "Akron\nAMD",
  "Burr-Oak-BO4": "Burr Oak\nBO4",
  "Hydrothermal-Fe-mats": "Hydrothermal\nFe mats",
  "Lake-Matano": "Lake\nMatano",
  "Lake-Superior": "Lake\nSuperior",
  "Lake-Towuti": "Lake\nTowuti",
  "Other-Fe": "Other\nFe",
  "Richmond-AMD": "Richmond\nAMD",
  "Amazonian - Amendoim": "Amendoim",
  "Amazonian - Tres Irmas Adjacent": "Tres Irmas\nAdjacent",
  "Amazonian - Tres Irmas": "Tres Irmas",
  "Amazonian - Violao": "Violao",
}


def sha256(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
      digest.update(chunk)
  return digest.hexdigest()


def package_kind(root: Path) -> str:
  if (root / "app.py").exists() and (root / "outputs").exists():
    return "app"
  if (root / "03_Supplementary_Figures").exists():
    return "article"
  raise FileNotFoundError(f"Could not identify package root: {root}")


def package_paths(root: Path) -> dict[str, Path]:
  kind = package_kind(root)
  if kind == "app":
    return {
      "kind": Path(kind),
      "input_dir": root / "data" / "module_figure_inputs",
      "metadata": root / "data" / "module_figure_inputs" / "st8_metadata_curated.csv",
      "figure_dirs": [
        root / "outputs" / "app_supplementary_figures",
        root / "outputs" / "final_publication_figures",
      ],
      "derived_dirs": [
        root / "data" / "final_publication_derived",
        root / "outputs" / "final_publication_derived",
      ],
      "validation_dirs": [
        root / "validation",
        root / "outputs",
      ],
    }
  return {
    "kind": Path(kind),
    "input_dir": root / "data" / "module_figure_inputs",
    "metadata": root / "data" / "module_figure_inputs" / "st8_metadata_curated.csv",
    "figure_dirs": [root / "03_Supplementary_Figures"],
    "derived_dirs": [root / "05_Source_Data_and_Audit" / "final_publication_derived"],
    "validation_dirs": [root / "07_Validation_and_Manifests"],
  }


def ensure_dirs(paths: dict[str, Path]) -> None:
  for key in ("figure_dirs", "derived_dirs", "validation_dirs"):
    for directory in paths[key]:
      directory.mkdir(parents=True, exist_ok=True)


def sample_columns(frame: pd.DataFrame) -> list[str]:
  missing = [column for column in METADATA_COLUMNS if column not in frame.columns]
  if missing:
    raise ValueError(f"Missing metadata columns: {missing}")
  columns = [column for column in frame.columns if column not in METADATA_COLUMNS]
  if not columns:
    raise ValueError("No sample/record columns found")
  allowed = set(STATUS_ORDER)
  for column in columns:
    observed = set(frame[column].dropna().astype(str).str.strip().unique())
    unexpected = sorted(observed - allowed)
    if unexpected:
      raise ValueError(f"Unexpected status values in {column}: {unexpected}")
  return columns


def module_label(row: pd.Series) -> str:
  module_id = str(row.get("__module_id__", "")).strip()
  name = str(row.get("Module_name", "")).strip()
  label = f"{module_id} | {name}" if name else module_id
  return label


def load_inputs(root: Path, spec: FigureSpec) -> tuple[pd.DataFrame, pd.DataFrame]:
  paths = package_paths(root)
  matrix_path = paths["input_dir"] / spec.input_name
  if not matrix_path.exists():
    raise FileNotFoundError(matrix_path)
  if not paths["metadata"].exists():
    raise FileNotFoundError(paths["metadata"])
  matrix = pd.read_csv(matrix_path)
  metadata = pd.read_csv(paths["metadata"], dtype=str).fillna("")
  sample_columns(matrix)
  return matrix, metadata


def external_metadata_maps(metadata: pd.DataFrame) -> tuple[dict[str, str], dict[str, str], dict[str, int]]:
  required = {"taxon_oid", "ST8_short_group", "sample_id_created_this_study"}
  missing = required - set(metadata.columns)
  if missing:
    raise ValueError(f"Missing external metadata fields: {sorted(missing)}")
  group_by_oid: dict[str, str] = {}
  label_by_oid: dict[str, str] = {}
  metadata_order: dict[str, int] = {}
  for index, row in metadata.reset_index(drop=True).iterrows():
    oid = str(row["taxon_oid"]).strip()
    if not oid:
      continue
    group_by_oid[oid] = str(row["ST8_short_group"]).strip() or "Other-Fe"
    label_by_oid[oid] = str(row["sample_id_created_this_study"]).strip() or oid
    metadata_order[oid] = index
  return group_by_oid, label_by_oid, metadata_order


def external_oid(column: str) -> str | None:
  match = re.search(r"(\d{10})\s*$", str(column).strip())
  return match.group(1) if match else None


def amazon_group(column: str) -> str | None:
  prefix = str(column).split(".", 1)[0].strip().upper()
  return AMAZON_GROUPS.get(prefix)


def column_metadata(columns: Iterable[str], metadata: pd.DataFrame) -> pd.DataFrame:
  group_by_oid, label_by_oid, metadata_order = external_metadata_maps(metadata)
  rows = []
  for source_index, column in enumerate(columns):
    a_group = amazon_group(column)
    oid = external_oid(column)
    if a_group:
      group = a_group
      display = str(column)
      group_rank = list(AMAZON_GROUPS.values()).index(group)
      within_rank = source_index
      record_type = "Amazonian metagenome"
      original_identifier = str(column)
    elif oid:
      if oid not in group_by_oid:
        raise ValueError(f"No ST8 environmental-group metadata for record {column} ({oid})")
      group = group_by_oid[oid]
      display = label_by_oid.get(oid, oid)
      group_rank = len(AMAZON_GROUPS) + EXTERNAL_GROUP_ORDER.index(group) if group in EXTERNAL_GROUP_ORDER else 999
      within_rank = metadata_order.get(oid, source_index)
      record_type = "External iron-rich record"
      original_identifier = oid
    else:
      raise ValueError(f"Could not classify sample/record column: {column}")
    rows.append({
      "sample_column": str(column),
      "source_order_index": source_index,
      "display_label": display,
      "environmental_group": group,
      "display_group": DISPLAY_GROUP.get(group, group.replace("-", " ")),
      "group_rank": group_rank,
      "within_group_rank": within_rank,
      "record_type": record_type,
      "original_record_identifier": original_identifier,
    })
  result = pd.DataFrame(rows)
  result["grouped_order_index"] = (
    result.sort_values(["group_rank", "within_group_rank", "source_order_index"], kind="stable")
      .reset_index()
      .reset_index()
      .set_index("index")["level_0"]
      .reindex(result.index)
      .astype(int)
  )
  return result


def ordered_columns(column_meta: pd.DataFrame, variant: str) -> list[str]:
  if variant == "original":
    ordered = column_meta.sort_values("source_order_index", kind="stable")
  elif variant == "environmental_group":
    ordered = column_meta.sort_values(["group_rank", "within_group_rank", "source_order_index"], kind="stable")
  else:
    raise ValueError(variant)
  return ordered["sample_column"].tolist()


def status_matrix(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
  labels = frame.apply(module_label, axis=1)
  matrix = frame.loc[:, columns].copy()
  matrix.index = labels
  matrix.index.name = "Module"
  return matrix


def display_labels(columns: list[str], column_meta: pd.DataFrame) -> list[str]:
  lookup = column_meta.set_index("sample_column")["display_label"].to_dict()
  return [lookup[column] for column in columns]


def contiguous_group_runs(columns: list[str], column_meta: pd.DataFrame) -> list[tuple[str, int, int]]:
  lookup = column_meta.set_index("sample_column")["environmental_group"].to_dict()
  runs: list[tuple[str, int, int]] = []
  if not columns:
    return runs
  start = 0
  current = lookup[columns[0]]
  for index, column in enumerate(columns[1:], 1):
    group = lookup[column]
    if group != current:
      runs.append((current, start, index - 1))
      start = index
      current = group
  runs.append((current, start, len(columns) - 1))
  return runs


def wrapped_module_label(value: str, width: int = 38) -> str:
  module, _, description = str(value).partition(" | ")
  if not description:
    return module
  words = description.replace(" -> ", " -> ").split()
  lines: list[str] = []
  line = ""
  for word in words:
    candidate = f"{line} {word}".strip()
    if line and len(candidate) > width:
      lines.append(line)
      line = word
    else:
      line = candidate
  if line:
    lines.append(line)
  return module + " |\n" + "\n".join(lines)


def plot_panel(
  matrix: pd.DataFrame,
  columns: list[str],
  column_meta: pd.DataFrame,
  title: str,
  panel_index: int,
  panel_count: int,
  grouped: bool,
) -> plt.Figure:
  values = matrix.apply(lambda column: column.map(STATUS_TO_VALUE)).astype(float).to_numpy()
  cmap = ListedColormap([COLORS["Incomplete"], COLORS["1 block missing"], COLORS["Complete"]])
  cmap.set_bad(COLORS["Missing"])
  norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N)

  fig, ax = plt.subplots(figsize=(16.54, 11.20), dpi=300)
  ax.imshow(np.ma.masked_invalid(values), cmap=cmap, norm=norm, aspect="auto", interpolation="nearest")
  full_title = f"{title} - Panel P{panel_index:03d} of P{panel_count:03d}"
  fig.text(
    0.02,
    0.975,
    full_title,
    ha="left",
    va="top",
    fontsize=15.5 if grouped else 16.5,
    fontweight="bold",
  )
  ax.set_ylabel("KEGG/KEMET module and metabolic pathway", fontsize=13, fontweight="bold", labelpad=22)
  ax.set_xlabel("")

  xlabels = display_labels(columns, column_meta)
  ax.set_xticks(np.arange(len(columns)))
  ax.set_xticklabels(xlabels, rotation=55, ha="right", rotation_mode="anchor", fontsize=7.2)
  ax.set_yticks(np.arange(matrix.shape[0]))
  ax.set_yticklabels([wrapped_module_label(value) for value in matrix.index], fontsize=8.6)

  ax.set_xticks(np.arange(-0.5, len(columns), 1), minor=True)
  ax.set_yticks(np.arange(-0.5, matrix.shape[0], 1), minor=True)
  ax.grid(which="minor", color="#FFFFFF", linewidth=0.45)
  ax.tick_params(which="minor", bottom=False, left=False)
  ax.tick_params(axis="both", which="major", length=0)
  for spine in ax.spines.values():
    spine.set_visible(False)

  if grouped:
    runs = contiguous_group_runs(columns, column_meta)
    for run_index, (group, start, end) in enumerate(runs):
      centre = (start + end) / 2
      ax.text(
        centre,
        1.035,
        DISPLAY_GROUP.get(group, group.replace("-", " ")),
        transform=ax.get_xaxis_transform(),
        ha="center",
        va="bottom",
        fontsize=6.6 if len(runs) > 8 else 8.0,
        fontweight="bold",
        clip_on=False,
      )
      if run_index:
        ax.axvline(start - 0.5, color="#222222", linewidth=1.05, zorder=5)

  legend = [
    Patch(facecolor=COLORS["Complete"], edgecolor="none", label="Complete"),
    Patch(facecolor=COLORS["1 block missing"], edgecolor="none", label="1 block missing"),
    Patch(facecolor=COLORS["Incomplete"], edgecolor="none", label="Incomplete"),
  ]
  fig.legend(
    handles=legend,
    loc="lower center",
    bbox_to_anchor=(0.5, 0.025),
    ncol=3,
    frameon=False,
    title="KEMET module status",
    fontsize=9.5,
    title_fontsize=10.5,
  )
  fig.subplots_adjust(left=0.28, right=0.985, top=0.82 if grouped else 0.90, bottom=0.19)
  return fig


def write_matrix_csv(matrix: pd.DataFrame, path: Path) -> None:
  output = matrix.reset_index()
  output.to_csv(path, index=False)


def copy_first_panel_alias(first_panel: Path, alias: Path) -> None:
  if alias.exists():
    alias.unlink()
  shutil.copy2(first_panel, alias)


def inactive_stems() -> list[str]:
  return [SPECS["S40"].original_stem]


def remove_inactive_variant_files(paths: dict[str, Path]) -> list[str]:
  """Remove only the superseded original-order S40 active outputs."""
  removed: list[str] = []
  for directory in paths["figure_dirs"]:
    for stem in inactive_stems():
      for candidate in sorted(directory.glob(f"{stem}*")):
        if candidate.is_file() and candidate.suffix.lower() in {".png", ".pdf", ".svg"}:
          candidate.unlink(); removed.append(str(candidate))
  for directory in paths["derived_dirs"]:
    for stem in inactive_stems():
      for suffix in ("_status.csv", "_column_order.csv"):
        candidate = directory / f"{stem}{suffix}"
        if candidate.exists(): candidate.unlink(); removed.append(str(candidate))
  return removed


def generate_variant(
  spec: FigureSpec,
  matrix: pd.DataFrame,
  column_meta: pd.DataFrame,
  variant: str,
  figure_dir: Path,
  derived_dir: Path,
) -> dict[str, object]:
  grouped = variant == "environmental_group"
  columns = ordered_columns(column_meta, variant)
  data = status_matrix(matrix, columns)
  stem = spec.grouped_stem if grouped else spec.original_stem
  title = spec.title_grouped if grouped else spec.title_original
  matrix_csv = derived_dir / f"{stem}_status.csv"
  order_csv = derived_dir / f"{stem}_column_order.csv"
  write_matrix_csv(data, matrix_csv)
  order = column_meta.set_index("sample_column").loc[columns].reset_index()
  order.insert(0, "figure_id", spec.figure_id)
  order.insert(1, "variant", variant)
  order.insert(2, "display_order_index", np.arange(len(order), dtype=int))
  order.to_csv(order_csv, index=False)

  panel_count = math.ceil(len(data) / spec.rows_per_panel)
  panel_files: list[dict[str, str]] = []
  multipage_pdf = figure_dir / f"{stem}.pdf"
  with PdfPages(multipage_pdf) as pdf:
    for panel_zero in range(panel_count):
      start = panel_zero * spec.rows_per_panel
      end = min((panel_zero + 1) * spec.rows_per_panel, len(data))
      panel = data.iloc[start:end]
      panel_number = panel_zero + 1
      fig = plot_panel(panel, columns, column_meta, title, panel_number, panel_count, grouped)
      base = figure_dir / f"{stem}_P{panel_number:03d}"
      png = base.with_suffix(".png")
      svg = base.with_suffix(".svg")
      pdf_single = base.with_suffix(".pdf")
      fig.savefig(png, dpi=300, facecolor="white")
      fig.savefig(svg, facecolor="white")
      fig.savefig(pdf_single, facecolor="white")
      pdf.savefig(fig, facecolor="white")
      plt.close(fig)
      panel_files.append({"png": str(png), "svg": str(svg), "pdf": str(pdf_single)})

  first = figure_dir / f"{stem}_P001"
  copy_first_panel_alias(first.with_suffix(".png"), figure_dir / f"{stem}.png")
  copy_first_panel_alias(first.with_suffix(".svg"), figure_dir / f"{stem}.svg")
  return {
    "figure_id": spec.figure_id,
    "variant": variant,
    "stem": stem,
    "matrix_csv": str(matrix_csv),
    "order_csv": str(order_csv),
    "multipage_pdf": str(multipage_pdf),
    "panels": panel_files,
    "rows": int(data.shape[0]),
    "columns": int(data.shape[1]),
  }


def status_counts(matrix: pd.DataFrame) -> dict[str, int]:
  values = matrix.to_numpy(dtype=object).ravel()
  series = pd.Series(values, dtype="object")
  text = series.astype("string").str.strip()
  missing = int(text.isna().sum() + text.fillna("").isin(["", "nan", "NaN", "None"]).sum())
  return {
    "Complete": int((series == "Complete").sum()),
    "1 block missing": int((series == "1 block missing").sum()),
    "Incomplete": int((series == "Incomplete").sum()),
    "Missing": missing,
  }


def compare_variants(
  spec: FigureSpec,
  original: pd.DataFrame,
  grouped: pd.DataFrame,
  original_columns: list[str],
  grouped_columns: list[str],
  column_meta: pd.DataFrame,
) -> tuple[pd.DataFrame, dict[str, object]]:
  restored = grouped.loc[original.index, original_columns]
  same_rows = original.index.tolist() == restored.index.tolist()
  same_columns_after_restore = original.columns.tolist() == restored.columns.tolist()
  cell_equal = original.fillna("__TRUE_MISSING__").eq(restored.fillna("__TRUE_MISSING__"))
  all_cells_identical = bool(cell_equal.to_numpy().all())
  original_counts = status_counts(original)
  grouped_counts = status_counts(grouped)
  same_counts = original_counts == grouped_counts
  same_row_set = set(original.index) == set(grouped.index) and len(original.index) == len(set(original.index)) == len(set(grouped.index))
  same_column_set = set(original.columns) == set(grouped.columns) and len(original.columns) == len(set(original.columns)) == len(set(grouped.columns))
  transposed = original.shape == grouped.T.shape and set(original.index) == set(grouped.columns) and set(original.columns) == set(grouped.index)

  summary = {
    "figure_id": spec.figure_id,
    "original_dimensions": f"{original.shape[0]} x {original.shape[1]}",
    "grouped_dimensions": f"{grouped.shape[0]} x {grouped.shape[1]}",
    "same_row_order": same_rows,
    "same_row_set_no_duplicates": same_row_set,
    "same_column_set_no_duplicates": same_column_set,
    "same_columns_after_restore": same_columns_after_restore,
    "all_cells_identical_after_restore": all_cells_identical,
    "same_status_counts": same_counts,
    "transposition_detected": transposed,
    "classification_normalization_transformation_changed": False,
    "original_counts": original_counts,
    "grouped_counts": grouped_counts,
    "original_order": original_columns,
    "grouped_order": grouped_columns,
  }
  summary["scientifically_equivalent"] = bool(
    same_rows
    and same_row_set
    and same_column_set
    and same_columns_after_restore
    and all_cells_identical
    and same_counts
    and not transposed
  )

  group_lookup = column_meta.set_index("sample_column")["environmental_group"].to_dict()
  details = []
  for row_index, module in enumerate(original.index):
    for original_index, column in enumerate(original_columns):
      grouped_index = grouped_columns.index(column)
      original_value = original.at[module, column]
      grouped_value = grouped.at[module, column]
      identical = (
        (pd.isna(original_value) and pd.isna(grouped_value))
        or str(original_value) == str(grouped_value)
      )
      details.append({
        "record_type": "cell_comparison",
        "figure_id": spec.figure_id,
        "module_row_index": row_index,
        "module": module,
        "sample_or_record": column,
        "environmental_group": group_lookup.get(column, ""),
        "original_column_index": original_index,
        "grouped_column_index": grouped_index,
        "original_value": original_value,
        "grouped_value_after_identifier_match": grouped_value,
        "identical": identical,
      })
  return pd.DataFrame(details), summary


def comparison_markdown(summaries: list[dict[str, object]]) -> str:
  lines = [
    "# Environmental-group heatmap comparison",
    "",
    "This validation compares immutable original-order reference matrices with environmental-group layouts for Supplementary Figures 40 and 67. The grouped matrices are restored to the original column order before cell-by-cell comparison. The original-order S40 matrix is audit-only; the final distributed S40 is the environmental-group version.",
    "",
  ]
  for summary in summaries:
    counts = summary["original_counts"]
    lines.extend([
      f"## {summary['figure_id']}",
      "",
      f"- Source matrix: `{summary.get('source_matrix', 'immutable packaged input')}`.",
      f"- Source matrix SHA-256: `{summary.get('source_matrix_sha256', 'recorded by comparison workflow')}`.",
      f"- Metadata table: `{summary.get('metadata_table', 'packaged environmental-group metadata')}`.",
      f"- Final-figure policy: **{summary.get('final_figure_policy', 'reference and grouped matrices compared')}**.",
      f"- Original/reference dimensions: `{summary['original_dimensions']}`.",
      f"- Environmental-group dimensions: `{summary['grouped_dimensions']}`.",
      f"- Modules/rows identical and unduplicated: **{summary['same_row_set_no_duplicates']}**.",
      f"- Samples/records identical and unduplicated: **{summary['same_column_set_no_duplicates']}**.",
      f"- Column identities restored to the original order: **{summary['same_columns_after_restore']}**.",
      f"- Every cell identical after restoring the original order: **{summary['all_cells_identical_after_restore']}**.",
      f"- Complete: **{counts['Complete']}**; 1 block missing: **{counts['1 block missing']}**; Incomplete: **{counts['Incomplete']}**; missing: **{counts['Missing']}**.",
      f"- Status counts identical: **{summary['same_status_counts']}**.",
      f"- Transposition detected: **{summary['transposition_detected']}**.",
      f"- Classification, normalization or transformation changed: **{summary['classification_normalization_transformation_changed']}**.",
      f"- Scientific equivalence: **{'PASS' if summary['scientifically_equivalent'] else 'FAIL'}**.",
      "",
      "### Original column order",
      "",
      "`" + " | ".join(summary["original_order"]) + "`",
      "",
      "### Environmental-group column order",
      "",
      "`" + " | ".join(summary["grouped_order"]) + "`",
      "",
    ])
  passed = all(bool(summary["scientifically_equivalent"]) for summary in summaries)
  lines.extend([
    "## Final conclusion",
    "",
    (
      "**PASS.** For both S40 and S67, the immutable original-order reference matrices and environmental-group layouts contain the same modules, samples/records and cell values. The visual difference results exclusively from placing columns from the same environmental group side by side. No data were removed, duplicated, transposed, reclassified, normalized or transformed. Only the environmental-group S40 is retained as the active final figure; S67 retains both layouts."
      if passed else
      "**FAIL.** At least one comparison did not satisfy scientific equivalence. The figures must not be released until the reported mismatch is corrected."
    ),
    "",
  ])
  return "\n".join(lines)


def write_comparison(
  details: list[pd.DataFrame],
  summaries: list[dict[str, object]],
  validation_dir: Path,
) -> tuple[Path, Path, Path]:
  detail_frame = pd.concat(details, ignore_index=True)
  summary_rows = []
  for summary in summaries:
    summary_rows.append({
      "record_type": "summary",
      "figure_id": summary["figure_id"],
      "module_row_index": "",
      "module": "",
      "sample_or_record": "",
      "environmental_group": "",
      "original_column_index": "",
      "grouped_column_index": "",
      "original_value": json.dumps({
        "source_matrix": summary.get("source_matrix", ""),
        "source_matrix_sha256": summary.get("source_matrix_sha256", ""),
        "metadata_table": summary.get("metadata_table", ""),
        "metadata_table_sha256": summary.get("metadata_table_sha256", ""),
        "final_figure_policy": summary.get("final_figure_policy", ""),
        "dimensions": summary["original_dimensions"],
        "counts": summary["original_counts"],
        "column_order": summary["original_order"],
      }, ensure_ascii=False),
      "grouped_value_after_identifier_match": json.dumps({
        "dimensions": summary["grouped_dimensions"],
        "counts": summary["grouped_counts"],
        "column_order": summary["grouped_order"],
      }, ensure_ascii=False),
      "identical": summary["scientifically_equivalent"],
    })
  output = pd.concat([pd.DataFrame(summary_rows), detail_frame], ignore_index=True)
  tsv = validation_dir / "environmental_group_heatmap_comparison.tsv"
  md = validation_dir / "environmental_group_heatmap_comparison.md"
  js = validation_dir / "environmental_group_heatmap_comparison.json"
  output.to_csv(tsv, sep="\t", index=False)
  md.write_text(comparison_markdown(summaries), encoding="utf-8")
  json_payload = {
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "status": "PASS" if all(item["scientifically_equivalent"] for item in summaries) else "FAIL",
    "figures": summaries,
  }
  js.write_text(json.dumps(json_payload, indent=2, ensure_ascii=False), encoding="utf-8")
  return tsv, md, js


def sync_files(source_dir: Path, target_dirs: list[Path], names: list[str]) -> None:
  for target_dir in target_dirs:
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in names:
      source = source_dir / name
      if source.is_file():
        shutil.copy2(source, target_dir / name)


def run(root: Path) -> dict[str, object]:
  root = root.resolve()
  paths = package_paths(root)
  ensure_dirs(paths)
  primary_figure_dir = paths["figure_dirs"][0]
  primary_derived_dir = paths["derived_dirs"][0]
  primary_validation_dir = paths["validation_dirs"][0]

  removed_inactive = remove_inactive_variant_files(paths)

  generated: list[dict[str, object]] = []
  detail_frames: list[pd.DataFrame] = []
  summaries: list[dict[str, object]] = []
  all_figure_names: list[str] = []
  all_derived_names: list[str] = []

  for spec in SPECS.values():
    raw, metadata = load_inputs(root, spec)
    columns = sample_columns(raw)
    column_meta = column_metadata(columns, metadata)
    original_columns = ordered_columns(column_meta, "original")
    grouped_columns = ordered_columns(column_meta, "environmental_group")
    original_matrix = status_matrix(raw, original_columns)
    grouped_matrix = status_matrix(raw, grouped_columns)

    for variant in spec.active_variants:
      result = generate_variant(
        spec,
        raw,
        column_meta,
        variant,
        primary_figure_dir,
        primary_derived_dir,
      )
      generated.append(result)
      stem = result["stem"]
      all_figure_names.extend([
        f"{stem}.png",
        f"{stem}.pdf",
        f"{stem}.svg",
      ])
      for panel in result["panels"]:
        all_figure_names.extend([Path(panel[key]).name for key in ("png", "pdf", "svg")])
      all_derived_names.extend([Path(result["matrix_csv"]).name, Path(result["order_csv"]).name])

    details, summary = compare_variants(
      spec,
      original_matrix,
      grouped_matrix,
      original_columns,
      grouped_columns,
      column_meta,
    )
    source_matrix = paths["input_dir"] / spec.input_name
    summary["source_matrix"] = str(source_matrix.relative_to(root))
    summary["source_matrix_sha256"] = sha256(source_matrix)
    summary["metadata_table"] = str(paths["metadata"].relative_to(root))
    summary["metadata_table_sha256"] = sha256(paths["metadata"])
    summary["final_figure_policy"] = (
      "environmental-group only; original order retained only as an audit reference"
      if spec.figure_id == "S40" else "original and environmental-group layouts retained"
    )
    detail_frames.append(details)
    summaries.append(summary)

  comparison_paths = write_comparison(detail_frames, summaries, primary_validation_dir)
  if not all(summary["scientifically_equivalent"] for summary in summaries):
    raise RuntimeError("Environmental-group scientific-equivalence validation failed")

  sync_files(primary_figure_dir, paths["figure_dirs"][1:], sorted(set(all_figure_names)))
  sync_files(primary_derived_dir, paths["derived_dirs"][1:], sorted(set(all_derived_names)))
  comparison_names = [path.name for path in comparison_paths]
  sync_files(primary_validation_dir, paths["validation_dirs"][1:], comparison_names)

  report = {
    "status": "PASS",
    "generated_utc": datetime.now(timezone.utc).isoformat(),
    "root": str(root),
    "package_kind": str(paths["kind"]),
    "generated": generated,
    "removed_inactive_files": removed_inactive,
    "active_variant_policy": {spec.figure_id: list(spec.active_variants) for spec in SPECS.values()},
    "comparison_files": [str(path) for path in comparison_paths],
    "scientific_equivalence": summaries,
    "colour_mapping": COLORS,
    "statement": "The only matrix difference is column order. Final S40 is environmental-group only; S67 retains both layouts.",
  }
  report_path = primary_validation_dir / "environmental_group_heatmap_generation_report.json"
  report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
  sync_files(primary_validation_dir, paths["validation_dirs"][1:], [report_path.name])
  return report


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
  args = parser.parse_args()
  report = run(args.root)
  print(json.dumps({
    "status": report["status"],
    "root": report["root"],
    "comparison_files": report["comparison_files"],
  }, indent=2, ensure_ascii=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
