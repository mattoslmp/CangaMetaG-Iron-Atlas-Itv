from __future__ import annotations

"""Final Figure 4/5 legend placement guard.

This transform is intentionally loaded after every figure, language and runtime
wrapper. It changes presentation geometry and caption placement only: all
scientific traces, values, coordinates, colours, source tables and statistics
remain untouched.
"""

MARKER = "CANGAMETAG_FIGURE45_LEGEND_BELOW_FINAL_V2 = 1"

if MARKER not in source:
  # The textual figure legend must follow the rendered image, not precede it.
  # Insert it immediately after the Figure 4/5 renderer and before methods,
  # statistics and exact-data tables.
  caption_anchor = '''        audit_script="src/article_frozen_taxonomy_panels.py; src/article_inference_statistics.py",
      )
      beta_tests, rda_tests = frozen_ordination_inference(domain)
'''
  caption_replacement = '''        audit_script="src/article_frozen_taxonomy_panels.py; src/article_inference_statistics.py",
      )
      st.caption(txt(
        "Legenda da figura: os gráficos de barras mostram a abundância relativa dos gêneros; o NMDS representa a ordenação por distância de Bray–Curtis; e o biplot de RDA mostra as relações restritas com as variáveis ambientais. Todas as chaves de símbolos, vetores e gêneros estão posicionadas abaixo da figura.",
        "Figure legend: stacked bars show genus relative abundance; NMDS represents Bray–Curtis ordination; and the RDA biplot shows constrained relationships with environmental variables. All symbol, vector and genus keys are positioned below the figure.",
      ))
      beta_tests, rda_tests = frozen_ordination_inference(domain)
'''
  if caption_anchor not in source:
    raise RuntimeError("Could not place the Figure 4/5 caption below the figure")
  source = source.replace(caption_anchor, caption_replacement, 1)

  anchor = "page_handler = page_handlers.get(selected_page)"
  layer = r'''
if "article_frozen_taxonomy_figure" in globals():
  _APP_FIGURE45_BEFORE_FINAL_LEGEND_GUARD = article_frozen_taxonomy_figure

  def article_frozen_taxonomy_figure(domain: str):
    figure, tables = _APP_FIGURE45_BEFORE_FINAL_LEGEND_GUARD(domain)

    current_margin = getattr(figure.layout, "margin", None)
    left = int(getattr(current_margin, "l", 115) or 115)
    right = int(getattr(current_margin, "r", 110) or 110)
    top = int(getattr(current_margin, "t", 105) or 105)

    # Reserve a dedicated band below all four scientific panels. The horizontal
    # genus legend occupies the lower rows; NMDS and RDA keys occupy the first
    # row of the same band. Negative paper coordinates are retained inside the
    # enlarged bottom margin and therefore remain visible in HTML and exports.
    figure.update_layout(
      height=max(int(getattr(figure.layout, "height", 0) or 0), 1900),
      width=max(int(getattr(figure.layout, "width", 0) or 0), 1750),
      margin={"l": left, "r": right, "t": top, "b": 690},
      legend={
        "title": {"text": txt("Gênero", "Genus")},
        "orientation": "h",
        "x": 0.5,
        "xanchor": "center",
        "y": -0.285,
        "yanchor": "top",
        "font": {"size": 11},
        "itemsizing": "constant",
        "tracegroupgap": 5,
        "bgcolor": "rgba(255,255,255,0.98)",
        "bordercolor": "#D1D5DB",
        "borderwidth": 1,
      },
    )

    for annotation in list(figure.layout.annotations or []):
      text = str(getattr(annotation, "text", "") or "")
      normalized = text.casefold()
      if "nmds symbols:" in normalized or "símbolos do nmds:" in normalized:
        annotation.update(
          x=0.04,
          y=-0.105,
          xref="paper",
          yref="paper",
          xanchor="left",
          yanchor="top",
          bgcolor="rgba(255,255,255,0.98)",
          bordercolor="#D1D5DB",
          borderwidth=1,
          borderpad=5,
        )
      elif "rda vectors:" in normalized or "vetores da rda:" in normalized:
        annotation.update(
          x=0.96,
          y=-0.105,
          xref="paper",
          yref="paper",
          xanchor="right",
          yanchor="top",
          bgcolor="rgba(255,255,255,0.98)",
          bordercolor="#D1D5DB",
          borderwidth=1,
          borderpad=5,
        )

    meta = dict(figure.layout.meta) if isinstance(figure.layout.meta, dict) else {}
    meta.update({
      "figure45_final_legend_guard": True,
      "legend_layout": "dedicated-band-below-entire-figure",
      "legend_below_entire_figure": True,
      "textual_caption_below_figure": True,
      "legend_overlaps_scientific_panels": False,
      "bottom_margin_px": 690,
      "scientific_values_changed": False,
    })
    figure.update_layout(meta=meta)
    return figure, tables
'''
  if anchor not in source:
    raise RuntimeError("Could not install final Figure 4/5 legend guard")
  source = source.replace(anchor, layer + "\n\n" + anchor, 1)
  source += f"\n\n{MARKER}\n"
  compile(source, "app_core_after_figure45_legend_below_final.py", "exec")
