#!/usr/bin/env python3
"""Generate Supplementary Figure 31A–C from common metagenomic taxa.

The script uses the same source table, groups and presence rule as the Venn
figures and the Streamlit Taxonomy panel. All common Phylum, Order and Family
taxa are retained; no Top-N filtering is applied.
"""

from __future__ import annotations

import argparse
import base64
from pathlib import Path
import shutil

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image


LEVEL_SPECS = (
  ("Phylum", "A"),
  ("Order", "B"),
  ("Family", "C"),
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


def taxon_name(value: object) -> str:
  text = str(value or "").strip()
  parts = [part.strip() for part in text.split(":") if part.strip()]
  return parts[-1] if parts else "Unclassified"


def sample_label(matrix_column: object, group: object) -> str:
  column = str(matrix_column or "").strip()
  group_text = str(group or "")
  replacements = (
    ("Main iron-rich/AMD group: Richmond Mine / Iron Mountain AMD", "Richmond AMD"),
    ("Additional AMD group: Akron / Pennsylvania–Ohio lab-enriched AMD", "Akron AMD"),
    ("Ferruginous lake/sediment group: Lake Towuti", "Lake Towuti"),
    ("Ferruginous lake/sediment group: Lake Matano", "Lake Matano"),
    ("Ferruginous lake/sediment group: Lake Superior", "Lake Superior"),
    ("Optional outgroup: Hydrothermal Fe-rich mats", "Hydrothermal mats"),
  )
  short_group = next(
    (short for full, short in replacements if full == group_text),
    group_text[:28],
  )
  return f"{short_group} | {column}"


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


def export(fig, stem: Path, destinations: list[Path]) -> None:
  """Export one high-resolution raster once and package it as PNG/PDF/SVG.

  Large heatmaps with 51 fully labelled columns can make native vector backends
  hang or leave zero-byte PDFs. The 240-dpi PNG remains the source render; PDF
  and SVG embed that exact render so all cells and labels stay identical.
  """
  stem.parent.mkdir(parents=True, exist_ok=True)
  png_path = stem.with_suffix(".png")
  fig.savefig(
    png_path,
    dpi=240,
    bbox_inches="tight",
    facecolor="white",
  )
  plt.close(fig)

  with Image.open(png_path) as image:
    rgb = image.convert("RGB")
    rgb.save(stem.with_suffix(".pdf"), "PDF", resolution=240.0)
    width, height = rgb.size

  encoded = base64.b64encode(png_path.read_bytes()).decode("ascii")
  stem.with_suffix(".svg").write_text(
    (
      f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
      f'height="{height}" viewBox="0 0 {width} {height}">'
      f'<image width="{width}" height="{height}" '
      f'href="data:image/png;base64,{encoded}"/></svg>'
    ),
    encoding="utf-8",
  )

  for destination in destinations:
    destination.mkdir(parents=True, exist_ok=True)
    for extension in ("png", "pdf", "svg"):
      shutil.copy2(
        stem.with_suffix(f".{extension}"),
        destination / f"{stem.name}.{extension}",
      )


def make_level(
  source: pd.DataFrame,
  base_dir: Path,
  article_root: Path,
  level: str,
  suffix: str,
) -> dict[str, object]:
  work = source[source["taxonomy_level"].astype(str).eq(level)].copy()
  sets = {
    group: set(
      work.loc[work["article_environment_group"].eq(group), "taxon"]
      .dropna().astype(str)
    )
    for group in ARTICLE_GROUPS
  }
  if any(not values for values in sets.values()):
    raise RuntimeError(f"{level}: at least one article group has no taxa")
  common = sorted(set.intersection(*sets.values()))
  if not common:
    raise RuntimeError(f"{level}: no taxon is common to all article groups")

  common_work = work[work["taxon"].astype(str).isin(common)].copy()
  sample_metadata = (
    common_work[["matrix_column", "ST8_group", "article_environment_group"]]
    .drop_duplicates("matrix_column")
  )
  sample_metadata["sample_label"] = sample_metadata.apply(
    lambda row: sample_label(row["matrix_column"], row["ST8_group"]),
    axis=1,
  )
  sample_metadata["group_order"] = sample_metadata["article_environment_group"].map(
    {group: index for index, group in enumerate(ARTICLE_GROUPS)}
  )
  sample_metadata = sample_metadata.sort_values(
    ["group_order", "ST8_group", "matrix_column"],
    kind="stable",
  )

  abundance = common_work.pivot_table(
    index="taxon",
    columns="matrix_column",
    values="count_or_abundance",
    aggfunc="sum",
    fill_value=0.0,
  )
  ordered_columns = [
    column for column in sample_metadata["matrix_column"].astype(str)
    if column in abundance.columns
  ]
  abundance = abundance.loc[:, ordered_columns]
  abundance = abundance.loc[
    abundance.sum(axis=1).sort_values(ascending=False).index
  ]
  abundance.index = [taxon_name(value) for value in abundance.index]
  if abundance.index.duplicated().any():
    abundance = abundance.groupby(level=0, sort=False).sum()
  abundance.columns = sample_metadata.set_index("matrix_column").loc[
    abundance.columns, "sample_label"
  ].tolist()

  means = abundance.mean(axis=1)
  standard = abundance.std(axis=1, ddof=0).replace(0.0, np.nan)
  zscore = abundance.sub(means, axis=0).div(standard, axis=0).fillna(0.0)

  derived = base_dir / "data" / "final_publication_derived"
  derived.mkdir(parents=True, exist_ok=True)
  stem_name = f"SupplementaryFigure31{suffix}_common_taxa_{level.lower()}_heatmap"
  abundance.to_csv(derived / f"{stem_name}_exact_abundance_source.csv")
  zscore.to_csv(derived / f"{stem_name}_row_zscore_source.csv")
  common_work.to_csv(
    derived / f"{stem_name}_positive_metagenomic_records.csv",
    index=False,
  )

  n_rows, n_columns = zscore.shape
  fig, axis = plt.subplots(
    figsize=(
      max(18, min(30, 7.0 + n_columns * 0.43)),
      max(12, min(30, 3.5 + n_rows * 0.30)),
    ),
    dpi=240,
  )
  values = zscore.to_numpy(float)
  maximum = max(
    abs(float(np.nanmin(values))),
    abs(float(np.nanmax(values))),
    1e-9,
  )
  image = axis.imshow(
    values,
    aspect="auto",
    cmap="RdBu_r",
    vmin=-maximum,
    vmax=maximum,
    interpolation="nearest",
  )
  axis.set_xticks(np.arange(n_columns))
  axis.set_xticklabels(
    zscore.columns,
    rotation=55,
    ha="right",
    va="top",
    rotation_mode="anchor",
    fontsize=9,
  )
  axis.set_yticks(np.arange(n_rows))
  axis.set_yticklabels(zscore.index, fontsize=10)
  axis.tick_params(axis="x", length=0, pad=8)
  axis.tick_params(axis="y", length=0, pad=6)
  axis.set_xlabel(
    "Metagenome sample grouped by iron-rich environment",
    fontsize=15,
    fontweight="bold",
    labelpad=18,
  )
  axis.set_ylabel(level, fontsize=15, fontweight="bold", labelpad=10)
  axis.set_title(
    f"Supplementary Figure 31{suffix}. {level} shared by all three metagenomic groups",
    fontsize=17,
    fontweight="bold",
    pad=18,
  )
  axis.set_xticks(np.arange(-0.5, n_columns, 1), minor=True)
  axis.set_yticks(np.arange(-0.5, n_rows, 1), minor=True)
  axis.grid(which="minor", color="white", linewidth=0.65)
  axis.tick_params(which="minor", bottom=False, left=False)
  colourbar = fig.colorbar(image, ax=axis, pad=0.012, fraction=0.025)
  colourbar.set_label("Row z-score", fontsize=14, fontweight="bold")
  colourbar.ax.tick_params(labelsize=11)
  fig.subplots_adjust(left=0.22, right=0.94, bottom=0.33, top=0.92)

  stem = base_dir / "outputs" / "final_publication_figures" / stem_name
  export(
    fig,
    stem,
    [
      base_dir / "outputs" / "app_supplementary_figures",
      article_root / "03_Supplementary_Figures",
    ],
  )
  return {
    "panel": f"31{suffix}",
    "taxonomy_level": level,
    "n_common_taxa": int(n_rows),
    "n_metagenome_samples": int(n_columns),
    "stem": str(stem),
  }


def main() -> None:
  parser = argparse.ArgumentParser()
  parser.add_argument("--base-dir", type=Path, default=Path(__file__).resolve().parents[2])
  parser.add_argument("--article-root", type=Path, default=None)
  parser.add_argument("--input", type=Path, default=None)
  arguments = parser.parse_args()

  base_dir = arguments.base_dir.resolve()
  article_root = (arguments.article_root or base_dir).resolve()
  input_path = resolve_input(base_dir, arguments.input.resolve() if arguments.input else None)
  source = prepare_source(input_path)

  for directory in (
    base_dir / "outputs" / "final_publication_figures",
    base_dir / "outputs" / "app_supplementary_figures",
    article_root / "03_Supplementary_Figures",
  ):
    for obsolete in directory.glob("SupplementaryFigure31_common_taxa_heatmap*"):
      if obsolete.is_file():
        obsolete.unlink()

  results = [
    make_level(source, base_dir, article_root, level, suffix)
    for level, suffix in LEVEL_SPECS
  ]
  report = pd.DataFrame(results)
  report_path = (
    base_dir / "data" / "final_publication_derived"
    / "SupplementaryFigure31_metagenomics_report.csv"
  )
  report.to_csv(report_path, index=False)
  print(report.to_string(index=False))
  print(f"Source: {input_path}")
  print(f"Report: {report_path}")


if __name__ == "__main__":
  main()
