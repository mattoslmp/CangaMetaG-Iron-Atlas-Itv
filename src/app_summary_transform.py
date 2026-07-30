from __future__ import annotations


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


# Move the scientific summary immediately below the abstract and display it once.
summary_start_marker = '  markers = marker_table()\n'
summary_end_marker = '\n  if st.session_state.get("admin_authenticated", False):'
summary_start = source.find(summary_start_marker)
if summary_start < 0:
  raise RuntimeError("Could not locate the article study-summary block")
summary_end = source.find(summary_end_marker, summary_start)
if summary_end < 0:
  raise RuntimeError("Could not locate the end of the article study-summary block")
summary_block = source[summary_start:summary_end]
source = source[:summary_start] + source[summary_end:]


summary_data_anchor = '''  markers = marker_table()
  meta = taxonomy_samples_metadata()
  iron_meta = iron_rich_environment_metadata()
'''
summary_data_replacement = '''  markers = marker_table()
  meta = taxonomy_samples_metadata()
  iron_meta = iron_rich_environment_metadata()

  article_metagenome_count = int(
    meta["sample.id"].dropna().astype(str).nunique()
  ) if "sample.id" in meta.columns else int(len(meta))

  img_total_records = int(len(iron_meta))
  layer_values = iron_meta.get(
    "data_layer_abbrev",
    iron_meta.get("data_layer", pd.Series("", index=iron_meta.index)),
  ).fillna("").astype(str).str.strip().str.upper()
  img_metagenomes = int(layer_values.eq("MGX").sum())
  img_metatranscriptomes = int(layer_values.eq("MTX").sum())
  img_combined_assemblies = int(layer_values.eq("COMB").sum())
  img_study_count = int(
    iron_meta.get("study_name", pd.Series("", index=iron_meta.index))
    .fillna("").astype(str).str.strip().replace("", np.nan).dropna().nunique()
  )

  if "include_in_selected_ST8" in iron_meta.columns:
    selected_mask = (
      iron_meta["include_in_selected_ST8"].fillna(False).astype(str)
      .str.strip().str.casefold().isin({"true", "1", "yes", "y"})
    )
    selected_iron_meta = iron_meta.loc[selected_mask].copy()
  else:
    selected_iron_meta = iron_meta.copy()

  def _joined_unique(frame, columns, limit=6):
    values = []
    for column in columns:
      if column not in frame.columns:
        continue
      for value in frame[column].dropna().astype(str):
        clean = value.strip()
        if clean and clean.casefold() not in {"nan", "none", "na", "n/a"} and clean not in values:
          values.append(clean)
    shown = values[:limit]
    suffix = f"; +{len(values) - limit} more" if len(values) > limit else ""
    return "; ".join(shown) + suffix

  combined_frame = iron_meta.loc[layer_values.eq("COMB")].copy()
  combined_record_name = _joined_unique(
    combined_frame,
    ["Genome Name / Sample Name", "ST8_matrix_column", "sample_id"],
    limit=1,
  ) or "Lake Superior Sediments combined assembly"
  combined_study_name = _joined_unique(
    combined_frame,
    ["Study Name", "study_name"],
    limit=1,
  ) or "Lake Superior Sediments"

  environment_rows = []
  environment_group_col = (
    "ST8_short_group" if "ST8_short_group" in selected_iron_meta.columns
    else "environmental_group"
  )
  if not selected_iron_meta.empty and environment_group_col in selected_iron_meta.columns:
    for environment_name, environment_frame in selected_iron_meta.groupby(environment_group_col, dropna=False):
      role = _joined_unique(environment_frame, ["core_comparison_group"], limit=3) or "Curated ST8 group"
      reason_map = {
        "Iron-rich comparison": "Selected as a core iron-rich comparison group in Supplementary Table 8.",
        "Outgroup": "Selected as the curated outgroup defined in Supplementary Table 8.",
        "Control": "Selected as the curated control defined in Supplementary Table 8.",
      }
      environment_rows.append({
        "Environment": str(environment_name),
        "Selection role": role,
        "Why included": reason_map.get(role, "Included as a curated supporting group in Supplementary Table 8."),
        "IMG/M records": int(environment_frame["sample_id"].astype(str).nunique()) if "sample_id" in environment_frame.columns else int(len(environment_frame)),
        "Studies": int(environment_frame.get("study_name", pd.Series("", index=environment_frame.index)).replace("", np.nan).dropna().nunique()),
        "Data layers": _joined_unique(environment_frame, ["data_layer", "data_layer_abbrev"], limit=4),
        "Documented habitat/ecosystem": _joined_unique(environment_frame, ["Habitat", "Specific Ecosystem", "sample_type"], limit=5),
        "Locations represented": _joined_unique(environment_frame, ["Geographic Location", "Isolation Country"], limit=4),
      })
  environment_summary = pd.DataFrame(environment_rows)

  article_mag_table = load_sheet("table7", "bins-identificados")
  article_mag_records = int(len(article_mag_table))

  deposition_path = BASE_DIR / "outputs" / "kegg_modules" / "MAG_genome_quality_completeness_table.csv"
  try:
    mag_deposition = pd.read_csv(deposition_path) if deposition_path.exists() else pd.DataFrame()
  except Exception:
    mag_deposition = pd.DataFrame()

  highest_mag_label = "not available"
  highest_ena_alias = "not available"
  highest_ena_accession = "not available"
  if not mag_deposition.empty and "MAG" in mag_deposition.columns:
    mag_numbers = pd.to_numeric(
      mag_deposition["MAG"].astype(str).str.extract(r"(?i)MAG[._ -]?(\\d+)", expand=False),
      errors="coerce",
    )
    if mag_numbers.notna().any():
      highest_index = mag_numbers.idxmax()
      highest_mag_label = f"MAG{int(mag_numbers.loc[highest_index])}"
      if "ENA sample alias" in mag_deposition.columns:
        value = str(mag_deposition.loc[highest_index, "ENA sample alias"]).strip()
        if value and value.casefold() != "nan":
          highest_ena_alias = value
      if "ENA analysis accession" in mag_deposition.columns:
        value = str(mag_deposition.loc[highest_index, "ENA analysis accession"]).strip()
        if value and value.casefold() != "nan":
          highest_ena_accession = value
'''
summary_block = replace_once(
  summary_block,
  summary_data_anchor,
  summary_data_replacement,
  "IMG/M, co-assembly and ENA summary calculations",
)


