from pathlib import Path

path = Path("app.py")
text = path.read_text(encoding="utf-8")

old_scope = '''def _kegg_scope_rows(article_status: pd.DataFrame, full_status: pd.DataFrame, scope: str) -> pd.DataFrame:
  """Select module rows from the immutable source-status matrix."""
  source = full_status.copy()
  if scope == "all_complete":
    return source.loc[source.eq("Complete").all(axis=1)].copy()
  if scope == "complete_any":
    return source.loc[source.eq("Complete").any(axis=1)].copy()
  if scope == "one_missing":
    return source.loc[source.eq("1 block missing").any(axis=1)].copy()
  return source
'''
new_scope = '''def _kegg_scope_rows(article_status: pd.DataFrame, full_status: pd.DataFrame, scope: str) -> pd.DataFrame:
  """Select module rows from the immutable source-status matrix."""
  source = full_status.copy()
  if scope == "complete_any":
    return source.loc[source.eq("Complete").any(axis=1)].copy()
  if scope == "one_missing":
    return source.loc[source.eq("1 block missing").any(axis=1)].copy()
  return source
'''
if old_scope not in text:
  raise SystemExit("Expected _kegg_scope_rows block was not found")
text = text.replace(old_scope, new_scope, 1)

old_labels = '''    scope_labels = {
      "all_complete": f"1. Complete in all {entity_plural}",
      "complete_any": f"2. Complete in at least one {entity_singular}",
      "one_missing": f"3. One block missing in at least one {entity_singular}",
      "all": "4. Full matrix — Complete, 1 block missing and Incomplete",
    }
'''
new_labels = '''    scope_labels = {
      "complete_any": f"1. Complete in at least one {entity_singular}",
      "one_missing": f"2. One block missing in at least one {entity_singular}",
      "all": "3. Full matrix — Complete, 1 block missing and Incomplete",
    }
'''
if old_labels not in text:
  raise SystemExit("Expected scope_labels block was not found")
text = text.replace(old_labels, new_labels, 1)

old_descriptions = '''    scope_descriptions = {
      "all_complete": f"Modules classified as Complete in every {entity_singular} of the immutable source matrix.",
      "complete_any": f"Modules classified as Complete in at least one {entity_singular}; all original cell statuses for retained rows are preserved.",
      "one_missing": f"Modules with at least one '1 block missing' call; Complete and Incomplete calls in the same retained rows remain visible.",
      "all": "All modules and all original statuses from the source matrix. No row-selection filter is applied.",
    }
'''
new_descriptions = '''    scope_descriptions = {
      "complete_any": f"Modules classified as Complete in at least one {entity_singular}; all original cell statuses for retained rows are preserved.",
      "one_missing": f"Modules with at least one '1 block missing' call; Complete and Incomplete calls in the same retained rows remain visible.",
      "all": "All modules and all original statuses from the source matrix. No row-selection filter is applied.",
    }
'''
if old_descriptions not in text:
  raise SystemExit("Expected scope_descriptions block was not found")
text = text.replace(old_descriptions, new_descriptions, 1)

for old, new in {
  "_module_scope_v9": "_module_scope_v10",
  "_show_all_modules_v9_": "_show_all_modules_v10_",
  "_module_count_v9_": "_module_count_v10_",
  "_samples_v9_": "_samples_v10_",
  "_visible_states_v9_": "_visible_states_v10_",
  "_interactive_v9_": "_interactive_v10_",
  "_status_matrix_v9_": "_status_matrix_v10_",
}.items():
  text = text.replace(old, new)

old_table_block = '''    table_out = view_original.reset_index().rename(columns={view_original.index.name or first_col: "KEGG module"})
    show_table(table_out, f"{key_prefix}_status_matrix_v10_{scope}_{module_count}", height=400)
    d1, d2 = st.columns(2)
    with d1:
      csv_button(table_out, f"{key_prefix}_{scope}_{module_count}_displayed_statuses.csv", "Download displayed matrix", context=key_prefix)
    with d2:
      csv_button(full_raw, f"{key_prefix}_complete_source_matrix.csv", "Download complete source matrix", context=f"{key_prefix}_source")
'''
new_table_block = '''    table_out = view_original.reset_index().rename(columns={view_original.index.name or first_col: "KEGG module"})
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
if old_table_block not in text:
  raise SystemExit("Expected source-table display block was not found")
text = text.replace(old_table_block, new_table_block, 1)

path.write_text(text, encoding="utf-8")
