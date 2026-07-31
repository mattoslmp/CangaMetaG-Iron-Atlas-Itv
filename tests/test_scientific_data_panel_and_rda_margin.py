from __future__ import annotations

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]


def test_scientific_data_panel_transform_compiles_and_adds_five_tabs() -> None:
  synthetic = '''from src.current_taxonomy_display import harmonize_figure as harmonize_current_taxonomy_figure


def render_figure_audit_expander(fig, chart_key, **kwargs):
  pass


def render_plotly_downloadable(fig, **kwargs):
  pass


def _render_static_figure_audit(path, title, key_prefix):
  pass


def _display_static_publication_image(path, title, caption="", key_prefix="figure"):
  pass


def article_frozen_taxonomy_figure(domain):
  return figure, tables

st.info(txt(
  "Estes painéis não recalculam NMDS ou RDA.",
  "These panels do not recompute NMDS or RDA.",
))

page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_scientific_data_panel_v3_transform.py"),
    init_globals={"source": synthetic},
  )["source"]
  compile(transformed, "synthetic_scientific_data_panel.py", "exec")

  assert "Scientific data used in this figure" in transformed
  for label in ["Source", "Processed", "Output", "Plotted values", "Script"]:
    assert label in transformed
  assert "expanded=False" in transformed
  assert '"r": 320' in transformed
  assert "right + 0.30 * span" in transformed
  assert "These panels do not recompute NMDS or RDA" not in transformed


def test_bilingual_static_figure45_generator_reserves_right_margin() -> None:
  generator = (
    ROOT / "src" / "article_frozen_taxonomy_static_bilingual.py"
  ).read_text(encoding="utf-8")
  assert "frozen_article_taxonomy_static_bilingual_v5" in generator
  assert "figsize=(29, 25.5)" in generator
  assert "x_span * 0.34" in generator
  assert "right=0.900" in generator
  assert "pad_inches=0.28" in generator
  assert "Perfis de gêneros — estação seca" in generator
  assert "Vetores da RDA" in generator


def test_canonical_script_records_bilingual_rda_layout() -> None:
  script = (
    ROOT / "scripts" / "final_publication_figures" /
    "02_05_generate_final_taxonomy_figures.py"
  ).read_text(encoding="utf-8")
  assert "final-v9-bilingual-figures" in script
  assert 'choices=["en", "pt", "both"]' in script
  assert '"right_axis_padding_fraction": 0.34' in script
  assert '"right_vector_labels_clipped": False' in script
  assert '"figure_source_values_changed": False' in script


def test_corrected_taxonomy_figures_call_standard_static_data_panel() -> None:
  transform = (
    ROOT / "src" / "app_corrected_taxonomy_static_assets_transform.py"
  ).read_text(encoding="utf-8")
  assert "_render_static_figure_audit(path, title, key_prefix)" in transform
  assert "Static figure built from the frozen tables" not in transform
  assert "These panels do not recompute NMDS or RDA" not in transform
  assert "audit_method=\"Bray-Curtis NMDS; PERMANOVA; PERMDISP; constrained RDA\"" in transform


def test_concise_method_transform_preserves_results_without_long_prose() -> None:
  transform = (
    ROOT / "src" / "app_concise_scientific_method_text_transform.py"
  ).read_text(encoding="utf-8")
  assert "Methods: PERMANOVA and PERMDISP." in transform
  assert "Method: RDA with permutation test." in transform
  assert "_concise_scientific_method_name" in transform


def test_app_loads_language_layer_after_figure_transforms() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  panel = app.index("app_scientific_data_panel_v3_transform.py")
  concise = app.index("app_concise_scientific_method_text_transform.py")
  other_taxa = app.index("app_other_taxa_percentage_label_transform.py")
  language = app.index("app_full_figure_language_transform.py")
  recovery = app.index("app_static_figure_renderer_recovery_transform.py")
  runtime_guard = app.index("app_runtime_name_guard_transform.py")
  assert panel < concise < other_taxa < language < recovery < runtime_guard
