from __future__ import annotations

"""Corrected static taxonomy assets shared by the article and public app.

The bundled SVGs are label-only corrections of the frozen article figures.
Their bars, cells, sample order, colours, coordinates and canvas geometry are
unchanged.  The application materialises a runtime overlay instead of writing
inside the repository checkout.
"""

from pathlib import Path
import os
import shutil
from zipfile import ZipFile


BASE_DIR = Path(__file__).resolve().parents[1]
BUNDLE_PATH = (
  BASE_DIR
  / "data"
  / "corrected_static_figures"
  / "taxonomy_corrected_article_static_svgs.zip"
)

CORRECTED_TAXONOMY_STATIC_MEMBERS: dict[str, str] = {
  "Figure2_taxonomic_phylum_bacteria_horizontal_CDS.svg": (
    "main/Figure2_taxonomic_phylum_bacteria_horizontal_CDS.svg"
  ),
  "Figure3_taxonomic_phylum_archaea_horizontal_CDS.svg": (
    "main/Figure3_taxonomic_phylum_archaea_horizontal_CDS.svg"
  ),
  "SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct.svg": (
    "supplementary/SupplementaryFigure43_Taxonomy_Bacteria_Phylum_individual_samples_barplot_100pct.svg"
  ),
  "SupplementaryFigure44_Taxonomy_Bacteria_Phylum_individual_samples_heatmap_relative_abundance.svg": (
    "supplementary/SupplementaryFigure44_Taxonomy_Bacteria_Phylum_individual_samples_heatmap_relative_abundance.svg"
  ),
  "SupplementaryFigure45_Taxonomy_Archaea_Phylum_individual_samples_barplot_100pct.svg": (
    "supplementary/SupplementaryFigure45_Taxonomy_Archaea_Phylum_individual_samples_barplot_100pct.svg"
  ),
  "SupplementaryFigure46_Taxonomy_Archaea_Phylum_individual_samples_heatmap_relative_abundance.svg": (
    "supplementary/SupplementaryFigure46_Taxonomy_Archaea_Phylum_individual_samples_heatmap_relative_abundance.svg"
  ),
}

CORRECTED_TAXONOMY_STATIC_FILENAMES = frozenset(
  CORRECTED_TAXONOMY_STATIC_MEMBERS
)
CORRECTED_TAXONOMY_STATIC_STEMS = frozenset(
  Path(name).stem for name in CORRECTED_TAXONOMY_STATIC_FILENAMES
)


def corrected_taxonomy_static_bytes(filename: str) -> bytes | None:
  """Return one corrected frozen SVG, or ``None`` for unrelated figures."""
  requested = Path(str(filename)).name
  stem = Path(requested).stem
  svg_name = f"{stem}.svg"
  member = CORRECTED_TAXONOMY_STATIC_MEMBERS.get(svg_name)
  if member is None or not BUNDLE_PATH.is_file():
    return None
  with ZipFile(BUNDLE_PATH) as archive:
    return archive.read(member)


def materialize_corrected_taxonomy_static(
  filename: str,
  runtime_root: Path | str,
) -> Path | None:
  """Write one corrected SVG to a runtime cache and return its path."""
  payload = corrected_taxonomy_static_bytes(filename)
  if payload is None:
    return None
  target_dir = Path(runtime_root) / "corrected_taxonomy_static"
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
  """Create read-only-equivalent figure directories with six corrected SVGs.

  Unrelated assets are linked to the repository files.  Any old PNG/SVG/PDF
  sharing one of the six corrected stems is excluded so the app cannot show a
  stale label variant beside the corrected article figure.
  """
  main_source = Path(main_source_dir)
  supplementary_source = Path(supplementary_source_dir)
  overlay_root = Path(runtime_root) / "corrected_taxonomy_publication_overlay"
  main_overlay = overlay_root / "main"
  supplementary_overlay = overlay_root / "supplementary"
  main_overlay.mkdir(parents=True, exist_ok=True)
  supplementary_overlay.mkdir(parents=True, exist_ok=True)

  for source_dir, destination_dir in (
    (main_source, main_overlay),
    (supplementary_source, supplementary_overlay),
  ):
    if not source_dir.is_dir():
      continue
    for source in source_dir.iterdir():
      if not source.is_file():
        continue
      if source.stem in CORRECTED_TAXONOMY_STATIC_STEMS:
        continue
      _link_or_copy(source, destination_dir / source.name)

  for svg_name, member in CORRECTED_TAXONOMY_STATIC_MEMBERS.items():
    destination_dir = main_overlay if member.startswith("main/") else supplementary_overlay
    payload = corrected_taxonomy_static_bytes(svg_name)
    if payload is None:
      continue
    destination = destination_dir / svg_name
    if not destination.exists() or destination.read_bytes() != payload:
      destination.write_bytes(payload)

  return main_overlay, supplementary_overlay
