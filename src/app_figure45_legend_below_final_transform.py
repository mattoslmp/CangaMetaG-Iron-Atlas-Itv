from __future__ import annotations

"""Install the final Figure 4/5 generator and large bottom-legend layout safely."""

MARKER = "CANGAMETAG_FIGURE45_FINAL_DATA_GENERATOR_V2 = 1"

if MARKER not in source:
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

  future_anchor = "from __future__ import annotations\n"
  imports = '''from src.figure45_large_legend_runtime import (
  apply_figure45_plotly_layout_large as _apply_figure45_plotly_layout_final,
  materialize_article_figure45_static_large as _materialize_article_figure45_static_final,
)
'''
  if imports not in source and future_anchor in source:
    source = source.replace(future_anchor, future_anchor + imports, 1)

  anchor = "page_handler = page_handlers.get(selected_page)"
  layer = r'''
# The static and interactive Figure 4/5 views now use one final implementation.
# Both read the packaged frozen article JSON inputs and only change layout.
materialize_frozen_article_static = _materialize_article_figure45_static_final
final_materialize_frozen_article_static = _materialize_article_figure45_static_final
materialize_frozen_article_static_bilingual = _materialize_article_figure45_static_final

if "article_frozen_taxonomy_figure" in globals():
  _APP_FIGURE45_BEFORE_FINAL_DATA_GENERATOR = article_frozen_taxonomy_figure

  def article_frozen_taxonomy_figure(domain: str):
    figure, tables = _APP_FIGURE45_BEFORE_FINAL_DATA_GENERATOR(domain)
    language = "pt" if globals().get("IS_PT", False) else "en"
    return _apply_figure45_plotly_layout_final(
      figure,
      language=language,
    ), tables


if "render_plotly_downloadable" in globals():
  _APP_RENDER_BEFORE_FIGURE45_FINAL_CAPTION = render_plotly_downloadable

  def render_plotly_downloadable(fig, *args, **kwargs):
    result = _APP_RENDER_BEFORE_FIGURE45_FINAL_CAPTION(fig, *args, **kwargs)
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
        "Legenda da figura: os gráficos de barras mostram a abundância relativa dos gêneros; o NMDS representa a ordenação por distância de Bray–Curtis; e o biplot de RDA mostra as relações restritas com as variáveis ambientais. As chaves de gêneros, símbolos e vetores estão ampliadas e posicionadas abaixo da figura.",
        "Figure legend: stacked bars show genus relative abundance; NMDS represents Bray–Curtis ordination; and the RDA biplot shows constrained relationships with environmental variables. Genus, symbol and vector keys are enlarged and positioned below the figure.",
      ))
    return result
'''

  # This final layer must never stop the application when another page changes.
  if anchor in source:
    source = source.replace(anchor, layer + "\n\n" + anchor, 1)

  source += f"\n\n{MARKER}\n"
  compile(source, "app_core_after_figure45_final_generator.py", "exec")
