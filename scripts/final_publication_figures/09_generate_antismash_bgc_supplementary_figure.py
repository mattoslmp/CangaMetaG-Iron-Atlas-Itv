#!/usr/bin/env python3
from __future__ import annotations

"""Generate Supplementary Figure 68 and its evidence table from antiSMASH GBKs."""

import argparse
import hashlib
import json
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.antismash_metabolism_runtime import bgc_metabolism_inventory  # noqa: E402
from src.antismash_supplementary_figure import (  # noqa: E402
  INPUT_PATHS,
  OUTPUT_FIGURE,
  OUTPUT_REPORT,
  OUTPUT_STEM,
  OUTPUT_TABLE,
  SCRIPT_PATH,
  bgc_supplementary_figure_svg,
  public_bgc_table,
)


SCRIPT_VERSION = "2026-08-01-antismash-supplementary-v1"


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--base-dir", type=Path, default=ROOT)
  parser.add_argument("--dpi", type=int, default=350)
  parser.add_argument("--skip-raster", action="store_true")
  return parser.parse_args()


def convert_svg(svg_path: Path, dpi: int) -> list[Path]:
  import cairosvg
  from PIL import Image

  payload = svg_path.read_bytes()
  png = svg_path.with_suffix(".png")
  pdf = svg_path.with_suffix(".pdf")
  tiff = svg_path.with_suffix(".tiff")
  cairosvg.svg2png(bytestring=payload, write_to=str(png), dpi=dpi)
  cairosvg.svg2pdf(bytestring=payload, write_to=str(pdf), dpi=dpi)
  with Image.open(png) as image:
    image.convert("RGB").save(tiff, format="TIFF", dpi=(dpi, dpi))
  return [png, pdf, tiff]


def main() -> int:
  args = parse_args()
  base_dir = args.base_dir.resolve()
  figure_path = base_dir / OUTPUT_FIGURE
  table_path = base_dir / OUTPUT_TABLE
  report_path = base_dir / OUTPUT_REPORT
  figure_path.parent.mkdir(parents=True, exist_ok=True)
  table_path.parent.mkdir(parents=True, exist_ok=True)
  report_path.parent.mkdir(parents=True, exist_ok=True)

  table = bgc_metabolism_inventory()
  svg = bgc_supplementary_figure_svg(table)
  if b"<svg" not in svg[:8192].lower():
    raise RuntimeError("Supplementary Figure 68 generator did not produce valid SVG")
  figure_path.write_bytes(svg)
  public_bgc_table(table).to_csv(table_path, index=False)

  outputs = [figure_path, table_path]
  if not args.skip_raster:
    outputs.extend(convert_svg(figure_path, args.dpi))
  hashes = {
    str(path.relative_to(base_dir)): hashlib.sha256(path.read_bytes()).hexdigest()
    for path in outputs
  }
  report = {
    "script": SCRIPT_PATH,
    "script_version": SCRIPT_VERSION,
    "input_patterns": INPUT_PATHS,
    "output_figure": OUTPUT_FIGURE,
    "output_table": OUTPUT_TABLE,
    "output_stem": OUTPUT_STEM,
    "bgc_rows": int(len(table)),
    "metal_direct_rows": int(table.get("metal evidence", []).astype(str).eq("direct BGC-class evidence").sum()) if not table.empty else 0,
    "metal_candidate_rows": int(table.get("metal evidence", []).astype(str).eq("gene-annotation candidate").sum()) if not table.empty else 0,
    "carbon_class_rows": int(table.get("carbon evidence", []).astype(str).eq("BGC-class chemistry").sum()) if not table.empty else 0,
    "source_values_changed": False,
    "generative_image_model_used": False,
    "cluster_drawing_method": "deterministic SVG arrows from CDS coordinates in antiSMASH region*.gbk",
    "sha256": hashes,
  }
  report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  print(json.dumps(report, indent=2, ensure_ascii=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
