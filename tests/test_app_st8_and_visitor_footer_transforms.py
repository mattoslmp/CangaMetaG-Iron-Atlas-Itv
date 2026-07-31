from __future__ import annotations

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]


def st8_source() -> str:
  return '''from __future__ import annotations
import numpy as np


def heatmap_figure(frame, numeric_cols, label_col, title, top_n=30, zscore_rows=False, x_label_map=None):
  return None


def markers_tab():
  counts = object()
  numeric_cols = []
  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  all_metab = sorted(counts["Metabolism"].dropna().astype(str).unique())
  complete_ko_panel = st.checkbox(
    txt(f"Mostrar o painel completo com todos os {len(counts)} KOs", f"Show the complete panel with all {len(counts)} KOs"),
    value=True, key="st8_lake_bio_complete_189",
  )
  selected_metab = []
  counts_f = counts.copy() if complete_ko_panel else counts[counts["Metabolism"].astype(str).isin(selected_metab)].copy()
  show_ko_pathway_detail = True
  ko_id = counts_f["KO"].fillna("").astype(str).str.strip()
  ko_pathway = counts_f["Metabolism"].fillna("Unclassified").astype(str).str.strip()
  counts_f["KO_pathway_label"] = np.where(
    show_ko_pathway_detail & ko_pathway.ne(""),
    ko_id + " | " + ko_pathway,
    ko_id,
  )
  st.caption(txt(
    f"Legenda: raw count e z-score usam exatamente os mesmos {top_n} KOs e as mesmas {len(lake_cols)} amostras. Todos os {len(counts_f)} KOs são mostrados por padrão; o filtro Top N é opcional.",
    f"Legend: raw-count and z-score panels use exactly the same {top_n} KOs and the same {len(lake_cols)} samples. All {len(counts_f)} KOs are displayed by default; the Top-N filter is optional."
  ))
  with st.expander("table"):
    lake_table = counts_f[[c for c in ["KO", "Metabolism", "KO description"] + lake_cols if c in counts_f.columns]]
  render_st8_heatmap_scope_controls(
    counts_f, numeric_cols, "KO_pathway_label", "All biogeochemical-cycle KO biomarkers", "bio_st8_environment",
  )


def site_access_gate():
  pass
'''


def test_st8_transform_filters_zero_rows_and_preserves_complete_source() -> None:
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_st8_biomarker_heatmap_transform.py"),
    init_globals={"source": st8_source()},
  )["source"]
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_st8_environment_label_transform.py"),
    init_globals={"source": transformed},
  )["source"]
  assert "_APP_ORIGINAL_ST8_HEATMAP_FIGURE" in transformed
  assert "include_undetected_st8" in transformed
  assert "counts_selected_source" in transformed
  assert "source_ko_pathway" in transformed
  assert "lake_scope_audit" in transformed
  assert "Todos os {len(counts_f)} KOs são mostrados por padrão" not in transformed
  assert "lake_table = counts[[c for c in" in transformed
  assert "counts_selected_source, numeric_cols" in transformed
  compile(transformed, "synthetic_st8_app.py", "exec")


def footer_source() -> str:
  return '''from __future__ import annotations


def visitor_counter_public_footer(key: str = "public_footer"):
  pass


def visitor_counter_compact():
  pass


def visitor_analytics_tab():
  if True:
    visitor_counter_public_footer("visitor_public_only")


def code_reproducibility_tab():
  visitor_counter_public_footer("code_reproducibility_counter")


visitor_counter_public_footer("bottom_public_counter")
'''


def test_footer_transform_keeps_one_map_without_redundant_credit() -> None:
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_visitor_footer_final_transform.py"),
    init_globals={"source": footer_source()},
  )["source"]
  assert 'visitor_counter_public_footer("visitor_public_only")' not in transformed
  assert 'visitor_counter_public_footer("code_reproducibility_counter")' not in transformed
  assert transformed.count('visitor_counter_public_footer("bottom_public_counter")') == 1
  assert "App desenvolvido por Leandro de Mattos Pereira." not in transformed
  assert "_visitor_last_location" in transformed
  compile(transformed, "synthetic_footer_app.py", "exec")
