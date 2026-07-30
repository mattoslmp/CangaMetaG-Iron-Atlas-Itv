#!/usr/bin/env python3
from __future__ import annotations

"""Refresh taxonomic names from NCBI and regenerate the canonical figures.

The script changes labels only. The original taxonomy file is restored after the
canonical figure generator finishes, while the harmonised table is saved under
``data/resultado.cds.tax.ncbi_current.tab`` for the app and future runs.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.ncbi_taxonomy_harmonization import (  # noqa: E402
  TARGET_RANKS,
  harmonize_taxonomy_frame,
  load_name_updates,
  transfer_palette_names,
)


TAXDUMP_URL = "https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz"
DATA = ROOT / "data"
ORIGINAL_TAXONOMY = DATA / "resultado.cds.tax.tab"
CURRENT_TAXONOMY = DATA / "resultado.cds.tax.ncbi_current.tab"
OTU_PATH = DATA / "resultado.cds.otu.tab"
UPDATE_AUDIT = DATA / "ncbi_taxonomy_name_updates.csv"
PALETTE_PATH = DATA / "taxonomy_palette.json"
FIGURE_SCRIPT = ROOT / "scripts" / "generate_final_domain_taxonomy_figures.py"
REPORT_PATH = ROOT / "reports" / "NCBI_TAXONOMY_HARMONIZATION_REPORT.json"
FIGURE_STEMS = [
  "Figure2_taxonomic_phylum_bacteria_horizontal_CDS",
  "Figure3_taxonomic_phylum_archaea_horizontal_CDS",
  "Figure4_taxonomic_bacteria_genus_profiles",
  "Figure5_taxonomic_archaea_genus_profiles",
]


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  parser.add_argument("--base-dir", type=Path, default=ROOT)
  parser.add_argument("--taxdump", type=Path, default=None, help="Existing NCBI taxdump.tar.gz or extracted directory")
  parser.add_argument("--download-taxdump", action="store_true", help="Download the current NCBI taxdump when needed")
  parser.add_argument("--skip-regeneration", action="store_true", help="Only update names and audit tables")
  parser.add_argument("--keep-cache", action="store_true")
  return parser.parse_args()


def _split_dmp(line: str) -> list[str]:
  return [part.strip() for part in line.rstrip("\n").split("\t|\t")]


def download_taxdump(target: Path) -> Path:
  target.parent.mkdir(parents=True, exist_ok=True)
  temporary = target.with_suffix(target.suffix + ".part")
  urllib.request.urlretrieve(TAXDUMP_URL, temporary)
  temporary.replace(target)
  return target


def extract_taxdump(taxdump: Path, destination: Path) -> Path:
  destination.mkdir(parents=True, exist_ok=True)
  if taxdump.is_dir():
    for name in ("names.dmp", "nodes.dmp"):
      source = taxdump / name
      if not source.exists():
        raise FileNotFoundError(source)
      shutil.copy2(source, destination / name)
    return destination
  with tarfile.open(taxdump, "r:gz") as archive:
    wanted = {"names.dmp", "nodes.dmp"}
    members = [member for member in archive.getmembers() if Path(member.name).name in wanted]
    if len(members) != 2:
      raise RuntimeError("NCBI taxdump does not contain names.dmp and nodes.dmp")
    for member in members:
      member.name = Path(member.name).name
      archive.extract(member, destination, filter="data")
  return destination


def target_names_by_rank(taxonomy: pd.DataFrame) -> dict[str, set[str]]:
  output: dict[str, set[str]] = {}
  for rank in TARGET_RANKS:
    if rank not in taxonomy.columns:
      output[rank] = set()
      continue
    output[rank] = {
      str(value).strip()
      for value in taxonomy[rank].dropna().astype(str)
      if str(value).strip().casefold() not in {"", "na", "nan", "none", "unknown", "unclassified"}
    }
  return output


def resolve_current_names(taxonomy: pd.DataFrame, extracted: Path) -> pd.DataFrame:
  targets = target_names_by_rank(taxonomy)
  target_lookup = {
    value.casefold(): (rank, value)
    for rank, names in targets.items()
    for value in names
  }
  candidate_rows: dict[str, list[dict[str, str]]] = {key: [] for key in target_lookup}
  candidate_taxids: set[str] = set()
  names_path = extracted / "names.dmp"
  with names_path.open("r", encoding="utf-8", errors="replace") as handle:
    for line in handle:
      parts = _split_dmp(line)
      if len(parts) < 4:
        continue
      taxid, name_txt, _, name_class = parts[:4]
      key = name_txt.casefold()
      if key in target_lookup:
        candidate_rows[key].append({"taxid": taxid, "matched_name_class": name_class, "matched_name": name_txt})
        candidate_taxids.add(taxid)

  node_ranks: dict[str, str] = {}
  with (extracted / "nodes.dmp").open("r", encoding="utf-8", errors="replace") as handle:
    for line in handle:
      parts = _split_dmp(line)
      if len(parts) >= 3 and parts[0] in candidate_taxids:
        node_ranks[parts[0]] = parts[2]

  scientific_names: dict[str, str] = {}
  if candidate_taxids:
    with names_path.open("r", encoding="utf-8", errors="replace") as handle:
      for line in handle:
        parts = _split_dmp(line)
        if len(parts) >= 4 and parts[0] in candidate_taxids and parts[3] == "scientific name":
          scientific_names[parts[0]] = parts[1]

  existing = load_name_updates(UPDATE_AUDIT)
  fallback = {
    (str(row["rank"]), str(row["original_name"]).casefold()): row
    for _, row in existing.iterrows()
  }
  records: list[dict[str, str]] = []
  for rank, values in targets.items():
    expected_rank = rank.casefold()
    for original in sorted(values, key=str.casefold):
      candidates = [
        row for row in candidate_rows.get(original.casefold(), [])
        if node_ranks.get(row["taxid"], "").casefold() == expected_rank
      ]
      chosen = None
      if candidates:
        chosen = next((row for row in candidates if row["matched_name_class"] == "scientific name"), candidates[0])
      if chosen is not None:
        taxid = chosen["taxid"]
        current = scientific_names.get(taxid, original)
        status = "updated" if current != original else "current"
        records.append({
          "rank": rank,
          "original_name": original,
          "current_name": current,
          "ncbi_taxid": taxid,
          "status": status,
          "matched_name_class": chosen["matched_name_class"],
          "source": f"NCBI taxdump: {TAXDUMP_URL}",
        })
        continue
      fallback_row = fallback.get((rank, original.casefold()))
      if fallback_row is not None:
        records.append({column: str(fallback_row.get(column, "")) for column in [
          "rank", "original_name", "current_name", "ncbi_taxid", "status", "matched_name_class", "source"
        ]})
      else:
        records.append({
          "rank": rank,
          "original_name": original,
          "current_name": original,
          "ncbi_taxid": "",
          "status": "unmatched-kept-unchanged",
          "matched_name_class": "",
          "source": f"NCBI taxdump: {TAXDUMP_URL}",
        })
  return pd.DataFrame(records).sort_values(["rank", "original_name"], key=lambda series: series.astype(str).str.casefold()).reset_index(drop=True)


def image_geometry(root: Path) -> dict[str, dict[str, float]]:
  directory = root / "outputs" / "final_publication_figures"
  output: dict[str, dict[str, float]] = {}
  for stem in FIGURE_STEMS:
    path = directory / f"{stem}.png"
    if not path.exists():
      continue
    with Image.open(path) as image:
      width, height = image.size
    output[stem] = {"width": width, "height": height, "aspect_ratio": width / max(height, 1)}
  return output


def update_palette(audit: pd.DataFrame) -> None:
  try:
    palette = json.loads(PALETTE_PATH.read_text(encoding="utf-8")) if PALETTE_PATH.exists() else {}
  except Exception:
    palette = {}
  transferred = transfer_palette_names({str(key): str(value) for key, value in palette.items()}, audit)
  PALETTE_PATH.write_text(json.dumps(dict(sorted(transferred.items(), key=lambda item: item[0].casefold())), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def regenerate_with_current_labels(root: Path, current_taxonomy: pd.DataFrame) -> dict[str, object]:
  before_geometry = image_geometry(root)
  original_bytes = ORIGINAL_TAXONOMY.read_bytes()
  temporary_path = ORIGINAL_TAXONOMY.with_suffix(ORIGINAL_TAXONOMY.suffix + ".ncbi-refresh.tmp")
  current_taxonomy.to_csv(temporary_path, sep="\t")
  try:
    temporary_path.replace(ORIGINAL_TAXONOMY)
    completed = subprocess.run(
      [sys.executable, str(FIGURE_SCRIPT)],
      cwd=str(root),
      check=True,
      capture_output=True,
      text=True,
    )
  finally:
    ORIGINAL_TAXONOMY.write_bytes(original_bytes)
    if temporary_path.exists():
      temporary_path.unlink()
  after_geometry = image_geometry(root)
  geometry_checks = []
  for stem in FIGURE_STEMS:
    before = before_geometry.get(stem)
    after = after_geometry.get(stem)
    if before and after:
      ratio_difference = abs(float(before["aspect_ratio"]) - float(after["aspect_ratio"]))
      geometry_checks.append({
        "figure": stem,
        "before_aspect_ratio": before["aspect_ratio"],
        "after_aspect_ratio": after["aspect_ratio"],
        "absolute_aspect_ratio_difference": ratio_difference,
        "status": "PASS" if ratio_difference <= 0.03 else "FAIL",
      })
  failures = [row for row in geometry_checks if row["status"] != "PASS"]
  if failures:
    raise RuntimeError(f"Figure proportions changed beyond tolerance: {failures}")
  return {
    "stdout_tail": completed.stdout[-4000:],
    "stderr_tail": completed.stderr[-4000:],
    "geometry_checks": geometry_checks,
  }


def main() -> int:
  args = parse_args()
  root = args.base_dir.resolve()
  if root != ROOT:
    raise ValueError(f"This packaged script expects repository root {ROOT}; received {root}")
  if not ORIGINAL_TAXONOMY.exists() or not OTU_PATH.exists():
    raise FileNotFoundError("Packaged taxonomy/OTU source files are missing")

  taxonomy = pd.read_csv(ORIGINAL_TAXONOMY, sep="\t", index_col=0, dtype=str, keep_default_na=False)
  taxonomy.columns = [str(column).strip() for column in taxonomy.columns]
  otu_before = pd.read_csv(OTU_PATH, sep="\t", index_col=0).apply(pd.to_numeric, errors="coerce").fillna(0.0)
  count_checksum_before = float(otu_before.to_numpy(float).sum())

  cache_root = root / ".cache" / "ncbi_taxonomy"
  cache_root.mkdir(parents=True, exist_ok=True)
  taxdump = args.taxdump.resolve() if args.taxdump is not None else cache_root / "taxdump.tar.gz"
  if not taxdump.exists():
    if not args.download_taxdump:
      raise FileNotFoundError(f"Taxdump not found: {taxdump}. Use --download-taxdump.")
    download_taxdump(taxdump)
  extracted = cache_root / "extracted"
  if extracted.exists():
    shutil.rmtree(extracted)
  extract_taxdump(taxdump, extracted)

  audit = resolve_current_names(taxonomy, extracted)
  audit.to_csv(UPDATE_AUDIT, index=False)
  current = harmonize_taxonomy_frame(taxonomy, audit)
  if current.shape != taxonomy.shape or not current.index.equals(taxonomy.index) or list(current.columns) != list(taxonomy.columns):
    raise RuntimeError("Taxonomy harmonisation changed table geometry or identifiers")
  CURRENT_TAXONOMY.parent.mkdir(parents=True, exist_ok=True)
  current.to_csv(CURRENT_TAXONOMY, sep="\t")
  update_palette(audit)

  otu_after = pd.read_csv(OTU_PATH, sep="\t", index_col=0).apply(pd.to_numeric, errors="coerce").fillna(0.0)
  count_checksum_after = float(otu_after.to_numpy(float).sum())
  if otu_before.shape != otu_after.shape or not np.array_equal(otu_before.to_numpy(float), otu_after.to_numpy(float)):
    raise RuntimeError("OTU/count data changed during taxonomy harmonisation")

  regeneration: dict[str, object] = {"skipped": True}
  if not args.skip_regeneration:
    regeneration = regenerate_with_current_labels(root, current)

  changed = audit[audit["original_name"].astype(str) != audit["current_name"].astype(str)]
  report = {
    "script": str(Path(__file__).relative_to(root)),
    "ncbi_taxdump": TAXDUMP_URL,
    "target_ranks": list(TARGET_RANKS),
    "taxonomy_rows": int(len(taxonomy)),
    "taxonomy_columns": list(taxonomy.columns),
    "resolved_names": int(len(audit)),
    "updated_names": int(len(changed)),
    "current_taxonomy_output": str(CURRENT_TAXONOMY.relative_to(root)),
    "audit_output": str(UPDATE_AUDIT.relative_to(root)),
    "otu_shape_before": list(otu_before.shape),
    "otu_shape_after": list(otu_after.shape),
    "count_checksum_before": count_checksum_before,
    "count_checksum_after": count_checksum_after,
    "counts_unchanged": bool(count_checksum_before == count_checksum_after and np.array_equal(otu_before.to_numpy(float), otu_after.to_numpy(float))),
    "regeneration": regeneration,
  }
  REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
  REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  if not args.keep_cache:
    shutil.rmtree(cache_root, ignore_errors=True)
  print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
