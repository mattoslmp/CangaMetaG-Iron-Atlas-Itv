from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WRAPPER = PROJECT_ROOT / "src" / "app_scientific_module_clarity_transform.py"
REVISION = PROJECT_ROOT / "src" / "app_scientific_module_clarity_v2_transform.py"


def test_transform_files_compile() -> None:
  compile(WRAPPER.read_text(encoding="utf-8"), str(WRAPPER), "exec")
  compile(REVISION.read_text(encoding="utf-8"), str(REVISION), "exec")


def test_revision_contains_required_scientific_clarity() -> None:
  text = REVISION.read_text(encoding="utf-8")
  required = [
    "dados originais e inéditos do trabalho",
    "original, previously unpublished study data",
    "Search lake MAG, classification or annotation",
    "Article MAGs available in BV-BRC",
    "Direct download of an article MAG",
    "number == 247",
    'ne("MAG247")',
    'drop(columns=["Map source"]',
    "Study area and lake samples — Brazil",
    "Supplementary Table 8 — external iron-rich environments",
    "pathway modules associated with biogeochemical cycles",
    "SupplementaryFigure38_metagenome_KEGG_module_completeness_heatmap_P001.png",
  ]
  missing = [value for value in required if value not in text]
  assert not missing, missing


def test_s38_uses_page_one_to_discover_following_pages() -> None:
  text = REVISION.read_text(encoding="utf-8")
  assert 'panel_key == "kegg_lagoon_metagenomes"' in text
  assert "canonical_page_one.exists()" in text
  assert "figure_path = canonical_page_one" in text
