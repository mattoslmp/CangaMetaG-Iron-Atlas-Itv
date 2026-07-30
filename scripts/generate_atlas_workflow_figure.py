from pathlib import Path
import shutil

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch, Circle


BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT_STEM = "SupplementaryFigure29_complete_computational_workflow"
OUTPUT_DIRS = [
  BASE_DIR / "outputs" / "final_publication_figures",
  BASE_DIR / "outputs" / "app_supplementary_figures",
  BASE_DIR / "outputs" / "article_highres_figures",
]

COLORS = {
  "ink": "#123534",
  "muted": "#475569",
  "teal": "#008A83",
  "teal_dark": "#075E5A",
  "teal_soft": "#E8F5F3",
  "gold_soft": "#FFF6D8",
  "blue": "#2563EB",
  "blue_soft": "#EAF2FF",
  "violet": "#7C3AED",
  "violet_soft": "#F1EBFF",
  "rose": "#BE123C",
  "rose_soft": "#FFF0F4",
  "gray_soft": "#F8FAFC",
}


def rounded_box(
  ax,
  x,
  y,
  w,
  h,
  face,
  edge,
  title,
  body=None,
  number=None,
  title_size=12.5,
  body_size=10.0,
):
  ax.add_patch(
    FancyBboxPatch(
      (x, y),
      w,
      h,
      boxstyle="round,pad=0.012,rounding_size=0.018",
      linewidth=1.8,
      edgecolor=edge,
      facecolor=face,
      zorder=2,
    )
  )

  title_y = y + h - 0.034
  if number is not None:
    circle_x = x + 0.027
    circle_y = title_y
    ax.add_patch(
      Circle(
        (circle_x, circle_y),
        0.014,
        facecolor=edge,
        edgecolor="none",
        zorder=4,
      )
    )
    ax.text(
      circle_x,
      circle_y,
      str(number),
      ha="center",
      va="center",
      fontsize=9.2,
      color="white",
      fontweight="bold",
      zorder=5,
    )
    title_x = x + 0.062
    title_ha = "left"
  else:
    title_x = x + w / 2
    title_ha = "center"

  ax.text(
    title_x,
    title_y,
    title,
    ha=title_ha,
    va="center",
    fontsize=title_size,
    color=COLORS["ink"],
    fontweight="bold",
    zorder=5,
  )

  if body:
    ax.text(
      x + w / 2,
      y + h * 0.41,
      body,
      ha="center",
      va="center",
      fontsize=body_size,
      color=COLORS["muted"],
      linespacing=1.32,
      zorder=5,
    )


def arrow(ax, start, end, color=None, rad=0.0):
  ax.add_patch(
    FancyArrowPatch(
      start,
      end,
      arrowstyle="-|>",
      mutation_scale=16,
      linewidth=1.8,
      color=color or COLORS["teal"],
      connectionstyle=f"arc3,rad={rad}",
      shrinkA=4,
      shrinkB=4,
      zorder=1,
    )
  )


