from __future__ import annotations

"""Shared inferential statistics for article figures and the public app.

This module contains the single implementation used by both the Streamlit
application and final article scripts. It never changes source values. It
calculates global parametric/non-parametric tests, pairwise tests with
Benjamini-Hochberg correction, and Bray-Curtis PERMANOVA/PERMDISP summaries.
"""

from itertools import combinations
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import pdist, squareform


DEFAULT_PERMUTATIONS = 999
DEFAULT_SEED = 42


def benjamini_hochberg(values: Iterable[float]) -> np.ndarray:
  raw = np.asarray(list(values), dtype=float)
  adjusted = np.full(raw.shape, np.nan, dtype=float)
  valid_mask = np.isfinite(raw)
  if not valid_mask.any():
    return adjusted
  valid = raw[valid_mask]
  order = np.argsort(valid)
  ranked = valid[order]
  count = len(ranked)
  corrected = ranked * count / np.arange(1, count + 1, dtype=float)
  corrected = np.minimum.accumulate(corrected[::-1])[::-1]
  restored = np.empty_like(corrected)
  restored[order] = np.clip(corrected, 0.0, 1.0)
  adjusted[valid_mask] = restored
  return adjusted


def _safe_test(function, *args, **kwargs) -> tuple[float, float]:
  try:
    result = function(*args, **kwargs)
    statistic = float(getattr(result, "statistic", result[0]))
    pvalue = float(getattr(result, "pvalue", result[1]))
    return statistic, pvalue
  except Exception:
    return np.nan, np.nan


def group_comparison_tests(
  frame: pd.DataFrame,
  value_column: str,
  group_column: str,
  feature_column: str | None = None,
  *,
  minimum_group_size: int = 2,
) -> pd.DataFrame:
  """Run global and pairwise tests for each displayed feature.

  Global tests are one-way ANOVA and Kruskal-Wallis. Pairwise tests are Welch
  t-test and Mann-Whitney U. Benjamini-Hochberg correction is applied
  independently to the complete set of pairwise p-values for each test family.
  """
  if frame is None or frame.empty:
    return pd.DataFrame()
  required = {value_column, group_column}
  if not required.issubset(frame.columns):
    return pd.DataFrame()

  work = frame.copy()
  work[value_column] = pd.to_numeric(work[value_column], errors="coerce")
  work[group_column] = work[group_column].fillna("Unclassified").astype(str)
  work = work.dropna(subset=[value_column])
  if work.empty:
    return pd.DataFrame()

  if feature_column and feature_column in work.columns:
    feature_groups = work.groupby(feature_column, sort=False, dropna=False)
  else:
    feature_groups = [("All", work)]

  rows: list[dict[str, object]] = []
  for feature, subset in feature_groups:
    grouped_values: dict[str, np.ndarray] = {}
    for group, values in subset.groupby(group_column, sort=False):
      numeric = pd.to_numeric(values[value_column], errors="coerce").dropna().to_numpy(float)
      if len(numeric) >= minimum_group_size:
        grouped_values[str(group)] = numeric
    groups = list(grouped_values)
    if len(groups) < 2:
      continue
    samples = [grouped_values[group] for group in groups]
    anova_stat, anova_p = _safe_test(stats.f_oneway, *samples)
    kruskal_stat, kruskal_p = _safe_test(stats.kruskal, *samples)
    for group1, group2 in combinations(groups, 2):
      values1 = grouped_values[group1]
      values2 = grouped_values[group2]
      welch_stat, welch_p = _safe_test(
        stats.ttest_ind,
        values1,
        values2,
        equal_var=False,
        nan_policy="omit",
      )
      mann_stat, mann_p = _safe_test(
        stats.mannwhitneyu,
        values1,
        values2,
        alternative="two-sided",
      )
      rows.append({
        "feature": str(feature),
        "value_column": value_column,
        "grouping_factor": group_column,
        "groups_compared_globally": "; ".join(groups),
        "global_parametric_test": "one-way ANOVA",
        "anova_F": anova_stat,
        "anova_pvalue": anova_p,
        "global_nonparametric_test": "Kruskal-Wallis",
        "kruskal_H": kruskal_stat,
        "kruskal_pvalue": kruskal_p,
        "pairwise_parametric_test": "Welch t-test",
        "pairwise_nonparametric_test": "Mann-Whitney U",
        "group1": group1,
        "group2": group2,
        "n_group1": int(len(values1)),
        "n_group2": int(len(values2)),
        "mean_group1": float(np.mean(values1)),
        "mean_group2": float(np.mean(values2)),
        "median_group1": float(np.median(values1)),
        "median_group2": float(np.median(values2)),
        "welch_t": welch_stat,
        "welch_pvalue": welch_p,
        "mannwhitney_U": mann_stat,
        "mannwhitney_pvalue": mann_p,
      })

  result = pd.DataFrame(rows)
  if result.empty:
    return result
  result["welch_qvalue_BH"] = benjamini_hochberg(result["welch_pvalue"])
  result["mannwhitney_qvalue_BH"] = benjamini_hochberg(result["mannwhitney_pvalue"])
  result["parametric_significant_q_lt_0_05"] = result["welch_qvalue_BH"].lt(0.05).fillna(False)
  result["nonparametric_significant_q_lt_0_05"] = result["mannwhitney_qvalue_BH"].lt(0.05).fillna(False)
  result["multiple_testing"] = "Benjamini-Hochberg FDR across all displayed pairwise comparisons"
  return result.sort_values(
    ["mannwhitney_qvalue_BH", "welch_qvalue_BH", "feature", "group1", "group2"],
    na_position="last",
  ).reset_index(drop=True)


