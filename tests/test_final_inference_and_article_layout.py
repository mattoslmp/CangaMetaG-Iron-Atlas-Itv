from __future__ import annotations

import json
from pathlib import Path
import runpy

import numpy as np
import pandas as pd

from src.article_inference_reporting import inference_summary
from src.article_inference_statistics import (
  alpha_diversity_group_tests,
  group_comparison_tests,
  taxonomy_barplot_group_tests_from_table,
)
from src.article_official_ordination_statistics import official_ordination_inference


ROOT = Path(__file__).resolve().parents[1]


def test_group_comparison_reports_parametric_and_nonparametric_results() -> None:
  frame = pd.DataFrame({
    "feature": ["K1"] * 9 + ["K2"] * 9,
    "group": ["A"] * 3 + ["B"] * 3 + ["C"] * 3 + ["A"] * 3 + ["B"] * 3 + ["C"] * 3,
    "value": [1.0, 1.2, 0.8, 4.0, 4.2, 3.8, 7.0, 7.2, 6.8,
              2.0, 2.1, 1.9, 2.2, 2.3, 2.1, 2.4, 2.5, 2.3],
  })
  original_values = frame["value"].copy()
  result = group_comparison_tests(
    frame,
    "value",
    "group",
    feature_column="feature",
  )

  expected = {
    "anova_F", "anova_pvalue", "kruskal_H", "kruskal_pvalue",
    "welch_t", "welch_pvalue", "welch_qvalue_BH",
    "mannwhitney_U", "mannwhitney_pvalue", "mannwhitney_qvalue_BH",
  }
  assert expected.issubset(result.columns)
  assert set(result["feature"]) == {"K1", "K2"}
  assert len(result) == 6
  assert frame["value"].equals(original_values)
  assert result["welch_qvalue_BH"].dropna().between(0, 1).all()
  assert result["mannwhitney_qvalue_BH"].dropna().between(0, 1).all()


def test_alpha_diversity_boxplots_use_all_four_test_families() -> None:
  rows = []
  for group_index, group in enumerate(["AM-D", "AM-R", "TIA-D"]):
    for replicate in range(3):
      rows.append({
        "Lake_season": group,
        "Observed_OTUs": 100 + 20 * group_index + replicate,
        "Chao1": 110 + 20 * group_index + replicate,
        "Shannon": 3.0 + 0.4 * group_index + 0.02 * replicate,
      })
  result = alpha_diversity_group_tests(pd.DataFrame(rows))
  assert set(result["feature"]) == {"Observed_OTUs", "Chao1", "Shannon"}
  assert set(result["global_parametric_test"]) == {"one-way ANOVA"}
  assert set(result["global_nonparametric_test"]) == {"Kruskal-Wallis"}
  assert set(result["pairwise_parametric_test"]) == {"Welch t-test"}
  assert set(result["pairwise_nonparametric_test"]) == {"Mann-Whitney U"}


def test_taxonomy_barplot_tests_compare_lakes_within_season() -> None:
  rows = []
  for taxon in ["Taxon A", "Taxon B"]:
    for lake_index, lake in enumerate(["AM", "TIA", "TI", "VI"]):
      for replicate in [1, 2]:
        rows.append({
          "domain": "Bacteria",
          "rank": "Order",
          "season": "Dry",
          "sample": f"{lake}.P{replicate}.D",
          "taxon": taxon,
          "relative_abundance_percent": 1.0 + lake_index + replicate / 10,
        })
  result = taxonomy_barplot_group_tests_from_table(pd.DataFrame(rows))
  assert set(result["feature"]) == {"Taxon A", "Taxon B"}
  assert set(result["grouping_factor"]) == {"lake"}
  assert set(result["season"]) == {"Dry"}
  assert result["groups_compared_globally"].str.contains("AM").all()