columns_anchor = '  c1, c2 = st.columns([0.52, 0.48])\n'
columns_replacement = '''  st.markdown("### " + txt("Novidades e inovação", "News and Innovation"))

  st.markdown("#### " + txt(
    "Reconstrução de MAGs e depósito no ENA",
    "MAG reconstruction and ENA deposition",
  ))
  st.markdown(txt(
    f"A coleção curada do artigo contém **{article_mag_records} MAGs montados/reconstruídos**. A numeração original depositada alcança **{highest_mag_label}**, com o alias de amostra ENA **{highest_ena_alias}** e o acesso de análise ENA **{highest_ena_accession}**.",
    f"The curated article collection contains **{article_mag_records} assembled/reconstructed MAGs**. The original deposited numbering reaches **{highest_mag_label}**, with ENA sample alias **{highest_ena_alias}** and ENA analysis accession **{highest_ena_accession}**."
  ))

  st.markdown("#### " + txt(
    "Anotação funcional de metagenomas e MAGs",
    "Functional annotation of metagenomes and MAGs",
  ))
  st.markdown(txt(
    f"O atlas consolida camadas de anotação funcional para o conjunto completo do estudo — **{article_metagenome_count} metagenomas de sedimento** e **{article_mag_records} MAGs montados** — conectando anotações IMG/JGI, perfis KO, biomarcadores biogeoquímicos e de ferro, módulos KEGG/KEMET e anotações genômicas. A cobertura específica de cada matriz é mantida conforme a tabela-fonte; resultados ausentes não são preenchidos nem simulados.",
    f"The atlas consolidates functional-annotation layers for the complete study set — **{article_metagenome_count} sediment metagenomes** and **{article_mag_records} assembled MAGs** — linking IMG/JGI annotations, KO profiles, biogeochemical and iron biomarkers, KEGG/KEMET modules and genome annotations. Coverage in each individual matrix is preserved exactly as reported by its source table; missing results are neither filled nor simulated."
  ))

  st.markdown("#### " + txt(
    "Importância dos ciclos biogeoquímicos em lagoas ferruginosas",
    "Importance of biogeochemical cycles in ferruginous lakes",
  ))
  st.markdown(txt(
    "A integração dos marcadores e módulos de **carbono e metano, nitrogênio, enxofre, ferro, hidrogênio e fotossíntese** permite avaliar, no mesmo sistema, o potencial microbiano para conectar transformação de matéria orgânica, ciclagem de metano, nutrientes e reações de ferro nos sedimentos lateríticos amazônicos. Esses resultados revelam o **potencial metagenômico, genômico e funcional** das comunidades microbianas das lagoas **Amendoim, Violão, Três Irmãs e Três Irmãs Adjacent** para contribuir com processos interconectados relacionados aos ciclos do carbono e metano, nitrogênio, enxofre, ferro, hidrogênio e fotossíntese. Estudos futuros com metatranscriptômica, proteômica e medições biogeoquímicas diretas permitirão determinar quando esses genes e vias são expressos ativamente e quantificar sua contribuição para as taxas biogeoquímicas em escala de ecossistema.",
    "Integrating **carbon and methane, nitrogen, sulfur, iron, hydrogen and photosynthesis** markers and modules makes it possible to evaluate, within the same system, the microbial potential linking organic-matter transformation, methane cycling, nutrients and iron reactions in Amazonian lateritic sediments. These results reveal the **metagenomic, genomic, and functional potential** of the microbial communities inhabiting the **Amendoim, Violão, Três Irmãs, and Três Irmãs Adjacent lakes** to contribute to interconnected carbon, methane, nitrogen, sulfur, iron, hydrogen, and photosynthesis-related processes. Future metatranscriptomic, proteomic, and direct biogeochemical measurements will help determine when these genes and pathways are actively expressed and quantify their contribution to ecosystem-level biogeochemical rates."
  ))

  st.markdown("#### " + txt(
    "Artigo digital e rastreabilidade",
    "Digital article and traceability",
  ))
  st.markdown(txt(
    "Além do manuscrito e das figuras estáticas, a publicação é apresentada como um atlas digital rastreável que conecta figuras, tabelas-fonte, visualizações interativas, downloads, identificadores IMG/M e ENA, scripts e proveniência dos dados em uma única interface.",
    "Beyond the manuscript and static figures, the publication is presented as a traceable digital atlas connecting figures, source tables, interactive visualizations, downloads, IMG/M and ENA identifiers, scripts and data provenance in one interface."
  ))

  c1, c2 = st.columns([0.52, 0.48])
'''
summary_block = replace_once(
  summary_block,
  columns_anchor,
  columns_replacement,
  "News and Innovation heading",
)
summary_block = summary_block.replace(
  'st.markdown("#### " + txt("Atualização dos biomarcadores e rastreabilidade", "Biomarker update and traceability"))',
  'st.markdown("#### " + txt("Atualização de biomarcadores e rastreabilidade", "Biomarker update and traceability"))',
  1,
)
summary_block = summary_block.replace(
  'm5.metric(txt("Ambientes IMG/M", "IMG/M environments"), iron_meta["sample_id"].nunique() if not iron_meta.empty and "sample_id" in iron_meta.columns else len(iron_meta))',
  'm5.metric(txt("Registros IMG/M", "IMG/M records"), img_total_records)',
  1,
)
summary_block = summary_block.replace(
  'm6.metric(txt("MAGs", "MAGs"), len(load_sheet("table7", "bins-identificados")))',
  'm6.metric(txt("MAGs montados", "Assembled MAGs"), article_mag_records)',
  1,
)