def alpha_diversity_group_tests(source: pd.DataFrame) -> pd.DataFrame:
  if source is None or source.empty or "Lake_season" not in source.columns:
    return pd.DataFrame()
  outputs = []
  for metric in ("Observed_OTUs", "Chao1", "Shannon"):
    if metric not in source.columns:
      continue
    tested = group_comparison_tests(
      source,
      metric,
      "Lake_season",
      feature_column=None,
    )
    if not tested.empty:
      tested["feature"] = metric
      tested["figure"] = "Supplementary Figure 4"
      outputs.append(tested)
  return pd.concat(outputs, ignore_index=True, sort=False) if outputs else pd.DataFrame()


def taxonomy_barplot_group_tests_from_table(table: pd.DataFrame) -> pd.DataFrame:
  """Test lake groups for one seasonal taxonomy barplot exact-value table."""
  if table is None or table.empty:
    return pd.DataFrame()
  required = {"taxon", "sample", "relative_abundance_percent"}
  if not required.issubset(table.columns):
    return pd.DataFrame()
  work = table.copy()
  work["lake"] = work["sample"].astype(str).str.extract(r"^(AM|TIA|TI|VI)", expand=False)
  work = work.dropna(subset=["lake"])
  result = group_comparison_tests(
    work,
    "relative_abundance_percent",
    "lake",
    feature_column="taxon",
  )
  if not result.empty:
    result["domain"] = str(work.get("domain", pd.Series([""])).iloc[0])
    result["rank"] = str(work.get("rank", pd.Series([""])).iloc[0])
    result["season"] = str(work.get("season", pd.Series([""])).iloc[0])
    result["observation_unit"] = "individual biological sample relative abundance"
  return result


def taxonomy_explorer_group_tests(
  domain: str,
  rank: str,
  *,
  top_n: int | None = None,
  base_dir: Path | str | None = None,
) -> pd.DataFrame:
  from .article_taxonomy import article_taxonomy_profile_table

  profile = article_taxonomy_profile_table(
    domain,
    rank,
    view_mode="Individual samples",
    top_n=top_n,
    base_dir=base_dir,
  )
  if profile.empty:
    return pd.DataFrame()
  outputs = []
  for factor in ("lake", "season"):
    result = group_comparison_tests(
      profile,
      "abundance",
      factor,
      feature_column="taxon",
    )
    if not result.empty:
      result["domain"] = domain
      result["rank"] = rank
      result["observation_unit"] = "individual biological sample relative abundance"
      outputs.append(result)
  return pd.concat(outputs, ignore_index=True, sort=False) if outputs else pd.DataFrame()


