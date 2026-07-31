from __future__ import annotations

"""Prevent optional runtime extensions from crashing app startup.

Several late transforms wrap functions created by earlier transforms. A public
release transform may remove or replace one of those base functions. The final
source must therefore resolve them through ``globals()`` and degrade safely
instead of raising NameError during module execution.
"""

MARKER = "CANGAMETAG_RUNTIME_NAME_GUARD_V1 = 1"

if MARKER not in source:
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
