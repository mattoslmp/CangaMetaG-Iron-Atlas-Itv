from __future__ import annotations

"""Single source of truth for taxonomy colours used by the app and figures.

Every displayed category receives one deterministic, globally unique colour.
The same taxon therefore keeps the same colour in every article, supplementary
and interactive barplot, while different labels never reuse an identical hex
value. Neutral/aggregate categories are also distinct from one another.
"""

import colorsys
import base64
import gzip
import hashlib
import json
from pathlib import Path
from typing import Iterable

BASE_DIR = Path(__file__).resolve().parents[1]
from src.runtime_paths import APP_DATA_DIR, ensure_runtime_layout
STATIC_PALETTE_PATH = BASE_DIR / "data" / "taxonomy_palette.json"
RUNTIME_PALETTE_PATH = APP_DATA_DIR / "taxonomy_palette.json"
PALETTE_PATH = STATIC_PALETTE_PATH
FULL_PALETTE_BUNDLE_NAME = "taxonomy_palette_full.json.gz.b64"

NEUTRAL_COLORS = {
  "Others": "#C89B3C",
  "Other taxa": "#D4A373",
  "Other taxa (<1%)": "#C6846F",
  "Other genera": "#8D6A9F",
  "Unclassified": "#5B7C99",
  "Unclassified taxa": "#4C6E91",
  "Unassigned": "#7B5E57",
  "Unknown": "#6CA6A1",
}

# The historical Chloroflexi colour is intentionally transferred to the current
# NCBI label Chloroflexota. This changes the displayed name only, never the
# palette identity or any scientific value.
FIXED_COLORS = {
  "Chloroflexota": "#7B2CBF",
  "Candidatus Rokubacteria": "#00A6A6",
  **NEUTRAL_COLORS,
}


def _normalise_taxon(value: object) -> str:
  text = str(value if value is not None else "").strip()
  if not text or text.casefold() in {"nan", "none", "na", "n/a", "null", "undefined"}:
    return "Unclassified"
  return text


def _candidate_colour(taxon: str, attempt: int = 0) -> str:
  """Return a deterministic high-contrast candidate colour for one taxon."""
  digest = hashlib.sha256(f"{taxon}|{attempt}".encode("utf-8")).digest()
  hue = ((int.from_bytes(digest[:4], "big") / 2**32) + attempt * 0.071) % 1.0
  saturation = 0.56 + (digest[4] / 255.0) * 0.38
  lightness = 0.34 + (digest[5] / 255.0) * 0.34
  r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
  return "#%02X%02X%02X" % (round(r * 255), round(g * 255), round(b * 255))


def _next_unique_colour(taxon: str, used: set[str]) -> str:
  attempt = 0
  colour = _candidate_colour(taxon, attempt).upper()
  while colour in used:
    attempt += 1
    colour = _candidate_colour(taxon, attempt).upper()
  return colour


def build_palette(taxa: Iterable[object], existing: dict[str, str] | None = None) -> dict[str, str]:
  """Build an order-independent taxonomy palette with no repeated hex colours."""
  mapping: dict[str, str] = {key: value.upper() for key, value in FIXED_COLORS.items()}
  used: set[str] = set(mapping.values())

  if existing:
    for raw_taxon, raw_colour in sorted(existing.items(), key=lambda item: _normalise_taxon(item[0]).casefold()):
      taxon = _normalise_taxon(raw_taxon)
      # Do not reintroduce a legacy label whose colour has been transferred to
      # the current NCBI name.
      if taxon == "Chloroflexi":
        continue
      if taxon in mapping:
        continue
      colour = str(raw_colour or "").strip().upper()
      if not colour.startswith("#") or len(colour) != 7 or colour in used:
        colour = _next_unique_colour(taxon, used)
      mapping[taxon] = colour
      used.add(colour)

  for taxon in sorted({_normalise_taxon(value) for value in taxa}, key=lambda value: value.casefold()):
    if taxon == "Chloroflexi":
      taxon = "Chloroflexota"
    if taxon in mapping:
      continue
    colour = _next_unique_colour(taxon, used)
    mapping[taxon] = colour
    used.add(colour)

  if mapping["Chloroflexota"] == mapping["Candidatus Rokubacteria"]:
    raise ValueError("Chloroflexota and Candidatus Rokubacteria must have different colours")
  if len(mapping) != len(set(mapping.values())):
    raise ValueError("The canonical taxonomy palette contains repeated colours")
  return dict(sorted(mapping.items(), key=lambda item: item[0].casefold()))


def load_palette(path: Path | None = None) -> dict[str, str]:
  candidates = [path] if path is not None else [STATIC_PALETTE_PATH, RUNTIME_PALETTE_PATH]
  for candidate in candidates:
    if candidate is None:
      continue
    try:
      data: dict[str, str] = {}
      bundle = candidate.with_name(FULL_PALETTE_BUNDLE_NAME)
      if bundle.exists():
        compressed = base64.b64decode(bundle.read_text(encoding="ascii"))
        decoded = json.loads(gzip.decompress(compressed).decode("utf-8"))
        if isinstance(decoded, dict):
          data.update({str(key): str(value) for key, value in decoded.items()})
      core = json.loads(candidate.read_text(encoding="utf-8"))
      if isinstance(core, dict):
        data.update({str(key): str(value) for key, value in core.items()})
      if data:
        return build_palette([], data)
    except Exception:
      continue
  return build_palette([])


def save_palette(mapping: dict[str, str], path: Path | None = None) -> None:
  target = path or RUNTIME_PALETTE_PATH
  ensure_runtime_layout([target.parent])
  canonical = build_palette(mapping.keys(), mapping)
  target.write_text(json.dumps(canonical, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
