from __future__ import annotations

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_figure45_legend_below_final_transform.py"


def _apply(source: str) -> str:
  return runpy.run_path(
    str(TRANSFORM),
    init_globals={"source": source},
  )["source"]


def test_final_figure45_transform_installs_large_data_generator_safely() -> None:
  source = '''from __future__ import annotations

def article_frozen_taxonomy_figure(domain: str):
  return object(), {}

def render_plotly_downloadable(fig, *args, **kwargs):
  return None

page_handler = page_handlers.get(selected_page)
'''
  transformed = _apply(source)
  compile(transformed, "synthetic_figure45_final_generator.py", "exec")
  assert "CANGAMETAG_FIGURE45_FINAL_DATA_GENERATOR_V2" in transformed
  assert "figure45_large_legend_runtime" in transformed
  assert "_materialize_article_figure45_static_final" in transformed
  assert "_apply_figure45_plotly_layout_final" in transformed
  assert "materialize_frozen_article_static =" in transformed
  assert "materialize_frozen_article_static_bilingual =" in transformed
  assert "_APP_FIGURE45_BEFORE_FINAL_DATA_GENERATOR" in transformed
  assert "_APP_RENDER_BEFORE_FIGURE45_FINAL_CAPTION" in transformed
  assert "Genus, symbol and vector keys are enlarged" in transformed
  assert "scripts/figures/generate_article_figure45_final.py" in transformed
  assert "--root ." in transformed


def test_transform_never_fails_when_page_implementation_changes() -> None:
  source = '''from __future__ import annotations

def unrelated_page():
  return "ok"
'''
  transformed = _apply(source)
  compile(transformed, "synthetic_figure45_no_anchor.py", "exec")
  assert "CANGAMETAG_FIGURE45_FINAL_DATA_GENERATOR_V2" in transformed
  assert "Could not place the Figure 4/5 caption" not in transformed
  assert "raise RuntimeError" not in transformed


def test_public_result_wording_replaces_internal_quality_terms() -> None:
  source = '''from __future__ import annotations
labels = [
  txt("Auditoria recente de visitas", "Recent visit audit"),
  txt("Baixar auditoria recente", "Download recent audit"),
  txt("Auditoria das amostras", "Sample audit"),
  "Tabela taxonômica completa para auditoria e download",
  "Complete taxonomic table for audit and download",
  "Data-source audit",
  "Download source audit",
  "No source audit is available yet.",
  "Tabela completa para auditoria",
  "Complete audit table",
]
page_handler = page_handlers.get(selected_page)
'''
  transformed = _apply(source)
  forbidden = [
    "Auditoria recente de visitas",
    "Recent visit audit",
    "Baixar auditoria recente",
    "Download recent audit",
    "Auditoria das amostras",
    "Sample audit",
    "auditoria e download",
    "audit and download",
    "Data-source audit",
    "Download source audit",
    "No source audit is available yet.",
    "Tabela completa para auditoria",
    "Complete audit table",
  ]
  for phrase in forbidden:
    assert phrase not in transformed
  assert "Registros recentes de visitas" in transformed
  assert "Amostras utilizadas" in transformed
  assert "Data-source records" in transformed
  assert "Tabela completa para consulta" in transformed


def test_real_app_core_public_phrases_are_cleaned() -> None:
  transformed = _apply((ROOT / "app_core.py").read_text(encoding="utf-8"))
  forbidden = [
    "Auditoria recente de visitas",
    "Recent visit audit",
    "Baixar auditoria recente",
    "Download recent audit",
    "Auditoria das amostras",
    "Sample audit",
    "Tabela taxonômica completa para auditoria e download",
    "Complete taxonomic table for audit and download",
    "Data-source audit",
    "Download source audit",
    "No source audit is available yet.",
    "Tabela completa para auditoria",
    "Complete audit table",
    "Sem auditoria de cobertura.",
    "Baixar auditoria de cobertura",
  ]
  for phrase in forbidden:
    assert phrase not in transformed


def test_figure45_and_ko_selector_are_loaded_after_other_runtime_wrappers() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  language = app.index("app_full_figure_language_transform.py")
  st8 = app.index("app_final_st8_ko_mtx_revision_transform.py")
  visitor = app.index("app_visitor_map_city_final_transform.py")
  final_legend = app.index("app_figure45_legend_below_final_transform.py")
  ko_selector = app.index("app_ko_heatmap_scale_selector_transform.py")
  assert language < st8 < visitor < final_legend < ko_selector
  assert ko_selector == app.rindex("app_ko_heatmap_scale_selector_transform.py")
