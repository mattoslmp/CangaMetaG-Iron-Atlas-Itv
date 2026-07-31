from __future__ import annotations

"""Label aggregate taxonomy traces with the declared 5% cutoff."""


MARKER = "CANGAMETAG_OTHER_TAXA_PERCENTAGE_LABEL_V2 = 1"

if MARKER not in source:
  anchor = "page_handler = page_handlers.get(selected_page)"
  layer = r'''
_OTHER_TAXA_THRESHOLD_PERCENT = 5.0


def _other_taxa_percentage_label(name: object, values: object = None) -> str:
  label = str(name)
  if label not in {"Other taxa", "Other genera"}:
    return label
  return f"{label} (<{_OTHER_TAXA_THRESHOLD_PERCENT:g}% each)"


if "article_season_barplot" in globals():
  _ORIGINAL_ARTICLE_SEASON_BARPLOT_OTHER_PERCENTAGE = article_season_barplot

  def article_season_barplot(*args, **kwargs):
    figure, exact_table, matrix = _ORIGINAL_ARTICLE_SEASON_BARPLOT_OTHER_PERCENTAGE(
      *args,
      **kwargs,
    )
    aggregate_labels = {}
    if isinstance(exact_table, pd.DataFrame) and not exact_table.empty:
      taxon_series = exact_table.get("taxon", pd.Series(dtype=str)).astype(str)
      for aggregate in ("Other taxa", "Other genera"):
        subset_index = exact_table.index[taxon_series.eq(aggregate)]
        if len(subset_index) == 0:
          continue
        display_name = _other_taxa_percentage_label(aggregate)
        aggregate_labels[aggregate] = display_name
        exact_table.loc[subset_index, "display_taxon"] = display_name

    for trace in list(getattr(figure, "data", []) or []):
      original_name = str(getattr(trace, "name", "") or "")
      if original_name in aggregate_labels:
        display_name = aggregate_labels[original_name]
        trace.name = display_name
        if getattr(trace, "legendgroup", None) == original_name:
          trace.legendgroup = display_name

    meta = dict(figure.layout.meta) if isinstance(figure.layout.meta, dict) else {}
    meta.update({
      "other_taxa_threshold_percent": _OTHER_TAXA_THRESHOLD_PERCENT,
      "other_taxa_display_labels": aggregate_labels,
      "other_taxa_label_rule": (
        "5% denotes the per-taxon cutoff; plotted aggregate values remain "
        "the exact sums from the source table"
      ),
    })
    figure.update_layout(meta=meta)
    return figure, exact_table, matrix
'''
  if anchor in source:
    source = source.replace(anchor, layer + "\n\n" + anchor, 1)
  source += f"\n\n{MARKER}\n"
