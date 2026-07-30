from __future__ import annotations


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


# Add an MTX-only option to KEGG completeness panels when the source matrix
# contains columns linked to ST8 metatranscriptome records.
kegg_scope_anchor = '''    entity_plural = "MAGs" if key_prefix == "kegg_mags" else "samples"
    entity_singular = "MAG" if key_prefix == "kegg_mags" else "sample"
    st.markdown("##### KEGG module completeness explorer")
    scope_labels = {
      "complete_any": f"1. Complete in at least one {entity_singular}",
      "one_missing": f"2. One block missing in at least one {entity_singular}",
      "all": "3. Full matrix — Complete, 1 block missing and Incomplete",
    }
'''
kegg_scope_replacement = '''    entity_plural = "MAGs" if key_prefix == "kegg_mags" else "samples"
    entity_singular = "MAG" if key_prefix == "kegg_mags" else "sample"

    mtx_columns = []
    mtx_label_map = {}
    mtx_hover_map = {}
    mtx_metadata_view = pd.DataFrame()
    if key_prefix != "kegg_mags":
      panel_meta = st8_column_metadata()
      if not panel_meta.empty:
        layer_abbrev = panel_meta.get("data_layer_abbrev", pd.Series("", index=panel_meta.index)).astype(str).str.upper()
        layer_name = panel_meta.get("data_layer", pd.Series("", index=panel_meta.index)).astype(str).str.casefold()
        mtx_records = panel_meta.loc[layer_abbrev.eq("MTX") | layer_name.str.contains("metatranscript", na=False)].copy()
        matrix_columns = [
          col for col in [
            "ST8_matrix_column", "matrix_column_all_KO", "matrix_column_iron_KO",
            "matrix_column_selected", "matrix_column",
          ] if col in mtx_records.columns
        ]
        matrix_to_row = {}
        for source_column in full_status.columns:
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
        mtx_columns = [str(col) for col in full_status.columns if str(col) in matrix_to_row]
        metadata_rows = []
        for matrix_column in mtx_columns:
          row = mtx_records.loc[matrix_to_row[matrix_column]]
          study = str(row.get("Study Name", row.get("study_name", ""))).strip()
          sample_name = str(row.get("Genome Name / Sample Name", "")).strip()
          img_identifier = str(row.get("taxon_oid", row.get("IMG Genome ID", ""))).strip()
          sample_identifier = str(row.get("sample_id_created_this_study", row.get("sample_id", ""))).strip()
          sra_run = str(row.get("SRA Run", row.get("SRA ID", ""))).strip()
          display_identifier = img_identifier or sample_identifier or matrix_column
          study_axis = study if len(study) <= 48 else study[:45].rstrip() + "…"
          mtx_label_map[matrix_column] = f"{display_identifier}<br>{study_axis}" if study_axis else display_identifier
          mtx_hover_map[matrix_column] = "<br>".join([
            f"<b>Study:</b> {study or 'not reported'}",
            f"<b>Sample:</b> {sample_name or 'not reported'}",
            f"<b>IMG/JGI identifier:</b> {img_identifier or 'not reported'}",
            f"<b>Study record:</b> {sample_identifier or 'not reported'}",
            f"<b>SRA:</b> {sra_run or 'not reported'}",
            f"<b>Matrix column:</b> {matrix_column}",
          ])
          metadata_rows.append({
            "Study Name": study,
            "Genome Name / Sample Name": sample_name,
            "IMG/JGI identifier": img_identifier,
            "Study record": sample_identifier,
            "SRA Run / ID": sra_run,
            "Matrix column used": matrix_column,
            "Omics layer": str(row.get("data_layer", "Metatranscriptomics")),
          })
        mtx_metadata_view = pd.DataFrame(metadata_rows)

    st.markdown("##### KEGG module completeness explorer")
    scope_labels = {
      "complete_any": f"1. Complete in at least one {entity_singular}",
      "one_missing": f"2. One block missing in at least one {entity_singular}",
      "all": "3. Full matrix — Complete, 1 block missing and Incomplete",
    }
    if mtx_columns:
      scope_labels["metatranscriptome_only"] = "4. Metatranscriptomes only — studies and identifiers"
'''
source = replace_once(source, kegg_scope_anchor, kegg_scope_replacement, "KEGG metatranscriptome scope metadata")

