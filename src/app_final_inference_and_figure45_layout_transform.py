from __future__ import annotations

"""Final public layout and inferential-statistics layer.

The transform removes internal validation prose, aligns interactive Figure 4/5
legends with the static article layout, and renders real inferential results
immediately below boxplots, taxonomy barplots, NMDS/PCoA and RDA panels.
"""

MARKER = "CANGAMETAG_FINAL_INFERENCE_AND_FIGURE45_LAYOUT_V1 = 1"


def _remove_call_containing(text: str, needle: str) -> str:
  """Remove a public Streamlit prose call containing an unwanted sentence."""
  while needle in text:
    position = text.find(needle)
    candidates = [
      text.rfind("st.caption(txt(", 0, position),
      text.rfind("st.info(txt(", 0, position),
      text.rfind("st.success(txt(", 0, position),
      text.rfind("st.warning(txt(", 0, position),
      text.rfind("st.markdown(txt(", 0, position),
    ]
    start = max(candidates)
    if start < 0:
      text = text.replace(needle, "")
      continue
    line_start = text.rfind("\n", 0, start) + 1
    end = text.find("\n", position)
    cursor = end if end >= 0 else len(text)
    # Multiline Streamlit calls in this app close with a line containing ``))``.
    while cursor < len(text):
      next_end = text.find("\n", cursor + 1)
      if next_end < 0:
        next_end = len(text)
      line = text[cursor + 1:next_end].strip()
      if line in {"))", ")))", ")"}:
        cursor = next_end
        break
      cursor = next_end
    text = text[:line_start] + text[cursor + 1:]
  return text


