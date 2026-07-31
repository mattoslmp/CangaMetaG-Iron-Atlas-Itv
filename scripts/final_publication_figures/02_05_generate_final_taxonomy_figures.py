#!/usr/bin/env python3
from __future__ import annotations

"""Generate final article Figures 2–5 from the same sources used by the app.

Figures 2/3
  Generated from the corrected frozen phylum source CSVs with the canonical
  two-panel article layout.

Figures 4/5
  Generated from the frozen article abundance, NMDS and RDA tables. Legends
  are placed in reserved regions outside the four scientific panels.

The app imports the same source modules. Therefore static article assets,
interactive viewers and future packaged releases share one implementation.
No abundance, coordinate, vector or statistic is recomputed in this script.
"""

import argparse
import json
from pathlib import Path
import shutil
import sys
import tempfile


SCRIPT_VERSION = "2026-07-31-final-v2"


def project_root() -> Path:
  return Path(__file__).resolve().parents[2]


ROOT = project_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.article_exact_taxonomy_phylum_generated import (  # noqa: E402
  exact_article_phylum_svg_bytes,
)
from src.article_frozen_taxonomy_static import (  # noqa: E402
  materialize_frozen_article_static,
)


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
    lambda cache: materialize_frozen_article_static("Bacteria", cache).read_bytes(),
  ),
  "Archaea_genus_ordination": (
    "Figure5_taxonomic_archaea_genus_profiles",
    lambda cache: materialize_frozen_article_static("Archaea", cache).read_bytes(),
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
  return parser.parse_args()


def validate_svg(stem: str, payload: bytes) -> None:
  head = payload[:8192].lower()
  if b"<svg" not in head:
    raise RuntimeError(f"Invalid SVG generated for {stem}")
  text = payload.decode("utf-8", errors="ignore")
  for legacy in PROHIBITED_LEGACY_LABELS.get(stem, ()):
    if legacy in text:
      raise RuntimeError(f"Legacy taxonomy label remains in {stem}: {legacy}")
  if stem.startswith(("Figure4_", "Figure5_")):
    required = (
      "Bray-Curtis NMDS", "RDA biplot", "Lake / season",
      "Environmental variable", "Representative genus vector",
    )
    missing = [label for label in required if label not in text]
    if missing:
      raise RuntimeError(f"Legend/layout labels missing from {stem}: {missing}")


def convert_svg(svg_path: Path, dpi: int) -> list[Path]:
  """Create PDF, PNG and TIFF from one validated SVG."""
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
  cairosvg.svg2png(
    bytestring=svg_path.read_bytes(),
    write_to=str(png_path),
    dpi=dpi,
  )
  cairosvg.svg2pdf(
    bytestring=svg_path.read_bytes(),
    write_to=str(pdf_path),
    dpi=dpi,
  )
  try:
    from PIL import Image
    with Image.open(png_path) as image:
      image.convert("RGB").save(tiff_path, format="TIFF", dpi=(dpi, dpi))
  except Exception as exc:
    raise RuntimeError(f"Could not create TIFF for {svg_path.name}: {exc}") from exc
  return [png_path, pdf_path, tiff_path]


def main() -> int:
  args = parse_args()
  base_dir = args.base_dir.resolve()
  output_dir = base_dir / "outputs" / "final_publication_figures"
  report_dir = base_dir / "reports"
  output_dir.mkdir(parents=True, exist_ok=True)
  report_dir.mkdir(parents=True, exist_ok=True)

  outputs: list[str] = []
  hashes: dict[str, str] = {}
  import hashlib

  with tempfile.TemporaryDirectory(prefix="cangametag_final_taxonomy_") as tmp:
    cache = Path(tmp)
    for figure_key, (stem, builder) in FIGURES.items():
      payload = builder(cache)
      validate_svg(stem, payload)
      svg_path = output_dir / f"{stem}.svg"
      svg_path.write_bytes(payload)
      hashes[svg_path.name] = hashlib.sha256(payload).hexdigest()
      outputs.append(str(svg_path.relative_to(base_dir)))
      if not args.skip_raster:
        for converted in convert_svg(svg_path, args.dpi):
          outputs.append(str(converted.relative_to(base_dir)))
          hashes[converted.name] = hashlib.sha256(converted.read_bytes()).hexdigest()

  report = {
    "script": "scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py",
    "script_version": SCRIPT_VERSION,
    "app_shared_modules": [
      "src/article_exact_taxonomy_phylum_generated.py",
      "src/article_frozen_taxonomy_static.py",
      "src/article_frozen_taxonomy_panels.py",
    ],
    "outputs": outputs,
    "sha256": hashes,
    "scientific_values_recomputed": False,
    "taxonomy_labels_updated_only_for_figures_2_3": True,
    "figure_4_5_legend_layout": "legends reserved outside scientific panels",
  }
  report_path = report_dir / "FINAL_DOMAIN_TAXONOMY_GENERATION_REPORT.json"
  report_path.write_text(
    json.dumps(report, indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
  )
  print(json.dumps(report, indent=2, ensure_ascii=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
