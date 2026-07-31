from __future__ import annotations

"""Add exact mean percentages to aggregate taxonomy legend labels."""


MARKER = "CANGAMETAG_OTHER_TAXA_PERCENTAGE_LABEL_V1 = 1"

if MARKER not in source:
  anchor = "page_handler = page_handlers.get(selected_page)"
  layer = r'''
def _other_taxa_percentage_label(name: object, values: object) -> str:
  label = str(name)
  if label not in {"Other taxa", "Other genera"}:
    return label
  numeric = pd.to_numeric(pd.Series(list(values)), errors="coerce").dropna()
  percentage = float(numeric.mean()) if not numeric.empty else 0.0
  return f"{label} ({percentage:.2f}%)"


if "article_season_barplot" in globals():
  _ORIGINAL_ARTICLE_SEASON_BARPLOT_OTHER_PERCENTAGE = article_season_barplot

  def article_season_barplot(*args, **kwargs):
    figure, exact_table, matrix = _ORIGINAL_ARTICLE_SEASON_BARPLOT_OTHER_PERCENTAGE(
      *args,
      **kwargs,
    )
    percentages = {}
    if isinstance(exact_table, pd.DataFrame) and not exact_table.empty:
      for aggregate in ("Other taxa", "Other genera"):
        subset = exact_table.loc[
          exact_table.get("taxon", pd.Series(dtype=str)).astype(str).eq(aggregate)
        ]
        if subset.empty or "relative_abundance_percent" not in subset.columns:
          continue
        values = pd.to_numeric(
          subset["relative_abundance_percent"],
          errors="coerce",
        ).dropna()
        if values.empty:
          continue
        percentages[aggregate] = float(values.mean())
        exact_table.loc[subset.index, "display_taxon"] = (
          f"{aggregate} ({percentages[aggregate]:.2f}%)"
        )

    for trace in list(getattr(figure, "data", []) or []):
      original_name = str(getattr(trace, "name", "") or "")
      if original_name in percentages:
        display_name = f"{original_name} ({percentages[original_name]:.2f}%)"
        trace.name = display_name
        if getattr(trace, "legendgroup", None) == original_name:
          trace.legendgroup = display_name

    meta = dict(figure.layout.meta) if isinstance(figure.layout.meta, dict) else {}
    meta.update({
      "other_taxa_percentage_label": percentages,
      "other_taxa_percentage_rule": (
        "arithmetic mean of relative-abundance percentages across samples "
        "displayed in the active panel"
      ),
    })
    figure.update_layout(meta=meta)
    return figure, exact_table, matrix
'''
  if anchor in source:
    source = source.replace(anchor, layer + "\n\n" + anchor, 1)
  source += f"\n\n{MARKER}\n"
