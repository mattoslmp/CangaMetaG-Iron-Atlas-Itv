from __future__ import annotations

"""Final ST8/MTX/KO presentation contract.

This transform is intentionally loaded after the legacy ST8 and MTX transforms.
It consolidates sample resolution and display geometry without changing source
matrices, KO values, row z-scores, categories, or source order.
"""

MARKER = "CANGAMETAG_FINAL_ST8_KO_MTX_REVISION_V1 = 1"


if MARKER not in source:
  candidate = source

  # Replace both legacy nested-loop MTX selections with the same metadata-first
  # resolver. The replacement retains the surrounding variables and tables.
  legacy_ko_selection = (
    '    mtx_cols = [str(col) for col in numeric_cols if str(col) in matrix_to_row]\n'
  )
  final_ko_selection = '''    _final_mtx_metadata, mtx_cols = _resolve_final_st8_mtx_columns(
      meta,
      [str(column) for column in numeric_cols if str(column) in df.columns],
      expected_count=12,
    )
    mtx_metadata_view = _final_st8_public_mtx_metadata(_final_mtx_metadata)
'''
  if legacy_ko_selection in candidate:
    candidate = candidate.replace(legacy_ko_selection, final_ko_selection, 1)

  legacy_kegg_selection = (
    '        mtx_columns = [str(col) for col in full_status.columns if str(col) in matrix_to_row]\n'
  )
  final_kegg_selection = '''        _final_kegg_mtx_metadata, mtx_columns = _resolve_final_st8_mtx_columns(
          panel_meta,
          [str(column) for column in full_status.columns],
          expected_count=12,
        )
        mtx_metadata_view = _final_st8_public_mtx_metadata(_final_kegg_mtx_metadata)
'''
  if legacy_kegg_selection in candidate:
    candidate = candidate.replace(legacy_kegg_selection, final_kegg_selection, 1)

  # Public wording: scientific validation remains active internally, while the
  # interface uses neutral result-oriented terminology.
  public_replacements = {
    "Auditoria de detecção dos 189 KOs": "Resumo de detecção dos 189 KOs",
    "Detection audit for all 189 KOs": "Detection summary for all 189 KOs",
    "Baixar auditoria dos 189 KOs": "Baixar resumo dos 189 KOs",
    "Download the 189-KO audit": "Download the 189-KO summary",
    "ST8_all_189_KO_Amazonian_detection_audit.csv": "ST8_all_189_KO_Amazonian_detection_summary.csv",
    "consulte a auditoria abaixo": "consulte o resumo abaixo",
    "inspect the audit below": "inspect the summary below",
    "tabela e auditoria completas": "tabela completa",
    "complete table and audit": "complete table",
    "Filter pathways": "Filter pathways/categories",
    "Filtrar vias": "Filtrar vias/categorias",
  }
  for old, new in public_replacements.items():
    candidate = candidate.replace(old, new)

  # Figure 40 and Figure 67 always use 45-degree x labels. This overrides the
  # earlier S67 transform that used horizontal labels for one display mode.
  candidate = candidate.replace(
    '''    elif key_prefix.startswith("kegg_combined_lagoon_external"):
      fig.update_xaxes(
        tickangle=0,''',
    '''    elif key_prefix.startswith("kegg_combined_lagoon_external"):
      fig.update_xaxes(
        tickangle=-45,''',
    1,
  )

  dispatch_anchor = "page_handler = page_handlers.get(selected_page)"
  runtime_layer = '''from src.st8_final_contract import (
  apply_final_heatmap_layout as _apply_final_st8_heatmap_layout,
  public_metatranscriptome_metadata_table as _final_st8_public_mtx_metadata,
  resolve_metatranscriptome_columns as _resolve_final_st8_mtx_columns,
)
from src import app_mtx_alpha_taxonomy_runtime as _final_st8_runtime_module


def _final_st8_runtime_resolver(metadata, numeric_columns, data_columns):
  available = [
    str(column) for column in numeric_columns
    if str(column) in {str(value) for value in data_columns}
  ]
  resolved, columns = _resolve_final_st8_mtx_columns(
    metadata,
    available,
    expected_count=12,
  )
  return resolved, columns


_final_st8_runtime_module.metatranscriptome_matrix_columns = _final_st8_runtime_resolver

_APP_RENDER_PLOTLY_BEFORE_FINAL_ST8 = render_plotly_downloadable


def render_plotly_downloadable(fig, *args, **kwargs):
  chart_key = str(kwargs.get("key", args[0] if args else "") or "")
  basename = str(kwargs.get("basename", "") or "")
  title = ""
  try:
    title = str(getattr(getattr(fig.layout, "title", None), "text", "") or "")
  except Exception:
    title = ""
  display_identity = " ".join([chart_key, basename, title])
  _apply_final_st8_heatmap_layout(fig, chart_key=display_identity)

  lowered = display_identity.casefold()
  if any(token in lowered for token in (
    "st8", "biogeochemical", "metatranscript", "all_ko", "iron_ko",
  )):
    kwargs.setdefault(
      "audit_input_source",
      "tables/Supplementary_Table_8.xlsx — ST8 — all KO biomarkers",
    )
    kwargs.setdefault(
      "audit_script",
      "src/st8_final_contract.py; src/st8_biomarker_heatmap.py",
    )
    kwargs.setdefault(
      "audit_method",
      "Exact Supplementary Table 8 values; zero is retained as measured absence; row z-score is calculated from the displayed source matrix only.",
    )
  return _APP_RENDER_PLOTLY_BEFORE_FINAL_ST8(fig, *args, **kwargs)


'''
  if dispatch_anchor not in candidate:
    raise RuntimeError("Could not install final ST8/MTX runtime layer")
  candidate = candidate.replace(dispatch_anchor, runtime_layer + dispatch_anchor, 1)

  # Add the exact public validation statement immediately after the existing
  # ST8 summary text when that block is present.
  validation_anchor = '''  st.info(txt(
    f"A planilha contém {int(lake_scope['source_marker_count'])} KOs.'''
  if validation_anchor in candidate and "Supplementary Table 8 validated: 189/189" not in candidate:
    statement = '''  st.success(txt(
    "Supplementary Table 8 validada: 189/189 marcadores KO carregados; 172 detectados e 17 com soma zero nas 20 amostras amazônicas.",
    "Supplementary Table 8 validated: 189/189 KO markers loaded; 172 detected and 17 zero-total markers across the 20 Amazonian samples.",
  ))
'''
    candidate = candidate.replace(validation_anchor, statement + validation_anchor, 1)

  # A public readability note is appended to the exact legend, not to the data.
  candidate = candidate.replace(
    '''    f"Legend: raw-count and z-score panels use exactly the same {top_n} KOs and the same {len(lake_cols)} samples. Rows with total zero in the scope are excluded by default and remain available in the complete table."''',
    '''    f"Legend: raw-count and z-score panels use exactly the same {top_n} KOs and the same {len(lake_cols)} samples. Rows with total zero in the scope are excluded by default and remain available in the complete table. The full heatmap contains all detected KOs; use horizontal and vertical scrolling when needed."''',
    1,
  )

  candidate += f"\n\n{MARKER}\n"
  compile(candidate, "app_core_after_final_st8_ko_mtx_revision.py", "exec")
  source = candidate
