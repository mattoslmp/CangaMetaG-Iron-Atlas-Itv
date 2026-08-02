from __future__ import annotations

"""Apply the canonical genus aggregation rule used by the article figures.

Only genus taxa whose maximum relative abundance is strictly below 1% across
all displayed groups are pooled into ``Other taxa (<1% each)``. Unclassified
taxa remain separate. The transform also disables Top-N truncation for genus
barplots and heatmaps, so taxa at or above 1% are never hidden in the aggregate.
"""


MARKER = "CANGAMETAG_GENUS_LT1_CANONICAL_V1 = 1"

if MARKER not in source:
  anchor = "page_handler = page_handlers.get(selected_page)"
  layer = r'''
_CANGAMETAG_GENUS_OTHER_THRESHOLD_PERCENT = 1.0
_CANGAMETAG_GENUS_OTHER_LABEL = "Other taxa (<1% each)"


def _cangametag_is_genus_level(level_name: object) -> bool:
  text = str(level_name or "")
  return "Genus" in text or "Gênero" in text or "Genero" in text


def _cangametag_aggregate_genus_lt1(frame: object) -> object:
  if not isinstance(frame, pd.DataFrame) or frame.empty:
    return frame
  required = {"group", "taxon"}
  if not required.issubset(frame.columns):
    return frame

  work = frame.copy()
  value_column = "abundance" if "abundance" in work.columns else (
    "count" if "count" in work.columns else None
  )
  if value_column is None:
    return frame
  work[value_column] = pd.to_numeric(work[value_column], errors="coerce").fillna(0.0)
  grouped = work.groupby(["group", "taxon"], as_index=False)[value_column].sum()
  totals = grouped.groupby("group")[value_column].transform("sum").replace(0, np.nan)
  grouped["_relative_percent"] = (
    grouped[value_column].div(totals).mul(100.0).fillna(0.0)
  )
  maximum = grouped.groupby("taxon")["_relative_percent"].max()
  protected = {
    str(name)
    for name in maximum.index
    if str(name).strip().casefold() in {
      "unclassified", "unclassified taxa", "unclassified genera",
      "other taxa", "other genera", "other taxa (<1% each)",
    }
  }
  rare = {
    str(name)
    for name, value in maximum.items()
    if float(value) < _CANGAMETAG_GENUS_OTHER_THRESHOLD_PERCENT
    and str(name) not in protected
  }
  if not rare:
    return work

  rare_mask = work["taxon"].astype(str).isin(rare)
  retained = work.loc[~rare_mask].copy()
  rare_rows = work.loc[rare_mask].copy()
  numeric_columns = [
    column for column in ("count", "abundance")
    if column in rare_rows.columns
  ]
  aggregate = rare_rows.groupby("group", as_index=False)[numeric_columns].sum()
  aggregate["taxon"] = _CANGAMETAG_GENUS_OTHER_LABEL
  for column in work.columns:
    if column in aggregate.columns:
      continue
    if column == "level":
      aggregate[column] = "Genus"
    elif column in {"lake", "season", "environment_feature", "source_sheet"}:
      first_values = rare_rows.groupby("group")[column].first()
      aggregate[column] = aggregate["group"].map(first_values)
    else:
      aggregate[column] = None
  aggregate = aggregate.reindex(columns=work.columns)
  combined = pd.concat([retained, aggregate], ignore_index=True, sort=False)
  return combined


if "taxonomy_profile_table" in globals():
  _CANGAMETAG_ORIGINAL_TAXONOMY_PROFILE_TABLE_LT1 = taxonomy_profile_table

  def taxonomy_profile_table(level_name, *args, **kwargs):
    result = _CANGAMETAG_ORIGINAL_TAXONOMY_PROFILE_TABLE_LT1(
      level_name, *args, **kwargs
    )
    if not _cangametag_is_genus_level(level_name):
      return result
    return _cangametag_aggregate_genus_lt1(result)


if "_taxonomy_heatmap_final" in globals():
  _CANGAMETAG_ORIGINAL_TAXONOMY_HEATMAP_LT1 = _taxonomy_heatmap_final

  def _taxonomy_heatmap_final(
    level_name,
    view_mode,
    top_n,
    zscore_rows=False,
    key_suffix="active",
    text_filter="",
  ):
    if _cangametag_is_genus_level(level_name):
      top_n = None
    return _CANGAMETAG_ORIGINAL_TAXONOMY_HEATMAP_LT1(
      level_name,
      view_mode,
      top_n,
      zscore_rows=zscore_rows,
      key_suffix=key_suffix,
      text_filter=text_filter,
    )


if "_taxonomy_barplot_final" in globals():
  _CANGAMETAG_ORIGINAL_TAXONOMY_BARPLOT_LT1 = _taxonomy_barplot_final

  def _taxonomy_barplot_final(
    level_name,
    view_mode,
    top_n,
    key_suffix,
    text_filter="",
  ):
    if _cangametag_is_genus_level(level_name):
      top_n = None
    frame, plotted = _CANGAMETAG_ORIGINAL_TAXONOMY_BARPLOT_LT1(
      level_name,
      view_mode,
      top_n,
      key_suffix,
      text_filter=text_filter,
    )
    if isinstance(plotted, pd.DataFrame) and "taxon" in plotted.columns:
      plotted = plotted.copy()
      plotted["taxon"] = plotted["taxon"].replace({
        "Other taxa": _CANGAMETAG_GENUS_OTHER_LABEL,
        "Other genera": _CANGAMETAG_GENUS_OTHER_LABEL,
      })
    return frame, plotted
'''
  if anchor not in source:
    raise RuntimeError("Could not locate the public-page dispatch anchor")
  source = source.replace(anchor, layer + "\n\n" + anchor, 1)
  source += f"\n\n{MARKER}\n"
