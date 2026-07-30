from pathlib import Path
import re

APP = Path("app.py")
text = APP.read_text(encoding="utf-8")

scope_function = '''def _kegg_scope_rows(article_status: pd.DataFrame, full_status: pd.DataFrame, scope: str) -> pd.DataFrame:
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
text, n_scope = re.subn(
  r"def _kegg_scope_rows\(.*?\n(?=def _display_kegg_completeness_panel)",
  scope_function,
  text,
  count=1,
  flags=re.S,
)
if n_scope != 1:
  raise SystemExit(f"Could not replace _kegg_scope_rows: {n_scope}")

panel_function = '''def _display_kegg_completeness_panel(fig_path: Path, caption: str, status_csv: Path, key_prefix: str, full_status_csv: Path | None = None) -> None:
  """Show the approved static figure and an explorer backed only by source statuses."""
  _display_static_publication_image(fig_path, fig_path.name, caption, key_prefix=key_prefix)
  source_csv = full_status_csv if full_status_csv and full_status_csv.exists() else status_csv
  if not source_csv.exists():
    st.caption("Interactive matrix not found.")
    return
  try:
    full_raw = pd.read_csv(source_csv, keep_default_na=False)
    full_status, first_col = _prepare_kegg_status_frame(full_raw)
    if full_status.empty:
      st.info("Empty KEGG status matrix.")
      return

    entity_plural = "MAGs" if key_prefix == "kegg_mags" else "samples"
    entity_singular = "MAG" if key_prefix == "kegg_mags" else "sample"
    st.markdown("##### KEGG module completeness explorer")
    scope_labels = {
      "all_complete": f"1. Complete in all {entity_plural}",
      "complete_any": f"2. Complete in at least one {entity_singular}",
      "one_missing": f"3. One block missing in at least one {entity_singular}",
      "all": "4. Full matrix — Complete, 1 block missing and Incomplete",
    }
    c1, c2 = st.columns([0.48, 0.52])
    with c1:
      scope = st.radio(
        "Module set",
        list(scope_labels),
        format_func=lambda value: scope_labels[value],
        key=f"{key_prefix}_module_scope_v9",
      )

    scope_status = _kegg_scope_rows(pd.DataFrame(), full_status, scope)
    ranked = _rank_kegg_modules_for_display(scope_status)
    available = len(ranked)
    if available == 0:
      st.info("No module matches this source-matrix criterion.")
      return

    with c2:
      show_all = st.checkbox(
        f"Show all {available} modules in this set",
        value=False,
        key=f"{key_prefix}_show_all_modules_v9_{scope}",
      )
      module_count = available if show_all else int(st.number_input(
        "Number of displayed modules",
        min_value=1,
        max_value=available,
        value=min(40, available),
        step=1,
        key=f"{key_prefix}_module_count_v9_{scope}_{available}",
      ))

    scope_descriptions = {
      "all_complete": f"Modules classified as Complete in every {entity_singular} of the immutable source matrix.",
      "complete_any": f"Modules classified as Complete in at least one {entity_singular}; all original cell statuses for retained rows are preserved.",
      "one_missing": f"Modules with at least one '1 block missing' call; Complete and Incomplete calls in the same retained rows remain visible.",
      "all": "All modules and all original statuses from the source matrix. No row-selection filter is applied.",
    }
    st.caption(scope_descriptions[scope])

    selected_modules = ranked[:module_count]
    all_samples = list(scope_status.columns)
    c3, c4 = st.columns([0.55, 0.45])
    with c3:
      sample_filter = st.multiselect(
        "Samples/MAGs",
        all_samples,
        default=all_samples,
        key=f"{key_prefix}_samples_v9_{scope}",
      )
    with c4:
      visible_states = st.multiselect(
        "Visible states",
        ["Complete", "1 block missing", "Incomplete"],
        default=["Complete", "1 block missing", "Incomplete"],
        key=f"{key_prefix}_visible_states_v9_{scope}",
      )
    if not sample_filter:
      sample_filter = all_samples

    view_original = scope_status.loc[selected_modules, sample_filter].copy()
    if view_original.empty:
      st.info("No module matches the filters.")
      return
    numeric, view_visual = _kegg_status_to_numeric_matrix(view_original)
    if visible_states:
      raw_visible_states = set(visible_states)
      if "Incomplete" in raw_visible_states:
        raw_visible_states.add("2 blocks missing")
      numeric = numeric.where(view_original.isin(raw_visible_states))

    x_labels = list(view_original.columns)
    y_labels_full = list(view_original.index)
    y_labels = [_wrap_kegg_axis_label(label, width=68) for label in y_labels_full]
    hover = []
    for row_name, row in view_original.iterrows():
      code, desc = _split_kegg_module_label(row_name)
      url = _kegg_official_module_url(code)
      hover.append([
        "<br>".join([
          f"<b>KEGG module:</b> {code}",
          f"<b>Description:</b> {desc or row_name}",
          f"<b>Sample/MAG:</b> {col}",
          f"<b>Original status:</b> {row[col]}",
          f"<b>Visual category:</b> {view_visual.at[row_name, col]}",
          f"<b>Official KEGG:</b> {url}",
        ]) for col in view_original.columns
      ])

    n_rows, n_cols = view_original.shape
    cell_w = 44 if n_cols <= 24 else 40 if n_cols <= 40 else 34
    cell_h = 34 if n_rows <= 180 else 30
    fig = go.Figure(go.Heatmap(
      z=numeric.to_numpy(float),
      x=x_labels,
      y=y_labels,
      customdata=np.asarray(hover, dtype=object),
      hovertemplate="%{customdata}<extra></extra>",
      zmin=0,
      zmax=2,
      colorscale=KEGG_MODULE_COLORSCALE,
      xgap=0.45,
      ygap=0.45,
      colorbar=dict(
        title=dict(text="KEGG module status", font=dict(size=14)),
        tickmode="array",
        tickvals=[0, 1, 2],
        ticktext=["Incomplete", "1 block missing", "Complete"],
        thickness=18,
        len=0.78,
        tickfont=dict(size=12),
      ),
    ))
    fig.update_layout(
      width=max(1250, min(16000, 650 + cell_w * n_cols)),
      height=max(720, min(26000, 300 + cell_h * n_rows)),
      margin=dict(l=760, r=180, t=70, b=330),
      font=dict(size=13, color="#111827"),
      meta={
        "preserve_cell_geometry": True,
        "force_all_y_ticks": True,
        "all_y_labels_visible": True,
        "cell_width_px": cell_w,
        "cell_height_px": cell_h,
      },
    )
    fig.update_xaxes(tickangle=-55, tickfont=dict(size=11), automargin=True, title="Sample / MAG")
    fig.update_yaxes(tickfont=dict(size=11), automargin=True, tickmode="array", tickvals=y_labels, ticktext=y_labels, title="KEGG module")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Modules in source matrix", len(full_status))
    m2.metric("Modules in selected set", available)
    m3.metric("Displayed modules", len(view_original))
    m4.metric("Samples/MAGs", len(sample_filter))
    render_plotly_downloadable(
      fig,
      key=f"{key_prefix}_interactive_v9_{scope}_{module_count}_{len(sample_filter)}",
      basename=f"{key_prefix}_{scope}_{module_count}_modules",
    )
    table_out = view_original.reset_index().rename(columns={view_original.index.name or first_col: "KEGG module"})
    show_table(table_out, f"{key_prefix}_status_matrix_v9_{scope}_{module_count}", height=400)
    d1, d2 = st.columns(2)
    with d1:
      csv_button(table_out, f"{key_prefix}_{scope}_{module_count}_displayed_statuses.csv", "Download displayed matrix", context=key_prefix)
    with d2:
      csv_button(full_raw, f"{key_prefix}_complete_source_matrix.csv", "Download complete source matrix", context=f"{key_prefix}_source")
  except Exception as exc:
    st.warning(f"Interactive version could not be generated: {exc}")


