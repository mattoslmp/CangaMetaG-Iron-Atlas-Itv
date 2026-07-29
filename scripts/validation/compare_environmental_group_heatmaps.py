#!/usr/bin/env python3
"""Compare S40/S67 reference and environmental-group matrices without rendering.

The command reconstructs both column orders from each immutable source matrix and
the environmental metadata, performs a full identifier-based cell audit, and
rewrites TSV/MD/JSON reports. Original-order S40 is audit-only; only grouped S40 is
an active final figure. No PNG, PDF or SVG file is written or modified.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "figures"
sys.path.insert(0, str(SCRIPT_DIR))
from generate_environmental_group_heatmaps import (  # noqa: E402
  SPECS,
  column_metadata,
  compare_variants,
  ensure_dirs,
  load_inputs,
  ordered_columns,
  package_paths,
  sample_columns,
  status_matrix,
  write_comparison,
)


def sha256(path: Path) -> str:
  digest = hashlib.sha256()
  with path.open("rb") as handle:
    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
      digest.update(chunk)
  return digest.hexdigest()


def run_comparison(root: Path) -> dict[str, object]:
  root = root.resolve()
  paths = package_paths(root)
  ensure_dirs(paths)
  validation_dir = paths["validation_dirs"][0]
  details = []
  summaries = []
  for spec in SPECS.values():
    raw, metadata = load_inputs(root, spec)
    columns = sample_columns(raw)
    column_meta = column_metadata(columns, metadata)
    original_columns = ordered_columns(column_meta, "original")
    grouped_columns = ordered_columns(column_meta, "environmental_group")
    original = status_matrix(raw, original_columns)
    grouped = status_matrix(raw, grouped_columns)
    detail, summary = compare_variants(
      spec, original, grouped, original_columns, grouped_columns, column_meta
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
    details.append(detail)
    summaries.append(summary)
  comparison_paths = write_comparison(details, summaries, validation_dir)
  for secondary in paths["validation_dirs"][1:]:
    secondary.mkdir(parents=True, exist_ok=True)
    for source in comparison_paths:
      (secondary / source.name).write_bytes(source.read_bytes())
  status = "PASS" if all(item["scientifically_equivalent"] for item in summaries) else "FAIL"
  return {
    "status": status,
    "figures": [item["figure_id"] for item in summaries],
    "comparison_files": [str(path) for path in comparison_paths],
    "statement": "The same source table is used for each pair; the only matrix difference is column order. Final S40 is environmental-group only.",
  }


def main() -> int:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[2])
  args = parser.parse_args()
  report = run_comparison(args.root)
  print(json.dumps(report, indent=2, ensure_ascii=False))
  return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
  raise SystemExit(main())