def build_figure():
  fig = plt.figure(figsize=(16, 10), dpi=300, facecolor="white")
  ax = fig.add_axes([0, 0, 1, 1])
  ax.set_xlim(0, 1)
  ax.set_ylim(0, 1)
  ax.set_axis_off()

  ax.text(
    0.5,
    0.965,
    "Computational workflow of the CangaMetaG Iron-Rich Metagenomic Atlas",
    ha="center",
    va="top",
    fontsize=19,
    color=COLORS["ink"],
    fontweight="bold",
  )

  rounded_box(
    ax,
    0.035,
    0.625,
    0.265,
    0.235,
    COLORS["teal_soft"],
    COLORS["teal"],
    "Scientific data layers",
    "Study metadata\nSample context\nTaxonomic profiles\nKO profiles\nMAG annotations\nIron-rich studies",
    number=1,
    body_size=9.6,
  )

  rounded_box(
    ax,
    0.365,
    0.625,
    0.265,
    0.235,
    COLORS["blue_soft"],
    COLORS["blue"],
    "Curation and harmonization",
    "Canonical sample and MAG identifiers\nTaxonomy and metadata standardization\nKO, pathway, and module mapping\nCross-study provenance and reference links",
    number=2,
    body_size=9.6,
  )

  rounded_box(
    ax,
    0.695,
    0.625,
    0.270,
    0.235,
    COLORS["gold_soft"],
    "#C58B00",
    "Atlas-ready scientific matrices",
    "Consistent taxonomic abundance tables\nBiogeochemical and iron-related KO matrices\nKEGG/KEMET module-completeness matrices\nGenome-resolved and cross-environment datasets",
    number=3,
    body_size=9.5,
  )

  arrow(ax, (0.300, 0.742), (0.365, 0.742), COLORS["teal"])
  arrow(ax, (0.630, 0.742), (0.695, 0.742), COLORS["blue"])

  ax.text(
    0.5,
    0.565,
    "Analytical modules",
    ha="center",
    va="center",
    fontsize=14,
    color=COLORS["ink"],
    fontweight="bold",
  )

  modules = [
    (
      0.035,
      "Taxonomic ecology",
      "Community composition\nAlpha and beta diversity\nNMDS, PCoA, PCA, and RDA",
      COLORS["teal_soft"],
      COLORS["teal"],
    ),
    (
      0.275,
      "Functional potential",
      "Biogeochemical markers\nIron metabolism\nDifferential abundance",
      COLORS["blue_soft"],
      COLORS["blue"],
    ),
    (
      0.515,
      "Genome-resolved atlas",
      "MAG quality and taxonomy\nGenome annotation\nBiosynthetic gene clusters",
      COLORS["violet_soft"],
      COLORS["violet"],
    ),
    (
      0.755,
      "Comparative context",
      "Amazonian versus external\niron-rich environments\nStudy-linked interpretation",
      COLORS["rose_soft"],
      COLORS["rose"],
    ),
  ]

  for x, title, body, face, edge in modules:
    rounded_box(
      ax,
      x,
      0.355,
      0.210,
      0.165,
      face,
      edge,
      title,
      body,
      title_size=11.5,
      body_size=9.5,
    )
    arrow(ax, (x + 0.105, 0.625), (x + 0.105, 0.520), edge)

  rounded_box(
    ax,
    0.095,
    0.115,
    0.245,
    0.150,
    COLORS["gray_soft"],
    COLORS["teal_dark"],
    "Interactive application",
    "Searchable tables and filters\nInteractive figures and linked resources\nDownloadable scientific results",
    number=4,
  )

  rounded_box(
    ax,
    0.380,
    0.115,
    0.240,
    0.150,
    COLORS["gray_soft"],
    COLORS["teal_dark"],
    "Publication outputs",
    "Main and supplementary figures\nSource-data tables\nHigh-resolution PNG, PDF, and SVG",
    number=5,
  )

  rounded_box(
    ax,
    0.660,
    0.115,
    0.245,
    0.150,
    COLORS["gray_soft"],
    COLORS["teal_dark"],
    "Reproducible code",
    "Figure-generation scripts\nReusable modules in src/\nDocumented commands and dependencies",
    number=6,
  )

  for x in [0.140, 0.380, 0.620, 0.860]:
    target_x = 0.215 if x < 0.25 else 0.500 if x < 0.65 else 0.785
    arrow(
      ax,
      (x, 0.355),
      (target_x, 0.265),
      COLORS["teal_dark"],
      rad=0.05 if x in [0.140, 0.860] else 0.0,
    )

  ax.text(
    0.5,
    0.055,
    "Input provenance is described by scientific content rather than table number; exact source-file and figure mappings remain available in the repository documentation.",
    ha="center",
    va="center",
    fontsize=9.5,
    color=COLORS["muted"],
  )

  return fig


def save_figure(fig):
  primary_dir = OUTPUT_DIRS[0]
  primary_dir.mkdir(parents=True, exist_ok=True)
  primary_files = {}

  for suffix in ("png", "pdf", "svg"):
    path = primary_dir / f"{OUTPUT_STEM}.{suffix}"
    fig.savefig(path, dpi=300, bbox_inches="tight", facecolor="white")
    primary_files[suffix] = path

  for directory in OUTPUT_DIRS[1:]:
    directory.mkdir(parents=True, exist_ok=True)
    for suffix, source in primary_files.items():
      target = directory / f"{OUTPUT_STEM}.{suffix}"
      shutil.copy2(source, target)

  for directory in OUTPUT_DIRS:
    for suffix in ("png", "pdf", "svg"):
      print(directory / f"{OUTPUT_STEM}.{suffix}")


if __name__ == "__main__":
  figure = build_figure()
  save_figure(figure)
  plt.close(figure)
