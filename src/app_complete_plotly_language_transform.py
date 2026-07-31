from __future__ import annotations

"""Apply complete Portuguese localization to every Plotly rendering route."""


MARKER = "CANGAMETAG_COMPLETE_PLOTLY_LANGUAGE_V1 = 1"

if MARKER not in source:
  future_anchor = "from __future__ import annotations\n"
  imports = '''from src.figure_language_localization_complete import localize_plotly_figure as complete_localize_plotly_figure
'''
  if imports not in source and future_anchor in source:
    source = source.replace(future_anchor, future_anchor + imports, 1)

  anchor = "page_handler = page_handlers.get(selected_page)"
  layer = r'''
def _complete_selected_figure_language() -> str:
  return "pt" if IS_PT else "en"


if "render_plotly_downloadable" in globals():
  _ORIGINAL_RENDER_PLOTLY_COMPLETE_LANGUAGE = render_plotly_downloadable

  def render_plotly_downloadable(fig, *args, **kwargs):
    localized = complete_localize_plotly_figure(
      fig,
      _complete_selected_figure_language(),
    )
    return _ORIGINAL_RENDER_PLOTLY_COMPLETE_LANGUAGE(localized, *args, **kwargs)


_ORIGINAL_ST_PLOTLY_CHART_COMPLETE_LANGUAGE = st.plotly_chart


def _complete_localized_st_plotly_chart(figure_or_data, *args, **kwargs):
  try:
    localized = complete_localize_plotly_figure(
      figure_or_data,
      _complete_selected_figure_language(),
    )
  except Exception:
    localized = figure_or_data

  config = dict(kwargs.get("config") or {})
  config.setdefault("locale", "pt-BR" if IS_PT else "en")
  kwargs["config"] = config
  return _ORIGINAL_ST_PLOTLY_CHART_COMPLETE_LANGUAGE(
    localized,
    *args,
    **kwargs,
  )


st.plotly_chart = _complete_localized_st_plotly_chart
'''
  if anchor in source:
    source = source.replace(anchor, layer + "\n\n" + anchor, 1)

  source += f"\n\n{MARKER}\n"
