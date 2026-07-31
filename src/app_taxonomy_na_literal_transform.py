from __future__ import annotations

"""Mark every app taxonomy barplot as allowing literal NA/N/A categories."""

MARKER = "CANGAMETAG_TAXONOMY_NA_LITERAL_V1 = 1"

if MARKER not in source:
  wrapper_code = r'''
_APP_ORIGINAL_ARTICLE_SEASON_BARPLOT = article_season_barplot


def article_season_barplot(*args, **kwargs):
  figure, exact_table, matrix = _APP_ORIGINAL_ARTICLE_SEASON_BARPLOT(
    *args, **kwargs
  )
  current_meta = getattr(figure.layout, "meta", None)
  meta = dict(current_meta) if isinstance(current_meta, dict) else {}
  meta.update({
    "allow_taxonomy_missing_literals": True,
    "taxonomy_values_recomputed": False,
  })
  figure.update_layout(meta=meta)
  return figure, exact_table, matrix
'''
  site_anchor = "def site_access_gate"
  if site_anchor in source and "_APP_ORIGINAL_ARTICLE_SEASON_BARPLOT" not in source:
    source = source.replace(site_anchor, wrapper_code + "\n\n" + site_anchor, 1)
  source += f"\n\n{MARKER}\n"
