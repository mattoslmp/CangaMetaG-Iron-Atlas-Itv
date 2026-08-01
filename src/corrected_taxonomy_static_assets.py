from __future__ import annotations

"""Current-name static taxonomy assets shared by the article and public app.

Regenerated repository outputs are authoritative. A deterministic runtime
regenerator is used when those SVGs are absent. The former label-only frozen
bundle remains only as a final compatibility fallback.
"""

from pathlib import Path
import base64
from io import BytesIO
import os
import shutil
from zipfile import BadZipFile, ZipFile


BASE_DIR = Path(__file__).resolve().parents[1]
ASSET_DIR = BASE_DIR / "data" / "corrected_static_figures" / "taxonomy_corrected_article_static_svgs"
BUNDLE_PATH = BASE_DIR / "data" / "corrected_static_figures" / "taxonomy_corrected_article_static_svgs.zip"
MAIN_OUTPUT_DIR = BASE_DIR / "outputs" / "final_publication_figures"
SUPPLEMENTARY_OUTPUT_DIR = BASE_DIR / "outputs" / "app_supplementary_figures"

CORRECTED_TAXONOMY_STATIC_MEMBERS: dict[str, str] = {
  "Figure2_taxonomic_phylum_bacteria_horizontal_CDS.svg": "main/Figure2_taxonomic_phylum_bacteria_horizontal_CDS.svg",
  "Figure3_taxonomic_phylum_archaea_horizontal_CDS.svg": "main/Figure3_taxonomic_phylum_archaea_horizontal_CDS.svg",
  "SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct.svg": "supplementary/SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct.svg",
  "SupplementaryFigure44_Taxonomy_Bacteria_Phylum_individual_samples_heatmap_relative_abundance.svg": "supplementary/SupplementaryFigure44_Taxonomy_Bacteria_Phylum_individual_samples_heatmap_relative_abundance.svg",
  "SupplementaryFigure45_Taxonomy_Archaea_Phylum_individual_samples_barplot_100pct.svg": "supplementary/SupplementaryFigure45_Taxonomy_Archaea_Phylum_individual_samples_barplot_100pct.svg",
  "SupplementaryFigure46_Taxonomy_Archaea_Phylum_individual_samples_heatmap_relative_abundance.svg": "supplementary/SupplementaryFigure46_Taxonomy_Archaea_Phylum_individual_samples_heatmap_relative_abundance.svg",
}

CORRECTED_TAXONOMY_STATIC_FILENAMES = frozenset(CORRECTED_TAXONOMY_STATIC_MEMBERS)
CORRECTED_TAXONOMY_STATIC_STEMS = frozenset(Path(name).stem for name in CORRECTED_TAXONOMY_STATIC_FILENAMES)


def _valid_svg_bytes(payload: bytes | None) -> bool:
  return bool(payload and b"<svg" in payload[:8192].lstrip().lower())


def _generated_output_path(svg_name: str) -> Path:
  member = CORRECTED_TAXONOMY_STATIC_MEMBERS.get(svg_name, "")
  directory = MAIN_OUTPUT_DIR if member.startswith("main/") else SUPPLEMENTARY_OUTPUT_DIR
  return directory / svg_name


def _runtime_generated_bytes(svg_name: str) -> bytes | None:
  try:
    from .taxonomy_final_contract import install_final_taxonomy_contract

    install_final_taxonomy_contract()
    if svg_name == "Figure2_taxonomic_phylum_bacteria_horizontal_CDS.svg":
      from .article_exact_taxonomy_phylum_generated import exact_article_phylum_svg_bytes
      return exact_article_phylum_svg_bytes("Bacteria", "en")
    if svg_name == "Figure3_taxonomic_phylum_archaea_horizontal_CDS.svg":
      from .article_exact_taxonomy_phylum_generated import exact_article_phylum_svg_bytes
      return exact_article_phylum_svg_bytes("Archaea", "en")
    from .final_taxonomy_static_figures import supplementary_taxonomy_assets
    return supplementary_taxonomy_assets("en").get(svg_name)
  except Exception:
    return None


