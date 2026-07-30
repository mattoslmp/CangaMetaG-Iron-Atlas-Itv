from __future__ import annotations

import re


MARKER = "CANGAMETAG_PUBLIC_RELEASE_V1_20260730 = 1"


def _replace_function(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
  start = text.find(start_marker)
  if start < 0:
    return text
  end = text.find(end_marker, start)
  if end < 0:
    return text
  return text[:start] + replacement.rstrip() + "\n\n" + text[end + 1:]


if MARKER not in source:
  if "import base64\n" not in source:
    source = source.replace("import json\n", "import base64\nimport json\n", 1)

  source = re.sub(
    r'^APP_VERSION\s*=\s*["\'][^"\']+["\']',
    'APP_VERSION = "1.0"',
    source,
    count=1,
    flags=re.MULTILINE,
  )
  source = re.sub(
    r'^PUBLIC_PROGRAM_VERSION\s*=\s*["\'][^"\']+["\']',
    'PUBLIC_PROGRAM_VERSION = "1.0"',
    source,
    count=1,
    flags=re.MULTILINE,
  )
  release_anchor = 'APP_VERSION = "1.0"\n'
  if "APP_RELEASE_DATE =" not in source and release_anchor in source:
    source = source.replace(
      release_anchor,
      release_anchor
      + 'APP_RELEASE_DATE = "2026-07-30"\n'
      + 'APP_RELEASE_LABEL = "30 July 2026"\n',
      1,
    )

  # Scripts and code previews are centralized in Final figures & scripts.
  source = _replace_function(
    source,
    "def render_section_script_inventory(",
    "\ndef taxonomy_tab():",
    '''def render_section_script_inventory(section_title: str, keywords: list[str], key_prefix: str) -> None:
  """Keep section-level script indexes internal; public scripts live in Final figures & scripts."""
  return''',
  )

  # Remove the dedicated Code & reproducibility navigation item. A concise
  # reproducibility section is embedded in Methods & references below.
  source = source.replace(
    '  ("code_reproducibility", "💻 " + txt("Códigos e reprodutibilidade", "Code & reproducibility"), code_reproducibility_tab),\n',
    '',
    1,
  )
  source = source.replace(
    '("methods_references", "📚 " + txt("Métodos e referências", "Methods & references"), references_methods_tab),',
    '("methods_references", "📚 " + txt("Métodos, referências e reprodutibilidade", "Methods, references & reproducibility"), references_methods_tab),',
    1,
  )

  # Version/date labels in the public header and overview.
  source = source.replace(
    '<span class="pill">App version {APP_VERSION}</span>',
    '<span class="pill">Version {APP_VERSION} • {APP_RELEASE_LABEL}</span>',
  )
  source = source.replace(
    'App version {APP_VERSION}</div>',
    'Version {APP_VERSION} • {APP_RELEASE_LABEL}</div>',
  )

  # Never render visit analytics in the header or inside a module. Remove all
  # call sites, then add one public footer after the active page has completed.
  source = re.sub(
    r'(?m)^[ \t]*visitor_counter_compact\([^\n]*\)\s*\n',
    '',
    source,
  )
  source = re.sub(
    r'(?m)^[ \t]*visitor_counter_public_footer\([^\n]*\)\s*\n',
    '',
    source,
  )
  bottom_anchor = '''if selected_page == article_atlas_label:
  contact_form_panel("global_contact", expanded=False)
'''
  if bottom_anchor in source:
    source = source.replace(
      bottom_anchor,
      bottom_anchor + 'visitor_counter_public_footer("bottom_public_counter")\n',
      1,
    )

  # Geographic visit details remain visible but are not downloadable.
  source = source.replace(
    '''      csv_button(
        detail,
        "visitor_country_region_detail.csv",
        txt("Baixar detalhes geográficos", "Download geographic details"),
      )
''',
    '',
    1,
  )

  # Render the workflow at a large, native-like width in a scrollable viewport.
  # The source artwork is not edited, so text cannot move over geometric shapes.
  old_workflow = '''  workflow_path = BASE_DIR / "outputs" / "app_supplementary_figures" / "SupplementaryFigure29_complete_computational_workflow.png"
  if workflow_path.exists():
    st.image(str(workflow_path), width="stretch", caption=txt("Workflow computacional completo do atlas.", "Complete computational workflow of the atlas."))
  else:
    st.warning(txt("Figura do workflow não encontrada em outputs/app_supplementary_figures/.", "Workflow figure not found in outputs/app_supplementary_figures/."))'''
  new_workflow = '''  workflow_path = BASE_DIR / "outputs" / "app_supplementary_figures" / "SupplementaryFigure29_complete_computational_workflow.png"
  if workflow_path.exists():
    workflow_width = 2400
    workflow_height = 1200
    if Image is not None:
      try:
        with Image.open(workflow_path) as workflow_image:
          workflow_width, workflow_height = workflow_image.size
      except Exception:
        pass
    display_width = max(1900, min(2800, int(workflow_width)))
    scaled_height = int(workflow_height * display_width / max(1, workflow_width))
    viewport_height = max(720, min(1180, scaled_height + 30))
    workflow_b64 = base64.b64encode(workflow_path.read_bytes()).decode("ascii")
    components.html(
      f"""
      <div style="width:100%;height:{viewport_height - 8}px;overflow:auto;background:#ffffff;
                  border:1px solid #cbd5e1;border-radius:14px;padding:10px;box-sizing:border-box;">
        <img src="data:image/png;base64,{workflow_b64}"
             alt="Complete computational workflow of the atlas"
             style="display:block;width:{display_width}px;max-width:none;height:auto;margin:0 auto;" />
      </div>
      """,
      height=viewport_height,
      scrolling=True,
    )
    st.caption(txt(
      "Workflow computacional completo em visualização ampliada. Use as barras de rolagem para ler todas as etapas; a geometria original foi preservada.",
      "Complete computational workflow in an enlarged view. Use the scrollbars to inspect every step; the original geometry is preserved.",
    ))
  else:
    st.warning(txt("Figura do workflow não encontrada em outputs/app_supplementary_figures/.", "Workflow figure not found in outputs/app_supplementary_figures/."))'''
  if old_workflow in source:
    source = source.replace(old_workflow, new_workflow, 1)

  # Internal ST8 inventories remain packaged but are not exposed as public
  # indexes/download buttons. Scientific result tables remain visible.
  inventory_start = source.find('  with st.expander(txt("Tabelas e metadados ST8 incluídos", "Included ST8 tables and metadata"), expanded=False):')
  inventory_end = source.find('  st.caption(txt(\n    "A tabela ST8 final foi reorganizada', inventory_start)
  if inventory_start >= 0 and inventory_end >= 0:
    source = source[:inventory_start] + source[inventory_end:]
  source = source.replace(
    '  csv_button(meta_f[cols], "ST8_final_metadata_filtered.csv", txt("Baixar metadados filtrados", "Download filtered metadata"))\n',
    '',
    1,
  )

  # Replace the public Methods page by a focused scientific methods/reference
  # view. Internal indexes and script previews stay on disk; script access is
  # centralized in Final figures & scripts.
  references_function = r'''def references_methods_tab():
  st.subheader(txt(
    "Materiais, métodos, referências e reprodutibilidade",
    "Materials, methods, references and reproducibility",
  ))
  st.caption(f"Version {APP_VERSION} — {APP_RELEASE_LABEL}")
  st.markdown(txt(
    "Esta seção apresenta as fontes científicas, os critérios analíticos e as referências realmente utilizadas pelo aplicativo público. Índices técnicos, hashes, inventários internos e visualização de scripts permanecem nos diretórios do projeto; todos os scripts públicos são centralizados em **Final figures & scripts**.",
    "This section presents the scientific sources, analytical criteria and references actually used by the public application. Technical indexes, hashes, internal inventories and script previews remain in the project directories; all public scripts are centralized under **Final figures & scripts**.",
  ))

  st.markdown(f"**{txt('Título', 'Title')}:** {article_field('title', DEFAULT_ARTICLE_TITLE)}")
  st.markdown(f"**{txt('Autores', 'Authors')}:** {normalize_authors_string(article_field('authors', DEFAULT_ARTICLE_AUTHORS))}")
  st.markdown(f"**{txt('Afiliação', 'Affiliation')}:** {article_field('affiliation', DEFAULT_ARTICLE_AFFILIATION)}")
  st.markdown(f"**{txt('Correspondência', 'Correspondence')}:** {article_field('correspondence', DEFAULT_ARTICLE_CORRESPONDENCE)}")
  st.markdown("### " + txt("Resumo do artigo", "Article abstract"))
  st.info(article_field("abstract", DEFAULT_ARTICLE_ABSTRACT))

  st.markdown("### " + txt("Tabelas suplementares do artigo", "Article supplementary tables"))
  table_rows = []
  for table_key, filename in TABLE_FILES.items():
    table_path = BASE_DIR / "tables" / filename
    if table_path.exists():
      table_rows.append({
        "key": table_key,
        "file": filename,
        "sheets": "; ".join(excel_sheet_names(table_key)),
      })
  table_index = pd.DataFrame(table_rows)
  if table_index.empty:
    st.info(txt("Nenhuma tabela suplementar foi localizada.", "No supplementary table was found."))
  else:
    selected_table_key = st.selectbox(
      txt("Visualizar tabela suplementar", "View supplementary table"),
      table_index["key"].tolist(),
      key="public_supplementary_table_selector_v1",
    )
    sheet_names = excel_sheet_names(selected_table_key)
    selected_sheet_name = st.selectbox(
      txt("Aba", "Sheet"),
      sheet_names,
      key="public_supplementary_sheet_selector_v1",
    )
    selected_df = load_sheet(selected_table_key, selected_sheet_name)
    st.caption(f"{selected_table_key} / {selected_sheet_name}: {selected_df.shape[0]:,} rows × {selected_df.shape[1]:,} columns")
    show_table(selected_df, f"public_table_v1_{selected_table_key}_{selected_sheet_name}", height=560)
    csv_button(
      selected_df,
      f"{selected_table_key}_{selected_sheet_name}.csv".replace("/", "_"),
      txt("Baixar aba científica visível", "Download visible scientific sheet"),
    )
    workbook_path = BASE_DIR / "tables" / TABLE_FILES[selected_table_key]
    if workbook_path.exists():
      st.download_button(
        txt("Baixar workbook suplementar original", "Download original supplementary workbook"),
        data=workbook_path.read_bytes(),
        file_name=workbook_path.name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key=f"download_public_workbook_v1_{selected_table_key}",
        width="stretch",
      )

  st.markdown("### " + txt("Fontes científicas e uso no aplicativo", "Scientific sources and use in the application"))
  sources = pd.DataFrame([
    {"Dataset": "Taxonomic profiles", "Source": "Supplementary Table 1 and packaged Kaiju outputs", "Use": "Taxonomic profiles, diversity, sample coordinates and collection dates"},
    {"Dataset": "Differential abundance", "Source": "Supplementary Tables 2 and 5", "Use": "Taxon and KO/pathway descriptive and statistical comparisons"},
    {"Dataset": "Biogeochemical KO biomarkers", "Source": "Supplementary Tables 4, 5 and 8", "Use": "Carbon, methane, nitrogen, sulfur, photosynthesis, phosphorus and iron markers"},
    {"Dataset": "MAGs and genome annotations", "Source": "Supplementary Table 7, BV-BRC and packaged Annotation/MAG folders", "Use": "MAG quality, taxonomy, FASTA, GenBank/GBK, features and public downloads"},
    {"Dataset": "KEGG/KEMET modules", "Source": "Packaged reportKMC matrices and Supplementary Tables 8 and 14", "Use": "Module completeness, thematic biogeochemical subsets and interactive full matrices"},
    {"Dataset": "Functional annotations", "Source": "Supplementary Tables 6 and 8 and IMG/M/JGI identifiers", "Use": "KO, EC/enzyme and PFAM count and row-z-score heatmaps"},
    {"Dataset": "External iron-rich environments", "Source": "Supplementary Table 8 and confirmed public study/data links", "Use": "Environmental metadata, taxonomy, KO profiles and Amazonian-versus-external comparisons"},
    {"Dataset": "Biosynthetic gene clusters", "Source": "Complete antiSMASH result directories", "Use": "Read-only BGC report visualization and original result downloads"},
  ])
  show_table(sources, "methods_sources_table_public_v1", height=390)

  st.markdown("### " + txt("Critérios analíticos", "Analytical criteria"))
  st.markdown(txt(
    """
- Os heatmaps usam as matrizes reais empacotadas; células ausentes permanecem ausentes.
- Heatmaps em z-score são escalados por linha: $z=(x-\\bar{x})/s$.
- Os painéis ST8 preservam todas as 20 amostras das lagoas quando a comparação inclui o conjunto amazônico e mantêm as colunas externas selecionadas.
- Contrastes Amazônia–ambientes externos são descritivos: $\\log_2((\\bar{x}_{Amazônia}+1)/(\\bar{x}_{externo}+1))$; não são apresentados como testes inferenciais sem valores de p/q.
- Os estados KEGG/KEMET são mantidos como Complete, 1 block missing, Incomplete ou missing; filtros interativos não recalculam valores.
- Coordenadas, datas, identificadores, taxonomia e metadados são lidos das tabelas suplementares e fontes públicas registradas; nenhuma ausência é preenchida com informação inventada.
- As figuras estáticas e interativas exibem tabelas de rastreabilidade com os valores efetivamente plotados.
    """,
    """
- Heatmaps use the packaged real matrices; missing cells remain missing.
- Row-z-score heatmaps use $z=(x-\\bar{x})/s$.
- ST8 panels preserve all 20 lake samples whenever the Amazonian set is included and retain the selected external columns.
- Amazonia-versus-external contrasts are descriptive: $\\log_2((\\bar{x}_{Amazonia}+1)/(\\bar{x}_{external}+1))$; they are not presented as inferential tests without explicit p/q values.
- KEGG/KEMET states remain Complete, 1 block missing, Incomplete or missing; interactive filters do not recalculate values.
- Coordinates, dates, identifiers, taxonomy and metadata are read from supplementary tables and recorded public sources; no absence is filled with invented information.
- Static and interactive figures provide traceability tables containing the values actually plotted.
    """,
  ))

  st.markdown("### " + txt("Código e reprodutibilidade", "Code and reproducibility"))
  st.info(txt(
    "Para evitar duplicação e exposição de índices internos, a visualização, o download e as instruções de execução dos scripts estão disponíveis exclusivamente no módulo **Final figures & scripts**. Esta página mantém apenas a descrição científica dos métodos e das fontes.",
    "To avoid duplication and exposure of internal indexes, script preview, download and execution instructions are available exclusively under **Final figures & scripts**. This page retains only the scientific description of methods and sources.",
  ))

  st.markdown("### " + txt("Referências e serviços efetivamente utilizados", "References and services actually used"))
  references = pd.DataFrame([
    {"Reference / service": "Chen et al. — IMG/M", "Use in the app": "IMG/M/JGI annotation, identifiers and microbiome metadata", "DOI / official URL": "https://doi.org/10.1093/nar/gky901"},
    {"Reference / service": "Salazar et al.", "Use in the app": "Biogeochemical-cycle KO marker framework", "DOI / official URL": "https://doi.org/10.1016/j.cell.2019.10.014"},
    {"Reference / service": "Garber et al. — FeGenie", "Use in the app": "Iron-metabolism categories and interpretation", "DOI / official URL": "https://doi.org/10.3389/fmicb.2020.00037"},
    {"Reference / service": "Menzel et al. — Kaiju", "Use in the app": "Taxonomic classification of metagenomic CDS", "DOI / official URL": "https://doi.org/10.1038/ncomms11257"},
    {"Reference / service": "CheckM and GTDB-Tk", "Use in the app": "MAG quality and taxonomic classification", "DOI / official URL": "https://doi.org/10.1093/bioinformatics/btac672"},
    {"Reference / service": "KEGG", "Use in the app": "KO, pathway, enzyme and module interpretation and links", "DOI / official URL": "https://www.kegg.jp/"},
    {"Reference / service": "Palù et al. — KEMET", "Use in the app": "KEGG module evaluation and reportKMC-based completeness", "DOI / official URL": "https://doi.org/10.1016/j.csbj.2022.03.015"},
    {"Reference / service": "Blin et al. — antiSMASH", "Use in the app": "Biosynthetic gene-cluster prediction and report visualization", "DOI / official URL": "https://doi.org/10.1093/nar/gkad344"},
    {"Reference / service": "BV-BRC / PATRIC", "Use in the app": "Public MAG annotations and direct public Workspace downloads", "DOI / official URL": "https://www.bv-brc.org/"},
    {"Reference / service": "NCBI / PubMed", "Use in the app": "BioProject, BioSample, SRA and bibliographic links", "DOI / official URL": "https://www.ncbi.nlm.nih.gov/"},
    {"Reference / service": "Google Maps and Google Earth", "Use in the app": "Opening recorded geographic coordinates", "DOI / official URL": "https://www.google.com/maps; https://earth.google.com/"},
    {"Reference / service": "Plotly", "Use in the app": "Interactive scientific charts and heatmaps", "DOI / official URL": "https://plotly.com/python/"},
    {"Reference / service": "Streamlit", "Use in the app": "Interactive scientific web-application framework", "DOI / official URL": "https://streamlit.io/"},
    {"Reference / service": "Streamlit Community and Community Cloud", "Use in the app": "Public deployment, sharing and community-supported application ecosystem", "DOI / official URL": "https://streamlit.io/cloud; https://discuss.streamlit.io/"},
  ])
  show_table(references, "methods_references_public_v1", height=560)
'''
  source = _replace_function(
    source,
    "def references_methods_tab():",
    "\ndef contact_recipients_from_settings",
    references_function,
  )

  # A final typography override prevents later Streamlit/theme rules from
  # shrinking the interface again.
  typography = r'''st.markdown(
  """
  <style id="cangametag-public-release-v1-typography">
    html, body, [data-testid="stAppViewContainer"] { font-size: 19px !important; }
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] div { font-size: 1.10rem !important; line-height: 1.66 !important; }
    [data-testid="stCaptionContainer"], .stCaption { font-size: 1.02rem !important; line-height: 1.52 !important; }
    [data-baseweb="tab"] { font-size: 1.08rem !important; font-weight: 750 !important; }
    .stButton button, .stDownloadButton button, .stLinkButton a,
    [data-baseweb="select"] *, [data-baseweb="input"] input,
    textarea, label { font-size: 1.06rem !important; }
    [data-testid="stMetricLabel"] *, [data-testid="stMetricValue"] * { font-size: 1.08rem !important; }
    [data-testid="stDataFrame"] * { font-size: 1.00rem !important; }
    h1 { font-size: 2.72rem !important; }
    h2 { font-size: 2.18rem !important; }
    h3 { font-size: 1.78rem !important; }
    h4 { font-size: 1.48rem !important; }
    h5 { font-size: 1.28rem !important; }
  </style>
  """,
  unsafe_allow_html=True,
)
'''
  source = source.replace("page_header()\n", typography + "page_header()\n", 1)

  # Persist an explicit marker in the generated source for validation.
  marker_anchor = "def page_header():\n"
  if marker_anchor in source:
    source = source.replace(marker_anchor, MARKER + "\n\n\n" + marker_anchor, 1)
