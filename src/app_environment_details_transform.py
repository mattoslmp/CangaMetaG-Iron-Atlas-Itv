from __future__ import annotations


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


# Keep both interactive map panels open when the page first loads.
source = source.replace(
  '  with st.expander(high_resolution_title, expanded=False):\n',
  '  with st.expander(high_resolution_title, expanded=True):\n',
)
source = source.replace(
  '''      expanded=False,
    ):
      show_leaflet_satellite_map(
        interactive_study_meta,''',
  '''      expanded=True,
    ):
      show_leaflet_satellite_map(
        interactive_study_meta,''',
  1,
)


helper_marker = 'def show_high_quality_sample_map('
helper_code = r'''def _clean_environment_detail_values(frame: pd.DataFrame, columns: list[str], limit: int = 8) -> list[str]:
  values: list[str] = []
  for column in columns:
    if column not in frame.columns:
      continue
    for value in frame[column].dropna().astype(str):
      clean = value.strip()
      if clean and clean.casefold() not in {"nan", "none", "na", "n/a", "<na>", "-"} and clean not in values:
        values.append(clean)
  return values[:limit]


def _pubmed_reference_for_environment(group_name: str, frame: pd.DataFrame) -> tuple[str, str]:
  searchable = " ".join(
    [str(group_name)]
    + _clean_environment_detail_values(
      frame,
      ["Study Name", "study_name", "Genome Name / Sample Name", "geographic_location", "ST8_group"],
      limit=12,
    )
  ).casefold()
  references = [
    (
      ("richmond", "iron mountain"),
      "Natural acidophilic biofilm communities reflect distinct organismal and functional organization",
      "18843299",
    ),
    (
      ("akron", "pennsylvania", "ohio", "coal mine"),
      "Depth-dependent geochemical and microbiological gradients in Fe(III) deposits resulting from coal mine-derived acid mine drainage",
      "24860562",
    ),
    (
      ("lake towuti", "towuti"),
      "Geomicrobiological Features of Ferruginous Sediments from Lake Towuti, Indonesia",
      "27446046",
    ),
    (
      ("lake matano", "matano"),
      "The methane cycle in ferruginous Lake Matano",
      "20854329",
    ),
    (
      ("lake superior", "superior"),
      "Aqueous Geochemical Controls on the Sestonic Microbial Community in Lakes Michigan and Superior",
      "36838469",
    ),
    (
      ("burr oak", "reservoir"),
      "Response of sediment microbial community structure in a freshwater reservoir to manipulations in oxygen availability",
      "22224595",
    ),
    (
      ("hydrothermal", "snakepit", "snake pit", "fe-rich mat"),
      "Microbial iron mats at the Mid-Atlantic Ridge and evidence that Zetaproteobacteria may be restricted to iron-oxidizing marine systems",
      "25760332",
    ),
  ]
  for tokens, title, pmid in references:
    if any(token in searchable for token in tokens):
      return title, f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"

  study_values = _clean_environment_detail_values(frame, ["Study Name", "study_name"], limit=1)
  query = study_values[0] if study_values else str(group_name)
  return (
    txt("Buscar literatura relacionada no PubMed", "Search related literature in PubMed"),
    "https://pubmed.ncbi.nlm.nih.gov/?term=" + quote_plus(query),
  )


def render_iron_environment_characteristics(frame: pd.DataFrame, key: str) -> None:
  if frame is None or frame.empty:
    return
  external = frame.copy()
  if "Map source" in external.columns:
    source_mask = external["Map source"].fillna("").astype(str).str.contains(
      "Supplementary Table 8", case=False, na=False
    )
    if source_mask.any():
      external = external.loc[source_mask].copy()
  if external.empty:
    return

  group_column = next(
    (
      column for column in [
        "ST8_short_group", "ST8_group", "dataset_group", "environment_feature",
        "Specific Ecosystem", "geographic_location",
      ]
      if column in external.columns
      and external[column].fillna("").astype(str).str.strip().ne("").any()
    ),
    None,
  )
  if group_column is None:
    return

  external["__environment_group__"] = external[group_column].fillna("").astype(str).str.strip()
  external = external.loc[
    external["__environment_group__"].ne("")
    & ~external["__environment_group__"].str.casefold().isin({"nan", "none", "na", "n/a"})
  ].copy()
  groups = sorted(external["__environment_group__"].drop_duplicates().tolist(), key=str.casefold)
  if not groups:
    return

  with st.expander(
    txt(
      "Características dos ambientes ricos em ferro selecionados e literatura",
      "Characteristics of the selected iron-rich environments and literature",
    ),
    expanded=False,
  ):
    st.caption(txt(
      "As descrições abaixo são montadas somente com os metadados registrados na Supplementary Table 8. Selecione um ambiente para ver sua localização, habitat, ecossistema, estudos, camadas ômicas e uma referência relacionada no PubMed.",
      "The descriptions below are assembled only from metadata recorded in Supplementary Table 8. Select an environment to view its location, habitat, ecosystem, studies, omics layers and a related PubMed reference.",
    ))
    selected = st.selectbox(
      txt("Ambiente em foco", "Environment in focus"),
      groups,
      key=f"{key}_selected_environment",
    )
    subset = external.loc[external["__environment_group__"].eq(selected)].copy()

    roles = _clean_environment_detail_values(subset, ["core_comparison_group"], limit=4)
    locations = _clean_environment_detail_values(
      subset, ["Geographic Location", "geographic_location", "Isolation Country", "isolation_country"], limit=8
    )
    habitats = _clean_environment_detail_values(subset, ["Habitat", "habitat"], limit=8)
    ecosystem_types = _clean_environment_detail_values(
      subset, ["Ecosystem", "Ecosystem Category", "Ecosystem Type", "Ecosystem Subtype"], limit=8
    )
    specific_ecosystems = _clean_environment_detail_values(
      subset, ["Specific Ecosystem", "environment_feature", "environment_feature2"], limit=8
    )
    isolations = _clean_environment_detail_values(subset, ["Isolation", "isolation"], limit=8)
    studies = _clean_environment_detail_values(subset, ["Study Name", "study_name"], limit=8)
    layers = _clean_environment_detail_values(subset, ["data_layer", "data_layer_abbrev"], limit=6)
    samples = _clean_environment_detail_values(
      subset, ["Genome Name / Sample Name", "sample_description", "sample_id", "ST8_matrix_column"], limit=10
    )
    bioprojects = _clean_environment_detail_values(subset, ["NCBI Bioproject Accession"], limit=8)
    biosamples = _clean_environment_detail_values(subset, ["NCBI Biosample Accession"], limit=8)
    sra_ids = _clean_environment_detail_values(subset, ["SRA ID", "SRA Run"], limit=8)

    st.markdown(f"#### {selected}")
    if roles:
      st.markdown("**" + txt("Papel no painel ST8:", "Role in the ST8 panel:") + "** " + "; ".join(roles))

    description_parts_pt = [
      f"O ambiente selecionado reúne **{len(subset)} registro(s) cartográfico(s)** da tabela-fonte."
    ]
    description_parts_en = [
      f"The selected environment contains **{len(subset)} mapped source record(s)**."
    ]
    if locations:
      description_parts_pt.append("Localização registrada: " + "; ".join(locations) + ".")
      description_parts_en.append("Recorded location: " + "; ".join(locations) + ".")
    if habitats:
      description_parts_pt.append("Habitat: " + "; ".join(habitats) + ".")
      description_parts_en.append("Habitat: " + "; ".join(habitats) + ".")
    if ecosystem_types:
      description_parts_pt.append("Classificação de ecossistema: " + "; ".join(ecosystem_types) + ".")
      description_parts_en.append("Ecosystem classification: " + "; ".join(ecosystem_types) + ".")
    if specific_ecosystems:
      description_parts_pt.append("Ecossistema específico: " + "; ".join(specific_ecosystems) + ".")
      description_parts_en.append("Specific ecosystem: " + "; ".join(specific_ecosystems) + ".")
    if isolations:
      description_parts_pt.append("Origem/isolamento registrado: " + "; ".join(isolations) + ".")
      description_parts_en.append("Recorded source/isolation: " + "; ".join(isolations) + ".")
    if layers:
      description_parts_pt.append("Camadas de dados: " + "; ".join(layers) + ".")
      description_parts_en.append("Data layers: " + "; ".join(layers) + ".")
    st.markdown(txt(" ".join(description_parts_pt), " ".join(description_parts_en)))

    if studies:
      st.markdown("**" + txt("Estudo(s) registrado(s)", "Recorded study/studies") + ":** " + "; ".join(studies))
    if samples:
      st.markdown("**" + txt("Amostras/entradas representadas", "Represented samples/entries") + ":** " + "; ".join(samples))
    identifiers = []
    if bioprojects:
      identifiers.append("BioProject: " + ", ".join(bioprojects))
    if biosamples:
      identifiers.append("BioSample: " + ", ".join(biosamples))
    if sra_ids:
      identifiers.append("SRA: " + ", ".join(sra_ids))
    if identifiers:
      st.markdown("**" + txt("Identificadores públicos", "Public identifiers") + ":** " + " · ".join(identifiers))

    reference_title, reference_url = _pubmed_reference_for_environment(selected, subset)
    st.markdown(
      "**" + txt("Literatura relacionada:", "Related literature:") + f"** [{reference_title}]({reference_url})"
    )


'''
source = replace_once(
  source,
  helper_marker,
  helper_code + helper_marker,
  "environment characteristic helpers",
)