def _permanova_components(distance: np.ndarray, labels: np.ndarray) -> tuple[float, float]:
  n = len(labels)
  groups = pd.unique(labels)
  if n < 3 or len(groups) < 2 or len(groups) >= n:
    return np.nan, np.nan
  squared = np.square(distance)
  total_ss = float(np.triu(squared, 1).sum() / n)
  within_ss = 0.0
  for group in groups:
    indices = np.flatnonzero(labels == group)
    if len(indices) < 2:
      continue
    group_distances = squared[np.ix_(indices, indices)]
    within_ss += float(np.triu(group_distances, 1).sum() / len(indices))
  among_ss = max(0.0, total_ss - within_ss)
  df_among = len(groups) - 1
  df_within = n - len(groups)
  if df_among <= 0 or df_within <= 0 or within_ss <= 0:
    return np.nan, among_ss / total_ss if total_ss > 0 else np.nan
  pseudo_f = (among_ss / df_among) / (within_ss / df_within)
  r_squared = among_ss / total_ss if total_ss > 0 else np.nan
  return float(pseudo_f), float(r_squared)


def permanova(
  matrix: pd.DataFrame,
  labels: pd.Series,
  *,
  permutations: int = DEFAULT_PERMUTATIONS,
  seed: int = DEFAULT_SEED,
) -> dict[str, object]:
  common = matrix.index.intersection(labels.index)
  data = matrix.loc[common].apply(pd.to_numeric, errors="coerce").fillna(0.0)
  groups = labels.loc[common].fillna("Unclassified").astype(str)
  if len(data) < 3 or groups.nunique() < 2:
    return {"status": "insufficient_groups"}
  distance = squareform(pdist(data.to_numpy(float), metric="braycurtis"))
  observed_f, r_squared = _permanova_components(distance, groups.to_numpy())
  rng = np.random.default_rng(seed)
  exceedances = 0
  valid = 0
  for _ in range(int(permutations)):
    permuted = rng.permutation(groups.to_numpy())
    statistic, _ = _permanova_components(distance, permuted)
    if np.isfinite(statistic):
      valid += 1
      if statistic >= observed_f - 1e-15:
        exceedances += 1
  pvalue = (exceedances + 1.0) / (valid + 1.0) if valid else np.nan
  return {
    "status": "PASS",
    "method": "PERMANOVA on Bray-Curtis distances",
    "pseudo_F": observed_f,
    "R2": r_squared,
    "pvalue_permutation": pvalue,
    "permutations": int(valid),
    "seed": int(seed),
    "n_samples": int(len(data)),
    "n_groups": int(groups.nunique()),
    "groups": "; ".join(pd.unique(groups)),
  }


def _pcoa_coordinates(distance: np.ndarray) -> np.ndarray:
  n = distance.shape[0]
  centering = np.eye(n) - np.ones((n, n), dtype=float) / n
  gram = -0.5 * centering @ np.square(distance) @ centering
  eigenvalues, eigenvectors = np.linalg.eigh(gram)
  order = np.argsort(eigenvalues)[::-1]
  eigenvalues = eigenvalues[order]
  eigenvectors = eigenvectors[:, order]
  positive = eigenvalues > 1e-12
  if not positive.any():
    return np.zeros((n, 1), dtype=float)
  return eigenvectors[:, positive] * np.sqrt(eigenvalues[positive])


