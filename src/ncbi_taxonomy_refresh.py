from __future__ import annotations

"""Robust implementation for current-NCBI taxonomy refresh and figure rebuild."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image

from .ncbi_taxonomy_harmonization import (
  TARGET_RANKS,
  harmonize_taxonomy_frame,
  load_name_updates,
  transfer_palette_names,
)


TAXDUMP_URL = "https://ftp.ncbi.nlm.nih.gov/pub/taxonomy/taxdump.tar.gz"
FIGURE_STEMS = [
  "Figure2_taxonomic_phylum_bacteria_horizontal_CDS",
  "Figure3_taxonomic_phylum_archaea_horizontal_CDS",
  "Figure4_taxonomic_bacteria_genus_profiles",
  "Figure5_taxonomic_archaea_genus_profiles",
]


def split_dmp(line: str) -> list[str]:
  """Parse NCBI .dmp rows regardless of the final tab before the pipe."""
  return [part.strip() for part in line.rstrip("\n").split("|")]


def download_taxdump(target: Path) -> Path:
  target.parent.mkdir(parents=True, exist_ok=True)
  partial = target.with_suffix(target.suffix + ".part")
  urllib.request.urlretrieve(TAXDUMP_URL, partial)
  partial.replace(target)
  return target


def extract_taxdump(source: Path, destination: Path) -> Path:
  destination.mkdir(parents=True, exist_ok=True)
  if source.is_dir():
    for name in ("names.dmp", "nodes.dmp"):
      path = source / name
      if not path.exists():
        raise FileNotFoundError(path)
      shutil.copy2(path, destination / name)
    return destination
  with tarfile.open(source, "r:gz") as archive:
    by_name = {Path(member.name).name: member for member in archive.getmembers()}
    for name in ("names.dmp", "nodes.dmp"):
      member = by_name.get(name)
      if member is None:
        raise RuntimeError(f"NCBI taxdump is missing {name}")
      handle = archive.extractfile(member)
      if handle is None:
        raise RuntimeError(f"Could not extract {name}")
      with handle, (destination / name).open("wb") as output:
        shutil.copyfileobj(handle, output)
  return destination


def target_names_by_rank(taxonomy: pd.DataFrame) -> dict[str, set[str]]:
  missing = {"", "na", "n/a", "nan", "none", "unknown", "unclassified", "undefined", "null"}
  result: dict[str, set[str]] = {}
  for rank in TARGET_RANKS:
    if rank not in taxonomy.columns:
      result[rank] = set()
      continue
    result[rank] = {
      str(value).strip()
      for value in taxonomy[rank].dropna().astype(str)
      if str(value).strip().casefold() not in missing
    }
  return result


def resolve_current_names(taxonomy: pd.DataFrame, extracted: Path, fallback_path: Path) -> pd.DataFrame:
  targets = target_names_by_rank(taxonomy)
  all_target_names = {value.casefold() for names in targets.values() for value in names}
  candidates: dict[str, list[dict[str, str]]] = {name: [] for name in all_target_names}
  candidate_taxids: set[str] = set()
  names_path = extracted / "names.dmp"

  with names_path.open("r", encoding="utf-8", errors="replace") as handle:
    for line in handle:
      parts = split_dmp(line)
      if len(parts) < 4:
        continue
      taxid, name_text, _, name_class = parts[:4]
      key = name_text.casefold()
      if key in candidates:
        candidates[key].append({
          "taxid": taxid,
          "matched_name": name_text,
          "matched_name_class": name_class,
        })
        candidate_taxids.add(taxid)

  node_rank: dict[str, str] = {}
  with (extracted / "nodes.dmp").open("r", encoding="utf-8", errors="replace") as handle:
    for line in handle:
      parts = split_dmp(line)
      if len(parts) >= 3 and parts[0] in candidate_taxids:
        node_rank[parts[0]] = parts[2]

  scientific_name: dict[str, str] = {}
  with names_path.open("r", encoding="utf-8", errors="replace") as handle:
    for line in handle:
      parts = split_dmp(line)
      if len(parts) >= 4 and parts[0] in candidate_taxids and parts[3] == "scientific name":
        scientific_name[parts[0]] = parts[1]

  fallback_frame = load_name_updates(fallback_path)
  fallback = {
    (str(row["rank"]), str(row["original_name"]).casefold()): row
    for _, row in fallback_frame.iterrows()
  }
  rows: list[dict[str, str]] = []
  columns = [
    "rank", "original_name", "current_name", "ncbi_taxid", "status",
    "matched_name_class", "source",
  ]
  for rank, names in targets.items():
    expected_rank = rank.casefold()
    for original in sorted(names, key=str.casefold):
      compatible = [
        row for row in candidates.get(original.casefold(), [])
        if node_rank.get(row["taxid"], "").casefold() == expected_rank
      ]
      chosen = next(
        (row for row in compatible if row["matched_name_class"] == "scientific name"),
        compatible[0] if compatible else None,
      )
      if chosen is not None:
        current = scientific_name.get(chosen["taxid"], original)
        rows.append({
          "rank": rank,
          "original_name": original,
          "current_name": current,
          "ncbi_taxid": chosen["taxid"],
          "status": "updated" if current != original else "current",
          "matched_name_class": chosen["matched_name_class"],
          "source": f"NCBI taxdump: {TAXDUMP_URL}",
        })
        continue
      fallback_row = fallback.get((rank, original.casefold()))
      if fallback_row is not None:
        rows.append({column: str(fallback_row.get(column, "")) for column in columns})
      else:
        rows.append({
          "rank": rank,
          "original_name": original,
          "current_name": original,
          "ncbi_taxid": "",
          "status": "unmatched-kept-unchanged",
          "matched_name_class": "",
          "source": f"NCBI taxdump: {TAXDUMP_URL}",
        })
  return pd.DataFrame(rows, columns=columns).sort_values(
    ["rank", "original_name"],
    key=lambda series: series.astype(str).str.casefold(),
  ).reset_index(drop=True)


def figure_geometry(root: Path) -> dict[str, dict[str, float]]:
  directory = root / "outputs" / "final_publication_figures"
  result: dict[str, dict[str, float]] = {}
  for stem in FIGURE_STEMS:
    path = directory / f"{stem}.png"
    if not path.exists():
      continue
    with Image.open(path) as image:
      width, height = image.size
    result[stem] = {
      "width": int(width),
      "height": int(height),
      "aspect_ratio": float(width / max(height, 1)),
    }
  return result


def update_palette(palette_path: Path, audit: pd.DataFrame) -> None:
  try:
    raw = json.loads(palette_path.read_text(encoding="utf-8")) if palette_path.exists() else {}
  except Exception:
    raw = {}
  updated = transfer_palette_names({str(key): str(value) for key, value in raw.items()}, audit)
  palette_path.write_text(
    json.dumps(dict(sorted(updated.items(), key=lambda item: item[0].casefold())), indent=2, ensure_ascii=False) + "\n",
    encoding="utf-8",
  )


def regenerate_figures(root: Path, current_taxonomy: pd.DataFrame) -> dict[str, object]:
  original_path = root / "data" / "resultado.cds.tax.tab"
  figure_scripts = [
    root / "scripts" / "generate_final_domain_taxonomy_figures.py",
    root / "scripts" / "generate_taxonomy_supplementary_figures.py",
  ]
  original_bytes = original_path.read_bytes()
  before = figure_geometry(root)
  temporary = original_path.with_suffix(original_path.suffix + ".ncbi-current.tmp")
  current_taxonomy.to_csv(temporary, sep="\t")
  executions: list[dict[str, str]] = []
  try:
    temporary.replace(original_path)
    with tempfile.TemporaryDirectory(prefix="cangametag-taxonomy-runtime-") as runtime_dir:
      child_environment = os.environ.copy()
      child_environment["CANGAMETAG_RUNTIME_DIR"] = runtime_dir
      child_environment["MPLCONFIGDIR"] = str(Path(runtime_dir) / "matplotlib")
      for figure_script in figure_scripts:
        if not figure_script.exists():
          continue
        command = [sys.executable, str(figure_script)]
        if figure_script.name == "generate_taxonomy_supplementary_figures.py":
          command.extend(["--base-dir", str(root)])
        completed = subprocess.run(
          command,
          cwd=str(root),
          check=False,
          capture_output=True,
          text=True,
          env=child_environment,
        )
        if completed.returncode != 0:
          raise RuntimeError(
            f"Taxonomy figure regeneration failed for {figure_script.relative_to(root)} "
            f"(exit {completed.returncode}).\nSTDOUT:\n{completed.stdout[-4000:]}\n"
            f"STDERR:\n{completed.stderr[-4000:]}"
          )
        executions.append({
          "script": str(figure_script.relative_to(root)),
          "stdout_tail": completed.stdout[-4000:],
          "stderr_tail": completed.stderr[-4000:],
        })
  finally:
    original_path.write_bytes(original_bytes)
    temporary.unlink(missing_ok=True)
  after = figure_geometry(root)
  checks: list[dict[str, object]] = []
  for stem in FIGURE_STEMS:
    if stem not in before or stem not in after:
      continue
    difference = abs(float(before[stem]["aspect_ratio"]) - float(after[stem]["aspect_ratio"]))
    checks.append({
      "figure": stem,
      "before_aspect_ratio": before[stem]["aspect_ratio"],
      "after_aspect_ratio": after[stem]["aspect_ratio"],
      "absolute_aspect_ratio_difference": difference,
      "status": "PASS" if difference <= 0.03 else "FAIL",
    })
  failures = [row for row in checks if row["status"] != "PASS"]
  if failures:
    raise RuntimeError(f"Figure proportions changed beyond tolerance: {failures}")
  return {
    "executions": executions,
    "geometry_checks": checks,
  }


def run_refresh(
  root: Path,
  taxdump: Path | None = None,
  download: bool = False,
  skip_regeneration: bool = False,
  keep_cache: bool = False,
) -> dict[str, object]:
  root = root.resolve()
  data = root / "data"
  original_taxonomy_path = data / "resultado.cds.tax.tab"
  current_taxonomy_path = data / "resultado.cds.tax.ncbi_current.tab"
  otu_path = data / "resultado.cds.otu.tab"
  audit_path = data / "ncbi_taxonomy_name_updates.csv"
  palette_path = data / "taxonomy_palette.json"
  report_path = root / "reports" / "NCBI_TAXONOMY_HARMONIZATION_REPORT.json"
  if not original_taxonomy_path.exists() or not otu_path.exists():
    raise FileNotFoundError("Packaged taxonomy or OTU source is missing")

  taxonomy = pd.read_csv(original_taxonomy_path, sep="\t", index_col=0, dtype=str, keep_default_na=False)
  taxonomy.columns = [str(column).strip() for column in taxonomy.columns]
  otu_before = pd.read_csv(otu_path, sep="\t", index_col=0).apply(pd.to_numeric, errors="coerce").fillna(0.0)

  cache = root / ".cache" / "ncbi_taxonomy"
  cache.mkdir(parents=True, exist_ok=True)
  dump_path = taxdump.resolve() if taxdump is not None else cache / "taxdump.tar.gz"
  if not dump_path.exists():
    if not download:
      raise FileNotFoundError(f"Taxdump not found: {dump_path}; use --download-taxdump")
    download_taxdump(dump_path)
  extracted = cache / "extracted"
  shutil.rmtree(extracted, ignore_errors=True)
  extract_taxdump(dump_path, extracted)

  audit = resolve_current_names(taxonomy, extracted, audit_path)
  audit.to_csv(audit_path, index=False)
  current = harmonize_taxonomy_frame(taxonomy, audit)
  if current.shape != taxonomy.shape or not current.index.equals(taxonomy.index) or list(current.columns) != list(taxonomy.columns):
    raise RuntimeError("Taxonomy table geometry or identifiers changed")
  current.to_csv(current_taxonomy_path, sep="\t")
  update_palette(palette_path, audit)

  otu_after = pd.read_csv(otu_path, sep="\t", index_col=0).apply(pd.to_numeric, errors="coerce").fillna(0.0)
  counts_equal = bool(
    otu_before.shape == otu_after.shape
    and otu_before.index.equals(otu_after.index)
    and otu_before.columns.equals(otu_after.columns)
    and np.array_equal(otu_before.to_numpy(float), otu_after.to_numpy(float))
  )
  if not counts_equal:
    raise RuntimeError("OTU/count data changed during taxonomy name harmonisation")

  regeneration: dict[str, object] = {"skipped": True}
  if not skip_regeneration:
    regeneration = regenerate_figures(root, current)
  changed = audit[audit["original_name"].astype(str) != audit["current_name"].astype(str)]
  report: dict[str, object] = {
    "implementation": "src/ncbi_taxonomy_refresh.py",
    "ncbi_taxdump": TAXDUMP_URL,
    "target_ranks": list(TARGET_RANKS),
    "taxonomy_shape": list(taxonomy.shape),
    "otu_shape": list(otu_before.shape),
    "otu_count_checksum": float(otu_before.to_numpy(float).sum()),
    "counts_unchanged": counts_equal,
    "resolved_names": int(len(audit)),
    "updated_names": int(len(changed)),
    "current_taxonomy_output": str(current_taxonomy_path.relative_to(root)),
    "audit_output": str(audit_path.relative_to(root)),
    "application_scope": "all taxonomy loaders and all interactive Plotly figure/audit labels",
    "traceability_tabs": ["Source", "Processed", "Output", "Plotted values"],
    "regeneration": regeneration,
  }
  report_path.parent.mkdir(parents=True, exist_ok=True)
  report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8")
  if not keep_cache:
    shutil.rmtree(cache, ignore_errors=True)
  return report