def test_figure45_uses_exact_official_permanova_dispersion_and_rda_results() -> None:
  beta, rda = official_ordination_inference("Bacteria", base_dir=ROOT)
  assert set(beta["analysis"]) == {"PERMANOVA", "PERMDISP"}
  assert set(beta["factor"]) == {"Lake", "Season", "LakeSeason"}
  assert beta["official_article_result"].all()

  lake_permanova = beta[(beta["analysis"] == "PERMANOVA") & (beta["factor"] == "Lake")].iloc[0]
  lake_dispersion = beta[(beta["analysis"] == "PERMDISP") & (beta["factor"] == "Lake")].iloc[0]
  assert np.isclose(float(lake_permanova["pseudo_F"]), 2.8188259778020694)
  assert np.isclose(float(lake_permanova["pvalue_permutation"]), 0.018)
  assert np.isclose(float(lake_dispersion["F"]), 6.152229499078603)
  assert np.isclose(float(lake_dispersion["pvalue_permutation"]), 0.039)

  assert {"R2", "pseudo_F", "pvalue_permutation", "RDA1_axis_permutation_p", "RDA2_axis_permutation_p"}.issubset(rda.columns)
  assert rda["official_article_result"].all()
  assert np.isclose(float(rda.iloc[0]["R2"]), 0.6706464754765119)
  assert np.isclose(float(rda.iloc[0]["pseudo_F"]), 1.018125548294663)
  assert np.isclose(float(rda.iloc[0]["pvalue_permutation"]), 0.537)
  summary = inference_summary(beta)
  assert "PERMANOVA (Lake)" in summary
  assert "PERMDISP (Season)" in summary


def test_final_app_transform_uses_article_legend_coordinates() -> None:
  synthetic = '''from src.publication_rda import (
  publication_rda_figure,
)


def article_alpha_boxplot(*args, **kwargs):
  pass


def article_season_barplot(*args, **kwargs):
  pass


def render_plotly_downloadable(*args, **kwargs):
  pass


def article_frozen_taxonomy_figure(domain):
  pass


def _render_beta_final(level_name):
  pass

page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_final_inference_and_figure45_layout_v2_transform.py"),
    init_globals={"source": synthetic},
  )["source"]
  compile(transformed, "synthetic_final_inference_app.py", "exec")
  assert '"lake_season_anchor": [0.075, -0.105]' in transformed
  assert '"rda_vector_anchor": [0.96, -0.105]' in transformed
  assert '"genus_anchor": [0.5, -0.305]' in transformed
  assert "PERMANOVA with 999 permutations" in transformed
  assert "ANOVA de uma via e Welch t-test" in transformed


def test_public_cleanup_removes_validation_and_generic_barplot_prose() -> None:
  forbidden = (
    "Method: the barplot was built from source-table values after active filters; "
    "each bar length corresponds to the displayed numeric value and ordering follows that metric. "
    "The result is descriptive unless statistical tests and p/q values are explicitly reported below the figure."
  )
  synthetic = f'''st.caption(txt(
    "Figura estática construída com as tabelas congeladas e o layout final do artigo. Nenhum valor de NMDS, RDA ou abundância foi recalculado.",
    "Static figure built from the frozen tables and final article layout. No NMDS, RDA or abundance value was recomputed.",
  ))
st.caption("{forbidden}")
'''
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_public_validation_prose_cleanup_transform.py"),
    init_globals={"source": synthetic},
  )["source"]
  assert "Static figure built from the frozen tables" not in transformed
  assert forbidden not in transformed


def test_app_loads_only_safe_final_inference_layers() -> None:
  app_text = (ROOT / "app.py").read_text(encoding="utf-8")
  assert "app_final_inference_and_figure45_layout_v2_transform.py" in app_text
  assert "app_inference_summary_fix_transform.py" in app_text
  assert "app_official_ordination_statistics_transform.py" in app_text
  assert "app_public_validation_prose_cleanup_transform.py" in app_text
  assert '"app_final_inference_and_figure45_layout_transform.py"' not in app_text


def test_final_scripts_and_manifest_register_inference_outputs() -> None:
  taxonomy_script = (
    ROOT / "scripts" / "final_publication_figures" /
    "02_05_generate_final_taxonomy_figures.py"
  ).read_text(encoding="utf-8")
  group_script = (
    ROOT / "scripts" / "final_publication_figures" /
    "08_generate_group_comparison_statistics.py"
  ).read_text(encoding="utf-8")
  manifest = json.loads(
    (ROOT / "scripts" / "FINAL_SCRIPT_MANIFEST.json").read_text(encoding="utf-8")
  )

  assert "official_ordination_inference" in taxonomy_script
  assert "NMDS_PCoA_PERMANOVA_PERMDISP.csv" in taxonomy_script
  assert "alpha_diversity_group_tests" in group_script
  assert "taxonomy_explorer_group_tests" in group_script
  assert "article_season_barplot" in group_script
  assert "official_ordination_inference" in group_script
  paths = {entry["path"] for entry in manifest["canonical_scripts"]}
  assert "scripts/final_publication_figures/08_generate_group_comparison_statistics.py" in paths
  assert manifest["manifest_version"] == "2026-07-31-final-v4-official-statistics"
