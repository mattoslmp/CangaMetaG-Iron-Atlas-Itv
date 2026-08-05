from __future__ import annotations

"""Central taxonomy normalization and strict per-sample <1% aggregation.

The functions in this module are shared by publication and application code.
They preserve the classified relative-abundance denominator, convert missing or
non-classified taxonomy labels to ``Unclassified``, apply rank-aware exact-name
mappings, and collapse only individual values strictly below 1.0% in each
sample into ``Other taxa (<1%)``. Values equal to 1.0% remain explicit.
Every classified taxon reaching 1.0% is displayed, and the missing or
non-classified labels are pooled into an independent ``Unclassified`` category
whose percentage is computed like any other displayed category.
"""

from pathlib import Path
from typing import Iterable
import csv
import numpy as np
import pandas as pd

MISSING_TOKENS = {"", "na", "n/a", "nan", "none", "null", "undefined", "unknown", "unassigned"}
UNCLASSIFIED = "Unclassified"
OTHER_TAXA_LT1 = "Other taxa (<1%)"
OTHER_TAXA_LT5 = OTHER_TAXA_LT1  # backward-compatible alias (label is <1%)
THRESHOLD_PERCENT = 1.0


def normalize_taxonomy_label(value: object) -> str:
  text = str(value if value is not None else "").strip()
  return UNCLASSIFIED if text.casefold() in MISSING_TOKENS else text


def load_rank_mapping(path: Path) -> dict[tuple[str, str], str]:
  mapping: dict[tuple[str, str], str] = {}
  if not path.exists():
    return mapping
  with path.open("r", encoding="utf-8-sig", newline="") as handle:
    for row in csv.DictReader(handle):
      rank = str(row.get("nivel_taxonomico", "")).strip().casefold()
      old = str(row.get("nome_antigo", "")).strip()
      new = str(row.get("nome_atual", "")).strip()
      if rank and old and new:
        mapping[(rank, old)] = new
  return mapping


def normalize_taxonomy_table(taxonomy: pd.DataFrame, mapping_path: Path | None = None) -> pd.DataFrame:
  out = taxonomy.copy()
  mapping = load_rank_mapping(mapping_path) if mapping_path else {}
  for column in out.columns:
    rank = str(column).strip().casefold()
    out[column] = out[column].map(normalize_taxonomy_label)
    if mapping:
      out[column] = out[column].map(lambda value: mapping.get((rank, value), value))
  return out


def aggregate_relative_abundance(
  counts: pd.DataFrame,
  taxonomy: pd.DataFrame,
  domain: str,
  rank: str,
) -> pd.DataFrame:
  shared = counts.index.intersection(taxonomy.index)
  domain_values = taxonomy.loc[shared, "Domain"].map(normalize_taxonomy_label)
  ids = shared[domain_values.astype(str).str.casefold().eq(str(domain).casefold()).to_numpy()]
  labels = taxonomy.loc[ids, rank].map(normalize_taxonomy_label)
  work = counts.loc[ids].apply(pd.to_numeric, errors="coerce").fillna(0.0).copy()
  work["__taxon__"] = labels.to_numpy()
  aggregated = work.groupby("__taxon__", sort=False, dropna=False).sum(numeric_only=True)
  relative = aggregated.div(aggregated.sum(axis=0).replace(0, np.nan), axis=1).fillna(0.0) * 100.0
  return relative.loc[relative.mean(axis=1).sort_values(ascending=False).index]


def aggregate_counts(
  counts: pd.DataFrame,
  taxonomy: pd.DataFrame,
  domain: str,
  rank: str,
) -> pd.DataFrame:
  """Aggregate the ORIGINAL counts per taxon and sample, without normalisation.

  This is the matrix the heatmaps must use. It is deliberately kept separate
  from :func:`aggregate_relative_abundance`: the heatmap transformation
  ``ln(x + 1)`` has to be applied to the observed counts, never to per-sample
  percentages, so the two paths must not be interchangeable by accident.

  Selection, domain filtering, label normalisation and grouping are identical to
  the relative-abundance path, so the two matrices contain exactly the same taxa
  and samples; only the final division by the column totals is omitted.
  """
  shared = counts.index.intersection(taxonomy.index)
  domain_values = taxonomy.loc[shared, "Domain"].map(normalize_taxonomy_label)
  ids = shared[domain_values.astype(str).str.casefold().eq(str(domain).casefold()).to_numpy()]
  labels = taxonomy.loc[ids, rank].map(normalize_taxonomy_label)
  work = counts.loc[ids].apply(pd.to_numeric, errors="coerce").fillna(0.0).copy()
  if (work.to_numpy() < 0).any():
    raise ValueError("Negative counts found in the source OTU table")
  work["__taxon__"] = labels.to_numpy()
  aggregated = work.groupby("__taxon__", sort=False, dropna=False).sum(numeric_only=True)
  return aggregated.loc[aggregated.mean(axis=1).sort_values(ascending=False).index]


