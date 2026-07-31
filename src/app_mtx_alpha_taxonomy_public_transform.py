from __future__ import annotations

"""Final public fixes for MTX coverage, alpha statistics, and taxonomy overlap.

The transform preserves scientific values and changes only runtime robustness,
figure placement, and public presentation. It is intentionally loaded near the
end of the app transform chain.
"""

MARKER = "CANGAMETAG_MTX_ALPHA_TAXONOMY_PUBLIC_V1 = 1"


def _remove_public_call_containing(text: str, phrase: str) -> str:
  while phrase in text:
    position = text.find(phrase)
    candidates = [
      text.rfind("st.caption(txt(", 0, position),
      text.rfind("st.info(txt(", 0, position),
      text.rfind("st.markdown(txt(", 0, position),
      text.rfind("st.warning(txt(", 0, position),
    ]
    start = max(candidates)
    if start < 0:
      return text.replace(phrase, "")
    line_start = text.rfind("\n", 0, start) + 1
    cursor = text.find("\n", position)
    if cursor < 0:
      cursor = len(text)
    depth = text[start:cursor].count("(") - text[start:cursor].count(")")
    while cursor < len(text) and depth > 0:
      next_cursor = text.find("\n", cursor + 1)
      if next_cursor < 0:
        next_cursor = len(text)
      chunk = text[cursor:next_cursor]
      depth += chunk.count("(") - chunk.count(")")
      cursor = next_cursor
    text = text[:line_start] + text[cursor + (1 if cursor < len(text) else 0):]
  return text


