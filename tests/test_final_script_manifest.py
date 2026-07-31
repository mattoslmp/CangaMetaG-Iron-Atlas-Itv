from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "scripts" / "FINAL_SCRIPT_MANIFEST.json"


def test_final_script_manifest_points_to_existing_files() -> None:
  data = json.loads(MANIFEST.read_text(encoding="utf-8"))
  scripts = data.get("canonical_scripts", [])
  assert len(scripts) >= 2
  paths = {record["path"] for record in scripts}
  assert "scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py" in paths
  assert "scripts/final_publication_figures/07_generate_st8_ko_biomarker_heatmaps.py" in paths
  for record in scripts:
    assert record["status"] == "canonical_final"
    assert (ROOT / record["path"]).exists()
    assert record.get("command")


def test_legacy_taxonomy_entrypoint_is_only_a_wrapper() -> None:
  path = ROOT / "scripts" / "generate_final_domain_taxonomy_figures.py"
  text = path.read_text(encoding="utf-8")
  assert "02_05_generate_final_taxonomy_figures.py" in text
  assert "def genus_multipanel" not in text
  assert "Chloroflexi" not in text


def test_canonical_scripts_declare_final_versions() -> None:
  taxonomy = (
    ROOT
    / "scripts"
    / "final_publication_figures"
    / "02_05_generate_final_taxonomy_figures.py"
  ).read_text(encoding="utf-8")
  st8 = (
    ROOT
    / "scripts"
    / "final_publication_figures"
    / "07_generate_st8_ko_biomarker_heatmaps.py"
  ).read_text(encoding="utf-8")
  assert "SCRIPT_VERSION" in taxonomy and "final" in taxonomy
  assert "SCRIPT_VERSION" in st8 and "final" in st8
  assert "all-zero row" in st8
  assert "Legends" in taxonomy or "legends" in taxonomy
