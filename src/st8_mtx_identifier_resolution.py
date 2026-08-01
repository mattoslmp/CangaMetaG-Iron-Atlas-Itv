from __future__ import annotations

"""Resolve ST8 metatranscriptome matrix columns from publication metadata.

The ST8 package uses more than one valid header convention: short study IDs
(`S2`, `S9`, ...), IMG/taxon identifiers, numeric identifiers imported by Excel
with a trailing `.0`, and composite labels containing one of those identifiers.
This module resolves those representations without changing, imputing, or
reordering scientific values.
"""

from collections.abc import Sequence
import re

import pandas as pd

from src.st8_final_contract import (
  MTX_IDENTIFIER_FIELDS,
  MTX_MATRIX_FIELDS,
  metatranscriptome_metadata,
  normalize_identifier,
)


ADDITIONAL_IDENTIFIER_FIELDS = (
  "Genome Name / Sample Name",
  "Sample Name",
  "sample_name",
  "sample_label",
  "ST8_sample_id",
  "ST8 sample ID",
)

_MISSING = {"", "nan", "none", "na", "n/a", "null", "<na>"}
_INTEGER_LIKE = re.compile(r"^[+-]?\d+(?:\.0+)?$")


def _clean_text(value: object) -> str:
  if value is None or pd.isna(value):
    return ""
  text = str(value).strip()
  return "" if text.casefold() in _MISSING else text


def _identifier_variants(value: object) -> list[str]:
  """Return stable textual variants for one metadata/header identifier."""
  text = _clean_text(value)
  if not text:
    return []

  variants = [text, text.casefold(), normalize_identifier(text)]
  if _INTEGER_LIKE.fullmatch(text):
    integer_text = text.split(".", 1)[0].lstrip("+")
    variants.extend((integer_text, integer_text.casefold(), normalize_identifier(integer_text)))
  return list(dict.fromkeys(variant for variant in variants if variant))


def _candidate_values(row: pd.Series, fields: Sequence[str]) -> list[str]:
  values: list[str] = []
  for field in fields:
    if field not in row.index:
      continue
    value = _clean_text(row.get(field))
    if value and value not in values:
      values.append(value)
  return values


def _unique_unused(matches: Sequence[str], used: set[str]) -> str:
  available = [value for value in dict.fromkeys(matches) if value not in used]
  return available[0] if len(available) == 1 else ""


def _exact_or_normalized_match(
  values: Sequence[str],
  available: Sequence[str],
  used: set[str],
) -> tuple[str, str]:
  for value in values:
    exact = _unique_unused(
      [column for column in available if column == value],
      used,
    )
    if exact:
      return exact, "exact metadata identifier"

  for value in values:
    casefolded = value.casefold()
    match = _unique_unused(
      [column for column in available if column.casefold() == casefolded],
      used,
    )
    if match:
      return match, "case-insensitive metadata identifier"

  for value in values:
    variants = set(_identifier_variants(value))
    match = _unique_unused(
      [
        column
        for column in available
        if variants.intersection(_identifier_variants(column))
      ],
      used,
    )
    if match:
      return match, "normalized metadata identifier"
  return "", ""


def _embedded_identifier_match(
  values: Sequence[str],
  available: Sequence[str],
  used: set[str],
) -> tuple[str, str]:
  matches: list[str] = []
  for column in available:
    if column in used:
      continue
    normalized_column = normalize_identifier(column)
    for value in values:
      text = _clean_text(value)
      if not text:
        continue
      normalized_value = normalize_identifier(text)
      if len(normalized_value) >= 6 and normalized_value in normalized_column:
        matches.append(column)
        break
      if re.fullmatch(r"[A-Za-z]+\d+", text):
        boundary = re.compile(
          rf"(?<![A-Za-z0-9]){re.escape(text)}(?![A-Za-z0-9])",
          re.IGNORECASE,
        )
        if boundary.search(column):
          matches.append(column)
          break
  match = _unique_unused(matches, used)
  return (match, "unique identifier embedded in matrix column") if match else ("", "")


def resolve_metatranscriptome_columns(
  metadata: pd.DataFrame,
  matrix_columns: Sequence[object],
  *,
  expected_count: int | None = 12,
) -> tuple[pd.DataFrame, list[str]]:
  """Resolve every MTX metadata row to one unique ST8 matrix column.

  Resolution follows metadata order and accepts exact matrix fields, exact
  sample/IMG identifiers, normalized numeric identifiers, and unique identifiers
  embedded in composite headers. Short IDs such as `S2` are accepted only by
  exact/normalized equality or token-boundary matching, preventing `S2` from
  being confused with `S21`.
  """
  mtx = metatranscriptome_metadata(metadata)
  available = list(dict.fromkeys(str(column).strip() for column in matrix_columns))
  fields = tuple(dict.fromkeys(
    tuple(MTX_MATRIX_FIELDS) + tuple(MTX_IDENTIFIER_FIELDS) + ADDITIONAL_IDENTIFIER_FIELDS
  ))

  resolved_rows: list[dict[str, object]] = []
  used: set[str] = set()
  for metadata_index, row in mtx.iterrows():
    matrix_values = _candidate_values(row, MTX_MATRIX_FIELDS)
    identifier_values = _candidate_values(row, fields)

    match, method = _exact_or_normalized_match(matrix_values, available, used)
    if not match:
      match, method = _exact_or_normalized_match(identifier_values, available, used)
    if not match:
      match, method = _embedded_identifier_match(identifier_values, available, used)

    resolved = row.to_dict()
    resolved.update({
      "metadata_index": metadata_index,
      "resolved_matrix_column": match,
      "resolution_method": method or "unresolved",
      "resolution_status": "resolved" if match else "unresolved",
    })
    resolved_rows.append(resolved)
    if match:
      used.add(match)

  resolved_metadata = pd.DataFrame(resolved_rows)
  columns = (
    resolved_metadata.loc[
      resolved_metadata.get("resolution_status", pd.Series(dtype=str)).eq("resolved"),
      "resolved_matrix_column",
    ].astype(str).tolist()
    if not resolved_metadata.empty else []
  )
  columns = list(dict.fromkeys(columns))

  if expected_count is not None and len(columns) != int(expected_count):
    diagnostic_fields = [
      field
      for field in (
        "taxon_oid",
        "sample_id_created_this_study",
        "Study Name",
        "resolution_method",
      )
      if field in resolved_metadata.columns
    ]
    unresolved = (
      resolved_metadata.loc[
        resolved_metadata.get("resolution_status", pd.Series(dtype=str)).ne("resolved"),
        diagnostic_fields,
      ].to_dict("records")
      if not resolved_metadata.empty else []
    )
    raise ValueError(
      f"Expected {expected_count} metatranscriptome columns, resolved {len(columns)}. "
      f"Unresolved metadata rows: {unresolved}. "
      f"Available matrix columns include: {available[:25]}"
    )

  return resolved_metadata, columns
