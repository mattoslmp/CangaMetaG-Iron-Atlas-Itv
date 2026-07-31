from __future__ import annotations

import numpy as np
import pandas as pd

from src.article_inference_statistics import alpha_diversity_group_tests
from src.article_official_ordination_statistics import official_ordination_inference
from src.article_taxonomy import load_article_alpha_source


def test_alpha_diversity_global_and_fdr_results_match_source_table() -> None:
  source = load_article_alpha_source()
  tested = alpha_diversity_group_tests(source)
  expected = {
    "Observed_OTUs": (0.5710601340391646, 0.4185427681272882),
    "Chao1": (0.43844782600187887, 0.3671556811748088),
    "Shannon": (0.6598275490061031, 0.4779743576107497),
  }
  for feature, (anova_p, kruskal_p) in expected.items():
    subset = tested[tested["feature"] == feature]
    assert not subset.empty
    assert np.isclose(float(subset["anova_pvalue"].iloc[0]), anova_p)
    assert np.isclose(float(subset["kruskal_pvalue"].iloc[0]), kruskal_p)
  assert not tested["welch_qvalue_BH"].lt(0.05).any()
  assert not tested["mannwhitney_qvalue_BH"].lt(0.05).any()


def test_official_bacteria_ordination_results_are_not_recomputed() -> None:
  beta, rda = official_ordination_inference("Bacteria")
  lake_permanova = beta[(beta["factor"] == "Lake") & (beta["analysis"] == "PERMANOVA")].iloc[0]
  lake_dispersion = beta[(beta["factor"] == "Lake") & (beta["analysis"] == "PERMDISP")].iloc[0]
  assert bool(lake_permanova["official_article_result"])
  assert np.isclose(float(lake_permanova["pseudo_F"]), 2.8188259778020694)
  assert np.isclose(float(lake_permanova["pvalue_permutation"]), 0.018)
  assert np.isclose(float(lake_dispersion["F"]), 6.152229499078603)
  assert np.isclose(float(lake_dispersion["pvalue_permutation"]), 0.039)
  assert np.isclose(float(rda.iloc[0]["R2"]), 0.6706464754765119)
  assert np.isclose(float(rda.iloc[0]["adjusted_R2"]), 0.011939426429535716)
  assert np.isclose(float(rda.iloc[0]["pseudo_F"]), 1.018125548294663)
  assert np.isclose(float(rda.iloc[0]["pvalue_permutation"]), 0.537)
  assert np.isclose(float(rda.iloc[0]["RDA1_axis_permutation_p"]), 0.338)
  assert np.isclose(float(rda.iloc[0]["RDA2_axis_permutation_p"]), 0.677)


def test_official_archaea_ordination_results_are_not_recomputed() -> None:
  beta, rda = official_ordination_inference("Archaea")
  lake_permanova = beta[(beta["factor"] == "Lake") & (beta["analysis"] == "PERMANOVA")].iloc[0]
  lake_dispersion = beta[(beta["factor"] == "Lake") & (beta["analysis"] == "PERMDISP")].iloc[0]
  assert bool(lake_permanova["official_article_result"])
  assert np.isclose(float(lake_permanova["pseudo_F"]), 3.542686889991666)
  assert np.isclose(float(lake_permanova["pvalue_permutation"]), 0.012)
  assert np.isclose(float(lake_dispersion["F"]), 2.643173987042219)
  assert np.isclose(float(lake_dispersion["pvalue_permutation"]), 0.233)
  assert np.isclose(float(rda.iloc[0]["R2"]), 0.6057625487634657)
  assert np.isclose(float(rda.iloc[0]["adjusted_R2"]), -0.18271235370960293)
  assert np.isclose(float(rda.iloc[0]["pseudo_F"]), 0.7682711863922088)
  assert np.isclose(float(rda.iloc[0]["pvalue_permutation"]), 0.698)
  assert np.isclose(float(rda.iloc[0]["RDA1_axis_permutation_p"]), 0.577)
  assert np.isclose(float(rda.iloc[0]["RDA2_axis_permutation_p"]), 0.909)
