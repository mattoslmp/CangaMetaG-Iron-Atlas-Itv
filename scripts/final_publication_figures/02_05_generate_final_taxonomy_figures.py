#!/usr/bin/env python3
from __future__ import annotations

"""Generate every canonical static taxonomy figure from packaged source data.

Figures 2–5 and Supplementary Figures 43–46 share one contract:
- current taxonomy names from the packaged NCBI mapping;
- ``Other taxa``/``Other genera`` contains every named taxon whose maximum
  abundance is strictly below 5% across all displayed samples;
- ``Unclassified`` remains a separate category;
- counts, percentages, ordination coordinates and statistical values are not
  invented or altered by presentation code.
"""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import tempfile


SCRIPT_VERSION = "2026-08-01-final-v10-current-taxonomy-lt5"


def project_root() -> Path:
  return Path(__file__).resolve().parents[2]


ROOT = project_root()
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.taxonomy_final_contract import (  # noqa: E402
  OTHER_TAXA_THRESHOLD_PERCENT,
  final_domain_rank_matrices,
  install_final_taxonomy_contract,
  legacy_labels_present,
)

install_final_taxonomy_contract()

from src.article_exact_taxonomy_phylum_generated import exact_article_phylum_svg_bytes  # noqa: E402
from src.article_frozen_taxonomy_static_bilingual import materialize_frozen_article_static_bilingual  # noqa: E402
from src.article_official_ordination_statistics import official_ordination_inference  # noqa: E402
from src.article_inference_reporting import inference_summary  # noqa: E402
from src.final_taxonomy_static_figures import supplementary_taxonomy_assets  # noqa: E402


MAIN_FIGURES = {
  "Bacteria_phylum": (
    "Figure2_taxonomic_phylum_bacteria_horizontal_CDS",
    lambda cache, language: exact_article_phylum_svg_bytes("Bacteria", language),
  ),
  "Archaea_phylum": (
    "Figure3_taxonomic_phylum_archaea_horizontal_CDS",
    lambda cache, language: exact_article_phylum_svg_bytes("Archaea", language),
  ),
  "Bacteria_genus_ordination": (
    "Figure4_taxonomic_bacteria_genus_profiles",
    lambda cache, language: materialize_frozen_article_static_bilingual(
      "Bacteria", cache, language=language
    ).read_bytes(),
  ),
  "Archaea_genus_ordination": (
    "Figure5_taxonomic_archaea_genus_profiles",
    lambda cache, language: materialize_frozen_article_static_bilingual(
      "Archaea", cache, language=language
    ).read_bytes(),
  ),
}


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description=__doc__)
  parser.add_argument("--base-dir", type=Path, default=ROOT)
  parser.add_argument("--skip-raster", action="store_true", help="Write SVG only")
  parser.add_argument("--dpi", type=int, default=350)
  parser.add_argument("--permutations", type=int, default=999)
  parser.add_argument("--seed", type=int, default=42)
  parser.add_argument(
    "--language",
    choices=["en", "pt", "both"],
    default="both",
  )
  return parser.parse_args()


def validate_taxonomy_contract(base_dir: Path) -> dict[str, object]:
  rows: list[dict[str, object]] = []
  for domain in ("Bacteria", "Archaea"):
    for rank in ("Phylum", "Genus"):
      counts, relative = final_domain_rank_matrices(domain, rank, base_dir=base_dir)
      legacy = legacy_labels_present(relative.index.astype(str).tolist(), rank, base_dir)
      aggregate = "Other genera" if rank == "Genus" else "Other taxa"
      aggregated_taxa = list(relative.attrs.get("aggregated_taxa", []))
      invalid_aggregated = []
      full_counts, full_relative = final_domain_rank_matrices(domain, rank, base_dir=base_dir)
      for taxon in aggregated_taxa:
        if taxon in full_relative.index and float(full_relative.loc[taxon].max()) >= OTHER_TAXA_THRESHOLD_PERCENT:
          invalid_aggregated.append(taxon)
      if legacy:
        raise RuntimeError(f"Legacy taxonomy labels remain for {domain}/{rank}: {legacy}")
      if invalid_aggregated:
        raise RuntimeError(
          f"Taxa at or above 5% were incorrectly aggregated for {domain}/{rank}: {invalid_aggregated}"
        )
      if not counts.sum(axis=0).gt(0).all():
        raise RuntimeError(f"Empty taxonomy sample found for {domain}/{rank}")
      if not relative.sum(axis=0).round(8).eq(100.0).all():
        raise RuntimeError(f"Relative-abundance columns do not sum to 100 for {domain}/{rank}")
      rows.append({
        "domain": domain,
        "rank": rank,
        "displayed_taxa": int(len(relative)),
        "aggregate_label": aggregate if aggregate in relative.index else "",
        "aggregated_taxa_count": len(aggregated_taxa),
        "legacy_labels_present": legacy,
        "unclassified_preserved": "Unclassified" in relative.index,
        "column_totals_preserved": True,
      })
  return {"status": "PASS", "checks": rows}


