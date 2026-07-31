from __future__ import annotations

"""Standard scientific-data panel and final Figure 4/5 display geometry."""


MARKER = "CANGAMETAG_SCIENTIFIC_DATA_PANEL_V3 = 1"


def _replace_function(text: str, start_marker: str, end_marker: str, replacement: str) -> str:
  start = text.find(start_marker)
  if start < 0:
    return text
  end = text.find(end_marker, start)
  if end < 0:
    return text
  return text[:start] + replacement.rstrip() + "\n\n" + text[end + 1:]


def _remove_public_call_containing(text: str, phrase: str) -> str:
  while phrase in text:
    position = text.find(phrase)
    starts = [
      text.rfind("st.info(txt(", 0, position),
      text.rfind("st.caption(txt(", 0, position),
      text.rfind("st.markdown(txt(", 0, position),
      text.rfind("st.warning(txt(", 0, position),
    ]
    start = max(starts)
    if start < 0:
      return text.replace(phrase, "")
    line_start = text.rfind("\n", 0, start) + 1
    cursor = text.find("\n", position)
    if cursor < 0:
      cursor = len(text)
    while cursor < len(text):
      next_end = text.find("\n", cursor + 1)
      if next_end < 0:
        next_end = len(text)
      if text[cursor + 1:next_end].strip() in {"))", ")))", ")"}:
        cursor = next_end
        break
      cursor = next_end
    text = text[:line_start] + text[cursor + 1:]
  return text