img_source_anchor = '''    st.markdown(txt(
      "**IMG/M source:** os metadados dos ambientes ricos em ferro vêm da aba `Iron-rich-environment` da Supplementary Table 8, derivada do portal Integrated Microbial Genomes with Microbiome Samples mantido pelo JGI.",
      "**IMG/M source:** metadata for iron-rich environments come from the `Iron-rich-environment` sheet in Supplementary Table 8, derived from the Integrated Microbial Genomes with Microbiome Samples portal maintained by JGI."
    ))
'''
img_source_replacement = '''    st.markdown(txt(
      f"**Fonte IMG/M:** os metadados vêm da aba `Iron-rich-environment`/tabela curada da Supplementary Table 8, derivada do portal Integrated Microbial Genomes with Microbiome Samples mantido pelo JGI. O painel empacotado reúne **{img_total_records} registros IMG/M de {img_study_count} estudos**, incluindo **{img_metagenomes} metagenomas**, **{img_metatranscriptomes} metatranscriptomas** e **{img_combined_assemblies} montagem combinada (co-assembly)**.",
      f"**IMG/M source:** metadata come from the `Iron-rich-environment`/curated table in Supplementary Table 8, derived from the Integrated Microbial Genomes with Microbiome Samples portal maintained by JGI. The packaged panel contains **{img_total_records} IMG/M records from {img_study_count} studies**, including **{img_metagenomes} metagenomes**, **{img_metatranscriptomes} metatranscriptomes** and **{img_combined_assemblies} combined assembly (co-assembly)**."
    ))
    if img_combined_assemblies:
      st.info(txt(
        f"**O que é a montagem combinada (co-assembly)?** É o registro **{combined_record_name}**, vinculado ao estudo **{combined_study_name}**, no qual leituras de vários projetos/amostras relacionados foram reunidas antes da montagem para produzir uma reconstrução computacional integrada. Portanto, ela **não representa uma nova amostra biológica independente** e é contabilizada separadamente dos registros MGX e MTX.",
        f"**What is the combined assembly (co-assembly)?** It is the **{combined_record_name}** record associated with **{combined_study_name}**, in which reads from multiple related projects/samples were pooled before assembly to produce an integrated computational reconstruction. It therefore **does not represent an additional independent biological sample** and is counted separately from MGX and MTX records."
      ))
'''
summary_block = replace_once(
  summary_block,
  img_source_anchor,
  img_source_replacement,
  "expanded IMG/M and co-assembly explanation",
)


