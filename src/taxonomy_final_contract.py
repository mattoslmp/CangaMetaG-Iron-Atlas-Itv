from __future__ import annotations

"""Canonical taxonomy contract for every static and interactive figure.

The contract applies current NCBI names from the packaged mapping and groups a
named taxon into ``Other taxa``/``Other genera`` only when its maximum relative
abundance is strictly below 5% across every displayed sample. Missing taxonomy
literals remain visible as ``Unclassified`` and are never hidden in ``Other``.
Counts and per-sample totals are preserved exactly.
"""

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from . import article_taxonomy as _article_taxonomy
from .ncbi_taxonomy_harmonization import load_name_updates, transfer_palette_names


BASE_DIR = Path(__file__).resolve().parents[1]
OTHER_TAXA_THRESHOLD_PERCENT = 5.0
MISSING_LABELS = {
  "", "na", "n/a", "nan", "none", "null", "undefined", "unknown",
  "unclassified", "unassigned",
}
AGGREGATE_LABELS = {"other taxa", "other genera"}

_ORIGINAL_DOMAIN_RANK_MATRICES = getattr(
  _article_taxonomy,
  "_FINAL_ORIGINAL_DOMAIN_RANK_MATRICES",
  _article_taxonomy.domain_rank_matrices,
)
_article_taxonomy._FINAL_ORIGINAL_DOMAIN_RANK_MATRICES = _ORIGINAL_DOMAIN_RANK_MATRICES


def _root(base_dir: Path | str | None = None) -> Path:
  return Path(base_dir).resolve() if base_dir is not None else BASE_DIR


@lru_cache(maxsize=16)
def _rank_mapping(rank: str, root_text: str) -> dict[str, str]:
  root = Path(root_text)
  updates = load_name_updates(root / "data" / "ncbi_taxonomy_name_updates.csv")
  selected = updates[updates["rank"].astype(str).str.casefold().eq(str(rank).casefold())]
  return {
    str(row.original_name).strip().casefold(): str(row.current_name).strip()
    for row in selected.itertuples(index=False)
    if str(row.original_name).strip() and str(row.current_name).strip()
  }


def current_taxonomy_label(
  value: object,
  rank: str,
  base_dir: Path | str | None = None,
) -> str:
  text = str(value if value is not None else "").strip()
  if text.casefold() in MISSING_LABELS:
    return "Unclassified"
  if text.casefold() in AGGREGATE_LABELS:
    return "Other genera" if str(rank).casefold() == "genus" else "Other taxa"
  mapping = _rank_mapping(str(rank).title(), str(_root(base_dir)))
  return mapping.get(text.casefold(), text)


def _harmonize_matrix_index(
  matrix: pd.DataFrame,
  rank: str,
  base_dir: Path | str | None = None,
) -> pd.DataFrame:
  out = matrix.copy()
  out.index = [current_taxonomy_label(value, rank, base_dir) for value in out.index]
  return out.groupby(level=0, sort=False).sum(numeric_only=True)


