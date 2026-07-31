from __future__ import annotations

"""Show one selectable KO heatmap scale instead of stacked raw/z-score plots."""

MARKER = "CANGAMETAG_KO_HEATMAP_SCALE_SELECTOR_V1 = 1"


if MARKER not in source:
  dispatch_anchor = "page_handler = page_handlers.get(selected_page)"
  runtime_layer = r'''
# Final KO heatmap presentation: raw and row-z-score are alternative views of
# the same rows and columns. Only the chosen view is rendered. The existing
# scientific-data panel therefore follows the selected figure and exposes its
# exact Source, Processed, Output, Plotted values and Script tabs.
_APP_RENDER_BEFORE_KO_SCALE_SELECTOR = render_plotly_downloadable
_FINAL_KO_SCALE_SELECTORS_RENDERED: set[str] = set()


def _final_ko_heatmap_pair_descriptor(chart_key: str, basename: str) -> tuple[str, str] | None:
  key_text = str(chart_key or "").strip()
  basename_text = str(basename or "").strip()
  identity = f"{key_text} {basename_text}".casefold()
  if "heatmap" not in identity:
    return None
  if "functional" in identity:
    # The functional-annotation module already has its own single-view scale
    # selector before figure construction.
    return None
  ko_tokens = (
    "all_ko",
    "ko_biomarker",
    "ko_marker",
    "biogeochemical",
    "iron_st8",
    "st8_iron",
    "iron_ko",
    "other_metals",
    "metatranscriptome_ko",
  )
  if not any(token in identity for token in ko_tokens):
    return None
  mode = "zscore" if any(token in identity for token in (
    "zscore", "z-score", "row_zscore", "row-z-score",
  )) else "raw"
  pair = key_text.casefold()
  pair = re.sub(r"row[_ -]?z[_ -]?score", "", pair)
  pair = re.sub(r"z[_ -]?score", "", pair)
  pair = re.sub(r"raw[_ -]?counts?", "", pair)
  pair = re.sub(r"absolute[_ -]?counts?", "", pair)
  pair = re.sub(r"(^|[_ -])raw($|[_ -])", r"\1\2", pair)
  pair = re.sub(r"[^a-z0-9]+", "_", pair).strip("_")
  return pair or "ko_heatmap", mode


def render_plotly_downloadable(fig, *args, **kwargs):
  chart_key = str(kwargs.get("key", args[0] if args else "") or "")
  basename = str(kwargs.get("basename", "") or "")
  descriptor = _final_ko_heatmap_pair_descriptor(chart_key, basename)
  if descriptor is None:
    return _APP_RENDER_BEFORE_KO_SCALE_SELECTOR(fig, *args, **kwargs)

  pair_key, mode = descriptor
  digest = hashlib.sha256(pair_key.encode("utf-8")).hexdigest()[:16]
  widget_key = f"ko_heatmap_scale_selector_{digest}"
  if pair_key not in _FINAL_KO_SCALE_SELECTORS_RENDERED:
    selected = st.radio(
      txt("Visualização do heatmap KO", "KO heatmap visualization"),
      ["Raw data", "Z-score"],
      horizontal=True,
      key=widget_key,
      help=txt(
        "As duas opções usam exatamente os mesmos KOs e amostras; somente a escala visual e os valores exibidos mudam.",
        "Both options use exactly the same KOs and samples; only the displayed scale and values change.",
      ),
    )
    _FINAL_KO_SCALE_SELECTORS_RENDERED.add(pair_key)
  else:
    selected = str(st.session_state.get(widget_key, "Raw data"))

  selected_mode = "zscore" if selected == "Z-score" else "raw"
  if mode != selected_mode:
    return None

  kwargs.setdefault(
    "audit_input_source",
    "tables/Supplementary_Table_8.xlsx — exact KO source matrix",
  )
  kwargs.setdefault(
    "audit_script",
    "src/supplementary_database.py; src/st8_biomarker_heatmap.py; scripts/generate_st8_final_figures.py",
  )
  if mode == "zscore":
    kwargs.setdefault(
      "audit_method",
      "Row z-score calculated independently for each KO from the exact displayed source matrix; no imputation and no replacement of source values.",
    )
  else:
    kwargs.setdefault(
      "audit_method",
      "Exact source values from the displayed KO matrix; zero is retained as measured absence and no value is imputed.",
    )
  return _APP_RENDER_BEFORE_KO_SCALE_SELECTOR(fig, *args, **kwargs)


'''
  if dispatch_anchor in source:
    source = source.replace(dispatch_anchor, runtime_layer + dispatch_anchor, 1)
  source += f"\n\n{MARKER}\n"
  compile(source, "app_core_after_ko_heatmap_scale_selector.py", "exec")
