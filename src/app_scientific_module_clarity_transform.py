from __future__ import annotations


MARKER = "CANGAMETAG_SCIENTIFIC_CLARITY_REVISION = 1"

if MARKER not in source:
  mags_start = source.find("def mags_tab():\n")
  if mags_start >= 0:
    source = source[:mags_start] + MARKER + "\n\n\n" + source[mags_start:]

  old_intro = '''  st.markdown(txt(
    "Esta é a seção principal da base: ela conecta os MAGs/bins do artigo às classificações taxonômicas, métricas de qualidade, FASTA, GenBank/GBK e demais arquivos de anotação. Os conjuntos enviados para `Annotation/MAG1`, `Annotation/MAG2`, ... são disponibilizados pelo app em modo somente leitura para download no computador do usuário.",
    "This is the main database section: it connects article MAGs/bins to taxonomic classifications, quality metrics, FASTA, GenBank/GBK and other annotation files. Sets uploaded to `Annotation/MAG1`, `Annotation/MAG2`, ... are offered by the read-only app for download to the user's computer."
  ))'''
  new_intro = '''  st.markdown(txt(
    "Este módulo apresenta os MAGs reconstruídos a partir dos metagenomas de sedimentos das lagoas lateríticas amazônicas analisadas neste estudo. Esses MAGs são dados originais e inéditos do trabalho, recuperados diretamente das amostras das lagoas, e não genomas externos adicionados apenas para comparação. A seção conecta cada MAG/bin às classificações taxonômicas, métricas de qualidade, FASTA, GenBank/GBK e demais arquivos de anotação. Os arquivos públicos podem ser baixados diretamente do BV-BRC para o computador do visitante; arquivos versionados em `Annotation/MAG1`, `Annotation/MAG2`, ... permanecem como fallback somente leitura.",
    "This module presents MAGs reconstructed from sediment metagenomes collected in the Amazonian lateritic lakes analyzed in this study. These MAGs are original, previously unpublished study data recovered directly from the lake samples, rather than external genomes added only for comparison. The section connects each MAG/bin to taxonomic classifications, quality metrics, FASTA, GenBank/GBK and other annotation files. Public files can be downloaded directly from BV-BRC to the visitor's computer; files versioned under `Annotation/MAG1`, `Annotation/MAG2`, ... remain available as a read-only fallback."
  ))'''
  if old_intro in source:
    source = source.replace(old_intro, new_intro, 1)

  source = source.replace(
    'q = st.text_input(txt("Buscar MAG, classificação ou anotação", "Search MAG, classification or annotation"), "", key="mags_q")',
    'q = st.text_input(txt("Buscar MAG das lagoas, classificação ou anotação", "Search lake MAG, classification or annotation"), "", key="mags_q")',
    1,
  )
  source = source.replace(
    '  st.markdown("#### " + txt("MAGs identificados no artigo", "Article MAGs"))',
    '  st.markdown("### " + txt("MAGs do artigo", "Article MAGs"))',
    1,
  )

  old_mag_options = '  mag_options = sort_mags_table(bins)["MAG"].astype(str).tolist() if "MAG" in bins.columns else []'
  new_mag_options = '''  mag_options = sort_mags_table(bins)["MAG"].astype(str).tolist() if "MAG" in bins.columns else []
  mag_options = [mag for mag in mag_options if mag_number(mag) != 247]'''
  if old_mag_options in source:
    source = source.replace(old_mag_options, new_mag_options, 1)

  inventory_start = source.find("def _bvbrc_public_workspace_inventory(")
  inventory_end = source.find("\n\n@st.cache_data(ttl=240", inventory_start)
  if inventory_start >= 0 and inventory_end >= 0:
    inventory_block = source[inventory_start:inventory_end]
    inventory_block = inventory_block.replace(
      '      if number is None or not name.lower().startswith(("mag", "bin")):',
      '      if number is None or number == 247 or not name.lower().startswith(("mag", "bin")):',
      1,
    )
    source = source[:inventory_start] + inventory_block + source[inventory_end:]

  record_start = source.find("def _bvbrc_public_record_for_mag(")
  record_end = source.find("\n\ndef bvbrc_cli_sync_panel", record_start)
  if record_start >= 0 and record_end >= 0:
    record_block = source[record_start:record_end]
    old_record_mag = '  mag_id = canonical_mag_id(selected_mag)\n  matched = inventory.loc[inventory["MAG"].astype(str) == mag_id]'
    new_record_mag = '''  mag_id = canonical_mag_id(selected_mag)
  if mag_number(mag_id) == 247:
    return None, "MAG247 is not part of the article MAG collection"
  matched = inventory.loc[inventory["MAG"].astype(str) == mag_id]'''
    if old_record_mag in record_block:
      record_block = record_block.replace(old_record_mag, new_record_mag, 1)
    source = source[:record_start] + record_block + source[record_end:]

  panel_start = source.find("def bvbrc_cli_sync_panel(mag_options: list[str]):\n")
  panel_end = source.find("\n\ndef repository_mag_download_panel(", panel_start)
  if panel_start >= 0 and panel_end >= 0:
    panel = source[panel_start:panel_end]
    panel = panel.replace("  st.info(txt(\n", "  st.markdown(txt(\n", 1)
    old_inventory_call = '''  inventory, error = _bvbrc_public_workspace_inventory(BVBRC_DEFAULT_WORKSPACE_BASE)
  if inventory.empty:'''
    new_inventory_call = '''  inventory, error = _bvbrc_public_workspace_inventory(BVBRC_DEFAULT_WORKSPACE_BASE)
  article_mag_ids = {
    canonical_mag_id(value)
    for value in mag_options
    if mag_number(value) not in {None, 247}
  }
  if not inventory.empty:
    inventory = inventory.loc[inventory["MAG"].astype(str).ne("MAG247")].copy()
    if article_mag_ids:
      inventory = inventory.loc[inventory["MAG"].astype(str).isin(article_mag_ids)].copy()
  if inventory.empty:'''
    if old_inventory_call in panel:
      panel = panel.replace(old_inventory_call, new_inventory_call, 1)

    old_table = '''  visible = inventory.drop(columns=["size_bytes", "endpoint"], errors="ignore")
  show_table(visible, "bvbrc_public_mag_inventory", height=320)'''
    new_table = '''  visible = inventory.drop(columns=["size_bytes", "endpoint"], errors="ignore")
  st.markdown("##### " + txt(
    "MAGs do artigo disponíveis no BV-BRC",
    "Article MAGs available in BV-BRC",
  ))
  show_table(visible, "bvbrc_public_mag_inventory", height=320)'''
    if old_table in panel:
      panel = panel.replace(old_table, new_table, 1)

    old_caption = '''  st.caption(txt(
    "Selecione um MAG específico abaixo. O botão de download será criado a partir de uma URL temporária do próprio BV-BRC, sem armazenar o arquivo no Streamlit.",
    "Select a specific MAG below. Its download button is created from a temporary BV-BRC URL without storing the file in Streamlit.",
  ))'''
    new_caption = '''  st.caption(txt(
    "A tabela contém somente os MAGs do artigo recuperados das lagoas. MAG247 e quaisquer outros registros externos ao conjunto do artigo são excluídos deste módulo.",
    "The table contains only article MAGs recovered from the lakes. MAG247 and any other records outside the article collection are excluded from this module.",
  ))

  direct_mag_options = visible["MAG"].dropna().astype(str).tolist()
  if direct_mag_options:
    st.markdown("##### " + txt(
      "Download direto de um MAG do artigo",
      "Direct download of an article MAG",
    ))
    selected_direct_mag = st.selectbox(
      txt("Selecione o MAG para baixar", "Select the MAG to download"),
      direct_mag_options,
      key="bvbrc_public_direct_article_mag_selector_v3",
    )
    selected_rows = inventory.loc[inventory["MAG"].astype(str) == selected_direct_mag]
    if not selected_rows.empty:
      selected_record = selected_rows.iloc[0].to_dict()
      remote_path = str(selected_record.get("remote_path", ""))
      object_type = str(selected_record.get("object_type", "")).casefold()
      direct_url = ""
      direct_error = ""
      direct_file_count = 0
      direct_total_size = 0
      with st.spinner(txt(
        "Gerando o link público temporário no BV-BRC...",
        "Generating the temporary public BV-BRC link...",
      )):
        if "director" in object_type or "folder" in object_type:
          direct_url, direct_file_count, direct_total_size, direct_error = _bvbrc_public_archive_url(
            remote_path,
            selected_direct_mag,
          )
        else:
          direct_url, direct_error = _bvbrc_public_file_url(remote_path)
      if direct_url:
        st.link_button(
          txt(
            f"Baixar {selected_direct_mag} diretamente do BV-BRC",
            f"Download {selected_direct_mag} directly from BV-BRC",
          ),
          direct_url,
          type="primary",
          width="stretch",
        )
        direct_details = []
        if direct_file_count:
          direct_details.append(txt(
            f"{direct_file_count} arquivos",
            f"{direct_file_count} files",
          ))
        if direct_total_size:
          direct_details.append(_repository_mag_size_text(direct_total_size))
        if direct_details:
          st.caption(" | ".join(direct_details))
        st.caption(txt(
          "O arquivo é enviado pelo BV-BRC diretamente ao navegador. O destino é controlado pela configuração de Downloads/Salvar como do visitante.",
          "BV-BRC sends the file directly to the browser. The destination is controlled by the visitor's Downloads/Save As settings.",
        ))
      else:
        st.warning(txt(
          "O MAG foi localizado, mas o BV-BRC não forneceu uma URL temporária de download neste momento.",
          "The MAG was found, but BV-BRC did not provide a temporary download URL at this time.",
        ))
        if direct_error:
          st.caption(str(direct_error)[:1500])'''
    if old_caption in panel:
      panel = panel.replace(old_caption, new_caption, 1)
    source = source[:panel_start] + panel + source[panel_end:]

  map_function_start = source.find("def show_high_quality_sample_map(")
  map_function_end = source.find("\ndef _clean_link_text", map_function_start)
  coordinate_start = source.find(
    "  coordinate_table = valid[coordinate_cols].drop_duplicates().copy()\n",
    map_function_start,
    map_function_end,
  )
  coordinate_end = source.find("\n  center_lat =", coordinate_start, map_function_end)
  if coordinate_start >= 0 and coordinate_end >= 0:
    coordinate_replacement = r'''  coordinate_table = valid[coordinate_cols].drop_duplicates().copy()
  coordinate_caption = txt(
    "Cada linha mantém a coordenada original disponível. Os links abrem Google Maps/Earth e a fonte ambiental ou IMG/JGI quando ela está registrada nos dados.",
    "Each row keeps the available original coordinate. Links open Google Maps/Earth and the environmental or IMG/JGI source when it is recorded in the data.",
  )
  source_column = "Map source" if "Map source" in coordinate_table.columns else None
  if source_column:
    source_values = coordinate_table[source_column].fillna("").astype(str)
    study_coordinates = coordinate_table.loc[
      source_values.str.contains("Study area and sampling design", case=False, na=False)
    ].copy()
    external_coordinates = coordinate_table.loc[
      source_values.str.contains("Supplementary Table 8", case=False, na=False)
    ].copy()
    other_coordinates = coordinate_table.loc[
      ~coordinate_table.index.isin(study_coordinates.index)
      & ~coordinate_table.index.isin(external_coordinates.index)
    ].copy()
  else:
    study_coordinates = pd.DataFrame(columns=coordinate_table.columns)
    external_coordinates = pd.DataFrame(columns=coordinate_table.columns)
    other_coordinates = coordinate_table.copy()

  def _render_coordinate_source_table(
    frame: pd.DataFrame,
    title_pt: str,
    title_en: str,
    suffix: str,
  ) -> None:
    if frame is None or frame.empty:
      return
    display_frame = frame.drop(columns=["Map source"], errors="ignore").reset_index(drop=True)
    st.markdown("##### " + txt(title_pt, title_en))
    st.caption(coordinate_caption)
    show_table(display_frame, f"{key}_{suffix}", height=420)
    csv_button(
      display_frame,
      f"{key}_{suffix}.csv",
      txt("Baixar coordenadas e links", "Download coordinates and links"),
    )

  if overview_mode:
    st.markdown(
      '''<div style="margin:1rem 0 .45rem 0;padding:.78rem 1rem;border-radius:14px;
      background:#FFF7D6;border-left:7px solid #D97706;border-top:1px solid #F2C94C;
      border-right:1px solid #F2C94C;border-bottom:1px solid #F2C94C;
      font-size:1.08rem;font-weight:900;color:#7C2D12;">★ Coordinate source tables</div>''',
      unsafe_allow_html=True,
    )
    _render_coordinate_source_table(
      study_coordinates,
      "Área do estudo e amostras das lagoas — Brasil",
      "Study area and lake samples — Brazil",
      "study_lake_coordinate_table",
    )
    _render_coordinate_source_table(
      external_coordinates,
      "Supplementary Table 8 — ambientes externos ricos em ferro",
      "Supplementary Table 8 — external iron-rich environments",
      "supplementary_table_8_external_iron_rich_coordinates",
    )
    _render_coordinate_source_table(
      other_coordinates,
      "Outras coordenadas registradas",
      "Other recorded coordinates",
      "other_coordinate_sources",
    )
    if not external_coordinates.empty:
      render_iron_environment_characteristics(
        external_coordinates,
        key=f"{key}_iron_environment_characteristics",
      )
  else:
    with st.expander(
      txt(
        "Coordenadas, pontos das lagoas e links de referência ambiental",
        "Coordinates, lake points and environment reference links",
      ),
      expanded=True,
    ):
      _render_coordinate_source_table(
        study_coordinates,
        "Área do estudo e amostras das lagoas — Brasil",
        "Study area and lake samples — Brazil",
        "study_lake_coordinate_table",
      )
      _render_coordinate_source_table(
        external_coordinates,
        "Supplementary Table 8 — ambientes externos ricos em ferro",
        "Supplementary Table 8 — external iron-rich environments",
        "supplementary_table_8_external_iron_rich_coordinates",
      )
      _render_coordinate_source_table(
        other_coordinates,
        "Outras coordenadas registradas",
        "Other recorded coordinates",
        "other_coordinate_sources",
      )
