from __future__ import annotations

"""Remove internal validation and generic descriptive prose from public pages."""

MARKER = "CANGAMETAG_PUBLIC_VALIDATION_PROSE_CLEANUP_V1 = 1"

if MARKER not in source:
  exact_blocks = [
    '''  st.caption(txt(
    "Figura estática construída com as tabelas congeladas e o layout final do artigo. Nenhum valor de NMDS, RDA ou abundância foi recalculado.",
    "Static figure built from the frozen tables and final article layout. No NMDS, RDA or abundance value was recomputed.",
  ))
''',
    '''  st.info(txt(
    "Estes painéis não recalculam NMDS ou RDA. Eles leem diretamente as matrizes, coordenadas, vetores e estatísticas congeladas em ARTICLE_FINAL_ISME_SUBMISSION_Leandrov27-julho FINAL_SUBMISSION_FILES.",
    "These panels do not recompute NMDS or RDA. They read the matrices, coordinates, vectors and statistics frozen in ARTICLE_FINAL_ISME_SUBMISSION_Leandrov27-julho FINAL_SUBMISSION_FILES directly.",
  ))
''',
    '''  st.info(txt(
    "O boxplot interativo usa exatamente a tabela gerada para a Supplementary Figure 4, a mesma ordem AM-D, AM-R, TIA-D, TIA-R, TI-D, TI-R, VI-D, VI-R, a mesma paleta e as métricas rarefeitas a 32.999 CDS. Nenhuma métrica é recalculada nesta tela.",
    "The interactive boxplot uses the exact table generated for Supplementary Figure 4, the same AM-D, AM-R, TIA-D, TIA-R, TI-D, TI-R, VI-D, VI-R order, the same palette and metrics rarefied to 32,999 CDS. No metric is recalculated on this screen.",
  ))
''',
    '''  st.info(txt(
    "Dry é sempre apresentado à esquerda e Rainy à direita. Cada painel é um gráfico independente, mas ambos usam a mesma seleção Top 14, a mesma paleta e a mesma matriz-fonte da figura estática. A tabela de validação compara os percentuais célula a célula.",
    "Dry is always shown on the left and Rainy on the right. Each panel is an independent chart, but both use the same Top-14 selection, palette and source matrix as the static figure. The validation table compares percentages cell by cell.",
  ))
''',
  ]
  for block in exact_blocks:
    source = source.replace(block, "")

  source = source.replace(
    "Method: the barplot was built from source-table values after active filters; each bar length corresponds to the displayed numeric value and ordering follows that metric. The result is descriptive unless statistical tests and p/q values are explicitly reported below the figure.",
    "",
  )
  source = source.replace(
    "Método: o gráfico de barras foi construído com os valores da tabela-fonte após os filtros ativos; o comprimento de cada barra corresponde ao valor numérico exibido e a ordenação segue essa métrica. O resultado é descritivo, salvo quando testes estatísticos e valores de p/q são apresentados explicitamente abaixo da figura.",
    "",
  )

  source += f"\n\n{MARKER}\n"
