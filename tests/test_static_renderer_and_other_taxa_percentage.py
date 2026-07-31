from __future__ import annotations

from pathlib import Path
import runpy

import numpy as np

from src.article_exact_taxonomy_phylum_generated import exact_article_phylum_svg_bytes
from src.article_exact_taxonomy_phylum_other_percentage import other_taxa_percentages


ROOT = Path(__file__).resolve().parents[1]


def test_other_taxa_percentages_match_exact_figure_sources() -> None:
  bacteria = other_taxa_percentages("Bacteria")
  archaea = other_taxa_percentages("Archaea")

  assert np.isclose(bacteria["overall"], 7.506762301591296)
  assert np.isclose(bacteria["dry"], 7.72986600974163)
  assert np.isclose(bacteria["rainy"], 7.283658593440961)

  assert np.isclose(archaea["overall"], 0.7254332021263236)
  assert np.isclose(archaea["dry"], 0.7027983103916904)
  assert np.isclose(archaea["rainy"], 0.7480680938609566)


def test_final_figure2_and_figure3_svg_labels_include_percentages() -> None:
  bacteria_svg = exact_article_phylum_svg_bytes("Bacteria").decode(
    "utf-8",
    errors="ignore",
  )
  archaea_svg = exact_article_phylum_svg_bytes("Archaea").decode(
    "utf-8",
    errors="ignore",
  )
  assert "Other taxa (7.51%)" in bacteria_svg
  assert "Other taxa (0.73%)" in archaea_svg


def test_recovery_transform_redefines_static_renderer_before_page_dispatch() -> None:
  synthetic = '''
def _display_static_publication_image(path, title, caption="", key_prefix="x"):
  for key in AMAZONIAN_LAKE_COORDINATE_OVERRIDES:
    pass

page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_static_figure_renderer_recovery_transform.py"),
    init_globals={"source": synthetic},
  )["source"]
  compile(transformed, "synthetic_static_renderer_recovery.py", "exec")

  final_definition = transformed.rfind("def _display_static_publication_image(")
  page_dispatch = transformed.index("page_handler = page_handlers.get(selected_page)")
  assert final_definition > transformed.index("AMAZONIAN_LAKE_COORDINATE_OVERRIDES")
  assert final_definition < page_dispatch
  final_body = transformed[final_definition:page_dispatch]
  assert "AMAZONIAN_LAKE_COORDINATE_OVERRIDES" not in final_body
  assert "_render_static_figure_audit" in final_body


def test_app_loads_percentage_and_recovery_layers_last() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  percentage = app.index("app_other_taxa_percentage_label_transform.py")
  recovery = app.index("app_static_figure_renderer_recovery_transform.py")
  runtime_guard = app.index("app_runtime_name_guard_transform.py")
  assert percentage < recovery < runtime_guard