'''
    source = source[:coordinate_start] + coordinate_replacement + source[coordinate_end:]

  old_kegg_loop = '''  for fig_name, fig_caption, status_csv, full_status_csv, panel_key in kegg_figures:
    _display_kegg_completeness_panel(figure_dir / fig_name, fig_caption, status_csv, panel_key, full_status_csv=full_status_csv)'''
  new_kegg_loop = '''  kegg_supplementary_context = {
    "kegg_mags": ("37", txt(
      "MAGs recuperados das lagoas",
      "MAGs recovered from the lakes",
    )),
    "kegg_lagoon_metagenomes": ("38", txt(
      "metagenomas das lagoas",
      "lake metagenomes",
    )),
    "kegg_external_iron_rich_environmental_group": ("40", txt(
      "metagenomas de ambientes externos ricos em ferro",
      "external iron-rich metagenomes",
    )),
    "kegg_combined_lagoon_external_original": ("67", txt(
      "lagoas e ambientes externos ricos em ferro",
      "lakes and external iron-rich environments",
    )),
    "kegg_combined_lagoon_external_environmental_group": ("67", txt(
      "lagoas e ambientes externos agrupados por contexto ambiental",
      "lakes and external environments grouped by environmental context",
    )),
  }
  for fig_name, fig_caption, status_csv, full_status_csv, panel_key in kegg_figures:
    supplementary_number, biological_scope = kegg_supplementary_context.get(
      panel_key,
      ("", txt("amostras analisadas", "analyzed samples")),
    )
    if supplementary_number:
      st.markdown("### " + txt(
        f"Figura Suplementar {supplementary_number}",
        f"Supplementary Figure {supplementary_number}",
      ))
      st.info(txt(
        f"Este painel é mostrado porque esses módulos estão destacados na Figura Suplementar {supplementary_number}. Eles representam módulos de vias associadas aos ciclos biogeoquímicos — incluindo carbono, metano, nitrogênio, fósforo, enxofre, fotossíntese oxigênica e metabolismo do ferro — no conjunto de {biological_scope}.",
        f"This panel is shown because these modules are highlighted in Supplementary Figure {supplementary_number}. They represent pathway modules associated with biogeochemical cycles — including carbon, methane, nitrogen, phosphorus, sulfur, oxygenic photosynthesis and iron metabolism — in the {biological_scope} dataset.",
      ))
    figure_path = figure_dir / fig_name
    if panel_key == "kegg_lagoon_metagenomes":
      canonical_page_one = (
        BASE_DIR
        / "outputs"
        / "final_publication_figures"
        / "SupplementaryFigure38_metagenome_KEGG_module_completeness_heatmap_P001.png"
      )
      if canonical_page_one.exists():
        figure_path = canonical_page_one
    _display_kegg_completeness_panel(
      figure_path,
      fig_caption,
      status_csv,
      panel_key,
      full_status_csv=full_status_csv,
    )'''
  if old_kegg_loop in source:
    source = source.replace(old_kegg_loop, new_kegg_loop, 1)
