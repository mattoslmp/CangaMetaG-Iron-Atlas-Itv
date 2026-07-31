from __future__ import annotations

"""Apply one Raw data / Z-score selector consistently to every heatmap."""

MARKER = "CANGAMETAG_ALL_HEATMAP_SCALE_SELECTOR_V3 = 1"


if MARKER not in source:
  # Heatmaps that already build only one figure keep their existing scientific
  # calculation. Only the visible control is standardised.
  source = source.replace(
    '[txt("Contagem absoluta", "Absolute counts"), txt("Z-score por função", "Row z-score")]',
    '["Raw data", "Z-score"]',
  )
  source = source.replace(
    'zscore_rows = view_mode == txt("Z-score por função", "Row z-score")',
    'zscore_rows = view_mode == "Z-score"',
  )
  source = source.replace(
    'zscore = st.checkbox(txt("Z-score por táxon no heatmap", "Row z-score in heatmap"), value=False, key=f"taxonomy_z_{level}_{hmode}")',
    'heatmap_scale = st.radio(txt("Visualização do heatmap", "Heatmap visualization"), ["Raw data", "Z-score"], horizontal=True, key=f"taxonomy_z_{level}_{hmode}")\n    zscore = heatmap_scale == "Z-score"',
  )
  source = source.replace(
    'zscore = st.checkbox("Z-score por linha", value=False, key=f"{key_prefix}_z")',
    'heatmap_scale = st.radio(txt("Visualização do heatmap", "Heatmap visualization"), ["Raw data", "Z-score"], horizontal=True, key=f"{key_prefix}_z")\n    zscore = heatmap_scale == "Z-score"',
  )

  # Keep public captions consistent with the new single-view control.
  caption_replacements = {
    "raw count e z-score usam exatamente": "as opções Raw data e Z-score usam exatamente",
    "raw-count and z-score panels use exactly": "the Raw data and Z-score options use exactly",
    "no painel raw": "na opção Raw data",
    "no painel z-score": "na opção Z-score",
    "in the raw panel": "in the Raw data option",
    "in the z-score panel": "in the Z-score option",
  }
  for old, new in caption_replacements.items():
    source = source.replace(old, new)

  # Add an explicit description inside the Plotted values tab. The description
  # is attached to the selected figure by the runtime wrapper below.
  plotted_anchor = '    with tabs[3]:\n      _scientific_render_tables(groups["plotted"], key_text, "plotted")'
  plotted_replacement = '''    with tabs[3]:
      figure_meta = getattr(fig.layout, "meta", None)
      figure_meta = figure_meta if isinstance(figure_meta, dict) else {}
      plotted_description = str(figure_meta.get("scientific_plotted_values_description", "") or "").strip()
      if plotted_description:
        st.markdown(f"**{txt('Descrição', 'Description')}:** {plotted_description}")
      _scientific_render_tables(groups["plotted"], key_text, "plotted")'''
  if plotted_anchor in source:
    source = source.replace(plotted_anchor, plotted_replacement, 1)

  dispatch_anchor = "page_handler = page_handlers.get(selected_page)"
  runtime_layer = r'''
# Final heatmap presentation layer. Every explicitly generated raw/z-score pair
# shares one selector and only the selected member is rendered. Heatmaps that
# already create one figure from an upstream selector are left untouched.
_APP_RENDER_BEFORE_ALL_HEATMAP_SELECTOR = render_plotly_downloadable
_APP_SCIENTIFIC_PANEL_BEFORE_ALL_HEATMAP_SELECTOR = globals().get("render_figure_audit_expander")
_FINAL_ALL_HEATMAP_SELECTORS_RENDERED: set[str] = set()


def _final_is_plotly_heatmap(fig) -> bool:
  try:
    return any(
      str(getattr(trace, "type", "") or "").casefold() in {"heatmap", "image"}
      for trace in list(getattr(fig, "data", []) or [])
    )
  except Exception:
    return False


def _final_heatmap_pair_descriptor(
  fig,
  chart_key: str,
  basename: str,
) -> tuple[str, str] | None:
  if not _final_is_plotly_heatmap(fig):
    return None
  key_text = str(chart_key or "").strip()
  basename_text = str(basename or "").strip()
  identity = f"{key_text} {basename_text}".casefold()

  z_tokens = (
    "zscore", "z-score", "row_zscore", "row-z-score", "row z-score",
    "row_z_score", "row-z_score",
  )
  raw_tokens = (
    "raw_counts", "raw-counts", "raw counts", "raw_count", "raw-count",
    "raw data", "raw_values", "raw-values", "raw values", "raw_matrix",
    "absolute_counts", "absolute-counts", "absolute counts",
  )
  if any(token in identity for token in z_tokens):
    mode = "zscore"
  elif any(token in identity for token in raw_tokens) or re.search(r"(^|[_-])raw($|[_-])", key_text.casefold()):
    mode = "raw"
  else:
    # No explicit pair marker means that the heatmap is already controlled by
    # its own single-view selector. Do not create a duplicate control.
    return None

  pair = key_text.casefold() or basename_text.casefold()
  pair = re.sub(r"row[_ -]?z[_ -]?score", "", pair)
  pair = re.sub(r"z[_ -]?score", "", pair)
  pair = re.sub(r"absolute[_ -]?counts?", "", pair)
  pair = re.sub(r"raw[_ -]?(?:counts?|values?|matrix|data)?", "", pair)
  pair = re.sub(r"[^a-z0-9]+", "_", pair).strip("_")
  return pair or "heatmap", mode


def _final_heatmap_scientific_context(identity: str, mode: str) -> dict[str, str]:
  key = str(identity or "").casefold()
  if "environmental_heatmap" in key:
    source = "Environmental matrix assembled from the exact coordinates/samples and packaged climate, Sentinel, soil and land-cover variables selected in the Environmental–Metagenomic Integrator."
    script = "app_core.py:environmental_integrator_tab"
    z_method = "Column-wise z-score: for each environmental variable, z=(value−column mean)/column population standard deviation across the displayed samples; constant columns are retained as zero after transformation."
  elif "taxonomy" in key:
    source = "tables/Supplementary_Table_1.xlsx and the packaged CDS OTU/taxonomy tables used by the selected taxonomic level."
    script = "src/supplementary_database.py:taxonomy_heatmap; app_core.py:taxonomy_tab"
    z_method = "Row-wise z-score calculated independently for each displayed taxon across the unchanged sample columns."
  elif "functional" in key:
    source = "tables/Supplementary_Table_6.xlsx and/or tables/Supplementary_Table_8.xlsx, using the exact selected KO, EC-number or PFAM matrix."
    script = "src/functional_annotations.py:functional_annotation_heatmap; app_core.py:functional_annotations_tab"
    z_method = "Row-wise z-score calculated independently for each selected function across the unchanged sample columns."
  elif "kegg" in key or "module" in key:
    source = "Packaged KEMET/KEGG module status or completeness matrices in outputs/kegg_modules and their source reportKMC files."
    script = "src/kegg_modules.py; app_core.py:kegg_modules_tab"
    z_method = "Row-wise z-score calculated for each KEGG module across the unchanged MAG or metagenome columns when the module view provides a transformed scale."
  elif any(token in key for token in (
    "st8", "all_ko", "ko_biomarker", "ko_marker", "biogeochemical",
    "iron_ko", "other_metals", "metatranscriptome",
  )):
    source = "tables/Supplementary_Table_8.xlsx — exact selected sheet, KO rows and environmental/metatranscriptome columns used by this heatmap."
    script = "src/supplementary_database.py:heatmap_figure; app_core.py:render_st8_heatmap_scope_controls; scripts/generate_st8_final_figures.py"
    z_method = "Per-KO row z-score calculated across the exact displayed columns; the KO order, sample order and active scientific filters are unchanged, with no imputation or replacement of source values."
  else:
    source = "Exact packaged matrix supplied by the active application module and preserved in the scientific-data tables below this heatmap."
    script = "app_core.py and the module-specific script displayed in the Script tab"
    z_method = "Row-wise z-score calculated from the exact displayed matrix only when that transformed counterpart is explicitly generated by the same module."

  if mode == "zscore":
    method = z_method
  else:
    method = "Exact non-standardized values supplied by the active module after its existing scientific filters; row and column order are unchanged and no values are imputed."
  return {"source": source, "script": script, "method": method}


def _final_attach_heatmap_metadata(fig, *, basename: str, mode: str, method: str):
  try:
    layout_meta = getattr(fig.layout, "meta", None)
    layout_meta = dict(layout_meta) if isinstance(layout_meta, dict) else {}
    clean_base = safe_filename(basename or "heatmap")
    layout_meta.update({
      "scientific_heatmap_view": "Z-score" if mode == "zscore" else "Raw data",
      "scientific_plotted_values_description": method,
      "scientific_output_files": [
        f"{clean_base}.png",
        f"{clean_base}.pdf",
        f"{clean_base}.svg",
        f"{clean_base}.html",
      ],
    })
    fig.update_layout(meta=layout_meta)
  except Exception:
    pass
  return fig


def render_plotly_downloadable(fig, *args, **kwargs):
  chart_key = str(kwargs.get("key", args[0] if args else "") or "")
  basename = str(kwargs.get("basename", "") or chart_key)
  descriptor = _final_heatmap_pair_descriptor(fig, chart_key, basename)
  if descriptor is None:
    return _APP_RENDER_BEFORE_ALL_HEATMAP_SELECTOR(fig, *args, **kwargs)

  pair_key, mode = descriptor
  digest = hashlib.sha256(pair_key.encode("utf-8")).hexdigest()[:16]
  widget_key = f"all_heatmap_scale_selector_{digest}"
  if pair_key not in _FINAL_ALL_HEATMAP_SELECTORS_RENDERED:
    selected = st.radio(
      txt("Visualização do heatmap", "Heatmap visualization"),
      ["Raw data", "Z-score"],
      horizontal=True,
      key=widget_key,
      help=txt(
        "As duas opções preservam exatamente as mesmas linhas, colunas, filtros e ordem; somente a escala já produzida pelo módulo é alternada.",
        "Both options preserve exactly the same rows, columns, filters and order; only the scale already produced by the module is switched.",
      ),
    )
    _FINAL_ALL_HEATMAP_SELECTORS_RENDERED.add(pair_key)
  else:
    selected = str(st.session_state.get(widget_key, "Raw data"))

  selected_mode = "zscore" if selected == "Z-score" else "raw"
  if mode != selected_mode:
    return None

  context = _final_heatmap_scientific_context(pair_key, mode)
  kwargs.setdefault("audit_input_source", context["source"])
  kwargs.setdefault("audit_script", context["script"])
  kwargs.setdefault("audit_method", context["method"])
  fig = _final_attach_heatmap_metadata(
    fig,
    basename=basename,
    mode=mode,
    method=str(kwargs.get("audit_method") or context["method"]),
  )
  return _APP_RENDER_BEFORE_ALL_HEATMAP_SELECTOR(fig, *args, **kwargs)


if _APP_SCIENTIFIC_PANEL_BEFORE_ALL_HEATMAP_SELECTOR is not None:
  def render_figure_audit_expander(
    fig, chart_key: str, *, input_table=None, processed_table=None,
    output_table=None, method=None, input_source=None, script=None,
    instructions=None,
  ) -> None:
    if _final_is_plotly_heatmap(fig):
      layout_meta = getattr(fig.layout, "meta", None)
      layout_meta = layout_meta if isinstance(layout_meta, dict) else {}
      output_files = list(layout_meta.get("scientific_output_files", []) or [])
      if output_files:
        output_table = pd.DataFrame({
          "Output": output_files,
          "View": [str(layout_meta.get("scientific_heatmap_view", ""))] * len(output_files),
        })
      plotted_description = str(layout_meta.get("scientific_plotted_values_description", "") or "").strip()
      if plotted_description and not method:
        method = plotted_description
    return _APP_SCIENTIFIC_PANEL_BEFORE_ALL_HEATMAP_SELECTOR(
      fig,
      chart_key,
      input_table=input_table,
      processed_table=processed_table,
      output_table=output_table,
      method=method,
      input_source=input_source,
      script=script,
      instructions=instructions,
    )


'''
  if dispatch_anchor not in source:
    raise RuntimeError("Could not install the final all-heatmap selector before page dispatch")
  source = source.replace(dispatch_anchor, runtime_layer + dispatch_anchor, 1)
  source += f"\n\n{MARKER}\n"
  compile(source, "app_core_after_all_heatmap_scale_selector.py", "exec")
