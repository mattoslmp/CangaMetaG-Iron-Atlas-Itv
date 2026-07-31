#!/usr/bin/env python3
from __future__ import annotations

"""Generate the final Supplementary Table 8 KO heatmaps and audits.

Scientific contract
-------------------
Input:
  tables/Supplementary_Table_8.xlsx
  sheet: ST8 — all KO biomarkers

The immutable worksheet contains 189 KO rows and 87 numeric sample columns.
An all-zero row in a selected scope is retained in the complete source/audit
files but excluded from the heatmap by default because it encodes no observed
signal. No count is imputed, rescaled or invented.

Examples
--------
python scripts/final_publication_figures/07_generate_st8_ko_biomarker_heatmaps.py
python scripts/final_publication_figures/07_generate_st8_ko_biomarker_heatmaps.py --scope all
python scripts/final_publication_figures/07_generate_st8_ko_biomarker_heatmaps.py --include-undetected
"""

import argparse
import json
from pathlib import Path
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SCRIPT_VERSION = "2026-07-31-final-v1"
SHEET_NAME = "ST8 — all KO biomarkers"
METADATA_COLUMNS = ["KO", "Metabolism", "KO description"]


def project_root() -> Path:
  return Path(__file__).resolve().parents[2]


ROOT = project_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.st8_biomarker_heatmap import (  # noqa: E402
  article_lake_columns,
  assert_no_undetected_heatmap_rows,
  filter_detected_markers,
  numeric_sample_columns,
  validate_st8_all_ko_table,
)


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--base-dir", type=Path, default=ROOT)
  parser.add_argument(
    "--workbook",
    type=Path,
    default=None,
    help="Override tables/Supplementary_Table_8.xlsx",
  )
  parser.add_argument(
    "--scope",
    choices=("amazonian", "external", "all"),
    default="amazonian",
  )
  parser.add_argument("--top-n", type=int, default=0, help="0 keeps every detected marker")
  parser.add_argument("--include-undetected", action="store_true")
  parser.add_argument("--dpi", type=int, default=350)
  return parser.parse_args()


def load_source(workbook: Path) -> pd.DataFrame:
  if not workbook.exists():
    raise FileNotFoundError(f"Supplementary Table 8 not found: {workbook}")
  frame = pd.read_excel(workbook, sheet_name=SHEET_NAME)
  frame.columns = [str(column).strip() for column in frame.columns]
  missing = [column for column in METADATA_COLUMNS if column not in frame.columns]
  if missing:
    raise ValueError(f"Missing ST8 metadata columns: {missing}")
  return frame


def selected_columns(frame: pd.DataFrame, scope: str) -> list[str]:
  numeric = numeric_sample_columns(frame, METADATA_COLUMNS)
  lake = article_lake_columns(numeric)
  external = [column for column in numeric if column not in lake]
  if scope == "amazonian":
    return lake
  if scope == "external":
    return external
  return numeric


def row_zscore(matrix: pd.DataFrame) -> pd.DataFrame:
  means = matrix.mean(axis=1)
  std = matrix.std(axis=1, ddof=0).replace(0, np.nan)
  return matrix.sub(means, axis=0).div(std, axis=0).fillna(0.0)


def marker_labels(frame: pd.DataFrame) -> list[str]:
  ko = frame["KO"].fillna("").astype(str).str.strip()
  pathway = frame["Metabolism"].fillna("Unclassified").astype(str).str.strip()
  return (ko + " | " + pathway).tolist()


def draw_heatmap(
  matrix: pd.DataFrame,
  output_stem: Path,
  title: str,
  zscore: bool,
  dpi: int,
) -> None:
  rows, columns = matrix.shape
  width = max(12.5, min(40.0, 4.5 + 0.48 * columns))
  height = max(8.0, min(56.0, 2.8 + 0.25 * rows))
  fig, ax = plt.subplots(figsize=(width, height))
  values = matrix.to_numpy(float)
  if zscore:
    limit = max(2.5, float(np.nanmax(np.abs(values))) if values.size else 2.5)
    image = ax.imshow(values, aspect="auto", interpolation="nearest", cmap="RdBu_r", vmin=-limit, vmax=limit)
    color_label = "Row z-score"
  else:
    image = ax.imshow(values, aspect="auto", interpolation="nearest", cmap="viridis", vmin=0)
    color_label = "Exact count"
  ax.set_xticks(np.arange(columns))
  ax.set_xticklabels(matrix.columns, rotation=60, ha="right", fontsize=8)
  ax.set_yticks(np.arange(rows))
  ax.set_yticklabels(matrix.index, fontsize=7.5)
  ax.set_xlabel("Supplementary Table 8 sample / record", fontweight="bold")
  ax.set_ylabel("KO | pathway/category", fontweight="bold")
  ax.set_title(title, loc="left", fontsize=13, fontweight="bold", pad=14)
  colorbar = fig.colorbar(image, ax=ax, fraction=0.022, pad=0.018)
  colorbar.set_label(color_label)
  fig.subplots_adjust(left=0.29, right=0.96, top=0.96, bottom=0.18)
  for suffix in ("png", "pdf", "svg"):
    kwargs = {"facecolor": "white", "bbox_inches": "tight"}
    if suffix == "png":
      kwargs["dpi"] = dpi
    fig.savefig(output_stem.with_suffix(f".{suffix}"), **kwargs)
  plt.close(fig)


