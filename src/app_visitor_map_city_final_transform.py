from __future__ import annotations

"""Install the canonical visitor map after every other app transform."""

MARKER = "CANGAMETAG_VISITOR_MAP_CITY_FINAL_V2 = 1"

if MARKER not in source:
  dispatch_anchor = "page_handler = page_handlers.get(selected_page)"
  overrides = '''from src.visitor_public_map import (
  render_public_visitor_footer as _render_public_visitor_footer_canonical,
  visitor_world_map_figure as _visitor_world_map_figure_canonical,
)


def _visitor_world_map_figure(country_frame: pd.DataFrame | None = None):
  return _visitor_world_map_figure_canonical(load_visitor_visits(), txt)


def visitor_counter_public_footer(key: str = "public_footer"):
  return _render_public_visitor_footer_canonical(globals(), key)


'''
  if dispatch_anchor not in source:
    raise RuntimeError("Could not locate app page dispatch for visitor-map override")
  source = source.replace(dispatch_anchor, overrides + dispatch_anchor, 1)
  source += f"\n\n{MARKER}\n"
