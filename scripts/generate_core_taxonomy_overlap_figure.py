#!/usr/bin/env python3
"""Generate article Venn diagrams for Phylum, Order and Family.

The source of truth is ``st8_taxonomy_summary_by_group.csv``. Only records whose
``data_layer`` is Metagenomics are used. The same grouping and presence rule are
used by the Streamlit Taxonomy panel:

* AMD systems;
* ferruginous lakes/sediments;
* hydrothermal Fe-rich mats;
* presence means ``count_or_abundance > 0``.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import pandas as pd


LEVELS = (
  ("Phylum", 26),
  ("Order", 27),
  ("Family", 28),
)
ARTICLE_GROUPS = (
  "AMD systems",
  "Ferruginous lakes/sediments",
  "Hydrothermal Fe-rich mats",
)


def broad_group(value: object) -> str:
  text = str(value or "")
  if any(token in text for token in ("AMD", "Akron", "Richmond")):
    return "AMD systems"
  if any(token in text for token in ("Lake Towuti", "Lake Matano", "Lake Superior")):
    return "Ferruginous lakes/sediments"
  if "Hydrothermal" in text:
    return "Hydrothermal Fe-rich mats"
  return "Other/unassigned"


def resolve_input(base_dir: Path, explicit: Path | None) -> Path:
  candidates = [
    explicit,
    base_dir / "data" / "st8_taxonomy_summary_by_group.csv",
    base_dir / "tables" / "st8_taxonomy_summary_by_group.csv",
    base_dir / "05_Source_Data_and_Audit" / "st8_taxonomy_summary_by_group.csv",
    base_dir / "05_Source_Data_and_Audit" / "st8" / "st8_taxonomy_summary_by_group.csv",
  ]
  for candidate in candidates:
    if candidate is not None and candidate.exists():
      return candidate
  raise FileNotFoundError("st8_taxonomy_summary_by_group.csv was not found")


def prepare_source(path: Path) -> pd.DataFrame:
  source = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)
  required = {
    "taxonomy_level",
    "ST8_group",
    "data_layer",
    "matrix_column",
    "taxon",
    "count_or_abundance",
  }
  missing = required.difference(source.columns)
  if missing:
    raise RuntimeError(f"{path} is missing columns: {sorted(missing)}")
  source["count_or_abundance"] = pd.to_numeric(
    source["count_or_abundance"], errors="coerce"
  ).fillna(0.0)
  source = source[
    source["data_layer"].astype(str).str.casefold().str.contains(
      "metagenomic", na=False
    )
    & source["count_or_abundance"].gt(0)
  ].copy()
  source["article_environment_group"] = source["ST8_group"].map(broad_group)
  return source[source["article_environment_group"].isin(ARTICLE_GROUPS)].copy()


def sets_for_level(
  source: pd.DataFrame,
  level: str,
) -> tuple[dict[str, set[str]], pd.DataFrame]:
  work = source[source["taxonomy_level"].astype(str).eq(level)].copy()
  sets = {
    group: set(
      work.loc[work["article_environment_group"].eq(group), "taxon"]
      .dropna().astype(str)
    )
    for group in ARTICLE_GROUPS
  }
  if any(not values for values in sets.values()):
    raise RuntimeError(f"{level}: at least one article group has no positive taxa")
  return sets, work


def region_members(sets: dict[str, set[str]]) -> dict[str, set[str]]:
  a, b, c = (sets[group] for group in ARTICLE_GROUPS)
  return {
    "AMD only": a - b - c,
    "Ferruginous only": b - a - c,
    "Hydrothermal only": c - a - b,
    "AMD ∩ Ferruginous": (a & b) - c,
    "AMD ∩ Hydrothermal": (a & c) - b,
    "Ferruginous ∩ Hydrothermal": (b & c) - a,
    "Common to all": a & b & c,
    "Union": a | b | c,
  }


def save_figure(fig, stem: Path, destinations: list[Path]) -> None:
  stem.parent.mkdir(parents=True, exist_ok=True)
  for extension in ("png", "pdf", "svg"):
    output = stem.with_suffix(f".{extension}")
    fig.savefig(output, dpi=300, bbox_inches="tight", facecolor="white")
  plt.close(fig)
  for destination in destinations:
    destination.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "pdf", "svg"):
      shutil.copy2(
        stem.with_suffix(f".{extension}"),
        destination / f"{stem.name}.{extension}",
      )


def make_venn(
  source: pd.DataFrame,
  level: str,
  figure_number: int,
  base_dir: Path,
  article_root: Path,
) -> dict[str, object]:
  sets, work = sets_for_level(source, level)
  regions = region_members(sets)

  fig, axis = plt.subplots(figsize=(12.5, 10.5), dpi=300)
  circles = (
    (0.39, 0.60, "#D5E8FF", ARTICLE_GROUPS[0], 0.935),
    (0.61, 0.60, "#DFF3DC", ARTICLE_GROUPS[1], 0.935),
    (0.50, 0.39, "#FFE6CC", ARTICLE_GROUPS[2], 0.105),
  )
  for x, y, colour, label, label_y in circles:
    axis.add_patch(Circle(
      (x, y), 0.285,
      facecolor=colour,
      edgecolor="#263238",
      alpha=0.62,
      linewidth=1.8,
    ))
    axis.text(
      x, label_y, label,
      ha="center", va="center",
      fontsize=12, fontweight="bold",
    )

  labels = (
    (0.25, 0.67, "AMD only"),
    (0.75, 0.67, "Ferruginous only"),
    (0.50, 0.18, "Hydrothermal only"),
    (0.50, 0.70, "AMD ∩ Ferruginous"),
    (0.37, 0.43, "AMD ∩ Hydrothermal"),
    (0.63, 0.43, "Ferruginous ∩ Hydrothermal"),
    (0.50, 0.52, "Common to all"),
  )
  for x, y, key in labels:
    axis.text(
      x, y, str(len(regions[key])),
      ha="center", va="center",
      fontsize=18 if key == "Common to all" else 15,
      fontweight="bold",
      color="#8B0000" if key == "Common to all" else "#111827",
    )

  axis.set_title(
    f"Supplementary Figure {figure_number}. {level}-level overlap across metagenomic iron-rich groups",
    fontsize=16,
    fontweight="bold",
    pad=22,
  )
  fig.text(
    0.5, 0.012,
    "Metagenomics only • presence = count_or_abundance > 0 • control and unassigned records excluded",
    ha="center", va="bottom", fontsize=10,
  )
  axis.set_xlim(0.05, 0.95)
  axis.set_ylim(0.0, 1.0)
  axis.set_axis_off()

  stem_name = f"SupplementaryFigure{figure_number}_taxonomic_overlap_{level.lower()}_original"
  stem = base_dir / "outputs" / "final_publication_figures" / stem_name
  save_figure(
    fig,
    stem,
    [
      base_dir / "outputs" / "app_supplementary_figures",
      article_root / "03_Supplementary_Figures",
    ],
  )

  derived = base_dir / "data" / "final_publication_derived"
  derived.mkdir(parents=True, exist_ok=True)
  member_rows: list[dict[str, object]] = []
  for region, taxa in regions.items():
    for taxon in sorted(taxa):
      member_rows.append({
        "figure": figure_number,
        "taxonomy_level": level,
        "data_layer": "Metagenomics",
        "region": region,
        "taxon": taxon,
      })
  pd.DataFrame(member_rows).to_csv(
    derived / f"{stem_name}_source.csv",
    index=False,
  )
  work.to_csv(
    derived / f"{stem_name}_positive_metagenomic_records.csv",
    index=False,
  )
  return {
    "figure": figure_number,
    "taxonomy_level": level,
    "n_metagenome_columns": int(work["matrix_column"].nunique()),
    "n_common_to_all": len(regions["Common to all"]),
    "n_union": len(regions["Union"]),
    "stem": str(stem),
  }


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[1])
  parser.add_argument("--article-root", type=Path, default=None)
  parser.add_argument("--input", type=Path, default=None)
  arguments = parser.parse_args()

  base_dir = arguments.base_dir.resolve()
  article_root = (arguments.article_root or base_dir).resolve()
  input_path = resolve_input(
    base_dir,
    arguments.input.resolve() if arguments.input else None,
  )
  source = prepare_source(input_path)
  results = [
    make_venn(source, level, number, base_dir, article_root)
    for level, number in LEVELS
  ]
  report = pd.DataFrame(results)
  report_path = (
    base_dir / "data" / "final_publication_derived"
    / "taxonomy_overlap_metagenomics_report.csv"
  )
  report.to_csv(report_path, index=False)
  print(report.to_string(index=False))
  print(f"Source: {input_path}")
  print(f"Report: {report_path}")


if __name__ == "__main__":
  main()
