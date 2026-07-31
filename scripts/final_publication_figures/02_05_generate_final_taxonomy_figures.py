#!/usr/bin/env python3
from __future__ import annotations

"""Generate final article Figures 2–5 and their statistical result tables.

Figures 2/3 are generated from the corrected frozen phylum source tables. Their
shared legend labels the aggregate row as ``Other taxa (<5% each)``. The 5%
value is the declared per-taxon cutoff, not the summed abundance of the
aggregate category. Figures 4/5 use the frozen article abundance, NMDS and RDA
values. Their legends use the article layout and the RDA panel reserves an
expanded right margin and axis range so every vector label remains visible.

PERMANOVA, dispersion and RDA results are loaded from the exact validated
tables distributed with the article. The same loaders are used by the app.
Figure values and statistical values are not altered.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile


SCRIPT_VERSION = "2026-07-31-final-v8-other-taxa-threshold5"


def project_root() -> Path:
  return Path(__file__).resolve().parents[2]


ROOT = project_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.article_exact_taxonomy_phylum_generated import exact_article_phylum_svg_bytes  # noqa: E402
from src.article_exact_taxonomy_phylum_other_percentage import OTHER_TAXA_THRESHOLD_PERCENT  # noqa: E402
from src.article_frozen_taxonomy_static_v3 import materialize_frozen_article_static_v3  # noqa: E402
from src.article_official_ordination_statistics import official_ordination_inference  # noqa: E402
from src.article_inference_reporting import inference_summary  # noqa: E402


FIGURES = {
  "Bacteria_phylum": (
    "Figure2_taxonomic_phylum_bacteria_horizontal_CDS",
    lambda cache: exact_article_phylum_svg_bytes("Bacteria"),
  ),
  "Archaea_phylum": (
    "Figure3_taxonomic_phylum_archaea_horizontal_CDS",
    lambda cache: exact_article_phylum_svg_bytes("Archaea"),
  ),
  "Bacteria_genus_ordination": (
    "Figure4_taxonomic_bacteria_genus_profiles",
    lambda cache: materialize_frozen_article_static_v3("Bacteria", cache).read_bytes(),
  ),
  "Archaea_genus_ordination": (
    "Figure5_taxonomic_archaea_genus_profiles",
    lambda cache: materialize_frozen_article_static_v3("Archaea", cache).read_bytes(),
  ),
}

PROHIBITED_LEGACY_LABELS = {
  "Figure2_taxonomic_phylum_bacteria_horizontal_CDS": (
    "Proteobacteria", "Acidobacteria", "Actinobacteria"
  ),
  "Figure3_taxonomic_phylum_archaea_horizontal_CDS": (
    "Euryarchaeota", "Thaumarchaeota"
  ),
}


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--base-dir", type=Path, default=ROOT)
  parser.add_argument("--skip-raster", action="store_true", help="Write SVG only")
  parser.add_argument("--dpi", type=int, default=350)
  parser.add_argument("--permutations", type=int, default=999)
  parser.add_argument("--seed", type=int, default=42)
  return parser.parse_args()


def validate_svg(stem: str, payload: bytes) -> None:
  if b"<svg" not in payload[:8192].lower():
    raise RuntimeError(f"Invalid SVG generated for {stem}")
  text = payload.decode("utf-8", errors="ignore")
  for legacy in PROHIBITED_LEGACY_LABELS.get(stem, ()):
    if legacy in text:
      raise RuntimeError(f"Legacy taxonomy label remains in {stem}: {legacy}")
  if stem.startswith(("Figure2_", "Figure3_")):
    required_labels = (
      "Other taxa (<5% each)",
      "Other taxa (&lt;5% each)",
    )
    if not any(label in text for label in required_labels):
      raise RuntimeError(
        f"The 5% aggregate-cutoff label is absent from {stem}"
      )
    if "Other taxa (7.51%)" in text or "Other taxa (0.73%)" in text:
      raise RuntimeError(f"Aggregate mean was incorrectly used as a label in {stem}")
  if stem.startswith(("Figure4_", "Figure5_")):
    required = (
      "Bray-Curtis NMDS", "RDA biplot", "Lake / season", "RDA vectors",
      "Environmental variable", "Representative genus vector", "Genus",
    )
    missing = [label for label in required if label not in text]
    if missing:
      raise RuntimeError(f"Legend/layout labels missing from {stem}: {missing}")


def convert_svg(svg_path: Path, dpi: int) -> list[Path]:
  try:
    import cairosvg
  except Exception as exc:
    raise RuntimeError(
      "CairoSVG is required for final PNG/PDF generation. Install with: "
      "python -m pip install cairosvg"
    ) from exc

  png_path = svg_path.with_suffix(".png")
  pdf_path = svg_path.with_suffix(".pdf")
  tiff_path = svg_path.with_suffix(".tiff")
  cairosvg.svg2png(bytestring=svg_path.read_bytes(), write_to=str(png_path), dpi=dpi)
  cairosvg.svg2pdf(bytestring=svg_path.read_bytes(), write_to=str(pdf_path), dpi=dpi)
  try:
    from PIL import Image
    with Image.open(png_path) as image:
      image.convert("RGB").save(tiff_path, format="TIFF", dpi=(dpi, dpi))
  except Exception as exc:
    raise RuntimeError(f"Could not create TIFF for {svg_path.name}: {exc}") from exc
  return [png_path, pdf_path, tiff_path]


def register_file(path: Path, base_dir: Path, outputs: list[str], hashes: dict[str, str]) -> None:
  outputs.append(str(path.relative_to(base_dir)))
  hashes[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()


def write_ordination_statistics(
  base_dir: Path,
  domain: str,
  permutations: int,
  seed: int,
) -> tuple[list[Path], dict[str, object]]:
  derived = base_dir / "data" / "final_publication_derived"
  derived.mkdir(parents=True, exist_ok=True)
  figure_number = "Figure4" if domain == "Bacteria" else "Figure5"
  beta, rda = official_ordination_inference(
    domain,
    base_dir=base_dir,
    permutations=permutations,
    seed=seed,
  )
  beta_path = derived / f"{figure_number}_{domain}_NMDS_PCoA_PERMANOVA_PERMDISP.csv"
  rda_path = derived / f"{figure_number}_{domain}_RDA_global_statistics.csv"
  beta.to_csv(beta_path, index=False)
  rda.to_csv(rda_path, index=False)
  return [beta_path, rda_path], {
    "domain": domain,
    "nmds_pcoa_method": "official article PERMANOVA and PERMDISP/betadisper tables",
    "nmds_pcoa_summary": inference_summary(beta),
    "rda_method": "official article RDA model-statistics table",
    "rda_results": rda.to_dict("records"),
  }


def main() -> int:
  args = parse_args()
  base_dir = args.base_dir.resolve()
  output_dir = base_dir / "outputs" / "final_publication_figures"
  report_dir = base_dir / "reports"
  output_dir.mkdir(parents=True, exist_ok=True)
  report_dir.mkdir(parents=True, exist_ok=True)

  outputs: list[str] = []
  hashes: dict[str, str] = {}

  with tempfile.TemporaryDirectory(prefix="cangametag_final_taxonomy_") as tmp:
    cache = Path(tmp)
    for _, (stem, builder) in FIGURES.items():
      payload = builder(cache)
      validate_svg(stem, payload)
      svg_path = output_dir / f"{stem}.svg"
      svg_path.write_bytes(payload)
      register_file(svg_path, base_dir, outputs, hashes)
      if not args.skip_raster:
        for converted in convert_svg(svg_path, args.dpi):
          register_file(converted, base_dir, outputs, hashes)

  inference_reports = []
  for domain in ("Bacteria", "Archaea"):
    statistics_files, statistics_report = write_ordination_statistics(
      base_dir,
      domain,
      args.permutations,
      args.seed,
    )
    inference_reports.append(statistics_report)
    for statistics_file in statistics_files:
      register_file(statistics_file, base_dir, outputs, hashes)

  report = {
    "script": "scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py",
    "script_version": SCRIPT_VERSION,
    "app_shared_modules": [
      "src/article_exact_taxonomy_phylum_generated.py",
      "src/article_exact_taxonomy_phylum_other_percentage.py",
      "src/article_frozen_taxonomy_static_v3.py",
      "src/article_frozen_taxonomy_panels.py",
      "src/article_official_ordination_statistics.py",
      "src/article_inference_reporting.py",
    ],
    "outputs": outputs,
    "sha256": hashes,
    "figure_source_values_changed": False,
    "official_article_statistical_values_used": True,
    "permutations": args.permutations,
    "seed": args.seed,
    "taxonomy_labels_updated_only_for_figures_2_3": True,
    "other_taxa_label": {
      "display": "Other taxa (<5% each)",
      "threshold_percent": OTHER_TAXA_THRESHOLD_PERCENT,
      "meaning": (
        "5% is the declared per-taxon cutoff. The plotted Other taxa segment "
        "continues to use the exact aggregate abundance from the source table."
      ),
    },
    "figure_4_5_legend_layout": {
      "lake_season": "below NMDS panel, matching article",
      "rda_vectors": "below RDA panel, matching article",
      "genus": "bottom centre, matching article",
      "overlap": False,
    },
    "figure_4_5_rda_layout": {
      "canvas_inches": [29, 25.5],
      "subplot_right_fraction": 0.900,
      "right_axis_padding_fraction": 0.34,
      "svg_pad_inches": 0.28,
      "right_vector_labels_clipped": False,
    },
    "ordination_inference": inference_reports,
  }
  report_path = report_dir / "FINAL_DOMAIN_TAXONOMY_GENERATION_REPORT.json"
  report_path.write_text(
    json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n",
    encoding="utf-8",
  )
  print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
