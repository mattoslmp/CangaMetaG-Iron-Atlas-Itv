from __future__ import annotations

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]


def synthetic_source() -> str:
  return '''from __future__ import annotations
import plotly.graph_objects as go


def _display_static_publication_image(path: Path, title: str, caption: str = "", key_prefix: str = "static_publication_image") -> None:
  pass


def taxonomy_tab():
  st.markdown("### " + txt(
    "Barplots interativos correspondentes às Figuras 2 e 3",
    "Interactive barplots corresponding to Figures 2 and 3",
  ))
  old_redraw = True
  st.markdown("### " + txt(
    "Explorador taxonômico interativo com nomenclatura NCBI atual",
    "Interactive taxonomy explorer with current NCBI nomenclature",
  ))


def site_access_gate():
  pass
'''


def test_exact_figure2_3_transform_replaces_old_redraw_block() -> None:
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_exact_figure2_3_alignment_transform.py"),
    init_globals={"source": synthetic_source()},
  )["source"]
  assert "def _render_exact_article_phylum_figures" in transformed
  assert "_render_exact_article_phylum_figures()" in transformed
  assert "old_redraw = True" not in transformed
  assert "_APP_ORIGINAL_VALIDATE_VISIBLE_TEXT" in transformed
  assert "materialize_exact_article_phylum_static" in transformed
  compile(transformed, "synthetic_app_core.py", "exec")


def test_generated_source_transform_routes_to_corrected_table_generator() -> None:
  initial = runpy.run_path(
    str(ROOT / "src" / "app_exact_figure2_3_alignment_transform.py"),
    init_globals={"source": synthetic_source()},
  )["source"]
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_exact_figure2_3_generated_source_transform.py"),
    init_globals={"source": initial},
  )["source"]
  assert "from src.article_exact_taxonomy_phylum_generated import (" in transformed
  assert "from src.article_exact_taxonomy_phylum import (" not in transformed
  compile(transformed, "synthetic_app_core_generated.py", "exec")


def test_taxonomy_na_transform_marks_generic_taxonomy_figures_only() -> None:
  base = synthetic_source().replace(
    "def site_access_gate():",
    '''def article_season_barplot(*args, **kwargs):
  return None, None, None


def site_access_gate():''',
  )
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_taxonomy_na_literal_transform.py"),
    init_globals={"source": base},
  )["source"]
  assert "_APP_ORIGINAL_ARTICLE_SEASON_BARPLOT" in transformed
  assert '"allow_taxonomy_missing_literals": True' in transformed
  compile(transformed, "synthetic_app_core_taxonomy_na.py", "exec")