def validate_svg(stem: str, payload: bytes, language: str) -> None:
  if b"<svg" not in payload[:8192].lower():
    raise RuntimeError(f"Invalid SVG generated for {stem} [{language}]")
  text = payload.decode("utf-8", errors="ignore")
  if stem.startswith(("Figure2_", "Figure3_", "SupplementaryFigure43_", "SupplementaryFigure45_")):
    labels = (
      ("Outros táxons (<5% cada)", "Outros táxons (&lt;5% cada)")
      if language == "pt"
      else ("Other taxa (<5% each)", "Other taxa (&lt;5% each)")
    )
    if not any(label in text for label in labels):
      raise RuntimeError(f"Strict <5% aggregate label absent from {stem} [{language}]")


def convert_svg(svg_path: Path, dpi: int) -> list[Path]:
  try:
    import cairosvg
  except Exception as exc:
    raise RuntimeError("CairoSVG is required for PNG/PDF generation") from exc
  from PIL import Image

  png_path = svg_path.with_suffix(".png")
  pdf_path = svg_path.with_suffix(".pdf")
  tiff_path = svg_path.with_suffix(".tiff")
  payload = svg_path.read_bytes()
  cairosvg.svg2png(bytestring=payload, write_to=str(png_path), dpi=dpi)
  cairosvg.svg2pdf(bytestring=payload, write_to=str(pdf_path), dpi=dpi)
  with Image.open(png_path) as image:
    image.convert("RGB").save(tiff_path, format="TIFF", dpi=(dpi, dpi))
  return [png_path, pdf_path, tiff_path]


def register_file(path: Path, base_dir: Path, outputs: list[str], hashes: dict[str, str]) -> None:
  outputs.append(str(path.relative_to(base_dir)))
  hashes[str(path.relative_to(base_dir))] = hashlib.sha256(path.read_bytes()).hexdigest()


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
  main_dir = base_dir / "outputs" / "final_publication_figures"
  supplementary_dir = base_dir / "outputs" / "app_supplementary_figures"
  report_dir = base_dir / "reports"
  main_dir.mkdir(parents=True, exist_ok=True)
  supplementary_dir.mkdir(parents=True, exist_ok=True)
  report_dir.mkdir(parents=True, exist_ok=True)

  contract_validation = validate_taxonomy_contract(base_dir)
  languages = ["en", "pt"] if args.language == "both" else [args.language]
  outputs: list[str] = []
  hashes: dict[str, str] = {}
  language_outputs: dict[str, list[str]] = {language: [] for language in languages}

  with tempfile.TemporaryDirectory(prefix="cangametag_final_taxonomy_") as tmp:
    cache = Path(tmp)
    for language in languages:
      suffix = "_pt" if language == "pt" else ""
      for _, (stem, builder) in MAIN_FIGURES.items():
        payload = builder(cache, language)
        validate_svg(stem, payload, language)
        path = main_dir / f"{stem}{suffix}.svg"
        path.write_bytes(payload)
        register_file(path, base_dir, outputs, hashes)
        language_outputs[language].append(str(path.relative_to(base_dir)))
        if not args.skip_raster:
          for converted in convert_svg(path, args.dpi):
            register_file(converted, base_dir, outputs, hashes)
            language_outputs[language].append(str(converted.relative_to(base_dir)))

      for filename, payload in supplementary_taxonomy_assets(language).items():
        validate_svg(Path(filename).stem, payload, language)
        path = supplementary_dir / filename
        path.write_bytes(payload)
        register_file(path, base_dir, outputs, hashes)
        language_outputs[language].append(str(path.relative_to(base_dir)))
        if not args.skip_raster:
          for converted in convert_svg(path, args.dpi):
            register_file(converted, base_dir, outputs, hashes)
            language_outputs[language].append(str(converted.relative_to(base_dir)))

  inference_reports = []
  for domain in ("Bacteria", "Archaea"):
    statistic_files, statistic_report = write_ordination_statistics(
      base_dir,
      domain,
      args.permutations,
      args.seed,
    )
    inference_reports.append(statistic_report)
    for path in statistic_files:
      register_file(path, base_dir, outputs, hashes)

  report = {
    "script": "scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py",
    "script_version": SCRIPT_VERSION,
    "taxonomy_contract": {
      "current_name_source": "data/ncbi_taxonomy_name_updates.csv generated from NCBI taxdump",
      "current_taxonomy_table": "data/resultado.cds.tax.ncbi_current.tab",
      "other_taxa_threshold_percent": OTHER_TAXA_THRESHOLD_PERCENT,
      "threshold_operator": "strictly less than",
      "threshold_scope": "maximum relative abundance across all displayed samples",
      "unclassified_preserved_separately": True,
      "counts_and_column_totals_preserved": True,
    },
    "validation": contract_validation,
    "languages_generated": languages,
    "language_outputs": language_outputs,
    "inputs": [
      "data/resultado.cds.otu.tab",
      "data/resultado.cds.tax.ncbi_current.tab",
      "data/ncbi_taxonomy_name_updates.csv",
      "data/article_frozen_taxonomy_bacteria.json",
      "data/article_frozen_taxonomy_archaea.json",
      "reproducibility/ordination_reproducibility/tables/*",
    ],
    "outputs": outputs,
    "sha256": hashes,
    "figure_source_values_changed": False,
    "ordination_values_recomputed": False,
    "official_article_statistical_values_used": True,
    "ordination_inference": inference_reports,
  }
  report_path = report_dir / "FINAL_DOMAIN_TAXONOMY_GENERATION_REPORT.json"
  report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
