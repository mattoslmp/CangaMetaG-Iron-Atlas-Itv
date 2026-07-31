from __future__ import annotations

"""Use corrected frozen taxonomy assets and exact article ordination panels."""

MARKER = "CANGAMETAG_CORRECTED_TAXONOMY_STATIC_ASSETS_V2 = 1"

if MARKER not in source:
  import_anchor = (
    "from src.current_taxonomy_display import harmonize_table as "
    "harmonize_current_taxonomy_table\n"
  )
  corrected_imports = '''from src.corrected_taxonomy_static_assets import (
  CORRECTED_TAXONOMY_STATIC_FILENAMES,
  build_corrected_taxonomy_publication_overlay,
  materialize_corrected_taxonomy_static,
)
from src.article_frozen_taxonomy_panels import article_frozen_taxonomy_figure
'''
  if corrected_imports not in source:
    if import_anchor in source:
      source = source.replace(import_anchor, import_anchor + corrected_imports, 1)
    else:
      source = corrected_imports + source

  display_signature = (
    'def _display_static_publication_image(path: Path, title: str, caption: str = "", '
    'key_prefix: str = "static_publication_image") -> None:'
  )
  display_start = source.find(display_signature)
  if display_start >= 0:
    display_end = source.find("\ndef ", display_start + len(display_signature))
    if display_end < 0:
      display_end = len(source)
    original = source[display_start:display_end].replace(
      "def _display_static_publication_image(",
      "def _display_static_publication_image_original(",
      1,
    )
    wrapper = r'''
def _display_static_publication_image(path: Path, title: str, caption: str = "", key_prefix: str = "static_publication_image") -> None:
  corrected_path = materialize_corrected_taxonomy_static(path.name, APP_CACHE_DIR)
  if corrected_path is None:
    return _display_static_publication_image_original(path, title, caption, key_prefix)
  st.markdown(f"#### `{path.name}`")
  st.image(str(corrected_path), width="stretch", caption=caption or None)
  st.download_button(
    txt("Baixar SVG corrigido", "Download corrected SVG"),
    data=corrected_path.read_bytes(),
    file_name=corrected_path.name,
    mime="image/svg+xml",
    key=f"{key_prefix}_{safe_filename(path.stem)}_corrected_svg",
    width="stretch",
  )
  st.caption(txt(
    "Ativo estático da versão congelada do artigo. Apenas a nomenclatura taxonômica validada foi atualizada; valores e geometria permanecem os do artigo.",
    "Static asset from the frozen article version. Only validated taxonomy nomenclature was updated; values and geometry remain those of the article.",
  ))
'''
    source = source[:display_start] + original + "\n\n" + wrapper + source[display_end:]

  valid_signature = "def is_valid_display_image(path: Path) -> tuple[bool, str]:"
  valid_start = source.find(valid_signature)
  if valid_start >= 0:
    valid_end = source.find("\ndef ", valid_start + len(valid_signature))
    if valid_end < 0:
      valid_end = len(source)
    original = source[valid_start:valid_end].replace(
      "def is_valid_display_image(",
      "def is_valid_display_image_original(",
      1,
    )
    wrapper = r'''
def is_valid_display_image(path: Path) -> tuple[bool, str]:
  if path.suffix.lower() == ".svg":
    try:
      text = path.read_text(encoding="utf-8", errors="strict")
      if "<svg" not in text[:5000].lower():
        return False, "invalid SVG"
      return True, "validated corrected SVG"
    except Exception as exc:
      return False, f"unreadable SVG: {exc}"
  return is_valid_display_image_original(path)
'''
    source = source[:valid_start] + original + "\n\n" + wrapper + source[valid_end:]

  directory_block = '''  main_fig_dir = BASE_DIR / "outputs" / "final_publication_figures"
  supplementary_fig_dir = BASE_DIR / "outputs" / "app_supplementary_figures"
'''
  directory_replacement = '''  source_main_fig_dir = BASE_DIR / "outputs" / "final_publication_figures"
  source_supplementary_fig_dir = BASE_DIR / "outputs" / "app_supplementary_figures"
  main_fig_dir, supplementary_fig_dir = build_corrected_taxonomy_publication_overlay(
    source_main_fig_dir,
    source_supplementary_fig_dir,
    APP_CACHE_DIR,
  )
'''
  if directory_block in source:
    source = source.replace(directory_block, directory_replacement, 1)

  raster_candidate = 'fp.suffix.lower() in image_suffixes and not _is_prohibited_publication_figure(fp)'
  corrected_candidate = (
    '(fp.suffix.lower() in image_suffixes or fp.name in '
    'CORRECTED_TAXONOMY_STATIC_FILENAMES) and not '
    '_is_prohibited_publication_figure(fp)'
  )
  source = source.replace(raster_candidate, corrected_candidate)

  exact_renderer = r'''
def _render_frozen_article_taxonomy_ordinations() -> None:
  st.markdown("### " + txt(
    "Painéis interativos exatos das Figuras 4 e 5",
    "Exact interactive panels from Figures 4 and 5",
  ))
  st.info(txt(
    "Estes painéis não recalculam NMDS ou RDA. Eles leem diretamente as matrizes, coordenadas, vetores e estatísticas congeladas em ARTICLE_FINAL_ISME_SUBMISSION_Leandrov27-julho FINAL_SUBMISSION_FILES.",
    "These panels do not recompute NMDS or RDA. They read the matrices, coordinates, vectors and statistics frozen in ARTICLE_FINAL_ISME_SUBMISSION_Leandrov27-julho FINAL_SUBMISSION_FILES directly.",
  ))
  tabs = st.tabs(["Bacteria — Figure 4", "Archaea — Figure 5"])
  for domain, tab in zip(["Bacteria", "Archaea"], tabs):
    with tab:
      figure, tables = article_frozen_taxonomy_figure(domain)
      render_plotly_downloadable(
        figure,
        key=f"frozen_article_taxonomy_{domain}",
        basename=f"{'Figure4' if domain == 'Bacteria' else 'Figure5'}_interactive_exact_article",
        audit_input_table=tables["genus_relative_abundance"],
        audit_processed_table=tables["nmds_scores"],
        audit_output_table=tables["ordination_statistics"],
        audit_method="Direct rendering of frozen article relative-abundance matrix, NMDS coordinates, RDA site scores, environmental vectors, representative-genus vectors and statistics; no ordination recomputation.",
        audit_input_source="data/article_frozen_taxonomy_bacteria.json or data/article_frozen_taxonomy_archaea.json",
        audit_script="src/article_frozen_taxonomy_panels.py",
      )
      with st.expander(txt("Tabelas exatas da figura", "Exact figure tables"), expanded=False):
        for table_name, table in tables.items():
          st.markdown(f"#### `{table_name}`")
          show_table(table, f"frozen_{domain}_{table_name}", height=320)
          csv_button(
            table,
            f"{'Figure4' if domain == 'Bacteria' else 'Figure5'}_{table_name}.csv",
            txt("Baixar tabela", "Download table"),
            key=f"frozen_{domain}_{table_name}_csv",
          )
'''
  site_anchor = "def site_access_gate"
  if site_anchor in source and "def _render_frozen_article_taxonomy_ordinations" not in source:
    source = source.replace(site_anchor, exact_renderer + "\n\n" + site_anchor, 1)

  old_tail = '''  _render_alpha_final(level_name)
  _render_beta_final(level_name)
  taxonomic_rda_panel()'''
  new_tail = '''  _render_alpha_final(level_name)
  _render_frozen_article_taxonomy_ordinations()'''
  source = source.replace(old_tail, new_tail, 1)

  source += f"\n\n{MARKER}\n"
