from __future__ import annotations

"""Current-NCBI labels for every displayed figure/table.

This module changes strings only. Numeric arrays, coordinates, counts, table
geometry and identifiers are preserved exactly.
"""

from pathlib import Path
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .ncbi_taxonomy_harmonization import load_name_updates, update_mapping_by_rank


_REPLACEMENTS: list[tuple[re.Pattern, str]] | None = None


def current_taxonomy_replacements(base_dir: Path) -> list[tuple[re.Pattern, str]]:
  global _REPLACEMENTS
  if _REPLACEMENTS is None:
    updates = load_name_updates(Path(base_dir) / "data" / "ncbi_taxonomy_name_updates.csv")
    mappings = update_mapping_by_rank(updates)
    unique: dict[str, str] = {}
    for rank_mapping in mappings.values():
      for legacy_casefold, current in rank_mapping.items():
        if legacy_casefold and current and legacy_casefold != str(current).casefold():
          unique[legacy_casefold] = str(current)
    _REPLACEMENTS = [
      (
        re.compile(
          rf"(?<![A-Za-z0-9_]){re.escape(legacy)}(?![A-Za-z0-9_])",
          re.IGNORECASE,
        ),
        current,
      )
      for legacy, current in sorted(unique.items(), key=lambda item: (-len(item[0]), item[0]))
    ]
  return _REPLACEMENTS


def harmonize_text(value: object, base_dir: Path) -> object:
  if not isinstance(value, str):
    return value
  output = value
  for pattern, current in current_taxonomy_replacements(base_dir):
    output = pattern.sub(current, output)
  return output


def harmonize_table(frame: pd.DataFrame | None, base_dir: Path) -> pd.DataFrame | None:
  """Return a label-updated copy with exactly the same numeric cells."""
  if frame is None or not isinstance(frame, pd.DataFrame):
    return frame
  output = frame.copy()
  numeric_before = output.select_dtypes(include=[np.number]).copy()
  for column in output.select_dtypes(include=["object", "string", "category"]).columns:
    output[column] = output[column].astype(object).map(lambda value: harmonize_text(value, base_dir))
  output.index = pd.Index(
    [harmonize_text(value, base_dir) for value in output.index],
    name=output.index.name,
  )
  numeric_after = output[numeric_before.columns]
  if (
    list(numeric_before.columns) != list(numeric_after.columns)
    or numeric_before.shape != numeric_after.shape
    or not np.array_equal(
      numeric_before.to_numpy(),
      numeric_after.to_numpy(),
      equal_nan=True,
    )
  ):
    raise RuntimeError("Current-taxonomy display harmonization changed numeric table values")
  return output


def harmonize_figure(fig, base_dir: Path):
  """Update Plotly strings recursively while preserving every numeric array."""
  payload = fig.to_plotly_json()

  def visit(value):
    if isinstance(value, dict):
      return {key: visit(item) for key, item in value.items()}
    if isinstance(value, list):
      return [visit(item) for item in value]
    if isinstance(value, tuple):
      return tuple(visit(item) for item in value)
    if isinstance(value, np.ndarray):
      return value
    return harmonize_text(value, base_dir)

  return go.Figure(visit(payload))
