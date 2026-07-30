from __future__ import annotations


MARKER = "CANGAMETAG_KEGG_S67_AXIS_READABILITY_V2 = 1"


if MARKER not in source:
  helper_anchor = "def _kegg_scope_rows("
  helper_code = r'''def _kegg_s67_compact_label(value: object, position: int) -> str:
  """Wrap one S67 x-axis label while preserving its original identifier.

  This helper changes display text only. Matrix columns, values, hover metadata
  and downloadable tables keep the exact original names.
  """
  text = re.sub(r"\s+", " ", str(value or "").strip())
  if re.match(r"^(AM|TIA|TI|VI)\.P\d+\.(D|R)$", text, flags=re.IGNORECASE):
    return text

  identifier_match = re.search(
    r"\b(?:Ga\d{6,}|\d{7,}|[SED]RR\d+|SAM[NED]A?\d+)\b\s*$",
    text,
    flags=re.IGNORECASE,
  )
  identifier = identifier_match.group(0).strip() if identifier_match else ""
  descriptor = text[:identifier_match.start()].strip(" -_/|,") if identifier_match else text

  display_replacements = {
    "Acid Mine Drainage": "Acid mine drainage",
    "Acid mine drainage": "Acid mine drainage",
    "Hydrotherm Fe rich": "Hydrothermal Fe-rich",
    "Metatransc of lab": "Lab metatranscriptome",
    "Metatransc of freshwater": "Freshwater metatranscriptome",
    "Freshwater sediment microbial": "Freshwater sediment",
    "Freshwater microbial communitie": "Freshwater microbial community",
    "Biofilm microbial communitie": "Biofilm microbial community",
    "Pink biofilm microbial": "Pink biofilm",
    "Lab enriched acid": "Lab-enriched acid",
    "Lab enriched sediment": "Lab-enriched sediment",
  }
  descriptor = display_replacements.get(descriptor, descriptor)
  descriptor_lines = textwrap.wrap(
    descriptor or f"External record {position}",
    width=16,
    break_long_words=False,
    break_on_hyphens=False,
  )
  if len(descriptor_lines) > 3:
    descriptor_lines = descriptor_lines[:2] + [" ".join(descriptor_lines[2:])]
  lines = descriptor_lines + ([identifier] if identifier else [])
  return "<br>".join(lines)


def _kegg_reorder_full_matrix_like_grouped_source(
  full_status: pd.DataFrame,
  status_csv: Path,
  key_prefix: str,
) -> pd.DataFrame:
  """Use the S67 grouped-source column order without changing any cell value."""
  if (
    not key_prefix.endswith("_environmental_group")
    or full_status is None
    or full_status.empty
    or status_csv is None
    or not status_csv.exists()
  ):
    return full_status
  try:
    grouped_raw = pd.read_csv(status_csv, keep_default_na=False)
    grouped_status, _ = _prepare_kegg_status_frame(grouped_raw)
  except Exception:
    return full_status
  if grouped_status.empty:
    return full_status
  grouped_order = [column for column in grouped_status.columns if column in full_status.columns]
  remaining = [column for column in full_status.columns if column not in grouped_order]
  if not grouped_order:
    return full_status
  reordered = full_status.loc[:, grouped_order + remaining].copy()
  if not reordered.sort_index(axis=1).equals(full_status.sort_index(axis=1)):
    raise RuntimeError("S67 environmental-group reordering changed source matrix values")
  return reordered


'''
  if helper_anchor in source and "def _kegg_s67_compact_label(" not in source:
    source = source.replace(helper_anchor, helper_code + helper_anchor, 1)

  preparation_anchor = '''    full_status, first_col = _prepare_kegg_status_frame(full_raw)
    if full_status.empty:
'''
  preparation_replacement = '''    full_status, first_col = _prepare_kegg_status_frame(full_raw)
    full_status = _kegg_reorder_full_matrix_like_grouped_source(
      full_status,
      status_csv,
      key_prefix,
    )
    if full_status.empty:
'''
  if preparation_anchor in source:
    source = source.replace(preparation_anchor, preparation_replacement, 1)

  old_labels = '    x_labels = [mtx_label_map.get(str(col), str(col)) for col in view_original.columns]\n'
  new_labels = '''    if key_prefix.startswith("kegg_combined_lagoon_external"):
      x_labels = [
        _kegg_s67_compact_label(mtx_label_map.get(str(col), str(col)), index + 1)
        for index, col in enumerate(view_original.columns)
      ]
    else:
      x_labels = [mtx_label_map.get(str(col), str(col)) for col in view_original.columns]
'''
  if old_labels in source:
    source = source.replace(old_labels, new_labels, 1)

  old_geometry = '''    n_rows, n_cols = view_original.shape
    cell_w = 44 if n_cols <= 24 else 40 if n_cols <= 40 else 34
    cell_h = 34 if n_rows <= 180 else 30
    if scope == "metatranscriptome_only":
      cell_w = 112 if n_cols <= 16 else 96 if n_cols <= 28 else 78
      cell_h = 40 if n_rows <= 140 else 34
'''
  new_geometry = '''    n_rows, n_cols = view_original.shape
    cell_w = 44 if n_cols <= 24 else 40 if n_cols <= 40 else 34
    cell_h = 34 if n_rows <= 180 else 30
    if scope == "metatranscriptome_only":
      cell_w = 112 if n_cols <= 16 else 96 if n_cols <= 28 else 78
      cell_h = 40 if n_rows <= 140 else 34
    if key_prefix.startswith("kegg_combined_lagoon_external"):
      cell_w = 104 if n_cols <= 50 else 94 if n_cols <= 90 else 86
      cell_h = 36 if n_rows <= 180 else 31
'''
  if old_geometry in source:
    source = source.replace(old_geometry, new_geometry, 1)

  old_layout = '''      width=max(1650 if scope == "metatranscriptome_only" else 1250, min(16000, 720 + cell_w * n_cols)),
      height=max(980 if scope == "metatranscriptome_only" else 720, min(26000, 340 + cell_h * n_rows)),
      margin=dict(
        l=780,
        r=210 if scope == "metatranscriptome_only" else 180,
        t=90 if scope == "metatranscriptome_only" else 70,
        b=430 if scope == "metatranscriptome_only" else 330,
      ),
'''
  new_layout = '''      width=max(
        2100 if key_prefix.startswith("kegg_combined_lagoon_external") else 1650 if scope == "metatranscriptome_only" else 1250,
        min(16000, 780 + cell_w * n_cols),
      ),
      height=max(
        980 if scope == "metatranscriptome_only" else 780 if key_prefix.startswith("kegg_combined_lagoon_external") else 720,
        min(26000, 340 + cell_h * n_rows),
      ),
      margin=dict(
        l=780,
        r=240 if key_prefix.startswith("kegg_combined_lagoon_external") else 210 if scope == "metatranscriptome_only" else 180,
        t=90 if scope == "metatranscriptome_only" else 80 if key_prefix.startswith("kegg_combined_lagoon_external") else 70,
        b=350 if key_prefix.startswith("kegg_combined_lagoon_external") else 430 if scope == "metatranscriptome_only" else 330,
      ),
'''
  if old_layout in source:
    source = source.replace(old_layout, new_layout, 1)

  old_axes = '''    else:
      fig.update_xaxes(tickangle=-55, tickfont=dict(size=11), automargin=True, title="Sample / MAG")
      fig.update_yaxes(tickfont=dict(size=11), automargin=True, tickmode="array", tickvals=y_labels, ticktext=y_labels, title="KEGG module")
'''
  new_axes = '''    elif key_prefix.startswith("kegg_combined_lagoon_external"):
      fig.update_xaxes(
        tickangle=0,
        tickfont=dict(size=10),
        automargin=True,
        title="Lake metagenomes and external iron-rich environments",
        constrain="domain",
        tickmode="array",
        tickvals=x_labels,
        ticktext=x_labels,
      )
      fig.update_yaxes(
        tickfont=dict(size=11),
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
  if old_axes in source:
    source = source.replace(old_axes, new_axes, 1)

  table_anchor = '    st.markdown("###### Source table used for this panel")\n'
  table_note = '''    if key_prefix.startswith("kegg_combined_lagoon_external"):
      st.caption(txt(
        "Na Figura Suplementar 67, cada ambiente externo aparece em linhas curtas no eixo X, com o identificador em uma linha separada. Os nomes originais completos permanecem no hover e na tabela-fonte. A visualização por grupo ambiental usa a ordem de colunas da figura agrupada, mas mantém exatamente os mesmos estados e valores da matriz completa.",
        "In Supplementary Figure 67, each external environment is displayed on short x-axis lines with its identifier on a separate line. Complete original names remain in hover text and the source table. The environmental-group view uses the grouped figure's column order while retaining exactly the same statuses and values from the full matrix.",
      ))
'''
  if table_anchor in source and "cada ambiente externo aparece em linhas curtas" not in source:
    source = source.replace(table_anchor, table_note + table_anchor, 1)

  marker_anchor = "def _kegg_s67_compact_label(value: object, position: int) -> str:\n"
  if marker_anchor in source:
    source = source.replace(marker_anchor, MARKER + "\n\n\n" + marker_anchor, 1)
