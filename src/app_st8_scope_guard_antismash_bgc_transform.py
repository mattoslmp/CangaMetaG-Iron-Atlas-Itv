from __future__ import annotations

"""Final scope guard for ST8 panels and antiSMASH BGC evidence display."""

MARKER = "CANGAMETAG_ST8_SCOPE_GUARD_ANTISMASH_BGC_V1 = 1"

if MARKER not in source:
  candidate = source
  future_anchor = "from __future__ import annotations\n"
  imports = '''from src.antismash_metabolism_runtime import render_bgc_metabolism_panel
from src.st8_final_contract import resolve_metatranscriptome_columns as _scope_guard_resolve_mtx
'''
  if imports not in candidate:
    candidate = candidate.replace(future_anchor, future_anchor + imports, 1)

  dispatch_anchor = "page_handler = page_handlers.get(selected_page)"
  runtime_guard = '''_APP_COMPLETE_MTX_PANEL_BEFORE_SCOPE_GUARD = render_complete_metatranscriptome_panel


def render_complete_metatranscriptome_panel(namespace, *, metadata, numeric_columns, data, render_pair, base_key):
  # The ST8 scope renderer is reused by complete, sediment-only and thematic
  # subsets. Only the complete matrix contains the 12 MTX columns; a subset with
  # no MTX columns must not invoke the strict 12-column contract.
  if data is None or getattr(data, "empty", True) or metadata is None or getattr(metadata, "empty", True):
    return
  _, available_mtx_columns = _scope_guard_resolve_mtx(
    metadata,
    [str(column) for column in data.columns],
    expected_count=None,
  )
  if not available_mtx_columns:
    return
  if len(available_mtx_columns) != 12:
    # A partially projected ST8 table is not the complete MTX panel. Do not
    # report a false application error inside unrelated sediment/theme scopes.
    return
  return _APP_COMPLETE_MTX_PANEL_BEFORE_SCOPE_GUARD(
    namespace,
    metadata=metadata,
    numeric_columns=numeric_columns,
    data=data,
    render_pair=render_pair,
    base_key=base_key,
  )


'''
  if dispatch_anchor not in candidate:
    raise RuntimeError("Could not install the final ST8 scope guard")
  candidate = candidate.replace(dispatch_anchor, runtime_guard + dispatch_anchor, 1)

  antismash_anchor = '''  inventory = antismash_inventory()
'''
  antismash_call = '''  inventory = antismash_inventory()
  render_bgc_metabolism_panel(globals())
'''
  if antismash_anchor not in candidate:
    raise RuntimeError("Could not locate the antiSMASH results section")
  candidate = candidate.replace(antismash_anchor, antismash_call, 1)

  candidate += f"\n\n{MARKER}\n"
  compile(candidate, "app_core_after_st8_scope_guard_antismash_bgc.py", "exec")
  source = candidate