'''
text, n_panel = re.subn(
  r"def _display_kegg_completeness_panel\(.*?\n(?=def kegg_modules_tab\(\):)",
  panel_function,
  text,
  count=1,
  flags=re.S,
)
if n_panel != 1:
  raise SystemExit(f"Could not replace _display_kegg_completeness_panel: {n_panel}")

old_intro = '''  st.markdown("### Direct visualization of KEGG module completeness")
  st.caption(txt(
    "Esta seção mostra diretamente as figuras finais de completude de módulos KEGG. Os arquivos exibidos são os mesmos sincronizados com o artigo, as figuras suplementares e a seção Final figures & scripts.",
    "This section directly shows the final KEGG module completeness figures. The displayed files are the same files synchronized with the manuscript, supplementary figures and Final figures & scripts section."
  ))
'''
new_intro = '''  st.markdown("### Direct visualization of KEGG module completeness")
  st.caption("The displayed files are the same source-linked figures used in the manuscript, supplementary material and Final figures & scripts section.")
  st.info("Data provenance: no synthetic, simulated or randomly generated values are used. MAG and lagoon-metagenome panels read their original packaged KEMET status matrices. ST8 external and combined panels use categorical module-status matrices deterministically derived from the KO profiles in tables/Supplementary_Table_8.xlsx; no imputation or value replacement is applied.")
'''
if old_intro not in text:
  raise SystemExit("Could not find the KEGG direct-visualization intro.")
text = text.replace(old_intro, new_intro, 1)

caption_replacements = {
  'txt("Completude dos módulos KEGG nos MAGs.", "KEGG module completeness in MAGs.")': '"KEGG module completeness in MAGs."',
  'txt("Completude dos módulos KEGG nos metagenomas das lagoas.", "KEGG module completeness in lagoon metagenomes.")': '"KEGG module completeness in lagoon metagenomes."',
  'txt("S40 — versão final por environmental group: todos os mesmos registros e estados da matriz-fonte, com alteração exclusiva da ordem das colunas para manter cada grupo lado a lado.", "S40 — final environmental-group version: all records and statuses from the same source matrix, with only the column order changed to keep each group together.")': '"S40 — external iron-rich metagenomes grouped by environmental context; source statuses are unchanged."',
  'txt("S67 — ordem original: completude combinada dos módulos KEGG nas lagoas e nos metagenomas externos ricos em ferro.", "S67 — original order: combined KEGG module completeness in lagoon and external iron-rich metagenomes.")': '"S67 — combined KEGG module completeness in lagoon and external iron-rich metagenomes, original source order."',
  'txt("S67 — por environmental group: as mesmas amostras, registros, módulos e estados da versão original, somente com as colunas do mesmo grupo ambiental lado a lado.", "S67 — by environmental group: the same samples, records, modules and statuses as the original version, with only columns from the same environmental group placed side by side.")': '"S67 — the same combined matrix, with columns grouped by environmental context; source statuses are unchanged."',
}
for old, new in caption_replacements.items():
  if old not in text:
    raise SystemExit(f"Could not find caption: {old[:80]}")
  text = text.replace(old, new, 1)

for forbidden in (
  "Interactive complete-matrix explorer",
  "Selected for the article",
  "Complete — all",
  "All modules in the source matrix",
  "Explorador interativo da matriz completa",
):
  if forbidden in text:
    raise SystemExit(f"Legacy label remains: {forbidden}")

compile(text, str(APP), "exec")
APP.write_text(text, encoding="utf-8")
print("Patched app.py successfully.")
