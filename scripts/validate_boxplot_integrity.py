#!/usr/bin/env python3
from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "app.py"


def load_functions(names: set[str]) -> dict[str, object]:
  tree = ast.parse(APP_PATH.read_text(encoding="utf-8"))
  selected = [node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name in names]
  module = ast.Module(body=selected, type_ignores=[])
  namespace = {"pd": pd, "np": np, "re": __import__("re")}
  exec(compile(module, str(APP_PATH), "exec"), namespace)
  return namespace


def manual_stats(values: np.ndarray) -> dict[str, float]:
  values = np.asarray(values, dtype=float)
  q1, median, q3 = np.quantile(values, [0.25, 0.5, 0.75], method="linear")
  iqr = q3 - q1
  low, high = q1 - 1.5 * iqr, q3 + 1.5 * iqr
  inside = values[(values >= low) & (values <= high)]
  return {
    "q1": float(q1), "median": float(median), "q3": float(q3),
    "lower_whisker": float(np.min(inside)), "upper_whisker": float(np.max(inside)),
    "outlier_count": int(np.sum((values < low) | (values > high))),
  }


def main() -> int:
  functions = load_functions({"_boxplot_descriptive_stats"})
  calculate = functions["_boxplot_descriptive_stats"]
  values = np.array([1.0, 2.0, 3.0, 4.0, 10.0])
  frame = pd.DataFrame({"category": ["A"] * len(values), "lake": ["AM"] * len(values), "value": values})
  result = calculate(frame, "value", ["category", "lake"])
  row = result.iloc[0]
  expected = manual_stats(values)
  checks = {
    key: bool(np.isclose(float(row[key]), value)) if key != "outlier_count" else int(row[key]) == int(value)
    for key, value in expected.items()
  }
  # Missing values must remain missing in the descriptive count, not become zero observations.
  missing_frame = pd.DataFrame({"category": ["B", "B", "B"], "lake": ["VI"] * 3, "value": [1.0, np.nan, 3.0]})
  missing_result = calculate(missing_frame, "value", ["category", "lake"]).iloc[0]
  checks["missing_preserved"] = int(missing_result["n_missing"]) == 1 and int(missing_result["n_observations"]) == 2
  payload = {"checks": checks, "passed": all(checks.values()), "expected": expected, "observed": row.to_dict()}
  out = ROOT / "validation" / "boxplot_integrity_validation.json"
  out.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
  print(json.dumps(payload, indent=2, default=str))
  return 0 if payload["passed"] else 1


if __name__ == "__main__":
  raise SystemExit(main())