if MARKER not in source:
  import_anchor = "from src.publication_rda import (\n"
  inference_imports = '''from src.article_inference_statistics import (
  alpha_diversity_group_tests,
  beta_tests_from_profile_table,
  frozen_ordination_inference,
  inference_summary,
  taxonomy_barplot_group_tests_from_table,
)
'''
  if inference_imports not in source:
    if import_anchor in source:
      source = source.replace(import_anchor, inference_imports + import_anchor, 1)
    else:
      source = inference_imports + source

  unwanted_public_prose = [
    "Static figure built from the frozen tables and final article layout.",
    "Figura estática construída com as tabelas congeladas e o layout final do artigo.",
    "These panels do not recompute NMDS or RDA.",
    "Estes painéis não recalculam NMDS ou RDA.",
    "The interactive boxplot uses the exact table generated for Supplementary Figure 4",
    "O boxplot interativo usa exatamente a tabela gerada para a Supplementary Figure 4",
    "Method: the barplot was built from source-table values after active filters; each bar length corresponds to the displayed numeric value and ordering follows that metric. The result is descriptive unless statistical tests and p/q values are explicitly reported below the figure.",
    "The result is descriptive unless statistical tests and p/q values are explicitly reported below the figure.",
    "Validation passed for",
    "Validação aprovada para",
  ]
  for prose in unwanted_public_prose:
    source = _remove_call_containing(source, prose)

  runtime_anchor = 'page_handler = page_handlers.get(selected_page)'
  final_layer = r'''

def _final_results_key(value: object) -> str:
  return safe_filename(str(value or "results")).replace("-", "_")


def _render_inferential_results_below_figure(
  table: pd.DataFrame,
  context: str,
  key: str,
) -> None:
  if table is None or table.empty:
    st.markdown(txt(
      f"**Resultados estatísticos — {context}:** não houve replicação suficiente para uma comparação válida.",
      f"**Statistical results — {context}:** there was insufficient replication for a valid comparison.",
    ))
    return
  st.markdown(txt(
    f"**Resultados estatísticos — {context}:** {inference_summary(table)}",
    f"**Statistical results — {context}:** {inference_summary(table)}",
  ))
  st.caption(txt(
    "Testes paramétricos: ANOVA de uma via e Welch t-test. Testes não paramétricos: Kruskal–Wallis e Mann–Whitney U. As comparações pareadas usam correção FDR de Benjamini–Hochberg; q < 0,05 define significância.",
    "Parametric tests: one-way ANOVA and Welch t-test. Non-parametric tests: Kruskal–Wallis and Mann–Whitney U. Pairwise comparisons use Benjamini–Hochberg FDR; q < 0.05 defines significance.",
  ))
  with st.expander(txt("Tabela completa dos testes", "Complete statistical-test table"), expanded=False):
    show_table(table, f"{key}_inferential_statistics", height=420)
    csv_button(
      table,
      f"{_final_results_key(key)}_inferential_statistics.csv",
      txt("Baixar resultados estatísticos", "Download statistical results"),
      key=f"{key}_inferential_statistics_csv",
    )


if "article_alpha_boxplot" in globals():
  _APP_ORIGINAL_ARTICLE_ALPHA_BOXPLOT_FINAL_STATS = article_alpha_boxplot

  def article_alpha_boxplot(*args, **kwargs):
    figure, source_table = _APP_ORIGINAL_ARTICLE_ALPHA_BOXPLOT_FINAL_STATS(*args, **kwargs)
    tests = alpha_diversity_group_tests(source_table)
    meta = dict(figure.layout.meta) if isinstance(figure.layout.meta, dict) else {}
    meta.update({
      "inferential_statistics_context": "Supplementary Figure 4 alpha-diversity boxplots",
      "inferential_statistics_records": tests.to_dict("records"),
      "inferential_statistics_method": "ANOVA, Kruskal-Wallis, Welch t-test, Mann-Whitney U and Benjamini-Hochberg FDR",
    })
    figure.update_layout(meta=meta)
    return figure, source_table


if "article_season_barplot" in globals():
  _APP_ORIGINAL_ARTICLE_SEASON_BARPLOT_FINAL_STATS = article_season_barplot

  def article_season_barplot(*args, **kwargs):
    figure, exact_table, matrix = _APP_ORIGINAL_ARTICLE_SEASON_BARPLOT_FINAL_STATS(*args, **kwargs)
    tests = taxonomy_barplot_group_tests_from_table(exact_table)
    domain = str(exact_table.get("domain", pd.Series([""])).iloc[0]) if not exact_table.empty else ""
    rank = str(exact_table.get("rank", pd.Series([""])).iloc[0]) if not exact_table.empty else ""
    season = str(exact_table.get("season", pd.Series([""])).iloc[0]) if not exact_table.empty else ""
    context = " — ".join(value for value in [domain, rank, season, "lake comparison"] if value)
    meta = dict(figure.layout.meta) if isinstance(figure.layout.meta, dict) else {}
    meta.update({
      "inferential_statistics_context": context or "taxonomy barplot group comparison",
      "inferential_statistics_records": tests.to_dict("records"),
      "inferential_statistics_method": "ANOVA, Kruskal-Wallis, Welch t-test, Mann-Whitney U and Benjamini-Hochberg FDR",
    })
    figure.update_layout(
      margin={"l": 95, "r": 250, "t": 88, "b": 165},
      meta=meta,
    )
    return figure, exact_table, matrix


if "render_plotly_downloadable" in globals():
  _APP_ORIGINAL_RENDER_PLOTLY_FINAL_STATS = render_plotly_downloadable

  def render_plotly_downloadable(fig, *args, **kwargs):
    result = _APP_ORIGINAL_RENDER_PLOTLY_FINAL_STATS(fig, *args, **kwargs)
    try:
      meta = dict(fig.layout.meta) if isinstance(fig.layout.meta, dict) else {}
      records = meta.get("inferential_statistics_records", [])
      if records:
        statistics_table = pd.DataFrame(records)
        context = str(meta.get("inferential_statistics_context", "group comparison"))
        chart_key = str(kwargs.get("key", "plotly_figure"))
        _render_inferential_results_below_figure(
          statistics_table,
          context,
          chart_key,
        )
    except Exception as exc:
      LOGGER.warning("Could not render inferential results below figure: %s", exc)
    return result


if "article_frozen_taxonomy_figure" in globals():
  _APP_ORIGINAL_FROZEN_TAXONOMY_FIGURE_ARTICLE_LAYOUT = article_frozen_taxonomy_figure

  def article_frozen_taxonomy_figure(domain: str):
    figure, tables = _APP_ORIGINAL_FROZEN_TAXONOMY_FIGURE_ARTICLE_LAYOUT(domain)
    # Match the normalized positions of the static article figure: lake/season
    # at lower left, RDA vectors at lower right and genus legend at bottom centre.
    figure.update_layout(
      height=1710,
      width=1750,
      margin={"l": 115, "r": 110, "t": 105, "b": 520},
      legend={
        "title": {"text": "Genus"},
        "orientation": "h",
        "x": 0.5,
        "xanchor": "center",
        "y": -0.305,
        "yanchor": "top",
        "font": {"size": 11},
        "itemsizing": "constant",
        "tracegroupgap": 4,
        "bgcolor": "rgba(255,255,255,0)",
        "borderwidth": 0,
      },
    )
    for annotation in list(figure.layout.annotations or []):
      text = str(getattr(annotation, "text", "") or "")
      if "NMDS symbols:" in text:
        annotation.update(
          x=0.075,
          y=-0.105,
          xref="paper",
          yref="paper",
          xanchor="left",
          yanchor="top",
          bgcolor="rgba(255,255,255,0)",
          borderwidth=0,
        )
      elif "RDA vectors:" in text:
        annotation.update(
          x=0.96,
          y=-0.105,
          xref="paper",
          yref="paper",
          xanchor="right",
          yanchor="top",
          bgcolor="rgba(255,255,255,0)",
          borderwidth=0,
        )
    meta = dict(figure.layout.meta) if isinstance(figure.layout.meta, dict) else {}
    meta.update({
      "legend_layout": "article-static-matched-v4",
      "lake_season_anchor": [0.075, -0.105],
      "rda_vector_anchor": [0.96, -0.105],
      "genus_anchor": [0.5, -0.305],
      "legend_overlaps_scientific_panels": False,
    })
    figure.update_layout(meta=meta)
    return figure, tables


def _render_frozen_article_taxonomy_ordinations() -> None:
  st.markdown("### " + txt(
    "Figuras 4 e 5 — perfis de gêneros e ordenações",
    "Figures 4 and 5 — genus profiles and ordinations",
  ))
  tabs = st.tabs(["Bacteria — Figure 4", "Archaea — Figure 5"])
  for domain, tab in zip(["Bacteria", "Archaea"], tabs):
    with tab:
      figure, tables = article_frozen_taxonomy_figure(domain)
      render_plotly_downloadable(
        figure,
        key=f"frozen_article_taxonomy_{domain}",
        basename=f"{'Figure4' if domain == 'Bacteria' else 'Figure5'}_interactive_exact_article",
        audit_input_table=tables["genus_relative_abundance"],
        audit_processed_table=tables["nmds_scores"],
        audit_output_table=tables["ordination_statistics"],
        audit_method="Frozen article genus profiles, Bray-Curtis NMDS and constrained RDA.",
        audit_input_source="data/article_frozen_taxonomy_bacteria.json or data/article_frozen_taxonomy_archaea.json",
        audit_script="src/article_frozen_taxonomy_panels.py; src/article_inference_statistics.py",
      )

      beta_tests, rda_tests = frozen_ordination_inference(domain)
      st.markdown("##### " + txt(
        "NMDS/PCoA — método e significância",
        "NMDS/PCoA — method and significance",
      ))
      st.markdown(txt(
        "Método: distância Bray–Curtis sobre os perfis de abundância relativa dos gêneros. A separação entre lagoas e estações foi testada por PERMANOVA com 999 permutações; a homogeneidade da dispersão foi testada por PERMDISP/betadisper. " + inference_summary(beta_tests),
        "Method: Bray-Curtis distance on genus relative-abundance profiles. Separation among lakes and seasons was tested by PERMANOVA with 999 permutations; homogeneity of dispersion was tested by PERMDISP/betadisper. " + inference_summary(beta_tests),
      ))
      show_table(beta_tests, f"figure45_{domain}_nmds_pcoa_statistics", height=300)
      csv_button(
        beta_tests,
        f"{'Figure4' if domain == 'Bacteria' else 'Figure5'}_{domain}_NMDS_PCoA_PERMANOVA_PERMDISP.csv",
        txt("Baixar testes NMDS/PCoA", "Download NMDS/PCoA tests"),
        key=f"figure45_{domain}_nmds_pcoa_statistics_csv",
      )

      st.markdown("##### " + txt(
        "RDA — método e significância",
        "RDA — method and significance",
      ))
      if not rda_tests.empty:
        row = rda_tests.iloc[0]
        pvalue = pd.to_numeric(pd.Series([row.get("pvalue_permutation")]), errors="coerce").iloc[0]
        result_pt = "significativo" if pd.notna(pvalue) and float(pvalue) < 0.05 else "não significativo"
        result_en = "significant" if pd.notna(pvalue) and float(pvalue) < 0.05 else "not significant"
        st.markdown(txt(
          f"Método: composição de gêneros transformada por Hellinger e restringida pelas variáveis ambientais padronizadas; significância global avaliada por teste de permutação. Resultado: R²={float(row.get('R2', np.nan)):.3g}, pseudo-F={float(row.get('pseudo_F', np.nan)):.3g}, p={float(pvalue):.3g}; modelo {result_pt} a 5%.",
          f"Method: Hellinger-transformed genus composition constrained by standardized environmental variables; global significance evaluated by permutation test. Result: R²={float(row.get('R2', np.nan)):.3g}, pseudo-F={float(row.get('pseudo_F', np.nan)):.3g}, p={float(pvalue):.3g}; model {result_en} at 5%.",
        ))
      show_table(rda_tests, f"figure45_{domain}_rda_statistics", height=220)
      csv_button(
        rda_tests,
        f"{'Figure4' if domain == 'Bacteria' else 'Figure5'}_{domain}_RDA_global_statistics.csv",
        txt("Baixar resultados da RDA", "Download RDA results"),
        key=f"figure45_{domain}_rda_statistics_csv",
      )

      with st.expander(txt("Tabelas exatas da figura", "Exact figure tables"), expanded=False):
        for table_name, table in tables.items():
          st.markdown(f"#### `{table_name}`")
          show_table(table, f"frozen_{domain}_{table_name}", height=320)
          csv_button(
            table,
            f"{'Figure4' if domain == 'Bacteria' else 'Figure5'}_{table_name}.csv",
            txt("Baixar tabela", "Download table"),
            key=f"frozen_{domain}_{table_name}_csv_final",
          )


if "_render_beta_final" in globals():
  _APP_ORIGINAL_RENDER_BETA_FINAL_WITHOUT_VISIBLE_TESTS = _render_beta_final

  def _render_beta_final(level_name: str) -> None:
    _APP_ORIGINAL_RENDER_BETA_FINAL_WITHOUT_VISIBLE_TESTS(level_name)
    try:
      profile = _taxonomy_count_profile_final(level_name, "Individual samples")
      tests = beta_tests_from_profile_table(profile)
    except Exception as exc:
      LOGGER.warning("Could not calculate beta-diversity inference: %s", exc)
      tests = pd.DataFrame()
    st.markdown("##### " + txt(
      "PCoA/NMDS — testes entre grupos",
      "PCoA/NMDS — group tests",
    ))
    st.markdown(txt(
      "Método: distância Bray–Curtis. PERMANOVA testa diferenças multivariadas entre lagoas e estações; PERMDISP testa diferenças de dispersão em torno dos centroides. " + inference_summary(tests),
      "Method: Bray-Curtis distance. PERMANOVA tests multivariate differences among lakes and seasons; PERMDISP tests differences in dispersion around group centroids. " + inference_summary(tests),
    ))
    if not tests.empty:
      show_table(tests, f"beta_group_tests_{safe_filename(level_name)}", height=300)
      csv_button(
        tests,
        f"beta_group_tests_{safe_filename(level_name)}.csv",
        txt("Baixar PERMANOVA/PERMDISP", "Download PERMANOVA/PERMDISP"),
        key=f"beta_group_tests_{safe_filename(level_name)}_csv",
      )
'''
  if runtime_anchor in source and "CANGAMETAG_FINAL_INFERENCE_RUNTIME_LAYER" not in source:
    source = source.replace(
      runtime_anchor,
      "CANGAMETAG_FINAL_INFERENCE_RUNTIME_LAYER = 1\n\n" + final_layer + "\n\n" + runtime_anchor,
      1,
    )

  source += f"\n\n{MARKER}\n"