overview_table_anchor = '''    csv_button(meta, "article_sample_dates_coordinates.csv", txt("Baixar datas/coordenadas", "Download dates/coordinates"))
'''
overview_table_replacement = '''    csv_button(meta, "article_sample_dates_coordinates.csv", txt("Baixar datas/coordenadas", "Download dates/coordinates"))

  figure1_sampling_path = BASE_DIR / "outputs" / "final_publication_figures" / "Figure1_sampling_map.png"
  st.markdown("### " + txt("Área de estudo e desenho amostral", "Study area and sampling design"))
  if figure1_sampling_path.exists():
    st.image(str(figure1_sampling_path), width="stretch")
    st.caption(txt(
      "Área de estudo e desenho amostral. Localização das lagoas lateríticas amazônicas Amendoim, Violão, Três Irmãs e Três Irmãs Adjacent. O estudo inclui 20 metagenomas de sedimento, compreendendo 10 amostras do período seco e 10 do período chuvoso.",
      "Study area and sampling design. Location of the Amazonian lateritic lakes Amendoim, Violão, Três Irmãs and Três Irmãs Adjacent. The study includes 20 sediment metagenomes, comprising 10 dry-season and 10 rainy-season samples."
    ))
  else:
    st.warning(txt(
      "A Figura 1 do mapa amostral não foi encontrada no diretório canônico de figuras finais.",
      "Figure 1 sampling map was not found in the canonical final-figures directory."
    ))
'''
summary_block = replace_once(
  summary_block,
  overview_table_anchor,
  overview_table_replacement,
  "Article Atlas Figure 1",
)


summary_block += '''

  st.markdown("### " + txt(
    "Metagenômica do ferro — ambientes IMG/M selecionados",
    "Iron metagenomics — selected IMG/M environments",
  ))
  st.markdown(txt(
    f"A tabela abaixo nomeia os grupos ambientais exatamente como curados na Supplementary Table 8 e explica a seleção usando o papel registrado no próprio conjunto (`Iron-rich comparison`, `Outgroup` ou `Control`). Dos {img_total_records} registros IMG/M disponíveis, {len(selected_iron_meta)} integram o painel ST8 selecionado.",
    f"The table below names the environmental groups exactly as curated in Supplementary Table 8 and explains their selection using the role recorded in the dataset itself (`Iron-rich comparison`, `Outgroup` or `Control`). Of {img_total_records} available IMG/M records, {len(selected_iron_meta)} belong to the selected ST8 panel."
  ))
  if not environment_summary.empty:
    show_table(environment_summary, "overview_img_iron_environment_summary", height=420)
    csv_button(environment_summary, "IMG_M_iron_environment_selection_summary.csv", txt("Baixar resumo dos ambientes", "Download environment summary"))

  external_map_meta = load_external_environment_coordinates(BASE_DIR)
  if external_map_meta.empty:
    external_map_meta = figure11_environment_metadata()
  with st.expander(txt(
    "Mapa dos outros ambientes ricos em ferro",
    "Map of the other iron-rich environments",
  ), expanded=False):
    if external_map_meta.empty:
      st.info(txt(
        "Não há coordenadas externas disponíveis nos metadados empacotados.",
        "No external coordinates are available in the packaged metadata."
      ))
    else:
      show_high_quality_sample_map(external_map_meta, key="overview_other_iron_rich_environment_map_v1")
      st.markdown("###### " + txt("Tabela-fonte do mapa", "Map source table"))
      show_table(external_map_meta, "overview_other_iron_rich_environment_map_source", height=460)
      csv_button(
        external_map_meta,
        "other_iron_rich_environment_map_source.csv",
        txt("Baixar tabela-fonte", "Download source table"),
      )
'''


workflow_anchor = '  st.markdown("### " + txt("Workflow do atlas", "Atlas workflow"))'
source = replace_once(
  source,
  workflow_anchor,
  summary_block + "\n\n" + workflow_anchor,
  "move article innovation below abstract",
)


