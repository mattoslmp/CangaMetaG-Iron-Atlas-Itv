from __future__ import annotations

from pathlib import Path
import runpy

from src.article_exact_taxonomy_phylum_generated import exact_article_phylum_svg_bytes
from src.article_exact_taxonomy_phylum_other_percentage import (
  OTHER_TAXA_THRESHOLD_PERCENT,
)


ROOT = Path(__file__).resolve().parents[1]


def test_other_taxa_threshold_is_five_percent() -> None:
  assert OTHER_TAXA_THRESHOLD_PERCENT == 5.0


def test_final_figure2_and_figure3_svg_labels_are_bilingual() -> None:
  for domain in ("Bacteria", "Archaea"):
    english = exact_article_phylum_svg_bytes(domain, "en").decode(
      "utf-8", errors="ignore"
    )
    portuguese = exact_article_phylum_svg_bytes(domain, "pt").decode(
      "utf-8", errors="ignore"
    )
    assert "Other taxa (&lt;5% each)" in english or "Other taxa (<5% each)" in english
    assert "Outros táxons (&lt;5% cada)" in portuguese or "Outros táxons (<5% cada)" in portuguese
    assert "Other taxa (7.51%)" not in english + portuguese
    assert "Other taxa (0.73%)" not in english + portuguese


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
  assert 'language = "pt" if IS_PT else "en"' in transformed


def test_app_loads_language_and_recovery_layers_last() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  percentage = app.index("app_other_taxa_percentage_label_transform.py")
  language = app.index("app_full_figure_language_transform.py")
  recovery = app.index("app_static_figure_renderer_recovery_transform.py")
  runtime_guard = app.index("app_runtime_name_guard_transform.py")
  assert percentage < language < recovery < runtime_guard
