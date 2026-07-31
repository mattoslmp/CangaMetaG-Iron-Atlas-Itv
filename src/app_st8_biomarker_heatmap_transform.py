from __future__ import annotations

"""Final app transform for Supplementary Table 8 KO heatmaps."""

MARKER = "CANGAMETAG_ST8_DETECTED_HEATMAP_V1 = 1"

if MARKER not in source:
  future_anchor = "from __future__ import annotations\n"
  imports = '''from src.st8_biomarker_heatmap import (
  filter_detected_markers as filter_detected_st8_markers,
  validate_st8_all_ko_table,
)
'''
  if imports not in source:
    source = source.replace(future_anchor, future_anchor + imports, 1)

  # Every ST8 heatmap must omit rows with zero total in the exact selected
  # columns unless the calling panel explicitly opted into displaying them.
  site_anchor = "def site_access_gate"
  wrapper = r'''
_APP_ORIGINAL_ST8_HEATMAP_FIGURE = heatmap_figure


def heatmap_figure(frame, numeric_cols, label_col, title, top_n=30, zscore_rows=False, x_label_map=None):
  title_text = str(title or "")
  is_st8 = (
    "supplementary table 8" in title_text.casefold()
    or "st8" in title_text.casefold()
  )
  if not is_st8 or frame is None or frame.empty:
    return _APP_ORIGINAL_ST8_HEATMAP_FIGURE(
      frame, numeric_cols, label_col, title,
      top_n=top_n, zscore_rows=zscore_rows, x_label_map=x_label_map,
    )
  include_undetected = bool(
    getattr(frame, "attrs", {}).get("st8_include_undetected", False)
  )
  prepared, summary, row_audit = filter_detected_st8_markers(
    frame,
    numeric_cols,
    include_undetected=include_undetected,
    scope_name=title_text,
  )
  effective_top = min(max(1, int(top_n)), max(1, len(prepared)))
  figure = _APP_ORIGINAL_ST8_HEATMAP_FIGURE(
    prepared, numeric_cols, label_col, title,
    top_n=effective_top, zscore_rows=zscore_rows, x_label_map=x_label_map,
  )
  current_meta = getattr(figure.layout, "meta", None)
  meta = dict(current_meta) if isinstance(current_meta, dict) else {}
  summary_row = summary.iloc[0].to_dict() if not summary.empty else {}
  meta.update({
    "st8_source_marker_count": int(summary_row.get("source_marker_count", len(frame))),
    "st8_detected_marker_count": int(summary_row.get("detected_marker_count", len(prepared))),
    "st8_undetected_marker_count": int(summary_row.get("undetected_marker_count", 0)),
    "st8_include_undetected": include_undetected,
    "st8_zero_rows_filtered_before_ranking": not include_undetected,
    "st8_values_imputed": False,
    "st8_audit_script": "src/st8_biomarker_heatmap.py",
  })
  figure.update_layout(meta=meta)
  return figure
'''
  if site_anchor in source and "_APP_ORIGINAL_ST8_HEATMAP_FIGURE" not in source:
    source = source.replace(site_anchor, wrapper + "\n\n" + site_anchor, 1)

  old_lake_anchor = '''  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  all_metab = sorted(counts["Metabolism"].dropna().astype(str).unique())'''
  new_lake_anchor = '''  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  st8_integrity = validate_st8_all_ko_table(counts, numeric_cols)
  _, lake_scope_summary, lake_scope_audit = filter_detected_st8_markers(
    counts,
    lake_cols,
    include_undetected=False,
    scope_name="20 Amazonian lake samples",
  )
  lake_scope = lake_scope_summary.iloc[0]
  audit_metrics = st.columns(4)
  audit_metrics[0].metric(txt("KOs na fonte", "Source KOs"), int(lake_scope["source_marker_count"]))
  audit_metrics[1].metric(txt("KOs detectados", "Detected KOs"), int(lake_scope["detected_marker_count"]))
  audit_metrics[2].metric(txt("Soma zero", "Zero-total KOs"), int(lake_scope["undetected_marker_count"]))
  audit_metrics[3].metric(txt("Amostras", "Samples"), int(lake_scope["selected_sample_count"]))
  if str(st8_integrity.iloc[0].get("status", "FAIL")) != "PASS":
    st.error(txt(
      "A estrutura da Supplementary Table 8 não corresponde ao contrato esperado; consulte a auditoria abaixo.",
      "The Supplementary Table 8 structure does not match the expected contract; inspect the audit below.",
    ))
  st.info(txt(
    f"A planilha contém {int(lake_scope['source_marker_count'])} KOs. Nas 20 amostras amazônicas, {int(lake_scope['detected_marker_count'])} têm pelo menos uma contagem positiva e {int(lake_scope['undetected_marker_count'])} têm soma zero. O heatmap mostra por padrão apenas os KOs detectados; nenhum valor é preenchido ou inventado.",
    f"The worksheet contains {int(lake_scope['source_marker_count'])} KOs. Across the 20 Amazonian samples, {int(lake_scope['detected_marker_count'])} have at least one positive count and {int(lake_scope['undetected_marker_count'])} have total zero. The heatmap displays detected KOs by default; no value is filled or invented.",
  ))
  include_undetected_st8 = st.checkbox(
    txt(
      "Incluir no heatmap os KOs não detectados no escopo (linhas totalmente zero)",
      "Include KOs not detected in the scope (all-zero rows) in the heatmap",
    ),
    value=False,
    key="st8_include_undetected_zero_rows",
  )
  with st.expander(txt("Auditoria de detecção dos 189 KOs", "Detection audit for all 189 KOs"), expanded=False):
    show_table(st8_integrity, "st8_ko_integrity_audit", height=160)
    show_table(lake_scope_audit, "st8_lake_scope_detection_audit", height=520)
    csv_button(
      lake_scope_audit,
      "ST8_all_189_KO_Amazonian_detection_audit.csv",
      txt("Baixar auditoria dos 189 KOs", "Download the 189-KO audit"),
    )
  all_metab = sorted(counts["Metabolism"].dropna().astype(str).unique())'''
  if old_lake_anchor in source:
    source = source.replace(old_lake_anchor, new_lake_anchor, 1)

  source = source.replace(
    'txt(f"Mostrar o painel completo com todos os {len(counts)} KOs", f"Show the complete panel with all {len(counts)} KOs")',
    'txt(f"Usar o catálogo-fonte completo com {len(counts)} KOs", f"Use the complete source catalogue with {len(counts)} KOs")',
    1,
  )

  old_counts_f = '''  counts_f = counts.copy() if complete_ko_panel else counts[counts["Metabolism"].astype(str).isin(selected_metab)].copy()'''
  new_counts_f = '''  counts_selected_source = (
    counts.copy()
    if complete_ko_panel
    else counts[counts["Metabolism"].astype(str).isin(selected_metab)].copy()
  )
  counts_f, active_scope_summary, active_scope_audit = filter_detected_st8_markers(
    counts_selected_source,
    lake_cols,
    include_undetected=include_undetected_st8,
    scope_name="20 Amazonian lake samples",
  )
  counts_f.attrs["st8_include_undetected"] = bool(include_undetected_st8)'''
  if old_counts_f in source:
    source = source.replace(old_counts_f, new_counts_f, 1)

  old_legend = '''    f"Legenda: raw count e z-score usam exatamente os mesmos {top_n} KOs e as mesmas {len(lake_cols)} amostras. Todos os {len(counts_f)} KOs são mostrados por padrão; o filtro Top N é opcional.",
    f"Legend: raw-count and z-score panels use exactly the same {top_n} KOs and the same {len(lake_cols)} samples. All {len(counts_f)} KOs are displayed by default; the Top-N filter is optional."'''
  new_legend = '''    f"Legenda: raw count e z-score usam exatamente os mesmos {top_n} KOs e as mesmas {len(lake_cols)} amostras. Linhas com soma zero no escopo são excluídas por padrão e permanecem disponíveis na tabela e auditoria completas.",
    f"Legend: raw-count and z-score panels use exactly the same {top_n} KOs and the same {len(lake_cols)} samples. Rows with total zero in the scope are excluded by default and remain available in the complete table and audit."'''
  if old_legend in source:
    source = source.replace(old_legend, new_legend, 1)

  old_lake_table = '''    lake_table = counts_f[[c for c in ["KO", "Metabolism", "KO description"] + lake_cols if c in counts_f.columns]]'''
  new_lake_table = '''    lake_table = counts[[c for c in ["KO", "Metabolism", "KO description"] + lake_cols if c in counts.columns]].copy()
    lake_table = lake_table.merge(
      lake_scope_audit[[
        "KO", "scope_total_count", "scope_detected_sample_count",
        "scope_detection_fraction", "heatmap_status", "included_by_default",
      ]],
      on="KO",
      how="left",
      validate="one_to_one",
    )'''
  if old_lake_table in source:
    source = source.replace(old_lake_table, new_lake_table, 1)

  # The comparison against external environments must begin from the complete
  # category-filtered source, not from the lake-detected subset. Its own exact
  # selected columns are filtered inside the heatmap wrapper above.
  source = source.replace(
    '''    counts_f, numeric_cols, "KO_pathway_label", "All biogeochemical-cycle KO biomarkers", "bio_st8_environment",''',
    '''    counts_selected_source, numeric_cols, "KO_pathway_label", "All biogeochemical-cycle KO biomarkers", "bio_st8_environment",''',
    1,
  )

  source += f"\n\n{MARKER}\n"
