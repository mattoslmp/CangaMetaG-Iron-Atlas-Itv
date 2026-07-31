from __future__ import annotations

import base64
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import numpy as np

from src import corrected_taxonomy_static_assets as static_assets
from src.article_frozen_taxonomy_panels import article_frozen_taxonomy_figure
from src.article_frozen_taxonomy_static import materialize_frozen_article_static


def test_corrupt_taxonomy_bundle_never_breaks_app(tmp_path: Path, monkeypatch) -> None:
  bad_bundle = tmp_path / "bad.zip"
  bad_bundle.write_text("this is not a zip file", encoding="utf-8")
  empty_assets = tmp_path / "assets"
  empty_assets.mkdir()
  monkeypatch.setattr(static_assets, "BUNDLE_PATH", bad_bundle)
  monkeypatch.setattr(static_assets, "ASSET_DIR", empty_assets)
  assert static_assets.corrected_taxonomy_static_bytes(
    "Figure2_taxonomic_phylum_bacteria_horizontal_CDS.png"
  ) is None


def test_base64_text_zip_bundle_is_decoded(tmp_path: Path, monkeypatch) -> None:
  svg = b'<?xml version="1.0"?><svg xmlns="http://www.w3.org/2000/svg"></svg>'
  buffer = BytesIO()
  with ZipFile(buffer, "w") as archive:
    archive.writestr(
      "main/Figure2_taxonomic_phylum_bacteria_horizontal_CDS.svg",
      svg,
    )
  wrapped_bundle = tmp_path / "wrapped.zip"
  wrapped_bundle.write_bytes(base64.b64encode(buffer.getvalue()))
  empty_assets = tmp_path / "assets"
  empty_assets.mkdir()
  monkeypatch.setattr(static_assets, "BUNDLE_PATH", wrapped_bundle)
  monkeypatch.setattr(static_assets, "ASSET_DIR", empty_assets)
  assert static_assets.corrected_taxonomy_static_bytes(
    "Figure2_taxonomic_phylum_bacteria_horizontal_CDS.png"
  ) == svg


def test_frozen_article_interactive_panels_use_exact_values() -> None:
  expected = {
    "Bacteria": (0.023405931118005, 0.6706464754765108, 0.533),
    "Archaea": (0.027111211776092, 0.6057625487634658, 0.651),
  }
  for domain, (stress, r2, p_value) in expected.items():
    figure, tables = article_frozen_taxonomy_figure(domain)
    statistics = tables["ordination_statistics"].iloc[0]
    assert float(statistics["NMDS_stress"]) == stress
    assert float(statistics["RDA_R2"]) == r2
    assert float(statistics["RDA_p"]) == p_value
    assert len(tables["nmds_scores"]) == 20
    assert len(tables["rda_site_scores"]) == 10
    profile = tables["genus_relative_abundance"].set_index("taxon")
    assert np.allclose(profile.sum(axis=0).to_numpy(float), 100.0, atol=1e-10, rtol=0.0)
    assert figure.layout.meta["recomputed"] is False
    assert figure.layout.meta["authority"] == (
      "ARTICLE_FINAL_ISME_SUBMISSION_Leandrov27-julho FINAL_SUBMISSION_FILES"
    )


def test_static_article_panels_are_generated_without_zip(tmp_path: Path) -> None:
  for domain, stem in [
    ("Bacteria", "Figure4_taxonomic_bacteria_genus_profiles"),
    ("Archaea", "Figure5_taxonomic_archaea_genus_profiles"),
  ]:
    path = materialize_frozen_article_static(domain, tmp_path)
    assert path.name == f"{stem}.svg"
    text = path.read_text(encoding="utf-8")
    assert "<svg" in text[:5000].lower()
    assert "Bray-Curtis NMDS" in text
    assert "RDA biplot" in text
    assert path.stat().st_size > 100000