def main() -> int:
  args = parse_args()
  base_dir = args.base_dir.resolve()
  workbook = (args.workbook or base_dir / "tables" / "Supplementary_Table_8.xlsx").resolve()
  output_dir = base_dir / "outputs" / "app_supplementary_figures"
  derived_dir = base_dir / "data" / "final_publication_derived"
  report_dir = base_dir / "reports"
  for directory in (output_dir, derived_dir, report_dir):
    directory.mkdir(parents=True, exist_ok=True)

  source = load_source(workbook)
  numeric = numeric_sample_columns(source, METADATA_COLUMNS)
  integrity = validate_st8_all_ko_table(source, numeric)
  if str(integrity.iloc[0]["status"]) != "PASS":
    raise RuntimeError("Supplementary Table 8 integrity validation failed")

  columns = selected_columns(source, args.scope)
  display, summary, audit = filter_detected_markers(
    source,
    columns,
    include_undetected=args.include_undetected,
    scope_name=args.scope,
  )
  if not args.include_undetected:
    assert_no_undetected_heatmap_rows(display, columns)

  display = display.copy()
  display["heatmap_label"] = marker_labels(display)
  matrix = display.set_index("heatmap_label")[columns].apply(pd.to_numeric, errors="coerce")
  if matrix.isna().any().any():
    raise RuntimeError("Blank numeric values detected; source values were not imputed")

  totals = matrix.abs().sum(axis=1)
  order = totals.sort_values(ascending=False, kind="stable").index
  matrix = matrix.loc[order]
  if args.top_n > 0:
    matrix = matrix.head(args.top_n)
  z_matrix = row_zscore(matrix)

  scope_token = {"amazonian": "Amazonian_lakes", "external": "external_environments", "all": "all_environments"}[args.scope]
  marker_count = len(matrix)
  raw_stem = output_dir / f"SupplementaryTable8_189_KO_{scope_token}_raw_counts_final"
  z_stem = output_dir / f"SupplementaryTable8_189_KO_{scope_token}_row_zscore_final"
  draw_heatmap(
    matrix,
    raw_stem,
    f"Supplementary Table 8 KO biomarkers — {scope_token.replace('_', ' ')} — exact counts ({marker_count} detected markers)",
    False,
    args.dpi,
  )
  draw_heatmap(
    z_matrix,
    z_stem,
    f"Supplementary Table 8 KO biomarkers — {scope_token.replace('_', ' ')} — row z-score ({marker_count} detected markers)",
    True,
    args.dpi,
  )

  source.to_csv(derived_dir / "ST8_all_189_KO_exact_source.csv", index=False)
  display.to_csv(derived_dir / f"ST8_{scope_token}_heatmap_display_source.csv", index=False)
  matrix.to_csv(derived_dir / f"ST8_{scope_token}_heatmap_exact_count_matrix.csv")
  z_matrix.to_csv(derived_dir / f"ST8_{scope_token}_heatmap_row_zscore_matrix.csv")
  integrity.to_csv(derived_dir / "ST8_all_189_KO_integrity_audit.csv", index=False)
  summary.to_csv(derived_dir / f"ST8_{scope_token}_detection_summary.csv", index=False)
  audit.to_csv(derived_dir / f"ST8_{scope_token}_marker_detection_audit.csv", index=False)

  report = {
    "script": "scripts/final_publication_figures/07_generate_st8_ko_biomarker_heatmaps.py",
    "script_version": SCRIPT_VERSION,
    "workbook": str(workbook.relative_to(base_dir) if workbook.is_relative_to(base_dir) else workbook),
    "sheet": SHEET_NAME,
    "scope": args.scope,
    "include_undetected": bool(args.include_undetected),
    "source_markers": int(len(source)),
    "selected_samples": int(len(columns)),
    "display_markers": int(len(display)),
    "plotted_markers": int(len(matrix)),
    "integrity": integrity.iloc[0].to_dict(),
    "detection": summary.iloc[0].to_dict(),
    "values_imputed": False,
    "outputs": [
      str(raw_stem.with_suffix(".png").relative_to(base_dir)),
      str(raw_stem.with_suffix(".pdf").relative_to(base_dir)),
      str(raw_stem.with_suffix(".svg").relative_to(base_dir)),
      str(z_stem.with_suffix(".png").relative_to(base_dir)),
      str(z_stem.with_suffix(".pdf").relative_to(base_dir)),
      str(z_stem.with_suffix(".svg").relative_to(base_dir)),
    ],
  }
  (report_dir / "FINAL_ST8_KO_HEATMAP_REPORT.json").write_text(
    json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )
  print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
