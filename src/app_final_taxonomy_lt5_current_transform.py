from __future__ import annotations

"""Install the canonical taxonomy contract immediately before app dispatch."""

MARKER = "CANGAMETAG_FINAL_TAXONOMY_CURRENT_LT5_V1 = 1"

if MARKER not in source:
  future_anchor = "from __future__ import annotations\n"
  imports = '''from src.taxonomy_final_contract import (
  final_domain_rank_matrices as _final_domain_rank_matrices,
  install_final_taxonomy_contract as _install_final_taxonomy_contract,
)
'''
  if imports not in source:
    source = source.replace(future_anchor, future_anchor + imports, 1)

  dispatch_anchor = "page_handler = page_handlers.get(selected_page)"
  runtime = '''_FINAL_TAXONOMY_CONTRACT = _install_final_taxonomy_contract()
domain_rank_matrices = _final_domain_rank_matrices

'''
  if dispatch_anchor not in source:
    raise RuntimeError("Could not install final taxonomy contract before page dispatch")
  source = source.replace(dispatch_anchor, runtime + dispatch_anchor, 1)
  source += f"\n\n{MARKER}\n"
  compile(source, "app_core_after_final_taxonomy_lt5_current.py", "exec")
