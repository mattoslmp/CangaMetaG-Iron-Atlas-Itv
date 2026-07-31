from __future__ import annotations

"""Final Figure 4/5 legend placement guard.

This transform is intentionally loaded after every figure, language and runtime
wrapper. It changes presentation geometry and caption placement only: all
scientific traces, values, coordinates, colours, source tables and statistics
remain untouched.
"""

MARKER = "CANGAMETAG_FIGURE45_LEGEND_BELOW_FINAL_V4 = 1"

if MARKER not in source:
  # Public terminology remains result-oriented. Internal identifiers and
  # function names are preserved because they are part of the implementation.
  public_replacements = {
    'txt("Auditoria recente de visitas", "Recent visit audit")': (
      'txt("Registros recentes de visitas", "Recent visit records")'
    ),
    'txt("Baixar auditoria recente", "Download recent audit")': (
      'txt("Baixar registros recentes", "Download recent records")'
    ),
    'txt("Auditoria das amostras", "Sample audit")': (
      'txt("Amostras utilizadas", "Samples used")'
    ),
    'c4.metric("Amostras auditadas",': 'c4.metric("Amostras verificadas",',
    '"Auditoria"])': '"Registros"])',
    '"Sem auditoria de cobertura."': '"Sem registros de cobertura."',
    '"Baixar auditoria de cobertura"': '"Baixar registros de cobertura"',
    '"Tabela taxonômica completa para auditoria e download"': (
      '"Tabela taxonômica completa para consulta e download"'
    ),
    '"Complete taxonomic table for audit and download"': (
      '"Complete taxonomic table and download"'
    ),
    '"A tabela taxonômica completa será exibida abaixo para auditoria e download."': (
      '"A tabela taxonômica completa será exibida abaixo para consulta e download."'
    ),
    '"The complete taxonomic table is displayed below for audit and download."': (
      '"The complete taxonomic table is displayed below for consultation and download."'
    ),
    '"As planilhas suplementares ficam ocultas para usuários públicos. O admin pode habilitar a visualização técnica para auditoria."': (
      '"As planilhas suplementares ficam ocultas para usuários públicos. O admin pode habilitar a consulta técnica."'
    ),
    '"Supplementary spreadsheets remain hidden to public users. The admin can enable technical viewing for audit."': (
      '"Supplementary spreadsheets remain hidden to public users. The admin can enable technical viewing."'
    ),
    '"sample inclusion audit"': '"sample inclusion record"',
    '"Source audit"': '"Source records"',
    '"Data-source audit"': '"Data-source records"',
    '"Download source audit"': '"Download source records"',
    '"No source audit is available yet."': '"No source records are available yet."',
    '"Sentinel-6 audit"': '"Sentinel-6 records"',
    '"sua ordem original permanece apenas como referência de auditoria. A S67 mantém as duas versões."': (
      '"sua ordem original permanece apenas como referência interna. A S67 mantém as duas versões."'
    ),
    '"its original order remains audit-only. S67 retains both layouts."': (
      '"its original order remains an internal reference. S67 retains both layouts."'
    ),
    '"Tabela completa para auditoria"': '"Tabela completa para consulta"',
    '"Complete audit table"': '"Complete reference table"',
    '"O objetivo é manter o painel auditável e reprodutível."': (
      '"O objetivo é manter o painel verificável e reprodutível."'
    ),
    '"The goal is to keep the panel auditable and reproducible."': (
      '"The goal is to keep the panel verifiable and reproducible."'
    ),
    '"Auditoria de detecção dos 189 KOs"': '"Resumo de detecção dos 189 KOs"',
    '"Detection audit for all 189 KOs"': '"Detection summary for all 189 KOs"',
    '"Baixar auditoria dos 189 KOs"': '"Baixar resumo dos 189 KOs"',
    '"Download the 189-KO audit"': '"Download the 189-KO summary"',
  }
  for old, new in public_replacements.items():
    source = source.replace(old, new)

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


if "render_plotly_downloadable" in globals():
  _APP_RENDER_BEFORE_FIGURE45_CAPTION = render_plotly_downloadable

  def render_plotly_downloadable(fig, *args, **kwargs):
    result = _APP_RENDER_BEFORE_FIGURE45_CAPTION(fig, *args, **kwargs)
    key = str(kwargs.get("key", args[0] if args else "") or "")
    basename = str(kwargs.get("basename", "") or "")
    identity = f"{key} {basename}".casefold()
    if (
      "frozen_article_taxonomy_bacteria" in identity
      or "frozen_article_taxonomy_archaea" in identity
      or "figure4_interactive_exact_article" in identity
      or "figure5_interactive_exact_article" in identity
    ):
      st.caption(txt(
        "Legenda da figura: os gráficos de barras mostram a abundância relativa dos gêneros; o NMDS representa a ordenação por distância de Bray–Curtis; e o biplot de RDA mostra as relações restritas com as variáveis ambientais. As chaves de símbolos, vetores e gêneros estão posicionadas abaixo da figura.",
        "Figure legend: stacked bars show genus relative abundance; NMDS represents Bray–Curtis ordination; and the RDA biplot shows constrained relationships with environmental variables. Symbol, vector and genus keys are positioned below the figure.",
      ))
    return result
'''

  # Never block application startup because a page implementation changed.
  if anchor in source:
    source = source.replace(anchor, layer + "\n\n" + anchor, 1)

  source += f"\n\n{MARKER}\n"
  compile(source, "app_core_after_figure45_legend_below_final.py", "exec")