if MARKER not in source:
  import_anchor = "from src.current_taxonomy_display import harmonize_figure as harmonize_current_taxonomy_figure\n"
  imports = '''from src.article_frozen_taxonomy_panels import frozen_taxonomy_domain_data as scientific_frozen_taxonomy_domain_data
from src.article_official_ordination_statistics import official_ordination_inference as scientific_official_ordination_inference
'''
  if imports not in source and import_anchor in source:
    source = source.replace(import_anchor, import_anchor + imports, 1)

  for phrase in [
    "These panels do not recompute NMDS or RDA.",
    "Estes painéis não recalculam NMDS ou RDA.",
    "They read the matrices, coordinates, vectors and statistics frozen in ARTICLE_FINAL_ISME_SUBMISSION_Leandrov27-julho FINAL_SUBMISSION_FILES directly.",
    "Eles leem diretamente as matrizes, coordenadas, vetores e estatísticas congeladas em ARTICLE_FINAL_ISME_SUBMISSION_Leandrov27-julho FINAL_SUBMISSION_FILES.",
  ]:
    source = _remove_public_call_containing(source, phrase)

  panel_code = r'''def _scientific_paths(raw_value: object) -> list[str]:
  values = []
  for item in str(raw_value or "").replace("\n", ";").split(";"):
    value = item.strip()
    if not value or value.casefold().startswith("see script"):
      continue
    value = value.split("#", 1)[0].strip()
    if value and value not in values:
      values.append(value)
  return values


def _scientific_read_tables(paths: list[str]) -> list[tuple[str, pd.DataFrame]]:
  resolved: list[tuple[str, pd.DataFrame]] = []
  for relative_name in paths:
    candidate = BASE_DIR / relative_name
    if not candidate.exists() or not candidate.is_file():
      continue
    try:
      table = _public_scientific_result_table(_read_tabular_input_for_audit(candidate))
    except Exception:
      table = pd.DataFrame()
    if table is not None and not table.empty:
      resolved.append((relative_name, table))
  return resolved


def _scientific_render_tables(
  tables: list[tuple[str, pd.DataFrame]],
  chart_key: str,
  section: str,
) -> None:
  for index, (label, table) in enumerate(tables, start=1):
    if table is None or table.empty:
      continue
    st.markdown(f"**{label}**")
    _audit_table_block(
      table,
      txt("Tabela científica", "Scientific table"),
      f"{chart_key}_{section}_{index}",
    )


def _scientific_script_metadata(
  *,
  method: str,
  script: str,
  command: str,
  inputs: list[str],
  outputs: list[str],
) -> pd.DataFrame:
  return pd.DataFrame([
    {"Field": "Method", "Value": method or "—"},
    {"Field": "Script", "Value": script or "—"},
    {"Field": "Command", "Value": command or "—"},
    {"Field": "Input", "Value": "; ".join(inputs) if inputs else "—"},
    {"Field": "Output", "Value": "; ".join(outputs) if outputs else "—"},
  ])


def _scientific_default_command(script: str, instructions: str = "") -> str:
  explicit = str(instructions or "").strip()
  if explicit:
    return explicit
  paths = _scientific_paths(script)
  if not paths:
    return "streamlit run app.py"
  first = paths[0]
  if first.startswith("scripts/") and first.endswith(".py"):
    return f"python {first} --base-dir ."
  return "streamlit run app.py"


def _scientific_script_tab(
  *,
  chart_key: str,
  method: str,
  script: str,
  command: str,
  inputs: list[str],
  outputs: list[str],
) -> None:
  metadata = _scientific_script_metadata(
    method=method,
    script=script,
    command=command,
    inputs=inputs,
    outputs=outputs,
  )
  show_table(metadata, f"{chart_key}_script_metadata", height=250)
  if command:
    st.code(command, language="bash")
  available_scripts = [
    value for value in _scientific_paths(script)
    if (BASE_DIR / value).exists() and (BASE_DIR / value).is_file()
  ]
  if available_scripts:
    selected_script = st.selectbox(
      txt("Script exibido", "Displayed script"),
      available_scripts,
      key=f"{chart_key}_script_selector",
    )
    script_path = BASE_DIR / selected_script
    script_text = script_path.read_text(encoding="utf-8", errors="replace")
    st.code(script_text, language="python")
    st.download_button(
      txt("Baixar script", "Download script"),
      data=script_text.encode("utf-8"),
      file_name=script_path.name,
      mime="text/x-python",
      key=f"{chart_key}_script_download",
    )


def _scientific_figure45_tables(domain: str) -> dict[str, list[tuple[str, pd.DataFrame]]]:
  frozen = scientific_frozen_taxonomy_domain_data(domain)
  beta, rda = scientific_official_ordination_inference(domain, base_dir=BASE_DIR)
  profile = frozen["profile"].copy()
  nmds = frozen["nmds"].copy()
  sites = frozen["rda_sites"].copy()
  environmental = frozen["rda_environment_vectors"].copy()
  taxa = frozen["rda_taxon_vectors"].copy()
  return {
    "source": [("Genus relative-abundance matrix", profile)],
    "processed": [
      ("NMDS scores", nmds),
      ("RDA site scores", sites),
      ("RDA environmental vectors", environmental),
      ("RDA genus vectors", taxa),
    ],
    "output": [
      ("PERMANOVA and PERMDISP results", beta),
      ("RDA model and axis statistics", rda),
    ],
    "plotted": [
      ("Genus relative-abundance values", profile),
      ("NMDS plotted coordinates", nmds),
      ("RDA plotted site coordinates", sites),
      ("RDA plotted environmental vectors", environmental),
      ("RDA plotted genus vectors", taxa),
    ],
  }


def render_figure_audit_expander(
  fig, chart_key: str, *, input_table: pd.DataFrame | None = None,
  processed_table: pd.DataFrame | None = None, output_table: pd.DataFrame | None = None,
  method: str | None = None, input_source: str | None = None,
  script: str | None = None, instructions: str | None = None,
) -> None:
  """Show the same retractable scientific-data panel below every Plotly figure."""
  key_text = str(chart_key or "figure")
  domain = ""
  if "frozen_article_taxonomy_Bacteria" in key_text:
    domain = "Bacteria"
  elif "frozen_article_taxonomy_Archaea" in key_text:
    domain = "Archaea"

  if domain:
    groups = _scientific_figure45_tables(domain)
    script_value = "scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py"
    command_value = "python scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py --base-dir ."
    inputs = [
      f"data/article_frozen_taxonomy_{domain.casefold()}.json",
      f"reproducibility/ordination_reproducibility/tables/{domain}_NMDS_PERMANOVA_and_dispersion_tests.csv",
      f"reproducibility/ordination_reproducibility/tables/{domain}_RDA_model_statistics.csv",
    ]
    outputs = [
      f"outputs/final_publication_figures/{'Figure4_taxonomic_bacteria_genus_profiles' if domain == 'Bacteria' else 'Figure5_taxonomic_archaea_genus_profiles'}.*",
    ]
    method_value = "Bray-Curtis NMDS; PERMANOVA; PERMDISP; constrained RDA"
  else:
    plotted = _public_scientific_result_table(
      harmonize_current_taxonomy_table(_plotly_exact_value_table(fig), BASE_DIR)
    )
    source_table = _public_scientific_result_table(
      harmonize_current_taxonomy_table(input_table, BASE_DIR)
    )
    processed = _public_scientific_result_table(
      harmonize_current_taxonomy_table(processed_table, BASE_DIR)
    )
    output = _public_scientific_result_table(
      harmonize_current_taxonomy_table(output_table, BASE_DIR)
    )
    available = [table for table in [source_table, processed, output, plotted] if table is not None and not table.empty]
    fallback = available[0].copy() if available else pd.DataFrame([{"Figure": key_text}])
    source_table = source_table if source_table is not None and not source_table.empty else fallback.copy()
    processed = processed if processed is not None and not processed.empty else source_table.copy()
    output = output if output is not None and not output.empty else processed.copy()
    plotted = plotted if plotted is not None and not plotted.empty else output.copy()
    groups = {
      "source": [(str(input_source or "Input table"), source_table)],
      "processed": [("Processed table", processed)],
      "output": [("Output table", output)],
      "plotted": [("Exact plotted values", plotted)],
    }
    script_value = str(script or "app.py")
    command_value = _scientific_default_command(script_value, str(instructions or ""))
    inputs = _scientific_paths(input_source) or [str(input_source or "Input table supplied by the active module")]
    outputs = [key_text]
    method_value = str(method or "")

  with st.expander(
    txt("Dados científicos usados nesta figura", "Scientific data used in this figure"),
    expanded=False,
  ):
    tabs = st.tabs([
      txt("Fonte", "Source"),
      txt("Processada", "Processed"),
      txt("Resultado", "Output"),
      txt("Valores plotados", "Plotted values"),
      "Script",
    ])
    with tabs[0]:
      _scientific_render_tables(groups["source"], key_text, "source")
    with tabs[1]:
      _scientific_render_tables(groups["processed"], key_text, "processed")
    with tabs[2]:
      _scientific_render_tables(groups["output"], key_text, "output")
    with tabs[3]:
      _scientific_render_tables(groups["plotted"], key_text, "plotted")
    with tabs[4]:
      _scientific_script_tab(
        chart_key=key_text,
        method=method_value,
        script=script_value,
        command=command_value,
        inputs=inputs,
        outputs=outputs,
      )'''
  source = _replace_function(
    source,
    "def render_figure_audit_expander(",
    "\ndef render_plotly_downloadable(",
    panel_code,
  )

  static_code = r'''def _render_static_figure_audit(path: Path, title: str, key_prefix: str) -> None:
  """Show the standard retractable scientific-data panel below a static figure."""
  record = _static_figure_manifest_record(path)
  figure_id = str(record.get("Figure", "") or "").strip() or path.stem
  stem = path.stem
  domain = "Bacteria" if stem.startswith("Figure4_") else "Archaea" if stem.startswith("Figure5_") else ""

  if domain:
    groups = _scientific_figure45_tables(domain)
    script_value = "scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py"
    command_value = "python scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py --base-dir ."
    inputs = [
      f"data/article_frozen_taxonomy_{domain.casefold()}.json",
      f"reproducibility/ordination_reproducibility/tables/{domain}_NMDS_PERMANOVA_and_dispersion_tests.csv",
      f"reproducibility/ordination_reproducibility/tables/{domain}_RDA_model_statistics.csv",
    ]
    method_value = "Bray-Curtis NMDS; PERMANOVA; PERMDISP; constrained RDA"
  else:
    inputs = _scientific_paths(record.get("Inputs", record.get("Input", "")))
    source_tables = _scientific_read_tables(inputs)
    if not source_tables:
      source_tables = [("Input files", pd.DataFrame({
        "Input": inputs or [str(record.get("Inputs", record.get("Input", "—")))],
      }))]
    processed_paths = _scientific_paths(record.get("Intermediate_files", ""))
    processed_tables = _scientific_read_tables(processed_paths) or [(label, table.copy()) for label, table in source_tables]
    exact_source = BASE_DIR / "data" / "final_publication_derived" / f"{stem}_source.csv"
    plotted_tables = []
    if exact_source.exists():
      exact_table = _public_scientific_result_table(_read_tabular_input_for_audit(exact_source))
      if exact_table is not None and not exact_table.empty:
        plotted_tables.append((str(exact_source.relative_to(BASE_DIR)), exact_table))
    if not plotted_tables:
      plotted_tables = [(label, table.copy()) for label, table in processed_tables]
    output_files = [
      str(record.get(column, "")).strip()
      for column in ["PNG", "PDF", "SVG"]
      if str(record.get(column, "")).strip()
    ]
    output_table = pd.DataFrame({"Output": output_files or [path.name]})
    groups = {
      "source": source_tables,
      "processed": processed_tables,
      "output": [("Generated files", output_table)],
      "plotted": plotted_tables,
    }
    script_value = str(record.get("Script", "") or "")
    command_value = str(record.get("Command", "") or _scientific_default_command(script_value))
    method_value = str(
      record.get("Statistical_methods", "")
      or record.get("Method / description", "")
      or record.get("Description", "")
      or title
    )

  outputs = [path.name]
  with st.expander(
    txt("Dados científicos usados nesta figura", "Scientific data used in this figure"),
    expanded=False,
  ):
    tabs = st.tabs([
      txt("Fonte", "Source"),
      txt("Processada", "Processed"),
      txt("Resultado", "Output"),
      txt("Valores plotados", "Plotted values"),
      "Script",
    ])
    with tabs[0]:
      _scientific_render_tables(groups["source"], f"{key_prefix}_{stem}", "source")
    with tabs[1]:
      _scientific_render_tables(groups["processed"], f"{key_prefix}_{stem}", "processed")
    with tabs[2]:
      _scientific_render_tables(groups["output"], f"{key_prefix}_{stem}", "output")
    with tabs[3]:
      _scientific_render_tables(groups["plotted"], f"{key_prefix}_{stem}", "plotted")
    with tabs[4]:
      _scientific_script_tab(
        chart_key=f"{key_prefix}_{stem}_{safe_filename(figure_id)}",
        method=method_value,
        script=script_value,
        command=command_value,
        inputs=inputs,
        outputs=outputs,
      )'''
  source = _replace_function(
    source,
    "def _render_static_figure_audit(",
    "\ndef _display_static_publication_image(",
    static_code,
  )

  geometry_anchor = "page_handler = page_handlers.get(selected_page)"
  geometry_code = r'''
if "article_frozen_taxonomy_figure" in globals():
  _ORIGINAL_ARTICLE_FROZEN_TAXONOMY_WIDE_RDA = article_frozen_taxonomy_figure

  def article_frozen_taxonomy_figure(domain: str):
    figure, tables = _ORIGINAL_ARTICLE_FROZEN_TAXONOMY_WIDE_RDA(domain)
    figure.update_layout(
      width=1950,
      height=1710,
      margin={"l": 115, "r": 320, "t": 105, "b": 520},
    )
    axis = getattr(figure.layout, "xaxis4", None)
    current_range = list(getattr(axis, "range", []) or []) if axis is not None else []
    if len(current_range) == 2:
      left = float(current_range[0])
      right = float(current_range[1])
      span = max(right - left, 1e-9)
      figure.update_xaxes(
        range=[left - 0.08 * span, right + 0.30 * span],
        row=2,
        col=2,
      )
    meta = dict(figure.layout.meta) if isinstance(figure.layout.meta, dict) else {}
    meta.update({
      "rda_right_margin_px": 320,
      "rda_right_axis_extension_fraction": 0.30,
      "rda_labels_clipped": False,
      "figure_generator": "scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py",
    })
    figure.update_layout(meta=meta)
    return figure, tables
'''
  if geometry_anchor in source:
    source = source.replace(geometry_anchor, geometry_code + "\n\n" + geometry_anchor, 1)

  source += f"\n\n{MARKER}\n"
