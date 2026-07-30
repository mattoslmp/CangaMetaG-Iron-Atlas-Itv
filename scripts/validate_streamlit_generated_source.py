#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import re
import runpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_PATH = PROJECT_ROOT / "app.py"
CORE_PATH = PROJECT_ROOT / "app_core.py"


def transform_paths() -> list[Path]:
  """Read the authoritative transform order directly from app.py."""
  app_text = APP_PATH.read_text(encoding="utf-8")
  transform_names = re.findall(
    r'with_name\("src"\) / "([^"]+\.py)"',
    app_text,
  )
  if not transform_names:
    raise RuntimeError("No Streamlit transforms were discovered in app.py")
  paths = [PROJECT_ROOT / "src" / name for name in transform_names]
  missing = [str(path.relative_to(PROJECT_ROOT)) for path in paths if not path.exists()]
  if missing:
    raise FileNotFoundError("Missing Streamlit transform files: " + "; ".join(missing))
  if len(paths) != len(set(paths)):
    raise RuntimeError("app.py contains duplicate Streamlit transforms")
  return paths


def generated_source() -> str:
  source = CORE_PATH.read_text(encoding="utf-8")
  for transform_path in transform_paths():
    namespace = runpy.run_path(
      str(transform_path),
      init_globals={"source": source},
    )
    source = namespace["source"]
  return source


def main() -> int:
  source = generated_source()
  compile(source, str(CORE_PATH), "exec")

  forbidden_public_controls = [
    "Remote BV-BRC metagenomes directory",
    "When selecting a MAG without a local folder, try to download it automatically",
    "Force update: download again",
    "Batch download MAG2–MAG50",
    "Downloading with p3-cp",
  ]
  present = [text for text in forbidden_public_controls if text in source]
  if present:
    raise RuntimeError(
      "Generated Streamlit source still exposes server-side BV-BRC controls: "
      + "; ".join(present)
    )

  required = [
    "def _bvbrc_public_workspace_inventory(",
    '"get_archive_url"',
    '"get_download_url"',
    "Deliberately do not send Authorization",
    "Download {mag_id} directly from BV-BRC",
    "No personal credential will be used",
    "def repository_mag_download_panel(",
    "def _visitor_world_map_frame(",
    "def _visitor_world_map_figure(",
    "Mapa-múndi detalhado de visitas",
    "Detailed world map of visits",
    "<b>Visits:</b>",
    "Visit details by country, region and city",
    "CANGAMETAG_SCIENTIFIC_CLARITY_REVISION = 1",
    "original, previously unpublished study data",
    "Search lake MAG, classification or annotation",
    "Article MAGs available in BV-BRC",
    "Direct download of an article MAG",
    "number == 247",
    'inventory["MAG"].astype(str).ne("MAG247")',
    "Supplementary Table 8 — external iron-rich environments",
    "Supplementary Figure {supplementary_number}",
    "pathway modules associated with biogeochemical cycles",
    "SupplementaryFigure38_metagenome_KEGG_module_completeness_heatmap_P001.png",
    "CANGAMETAG_TAXONOMY_ARTICLE_ALIGNMENT_V1 = 1",
    "def _retractable_dataframe(",
    'txt("Mostrar/ocultar tabela", "Show/hide table")',
    "Barplots interativos correspondentes às Figuras 2 e 3",
    "article_static_source_validation",
    "Harmonização reprodutível da taxonomia NCBI",
    "CANGAMETAG_KEGG_S67_AXIS_READABILITY_V2 = 1",
    "def _kegg_s67_compact_label(",
    "def _kegg_reorder_full_matrix_like_grouped_source(",
    "cell_w = 104 if n_cols <= 50 else 94 if n_cols <= 90 else 86",
    "tickangle=0",
    "Lake metagenomes and external iron-rich environments",
  ]
  missing = [text for text in required if text not in source]
  if missing:
    raise RuntimeError(
      "Generated Streamlit source is missing required public features: "
      + "; ".join(missing)
    )

  if source.count('Path(__file__).with_name("src")'):
    raise RuntimeError("Generated source unexpectedly contains transform-chain declarations")

  direct_start = source.find("def _bvbrc_public_rpc")
  direct_end = source.find("def mags_tab():", direct_start)
  direct_layer = source[direct_start:direct_end]
  forbidden_auth = [
    'headers["Authorization"]',
    "headers['Authorization']",
    "BVBRC_TOKEN",
    "KB_AUTH_TOKEN",
  ]
  leaked = [text for text in forbidden_auth if text in direct_layer]
  if leaked:
    raise RuntimeError(
      "Anonymous BV-BRC download layer unexpectedly references authentication: "
      + "; ".join(leaked)
    )

  s67_start = source.find("def _kegg_s67_compact_label(")
  s67_end = source.find("def _kegg_scope_rows(", s67_start)
  s67_helpers = source[s67_start:s67_end]
  if not all(token in s67_helpers for token in [
    'width=16',
    'return "<br>".join(lines)',
    'reordered.sort_index(axis=1).equals(full_status.sort_index(axis=1))',
  ]):
    raise RuntimeError("S67 label wrapping or value-preservation checks are incomplete")

  print(
    "Generated Streamlit source compiled successfully: "
    f"{len(source.splitlines())} lines, {len(source.encode('utf-8'))} bytes, "
    f"{len(transform_paths())} transforms"
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