def permdisp(
  matrix: pd.DataFrame,
  labels: pd.Series,
  *,
  permutations: int = DEFAULT_PERMUTATIONS,
  seed: int = DEFAULT_SEED,
) -> dict[str, object]:
  common = matrix.index.intersection(labels.index)
  data = matrix.loc[common].apply(pd.to_numeric, errors="coerce").fillna(0.0)
  groups = labels.loc[common].fillna("Unclassified").astype(str)
  if len(data) < 3 or groups.nunique() < 2:
    return {"status": "insufficient_groups"}
  distance = squareform(pdist(data.to_numpy(float), metric="braycurtis"))
  coordinates = _pcoa_coordinates(distance)

  def centroid_distances(group_values: np.ndarray) -> np.ndarray:
    output = np.zeros(len(group_values), dtype=float)
    for group in pd.unique(group_values):
      indices = np.flatnonzero(group_values == group)
      centroid = coordinates[indices].mean(axis=0)
      output[indices] = np.linalg.norm(coordinates[indices] - centroid, axis=1)
    return output

  label_array = groups.to_numpy()
  observed_distances = centroid_distances(label_array)
  samples = [observed_distances[label_array == group] for group in pd.unique(label_array)]
  observed_f, anova_p = _safe_test(stats.f_oneway, *samples)
  kruskal_h, kruskal_p = _safe_test(stats.kruskal, *samples)
  rng = np.random.default_rng(seed)
  exceedances = 0
  valid = 0
  for _ in range(int(permutations)):
    permuted = rng.permutation(label_array)
    permuted_distances = centroid_distances(permuted)
    permuted_samples = [permuted_distances[permuted == group] for group in pd.unique(permuted)]
    statistic, _ = _safe_test(stats.f_oneway, *permuted_samples)
    if np.isfinite(statistic):
      valid += 1
      if statistic >= observed_f - 1e-15:
        exceedances += 1
  permutation_p = (exceedances + 1.0) / (valid + 1.0) if valid else np.nan
  return {
    "status": "PASS",
    "method": "PERMDISP / betadisper on distances to group centroids",
    "F": observed_f,
    "anova_pvalue": anova_p,
    "kruskal_H": kruskal_h,
    "kruskal_pvalue": kruskal_p,
    "pvalue_permutation": permutation_p,
    "permutations": int(valid),
    "seed": int(seed),
    "n_samples": int(len(data)),
    "n_groups": int(groups.nunique()),
    "groups": "; ".join(pd.unique(groups)),
  }


def beta_tests_from_profile_table(
  profile: pd.DataFrame,
  *,
  value_column: str = "abundance",
  sample_column: str = "group",
  taxon_column: str = "taxon",
  factors: tuple[str, ...] = ("lake", "season"),
  permutations: int = DEFAULT_PERMUTATIONS,
  seed: int = DEFAULT_SEED,
) -> pd.DataFrame:
  if profile is None or profile.empty:
    return pd.DataFrame()
  required = {value_column, sample_column, taxon_column}
  if not required.issubset(profile.columns):
    return pd.DataFrame()
  matrix = profile.pivot_table(
    index=sample_column,
    columns=taxon_column,
    values=value_column,
    aggfunc="sum",
    fill_value=0.0,
  )
  metadata_columns = [sample_column] + [factor for factor in factors if factor in profile.columns]
  metadata = profile[metadata_columns].drop_duplicates(sample_column).set_index(sample_column)
  rows: list[dict[str, object]] = []
  for factor in factors:
    if factor not in metadata.columns or metadata[factor].nunique() < 2:
      continue
    perma = permanova(matrix, metadata[factor], permutations=permutations, seed=seed)
    rows.append({"analysis": "PERMANOVA", "factor": factor, **perma})
    dispersion = permdisp(matrix, metadata[factor], permutations=permutations, seed=seed)
    rows.append({"analysis": "PERMDISP", "factor": factor, **dispersion})
  return pd.DataFrame(rows)


