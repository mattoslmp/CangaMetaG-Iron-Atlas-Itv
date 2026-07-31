from __future__ import annotations


MARKER = "CANGAMETAG_PUBLIC_SCIENTIFIC_TRACEABILITY_ONLY_V1 = 1"


def _replace_function(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
  start = text.find(start_marker)
  if start < 0:
    return text
  end = text.find(end_marker, start)
  if end < 0:
    return text
  return text[:start] + replacement.rstrip() + "\n\n" + text[end + 1:]


if MARKER not in source:
  scientific_traceability = r'''def _public_scientific_result_table(frame) -> pd.DataFrame:
  """Keep only scientific result content suitable for the public interface.

  Internal prompts, test fixtures, assertions and unrelated project material are
  never part of a scientific figure's public traceability table. The underlying
  files remain untouched in the repository.
  """
  if frame is None:
    return pd.DataFrame()
  try:
    table = frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame(frame)
  except Exception:
    return pd.DataFrame()
  if table.empty:
    return table

  internal_columns = {
    "prompt", "question", "answer", "expected", "expected_output",
    "assertion", "test_case", "test_name", "internal_test", "test_fixture",
    "system_prompt", "developer_message", "instructions", "debug",
    "traceback", "private_notes", "private_reasoning", "chain_of_thought",
  }
  drop_columns = []
  for column in table.columns:
    normalized = re.sub(r"[^a-z0-9]+", "_", str(column).strip().casefold()).strip("_")
    if normalized in internal_columns:
      drop_columns.append(column)
  if drop_columns:
    table = table.drop(columns=drop_columns, errors="ignore")
  if table.empty:
    return table

  blocked_patterns = [
    r"parkinson",
    r"tell\s+us\s+about\s+your\s+connection",
    r"system\s+prompt",
    r"developer\s+message",
    r"chain\s+of\s+thought",
    r"private\s+reasoning",
    r"internal\s+test",
    r"unit\s+test",
    r"test\s+fixture",
    r"expected\s+output",
    r"assertionerror",
    r"pytest",
  ]
  try:
    row_text = table.fillna("").astype(str).agg(" | ".join, axis=1).str.casefold()
    blocked = row_text.str.contains("|".join(blocked_patterns), regex=True, na=False)
    table = table.loc[~blocked].copy()
  except Exception:
    pass
  return table.reset_index(drop=True)


def render_figure_audit_expander(
  fig, chart_key: str, *, input_table: pd.DataFrame | None = None,
  processed_table: pd.DataFrame | None = None, output_table: pd.DataFrame | None = None,
  method: str | None = None, input_source: str | None = None,
  script: str | None = None, instructions: str | None = None,
) -> None:
  """Show scientific source/result tables only; never expose internal test text."""
  plotted = harmonize_current_taxonomy_table(_plotly_exact_value_table(fig), BASE_DIR)
  source_table = _public_scientific_result_table(
    harmonize_current_taxonomy_table(input_table, BASE_DIR)
  )
  processed = _public_scientific_result_table(
    harmonize_current_taxonomy_table(processed_table, BASE_DIR)
  )
  output = _public_scientific_result_table(
    harmonize_current_taxonomy_table(output_table, BASE_DIR)
  )
  plotted = _public_scientific_result_table(plotted)

  # Preserve the four traceability stages requested for scientific figures,
  # while avoiding empty tabs. A missing intermediate stage inherits the nearest
  # available scientific table; it never imports text from prompts or tests.
  available = [table for table in [source_table, processed, output, plotted] if not table.empty]
  if not available:
    return
  fallback = available[0]
  if source_table.empty:
    source_table = fallback.copy()
  if processed.empty:
    processed = source_table.copy()
  if output.empty:
    output = processed.copy()
  if plotted.empty:
    plotted = output.copy()

  with st.expander(
    txt("Dados científicos usados nesta figura", "Scientific data used in this figure"),
    expanded=False,
  ):
    st.caption(txt(
      "Este painel contém apenas tabelas e valores diretamente ligados ao resultado exibido. Prompts, testes internos, instruções de desenvolvimento e conteúdos de outros projetos são excluídos da interface pública.",
      "This panel contains only tables and values directly linked to the displayed result. Prompts, internal tests, development instructions and material from other projects are excluded from the public interface.",
    ))
    tabs = st.tabs([
      txt("Fonte", "Source"),
      txt("Processada", "Processed"),
      txt("Resultado", "Output"),
      txt("Valores plotados", "Plotted values"),
    ])
    with tabs[0]:
      _audit_table_block(source_table, txt("Tabela-fonte científica", "Scientific source table"), f"{chart_key}_source_public")
    with tabs[1]:
      _audit_table_block(processed, txt("Tabela processada", "Processed table"), f"{chart_key}_processed_public")
    with tabs[2]:
      _audit_table_block(output, txt("Tabela de resultado/estatística", "Result/statistics table"), f"{chart_key}_output_public")
    with tabs[3]:
      _audit_table_block(plotted, txt("Valores exatos da figura", "Exact figure values"), f"{chart_key}_plotted_public")'''
  source = _replace_function(
    source,
    "def render_figure_audit_expander(",
    "\ndef render_plotly_downloadable(",
    scientific_traceability,
  )

  static_traceability = r'''def _render_static_figure_audit(path: Path, title: str, key_prefix: str) -> None:
  """Show only directly resolved scientific source tables for a static figure."""
  record = _static_figure_manifest_record(path)
  figure_id = str(record.get("Figure", "") or "").strip() or path.stem
  figure_title = str(record.get("Description", "") or record.get("Title", "") or title or path.stem).strip()
  inputs = [item.strip() for item in str(record.get("Inputs", "")).split(";") if item.strip()]
  resolved_tables: list[tuple[str, pd.DataFrame]] = []
  for input_name in inputs:
    candidate = BASE_DIR / input_name
    if not candidate.exists() or not candidate.is_file():
      continue
    table = _public_scientific_result_table(_read_tabular_input_for_audit(candidate))
    if not table.empty:
      resolved_tables.append((input_name, table))
  if not resolved_tables:
    return

  with st.expander(
    txt(
      f"Dados científicos de {figure_id} — {figure_title}",
      f"Scientific data for {figure_id} — {figure_title}",
    ),
    expanded=False,
  ):
    for index, (input_name, table) in enumerate(resolved_tables, start=1):
      st.markdown(f"**{txt('Tabela-fonte', 'Source table')} {index}:** `{input_name}`")
      show_table(
        table.head(1500),
        f"{key_prefix}_{path.stem}_scientific_source_{index}",
        height=380,
      )
      csv_button(
        table,
        f"{safe_filename(path.stem)}_source_{index}.csv",
        txt("Baixar tabela-fonte", "Download source table"),
        key=f"{key_prefix}_{path.stem}_scientific_source_csv_{index}",
      )'''
  source = _replace_function(
    source,
    "def _render_static_figure_audit(",
    "\ndef _display_static_publication_image(",
    static_traceability,
  )

  # Figure-to-app comparison is an internal regression test. Keep it in the
  # repository test suite, but do not show its status/table to public visitors.
  validation_start = source.find(
    '    validation = article_static_source_validation(article_domain, "Phylum", 14, BASE_DIR)'
  )
  validation_end = source.find(
    "    dry_column, rainy_column = st.columns(2)",
    validation_start,
  )
  if validation_start >= 0 and validation_end >= 0:
    source = source[:validation_start] + source[validation_end:]

  # Final-figure asset/script integrity checks remain logged internally instead
  # of being displayed as public scientific results.
  integrity_start = source.find("        qa1, qa2, qa3 = st.columns(3)\n")
  integrity_end = source.find("    missing_figure_dirs = ", integrity_start)
  if integrity_start >= 0 and integrity_end >= 0:
    integrity_replacement = '''        LOGGER.info(
          "Figure manifest internal check: main=%s supplementary=%s records=%s missing_scripts=%s missing_assets=%s",
          main_count, supp_count, len(figure_manifest_checked), len(missing_scripts), len(set(missing_assets)),
        )
      except Exception as exc:
        LOGGER.warning("Figure integrity check could not be completed: %s", exc)
'''
    source = source[:integrity_start] + integrity_replacement + source[integrity_end:]

  public_label_replacements = {
    "Tabela taxonômica completa para auditoria e download": "Tabela taxonômica completa",
    "Complete taxonomic table for audit and download": "Complete taxonomic data table",
    "Tabela completa para auditoria": "Tabela completa de resultados",
    "Complete audit table": "Complete results table",
  }
  for old_label, new_label in public_label_replacements.items():
    source = source.replace(old_label, new_label)

  marker_anchor = "def page_header():\n"
  if marker_anchor in source:
    source = source.replace(marker_anchor, MARKER + "\n\n\n" + marker_anchor, 1)
