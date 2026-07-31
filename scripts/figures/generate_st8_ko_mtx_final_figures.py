#!/usr/bin/env python3
"""Generate final ST8 KO heatmaps containing all metatranscriptome samples.

Outputs are produced for:
- all 12 ST8 metatranscriptomes;
- the 20 Amazonian lake metagenomes plus all 12 metatranscriptomes;
- raw counts, within-sample relative abundance, and row z-score.

The same 189 KO rows and the same metadata-defined sample order are used in all
three representations. Zero is retained as measured absence. No value is
imputed and no sample is removed because it contains zeros.

Internal validation tables distinguish genuinely missing/non-numeric cells,
measured zeros, and constant rows whose row z-score is necessarily zero. These
files are written to ``data/final_publication_derived`` and are not rendered in
the public application.
"""
from __future__ import annotations

import argparse
import base64
import json
import math
from pathlib import Path
import shutil
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image
from pypdf import PdfWriter

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.st8_final_contract import (
  amazonian_sample_columns,
  resolve_metatranscriptome_columns,
  row_zscore,
  validate_all_ko_contract,
)


MODES = (
  ("raw", "Raw count", "viridis"),
  ("relative", "Relative abundance within sample (%)", "viridis"),
  ("zscore", "Row z-score", "RdBu_r"),
)


def resolve_workbook(root: Path, explicit: Path | None) -> Path:
  candidates = [
    explicit,
    root / "tables" / "Supplementary_Table_8.xlsx",
    root / "05_Source_Data_and_Audit" / "tables" / "Supplementary_Table_8.xlsx",
    root / "05_Source_Data_and_Audit" / "Supplementary_Table_8.xlsx",
  ]
  for candidate in candidates:
    if candidate is not None and candidate.is_file():
      return candidate
  raise FileNotFoundError("Supplementary_Table_8.xlsx was not found")


def output_directories(root: Path, article_root: Path | None) -> tuple[list[Path], Path]:
  figure_dirs = [
    root / "outputs" / "final_publication_figures",
    root / "outputs" / "app_supplementary_figures",
  ]
  if article_root is not None:
    figure_dirs.append(article_root / "03_Supplementary_Figures")
  unique = list(dict.fromkeys(path.resolve() for path in figure_dirs))
  for directory in unique:
    directory.mkdir(parents=True, exist_ok=True)
  derived = root / "data" / "final_publication_derived"
  derived.mkdir(parents=True, exist_ok=True)
  return unique, derived


def relative_abundance(matrix: pd.DataFrame) -> pd.DataFrame:
  totals = matrix.sum(axis=0).replace(0.0, np.nan)
  return matrix.divide(totals, axis=1).multiply(100.0).fillna(0.0)


def write_embedded_svg(png_path: Path, svg_path: Path) -> None:
  with Image.open(png_path) as image:
    width, height = image.size
  payload = base64.b64encode(png_path.read_bytes()).decode("ascii")
  svg_path.write_text(
    f"<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' "
    f"viewBox='0 0 {width} {height}'>"
    f"<image width='{width}' height='{height}' href='data:image/png;base64,{payload}'/>"
    "</svg>",
    encoding="utf-8",
  )


def write_png_pdf(png_path: Path, pdf_path: Path) -> None:
  with Image.open(png_path) as image:
    image.convert("RGB").save(pdf_path, "PDF", resolution=240.0)


def merge_pdfs(paths: list[Path], output: Path) -> None:
  writer = PdfWriter()
  for path in paths:
    writer.append(str(path))
  with output.open("wb") as handle:
    writer.write(handle)
  writer.close()


def sample_label(column: str) -> str:
  text = str(column)
  if text.startswith(("AM.", "TIA.", "TI.", "VI.")):
    return text
  parts = text.rsplit("-", 2)
  if len(parts) == 3 and parts[-1].isdigit():
    return f"{parts[-2]}\n{parts[-1]}"
  return text