def frozen_ordination_inference(
  domain: str,
  *,
  permutations: int = DEFAULT_PERMUTATIONS,
  seed: int = DEFAULT_SEED,
) -> tuple[pd.DataFrame, pd.DataFrame]:
  from .article_frozen_taxonomy_panels import frozen_taxonomy_domain_data

  data = frozen_taxonomy_domain_data(domain)
  profile = data["profile"].set_index("taxon").T
  profile.index.name = "Sample"
  scores = data["nmds"].copy().set_index("Sample")
  common = profile.index.intersection(scores.index)
  profile = profile.loc[common]
  scores = scores.loc[common]

  beta_rows: list[dict[str, object]] = []
  for factor in ("Lake", "Season"):
    if factor not in scores.columns or scores[factor].nunique() < 2:
      continue
    perma = permanova(profile, scores[factor], permutations=permutations, seed=seed)
    beta_rows.append({"domain": domain, "ordination": "NMDS / PCoA", "analysis": "PERMANOVA", "factor": factor, **perma})
    dispersion = permdisp(profile, scores[factor], permutations=permutations, seed=seed)
    beta_rows.append({"domain": domain, "ordination": "NMDS / PCoA", "analysis": "PERMDISP", "factor": factor, **dispersion})
  beta = pd.DataFrame(beta_rows)

  frozen_stats = data["statistics"].iloc[0].to_dict()
  display = dict(data["display"])
  rda = pd.DataFrame([{
    "domain": domain,
    "analysis": "RDA global permutation test",
    "method": "Hellinger-transformed genus composition constrained by standardized environmental variables; global permutation test",
    "R2": frozen_stats.get("RDA_R2", np.nan),
    "adjusted_R2": frozen_stats.get("RDA_adjusted_R2", frozen_stats.get("RDA_adj_R2", np.nan)),
    "pseudo_F": frozen_stats.get("RDA_F", frozen_stats.get("RDA_pseudo_F", np.nan)),
    "pvalue_permutation": frozen_stats.get("RDA_p", np.nan),
    "RDA1_constrained_variation_percent": display.get("rda1_percent", np.nan),
    "RDA2_constrained_variation_percent": display.get("rda2_percent", np.nan),
    "permutations": frozen_stats.get("RDA_permutations", 999),
    "NMDS_stress": frozen_stats.get("NMDS_stress", np.nan),
    "source": "frozen article Figure 4/5 ordination statistics",
  }])
  return beta, rda


def inference_summary(table: pd.DataFrame) -> str:
  if table is None or table.empty:
    return "No valid statistical comparison was available."
  if "analysis" in table.columns and table["analysis"].isin(["PERMANOVA", "PERMDISP"]).any():
    parts = []
    for _, row in table.iterrows():
      pvalue = row.get("pvalue_permutation", np.nan)
      statistic = row.get("pseudo_F", row.get("F", np.nan))
      stat_label = "pseudo-F" if row.get("analysis") == "PERMANOVA" else "F"
      r2_text = f", R²={float(row['R2']):.3g}" if pd.notna(row.get("R2")) else ""
      parts.append(
        f"{row.get('analysis')} ({row.get('factor')}): {stat_label}={float(statistic):.3g}{r2_text}, p={float(pvalue):.3g}"
        if pd.notna(statistic) and pd.notna(pvalue)
        else f"{row.get('analysis')} ({row.get('factor')}): insufficient result"
      )
    return "; ".join(parts) + "."

  global_features = int(table["feature"].nunique()) if "feature" in table.columns else 1
  anova_significant = int(table.loc[pd.to_numeric(table.get("anova_pvalue"), errors="coerce").lt(0.05), "feature"].nunique()) if "anova_pvalue" in table.columns and "feature" in table.columns else 0
  kruskal_significant = int(table.loc[pd.to_numeric(table.get("kruskal_pvalue"), errors="coerce").lt(0.05), "feature"].nunique()) if "kruskal_pvalue" in table.columns and "feature" in table.columns else 0
  welch_pairs = int(pd.to_numeric(table.get("welch_qvalue_BH"), errors="coerce").lt(0.05).sum()) if "welch_qvalue_BH" in table.columns else 0
  mann_pairs = int(pd.to_numeric(table.get("mannwhitney_qvalue_BH"), errors="coerce").lt(0.05).sum()) if "mannwhitney_qvalue_BH" in table.columns else 0
  return (
    f"Features tested: {global_features}; global ANOVA p<0.05: {anova_significant}; "
    f"global Kruskal-Wallis p<0.05: {kruskal_significant}; "
    f"FDR-significant Welch pairs: {welch_pairs}; "
    f"FDR-significant Mann-Whitney pairs: {mann_pairs}."
  )