def collapse_below_threshold(
  relative: pd.DataFrame,
  threshold: float = THRESHOLD_PERCENT,
  other_label: str = OTHER_TAXA_LT1,
  preserved_labels: Iterable[str] = (UNCLASSIFIED,),
) -> pd.DataFrame:
  """Collapse each taxon value < threshold in each sample, preserving exact 1%."""
  preserved = {normalize_taxonomy_label(label) for label in preserved_labels}
  relative = relative.copy().apply(pd.to_numeric, errors="coerce").fillna(0.0)
  explicit_taxa = [
    taxon for taxon in relative.index
    if normalize_taxonomy_label(taxon) in preserved or bool((relative.loc[taxon] >= float(threshold)).any())
  ]
  out = pd.DataFrame(0.0, index=explicit_taxa + [other_label], columns=relative.columns)
  for sample in relative.columns:
    for raw_taxon in relative.index:
      taxon = normalize_taxonomy_label(raw_taxon)
      value = float(relative.at[raw_taxon, sample])
      if taxon in preserved:
        out.at[taxon, sample] += value
      elif value >= float(threshold):
        out.at[taxon, sample] += value
      else:
        out.at[other_label, sample] += value
  if np.isclose(float(out.loc[other_label].sum()), 0.0, atol=1e-12):
    out = out.drop(index=other_label)
  totals = out.sum(axis=0)
  if not np.allclose(totals.to_numpy(float), 100.0, atol=1e-8, rtol=0.0):
    raise ValueError(f"Taxonomy abundance totals are not 100% after <1% aggregation: {totals.to_dict()}")
  order = out.mean(axis=1).sort_values(ascending=False).index.tolist()
  for trailing in (UNCLASSIFIED, other_label):
    if trailing in order:
      order = [label for label in order if label != trailing] + [trailing]
  return out.loc[order]


def validate_strict_threshold(
  original_relative: pd.DataFrame,
  displayed: pd.DataFrame,
  threshold: float = THRESHOLD_PERCENT,
  other_label: str = OTHER_TAXA_LT1,
) -> dict[str, object]:
  failures: list[dict[str, object]] = []
  for sample in original_relative.columns:
    expected_other = float(original_relative.loc[
      [taxon for taxon in original_relative.index if normalize_taxonomy_label(taxon) != UNCLASSIFIED and float(original_relative.at[taxon, sample]) < threshold],
      sample,
    ].sum())
    observed_other = float(displayed.at[other_label, sample]) if other_label in displayed.index else 0.0
    if not np.isclose(expected_other, observed_other, atol=1e-8, rtol=0.0):
      failures.append({"sample": sample, "expected_other": expected_other, "observed_other": observed_other})
    for taxon in displayed.index:
      if taxon in {UNCLASSIFIED, other_label} or taxon not in original_relative.index:
        continue
      value = float(displayed.at[taxon, sample])
      original = float(original_relative.at[taxon, sample])
      expected = original if original >= threshold else 0.0
      if not np.isclose(value, expected, atol=1e-8, rtol=0.0):
        failures.append({"sample": sample, "taxon": taxon, "expected": expected, "observed": value})
  return {
    "threshold_percent": float(threshold),
    "strict_less_than": True,
    "exactly_threshold_percent_remains_explicit": True,
    "unclassified_preserved": UNCLASSIFIED in displayed.index,
    "totals_100_percent": bool(np.allclose(displayed.sum(axis=0).to_numpy(float), 100.0, atol=1e-8, rtol=0.0)),
    "failures": failures,
    "pass": not failures,
  }


def build_threshold_audit(
  original_relative: pd.DataFrame,
  displayed: pd.DataFrame,
  domain: str,
  taxonomic_level: str,
  threshold: float = THRESHOLD_PERCENT,
  other_label: str = OTHER_TAXA_LT1,
) -> pd.DataFrame:
  """Return one fully traceable PASS/FAIL record per original taxon and sample."""
  records: list[dict[str, object]] = []
  for sample in original_relative.columns:
    sum_before = float(original_relative[sample].sum())
    sum_after = float(displayed[sample].sum())
    expected_other = float(sum(
      float(original_relative.at[taxon, sample])
      for taxon in original_relative.index
      if normalize_taxonomy_label(taxon) != UNCLASSIFIED
      and float(original_relative.at[taxon, sample]) < float(threshold)
    ))
    observed_other = float(displayed.at[other_label, sample]) if other_label in displayed.index else 0.0
    for raw_taxon in original_relative.index:
      taxon = normalize_taxonomy_label(raw_taxon)
      original = float(original_relative.at[raw_taxon, sample])
      is_unclassified = taxon == UNCLASSIFIED
      grouped = not is_unclassified and original < float(threshold)
      final_category = other_label if grouped else taxon
      displayed_percentage = float(displayed.at[final_category, sample]) if final_category in displayed.index else 0.0
      expected_displayed = observed_other if grouped else original
      valid = (
        np.isclose(sum_before, 100.0, atol=1e-8, rtol=0.0)
        and np.isclose(sum_after, 100.0, atol=1e-8, rtol=0.0)
        and np.isclose(expected_other, observed_other, atol=1e-8, rtol=0.0)
        and np.isclose(displayed_percentage, expected_displayed, atol=1e-8, rtol=0.0)
        and (not is_unclassified or final_category == UNCLASSIFIED)
        and (not grouped or original < float(threshold))
        and (grouped or is_unclassified or original >= float(threshold))
      )
      records.append({
        "domain": domain,
        "taxonomic_level": taxonomic_level,
        "sample_or_group": str(sample),
        "original_taxon": str(taxon),
        "original_relative_abundance": original,
        "final_display_category": final_category,
        "grouped_into_other": grouped,
        "is_unclassified": is_unclassified,
        "displayed_percentage": displayed_percentage,
        "sum_before": sum_before,
        "sum_after": sum_after,
        "validation_status": "PASS" if valid else "FAIL",
        "grouping_reason": (
          "Unclassified preserved independently"
          if is_unclassified else
          ("classified taxon strictly below 1% in this sample" if grouped else "classified taxon at or above 1% in this sample")
        ),
      })
  return pd.DataFrame.from_records(records)

