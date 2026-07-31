from __future__ import annotations

"""Prevent missing runtime names from crashing app startup.

Several late transforms wrap, move or replace functions created by earlier
layers. The final generated source must therefore restore essential public data
loaders explicitly, initialize variables required by ``page_header`` and resolve
optional extensions through ``globals()``. This transform is loaded last,
immediately before the transformed source is compiled and executed.
"""

MARKER = "CANGAMETAG_RUNTIME_NAME_GUARD_V3 = 1"

if MARKER not in source:
  future_anchor = "from __future__ import annotations\n"
  marker_import = (
    "from src.supplementary_database import "
    "marker_table as _canonical_marker_table_runtime\n"
    "marker_table = _canonical_marker_table_runtime\n"
  )
  if marker_import not in source:
    if future_anchor not in source:
      raise RuntimeError("Could not install marker_table runtime import guard")
    source = source.replace(
      future_anchor,
      future_anchor + marker_import,
      1,
    )

  page_header_signature = "def page_header():\n"
  page_header_initialization = '''def page_header():
  _localized_title_loader = globals().get("_localized_article_text")
  _title_en = globals().get(
    "DEFAULT_ARTICLE_TITLE_EN",
    globals().get("DEFAULT_ARTICLE_TITLE", ""),
  )
  _title_pt = globals().get(
    "DEFAULT_ARTICLE_TITLE_PT",
    globals().get("DEFAULT_ARTICLE_TITLE", ""),
  )
  if callable(_localized_title_loader):
    title = _localized_title_loader("title", _title_en, _title_pt)
  else:
    title = _title_pt if bool(globals().get("IS_PT", False)) else _title_en

  _localized_abstract_loader = globals().get("_localized_article_text")
  _abstract_en = globals().get(
    "DEFAULT_ARTICLE_ABSTRACT_EN",
    globals().get("DEFAULT_ARTICLE_ABSTRACT", ""),
  )
  _abstract_pt = globals().get(
    "DEFAULT_ARTICLE_ABSTRACT_PT",
    globals().get("DEFAULT_ARTICLE_ABSTRACT", ""),
  )
  if callable(_localized_abstract_loader):
    abstract = _localized_abstract_loader(
      "abstract",
      _abstract_en,
      _abstract_pt,
    )
  else:
    abstract = (
      _abstract_pt if bool(globals().get("IS_PT", False)) else _abstract_en
    )

  catalogue = _canonical_marker_table_runtime()
'''
  if page_header_initialization not in source:
    if page_header_signature not in source:
      raise RuntimeError("Could not initialize page_header runtime variables")
    source = source.replace(
      page_header_signature,
      page_header_initialization,
      1,
    )

  source = source.replace(
    "_APP_ORIGINAL_ST8_HEATMAP_FIGURE = heatmap_figure",
    '_APP_ORIGINAL_ST8_HEATMAP_FIGURE = globals().get("heatmap_figure")',
  )
  st8_signature = '''def heatmap_figure(frame, numeric_cols, label_col, title, top_n=30, zscore_rows=False, x_label_map=None):
  title_text = str(title or "")'''
  st8_replacement = '''def heatmap_figure(frame, numeric_cols, label_col, title, top_n=30, zscore_rows=False, x_label_map=None):
  if not callable(_APP_ORIGINAL_ST8_HEATMAP_FIGURE):
    return None
  title_text = str(title or "")'''
  source = source.replace(st8_signature, st8_replacement, 1)

  source = source.replace(
    "_APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE = _visitor_world_map_figure",
    '_APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE = globals().get("_visitor_world_map_figure")',
  )
  visitor_map_signature = '''def _visitor_world_map_figure(country_frame: pd.DataFrame):
  figure = _APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE(country_frame)'''
  visitor_map_replacement = '''def _visitor_world_map_figure(country_frame: pd.DataFrame):
  if not callable(_APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE):
    figure = go.Figure()
    figure.add_annotation(
      text=txt("Mapa temporariamente indisponível", "Map temporarily unavailable"),
      x=0.5, y=0.5, xref="paper", yref="paper", showarrow=False,
    )
    return figure
  figure = _APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE(country_frame)'''
  source = source.replace(visitor_map_signature, visitor_map_replacement, 1)

  source = source.replace(
    "_APP_ORIGINAL_VISITOR_COUNTER_PUBLIC_FOOTER_FINAL = visitor_counter_public_footer",
    '_APP_ORIGINAL_VISITOR_COUNTER_PUBLIC_FOOTER_FINAL = globals().get("visitor_counter_public_footer")',
  )
  footer_signature = '''def visitor_counter_public_footer(key: str = "public_footer"):
  _APP_ORIGINAL_VISITOR_COUNTER_PUBLIC_FOOTER_FINAL(key)'''
  footer_replacement = '''def visitor_counter_public_footer(key: str = "public_footer"):
  if callable(_APP_ORIGINAL_VISITOR_COUNTER_PUBLIC_FOOTER_FINAL):
    _APP_ORIGINAL_VISITOR_COUNTER_PUBLIC_FOOTER_FINAL(key)'''
  source = source.replace(footer_signature, footer_replacement, 1)

  source += f"\n\n{MARKER}\n"