source = replace_once(
  source,
  '    scope_status = _kegg_scope_rows(pd.DataFrame(), full_status, scope)\n',
  '''    scope_status = _kegg_scope_rows(pd.DataFrame(), full_status, scope)
    if scope == "metatranscriptome_only":
      scope_status = full_status.loc[:, mtx_columns].copy()
''',
  "KEGG metatranscriptome source columns",
)

kegg_descriptions_anchor = '''    scope_descriptions = {
      "complete_any": f"Modules classified as Complete in at least one {entity_singular}; all original cell statuses for retained rows are preserved.",
      "one_missing": f"Modules with at least one '1 block missing' call; Complete and Incomplete calls in the same retained rows remain visible.",
      "all": "All modules and all original statuses from the source matrix. No row-selection filter is applied.",
    }
'''
kegg_descriptions_replacement = '''    scope_descriptions = {
      "complete_any": f"Modules classified as Complete in at least one {entity_singular}; all original cell statuses for retained rows are preserved.",
      "one_missing": f"Modules with at least one '1 block missing' call; Complete and Incomplete calls in the same retained rows remain visible.",
      "all": "All modules and all original statuses from the source matrix. No row-selection filter is applied.",
      "metatranscriptome_only": "All source modules restricted to records classified as metatranscriptomes in the packaged ST8 metadata. Study names and identifiers are linked below the figure.",
    }
'''
source = replace_once(source, kegg_descriptions_anchor, kegg_descriptions_replacement, "KEGG metatranscriptome scope description")

source = replace_once(
  source,
  '    x_labels = list(view_original.columns)\n',
  '    x_labels = [mtx_label_map.get(str(col), str(col)) for col in view_original.columns]\n',
  "KEGG metatranscriptome axis labels",
)
source = replace_once(
  source,
  '          f"<b>Sample/MAG:</b> {col}",\n',
  '''          f"<b>Sample/MAG:</b> {mtx_label_map.get(str(col), str(col))}",
          mtx_hover_map.get(str(col), f"<b>Identifier:</b> {col}"),
''',
  "KEGG metatranscriptome hover metadata",
)

# Dedicated MTX geometry. Values and row/column selection remain untouched;
# only the pixel geometry and axis presentation change.
kegg_geometry_anchor = '''    n_rows, n_cols = view_original.shape
    cell_w = 44 if n_cols <= 24 else 40 if n_cols <= 40 else 34
    cell_h = 34 if n_rows <= 180 else 30
'''
kegg_geometry_replacement = '''    n_rows, n_cols = view_original.shape
    cell_w = 44 if n_cols <= 24 else 40 if n_cols <= 40 else 34
    cell_h = 34 if n_rows <= 180 else 30
    if scope == "metatranscriptome_only":
      cell_w = 112 if n_cols <= 16 else 96 if n_cols <= 28 else 78
      cell_h = 40 if n_rows <= 140 else 34
'''
source = replace_once(source, kegg_geometry_anchor, kegg_geometry_replacement, "KEGG MTX cell geometry")

kegg_layout_anchor = '''    fig.update_layout(
      width=max(1250, min(16000, 650 + cell_w * n_cols)),
      height=max(720, min(26000, 300 + cell_h * n_rows)),
      margin=dict(l=760, r=180, t=70, b=330),
      font=dict(size=13, color="#111827"),
'''
kegg_layout_replacement = '''    fig.update_layout(
      width=max(1650 if scope == "metatranscriptome_only" else 1250, min(16000, 720 + cell_w * n_cols)),
      height=max(980 if scope == "metatranscriptome_only" else 720, min(26000, 340 + cell_h * n_rows)),
      margin=dict(
        l=780,
        r=210 if scope == "metatranscriptome_only" else 180,
        t=90 if scope == "metatranscriptome_only" else 70,
        b=430 if scope == "metatranscriptome_only" else 330,
      ),
      font=dict(size=13, color="#111827"),
'''
source = replace_once(source, kegg_layout_anchor, kegg_layout_replacement, "KEGG MTX layout geometry")