def metatranscriptome_value_diagnostics(
  all_ko: pd.DataFrame,
  mtx_columns: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
  """Classify MTX value states without changing or imputing source values."""
  columns = [str(column) for column in mtx_columns if str(column) in all_ko.columns]
  raw = all_ko.loc[:, columns].copy()
  numeric = raw.apply(pd.to_numeric, errors="coerce")
  text = raw.astype("string").apply(lambda series: series.str.strip())
  missing_tokens = {"", "nan", "none", "na", "n/a", "null", "<na>"}
  blank_mask = raw.isna() | text.apply(
    lambda series: series.str.casefold().isin(missing_tokens)
  )
  non_numeric_mask = numeric.isna() & ~blank_mask
  issue_mask = blank_mask | non_numeric_mask

  issue_rows: list[dict[str, object]] = []
  for row_position, row_index in enumerate(all_ko.index):
    for column in columns:
      if not bool(issue_mask.loc[row_index, column]):
        continue
      issue_rows.append({
        "source_row": row_position + 1,
        "KO": str(all_ko.at[row_index, "KO"]) if "KO" in all_ko.columns else "",
        "Metabolism": (
          str(all_ko.at[row_index, "Metabolism"])
          if "Metabolism" in all_ko.columns else ""
        ),
        "matrix_column": column,
        "source_value": raw.at[row_index, column],
        "issue_type": (
          "blank_source_cell"
          if bool(blank_mask.loc[row_index, column])
          else "non_numeric_source_cell"
        ),
      })
  issues = pd.DataFrame(issue_rows, columns=[
    "source_row",
    "KO",
    "Metabolism",
    "matrix_column",
    "source_value",
    "issue_type",
  ])

  filled = numeric.fillna(0.0)
  zero_cells = filled.eq(0.0).sum(axis=1)
  nonzero_cells = filled.ne(0.0).sum(axis=1)
  missing_cells = numeric.isna().sum(axis=1)
  unique_numeric = numeric.nunique(axis=1, dropna=True)
  all_zero = filled.eq(0.0).all(axis=1) & numeric.notna().any(axis=1)
  constant = unique_numeric.le(1) & numeric.notna().any(axis=1)

  status_rows: list[dict[str, object]] = []
  for row_position, row_index in enumerate(all_ko.index):
    missing_count = int(missing_cells.loc[row_index])
    all_zero_row = bool(all_zero.loc[row_index])
    constant_row = bool(constant.loc[row_index])
    if missing_count:
      reason = "missing_or_non_numeric_source_cells"
    elif all_zero_row:
      reason = "measured_zero_in_all_12_mtx_samples"
    elif constant_row:
      reason = "constant_across_mtx_row_zscore_is_zero"
    else:
      reason = "observed_values_present"
    row_values = numeric.loc[row_index]
    status_rows.append({
      "source_row": row_position + 1,
      "KO": str(all_ko.at[row_index, "KO"]) if "KO" in all_ko.columns else "",
      "Metabolism": (
        str(all_ko.at[row_index, "Metabolism"])
        if "Metabolism" in all_ko.columns else ""
      ),
      "selected_mtx_samples": len(columns),
      "missing_or_non_numeric_cells": missing_count,
      "zero_cells": int(zero_cells.loc[row_index]),
      "nonzero_cells": int(nonzero_cells.loc[row_index]),
      "all_zero_across_mtx": all_zero_row,
      "constant_across_mtx": constant_row,
      "raw_sum": float(row_values.fillna(0.0).sum()),
      "raw_min": float(row_values.min()) if row_values.notna().any() else np.nan,
      "raw_max": float(row_values.max()) if row_values.notna().any() else np.nan,
      "display_explanation": reason,
      "values_imputed": False,
    })
  ko_status = pd.DataFrame(status_rows)

  sample_rows: list[dict[str, object]] = []
  for column in columns:
    sample_rows.append({
      "matrix_column": column,
      "KO_rows": int(len(all_ko)),
      "missing_or_non_numeric_cells": int(numeric[column].isna().sum()),
      "zero_cells": int(filled[column].eq(0.0).sum()),
      "nonzero_cells": int(filled[column].ne(0.0).sum()),
      "raw_sum": float(filled[column].sum()),
      "values_imputed": False,
    })
  sample_status = pd.DataFrame(sample_rows)
  return ko_status, issues, sample_status


def render_heatmap_panels(
  matrix: pd.DataFrame,
  *,
  stem: str,
  title: str,
  colorbar_label: str,
  cmap: str,
  figure_dirs: list[Path],
  rows_per_panel: int = 48,
) -> list[dict[str, object]]:
  panel_count = math.ceil(len(matrix) / rows_per_panel)
  primary = figure_dirs[0]
  panel_records: list[dict[str, object]] = []
  page_pdfs: list[Path] = []
  values_all = matrix.to_numpy(float)
  if colorbar_label == "Row z-score":
    vmax = max(abs(float(np.nanmin(values_all))), abs(float(np.nanmax(values_all))), 1e-9)
    vmin = -vmax
  else:
    vmin = 0.0
    vmax = float(np.nanmax(values_all)) if np.isfinite(values_all).any() else 1.0
    vmax = max(vmax, 1e-9)

  for panel_zero in range(panel_count):
    start = panel_zero * rows_per_panel
    end = min((panel_zero + 1) * rows_per_panel, len(matrix))
    panel = matrix.iloc[start:end]
    n_rows, n_cols = panel.shape
    width = max(17.0, min(34.0, 8.0 + 0.58 * n_cols))
    height = max(12.0, min(25.0, 3.5 + 0.34 * n_rows))
    fig, axis = plt.subplots(figsize=(width, height), dpi=240)
    image = axis.imshow(
      panel.to_numpy(float),
      aspect="auto",
      interpolation="nearest",
      cmap=cmap,
      vmin=vmin,
      vmax=vmax,
    )
    axis.set_xticks(np.arange(n_cols))
    axis.set_xticklabels(
      [sample_label(column) for column in panel.columns],
      rotation=45,
      ha="right",
      va="top",
      rotation_mode="anchor",
      fontsize=9,
    )
    axis.set_yticks(np.arange(n_rows))
    axis.set_yticklabels(panel.index.astype(str), fontsize=8.5)
    axis.set_xlabel("ST8 sample / matrix column", fontsize=14, fontweight="bold", labelpad=18)
    axis.set_ylabel("KO and biogeochemical pathway", fontsize=14, fontweight="bold", labelpad=14)
    axis.set_title(
      f"{title} — panel {panel_zero + 1}/{panel_count}",
      fontsize=16,
      fontweight="bold",
      pad=18,
    )
    axis.set_xticks(np.arange(-0.5, n_cols, 1), minor=True)
    axis.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
    axis.grid(which="minor", color="white", linewidth=0.45)
    axis.tick_params(which="minor", bottom=False, left=False)
    axis.tick_params(axis="both", which="major", length=0)
    colorbar = fig.colorbar(image, ax=axis, pad=0.012, fraction=0.025)
    colorbar.set_label(colorbar_label, fontsize=12, fontweight="bold")
    fig.subplots_adjust(left=0.29, right=0.95, bottom=0.28, top=0.92)

    panel_stem = primary / f"{stem}_P{panel_zero + 1:03d}"
    png = panel_stem.with_suffix(".png")
    pdf = panel_stem.with_suffix(".pdf")
    svg = panel_stem.with_suffix(".svg")
    fig.savefig(png, dpi=240, facecolor="white")
    plt.close(fig)
    write_png_pdf(png, pdf)
    write_embedded_svg(png, svg)
    page_pdfs.append(pdf)
    panel_records.append({
      "panel": panel_zero + 1,
      "start_row": start,
      "end_row_exclusive": end,
      "rows": n_rows,
      "columns": n_cols,
      "png": png.name,
      "pdf": pdf.name,
      "svg": svg.name,
    })

  merge_pdfs(page_pdfs, primary / f"{stem}.pdf")
  for extension in ("png", "svg"):
    shutil.copy2(
      primary / f"{stem}_P001.{extension}",
      primary / f"{stem}.{extension}",
    )
  produced = [path for path in primary.glob(f"{stem}*") if path.is_file()]
  for destination in figure_dirs[1:]:
    for path in produced:
      shutil.copy2(path, destination / path.name)
  return panel_records


def build_matrix(all_ko: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
  numeric = all_ko.loc[:, columns].apply(pd.to_numeric, errors="raise")
  labels = (
    all_ko["KO"].astype(str)
    + " — "
    + all_ko["Metabolism"].fillna("Unclassified").astype(str)
  )
  numeric.index = labels
  numeric.index.name = "KO / pathway"
  return numeric


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--root", type=Path, default=ROOT)
  parser.add_argument("--article-root", type=Path, default=None)
  parser.add_argument("--workbook", type=Path, default=None)
  args = parser.parse_args()

  root = args.root.resolve()
  article_root = args.article_root.resolve() if args.article_root else None
  workbook = resolve_workbook(root, args.workbook.resolve() if args.workbook else None)
  all_ko = pd.read_excel(workbook, sheet_name="ST8 — all KO biomarkers")
  metadata = pd.read_excel(workbook, sheet_name="metadata", dtype=str)

  figure_dirs, derived = output_directories(root, article_root)
  lake_columns = amazonian_sample_columns(all_ko.columns)
  resolved_metadata, mtx_columns = resolve_metatranscriptome_columns(
    metadata,
    all_ko.columns,
    expected_count=12,
  )
  ko_status, source_issues, sample_status = metatranscriptome_value_diagnostics(
    all_ko,
    mtx_columns,
  )
  resolved_metadata.to_csv(
    derived / "ST8_metatranscriptome_12_sample_resolution.csv",
    index=False,
  )
  ko_status.to_csv(derived / "ST8_MTX_KO_value_status.csv", index=False)
  source_issues.to_csv(derived / "ST8_MTX_source_cell_issues.csv", index=False)
  sample_status.to_csv(derived / "ST8_MTX_sample_value_summary.csv", index=False)

  validation = validate_all_ko_contract(all_ko, metadata)
  validation.update({
    "mtx_source_issue_cells": int(len(source_issues)),
    "mtx_all_zero_ko_rows": int(ko_status["all_zero_across_mtx"].sum()),
    "mtx_constant_ko_rows": int(ko_status["constant_across_mtx"].sum()),
    "mtx_observed_value_rows": int(
      ko_status["display_explanation"].eq("observed_values_present").sum()
    ),
  })
  if validation["status"] != "PASS" or not source_issues.empty:
    validation["status"] = "FAIL"
    failure_path = derived / "ST8_final_KO_MTX_validation.json"
    failure_path.write_text(
      json.dumps({
        "status": "FAIL",
        "workbook": str(workbook),
        "contract": validation,
        "MTX_columns": mtx_columns,
        "source_issue_file": str(
          (derived / "ST8_MTX_source_cell_issues.csv").relative_to(root)
        ),
      }, ensure_ascii=False, indent=2),
      encoding="utf-8",
    )
    raise RuntimeError(json.dumps(validation, ensure_ascii=False, indent=2))

  scopes = {
    "ST8_MTX_all_12_samples": mtx_columns,
    "ST8_Amazonian_20_plus_MTX_12": lake_columns + mtx_columns,
  }
  reports: list[dict[str, object]] = []

  for scope_name, columns in scopes.items():
    raw = build_matrix(all_ko, columns)
    relative = relative_abundance(raw)
    zscore = row_zscore(raw)
    matrices = {"raw": raw, "relative": relative, "zscore": zscore}
    for mode, colorbar_label, cmap in MODES:
      matrix = matrices[mode]
      source_csv = derived / f"{scope_name}_{mode}_matrix.csv"
      matrix.to_csv(source_csv)
      stem = f"SupplementaryAppFigure_{scope_name}_{mode}_heatmap"
      panels = render_heatmap_panels(
        matrix,
        stem=stem,
        title=f"{scope_name.replace('_', ' ')} — {colorbar_label}",
        colorbar_label=colorbar_label,
        cmap=cmap,
        figure_dirs=figure_dirs,
      )
      reports.append({
        "scope": scope_name,
        "mode": mode,
        "KO_rows": int(matrix.shape[0]),
        "sample_columns": int(matrix.shape[1]),
        "sample_order": "; ".join(matrix.columns.astype(str)),
        "source_csv": str(source_csv.relative_to(root)),
        "figure_stem": stem,
        "panels": len(panels),
        "zero_values_preserved": True,
        "values_imputed": False,
      })

  report = pd.DataFrame(reports)
  report_path = derived / "ST8_final_KO_MTX_figure_report.csv"
  report.to_csv(report_path, index=False)
  validation_path = derived / "ST8_final_KO_MTX_validation.json"
  validation_path.write_text(
    json.dumps({
      "status": "PASS",
      "workbook": str(workbook),
      "contract": validation,
      "MTX_columns": mtx_columns,
      "lake_columns": lake_columns,
      "KO_value_status_file": str(
        (derived / "ST8_MTX_KO_value_status.csv").relative_to(root)
      ),
      "source_cell_issues_file": str(
        (derived / "ST8_MTX_source_cell_issues.csv").relative_to(root)
      ),
      "sample_value_summary_file": str(
        (derived / "ST8_MTX_sample_value_summary.csv").relative_to(root)
      ),
      "figure_records": reports,
    }, ensure_ascii=False, indent=2),
    encoding="utf-8",
  )
  print(report.to_string(index=False))
  print(f"Validation: {validation_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
