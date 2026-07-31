from __future__ import annotations

MARKER = "CANGAMETAG_OFFICIAL_ORDINATION_STATISTICS_V1 = 1"

if MARKER not in source:
  anchor = "page_handler = page_handlers.get(selected_page)"
  patch = '''from src.article_official_ordination_statistics import official_ordination_inference as frozen_ordination_inference\n\n'''
  if anchor in source:
    source = source.replace(anchor, patch + anchor, 1)
  source += f"\n\n{MARKER}\n"
