from __future__ import annotations

"""Apply the selected interface language to every figure presentation element."""


MARKER = "CANGAMETAG_FULL_FIGURE_LANGUAGE_V3 = 1"

if MARKER not in source:
  future_anchor = "from __future__ import annotations\n"
  imports = '''from src.figure_language_localization import localize_plotly_figure as final_localize_plotly_figure
from src.figure_language_localization import translate_figure_text as final_translate_figure_text
'''
  if imports not in source and future_anchor in source:
    source = source.replace(future_anchor, future_anchor + imports, 1)

  replacements = {
    'tabs = st.tabs(["Bacteria — Figure 2", "Archaea — Figure 3"])': (
      'tabs = st.tabs([txt("Bacteria — Figura 2", "Bacteria — Figure 2"), '
      'txt("Archaea — Figura 3", "Archaea — Figure 3")])'
    ),
    'tabs = st.tabs(["Bacteria — Figure 4", "Archaea — Figure 5"])': (
      'tabs = st.tabs([txt("Bacteria — Figura 4", "Bacteria — Figure 4"), '
      'txt("Archaea — Figura 5", "Archaea — Figure 5")])'
    ),
    '"Language / Idioma",\n  ["Português", "English"],': (
      '"Idioma / Language",\n  ["Português", "English"],'
    ),
    'help="Choose the interface language. Data columns keep the original names from the supplementary tables.",': (
      'help=("Escolha o idioma da interface. Os nomes taxonômicos, identificadores e valores científicos não são alterados." '
      'if st.session_state.get("sidebar_language_idioma") == "Português" else '
      '"Choose the interface language. Taxonomic names, identifiers and scientific values are not changed."),'
    ),
    'key="taxonomy_final_rank")': (
      'key="taxonomy_final_rank",\n'
      '      format_func=lambda value: (final_translate_figure_text(value, "pt") if IS_PT else value),\n'
      '    )'
    ),
    'key="taxonomy_final_visualization")': (
      'key="taxonomy_final_visualization",\n'
      '      format_func=lambda value: (final_translate_figure_text(value, "pt") if IS_PT else value),\n'
      '    )'
    ),
    'selected_title = f"{domain} — {rank} — {visualization}"': (
      'rank_display = final_translate_figure_text(rank, "pt" if IS_PT else "en")\n'
      '  visualization_display = final_translate_figure_text(visualization, "pt" if IS_PT else "en")\n'
      '  selected_title = f"{domain} — {rank_display} — {visualization_display}"'
    ),
    'view_suffix = "individual samples" if view_mode.startswith("Individual") else "aggregated lake–season groups"': (
      'view_suffix = txt("amostras individuais", "individual samples") if view_mode.startswith("Individual") else '
      'txt("grupos agregados por lagoa–estação", "aggregated lake–season groups")'
    ),
  }
  for old, new in replacements.items():
    source = source.replace(old, new)

  anchor = "page_handler = page_handlers.get(selected_page)"
  layer = r'''
def _selected_figure_language() -> str:
  return "pt" if IS_PT else "en"


if "render_plotly_downloadable" in globals():
  _ORIGINAL_RENDER_PLOTLY_LANGUAGE = render_plotly_downloadable

  def render_plotly_downloadable(fig, *args, **kwargs):
    localized = final_localize_plotly_figure(
      fig,
      _selected_figure_language(),
    )
    return _ORIGINAL_RENDER_PLOTLY_LANGUAGE(localized, *args, **kwargs)


_ORIGINAL_ST_PLOTLY_CHART_LANGUAGE = st.plotly_chart


def _localized_st_plotly_chart(figure_or_data, *args, **kwargs):
  try:
    localized = final_localize_plotly_figure(
      figure_or_data,
      _selected_figure_language(),
    )
  except Exception:
    localized = figure_or_data
  return _ORIGINAL_ST_PLOTLY_CHART_LANGUAGE(localized, *args, **kwargs)


st.plotly_chart = _localized_st_plotly_chart


if "exact_article_phylum_interactive" in globals():
  _ORIGINAL_EXACT_ARTICLE_PHYLUM_INTERACTIVE_LANGUAGE = exact_article_phylum_interactive

  def exact_article_phylum_interactive(domain: str):
    try:
      return _ORIGINAL_EXACT_ARTICLE_PHYLUM_INTERACTIVE_LANGUAGE(
        domain,
        language=_selected_figure_language(),
      )
    except TypeError:
      figure, table, svg = _ORIGINAL_EXACT_ARTICLE_PHYLUM_INTERACTIVE_LANGUAGE(domain)
      return final_localize_plotly_figure(
        figure,
        _selected_figure_language(),
      ), table, svg


if "article_frozen_taxonomy_figure" in globals():
  _ORIGINAL_ARTICLE_FROZEN_TAXONOMY_LANGUAGE = article_frozen_taxonomy_figure

  def article_frozen_taxonomy_figure(domain: str):
    figure, tables = _ORIGINAL_ARTICLE_FROZEN_TAXONOMY_LANGUAGE(domain)
    return final_localize_plotly_figure(
      figure,
      _selected_figure_language(),
    ), tables


if "_scientific_render_tables" in globals():
  _ORIGINAL_SCIENTIFIC_RENDER_TABLES_LANGUAGE = _scientific_render_tables

  def _scientific_render_tables(tables, chart_key: str, section: str) -> None:
    localized_tables = [
      (
        final_translate_figure_text(label, _selected_figure_language()),
        table,
      )
      for label, table in tables
    ]
    return _ORIGINAL_SCIENTIFIC_RENDER_TABLES_LANGUAGE(
      localized_tables,
      chart_key,
      section,
    )


if "_scientific_script_metadata" in globals():
  _ORIGINAL_SCIENTIFIC_SCRIPT_METADATA_LANGUAGE = _scientific_script_metadata

  def _scientific_script_metadata(
    *,
    method: str,
    script: str,
    command: str,
    inputs: list[str],
    outputs: list[str],
  ) -> pd.DataFrame:
    table = _ORIGINAL_SCIENTIFIC_SCRIPT_METADATA_LANGUAGE(
      method=method,
      script=script,
      command=command,
      inputs=inputs,
      outputs=outputs,
    )
    if not IS_PT or table is None or table.empty:
      return table
    localized = table.copy()
    if "Field" in localized.columns:
      localized["Field"] = localized["Field"].map(
        lambda value: final_translate_figure_text(value, "pt")
      )
      method_rows = localized["Field"].astype(str).eq("Método")
      if "Value" in localized.columns:
        localized.loc[method_rows, "Value"] = localized.loc[method_rows, "Value"].map(
          lambda value: final_translate_figure_text(value, "pt")
        )
      localized = localized.rename(columns={"Field": "Campo", "Value": "Valor"})
    return localized


if "_static_figure_manifest_record" in globals():
  _ORIGINAL_STATIC_FIGURE_MANIFEST_LANGUAGE = _static_figure_manifest_record

  def _static_figure_manifest_record(path: Path) -> dict:
    record = dict(_ORIGINAL_STATIC_FIGURE_MANIFEST_LANGUAGE(path) or {})
    if IS_PT:
      for field in [
        "Description", "Title", "Purpose", "Statistical_methods", "Notes",
        "Usage", "Panel", "Data_origin", "Parameters", "Filters",
      ]:
        if field in record:
          record[field] = final_translate_figure_text(record[field], "pt")
    return record
'''
  if anchor in source:
    source = source.replace(anchor, layer + "\n\n" + anchor, 1)

  source += f"\n\n{MARKER}\n"
