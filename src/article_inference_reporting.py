from __future__ import annotations

import numpy as np
import pandas as pd


def _number(value: object) -> float:
  return pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0]


def inference_summary(table: pd.DataFrame) -> str:
  """Return a compact result summary without hiding test values."""
  if table is None or table.empty:
    return "No valid statistical comparison was available."

  if "analysis" in table.columns and table["analysis"].isin(["PERMANOVA", "PERMDISP"]).any():
    parts: list[str] = []
    for _, row in table.iterrows():
      analysis = str(row.get("analysis", ""))
      factor = str(row.get("factor", ""))
      pvalue = _number(row.get("pvalue_permutation", np.nan))
      if analysis == "PERMANOVA":
        statistic = _number(row.get("pseudo_F", np.nan))
        r_squared = _number(row.get("R2", np.nan))
        result = f"pseudo-F={statistic:.3g}"
        if pd.notna(r_squared):
          result += f", R²={r_squared:.3g}"
      else:
        statistic = _number(row.get("F", np.nan))
        kruskal_p = _number(row.get("kruskal_pvalue", np.nan))
        result = f"F={statistic:.3g}"
        if pd.notna(kruskal_p):
          result += f", Kruskal p={kruskal_p:.3g}"
      if pd.notna(pvalue):
        result += f", permutation p={pvalue:.3g}"
      parts.append(f"{analysis} ({factor}): {result}")
    return "; ".join(parts) + "."

  feature_count = int(table["feature"].nunique()) if "feature" in table.columns else 1
  anova = pd.to_numeric(table.get("anova_pvalue", pd.Series(np.nan, index=table.index)), errors="coerce")
  kruskal = pd.to_numeric(table.get("kruskal_pvalue", pd.Series(np.nan, index=table.index)), errors="coerce")
  if "feature" in table.columns:
    anova_count = int(table.loc[anova.lt(0.05), "feature"].astype(str).nunique())
    kruskal_count = int(table.loc[kruskal.lt(0.05), "feature"].astype(str).nunique())
  else:
    anova_count = int(anova.lt(0.05).any())
    kruskal_count = int(kruskal.lt(0.05).any())
  welch_q = pd.to_numeric(table.get("welch_qvalue_BH", pd.Series(np.nan, index=table.index)), errors="coerce")
  mann_q = pd.to_numeric(table.get("mannwhitney_qvalue_BH", pd.Series(np.nan, index=table.index)), errors="coerce")
  return (
    f"Features tested: {feature_count}; global ANOVA p<0.05: {anova_count}; "
    f"global Kruskal-Wallis p<0.05: {kruskal_count}; "
    f"FDR-significant Welch pairs: {int(welch_q.lt(0.05).sum())}; "
    f"FDR-significant Mann-Whitney pairs: {int(mann_q.lt(0.05).sum())}."
  )