kegg_axes_anchor = '''    fig.update_xaxes(tickangle=-55, tickfont=dict(size=11), automargin=True, title="Sample / MAG")
    fig.update_yaxes(tickfont=dict(size=11), automargin=True, tickmode="array", tickvals=y_labels, ticktext=y_labels, title="KEGG module")
'''
kegg_axes_replacement = '''    if scope == "metatranscriptome_only":
      fig.update_xaxes(
        tickangle=-45,
        tickfont=dict(size=12),
        automargin=True,
        title="Metatranscriptome — IMG/JGI identifier and study",
        constrain="domain",
      )
      fig.update_yaxes(
        tickfont=dict(size=12),
        automargin=True,
        tickmode="array",
        tickvals=y_labels,
        ticktext=y_labels,
        title="KEGG module",
      )
    else:
      fig.update_xaxes(tickangle=-55, tickfont=dict(size=11), automargin=True, title="Sample / MAG")
      fig.update_yaxes(tickfont=dict(size=11), automargin=True, tickmode="array", tickvals=y_labels, ticktext=y_labels, title="KEGG module")
'''
source = replace_once(source, kegg_axes_anchor, kegg_axes_replacement, "KEGG MTX axis geometry")

kegg_table_anchor = '''    table_out = view_original.reset_index().rename(columns={view_original.index.name or first_col: "KEGG module"})
    source_table_out = full_status.reset_index().rename(columns={full_status.index.name or first_col: "KEGG module"})
    st.markdown("###### Source table used for this panel")
    st.caption("This table contains the complete source-status matrix used to generate the interactive panel above.")
    show_table(source_table_out, f"{key_prefix}_source_status_matrix_v10", height=460)
    with st.expander("Displayed subset table", expanded=False):
      show_table(table_out, f"{key_prefix}_status_matrix_v10_{scope}_{module_count}", height=360)
    d1, d2 = st.columns(2)
    with d1:
      csv_button(table_out, f"{key_prefix}_{scope}_{module_count}_displayed_statuses.csv", "Download displayed matrix", context=key_prefix)
    with d2:
      csv_button(source_table_out, f"{key_prefix}_complete_source_matrix.csv", "Download complete source matrix", context=f"{key_prefix}_source")
'''
kegg_table_replacement = '''    table_out = view_original.reset_index().rename(columns={view_original.index.name or first_col: "KEGG module"})
    if scope == "metatranscriptome_only":
      source_table_out = table_out.copy()
      source_caption = "Exact metatranscriptome status matrix used to generate the interactive panel above."
      source_filename = f"{key_prefix}_metatranscriptome_source_matrix.csv"
    else:
      source_table_out = full_status.reset_index().rename(columns={full_status.index.name or first_col: "KEGG module"})
      source_caption = "This table contains the complete source-status matrix used to generate the interactive panel above."
      source_filename = f"{key_prefix}_complete_source_matrix.csv"
    st.markdown("###### Source table used for this panel")
    st.caption(source_caption)
    show_table(source_table_out, f"{key_prefix}_source_status_matrix_v13_{scope}", height=520 if scope == "metatranscriptome_only" else 460)
    if scope == "metatranscriptome_only" and not mtx_metadata_view.empty:
      st.markdown("###### Metatranscriptome studies and identifiers")
      show_table(mtx_metadata_view, f"{key_prefix}_metatranscriptome_metadata_v2", height=440)
      csv_button(
        mtx_metadata_view,
        f"{key_prefix}_metatranscriptome_studies_identifiers.csv",
        "Download metatranscriptome studies and identifiers",
        context=f"{key_prefix}_mtx_metadata",
      )
    with st.expander("Displayed subset table", expanded=False):
      show_table(table_out, f"{key_prefix}_status_matrix_v13_{scope}_{module_count}", height=400)
    d1, d2 = st.columns(2)
    with d1:
      csv_button(table_out, f"{key_prefix}_{scope}_{module_count}_displayed_statuses.csv", "Download displayed matrix", context=key_prefix)
    with d2:
      csv_button(source_table_out, source_filename, "Download source matrix", context=f"{key_prefix}_source_{scope}")
'''
source = replace_once(source, kegg_table_anchor, kegg_table_replacement, "KEGG metatranscriptome source tables")
