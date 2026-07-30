from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
WORKFLOW_SCRIPT = ROOT / "scripts" / "generate_atlas_workflow_figure.py"
SUPP_DB = ROOT / "src" / "supplementary_database.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Expected block not found: {label}")
  return text.replace(old, new, 1)


def patch_app() -> None:
  text = APP.read_text(encoding="utf-8")

  text = replace_once(
    text,
    '      st.info("Logo não encontrado. Coloque `assets/itv_logo.png` ou `assets/itv_logo.svg`.")',
    '      st.info(txt("Logo não encontrado. Coloque `assets/itv_logo.png` ou `assets/itv_logo.svg`.", "Logo not found. Place `assets/itv_logo.png` or `assets/itv_logo.svg`."))',
    "bilingual missing-logo message",
  )

  old_cards = '''  module_cards = [
    ("🧭", "Article Atlas / Overview", "Resumo do estudo, workflow, rastreabilidade e inventários principais.", "Workflow, cartões do artigo e tabelas de inventário."),
    ("🧬", "Taxonomic profiles", "Perfis taxonômicos das lagoas, diversidade, NMDS, heatmaps e barplots por amostra e lagoa–estação.", "Supplementary Table 1; Figures 2-6; Supplementary Figures 1-4, 14, 19-31, 39 and 43-66."),
    ("🧫", "MAGs and genomes", "Qualidade dos MAGs, taxonomia, anotações, FASTA/GBK e BGCs antiSMASH.", "Supplementary Tables 7, 9 and 11; Figure 7; Supplementary Figures 5, 17-18."),
    ("🧪", "KO Biogeochemical Cycles Biomarkers and differential abundance", "Biomarcadores KO, vias C/N/S/fotossíntese, abundância diferencial e contrastes direcionais.", "Supplementary Tables 4-5 and 8; Figure 8; Supplementary Figures 6-12, 32-36 and 68-69."),
    ("🗺️", "KEGG/KEMET modules", "Completude de módulos KEGG em MAGs e metagenomas com raw values, z-score e tabelas baixáveis.", "Supplementary Tables 3 and 9; Supplementary Figures 38-39; outputs/kegg_modules/*.csv."),
    ("⛓️", "Iron-rich environment comparison", "Comparação entre lagoas amazônicas e ambientes ricos em ferro usando ST8, taxonomia, KOs e metadados IMG/JGI.", "Supplementary Table 8; ST8 heatmaps, metadata tables and comparison figures."),
    ("📚", "Code, methods and references", "Scripts, documentação, métodos, referências e manifestos figura–script.", "Script manifest, documentation index, methods and reference tables."),
  ]
  cards_html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:0.8rem;margin:0.4rem 0 1rem 0;">'
  for icon, title_card, desc, figs in module_cards:
    cards_html += f'<div style="border:1px solid #D1D5DB;border-radius:18px;padding:0.9rem 1rem;background:#FFFFFF;box-shadow:0 2px 8px rgba(15,63,60,0.06);"><div style="font-size:1.6rem;line-height:1;">{icon}</div><div style="font-weight:800;color:#0f3f3c;margin-top:0.35rem;">{html_lib.escape(title_card)}</div><div style="font-size:0.92rem;color:#334155;margin-top:0.35rem;">{html_lib.escape(desc)}</div><div style="font-size:0.84rem;color:#475569;margin-top:0.5rem;"><b>Figures/data:</b> {html_lib.escape(figs)}</div></div>'
'''
  new_cards = '''  module_cards = [
    (
      "🧭",
      txt("Atlas do artigo / Visão geral", "Article Atlas / Overview"),
      txt("Resumo do estudo, workflow, rastreabilidade e inventários principais.", "Study overview, workflow, traceability and core inventories."),
      txt("Workflow, cartões do artigo e tabelas de inventário.", "Workflow, article cards and inventory tables."),
    ),
    (
      "🧬",
      txt("Perfis taxonômicos", "Taxonomic profiles"),
      txt("Perfis taxonômicos das lagoas, diversidade, NMDS, heatmaps e barplots por amostra e lagoa–estação.", "Lagoon taxonomic profiles, diversity, NMDS, heatmaps and barplots by sample and lake–season group."),
      "Supplementary Table 1; Figures 2-6; Supplementary Figures 1-4, 14, 19-31, 39 and 43-66.",
    ),
    (
      "🧫",
      txt("MAGs e genomas", "MAGs and genomes"),
      txt("Qualidade dos MAGs, taxonomia, anotações, FASTA/GBK e BGCs antiSMASH.", "MAG quality, taxonomy, annotations, FASTA/GBK files and antiSMASH BGCs."),
      "Supplementary Tables 7, 9 and 11; Figure 7; Supplementary Figures 5, 17-18.",
    ),
    (
      "🧪",
      txt("Biomarcadores KO de ciclos biogeoquímicos e abundância diferencial", "KO biogeochemical-cycle biomarkers and differential abundance"),
      txt("Biomarcadores KO, vias de C/N/S/fotossíntese, abundância diferencial e contrastes direcionais.", "KO biomarkers, carbon/nitrogen/sulfur/photosynthesis pathways, differential abundance and directional contrasts."),
      "Supplementary Tables 4-5 and 8; Figure 8; Supplementary Figures 6-12, 32-36 and 68-69.",
    ),
    (
      "🗺️",
      "KEGG/KEMET modules",
      txt("Completude de módulos KEGG em MAGs e metagenomas com valores originais e tabelas baixáveis.", "KEGG module completeness in MAGs and metagenomes with original statuses and downloadable source tables."),
      "Supplementary Tables 3 and 9; Supplementary Figures 38-41 and 67; data/final_kegg_st8_update/*.csv.",
    ),
    (
      "⛓️",
      txt("Comparação com ambientes ricos em ferro", "Iron-rich environment comparison"),
      txt("Comparação entre lagoas amazônicas e ambientes ricos em ferro usando ST8, taxonomia, KOs e metadados IMG/JGI.", "Comparison between Amazonian lakes and external iron-rich environments using ST8, taxonomy, KOs and IMG/JGI metadata."),
      "Supplementary Table 8; ST8 heatmaps, metadata tables and comparison figures.",
    ),
    (
      "📚",
      txt("Código, métodos e referências", "Code, methods and references"),
      txt("Scripts, documentação, métodos, referências e manifestos figura–script.", "Scripts, documentation, methods, references and figure-to-script manifests."),
      "Script manifest, documentation index, methods and reference tables.",
    ),
  ]
  figures_data_label = txt("Figuras/dados", "Figures/data")
  cards_html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:0.8rem;margin:0.4rem 0 1rem 0;">'
  for icon, title_card, desc, figs in module_cards:
    cards_html += f'<div style="border:1px solid #D1D5DB;border-radius:18px;padding:0.9rem 1rem;background:#FFFFFF;box-shadow:0 2px 8px rgba(15,63,60,0.06);"><div style="font-size:1.6rem;line-height:1;">{icon}</div><div style="font-weight:800;color:#0f3f3c;margin-top:0.35rem;">{html_lib.escape(title_card)}</div><div style="font-size:0.92rem;color:#334155;margin-top:0.35rem;">{html_lib.escape(desc)}</div><div style="font-size:0.84rem;color:#475569;margin-top:0.5rem;"><b>{html_lib.escape(figures_data_label)}:</b> {html_lib.escape(figs)}</div></div>'
'''
  text = replace_once(text, old_cards, new_cards, "bilingual module cards")

  old_show_all = '''    with c2:
      show_all = st.checkbox(
        f"Show all {available} modules in this set",
        value=False,
        key=f"{key_prefix}_show_all_modules_v10_{scope}",
      )
      module_count = available if show_all else int(st.number_input(
        "Number of displayed modules",
        min_value=1,
        max_value=available,
        value=min(40, available),
        step=1,
        key=f"{key_prefix}_module_count_v10_{scope}_{available}",
      ))
'''
  new_show_all = '''    with c2:
      module_count = int(st.number_input(
        "Number of displayed modules",
        min_value=1,
        max_value=available,
        value=min(40, available),
        step=1,
        key=f"{key_prefix}_module_count_v11_{scope}_{available}",
      ))
'''
  text = replace_once(text, old_show_all, new_show_all, "remove show-all-modules control")

  old_audit_call = '''  _render_static_figure_audit(path, title, key_prefix)
'''
  new_audit_call = '''  page_root = re.sub(r"_P\\d{2,3}$", "", path.stem, flags=re.IGNORECASE)
  page_directories = [
    path.parent,
    BASE_DIR / "outputs" / "final_publication_figures",
    BASE_DIR / "outputs" / "app_supplementary_figures",
    BASE_DIR / "outputs" / "article_highres_figures",
  ]
  additional_pages: dict[int, Path] = {}
  for directory in page_directories:
    if not directory.exists():
      continue
    for candidate in sorted(directory.glob(f"{page_root}_P*.png")):
      match = re.search(r"_P(\\d{2,3})$", candidate.stem, flags=re.IGNORECASE)
      if not match:
        continue
      page_number = int(match.group(1))
      if page_number <= 1:
        continue
      additional_pages.setdefault(page_number, candidate)
  if additional_pages:
    st.markdown("##### " + txt("Páginas adicionais da figura", "Additional figure pages"))
    for page_number, page_path in sorted(additional_pages.items()):
      st.markdown(f"**{txt('Página', 'Page')} {page_number}**")
      st.image(str(page_path), width="stretch")
      page_columns = st.columns(3)
      for page_column, extension, label, mime in zip(
        page_columns,
        [".png", ".pdf", ".svg"],
        ["PNG", "PDF", "SVG"],
        ["image/png", "application/pdf", "image/svg+xml"],
      ):
        page_file = page_path.with_suffix(extension)
        with page_column:
          if page_file.exists():
            st.download_button(
              f"Download page {page_number} {label}",
              data=page_file.read_bytes(),
              file_name=page_file.name,
              mime=mime,
              key=f"download_{key_prefix}_{page_file.stem}_{extension.lstrip('.')}",
              width="stretch",
            )
  _render_static_figure_audit(path, title, key_prefix)
'''
  text = replace_once(text, old_audit_call, new_audit_call, "additional multi-page figure rendering")

  old_palette_caption_anchor = '''  render_plotly_downloadable(fig, key=f"taxonomy_barplot_final_{safe_filename(level_name)}_{safe_filename(view_mode)}_{key_suffix}", basename=f"taxonomy_barplot_{safe_filename(level_name)}_{safe_filename(view_mode)}")
  stats_df, tested, displayed = taxonomy_barplot_statistics(level_name, selected_groups=df["group"].drop_duplicates().tolist(), view_mode=view_mode, top_n=top_n, grouping_factor="lake")
'''
  new_palette_caption_anchor = '''  render_plotly_downloadable(fig, key=f"taxonomy_barplot_final_{safe_filename(level_name)}_{safe_filename(view_mode)}_{key_suffix}", basename=f"taxonomy_barplot_{safe_filename(level_name)}_{safe_filename(view_mode)}")
  st.caption(txt(
    "As cores dos táxons são carregadas da mesma paleta canônica usada para gerar as figuras taxonômicas do artigo (`data/taxonomy_palette.json`).",
    "Taxon colours are loaded from the same canonical palette used to generate the article taxonomy figures (`data/taxonomy_palette.json`).",
  ))
  stats_df, tested, displayed = taxonomy_barplot_statistics(level_name, selected_groups=df["group"].drop_duplicates().tolist(), view_mode=view_mode, top_n=top_n, grouping_factor="lake")
'''
  text = replace_once(text, old_palette_caption_anchor, new_palette_caption_anchor, "taxonomy article-palette caption")

  APP.write_text(text, encoding="utf-8")


