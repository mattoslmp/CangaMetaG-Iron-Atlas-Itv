#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import runpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = PROJECT_ROOT / "app_core.py"
TRANSFORMS = [
  PROJECT_ROOT / "src" / "app_base_transform.py",
  PROJECT_ROOT / "src" / "app_summary_transform.py",
  PROJECT_ROOT / "src" / "app_map_transform.py",
  PROJECT_ROOT / "src" / "app_bvbrc_transform.py",
  PROJECT_ROOT / "src" / "app_kegg_mtx_transform.py",
  PROJECT_ROOT / "src" / "app_ko_mtx_transform.py",
  PROJECT_ROOT / "src" / "app_public_ui_transform.py",
  PROJECT_ROOT / "src" / "app_public_runtime_defaults_transform.py",
  PROJECT_ROOT / "src" / "app_environment_details_transform.py",
  PROJECT_ROOT / "src" / "app_environment_reference_fix_transform.py",
  PROJECT_ROOT / "src" / "app_remove_static_overview_map_transform.py",
  PROJECT_ROOT / "src" / "app_scientific_contact_recipient_transform.py",
  PROJECT_ROOT / "src" / "app_bvbrc_cli_runtime_transform.py",
  PROJECT_ROOT / "src" / "app_antismash_clean_names_transform.py",
  PROJECT_ROOT / "src" / "app_repository_mag_download_transform.py",
]


def generated_source() -> str:
  source = CORE_PATH.read_text(encoding="utf-8")
  for transform_path in TRANSFORMS:
    namespace = runpy.run_path(
      str(transform_path),
      init_globals={"source": source},
    )
    source = namespace["source"]
  return source


def main() -> int:
  source = generated_source()
  compile(source, str(CORE_PATH), "exec")
  if ".repaired" in source.casefold():
    raise RuntimeError("Generated public Streamlit source still exposes .repaired")
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
    "def repository_mag_download_panel(",
    "Prepare the complete ZIP package for this MAG",
    "The application acts only as a download intermediary",
  ]
  missing = [text for text in required if text not in source]
  if missing:
    raise RuntimeError(
      "Generated Streamlit source is missing repository download features: "
      + "; ".join(missing)
    )
  print(
    "Generated Streamlit source compiled successfully: "
    f"{len(source.splitlines())} lines, {len(source.encode('utf-8'))} bytes"
  )
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