def aggregate_below_five_percent(
  counts: pd.DataFrame,
  relative: pd.DataFrame,
  rank: str,
  *,
  threshold: float = OTHER_TAXA_THRESHOLD_PERCENT,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
  """Aggregate every named taxon whose maximum abundance is strictly <5%."""
  count_work = counts.copy()
  relative_work = relative.copy()
  all_taxa = list(dict.fromkeys([*count_work.index.astype(str), *relative_work.index.astype(str)]))
  count_work = count_work.reindex(all_taxa).fillna(0.0)
  relative_work = relative_work.reindex(all_taxa).fillna(0.0)

  low_taxa: list[str] = []
  for taxon in all_taxa:
    normalized = str(taxon).strip().casefold()
    if normalized in MISSING_LABELS or normalized == "unclassified" or normalized in AGGREGATE_LABELS:
      continue
    values = pd.to_numeric(relative_work.loc[taxon], errors="coerce").fillna(0.0)
    if float(values.max()) < float(threshold):
      low_taxa.append(taxon)

  existing_aggregate = [taxon for taxon in all_taxa if str(taxon).strip().casefold() in AGGREGATE_LABELS]
  to_aggregate = list(dict.fromkeys([*low_taxa, *existing_aggregate]))
  aggregate_label = "Other genera" if str(rank).casefold() == "genus" else "Other taxa"

  keep = [taxon for taxon in all_taxa if taxon not in to_aggregate]
  count_final = count_work.loc[keep].copy()
  relative_final = relative_work.loc[keep].copy()
  if to_aggregate:
    count_final.loc[aggregate_label] = count_work.loc[to_aggregate].sum(axis=0)
    relative_final.loc[aggregate_label] = relative_work.loc[to_aggregate].sum(axis=0)

  ordered_named = sorted(
    [taxon for taxon in count_final.index if taxon not in {aggregate_label, "Unclassified"}],
    key=lambda taxon: float(relative_final.loc[taxon].max()),
    reverse=True,
  )
  order = ordered_named
  if "Unclassified" in count_final.index:
    order.append("Unclassified")
  if aggregate_label in count_final.index:
    order.append(aggregate_label)
  count_final = count_final.loc[order]
  relative_final = relative_final.loc[order]

  before_counts = count_work.sum(axis=0).to_numpy(float)
  after_counts = count_final.sum(axis=0).to_numpy(float)
  before_relative = relative_work.sum(axis=0).to_numpy(float)
  after_relative = relative_final.sum(axis=0).to_numpy(float)
  if not np.allclose(before_counts, after_counts, rtol=0.0, atol=1e-8):
    raise RuntimeError("Taxonomy count totals changed while applying the <5% contract")
  if not np.allclose(before_relative, after_relative, rtol=0.0, atol=1e-8):
    raise RuntimeError("Taxonomy relative-abundance totals changed while applying the <5% contract")
  return count_final, relative_final, low_taxa


def final_domain_rank_matrices(
  domain: str,
  rank: str,
  top_n: int | None = None,
  base_dir: Path | str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
  """Return current-name matrices under the single strict <5% display rule."""
  root = _root(base_dir)
  counts, relative = _ORIGINAL_DOMAIN_RANK_MATRICES(
    domain,
    rank,
    top_n=None,
    base_dir=root,
  )
  counts = _harmonize_matrix_index(counts, rank, root)
  relative = _harmonize_matrix_index(relative, rank, root)
  counts, relative, low_taxa = aggregate_below_five_percent(counts, relative, rank)
  counts.attrs.update({
    "taxonomy_contract": "current NCBI names; maximum abundance <5% in all displayed samples",
    "other_taxa_threshold_percent": OTHER_TAXA_THRESHOLD_PERCENT,
    "aggregated_taxa": low_taxa,
    "source_values_changed": False,
  })
  relative.attrs.update(counts.attrs)
  return counts, relative


def final_exact_phylum_table(domain: str) -> pd.DataFrame:
  _, relative = final_domain_rank_matrices(domain, "Phylum", base_dir=BASE_DIR)
  table = relative.copy()
  table.insert(0, "taxon", table.index.astype(str))
  table = table.reset_index(drop=True)
  table.attrs.update({
    "source_path": (
      "data/resultado.cds.otu.tab; data/resultado.cds.tax.ncbi_current.tab; "
      "data/ncbi_taxonomy_name_updates.csv"
    ),
    "other_taxa_threshold_percent": OTHER_TAXA_THRESHOLD_PERCENT,
    "source_values_changed": False,
  })
  return table


def _harmonize_vector_names(frame: pd.DataFrame, rank: str, column: str) -> pd.DataFrame:
  out = frame.copy()
  if column in out.columns:
    out[column] = out[column].map(lambda value: current_taxonomy_label(value, rank, BASE_DIR))
    out = out.drop_duplicates(subset=[column], keep="first").reset_index(drop=True)
  return out


def final_frozen_taxonomy_domain_data(domain: str) -> dict[str, object]:
  canonical = "Archaea" if str(domain).casefold().startswith("arch") else "Bacteria"
  path = BASE_DIR / "data" / f"article_frozen_taxonomy_{canonical.casefold()}.json"
  raw = json.loads(path.read_text(encoding="utf-8"))

  _, relative = final_domain_rank_matrices(canonical, "Genus", base_dir=BASE_DIR)
  profile = relative.copy()
  profile.insert(0, "taxon", profile.index.astype(str))
  profile = profile.reset_index(drop=True)

  rda_taxa = _harmonize_vector_names(
    pd.DataFrame(raw["rda_taxon_vectors"]),
    "Genus",
    "Genus",
  )
  updates = load_name_updates(BASE_DIR / "data" / "ncbi_taxonomy_name_updates.csv")
  palette = transfer_palette_names(dict(raw.get("palette", {})), updates)
  generated_palette = _article_taxonomy._article_palette(
    profile["taxon"].astype(str).tolist(),
    BASE_DIR,
  )
  palette.update(generated_palette)
  palette["Other genera"] = "#9CA3AF"
  palette["Other taxa"] = "#9CA3AF"
  palette["Unclassified"] = palette.get("Unclassified", "#D1D5DB")

  return {
    "domain": canonical,
    "profile": profile,
    "nmds": pd.DataFrame(raw["nmds"]),
    "rda_sites": pd.DataFrame(raw["rda_sites"]),
    "rda_environment_vectors": pd.DataFrame(raw["rda_environment_vectors"]),
    "rda_taxon_vectors": rda_taxa,
    "statistics": pd.DataFrame([raw["statistics"]]),
    "display": dict(raw["display"]),
    "palette": palette,
    "source_files": list(dict.fromkeys([
      *list(raw.get("source_files", [])),
      "data/resultado.cds.otu.tab",
      "data/resultado.cds.tax.ncbi_current.tab",
      "data/ncbi_taxonomy_name_updates.csv",
    ])),
    "taxonomy_contract": {
      "current_names": True,
      "other_taxa_threshold_percent": OTHER_TAXA_THRESHOLD_PERCENT,
      "threshold_operator": "strictly less than",
      "unclassified_preserved": True,
      "ordination_values_recomputed": False,
    },
  }


def legacy_labels_present(labels: list[str], rank: str, base_dir: Path | str | None = None) -> list[str]:
  mapping = _rank_mapping(str(rank).title(), str(_root(base_dir)))
  observed = {str(label).strip().casefold() for label in labels}
  return sorted(
    old for old, new in mapping.items()
    if old != str(new).strip().casefold() and old in observed
  )


def install_final_taxonomy_contract() -> dict[str, Any]:
  """Patch every shared figure entry point to the same current-name contract."""
  _article_taxonomy.domain_rank_matrices = final_domain_rank_matrices

  from . import article_exact_taxonomy_phylum as exact_phylum
  from . import article_exact_taxonomy_phylum_generated as exact_generated
  from . import article_exact_taxonomy_phylum_other_percentage as exact_other
  from . import article_frozen_taxonomy_panels as frozen_panels
  from . import article_frozen_taxonomy_static_bilingual as frozen_static_bilingual

  exact_phylum.load_exact_article_phylum_table = final_exact_phylum_table
  exact_generated.load_exact_article_phylum_table = final_exact_phylum_table
  exact_other.load_exact_article_phylum_table = final_exact_phylum_table
  frozen_panels.frozen_taxonomy_domain_data = final_frozen_taxonomy_domain_data
  frozen_static_bilingual.frozen_taxonomy_domain_data = final_frozen_taxonomy_domain_data
  frozen_static_bilingual.CACHE_VERSION = "frozen_article_taxonomy_current_names_lt5_v1"
  exact_generated.CACHE_VERSION = "exact_article_taxonomy_current_names_lt5_v1"

  try:
    exact_generated.exact_article_phylum_svg_bytes.cache_clear()
  except Exception:
    pass
  try:
    frozen_panels._payload.cache_clear()
  except Exception:
    pass

  try:
    from . import article_frozen_taxonomy_static as frozen_static
    frozen_static.frozen_taxonomy_domain_data = final_frozen_taxonomy_domain_data
  except Exception:
    pass

  return {
    "current_names": True,
    "mapping": "data/ncbi_taxonomy_name_updates.csv",
    "threshold_percent": OTHER_TAXA_THRESHOLD_PERCENT,
    "threshold_operator": "<",
    "unclassified_preserved": True,
    "source_values_changed": False,
  }