metadata_columns_anchor = '''    "dataset_group", "sample_description", "environment_feature", "environment_biome",
    "environment_feature2", "geographic_location", "habitat", "isolation",
    "isolation_country", "collection_date_raw", "lat", "lon", "google_maps_url",
    "google_earth_url", "environment_reference_url", "img_jgi_url",
'''
metadata_columns_replacement = '''    "dataset_group", "ST8_group", "ST8_short_group", "core_comparison_group",
    "Study Name", "study_name", "Genome Name / Sample Name", "sample_description",
    "data_layer", "data_layer_abbrev", "Ecosystem", "Ecosystem Category",
    "Ecosystem Type", "Ecosystem Subtype", "Specific Ecosystem",
    "environment_feature", "environment_biome", "environment_feature2",
    "Geographic Location", "geographic_location", "Habitat", "habitat",
    "Isolation", "isolation", "Isolation Country", "isolation_country",
    "NCBI Bioproject Accession", "NCBI Biosample Accession", "SRA ID", "SRA Run",
    "sample_id_created_this_study", "ST8_matrix_column", "collection_date_raw",
    "lat", "lon", "google_maps_url", "google_earth_url",
    "environment_reference_url", "img_jgi_url",
'''
source = replace_once(
  source,
  metadata_columns_anchor,
  metadata_columns_replacement,
  "environment detail source columns",
)


map_table_anchor = '''    csv_button(
      coordinate_table,
      f"{key}_map_source_table.csv",
      txt("Baixar Map source table", "Download Map source table"),
    )
  else:
'''
map_table_replacement = '''    csv_button(
      coordinate_table,
      f"{key}_map_source_table.csv",
      txt("Baixar Map source table", "Download Map source table"),
    )
    render_iron_environment_characteristics(
      coordinate_table,
      key=f"{key}_iron_environment_characteristics",
    )
  else:
'''
source = replace_once(
  source,
  map_table_anchor,
  map_table_replacement,
  "environment characteristics below map source table",
)
