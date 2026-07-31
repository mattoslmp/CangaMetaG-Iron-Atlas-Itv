from __future__ import annotations

from src.corrected_taxonomy_static_assets import (
  CORRECTED_TAXONOMY_STATIC_FILENAMES,
  corrected_taxonomy_static_bytes,
)


LEGACY_LABELS = {
  "Proteobacteria",
  "Actinobacteria",
  "Acidobacteria",
  "Bacteroidetes",
  "Euryarchaeota",
  "Crenarchaeota",
  "Thaumarchaeota",
}
CURRENT_LABELS = {
  "Pseudomonadota",
  "Actinomycetota",
  "Acidobacteriota",
  "Bacteroidota",
  "Methanobacteriota",
  "Thermoproteota",
  "Nitrososphaerota",
}


def test_all_six_corrected_static_assets_are_packaged() -> None:
  assert len(CORRECTED_TAXONOMY_STATIC_FILENAMES) == 6
  for filename in CORRECTED_TAXONOMY_STATIC_FILENAMES:
    payload = corrected_taxonomy_static_bytes(filename)
    assert payload is not None
    text = payload.decode("utf-8")
    assert "<svg" in text[:5000].lower()
    assert any(label in text for label in CURRENT_LABELS)
    assert not any(label in text for label in LEGACY_LABELS)


def test_corrected_asset_lookup_accepts_original_png_name() -> None:
  payload = corrected_taxonomy_static_bytes(
    "Figure2_taxonomic_phylum_bacteria_horizontal_CDS.png"
  )
  assert payload is not None
  assert b"Pseudomonadota" in payload