def _bundle_zip() -> ZipFile | None:
  if not BUNDLE_PATH.is_file():
    return None
  try:
    return ZipFile(BUNDLE_PATH)
  except (BadZipFile, OSError, RuntimeError, ValueError):
    pass
  try:
    encoded = b"".join(BUNDLE_PATH.read_bytes().split())
    decoded = base64.b64decode(encoded, validate=True)
    return ZipFile(BytesIO(decoded))
  except (BadZipFile, OSError, RuntimeError, ValueError, TypeError, base64.binascii.Error):
    return None


def corrected_taxonomy_static_bytes(filename: str) -> bytes | None:
  requested = Path(str(filename)).name
  svg_name = f"{Path(requested).stem}.svg"
  member = CORRECTED_TAXONOMY_STATIC_MEMBERS.get(svg_name)
  if member is None:
    return None

  generated_path = _generated_output_path(svg_name)
  try:
    if generated_path.is_file():
      payload = generated_path.read_bytes()
      if _valid_svg_bytes(payload):
        return payload
  except OSError:
    pass

  runtime_payload = _runtime_generated_bytes(svg_name)
  if _valid_svg_bytes(runtime_payload):
    return runtime_payload

  direct_path = ASSET_DIR / svg_name
  try:
    if direct_path.is_file():
      payload = direct_path.read_bytes()
      if _valid_svg_bytes(payload):
        return payload
  except OSError:
    pass

  archive = _bundle_zip()
  if archive is None:
    return None
  try:
    with archive:
      payload = archive.read(member)
    return payload if _valid_svg_bytes(payload) else None
  except (BadZipFile, KeyError, OSError, RuntimeError, ValueError):
    return None


def materialize_corrected_taxonomy_static(filename: str, runtime_root: Path | str) -> Path | None:
  payload = corrected_taxonomy_static_bytes(filename)
  if payload is None:
    return None
  target_dir = Path(runtime_root) / "current_taxonomy_lt5_static"
  target_dir.mkdir(parents=True, exist_ok=True)
  target = target_dir / f"{Path(filename).stem}.svg"
  if not target.exists() or target.read_bytes() != payload:
    target.write_bytes(payload)
  return target


def _link_or_copy(source: Path, destination: Path) -> None:
  if destination.exists() or destination.is_symlink():
    return
  try:
    destination.symlink_to(source.resolve())
    return
  except OSError:
    pass
  try:
    os.link(source, destination)
    return
  except OSError:
    pass
  shutil.copy2(source, destination)


def build_corrected_taxonomy_publication_overlay(
  main_source_dir: Path | str,
  supplementary_source_dir: Path | str,
  runtime_root: Path | str,
) -> tuple[Path, Path]:
  main_source = Path(main_source_dir)
  supplementary_source = Path(supplementary_source_dir)
  overlay_root = Path(runtime_root) / "current_taxonomy_lt5_publication_overlay"
  main_overlay = overlay_root / "main"
  supplementary_overlay = overlay_root / "supplementary"
  main_overlay.mkdir(parents=True, exist_ok=True)
  supplementary_overlay.mkdir(parents=True, exist_ok=True)

  corrected_payloads = {
    name: corrected_taxonomy_static_bytes(name)
    for name in CORRECTED_TAXONOMY_STATIC_FILENAMES
  }
  available_stems = {
    Path(name).stem for name, payload in corrected_payloads.items()
    if _valid_svg_bytes(payload)
  }

  for source_dir, destination_dir in (
    (main_source, main_overlay),
    (supplementary_source, supplementary_overlay),
  ):
    if not source_dir.is_dir():
      continue
    for source_path in source_dir.iterdir():
      if not source_path.is_file() or source_path.stem in available_stems:
        continue
      _link_or_copy(source_path, destination_dir / source_path.name)

  for svg_name, member in CORRECTED_TAXONOMY_STATIC_MEMBERS.items():
    payload = corrected_payloads.get(svg_name)
    if not _valid_svg_bytes(payload):
      continue
    destination_dir = main_overlay if member.startswith("main/") else supplementary_overlay
    destination = destination_dir / svg_name
    if not destination.exists() or destination.read_bytes() != payload:
      destination.write_bytes(payload)
  return main_overlay, supplementary_overlay
