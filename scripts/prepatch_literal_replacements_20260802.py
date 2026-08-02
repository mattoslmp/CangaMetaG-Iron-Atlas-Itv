#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "scripts" / "fix_delivery_workspace_20260802.py"
text = path.read_text(encoding="utf-8")
replacements = {
  "    read_otu_block,\n    text,": "    lambda _match: read_otu_block,\n    text,",
  "    predictor_patch,\n    text,": "    lambda _match: predictor_patch,\n    text,",
  "  identifiers = [str(value) for value in jgi_ids]\n  identifier_set = set(identifiers)": (
    "  raw_identifiers = [str(value) for value in jgi_ids]\n"
    "  aliases = {}\n"
    "  for raw_identifier in raw_identifiers:\n"
    "    match = re.search(r\"(?i)Ga\\d+\", raw_identifier)\n"
    "    aliases[raw_identifier] = match.group(0) if match else raw_identifier\n"
    "  identifiers = list(dict.fromkeys(aliases.values()))\n"
    "  identifier_set = set(identifiers)"
  ),
  "    \"requested_jgi_ids\": identifiers,\n    \"resolved_mapping\": mapping,": (
    "    \"requested_jgi_ids\": raw_identifiers,\n"
    "    \"normalized_jgi_aliases\": aliases,\n"
    "    \"resolved_mapping\": {\n"
    "      raw_identifier: mapping[alias]\n"
    "      for raw_identifier, alias in aliases.items()\n"
    "      if alias in mapping\n"
    "    },"
  ),
  "  return mapping, diagnostic\n\n\ndef read_otu": (
    "  raw_mapping = {\n"
    "    raw_identifier: mapping[alias]\n"
    "    for raw_identifier, alias in aliases.items()\n"
    "    if alias in mapping\n"
    "  }\n"
    "  return raw_mapping, diagnostic\n\n\ndef read_otu"
  ),
}
for old, new in replacements.items():
  if old in text:
    text = text.replace(old, new, 1)
  elif new not in text:
    raise RuntimeError(f"Expected replacement anchor was not found: {old!r}")
path.write_text(text, encoding="utf-8")
print("Literal replacement safeguards and JGI alias normalization applied.")
