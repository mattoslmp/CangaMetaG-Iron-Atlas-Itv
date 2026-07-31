from __future__ import annotations

"""Place every Figure 4/5 interactive legend in a dedicated bottom band."""

MARKER = "CANGAMETAG_FIGURE45_BOTTOM_LEGEND_V3 = 1"

if MARKER not in source:
  anchor = "page_handler = page_handlers.get(selected_page)"
  wrapper = r'''
if "article_frozen_taxonomy_figure" in globals():
  _APP_ORIGINAL_ARTICLE_FROZEN_TAXONOMY_FIGURE_BOTTOM_LEGEND = article_frozen_taxonomy_figure

  def article_frozen_taxonomy_figure(domain: str):
    figure, tables = _APP_ORIGINAL_ARTICLE_FROZEN_TAXONOMY_FIGURE_BOTTOM_LEGEND(domain)
    figure.update_layout(
      height=1700,
      margin={"l": 115, "r": 110, "t": 105, "b": 520},
      legend={
        "title": {"text": "Genus"},
        "orientation": "h",
        "x": 0.5,
        "xanchor": "center",
        "y": -0.30,
        "yanchor": "top",
        "font": {"size": 11},
        "itemsizing": "constant",
        "tracegroupgap": 4,
        "bgcolor": "rgba(255,255,255,0.98)",
        "bordercolor": "#D1D5DB",
        "borderwidth": 1,
      },
    )
    for annotation in list(figure.layout.annotations or []):
      text = str(getattr(annotation, "text", "") or "")
      if "NMDS symbols:" in text:
        annotation.update(
          x=0.24,
          y=-0.105,
          xref="paper",
          yref="paper",
          xanchor="center",
          yanchor="top",
        )
      elif "RDA vectors:" in text:
        annotation.update(
          x=0.76,
          y=-0.105,
          xref="paper",
          yref="paper",
          xanchor="center",
          yanchor="top",
        )
    meta = figure.layout.meta if isinstance(figure.layout.meta, dict) else {}
    meta = dict(meta)
    meta.update({
      "legend_layout": "dedicated-bottom-band-v3",
      "legend_below_entire_figure": True,
      "legend_overlaps_scientific_panels": False,
    })
    figure.update_layout(meta=meta)
    return figure, tables
'''
  if anchor in source and "_APP_ORIGINAL_ARTICLE_FROZEN_TAXONOMY_FIGURE_BOTTOM_LEGEND" not in source:
    source = source.replace(anchor, wrapper + "\n\n" + anchor, 1)
  source += f"\n\n{MARKER}\n"
