from __future__ import annotations

"""Apply the shared Order-label normalization before taxonomy rendering."""

MARKER = "CANGAMETAG_ORDER_UNCLASSIFIED_V1 = 1"

if MARKER not in source:
  anchor = 'def runtime_setting(key: str, default: str = "") -> str:'
  patch_code = '''from src.taxonomy_order_unclassified import patch_taxonomy_modules as _patch_order_taxonomy_modules\n\n_ORDER_TAXONOMY_PATCH_STATUS = _patch_order_taxonomy_modules()\n\n'''
  if anchor in source and "_patch_order_taxonomy_modules" not in source:
    source = source.replace(anchor, patch_code + anchor, 1)
  source += f"\n\n{MARKER}\n"