def patch_workflow_script() -> None:
  text = WORKFLOW_SCRIPT.read_text(encoding="utf-8")
  old = '''  rounded_box(
    ax,
    0.035,
    0.625,
    0.265,
    0.235,
    COLORS["teal_soft"],
    COLORS["teal"],
    "Scientific data layers",
    "Study metadata\nSample context\nTaxonomic profiles\nKO profiles\nMAG annotations\nIron-rich studies",
    number=1,
    body_size=9.6,
  )
'''
  new = '''  rounded_box(
    ax,
    0.035,
    0.625,
    0.265,
    0.235,
    COLORS["teal_soft"],
    COLORS["teal"],
    "Scientific data layers",
    body=None,
    number=1,
  )
  ax.text(
    0.065,
    0.782,
    "Study metadata\nSample context\nTaxonomic profiles\nKO profiles\nMAG annotations\nIron-rich studies",
    ha="left",
    va="top",
    fontsize=9.2,
    color=COLORS["muted"],
    linespacing=1.30,
    zorder=5,
  )
'''
  text = replace_once(text, old, new, "Scientific data layers layout")
  WORKFLOW_SCRIPT.write_text(text, encoding="utf-8")


def patch_supplementary_database() -> None:
  text = SUPP_DB.read_text(encoding="utf-8")
  import_anchor = '''from .sample_metadata import amazonian_sample_metadata, lake_column_metadata, publication_sample_id
'''
  import_replacement = '''from .sample_metadata import amazonian_sample_metadata, lake_column_metadata, publication_sample_id
from .taxonomy_palette import build_palette as build_taxonomy_palette, load_palette as load_taxonomy_palette
'''
  text = replace_once(text, import_anchor, import_replacement, "taxonomy palette import")

  old = '''  long['relative_abundance'] = long['abundance'] * float(display_factor)
  fig = px.bar(long, x='group', y='relative_abundance', color='taxon', title=f'{level} relative abundance')
  fig.update_layout(barmode='stack', xaxis_title='Sample/group', yaxis_title='Relative abundance (%)', height=650)
'''
  new = '''  long['relative_abundance'] = long['abundance'] * float(display_factor)
  taxon_order = [str(value) for value in ranking.index if str(value) in set(long['taxon'].astype(str))]
  if 'Other taxa' in set(long['taxon'].astype(str)):
    taxon_order.append('Other taxa')
  palette = build_taxonomy_palette(taxon_order, load_taxonomy_palette())
  color_map = {taxon: palette[taxon] for taxon in taxon_order}
  fig = px.bar(
    long,
    x='group',
    y='relative_abundance',
    color='taxon',
    title=f'{level} relative abundance',
    color_discrete_map=color_map,
    category_orders={'taxon': taxon_order},
  )
  fig.update_layout(
    barmode='stack',
    xaxis_title='Sample/group',
    yaxis_title='Relative abundance (%)',
    height=650,
    meta={
      'taxonomy_palette_source': 'data/taxonomy_palette.json',
      'matches_article_taxonomy_palette': True,
    },
  )
'''
  text = replace_once(text, old, new, "canonical taxonomy colours in stacked barplot")
  SUPP_DB.write_text(text, encoding="utf-8")


if __name__ == "__main__":
  patch_app()
  patch_workflow_script()
  patch_supplementary_database()
  print("Application, workflow and taxonomy palette references updated.")
