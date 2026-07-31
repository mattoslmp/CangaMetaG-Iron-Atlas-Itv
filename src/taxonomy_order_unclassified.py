from __future__ import annotations

"""Normalize missing taxonomic Order labels without changing any counts.

The source taxonomy tables sometimes contain the literal strings ``NA`` or
``N/A``. Pandas does not treat those strings as missing when files are loaded
with ``keep_default_na=False``. This module converts only missing-like values in
the Order column to ``Unclassified`` before taxonomic aggregation.
"""

from pathlib import Path
from typing import Any

import pandas as pd


ORDER_MISSING_LABELS = frozenset({
  "",
  "na",
  "n/a",
  "nan",
  "none",
  "null",
  "<na>",
})


def normalize_order_label(value: object) -> str:
  """Return ``Unclassified`` for a missing-like Order label."""
  text = "" if value is None else str(value).strip()
  return "Unclassified" if text.casefold() in ORDER_MISSING_LABELS else text


def normalize_order_taxonomy_frame(frame: pd.DataFrame) -> pd.DataFrame:
  """Normalize the Order column while preserving shape, index and other ranks."""
  if frame is None:
    return pd.DataFrame()
  out = frame.copy()
  order_column = next(
    (column for column in out.columns if str(column).strip().casefold() == "order"),
    None,
  )
  if order_column is None:
    return out
  out[order_column] = out[order_column].map(normalize_order_label)
  return out


def normalize_current_taxonomy_file(root: Path | str) -> dict[str, Any]:
  """Normalize the packaged current-taxonomy table used by figure scripts."""
  base = Path(root).resolve()
  path = base / "data" / "resultado.cds.tax.ncbi_current.tab"
  if not path.exists():
    return {
      "status": "SKIPPED",
      "path": str(path),
      "reason": "current taxonomy table not found",
      "changed_order_cells": 0,
      "counts_changed": False,
    }

  frame = pd.read_csv(
    path,
    sep="\t",
    index_col=0,
    dtype=str,
    keep_default_na=False,
  )
  frame.columns = [str(column).strip() for column in frame.columns]
  order_column = next(
    (column for column in frame.columns if str(column).casefold() == "order"),
    None,
  )
  if order_column is None:
    return {
      "status": "SKIPPED",
      "path": str(path.relative_to(base)),
      "reason": "Order column not found",
      "changed_order_cells": 0,
      "counts_changed": False,
    }

  before = frame[order_column].astype(str).str.strip()
  normalized = normalize_order_taxonomy_frame(frame)
  after = normalized[order_column].astype(str)
  changed = int(before.ne(after).sum())
  normalized.to_csv(path, sep="\t")
  return {
    "status": "PASS",
    "path": str(path.relative_to(base)),
    "changed_order_cells": changed,
    "replacement": "Unclassified",
    "counts_changed": False,
    "table_shape_unchanged": tuple(normalized.shape) == tuple(frame.shape),
    "index_unchanged": bool(normalized.index.equals(frame.index)),
  }


def patch_taxonomy_modules() -> dict[str, bool]:
  """Patch shared app taxonomy loaders before any Order graph is generated."""
  patched = {
    "article_taxonomy": False,
    "supplementary_database": False,
  }

  try:
    from src import article_taxonomy

    if not getattr(article_taxonomy, "_ORDER_UNCLASSIFIED_PATCHED", False):
      original_load_article_inputs = article_taxonomy.load_article_inputs

      def load_article_inputs(*args, **kwargs):
        otu, taxonomy = original_load_article_inputs(*args, **kwargs)
        return otu, normalize_order_taxonomy_frame(taxonomy)

      article_taxonomy.load_article_inputs = load_article_inputs
      article_taxonomy._ORDER_UNCLASSIFIED_PATCHED = True
    patched["article_taxonomy"] = True
  except Exception:
    patched["article_taxonomy"] = False

  try:
    from src import supplementary_database

    if not getattr(supplementary_database, "_ORDER_UNCLASSIFIED_PATCHED", False):
      original_taxonomy_raw = supplementary_database._taxonomy_raw

      def taxonomy_raw(*args, **kwargs):
        otu, taxonomy = original_taxonomy_raw(*args, **kwargs)
        return otu, normalize_order_taxonomy_frame(taxonomy)

      supplementary_database._taxonomy_raw = taxonomy_raw
      supplementary_database._ORDER_UNCLASSIFIED_PATCHED = True
    patched["supplementary_database"] = True
  except Exception:
    patched["supplementary_database"] = False

  return patched
