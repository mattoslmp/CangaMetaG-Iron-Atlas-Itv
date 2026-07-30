from __future__ import annotations


MARKER = "KEGG_INTERACTIVE_EXPLANATION_REVISION = 1"

if MARKER not in source:
  anchor = '    st.markdown("##### KEGG module completeness explorer")\n'
  if anchor in source:
    replacement = r'''    KEGG_INTERACTIVE_EXPLANATION_REVISION = 1
    st.markdown("##### " + txt(
      "Explorador interativo da completude dos módulos KEGG",
      "Interactive KEGG module completeness explorer",
    ))

    interactive_contexts = {
      "kegg_mags": {
        "figure": "37",
        "scope_pt": "MAGs recuperados dos metagenomas de sedimentos das lagoas",
        "scope_en": "MAGs recovered from the lake-sediment metagenomes",
        "source_pt": "matriz completa de estados KEGG/KEMET dos MAGs",
        "source_en": "complete KEGG/KEMET status matrix for the MAGs",
        "tables_pt": "**Correspondência com o material suplementar:** a Figura Suplementar 37 apresenta o subconjunto temático em formato estático. A Supplementary Table 7 fornece a identificação, qualidade e classificação taxonômica dos MAGs; a Supplementary Table 8 fornece o contexto dos biomarcadores KO usados na seleção temática; e a Supplementary Table 14 documenta o catálogo de módulos temáticos dos ciclos biogeoquímicos.",
        "tables_en": "**Correspondence with the supplementary material:** Supplementary Figure 37 presents the thematic subset as a static figure. Supplementary Table 7 provides MAG identification, quality and taxonomic classification; Supplementary Table 8 provides the KO-biomarker context used for thematic selection; and Supplementary Table 14 documents the thematic biogeochemical-module catalogue.",
      },
      "kegg_lagoon_metagenomes": {
        "figure": "38",
        "scope_pt": "20 metagenomas das lagoas amazônicas",
        "scope_en": "20 Amazonian lake metagenomes",
        "source_pt": "matriz completa de estados KEGG/KEMET dos metagenomas das lagoas",
        "source_en": "complete KEGG/KEMET status matrix for the lake metagenomes",
        "tables_pt": "**Correspondência com o material suplementar:** a Figura Suplementar 38 apresenta o subconjunto temático em cinco páginas estáticas (P001–P005). A Supplementary Table 8 fornece o contexto dos biomarcadores KO usados para priorizar módulos relacionados aos ciclos biogeoquímicos, e a Supplementary Table 14 documenta o catálogo temático aplicado à figura.",
        "tables_en": "**Correspondence with the supplementary material:** Supplementary Figure 38 presents the thematic subset in five static pages (P001–P005). Supplementary Table 8 provides the KO-biomarker context used to prioritize modules associated with biogeochemical cycles, and Supplementary Table 14 documents the thematic catalogue applied to the figure.",
      },
      "kegg_external_iron_rich_environmental_group": {
        "figure": "40",
        "scope_pt": "metagenomas externos de ambientes ricos em ferro organizados por grupo ambiental",
        "scope_en": "external iron-rich metagenomes organized by environmental group",
        "source_pt": "matriz completa de estados de módulos derivada dos perfis KO dos registros externos",
        "source_en": "complete module-status matrix derived from the KO profiles of the external records",
        "tables_pt": "**Correspondência com o material suplementar:** a Figura Suplementar 40 apresenta o subconjunto temático dos ambientes externos ricos em ferro. A Supplementary Table 8 contém os registros, metadados ambientais e perfis KO externos usados nessa comparação; a Supplementary Table 14 documenta o catálogo de módulos temáticos. O agrupamento ambiental altera somente a ordem de apresentação das colunas, não os estados dos módulos.",
        "tables_en": "**Correspondence with the supplementary material:** Supplementary Figure 40 presents the thematic subset for external iron-rich environments. Supplementary Table 8 contains the external records, environmental metadata and KO profiles used in this comparison; Supplementary Table 14 documents the thematic module catalogue. Environmental grouping changes only the display order of columns, not module states.",
      },
      "kegg_combined_lagoon_external_original": {
        "figure": "67",
        "scope_pt": "matriz combinada das lagoas e dos ambientes externos ricos em ferro, na ordem original",
        "scope_en": "combined lake and external iron-rich matrix in the original order",
        "source_pt": "matriz completa combinada dos estados KEGG/KEMET das lagoas e dos estados derivados dos perfis KO externos",
        "source_en": "complete combined matrix of lake KEGG/KEMET states and states derived from external KO profiles",
        "tables_pt": "**Correspondência com o material suplementar:** a Figura Suplementar 67 integra metagenomas das lagoas e registros externos ricos em ferro. A Supplementary Table 8 fornece os biomarcadores KO, os registros externos e seus metadados; a Supplementary Table 14 documenta o catálogo temático usado para selecionar os módulos apresentados na figura estática.",
        "tables_en": "**Correspondence with the supplementary material:** Supplementary Figure 67 integrates lake metagenomes and external iron-rich records. Supplementary Table 8 provides the KO biomarkers, external records and their metadata; Supplementary Table 14 documents the thematic catalogue used to select modules presented in the static figure.",
      },
      "kegg_combined_lagoon_external_environmental_group": {
        "figure": "67",
        "scope_pt": "mesma matriz combinada da Figura Suplementar 67, com as colunas agrupadas por contexto ambiental",
        "scope_en": "the same combined matrix as Supplementary Figure 67, with columns grouped by environmental context",
        "source_pt": "matriz completa combinada dos estados KEGG/KEMET das lagoas e dos estados derivados dos perfis KO externos",
        "source_en": "complete combined matrix of lake KEGG/KEMET states and states derived from external KO profiles",
        "tables_pt": "**Correspondência com o material suplementar:** esta é a visualização alternativa por grupo ambiental da Figura Suplementar 67. A Supplementary Table 8 fornece os biomarcadores KO, os registros externos e seus metadados; a Supplementary Table 14 documenta o catálogo temático. O agrupamento modifica somente a ordem visual das colunas e preserva todos os estados originais.",
        "tables_en": "**Correspondence with the supplementary material:** this is the environmental-group alternative view of Supplementary Figure 67. Supplementary Table 8 provides the KO biomarkers, external records and their metadata; Supplementary Table 14 documents the thematic catalogue. Grouping changes only the visual column order and preserves every original state.",
      },
    }
    interactive_context = interactive_contexts.get(
      key_prefix,
      {
        "figure": "",
        "scope_pt": "amostras analisadas",
        "scope_en": "analyzed samples",
        "source_pt": "matriz-fonte completa de estados dos módulos",
        "source_en": "complete source matrix of module states",
        "tables_pt": "",
        "tables_en": "",
      },
    )
    figure_number = interactive_context["figure"]
    st.info(txt(
      f"Este painel é a versão interativa e complementar da Figura Suplementar {figure_number}. A figura estática mostra um subconjunto temático selecionado para publicação e pode ser dividido em páginas. O explorador permite consultar a {interactive_context['source_pt']} para {interactive_context['scope_pt']}, incluindo resultados que não aparecem na figura suplementar por estarem fora do subconjunto temático, por não apresentarem ao menos uma chamada Complete, ou por estarem em outras páginas. Ao selecionar Full matrix, todos os módulos e todos os estados originais disponíveis na matriz-fonte podem ser explorados. Os filtros apenas controlam a visualização; nenhum valor é recalculado, imputado ou substituído.",
      f"This panel is the interactive companion to Supplementary Figure {figure_number}. The static figure shows a publication-oriented thematic subset and may be divided into pages. The explorer provides access to the {interactive_context['source_en']} for {interactive_context['scope_en']}, including results not shown in the supplementary figure because they fall outside the thematic subset, have no Complete call in at least one record, or occur on other pages. Selecting Full matrix makes every module and every original state available from the source matrix. Filters control visualization only; no value is recalculated, imputed or replaced.",
    ))
    if interactive_context["tables_pt"]:
      st.markdown(txt(
        interactive_context["tables_pt"],
        interactive_context["tables_en"],
      ))
    st.caption(txt(
      "Como usar: escolha o conjunto de módulos, defina quantos módulos deseja mostrar, selecione amostras/MAGs e controle os estados visíveis. A tabela-fonte completa permanece disponível abaixo do gráfico para auditoria e download.",
      "How to use: choose the module set, define how many modules to display, select samples/MAGs and control visible states. The complete source table remains available below the chart for audit and download.",
    ))
'''
    source = source.replace(anchor, replacement, 1)
