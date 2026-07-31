from __future__ import annotations

"""Remove complex pandas attrs before marker-table reshape operations."""

MARKER = "CANGAMETAG_DATAFRAME_ATTRS_MELT_GUARD_V1 = 1"

if MARKER not in source:
  anchor = "page_handler = page_handlers.get(selected_page)"
  wrapper = r'''
# pandas propagates DataFrame.attrs to Series selected by melt(). If attrs
# contain DataFrames, pandas concat compares them and raises an ambiguous
# truth-value ValueError. Scientific columns and values are preserved; only
# non-tabular runtime metadata are removed before reshaping.
if "_long_marker_counts_for_boxplot" in globals():
  _APP_ORIGINAL_LONG_MARKER_COUNTS_FOR_BOXPLOT = _long_marker_counts_for_boxplot

  def _long_marker_counts_for_boxplot(*args, **kwargs):
    clean_args = []
    for value in args:
      if isinstance(value, pd.DataFrame):
        value = value.copy(deep=False)
        value.attrs.clear()
      clean_args.append(value)
    clean_kwargs = {}
    for key, value in kwargs.items():
      if isinstance(value, pd.DataFrame):
        value = value.copy(deep=False)
        value.attrs.clear()
      clean_kwargs[key] = value
    result = _APP_ORIGINAL_LONG_MARKER_COUNTS_FOR_BOXPLOT(
      *clean_args,
      **clean_kwargs,
    )
    if isinstance(result, pd.DataFrame):
      result.attrs.clear()
    return result
'''
  if anchor in source and "_APP_ORIGINAL_LONG_MARKER_COUNTS_FOR_BOXPLOT" not in source:
    source = source.replace(anchor, wrapper + "\n\n" + anchor, 1)
  source += f"\n\n{MARKER}\n"
