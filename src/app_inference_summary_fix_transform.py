from __future__ import annotations

MARKER = "CANGAMETAG_INFERENCE_SUMMARY_FIX_V1 = 1"

if MARKER not in source:
  anchor = "page_handler = page_handlers.get(selected_page)"
  patch = '''from src.article_inference_reporting import inference_summary as inference_summary\n\n'''
  if anchor in source:
    source = source.replace(anchor, patch + anchor, 1)
  source += f"\n\n{MARKER}\n"
