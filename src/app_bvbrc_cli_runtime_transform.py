from __future__ import annotations


old = "from src.bvbrc_cli_sync import (\n"
new = "from src.bvbrc_cli_streamlit import (\n"
if old not in source:
  raise RuntimeError("Could not locate the BV-BRC CLI import block")
source = source.replace(old, new, 1)
