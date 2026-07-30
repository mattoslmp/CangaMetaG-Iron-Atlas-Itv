from __future__ import annotations


MARKER = "CANGAMETAG_KEGG_S67_AXIS_READABILITY_V1 = 1"


if MARKER not in source:
  helper_anchor = "def _kegg_scope_rows("
  helper_code = r'''def _kegg_s67_compact_label(value: object, position: int) -> str:
  """Return a compact, stable axis label without altering matrix identifiers."""
  text = str(value or "").strip()
  if re.match(r"^(AM|TIA|TI|VI)\.P\d+\.(D|R)$", text, flags=re.IGNORECASE):
    return text
  identifier_match = re.search(r"\b(?:Ga\d{6,}|\d{7,}|[SED]RR\d+|SAM[NED]A?\d+)\b", text, flags=re.IGNORECASE)
  if identifier_match:
    return identifier_match.group(0)
  normalized = re.sub(r"\s+", " ", text)
  if len(normalized) <= 22:
    return normalized
  words = normalized.split(" ")
  abbreviated = " ".join(words[:3]).strip(" -_/|,")
  if abbreviated and len(abbreviated) <= 24:
    return abbreviated + "…"
  return f"EXT-{position:03d}"


'''
  if helper_anchor in source and "def _kegg_s67_compact_label(" not in source:
    source = source.replace(helper_anchor, helper_code + helper_anchor, 1)

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
      cell_w = 62 if n_cols <= 50 else 54 if n_cols <= 90 else 48
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
        1850 if key_prefix.startswith("kegg_combined_lagoon_external") else 1650 if scope == "metatranscriptome_only" else 1250,
        min(16000, 760 + cell_w * n_cols),
      ),
      height=max(980 if scope == "metatranscriptome_only" else 760 if key_prefix.startswith("kegg_combined_lagoon_external") else 720, min(26000, 340 + cell_h * n_rows)),
      margin=dict(
        l=780,
        r=230 if key_prefix.startswith("kegg_combined_lagoon_external") else 210 if scope == "metatranscriptome_only" else 180,
        t=90 if scope == "metatranscriptome_only" else 80 if key_prefix.startswith("kegg_combined_lagoon_external") else 70,
        b=500 if key_prefix.startswith("kegg_combined_lagoon_external") else 430 if scope == "metatranscriptome_only" else 330,
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
        tickangle=-65,
        tickfont=dict(size=10),
        automargin=True,
        title="Lake metagenomes and external iron-rich environments",
        constrain="domain",
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
        "Na Figura Suplementar 67, os nomes longos dos ambientes externos são abreviados somente no eixo X para evitar sobreposição. Os identificadores originais e os nomes completos permanecem no hover e nesta tabela-fonte; nenhuma coluna, estado ou valor foi modificado.",
        "For Supplementary Figure 67, long external-environment names are abbreviated on the x axis only to prevent overlap. Original identifiers and complete names remain in the hover and source table; no column, state or value was modified.",
      ))
'''
  if table_anchor in source and "Na Figura Suplementar 67" not in source:
    source = source.replace(table_anchor, table_note + table_anchor, 1)

  marker_anchor = "def _kegg_s67_compact_label(value: object, position: int) -> str:\n"
  if marker_anchor in source:
    source = source.replace(marker_anchor, MARKER + "\n\n\n" + marker_anchor, 1)
