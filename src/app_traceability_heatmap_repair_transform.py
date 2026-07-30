from __future__ import annotations


MARKER = "CANGAMETAG_TRACEABILITY_HEATMAP_REPAIR_V1 = 1"


def _replace_function(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
  start = text.find(start_marker)
  if start < 0:
    return text
  end = text.find(end_marker, start)
  if end < 0:
    return text
  return text[:start] + replacement.rstrip() + "\n\n" + text[end + 1:]


if MARKER not in source:
  plotted_extractor = r'''def _plotly_exact_value_table(fig) -> pd.DataFrame:
  """Extract the exact values encoded in common Plotly trace types."""
  traces = list(getattr(fig, "data", []) or [])
  extracted: list[pd.DataFrame] = []

  for trace_index, trace in enumerate(traces):
    trace_type = str(getattr(trace, "type", "") or "unknown").lower()
    trace_name = str(getattr(trace, "name", "") or f"trace_{trace_index + 1}")

    raw_z = getattr(trace, "z", None)
    if raw_z is not None:
      try:
        z = np.asarray(raw_z, dtype=object)
      except Exception:
        z = np.asarray([], dtype=object)
      if z.ndim == 2 and z.size:
        raw_x = getattr(trace, "x", None)
        raw_y = getattr(trace, "y", None)
        x_values = list(raw_x) if raw_x is not None else list(range(z.shape[1]))
        y_values = list(raw_y) if raw_y is not None else list(range(z.shape[0]))
        if len(x_values) == z.shape[1] and len(y_values) == z.shape[0]:
          matrix = pd.DataFrame(z, columns=[str(value) for value in x_values])
          matrix.insert(0, "row_label", [str(value) for value in y_values])
          matrix.insert(0, "trace", trace_name)
          matrix.insert(1, "trace_type", trace_type)
          extracted.append(matrix)
          continue

    if trace_type == "table":
      try:
        headers = list(getattr(getattr(trace, "header", None), "values", None) or [])
        cell_columns = list(getattr(getattr(trace, "cells", None), "values", None) or [])
        if cell_columns:
          max_len = max(len(list(column)) for column in cell_columns)
          payload = {}
          for column_index, column in enumerate(cell_columns):
            values = list(column)
            header = str(headers[column_index]) if column_index < len(headers) else f"column_{column_index + 1}"
            payload[header] = values + [None] * (max_len - len(values))
          frame = pd.DataFrame(payload)
          frame.insert(0, "trace", trace_name)
          frame.insert(1, "trace_type", trace_type)
          extracted.append(frame)
          continue
      except Exception:
        pass

    if trace_type == "pie":
      labels = list(getattr(trace, "labels", None) or [])
      values = list(getattr(trace, "values", None) or [])
      rows = []
      for point_index in range(max(len(labels), len(values))):
        rows.append({
          "trace": trace_name,
          "trace_type": trace_type,
          "point_index": point_index,
          "label": labels[point_index] if point_index < len(labels) else None,
          "value": values[point_index] if point_index < len(values) else None,
        })
      if rows:
        extracted.append(pd.DataFrame(rows))
        continue

    fields = {
      "x": getattr(trace, "x", None),
      "y": getattr(trace, "y", None),
      "z": getattr(trace, "z", None),
      "latitude": getattr(trace, "lat", None),
      "longitude": getattr(trace, "lon", None),
      "location": getattr(trace, "locations", None),
      "label": getattr(trace, "labels", None),
      "value": getattr(trace, "values", None),
      "text": getattr(trace, "text", None),
      "open": getattr(trace, "open", None),
      "high": getattr(trace, "high", None),
      "low": getattr(trace, "low", None),
      "close": getattr(trace, "close", None),
    }
    normalized: dict[str, list] = {}
    for field_name, raw_values in fields.items():
      if raw_values is None:
        continue
      try:
        values = list(raw_values)
      except TypeError:
        values = [raw_values]
      if values:
        normalized[field_name] = values
    if not normalized:
      continue
    row_count = max(len(values) for values in normalized.values())
    rows = []
    for point_index in range(row_count):
      row = {
        "trace": trace_name,
        "trace_type": trace_type,
        "point_index": point_index,
      }
      for field_name, values in normalized.items():
        row[field_name] = values[point_index] if point_index < len(values) else None
      rows.append(row)
    if rows:
      extracted.append(pd.DataFrame(rows))

  if not extracted:
    return pd.DataFrame()
  if len(extracted) == 1:
    return extracted[0].reset_index(drop=True)
  return pd.concat(extracted, ignore_index=True, sort=False)
'''
  source = _replace_function(
    source,
    "def _plotly_exact_value_table(fig) -> pd.DataFrame:",
    "\ndef _audit_table_block",
    plotted_extractor,
  )

  audit_renderer = r'''def render_figure_audit_expander(
  fig, chart_key: str, *, input_table: pd.DataFrame | None = None,
  processed_table: pd.DataFrame | None = None, output_table: pd.DataFrame | None = None,
  method: str | None = None, input_source: str | None = None,
  script: str | None = None, instructions: str | None = None,
) -> None:
  context = _infer_figure_audit_context(chart_key, fig)
  plotted = _plotly_exact_value_table(fig)
  figure_id, figure_title = _figure_display_identity(fig, chart_key)
  if plotted is None or plotted.empty:
    plotted = pd.DataFrame([{
      "figure": figure_id,
      "title": figure_title,
      "chart_key": str(chart_key),
      "trace_count": len(list(getattr(fig, "data", []) or [])),
      "traceability_note": "No vector or matrix values could be extracted from the Plotly trace; use the upstream source path and final script listed above.",
    }])

  def _valid_table(frame: pd.DataFrame | None) -> bool:
    return isinstance(frame, pd.DataFrame) and not frame.empty

  source_frame = input_table.copy() if _valid_table(input_table) else plotted.copy()
  processed_frame = processed_table.copy() if _valid_table(processed_table) else source_frame.copy()
  output_frame = output_table.copy() if _valid_table(output_table) else plotted.copy()

  expander_label = txt(
    f"Dados utilizados em {figure_id} — {figure_title}",
    f"Source data for {figure_id} — {figure_title}",
  )
  with st.expander(expander_label, expanded=False):
    st.markdown(f"**{figure_id} — {figure_title}**")
    st.markdown(f"**{txt('Método', 'Method')}:** {method or context['method']}")
    st.markdown(f"**{txt('Input/fonte', 'Input/source')}:** {input_source or context['input']}")
    final_script = script or context['script']
    st.markdown(f"**{txt('Script final', 'Final script')}:** `{final_script}`")
    if instructions:
      st.markdown(f"**{txt('Instruções', 'Instructions')}:** {instructions}")
    st.caption(txt(
      "Política de dados: somente valores reais das tabelas e arquivos empacotados são usados; ausências não são substituídas por valores sintéticos.",
      "Data policy: only real values from packaged tables and files are used; missing values are not replaced by synthetic values.",
    ))

    tabs = st.tabs([
      txt("Fonte", "Source"),
      txt("Processada", "Processed"),
      txt("Output", "Output"),
      txt("Valores plotados", "Plotted values"),
    ])
    with tabs[0]:
      if not _valid_table(input_table):
        st.info(txt(
          "Nenhuma tabela-fonte separada foi passada a este gráfico. Para manter a rastreabilidade, esta aba mostra o snapshot exato extraído da figura; a fonte upstream está identificada acima.",
          "No separate source dataframe was passed to this chart. To preserve traceability, this tab shows the exact snapshot extracted from the figure; the upstream source is identified above.",
        ))
      _audit_table_block(source_frame, txt("Tabela-fonte rastreável", "Traceable source table"), f"{chart_key}_source")
    with tabs[1]:
      if not _valid_table(processed_table):
        st.info(txt(
          "Não existe uma tabela intermediária separada para este painel; os valores rastreáveis permanecem iguais ao snapshot de entrada exibido.",
          "No separate intermediate dataframe exists for this panel; the traceable values remain the same as the displayed input snapshot.",
        ))
      _audit_table_block(processed_frame, txt("Tabela processada", "Processed table"), f"{chart_key}_processed")
    with tabs[2]:
      if not _valid_table(output_table):
        st.info(txt(
          "Nenhuma tabela estatística de output distinta foi fornecida; esta aba registra os valores efetivamente enviados ao gráfico.",
          "No distinct statistical output dataframe was supplied; this tab records the values actually sent to the chart.",
        ))
      _audit_table_block(output_frame, txt("Tabela de output/estatística", "Output/statistics table"), f"{chart_key}_output")
    with tabs[3]:
      _audit_table_block(plotted, txt("Valores exatos da figura", "Exact figure values"), f"{chart_key}_plotted")
'''
  source = _replace_function(
    source,
    "def render_figure_audit_expander(",
    "\ndef render_plotly_downloadable",
    audit_renderer,
  )

  # Recognize all article-lake column spellings used by the packaged workbooks.
  source = source.replace(
    '''def _is_article_lake_sample_column(col: object) -> bool:
  return bool(re.match(r"^(AM|TIA|TI|VI)\\.P\\d+\\.(D|R)$", str(col).strip()))''',
    '''def _is_article_lake_sample_column(col: object) -> bool:
  text = re.sub(r"\\s+", "", str(col or "").strip()).upper()
  if re.match(r"^(AM|TIA|TI|VI)\\.P\\d+\\.(D|R)$", text):
    return True
  normalized = re.sub(r"[^A-Z0-9]+", ".", text).strip(".")
  return bool(re.match(r"^(AM|TIA|TI|VI)(?:\\.P)?\\d+(?:\\.(?:D|R|DRY|RAINY))?$", normalized))''',
    1,
  )

  old_lake_detection = '''  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  external_cols = [c for c in numeric_cols if c not in lake_cols]
  combined_cols = lake_cols + external_cols

  if len(lake_cols) != 20:
    st.error(txt(
      f"Falha na composição das lagoas: esperado 20 amostras AM/TI/TIA/VI, mas {len(lake_cols)} foram identificadas.",
      f"Lake-composition failure: expected 20 AM/TI/TIA/VI samples, but {len(lake_cols)} were identified.",
    ))
    return'''
  new_lake_detection = '''  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  if len(lake_cols) != 20:
    broad_pattern = re.compile(r"(?i)^(?:AM|TIA|TI|VI)(?:[._\\- ]*P)?[._\\- ]*\\d+(?:[._\\- ]*(?:D|R|DRY|RAINY))?$")
    broad_matches = [c for c in numeric_cols if broad_pattern.match(str(c).strip())]
    lake_cols = list(dict.fromkeys(lake_cols + broad_matches))
  if len(lake_cols) != 20 and isinstance(meta, pd.DataFrame) and not meta.empty:
    metadata_value_columns = [c for c in [
      "sample_id_created_this_study", "sample_id", "sample.id", "matrix_column",
      "ST8_matrix_column", "matrix_column_all_KO", "matrix_column_iron_KO",
      "matrix_column_selected", "lake_sample",
    ] if c in meta.columns]
    article_mask = pd.Series(False, index=meta.index)
    for column in metadata_value_columns:
      article_mask = article_mask | meta[column].fillna("").astype(str).str.match(
        r"(?i)^(?:AM|TIA|TI|VI)(?:[._\\- ]*P)?[._\\- ]*\\d+",
        na=False,
      )
    metadata_tokens: set[str] = set()
    for column in metadata_value_columns:
      metadata_tokens.update(meta.loc[article_mask, column].dropna().astype(str).str.strip().tolist())
    normalized_tokens = {re.sub(r"[^A-Z0-9]+", "", token.upper()) for token in metadata_tokens}
    metadata_matches = [
      c for c in numeric_cols
      if str(c).strip() in metadata_tokens
      or re.sub(r"[^A-Z0-9]+", "", str(c).upper()) in normalized_tokens
    ]
    lake_cols = list(dict.fromkeys(lake_cols + metadata_matches))
  lake_cols = [c for c in numeric_cols if c in set(lake_cols)]
  external_cols = [c for c in numeric_cols if c not in lake_cols]
  combined_cols = lake_cols + external_cols

  if len(lake_cols) != 20:
    st.warning(txt(
      f"Foram reconhecidas {len(lake_cols)}/20 amostras AM/TI/TIA/VI. Os heatmaps permanecerão visíveis com todas as colunas reconhecidas, e a tabela de rastreabilidade permitirá conferir os nomes originais.",
      f"{len(lake_cols)}/20 AM/TI/TIA/VI samples were recognized. Heatmaps remain visible with every recognized column, and the traceability table can be used to verify the original names.",
    ))'''
  if old_lake_detection in source:
    source = source.replace(old_lake_detection, new_lake_detection, 1)

  source = source.replace(
    '''    if require_all_lakes and len(pair_lakes) != 20:
      st.error(txt(
        f"O heatmap combinado foi bloqueado porque continha somente {len(pair_lakes)}/20 amostras das lagoas.",
        f"The combined heatmap was blocked because it contained only {len(pair_lakes)}/20 lake samples.",
      ))
      return''',
    '''    if require_all_lakes and len(pair_lakes) != 20:
      st.warning(txt(
        f"O painel combinado contém {len(pair_lakes)}/20 amostras reconhecidas das lagoas. Ele será mostrado para evitar ocultar os resultados; confira os identificadores na tabela de rastreabilidade.",
        f"The combined panel contains {len(pair_lakes)}/20 recognized lake samples. It remains visible so results are not hidden; verify identifiers in the traceability table.",
      ))''',
    1,
  )

  # Resolve manifest assets by exact name, canonical base name, P001 page or
  # multipage equivalent before reporting a missing final-figure file.
  old_integrity = '''        available_asset_names = {p.name for folder in (main_fig_dir, supplementary_fig_dir) if folder.exists() for p in folder.iterdir() if p.is_file()}
        missing_assets = []
        for _, audit_row in figure_manifest_checked.iterrows():
          for asset_col in ["PNG", "SVG", "PDF"]:
            asset_name = str(audit_row.get(asset_col, "")).strip()
            if asset_name and asset_name not in available_asset_names:
              missing_assets.append(asset_name)'''
  new_integrity = '''        asset_directories = [
          main_fig_dir,
          supplementary_fig_dir,
          BASE_DIR / "outputs" / "article_highres_figures",
          BASE_DIR / "outputs" / "publication_figure_exports",
        ]
        available_assets = [
          path
          for folder in asset_directories if folder.exists()
          for path in folder.rglob("*") if path.is_file()
        ]
        available_asset_names = {path.name for path in available_assets}

        def _manifest_asset_present(asset_name: str) -> bool:
          if asset_name in available_asset_names:
            return True
          requested = Path(asset_name)
          stem = requested.stem
          suffix = requested.suffix.lower()
          stems = {stem}
          page_match = re.search(r"_P0*1$", stem, flags=re.IGNORECASE)
          if page_match:
            stems.add(stem[:page_match.start()])
          else:
            stems.add(stem + "_P001")
            stems.add(stem + "_P01")
          stems.add(re.sub(r"_multipage$", "", stem, flags=re.IGNORECASE))
          for candidate in available_assets:
            if candidate.suffix.lower() != suffix:
              continue
            candidate_stem = candidate.stem
            if candidate_stem in stems:
              return True
            if any(candidate_stem.startswith(base + "_P") for base in stems):
              return True
            if suffix == ".pdf" and any(candidate_stem == base + "_multipage" for base in stems):
              return True
          return False

        missing_assets = []
        for _, audit_row in figure_manifest_checked.iterrows():
          for asset_col in ["PNG", "SVG", "PDF"]:
            asset_name = str(audit_row.get(asset_col, "")).strip()
            if asset_name and not _manifest_asset_present(asset_name):
              missing_assets.append(asset_name)'''
  if old_integrity in source:
    source = source.replace(old_integrity, new_integrity, 1)

  marker_anchor = "def _plotly_exact_value_table(fig) -> pd.DataFrame:\n"
  if marker_anchor in source:
    source = source.replace(marker_anchor, MARKER + "\n\n\n" + marker_anchor, 1)
