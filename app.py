from __future__ import annotations

"""Streamlit entry point with explicit, non-invasive source layout updates.

The complete application remains in ``app_core.py``. This loader changes only
requested presentation details before compiling the original application. It
does not monkeypatch Streamlit and does not replace scientific calculations.
"""

from pathlib import Path


CORE_PATH = Path(__file__).with_name("app_core.py")
source = CORE_PATH.read_text(encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


# ---------------------------------------------------------------------------
# Rename the ST8 reference module with the requested public-facing title.
# ---------------------------------------------------------------------------
source = source.replace(
  'txt("Referências bibliográficas e links dos estudos ST8", "ST8 study references and links")',
  'txt("Metagenômica do ferro — fontes de dados, links e referências", "Iron Metagenomics — Data Source, Links & References")',
)
source = source.replace(
  'txt("Referências dos estudos ST8", "ST8 study references")',
  'txt("Metagenômica do ferro — fontes de dados, links e referências", "Iron Metagenomics — Data Source, Links & References")',
)


# ---------------------------------------------------------------------------
# Remove the empty bin-classification/ENA tab and blank terminal rows.
# The quality table containing real ENA accessions remains untouched.
# ---------------------------------------------------------------------------
source = source.replace(
  '    ("bin.classification", txt("Classificação taxonômica dos bins e acessos ENA", "Bin taxonomic classification and ENA accessions")),\n',
  '',
  1,
)
source = source.replace(
  'st.markdown("#### " + txt("Classificação taxonômica e acessos ENA dos MAGs", "MAG taxonomic classification and ENA accessions"))',
  'st.markdown("#### " + txt("Classificação taxonômica dos MAGs", "MAG taxonomic classification"))',
  1,
)
classification_load_anchor = '      df = load_mag_classification_sheet(sheet_name)\n'
classification_load_replacement = '''      df = load_mag_classification_sheet(sheet_name)
      if not df.empty:
        df = df.replace(r"^\\s*$", np.nan, regex=True).dropna(how="all").dropna(axis=1, how="all")
        row_text = df.fillna("").astype(str).agg(" ".join, axis=1).str.strip().str.casefold()
        df = df.loc[~row_text.isin({"bin taxonomic classification", "ena accessions"})].copy()
'''
source = replace_once(
  source,
  classification_load_anchor,
  classification_load_replacement,
  "empty MAG classification row removal",
)


# ---------------------------------------------------------------------------
# Render the Taxonomy sampling map exactly once after its metadata table.
# ---------------------------------------------------------------------------
taxonomy_anchor = '''    csv_button(meta, "taxonomy_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))

  st.markdown("### " + txt("Figuras taxonômicas finais usadas no artigo", "Final taxonomy figures used in the article"))'''

taxonomy_replacement = '''    csv_button(meta, "taxonomy_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))

  if {"lat", "lon"}.issubset(meta.columns):
    show_high_quality_sample_map(meta, key="taxonomy_sampling_map_after_metadata_v6")

  st.markdown("### " + txt("Figuras taxonômicas finais usadas no artigo", "Final taxonomy figures used in the article"))'''

source = replace_once(source, taxonomy_anchor, taxonomy_replacement, "Taxonomy sampling map")


# ---------------------------------------------------------------------------
# Move the study-summary block immediately below the article abstract.
# This removes the old lower-page copy, so the material is displayed once.
# ---------------------------------------------------------------------------
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


# Add exact IMG/M, environment and MAG/KEGG calculations to the moved block.
summary_data_anchor = '''  markers = marker_table()
  meta = taxonomy_samples_metadata()
  iron_meta = iron_rich_environment_metadata()
'''
summary_data_replacement = '''  markers = marker_table()
  meta = taxonomy_samples_metadata()
  iron_meta = iron_rich_environment_metadata()

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
  mag_status, _mag_score = load_module_matrices("MAGs")
  mag_label_table = mag_taxonomy_metadata()
  cycle_pattern = re.compile(
    r"carbon fixation|methan|nitrogen|nitrate|nitrite|ammonia|urea|"
    r"sulfur|sulfate|sulfide|thiosulfate|photosynth|iron|ferr|hydrogen",
    flags=re.IGNORECASE,
  )

  def _compact_modules(modules, limit=7):
    labels = [str(module).replace(" | ", " — ", 1).strip() for module in modules]
    if not labels:
      return "None at Complete/1 block missing status"
    visible = labels[:limit]
    if len(labels) > limit:
      visible.append(f"+{len(labels) - limit} more")
    return "; ".join(visible)

  mag_pathway_rows = []
  if not mag_status.empty and not mag_label_table.empty:
    module_names = pd.Index(mag_status.index.astype(str))
    target_modules = module_names[module_names.map(lambda value: bool(cycle_pattern.search(value)))]
    for _, mag_record in mag_label_table.iterrows():
      matrix_column = str(mag_record.get("Original matrix column", ""))
      mag_identifier = str(mag_record.get("MAG identifier", ""))
      taxon = str(mag_record.get("Full source taxonomic classification", "Unclassified"))
      if matrix_column in mag_status.columns:
        statuses = mag_status.loc[target_modules, matrix_column].fillna("").astype(str)
        complete_modules = statuses[statuses.eq("Complete")].index.tolist()
        near_modules = statuses[statuses.eq("1 block missing")].index.tolist()
      else:
        complete_modules = []
        near_modules = []
      importance = (
        f"Genome-resolved representative linking {taxon} to "
        f"{len(complete_modules)} complete and {len(near_modules)} one-block-missing "
        "targeted biogeochemical KEGG modules in the packaged matrix."
      )
      mag_pathway_rows.append({
        "MAG": mag_identifier,
        "Taxonomic assignment": taxon,
        "Importance in this atlas": importance,
        "Complete biogeochemical modules": _compact_modules(complete_modules),
        "Near-complete biogeochemical modules": _compact_modules(near_modules),
        "Source matrix column": matrix_column,
      })
  mag_pathway_summary = pd.DataFrame(mag_pathway_rows)
  mag_kegg_count = int(len(mag_pathway_summary))
'''
summary_block = replace_once(
  summary_block,
  summary_data_anchor,
  summary_data_replacement,
  "IMG/M and MAG summary calculations",
)


# Use the requested innovation title and expose the exact IMG/M counts.
summary_block = summary_block.replace(
  'st.markdown("#### " + txt("Atualização dos biomarcadores e rastreabilidade", "Biomarker update and traceability"))',
  'st.markdown("### " + txt("Novidades e inovação apresentadas pelo artigo: atualização de biomarcadores e rastreabilidade", "News and Innovation provided by the article: Biomarker update and traceability"))',
  1,
)
summary_block = summary_block.replace(
  'm5.metric(txt("Ambientes IMG/M", "IMG/M environments"), iron_meta["sample_id"].nunique() if not iron_meta.empty and "sample_id" in iron_meta.columns else len(iron_meta))',
  'm5.metric(txt("Registros IMG/M", "IMG/M records"), img_total_records)',
  1,
)
summary_block = summary_block.replace(
  'm6.metric(txt("MAGs", "MAGs"), len(load_sheet("table7", "bins-identificados")))',
  'm6.metric(txt("Registros de MAG", "MAG records"), article_mag_records)',
  1,
)

img_source_anchor = '''    st.markdown(txt(
      "**IMG/M source:** os metadados dos ambientes ricos em ferro vêm da aba `Iron-rich-environment` da Supplementary Table 8, derivada do portal Integrated Microbial Genomes with Microbiome Samples mantido pelo JGI.",
      "**IMG/M source:** metadata for iron-rich environments come from the `Iron-rich-environment` sheet in Supplementary Table 8, derived from the Integrated Microbial Genomes with Microbiome Samples portal maintained by JGI."
    ))
'''
img_source_replacement = '''    st.markdown(txt(
      f"**Fonte IMG/M:** os metadados dos ambientes ricos em ferro vêm da aba `Iron-rich-environment`/tabela curada da Supplementary Table 8, derivada do portal Integrated Microbial Genomes with Microbiome Samples mantido pelo JGI. O painel empacotado reúne **{img_total_records} registros IMG/M de {img_study_count} estudos**, incluindo **{img_metagenomes} metagenomas**, **{img_metatranscriptomes} metatranscriptomas** e **{img_combined_assemblies} assembly combinado**.",
      f"**IMG/M source:** metadata for iron-rich environments come from the `Iron-rich-environment`/curated metadata table in Supplementary Table 8, derived from the Integrated Microbial Genomes with Microbiome Samples portal maintained by JGI. The packaged panel contains **{img_total_records} IMG/M records from {img_study_count} studies**, including **{img_metagenomes} metagenomes**, **{img_metatranscriptomes} metatranscriptomes** and **{img_combined_assemblies} combined assembly**."
    ))
    st.markdown(txt(
      "**Inovação digital do artigo:** além do manuscrito e das figuras estáticas, esta publicação é apresentada como um atlas digital rastreável que conecta figuras, tabelas-fonte, visualizações interativas, downloads, identificadores de acesso, scripts e proveniência dos dados em uma única interface.",
      "**Digital-publication innovation:** beyond the manuscript and static figures, the publication is presented as a traceable digital atlas connecting figures, source tables, interactive visualizations, downloads, accession identifiers, scripts and data provenance in one interface."
    ))
'''
summary_block = replace_once(
  summary_block,
  img_source_anchor,
  img_source_replacement,
  "expanded IMG/M source and digital novelty text",
)


# Keep canonical Figure 1 immediately after the article sample table.
overview_table_anchor = '''    csv_button(meta, "article_sample_dates_coordinates.csv", txt("Baixar datas/coordenadas", "Download dates/coordinates"))
'''
overview_table_replacement = '''    csv_button(meta, "article_sample_dates_coordinates.csv", txt("Baixar datas/coordenadas", "Download dates/coordinates"))

  figure1_sampling_path = BASE_DIR / "outputs" / "final_publication_figures" / "Figure1_sampling_map.png"
  st.markdown("### " + txt("Área de estudo e desenho amostral", "Study area and sampling design"))
  if figure1_sampling_path.exists():
    st.image(str(figure1_sampling_path), width="stretch")
    st.caption(txt(
      "Área de estudo e desenho amostral. Localização das lagoas lateríticas amazônicas Amendoim, Violão, Três Irmãs e Três Irmãs Adjacent. O estudo inclui 20 metagenomas de sedimento, compreendendo 10 amostras do período seco e 10 do período chuvoso.",
      "Study area and sampling design. Location of the Amazonian lateritic lakes Amendoim, Violão, Três Irmãs and Três Irmãs Adjacent. The study includes 20 sediment metagenomes, comprising 10 dry-season and 10 rainy-season samples.",
    ))
  else:
    st.warning(txt(
      "A Figura 1 do mapa amostral não foi encontrada no diretório canônico de figuras finais.",
      "Figure 1 sampling map was not found in the canonical final-figures directory.",
    ))
'''
summary_block = replace_once(
  summary_block,
  overview_table_anchor,
  overview_table_replacement,
  "Article Atlas Figure 1",
)


# Add full-width, data-derived environment and MAG pathway tables.
summary_block += '''

  st.markdown("### " + txt(
    "Metagenômica do ferro — ambientes IMG/M selecionados",
    "Iron metagenomics — selected IMG/M environments",
  ))
  st.markdown(txt(
    f"A tabela abaixo nomeia os grupos ambientais exatamente como curados na Supplementary Table 8 e explica a seleção usando o papel registrado no próprio conjunto (`Iron-rich comparison`, `Outgroup` ou `Control`). Dos {img_total_records} registros IMG/M disponíveis, {len(selected_iron_meta)} integram o painel ST8 selecionado.",
    f"The table below names the environmental groups exactly as curated in Supplementary Table 8 and explains their selection using the role recorded in the dataset itself (`Iron-rich comparison`, `Outgroup` or `Control`). Of {img_total_records} available IMG/M records, {len(selected_iron_meta)} belong to the selected ST8 panel.",
  ))
  if not environment_summary.empty:
    show_table(environment_summary, "overview_img_iron_environment_summary", height=420)
    csv_button(environment_summary, "IMG_M_iron_environment_selection_summary.csv", txt("Baixar resumo dos ambientes", "Download environment summary"))

  st.markdown("### " + txt(
    "MAGs e vias metabólicas ligadas aos ciclos biogeoquímicos",
    "MAGs and metabolic pathways linked to biogeochemical cycles",
  ))
  st.markdown(txt(
    f"A planilha de qualidade contém **{article_mag_records} registros de MAG**. A matriz KEGG empacotada contém **{mag_kegg_count} MAGs com mapeamento de módulos**. Cada linha abaixo resume um MAG e mostra somente módulos relacionados a carbono, metano, nitrogênio, enxofre, fotossíntese, ferro ou hidrogênio classificados como `Complete` ou `1 block missing`; ausências permanecem explicitamente ausentes.",
    f"The quality workbook contains **{article_mag_records} MAG records**. The packaged KEGG matrix contains **{mag_kegg_count} MAGs with module mapping**. Each row below summarizes one MAG and reports only carbon-, methane-, nitrogen-, sulfur-, photosynthesis-, iron- or hydrogen-related modules classified as `Complete` or `1 block missing`; missing results remain explicitly missing.",
  ))
  if not mag_pathway_summary.empty:
    show_table(mag_pathway_summary, "overview_mag_biogeochemical_pathways", height=640)
    csv_button(mag_pathway_summary, "MAG_biogeochemical_KEGG_pathway_summary.csv", txt("Baixar resumo MAG–vias", "Download MAG–pathway summary"))
'''


workflow_anchor = '  st.markdown("### " + txt("Workflow do atlas", "Atlas workflow"))'
source = replace_once(
  source,
  workflow_anchor,
  summary_block + "\n\n" + workflow_anchor,
  "move article innovation below abstract",
)


# Fail before execution if any source transformation introduces invalid Python.
code = compile(source, str(CORE_PATH), "exec")
exec(code, globals(), globals())
