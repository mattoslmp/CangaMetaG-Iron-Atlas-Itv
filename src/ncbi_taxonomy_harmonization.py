from __future__ import annotations

"""NCBI-taxonomy name harmonisation without changing scientific measurements.

Only taxonomic labels are replaced. OTU/count matrices, sample identifiers and
all numeric values remain untouched. A packaged audit table provides an offline
fallback, while the reproducible refresh script can rebuild the mapping from the
current NCBI taxonomy dump for Phylum, Order, Family and Genus.
"""

from pathlib import Path
from typing import Iterable

import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_UPDATE_PATH = BASE_DIR / "data" / "ncbi_taxonomy_name_updates.csv"
DEFAULT_CURRENT_TAXONOMY_PATH = BASE_DIR / "data" / "resultado.cds.tax.ncbi_current.tab"
TARGET_RANKS = ("Phylum", "Order", "Family", "Genus")
_MISSING = {"", "na", "n/a", "nan", "none", "null", "undefined", "unknown", "unclassified"}


def clean_taxonomy_label(value: object) -> str:
  text = str(value if value is not None else "").strip()
  return "Unclassified" if text.casefold() in _MISSING else text


def load_name_updates(path: Path | str | None = None) -> pd.DataFrame:
  target = Path(path) if path is not None else DEFAULT_UPDATE_PATH
  columns = [
    "rank", "original_name", "current_name", "ncbi_taxid", "status",
    "matched_name_class", "source",
  ]
  if not target.exists():
    return pd.DataFrame(columns=columns)
  frame = pd.read_csv(target, dtype=str, keep_default_na=False)
  for column in columns:
    if column not in frame.columns:
      frame[column] = ""
  frame["rank"] = frame["rank"].astype(str).str.strip().str.title()
  frame["original_name"] = frame["original_name"].map(clean_taxonomy_label)
  frame["current_name"] = frame["current_name"].map(clean_taxonomy_label)
  frame = frame[
    frame["rank"].isin(TARGET_RANKS)
    & frame["original_name"].ne("Unclassified")
    & frame["current_name"].ne("Unclassified")
  ].copy()
  return frame[columns].drop_duplicates(["rank", "original_name"], keep="last").reset_index(drop=True)


def update_mapping_by_rank(updates: pd.DataFrame | None = None) -> dict[str, dict[str, str]]:
  frame = load_name_updates() if updates is None else updates.copy()
  mapping: dict[str, dict[str, str]] = {rank: {} for rank in TARGET_RANKS}
  if frame.empty:
    return mapping
  for _, row in frame.iterrows():
    rank = str(row.get("rank", "")).strip().title()
    old = clean_taxonomy_label(row.get("original_name", ""))
    new = clean_taxonomy_label(row.get("current_name", ""))
    if rank in mapping and old != "Unclassified" and new != "Unclassified":
      mapping[rank][old.casefold()] = new
  return mapping


def harmonize_taxonomy_frame(
  frame: pd.DataFrame,
  updates: pd.DataFrame | None = None,
  ranks: Iterable[str] = TARGET_RANKS,
) -> pd.DataFrame:
  """Return a label-updated copy while preserving shape, index and numeric data."""
  if frame is None:
    return pd.DataFrame()
  out = frame.copy()
  mapping = update_mapping_by_rank(updates)
  for raw_rank in ranks:
    rank = str(raw_rank).strip().title()
    if rank not in out.columns:
      continue
    rank_map = mapping.get(rank, {})
    out[rank] = out[rank].map(clean_taxonomy_label).map(
      lambda value: rank_map.get(str(value).casefold(), str(value))
    )
  return out


def load_current_taxonomy_table(
  original_path: Path | str | None = None,
  current_path: Path | str | None = None,
  updates_path: Path | str | None = None,
) -> pd.DataFrame:
  original = Path(original_path) if original_path is not None else BASE_DIR / "data" / "resultado.cds.tax.tab"
  current = Path(current_path) if current_path is not None else DEFAULT_CURRENT_TAXONOMY_PATH
  if current.exists():
    table = pd.read_csv(current, sep="\t", index_col=0, dtype=str, keep_default_na=False)
    table.columns = [str(column).strip() for column in table.columns]
    return table
  if not original.exists():
    return pd.DataFrame()
  table = pd.read_csv(original, sep="\t", index_col=0, dtype=str, keep_default_na=False)
  table.columns = [str(column).strip() for column in table.columns]
  return harmonize_taxonomy_frame(table, load_name_updates(updates_path))


def transfer_palette_names(
  palette: dict[str, str],
  updates: pd.DataFrame | None = None,
) -> dict[str, str]:
  """Move each legacy colour to its current label without creating duplicates."""
  output = {str(key): str(value).upper() for key, value in (palette or {}).items()}
  frame = load_name_updates() if updates is None else updates.copy()
  if frame.empty:
    return output
  for _, row in frame.iterrows():
    old = clean_taxonomy_label(row.get("original_name", ""))
    new = clean_taxonomy_label(row.get("current_name", ""))
    if old == "Unclassified" or new == "Unclassified" or old == new:
      continue
    if old in output and new not in output:
      output[new] = output[old]
    if old in output:
      del output[old]
  return output


def changed_labels(frame: pd.DataFrame, updates: pd.DataFrame | None = None) -> pd.DataFrame:
  mapping = update_mapping_by_rank(updates)
  rows: list[dict[str, str]] = []
  for rank in TARGET_RANKS:
    if rank not in frame.columns:
      continue
    for value in sorted(frame[rank].map(clean_taxonomy_label).unique(), key=str.casefold):
      current = mapping.get(rank, {}).get(str(value).casefold(), str(value))
      if current != value:
        rows.append({"rank": rank, "original_name": str(value), "current_name": current})
  return pd.DataFrame(rows, columns=["rank", "original_name", "current_name"])
