#!/usr/bin/env python3
from __future__ import annotations

"""Generate inferential tables shown below article boxplots and barplots.

The script uses the same functions imported by the Streamlit app. It writes:
- alpha-diversity ANOVA/Kruskal-Wallis and Welch/Mann-Whitney results;
- exact Figure 2/3 Top-14 seasonal barplot lake-comparison results;
- taxonomy explorer group tests for Phylum, Order, Family and Genus;
- Figure 4/5 NMDS/PCoA PERMANOVA/PERMDISP and global RDA results.
"""

import argparse
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.article_inference_reporting import inference_summary  # noqa: E402
from src.article_inference_statistics import (  # noqa: E402
  alpha_diversity_group_tests,
  frozen_ordination_inference,
  taxonomy_barplot_group_tests_from_table,
  taxonomy_explorer_group_tests,
)
from src.article_taxonomy import article_season_barplot, load_article_alpha_source  # noqa: E402


SCRIPT_VERSION = "2026-07-31-final-v2-exact-figure2-3-tests"


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--base-dir", type=Path, default=ROOT)
  parser.add_argument("--top-n", type=int, default=20)
  parser.add_argument("--permutations", type=int, default=999)
  parser.add_argument("--seed", type=int, default=42)
  return parser.parse_args()


def write_csv(frame, path: Path, outputs: list[str], base_dir: Path) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  frame.to_csv(path, index=False)
  outputs.append(str(path.relative_to(base_dir)))


def main() -> int:
  args = parse_args()
  base_dir = args.base_dir.resolve()
  derived = base_dir / "data" / "final_publication_derived"
  reports = base_dir / "reports"
  derived.mkdir(parents=True, exist_ok=True)
  reports.mkdir(parents=True, exist_ok=True)

  outputs: list[str] = []
  summaries: dict[str, object] = {}

  alpha_source = load_article_alpha_source(base_dir)
  alpha_tests = alpha_diversity_group_tests(alpha_source)
  alpha_path = derived / "SupplementaryFigure4_alpha_diversity_group_tests.csv"
  write_csv(alpha_tests, alpha_path, outputs, base_dir)
  summaries["alpha_diversity"] = inference_summary(alpha_tests)

  # Figures 2 and 3 use the exact Top-14 rule and separate Dry/Rainy panels.
  for domain in ("Bacteria", "Archaea"):
    figure_number = "Figure2" if domain == "Bacteria" else "Figure3"
    for season in ("Dry", "Rainy"):
      _, exact_table, _ = article_season_barplot(
        domain,
        "Phylum",
        season,
        top_n=14,
        base_dir=base_dir,
      )
      tested = taxonomy_barplot_group_tests_from_table(exact_table)
      path = derived / f"{figure_number}_{domain}_Phylum_{season}_lake_group_tests.csv"
      write_csv(tested, path, outputs, base_dir)
      summaries[f"{figure_number}_{domain}_{season}"] = inference_summary(tested)

  # General explorer tables use the active Top-N parameter and test both lake
  # and season factors for every displayed taxon.
  for domain in ("Bacteria", "Archaea"):
    for rank in ("Phylum", "Order", "Family", "Genus"):
      tested = taxonomy_explorer_group_tests(
        domain,
        rank,
        top_n=args.top_n,
        base_dir=base_dir,
      )
      if tested.empty:
        continue
      path = derived / f"Taxonomy_{domain}_{rank}_top{args.top_n}_group_tests.csv"
      write_csv(tested, path, outputs, base_dir)
      summaries[f"taxonomy_{domain}_{rank}"] = inference_summary(tested)

  for domain in ("Bacteria", "Archaea"):
    beta, rda = frozen_ordination_inference(
      domain,
      permutations=args.permutations,
      seed=args.seed,
    )
    figure_number = "Figure4" if domain == "Bacteria" else "Figure5"
    beta_path = derived / f"{figure_number}_{domain}_NMDS_PCoA_PERMANOVA_PERMDISP.csv"
    rda_path = derived / f"{figure_number}_{domain}_RDA_global_statistics.csv"
    write_csv(beta, beta_path, outputs, base_dir)
    write_csv(rda, rda_path, outputs, base_dir)
    summaries[f"{figure_number}_{domain}_NMDS_PCoA"] = inference_summary(beta)
    summaries[f"{figure_number}_{domain}_RDA"] = rda.to_dict("records")

  report = {
    "script": "scripts/final_publication_figures/08_generate_group_comparison_statistics.py",
    "script_version": SCRIPT_VERSION,
    "shared_app_module": "src/article_inference_statistics.py",
    "reporting_module": "src/article_inference_reporting.py",
    "tests": {
      "global_parametric": "one-way ANOVA",
      "global_nonparametric": "Kruskal-Wallis",
      "pairwise_parametric": "Welch t-test",
      "pairwise_nonparametric": "Mann-Whitney U",
      "pairwise_multiple_testing": "Benjamini-Hochberg FDR",
      "ordination_location": "PERMANOVA on Bray-Curtis distances",
      "ordination_dispersion": "PERMDISP/betadisper",
      "rda": "global permutation test from frozen article results",
    },
    "figure2_3_top_n": 14,
    "taxonomy_explorer_top_n": args.top_n,
    "permutations": args.permutations,
    "seed": args.seed,
    "source_values_modified": False,
    "outputs": outputs,
    "summaries": summaries,
  }
  report_path = reports / "FINAL_GROUP_COMPARISON_STATISTICS_REPORT.json"
  report_path.write_text(
    json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )
  print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
