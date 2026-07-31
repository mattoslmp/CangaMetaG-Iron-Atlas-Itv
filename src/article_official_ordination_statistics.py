from __future__ import annotations

"""Load the exact ordination significance tables distributed with the article.

The public app and final scripts must report the same PERMANOVA, dispersion and
RDA values already validated in the article package. Recalculation is retained
only as a fallback when the official tables are absent.
"""

from pathlib import Path

import numpy as np
import pandas as pd


BASE_DIR = Path(__file__).resolve().parents[1]
TABLE_DIR = BASE_DIR / "reproducibility" / "ordination_reproducibility" / "tables"


def _domain(domain: str) -> str:
  return "Archaea" if str(domain).casefold().startswith("arch") else "Bacteria"


def _beta_path(domain: str, base_dir: Path) -> Path:
  return (
    base_dir
    / "reproducibility"
    / "ordination_reproducibility"
    / "tables"
    / f"{domain}_NMDS_PERMANOVA_and_dispersion_tests.csv"
  )


def _rda_path(domain: str, base_dir: Path) -> Path:
  return (
    base_dir
    / "reproducibility"
    / "ordination_reproducibility"
    / "tables"
    / f"{domain}_RDA_model_statistics.csv"
  )


def official_ordination_inference(
  domain: str,
  *,
  base_dir: Path | str | None = None,
  permutations: int = 999,
  seed: int = 42,
) -> tuple[pd.DataFrame, pd.DataFrame]:
  """Return official Figure 4/5 NMDS and RDA statistical results."""
  canonical = _domain(domain)
  root = Path(base_dir).resolve() if base_dir is not None else BASE_DIR
  beta_file = _beta_path(canonical, root)
  rda_file = _rda_path(canonical, root)

  if beta_file.exists() and rda_file.exists():
    source_beta = pd.read_csv(beta_file)
    beta_rows: list[dict[str, object]] = []
    for _, row in source_beta.iterrows():
      factor = str(row.get("factor", ""))
      beta_rows.append({
        "domain": canonical,
        "ordination": "NMDS / PCoA",
        "analysis": "PERMANOVA",
        "factor": factor,
        "method": "PERMANOVA on Bray-Curtis distances",
        "pseudo_F": pd.to_numeric(row.get("PERMANOVA_pseudo_F"), errors="coerce"),
        "pvalue_permutation": pd.to_numeric(row.get("PERMANOVA_p_value"), errors="coerce"),
        "df_between": pd.to_numeric(row.get("PERMANOVA_df_between"), errors="coerce"),
        "df_within": pd.to_numeric(row.get("PERMANOVA_df_within"), errors="coerce"),
        "permutations": int(pd.to_numeric(row.get("PERMANOVA_permutations"), errors="coerce")),
        "source": str(beta_file.relative_to(root)),
        "official_article_result": True,
      })
      beta_rows.append({
        "domain": canonical,
        "ordination": "NMDS / PCoA",
        "analysis": "PERMDISP",
        "factor": factor,
        "method": "PERMDISP / betadisper permutation test",
        "F": pd.to_numeric(row.get("dispersion_F"), errors="coerce"),
        "pvalue_permutation": pd.to_numeric(row.get("dispersion_p_value"), errors="coerce"),
        "df_between": pd.to_numeric(row.get("dispersion_df_between"), errors="coerce"),
        "df_within": pd.to_numeric(row.get("dispersion_df_within"), errors="coerce"),
        "permutations": int(pd.to_numeric(row.get("dispersion_permutations"), errors="coerce")),
        "source": str(beta_file.relative_to(root)),
        "official_article_result": True,
      })
    beta = pd.DataFrame(beta_rows)

    source_rda = pd.read_csv(rda_file)
    rda = source_rda.rename(columns={
      "global_permutation_p": "pvalue_permutation",
      "RDA1_constrained_variance_percent": "RDA1_constrained_variation_percent",
      "RDA2_constrained_variance_percent": "RDA2_constrained_variation_percent",
    }).copy()
    rda.insert(1, "analysis", "RDA global permutation test")
    rda.insert(
      2,
      "method",
      "Hellinger-transformed genus composition constrained by standardized environmental variables; global and axis permutation tests",
    )
    rda["source"] = str(rda_file.relative_to(root))
    rda["official_article_result"] = True
    return beta, rda

  from .article_inference_statistics import frozen_ordination_inference

  beta, rda = frozen_ordination_inference(
    canonical,
    permutations=permutations,
    seed=seed,
  )
  if not beta.empty:
    beta["official_article_result"] = False
    beta["source"] = "fallback calculation from frozen Figure 4/5 matrices"
  if not rda.empty:
    rda["official_article_result"] = False
  return beta, rda