if MARKER not in source:
  runtime_anchor = "page_handler = page_handlers.get(selected_page)"
  runtime_code = r'''
# Pandas categorical group columns cannot be filled with a new category directly.
# Patch the shared statistics function once, converting only the grouping column
# to an object/string representation before the original numerical tests run.
from src import article_inference_statistics as _article_inference_statistics_runtime

if not getattr(_article_inference_statistics_runtime, "_categorical_group_guard_installed", False):
  _original_group_comparison_tests_runtime = _article_inference_statistics_runtime.group_comparison_tests

  def _categorical_safe_group_comparison_tests(
    frame: pd.DataFrame,
    value_column: str,
    group_column: str,
    feature_column: str | None = None,
    *,
    minimum_group_size: int = 2,
  ) -> pd.DataFrame:
    safe_frame = frame.copy() if isinstance(frame, pd.DataFrame) else frame
    if isinstance(safe_frame, pd.DataFrame) and group_column in safe_frame.columns:
      group_values = safe_frame[group_column]
      if isinstance(group_values.dtype, pd.CategoricalDtype):
        group_values = group_values.astype(object)
      safe_frame[group_column] = group_values.where(pd.notna(group_values), "Unclassified").astype(str)
    return _original_group_comparison_tests_runtime(
      safe_frame,
      value_column,
      group_column,
      feature_column,
      minimum_group_size=minimum_group_size,
    )

  _article_inference_statistics_runtime.group_comparison_tests = _categorical_safe_group_comparison_tests
  _article_inference_statistics_runtime._categorical_group_guard_installed = True


def _article_overlap_broad_group(value: object) -> str:
  text = str(value or "")
  if "AMD" in text or "Akron" in text or "Richmond" in text:
    return "AMD systems"
  if "Lake Towuti" in text or "Lake Matano" in text or "Lake Superior" in text:
    return "Ferruginous lakes/sediments"
  if "Hydrothermal" in text:
    return "Hydrothermal Fe-rich mats"
  return "Other/unassigned"


def _taxonomy_article_overlap_panel() -> None:
  """Interactive article Venn and common-taxa heatmap from the final ST8 table."""
  tax, tax_path = _load_st8_csv("st8_taxonomy_summary_by_group.csv")
  if tax.empty:
    try:
      tax = load_sheet("table8", "Taxonomy_summary_by_group")
      tax_path = BASE_DIR / TABLE_FILES.get("table8", "tables/Supplementary_Table_8.xlsx")
    except Exception:
      tax = pd.DataFrame()
  required = {"taxonomy_level", "ST8_group", "data_layer", "matrix_column", "taxon", "count_or_abundance"}
  if tax.empty or not required.issubset(tax.columns):
    st.info(txt(
      "As tabelas de sobreposição taxonômica do artigo não estão disponíveis no pacote atual.",
      "The article taxonomic-overlap tables are not available in the current package.",
    ))
    return

  st.markdown("### " + txt(
    "Táxons compartilhados entre metagenomas — Venn e heatmap do artigo",
    "Taxa shared across metagenomes — article Venn and heatmap",
  ))
  level = st.radio(
    txt("Nível taxonômico da comparação", "Taxonomic rank for comparison"),
    ["Phylum", "Order", "Family"],
    horizontal=True,
    key="taxonomy_article_overlap_level_v1",
  )
  work = tax[
    tax["taxonomy_level"].astype(str).eq(level)
    & tax["data_layer"].astype(str).str.casefold().eq("metagenomics")
  ].copy()
  work["count_or_abundance"] = pd.to_numeric(work["count_or_abundance"], errors="coerce").fillna(0.0)
  work = work[work["count_or_abundance"] > 0].copy()
  work["article_environment_group"] = work["ST8_group"].map(_article_overlap_broad_group)
  article_groups = ["AMD systems", "Ferruginous lakes/sediments", "Hydrothermal Fe-rich mats"]
  work = work[work["article_environment_group"].isin(article_groups)].copy()
  if work.empty:
    st.info(txt("Nenhum táxon positivo foi encontrado para esta seleção.", "No positive taxon was found for this selection."))
    return

  set_map = {
    group: set(work.loc[work["article_environment_group"].eq(group), "taxon"].dropna().astype(str))
    for group in article_groups
  }
  set_map = {name: values for name, values in set_map.items() if values}
  if len(set_map) < 2:
    st.info(txt("São necessários pelo menos dois grupos para o diagrama.", "At least two groups are required for the diagram."))
    return

  regions = venn_region_sets(set_map)
  figure_key = f"taxonomy_article_mgx_venn_{level}"
  fig = simple_venn_figure(
    set_map,
    txt(
      f"Sobreposição de {level} entre grupos metagenômicos do artigo",
      f"{level} overlap among article metagenomic groups",
    ),
  )
  if fig is not None:
    st.plotly_chart(fig, width="stretch", key=figure_key, config={"displaylogo": False})

  region_rows = []
  for region_key, region in regions.items():
    region_rows.append({
      "region_key": region_key,
      "region": region["label"],
      "description": region["description"],
      "compared_sets": "; ".join(region["sets"]),
      "n_taxa": len(region["members"]),
    })
  region_summary = pd.DataFrame(region_rows)
  common_taxa = sorted(set.intersection(*set_map.values()))
  common_table = pd.DataFrame({"taxonomy_level": level, "taxon_common_to_all_article_groups": common_taxa})

  if fig is not None:
    render_figure_audit_expander(
      fig,
      figure_key,
      input_table=work[["taxonomy_level", "ST8_group", "data_layer", "matrix_column", "taxon", "count_or_abundance"]],
      processed_table=work[["taxonomy_level", "article_environment_group", "matrix_column", "taxon", "count_or_abundance"]],
      output_table=region_summary,
      method="Presence defined by count_or_abundance > 0; Venn sets are AMD systems, ferruginous lakes/sediments and hydrothermal Fe-rich mats.",
      input_source="data/st8_taxonomy_summary_by_group.csv",
      script="scripts/generate_core_taxonomy_overlap_figure.py",
      instructions="python scripts/generate_core_taxonomy_overlap_figure.py",
    )

  if common_taxa:
    common_work = work[work["taxon"].astype(str).isin(common_taxa)].copy()
    abundance = common_work.pivot_table(
      index="taxon",
      columns="matrix_column",
      values="count_or_abundance",
      aggfunc="sum",
      fill_value=0.0,
    )
    abundance = abundance.loc[abundance.sum(axis=1).sort_values(ascending=False).index]
    zscore = abundance.astype(float)
    means = zscore.mean(axis=1)
    standard = zscore.std(axis=1, ddof=0).replace(0.0, np.nan)
    zscore = zscore.sub(means, axis=0).div(standard, axis=0).fillna(0.0)
    heatmap_fig = px.imshow(
      zscore,
      aspect="auto",
      color_continuous_scale="RdBu_r",
      color_continuous_midpoint=0,
      title=txt(
        f"{level} compartilhados pelos três grupos — todas as amostras metagenômicas",
        f"{level} shared by all three groups — all metagenomic samples",
      ),
      labels={"x": txt("Amostra metagenômica", "Metagenomic sample"), "y": level, "color": "Row z-score"},
    )
    heatmap_fig.update_layout(
      height=max(620, 28 * len(zscore) + 240),
      width=max(1500, 42 * len(zscore.columns) + 520),
      margin=dict(l=260, r=100, t=105, b=250),
      meta={"preserve_cell_geometry": True, "force_all_y_ticks": True, "no_synthetic_values": True},
    )
    heatmap_fig.update_xaxes(tickangle=-55, automargin=True)
    heatmap_fig.update_yaxes(automargin=True)
    render_plotly_downloadable(
      heatmap_fig,
      key=f"taxonomy_article_mgx_common_heatmap_{level}",
      basename=f"SupplementaryFigure31_{level}_common_taxa_metagenomic_heatmap",
      audit_input_table=common_work,
      audit_processed_table=zscore.reset_index(),
      audit_output_table=common_table,
      audit_method="Taxa present in all three article environmental groups; exact per-metagenome abundance followed by row z-score.",
      audit_input_source="data/st8_taxonomy_summary_by_group.csv",
      audit_script="scripts/figures/generate_s31_taxonomic_levels_revision3.py",
      audit_instructions="python scripts/figures/generate_s31_taxonomic_levels_revision3.py --base-dir . --article-root ARTICLE_ROOT",
    )
  else:
    st.info(txt(
      f"Nenhum {level.lower()} foi detectado simultaneamente nos três grupos metagenômicos do artigo.",
      f"No {level.lower()} was detected simultaneously in all three article metagenomic groups.",
    ))

  with st.expander(txt("Táxons compartilhados e regiões do Venn", "Shared taxa and Venn regions"), expanded=False):
    show_table(common_table, f"taxonomy_article_common_{level}", height=320)
    show_table(region_summary, f"taxonomy_article_regions_{level}", height=320)
    csv_button(common_table, f"taxonomy_article_common_{level}.csv", txt("Baixar táxons compartilhados", "Download shared taxa"))
'''
  if runtime_anchor not in source:
    raise RuntimeError("Could not install MTX/alpha/taxonomy runtime layer")
  source = source.replace(runtime_anchor, runtime_code + "\n\n" + runtime_anchor, 1)

  taxonomy_anchor = '  st.markdown("### " + txt("Visualização taxonômica interativa", "Interactive taxonomic visualization"))'
  if taxonomy_anchor not in source:
    raise RuntimeError("Could not locate the active Taxonomy visualization anchor")
  source = source.replace(
    taxonomy_anchor,
    "  _taxonomy_article_overlap_panel()\n\n" + taxonomy_anchor,
    1,
  )

  old_caption = '''    st.caption(txt(
      f"Composição exibida: {len(pair_lakes)}/20 amostras das lagoas + {len(pair_external)} colunas externas; {len(cols)} colunas no total.",
      f"Displayed composition: {len(pair_lakes)}/20 lake samples + {len(pair_external)} external columns; {len(cols)} columns in total.",
    ))'''
  new_caption = '''    if pair_lakes:
      st.caption(txt(
        f"Composição exibida: {len(pair_lakes)}/20 amostras das lagoas + {len(pair_external)} colunas externas; {len(cols)} colunas no total.",
        f"Displayed composition: {len(pair_lakes)}/20 lake samples + {len(pair_external)} external columns; {len(cols)} columns in total.",
      ))
    else:
      is_mtx_scope = "metatranscript" in (scope_name_pt + " " + scope_name_en).casefold()
      if is_mtx_scope:
        st.caption(txt(
          f"Composição exibida: {len(pair_external)}/{len(pair_external)} amostras de metatranscriptoma; todos os {len(df)} KOs/marcadores estão selecionados por padrão.",
          f"Displayed composition: {len(pair_external)}/{len(pair_external)} metatranscriptome samples; all {len(df)} KOs/markers are selected by default.",
        ))
      else:
        st.caption(txt(
          f"Composição exibida: {len(pair_external)} colunas externas; {len(cols)} colunas no total.",
          f"Displayed composition: {len(pair_external)} external columns; {len(cols)} columns in total.",
        ))'''
  if old_caption not in source:
    raise RuntimeError("Could not replace the ST8 composition caption")
  source = source.replace(old_caption, new_caption, 1)

  mtx_anchor = '''  render_pair(
    "2B. Lagoas amazônicas + todos os ambientes externos",'''
  mtx_section = '''  mtx_meta = meta[
    meta.get("data_layer", pd.Series("", index=meta.index)).astype(str).str.casefold().eq("metatranscriptomics")
  ].copy() if not meta.empty else pd.DataFrame()
  mtx_matrix_fields = [
    field for field in ["ST8_matrix_column", "matrix_column_all_KO", "matrix_column_iron_KO", "matrix_column_selected"]
    if field in mtx_meta.columns
  ]
  mtx_cols = []
  for _, mtx_row in mtx_meta.iterrows():
    for field in mtx_matrix_fields:
      candidate = str(mtx_row.get(field, "")).strip()
      if candidate in numeric_cols and candidate in df.columns:
        mtx_cols.append(candidate)
        break
  mtx_cols = list(dict.fromkeys(mtx_cols))
  if mtx_cols:
    with st.expander(
      txt("Metatranscriptomas — estudos e identificadores", "Metatranscriptomes — studies and identifiers"),
      expanded=True,
    ):
      mtx_show_columns = [
        column for column in [
          "sample_id_created_this_study", "taxon_oid", "ST8_matrix_column", "Study Name",
          "Genome Name / Sample Name", "ST8_group", "data_layer", "NCBI Bioproject Accession", "SRA Run",
        ] if column in mtx_meta.columns
      ]
      show_table(mtx_meta[mtx_show_columns], f"{base_key}_all_mtx_metadata", height=420)
      csv_button(mtx_meta[mtx_show_columns], f"{base_key}_all_12_metatranscriptomes_metadata.csv", txt("Baixar metadados dos metatranscriptomas", "Download metatranscriptome metadata"))
    render_pair(
      "Metatranscriptomas — todas as amostras, estudos e identificadores",
      "Metatranscriptomes — all samples, studies and identifiers",
      mtx_cols,
      "metatranscriptomics_all_samples",
      f"Todas as {len(mtx_cols)} amostras de metatranscriptoma presentes na ST8 são exibidas com a matriz completa de {len(df)} KOs/marcadores por padrão.",
      f"All {len(mtx_cols)} metatranscriptome samples present in ST8 are displayed with the complete {len(df)}-KO/marker matrix by default.",
    )

  render_pair(
    "2B. Lagoas amazônicas + todos os ambientes externos",'''
  if mtx_anchor not in source:
    raise RuntimeError("Could not locate the ST8 2B anchor for the complete MTX panel")
  source = source.replace(mtx_anchor, mtx_section, 1)

  for phrase in [
    "O visualizador interativo incorpora o mesmo SVG corrigido exibido como figura estática.",
    "The interactive viewer embeds the same corrected SVG displayed as the static figure.",
    "Integridade confirmada: 189/189 KOs",
    "Integrity confirmed: 189/189 KOs",
  ]:
    source = _remove_public_call_containing(source, phrase)

  replacements = {
    "Tabela taxonômica completa para auditoria e download": "Tabela taxonômica completa e download",
    "Complete taxonomic table for audit and download": "Complete taxonomic table and download",
    "Auditoria das amostras": "Amostras incluídas",
    "Sample audit": "Included samples",
  }
  for old, new in replacements.items():
    source = source.replace(old, new)

  source += f"\n\n{MARKER}\n"
