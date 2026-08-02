#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "scripts" / "fix_delivery_workspace_20260802.py"
text = path.read_text(encoding="utf-8")
replacements = {
  "    read_otu_block,\n    text,": "    lambda _match: read_otu_block,\n    text,",
  "    predictor_patch,\n    text,": "    lambda _match: predictor_patch,\n    text,",
}
for old, new in replacements.items():
  if old in text:
    text = text.replace(old, new, 1)
  elif new not in text:
    raise RuntimeError(f"Expected replacement anchor was not found: {old!r}")
path.write_text(text, encoding="utf-8")
print("Literal replacement safeguards applied.")
