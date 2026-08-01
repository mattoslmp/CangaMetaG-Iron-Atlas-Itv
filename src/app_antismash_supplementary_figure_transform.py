from __future__ import annotations

"""Replace the antiSMASH evidence renderer with its supplementary-figure view."""

MARKER = "CANGAMETAG_ANTISMASH_SUPPLEMENTARY_FIGURE68_V1 = 1"

if MARKER not in source:
  future_anchor = "from __future__ import annotations\n"
  imports = '''from src.antismash_supplementary_figure import (
  render_bgc_metabolism_panel_with_supplementary as _render_bgc_panel_final,
)
'''
  if imports not in source:
    source = source.replace(future_anchor, future_anchor + imports, 1)
  dispatch_anchor = "page_handler = page_handlers.get(selected_page)"
  override = '''render_bgc_metabolism_panel = _render_bgc_panel_final

'''
  if dispatch_anchor not in source:
    raise RuntimeError("Could not install antiSMASH Supplementary Figure 68 renderer")
  source = source.replace(dispatch_anchor, override + dispatch_anchor, 1)
  source += f"\n\n{MARKER}\n"
  compile(source, "app_core_after_antismash_supplementary_figure68.py", "exec")
