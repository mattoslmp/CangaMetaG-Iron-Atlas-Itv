from __future__ import annotations


MARKER = "CANGAMETAG_TAXONOMY_ARTICLE_ALIGNMENT_V1 = 1"


def _replace_function(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
  start = text.find(start_marker)
  if start < 0:
    return text
  end = text.find(end_marker, start)
  if end < 0:
    return text
  return text[:start] + replacement.rstrip() + "\n\n" + text[end + 1:]


if MARKER not in source:
  import_anchor = "from src.taxonomy_palette import build_palette as build_canonical_taxonomy_palette, load_palette as load_canonical_taxonomy_palette\n"
  article_imports = '''from src.article_taxonomy import (
  ARTICLE_ALPHA_ORDER,
  article_alpha_boxplot,
  article_season_barplot,
  article_static_source_validation,
  article_taxonomy_profile_table,
)
'''
  if article_imports not in source and import_anchor in source:
    source = source.replace(import_anchor, import_anchor + article_imports, 1)

  # Every public table receives a visible-by-default show/hide control. The
  # replacement is applied before injecting the wrappers so the original
  # Streamlit call remains available internally.
  source = source.replace("st.dataframe(", "_retractable_dataframe(")
  source = source.replace("st.table(", "_retractable_table(")
  wrapper_anchor = "def runtime_setting(key: str, default: str = \"\") -> str:\n"
  wrapper_code = r'''_ORIGINAL_ST_DATAFRAME = st.dataframe
_ORIGINAL_ST_TABLE = st.table
_RETRACTABLE_TABLE_SEQUENCE = 0


def _retractable_table_key(raw_key: object, kind: str) -> str:
  global _RETRACTABLE_TABLE_SEQUENCE
  _RETRACTABLE_TABLE_SEQUENCE += 1
  text = str(raw_key or "").strip()
  if text:
    token = re.sub(r"[^A-Za-z0-9_.-]+", "_", text)[:140]
  else:
    token = f"anonymous_{_RETRACTABLE_TABLE_SEQUENCE}"
  return f"retractable_{kind}_{token}_visibility"


def _retractable_dataframe(data=None, *args, **kwargs):
  raw_key = kwargs.get("key")
  raw_key_text = str(raw_key or "")
  visibility_label = (
    txt("MAGs do artigo — mostrar/ocultar tabela", "Article MAGs — show/hide table")
    if "bins_identificados" in raw_key_text
    else txt("Mostrar/ocultar tabela", "Show/hide table")
  )
  visible = st.toggle(
    visibility_label,
    value=True,
    key=_retractable_table_key(raw_key, "dataframe"),
  )
  if not visible:
    st.caption(txt("Tabela recolhida pelo usuário.", "Table collapsed by the user."))
    return None
  return _ORIGINAL_ST_DATAFRAME(data, *args, **kwargs)


def _retractable_table(data=None, *args, **kwargs):
  visible = st.toggle(
    txt("Mostrar/ocultar tabela", "Show/hide table"),
    value=True,
    key=_retractable_table_key(kwargs.get("key"), "table"),
  )
  if not visible:
    st.caption(txt("Tabela recolhida pelo usuário.", "Table collapsed by the user."))
    return None
  return _ORIGINAL_ST_TABLE(data, *args, **kwargs)


'''
  if wrapper_anchor in source and "def _retractable_dataframe(" not in source:
    source = source.replace(wrapper_anchor, wrapper_code + wrapper_anchor, 1)

  # Replace the previous oversized workflow viewport by a whole-page fit. The
  # original raster is displayed without redrawing or moving any text/shape.
  overview_start = source.find("def overview_tab():\n")
  workflow_start = source.find(
    '  workflow_path = BASE_DIR / "outputs" / "app_supplementary_figures" / "SupplementaryFigure29_complete_computational_workflow.png"',
    overview_start,
  )
  workflow_end = source.find(
    '\n\n  st.markdown("#### " + txt("Logos dos módulos e o que cada módulo faz"',
    workflow_start,
  )
  if workflow_start >= 0 and workflow_end >= 0:
    workflow_block = r'''  workflow_path = BASE_DIR / "outputs" / "app_supplementary_figures" / "SupplementaryFigure29_complete_computational_workflow.png"
  if workflow_path.exists():
    st.image(
      str(workflow_path),
      width="stretch",
      caption=txt(
        "Workflow computacional completo do atlas. A imagem inteira foi ajustada à largura da página sem alterar sua geometria.",
        "Complete computational workflow of the atlas. The whole image is fitted to the page width without changing its geometry.",
      ),
    )
  else:
    st.warning(txt(
      "Figura do workflow não encontrada em outputs/app_supplementary_figures/.",
      "Workflow figure not found under outputs/app_supplementary_figures/.",
    ))'''
    source = source[:workflow_start] + workflow_block + source[workflow_end:]

  count_profile = r'''def _taxonomy_count_profile_final(level_name: str, view_mode: str) -> pd.DataFrame:
  domain, rank = _taxonomy_selection_parts(level_name)
  frame = article_taxonomy_profile_table(domain, rank, view_mode=view_mode, top_n=None, base_dir=BASE_DIR)
  if frame is None or frame.empty:
    return pd.DataFrame(columns=[
      "group", "taxon", "count", "abundance", "domain", "rank",
      "source_sheet", "environment_feature", "lake", "season",
    ])
  frame = frame.copy()
  frame["level"] = level_name
  return frame'''
  source = _replace_function(
    source,
    "def _taxonomy_count_profile_final(level_name: str, view_mode: str) -> pd.DataFrame:",
    "\ndef _taxonomy_matrix_from_profile_final",
    count_profile,
  )

  alpha_renderer = r'''def _render_alpha_final(level_name: str) -> None:
  st.markdown("### " + txt(
    "Diversidade alfa — mesma fonte e desenho da figura do artigo",
    "Alpha diversity — same source and design as the article figure",
  ))
  figure, source_table = article_alpha_boxplot(BASE_DIR)
  if source_table.empty or not list(getattr(figure, "data", []) or []):
    st.warning(txt(
      "A tabela-fonte da Supplementary Figure 4 não foi encontrada.",
      "The Supplementary Figure 4 source table was not found.",
    ))
    return
  st.info(txt(
    "O boxplot interativo usa exatamente a tabela gerada para a Supplementary Figure 4, a mesma ordem AM-D, AM-R, TIA-D, TIA-R, TI-D, TI-R, VI-D, VI-R, a mesma paleta e as métricas rarefeitas a 32.999 CDS. Nenhuma métrica é recalculada nesta tela.",
    "The interactive boxplot uses the exact table generated for Supplementary Figure 4, the same AM-D, AM-R, TIA-D, TIA-R, TI-D, TI-R, VI-D, VI-R order, the same palette and metrics rarefied to 32,999 CDS. No metric is recalculated on this screen.",
  ))
  render_plotly_downloadable(
    figure,
    key="article_exact_alpha_diversity_boxplot_s4",
    basename="SupplementaryFigure4_alpha_diversity_interactive",
    audit_input_table=source_table,
    audit_processed_table=source_table,
    audit_output_table=source_table,
    audit_method="Deterministic rarefaction to 32,999 CDS followed by Observed OTUs, Chao1 and Shannon; same source, group order and palette as Supplementary Figure 4.",
    audit_input_source="data/final_publication_derived/SupplementaryFigure4_alpha_diversity_CDS_32999_source.csv",
    audit_script="scripts/final_publication_figures/06_recalculate_rarefaction_alpha_32999.py",
  )
  with st.expander(
    txt("Tabela exata da Supplementary Figure 4", "Exact Supplementary Figure 4 table"),
    expanded=True,
  ):
    show_table(source_table, "article_exact_alpha_diversity_source_s4", height=390)
    csv_button(
      source_table,
      "SupplementaryFigure4_alpha_diversity_CDS_32999_source.csv",
      txt("Baixar tabela científica", "Download scientific table"),
    )'''
  source = _replace_function(
    source,
    "def _render_alpha_final(level_name: str) -> None:",
    "\ndef _permanova_final",
    alpha_renderer,
  )

  taxonomy_tab = r'''def taxonomy_tab():
  st.subheader(txt(
    "Perfis taxonômicos da Supplementary Table 1",
    "Taxonomic profiles from Supplementary Table 1",
  ))
  st.markdown(txt(
    "As figuras estáticas e os painéis interativos usam os mesmos arquivos `data/resultado.cds.otu.tab` e `data/resultado.cds.tax.tab`. A classificação é separada por domínio antes da agregação; a nomenclatura atual do NCBI altera somente os rótulos de Phylum, Order, Family e Genus, nunca as contagens.",
    "Static figures and interactive panels use the same `data/resultado.cds.otu.tab` and `data/resultado.cds.tax.tab` files. Classification is separated by domain before aggregation; current NCBI nomenclature changes Phylum, Order, Family and Genus labels only, never counts.",
  ))

  meta = taxonomy_samples_metadata()
  with st.expander(
    txt("Amostras, datas, coordenadas e environment_feature", "Samples, dates, coordinates and environment_feature"),
    expanded=True,
  ):
    columns = [column for column in [
      "sample.id", "Sample", "collection.date", "collection_date", "latitude",
      "longitude", "lat", "lon", "environment_feature", "lake", "season", "depth",
    ] if column in meta.columns]
    show_table(meta[columns], "taxonomy_metadata_final_article_aligned", height=310)
    csv_button(meta, "taxonomy_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))
  if {"lat", "lon"}.issubset(meta.columns):
    show_high_quality_sample_map(meta, key="taxonomy_sampling_map_article_aligned")

  audit_specs = [
    ("TAXONOMY_STRICT_LT1_ROW_AUDIT_20260805.csv", txt("Auditoria linha a linha do limiar estrito <1%", "Row-level strict <1% audit")),
    ("OTHER_TAXA_LT1_TRACEABILITY_20260805.csv", txt("Rastreabilidade de Other taxa (<1%)", "Other taxa (<1%) traceability")),
    ("UNCLASSIFIED_PERCENTAGES_20260805.csv", txt("Percentuais exatos de Unclassified", "Exact Unclassified percentages")),
  ]
  with st.expander(txt("Auditorias taxonômicas canônicas", "Canonical taxonomy audits"), expanded=False):
    for audit_name, audit_label in audit_specs:
      audit_path = BASE_DIR / "data" / "final_publication_derived" / audit_name
      if audit_path.exists():
        audit_table = pd.read_csv(audit_path)
        st.markdown(f"**{audit_label}**")
        show_table(audit_table, f"taxonomy_audit_{audit_name}", height=280)
        csv_button(audit_table, audit_name, txt("Baixar auditoria", "Download audit"))

  st.markdown("### " + txt(
    "Figuras taxonômicas finais usadas no artigo",
    "Final taxonomy figures used in the article",
  ))
  taxonomy_figures = [
    ("Figure2_taxonomic_phylum_bacteria_horizontal_CDS.png", txt("Perfis de filos de Bacteria nas estações seca e chuvosa.", "Bacteria phylum profiles in dry and rainy seasons.")),
    ("Figure3_taxonomic_phylum_archaea_horizontal_CDS.png", txt("Perfis de filos de Archaea nas estações seca e chuvosa.", "Archaea phylum profiles in dry and rainy seasons.")),
    ("Figure4_taxonomic_bacteria_genus_profiles.png", txt("Perfis de gêneros, NMDS e biplot RDA de Bacteria.", "Bacteria genus profiles, NMDS and RDA biplot.")),
    ("Figure5_taxonomic_archaea_genus_profiles.png", txt("Perfis de gêneros, NMDS e biplot RDA de Archaea.", "Archaea genus profiles, NMDS and RDA biplot.")),
    ("SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct.png", txt("Barplot suplementar de filos de Bacteria.", "Supplementary Bacteria phylum barplot.")),
    ("SupplementaryFigure45_Taxonomy_Archaea_Phylum_individual_samples_barplot_100pct.png", txt("Barplot suplementar de filos de Archaea.", "Supplementary Archaea phylum barplot.")),
    ("SupplementaryFigure59_Taxonomy_Bacteria_Genus_individual_samples_barplot_100pct.png", txt("Barplot suplementar de gêneros de Bacteria.", "Supplementary Bacteria genus barplot.")),
    ("SupplementaryFigure61_Taxonomy_Archaea_Genus_individual_samples_barplot_100pct.png", txt("Barplot suplementar de gêneros de Archaea.", "Supplementary Archaea genus barplot.")),
  ]
  for figure_name, figure_caption in taxonomy_figures:
    _display_static_publication_image(
      BASE_DIR / "outputs" / "final_publication_figures" / figure_name,
      figure_name,
      figure_caption,
      key_prefix="taxonomy_direct_final_article_aligned",
    )

  st.markdown("### " + txt(
    "Barplots interativos correspondentes às Figuras 2 e 3",
    "Interactive barplots corresponding to Figures 2 and 3",
  ))
  st.info(txt(
    "Dry é sempre apresentado à esquerda e Rainy à direita. Cada painel usa a mesma regra estrita por amostra: todos os táxons que atingem 1% permanecem explícitos, somente valores abaixo de 1% formam Other taxa (<1%) e Unclassified permanece separado com seu percentual exato. Não há corte Top-N.",
    "Dry is always shown on the left and Rainy on the right. Each panel uses the same strict per-sample rule: every taxon reaching 1% remains explicit, only values below 1% form Other taxa (<1%), and Unclassified stays separate with its exact percentage. No Top-N cutoff is used.",
  ))
  for article_domain in ["Bacteria", "Archaea"]:
    st.markdown(f"#### {article_domain} — Phylum")
    validation = article_static_source_validation(article_domain, "Phylum", None, BASE_DIR)
    validation_status = str(validation.iloc[0].get("status", "")) if not validation.empty else ""
    if validation_status == "PASS":
      st.success(txt(
        f"Validação aprovada para {article_domain}: o painel interativo e a tabela-fonte da figura estática possuem os mesmos percentuais.",
        f"Validation passed for {article_domain}: the interactive panel and static-figure source table contain the same percentages.",
      ))
    else:
      st.warning(txt(
        f"A validação automática de {article_domain} retornou {validation_status or 'sem resultado'}; consulte a tabela abaixo antes de interpretar o painel.",
        f"The automatic {article_domain} validation returned {validation_status or 'no result'}; inspect the table below before interpreting the panel.",
      ))
    with st.expander(txt("Validação figura–app", "Figure–app validation"), expanded=True):
      show_table(validation, f"taxonomy_static_interactive_validation_{article_domain}", height=190)

    dry_column, rainy_column = st.columns(2)
    for season_name, column in [("Dry", dry_column), ("Rainy", rainy_column)]:
      with column:
        figure, exact_table, matrix = article_season_barplot(
          article_domain, "Phylum", season_name, top_n=None, base_dir=BASE_DIR,
        )
        render_plotly_downloadable(
          figure,
          key=f"article_exact_{article_domain}_Phylum_{season_name}",
          basename=f"{article_domain}_Phylum_{season_name}_interactive_article_matched",
          audit_input_table=exact_table,
          audit_processed_table=matrix,
          audit_output_table=exact_table,
          audit_method="Domain-filtered CDS counts; per-sample normalization; classified taxa strictly below 1% combined as Other taxa (<1%); exactly 1% explicit; Unclassified independent with exact labels; no Top-N.",
          audit_input_source="data/resultado.cds.otu.tab + data/resultado.cds.tax.tab",
          audit_script="scripts/generate_final_domain_taxonomy_figures.py; scripts/taxonomy/harmonize_ncbi_taxonomy_and_regenerate.py",
        )
        with st.expander(
          txt(f"Tabela exata — {season_name}", f"Exact table — {season_name}"),
          expanded=True,
        ):
          show_table(
            exact_table,
            f"article_exact_table_{article_domain}_Phylum_{season_name}",
            height=390,
          )
          csv_button(
            exact_table,
            f"{article_domain}_Phylum_{season_name}_article_matched.csv",
            txt("Baixar tabela científica", "Download scientific table"),
          )

  st.markdown("### " + txt(
    "Explorador taxonômico interativo com nomenclatura NCBI atual",
    "Interactive taxonomy explorer with current NCBI nomenclature",
  ))
  controls = st.columns(3)
  with controls[0]:
    selected_domain = st.selectbox("Domain", ["Bacteria", "Archaea"], index=0, key="taxonomy_article_domain")
  with controls[1]:
    selected_rank = st.selectbox(
      txt("Nível taxonômico", "Taxonomic level"),
      ["Phylum", "Order", "Family", "Genus"],
      index=1,
      key="taxonomy_article_rank",
    )
  with controls[2]:
    selected_visualization = st.selectbox(
      txt("Visualização", "Visualization"),
      ["Seasonal barplots", "Relative-abundance heatmap"],
      index=0,
      key="taxonomy_article_visualization",
      format_func=lambda value: txt("Barplots sazonais", "Seasonal barplots") if value.startswith("Seasonal") else txt("Heatmap de abundância relativa", "Relative-abundance heatmap"),
    )
  level_name = f"{selected_rank} — {selected_domain}"
  top_n = None

  explorer_tables = []
  if selected_visualization == "Seasonal barplots":
    left_panel, right_panel = st.columns(2)
    for season_name, column in [("Dry", left_panel), ("Rainy", right_panel)]:
      with column:
        figure, exact_table, matrix = article_season_barplot(
          selected_domain, selected_rank, season_name, top_n=top_n, base_dir=BASE_DIR,
        )
        render_plotly_downloadable(
          figure,
          key=f"taxonomy_explorer_{selected_domain}_{selected_rank}_{season_name}_strict_lt1",
          basename=f"taxonomy_{selected_domain}_{selected_rank}_{season_name}_strict_lt1",
          audit_input_table=exact_table,
          audit_processed_table=matrix,
          audit_output_table=exact_table,
          audit_method="Same domain-separated CDS matrix as the article; current NCBI label harmonisation; counts unchanged.",
          audit_input_source="data/resultado.cds.otu.tab + data/resultado.cds.tax.tab",
          audit_script="scripts/taxonomy/harmonize_ncbi_taxonomy_and_regenerate.py",
        )
        explorer_tables.append(exact_table)
  else:
    heatmap_mode = st.radio(
      txt("Unidades do heatmap", "Heatmap units"),
      ["Individual samples", "Aggregated lake-season groups"],
      horizontal=True,
      key=f"taxonomy_article_heatmap_mode_{selected_domain}_{selected_rank}",
    )
    exact_table, _ = _taxonomy_heatmap_final(
      level_name, heatmap_mode, top_n, False, "article_aligned", text_filter="",
    )
    explorer_tables.append(exact_table)

  if explorer_tables:
    combined_table = pd.concat(explorer_tables, ignore_index=True, sort=False)
    with st.expander(
      txt("Tabela exata do explorador", "Exact explorer table"),
      expanded=True,
    ):
      show_table(
        combined_table,
        f"taxonomy_explorer_exact_{selected_domain}_{selected_rank}_{selected_visualization}",
        height=500,
      )
      csv_button(
        combined_table,
        f"taxonomy_explorer_{selected_domain}_{selected_rank}.csv",
        txt("Baixar tabela científica", "Download scientific table"),
      )

  _render_alpha_final(level_name)
  _render_beta_final(level_name)
  taxonomic_rda_panel()'''
  source = _replace_function(source, "def taxonomy_tab():", "\ndef site_access_gate", taxonomy_tab)

  # Add the reproducible NCBI harmonisation procedure to the public methodology,
  # while script preview/download remains centralized in Final figures & scripts.
  methods_anchor = '  st.markdown("### " + txt("Código e reprodutibilidade", "Code and reproducibility"))\n'
  methods_text = r'''  st.markdown("### " + txt(
    "Harmonização reprodutível da taxonomia NCBI",
    "Reproducible NCBI taxonomy harmonisation",
  ))
  st.markdown(txt(
    "Os nomes em Phylum, Order, Family e Genus são comparados às entradas do taxdump atual do NCBI pelo script `scripts/taxonomy/harmonize_ncbi_taxonomy_and_regenerate.py`. Somente nomes científicos/sinônimos com rank compatível são substituídos. A matriz OTU, os identificadores, as dimensões e todas as contagens são verificados antes e depois; qualquer diferença numérica interrompe a execução. As Figuras 2–5 são então regeneradas pelo gerador canônico, preservando proporções, ordem de amostras, paleta e elementos gráficos. Comando reproduzível: `python scripts/taxonomy/harmonize_ncbi_taxonomy_and_regenerate.py --download-taxdump`.",
    "Names at Phylum, Order, Family and Genus ranks are compared with the current NCBI taxdump by `scripts/taxonomy/harmonize_ncbi_taxonomy_and_regenerate.py`. Only scientific names/synonyms with a compatible rank are replaced. The OTU matrix, identifiers, dimensions and all counts are checked before and after; any numeric difference stops execution. Figures 2–5 are then regenerated by the canonical generator while preserving proportions, sample order, palette and graphical elements. Reproducible command: `python scripts/taxonomy/harmonize_ncbi_taxonomy_and_regenerate.py --download-taxdump`.",
  ))

'''
  if methods_anchor in source and "Harmonização reprodutível da taxonomia NCBI" not in source:
    source = source.replace(methods_anchor, methods_text + methods_anchor, 1)

  marker_anchor = "def page_header():\n"
  if marker_anchor in source:
    source = source.replace(marker_anchor, MARKER + "\n\n\n" + marker_anchor, 1)
