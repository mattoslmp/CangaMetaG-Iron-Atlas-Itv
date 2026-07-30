from __future__ import annotations


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


# Add an MTX-only KO panel to every ST8 matrix that actually contains MTX
# columns. The all-KO and iron-KO pages call the same rendering function.
ko_matrix_anchor = '''  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  external_cols = [c for c in numeric_cols if c not in lake_cols]
  combined_cols = lake_cols + external_cols
'''
ko_matrix_replacement = '''  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  external_cols = [c for c in numeric_cols if c not in lake_cols]
  combined_cols = lake_cols + external_cols

  mtx_cols = []
  mtx_metadata_view = pd.DataFrame()
  if not meta.empty:
    layer_abbrev = meta.get("data_layer_abbrev", pd.Series("", index=meta.index)).astype(str).str.upper()
    layer_name = meta.get("data_layer", pd.Series("", index=meta.index)).astype(str).str.casefold()
    mtx_records = meta.loc[layer_abbrev.eq("MTX") | layer_name.str.contains("metatranscript", na=False)].copy()
    matrix_columns = [
      col for col in [
        "ST8_matrix_column", "matrix_column_all_KO", "matrix_column_iron_KO",
        "matrix_column_selected", "matrix_column",
      ] if col in mtx_records.columns
    ]
    matrix_to_row = {}
    for source_column in numeric_cols:
      source_text = str(source_column).strip()
      for row_index, row in mtx_records.iterrows():
        exact_values = [str(row.get(col, "")).strip() for col in matrix_columns]
        identifier_values = [
          str(row.get(col, "")).strip() for col in [
            "taxon_oid", "IMG Genome ID", "sample_id_created_this_study",
            "sample_id", "SRA Run", "SRA ID",
          ] if col in mtx_records.columns
        ]
        exact_match = source_text in {value for value in exact_values if value}
        identifier_match = any(
          len(value) >= 6 and value in source_text
          for value in identifier_values if value and value.casefold() != "nan"
        )
        if exact_match or identifier_match:
          matrix_to_row[source_text] = row_index
          break
    mtx_cols = [str(col) for col in numeric_cols if str(col) in matrix_to_row]
    metadata_rows = []
    for matrix_column in mtx_cols:
      row = mtx_records.loc[matrix_to_row[matrix_column]]
      metadata_rows.append({
        "Study Name": str(row.get("Study Name", row.get("study_name", ""))).strip(),
        "Genome Name / Sample Name": str(row.get("Genome Name / Sample Name", "")).strip(),
        "IMG/JGI identifier": str(row.get("taxon_oid", row.get("IMG Genome ID", ""))).strip(),
        "Study record": str(row.get("sample_id_created_this_study", row.get("sample_id", ""))).strip(),
        "SRA Run / ID": str(row.get("SRA Run", row.get("SRA ID", ""))).strip(),
        "Matrix column used": matrix_column,
        "Omics layer": str(row.get("data_layer", "Metatranscriptomics")),
      })
    mtx_metadata_view = pd.DataFrame(metadata_rows)
'''
source = replace_once(source, ko_matrix_anchor, ko_matrix_replacement, "KO metatranscriptome source columns")

source = replace_once(
  source,
  '''    require_all_lakes: bool = False,
  ):
''',
  '''    require_all_lakes: bool = False,
    show_source_table: bool = False,
  ):
''',
  "KO metatranscriptome panel option",
)

ko_download_anchor = '''    d1, d2 = st.columns(2)
    with d1:
      csv_button(raw_table, f"{base_key}_{scope_key}_raw_counts_table.csv", txt("Baixar tabela raw count usada", "Download raw-count source table"))
    with d2:
      csv_button(z_table, f"{base_key}_{scope_key}_row_zscore_table.csv", txt("Baixar tabela z-score usada", "Download row-z-score source table"))
    st.caption(txt(caption_pt, caption_en))
'''
ko_download_replacement = '''    d1, d2 = st.columns(2)
    with d1:
      csv_button(raw_table, f"{base_key}_{scope_key}_raw_counts_table.csv", txt("Baixar tabela raw count usada", "Download raw-count source table"))
    with d2:
      csv_button(z_table, f"{base_key}_{scope_key}_row_zscore_table.csv", txt("Baixar tabela z-score usada", "Download row-z-score source table"))
    if show_source_table:
      st.markdown("###### " + txt("Tabela-fonte usada no painel", "Source table used for this panel"))
      show_table(raw_table, f"{base_key}_{scope_key}_visible_source_table", height=520)
      if not mtx_metadata_view.empty:
        st.markdown("###### " + txt("Estudos e identificadores dos metatranscriptomas", "Metatranscriptome studies and identifiers"))
        show_table(mtx_metadata_view, f"{base_key}_{scope_key}_metadata", height=420)
        csv_button(
          mtx_metadata_view,
          f"{base_key}_{scope_key}_studies_identifiers.csv",
          txt("Baixar estudos e identificadores", "Download studies and identifiers"),
        )
    st.caption(txt(caption_pt, caption_en))
'''
source = replace_once(source, ko_download_anchor, ko_download_replacement, "KO metatranscriptome source table")

ko_external_call_anchor = '''  render_pair(
    "2A. Somente ambientes externos ricos em ferro",
    "2A. External iron-rich environments only",
    external_cols,
    "external_only",
    f"Legenda: painel externo completo com {len(external_cols)} colunas ambientais, sem repetir as 20 amostras amazônicas já mostradas na seção 1. Raw e z-score usam exatamente as mesmas linhas e colunas.",
    f"Legend: complete external panel with {len(external_cols)} environment columns, without repeating the 20 Amazonian samples already shown in section 1. Raw and z-score use exactly the same rows and columns.",
  )
'''
ko_external_call_replacement = ko_external_call_anchor + '''  if mtx_cols:
    render_pair(
      "Metatranscriptomas — estudos e identificadores",
      "Metatranscriptomes — studies and identifiers",
      mtx_cols,
      "metatranscriptomes_only",
      f"Painel formado exclusivamente pelas {len(mtx_cols)} colunas classificadas como metatranscriptômicas nos metadados ST8. Os nomes dos estudos e identificadores estão vinculados à tabela-fonte abaixo.",
      f"Panel containing only the {len(mtx_cols)} columns classified as metatranscriptomic in the ST8 metadata. Study names and identifiers are linked to the source table below.",
      show_source_table=True,
    )
'''
source = replace_once(source, ko_external_call_anchor, ko_external_call_replacement, "KO metatranscriptome panel")


