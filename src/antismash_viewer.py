from __future__ import annotations

from io import BytesIO
from pathlib import Path
import base64
import mimetypes
import re
import zipfile
import pandas as pd

from ._helpers import BASE_DIR, zip_directory


_REPAIRED_SUFFIX = re.compile(r"\.repaired", flags=re.IGNORECASE)


def clean_antismash_name(value: str | Path) -> str:
  """Remove only the public ``.repaired`` label from an antiSMASH name.

  This function never renames or edits a source file. It is used exclusively
  for labels and suggested download filenames, because changing files inside
  an antiSMASH run could break references from index.html, regions.js or other
  packaged assets.
  """
  original = str(value)
  cleaned = _REPAIRED_SUFFIX.sub("", original)
  return cleaned or original


def discover_antismash_runs() -> list[dict]:
  roots = [
    BASE_DIR / "data" / "kegg_modules" / "mags" / "gbk_antismash",
    BASE_DIR / "data" / "antismash",
    BASE_DIR / "outputs" / "antismash",
  ]
  runs = []
  for root in roots:
    if not root.exists():
      continue
    for index in sorted(root.rglob("index.html")):
      run_dir = index.parent
      source_run_name = run_dir.name
      display_run_name = clean_antismash_name(source_run_name)
      match = re.search(
        r"(?:bin[._-]?|MAG[._-]?)(\d+)",
        source_run_name,
        flags=re.I,
      )
      mag_id = f"MAG{int(match.group(1))}" if match else ""
      gbks = sorted(run_dir.rglob("*.gbk"))
      fastas = sorted([
        path
        for path in run_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".fa", ".fasta", ".fna"}
      ])
      gbk_path = gbks[0] if gbks else None
      fasta_path = fastas[0] if fastas else None
      runs.append({
        "run_name": (
          f"{mag_id} — {display_run_name}" if mag_id else display_run_name
        ),
        "name": display_run_name,
        # Keep the legacy public key, but expose the cleaned label only.
        # The real directory remains available through run_dir for reading.
        "original_run_name": display_run_name,
        "mag_id": mag_id,
        "run_dir": str(run_dir),
        "index_html": str(index),
        "regions": len([path for path in gbks if "region" in path.name.lower()]),
        "gbk_path": str(gbk_path) if gbk_path else "",
        "fasta_path": str(fasta_path) if fasta_path else "",
        "gbk_download_name": clean_antismash_name(gbk_path.name) if gbk_path else "",
        "fasta_download_name": clean_antismash_name(fasta_path.name) if fasta_path else "",
      })
  return runs


def antismash_inventory() -> pd.DataFrame:
  """Return a public inventory without exposing source paths or repaired labels."""
  columns = [
    "run_name",
    "name",
    "mag_id",
    "regions",
    "gbk_file",
    "fasta_file",
    "run_data_preserved",
  ]
  rows = []
  for run in discover_antismash_runs():
    rows.append({
      "run_name": run.get("run_name", ""),
      "name": run.get("name", ""),
      "mag_id": run.get("mag_id", ""),
      "regions": run.get("regions", 0),
      "gbk_file": run.get("gbk_download_name", ""),
      "fasta_file": run.get("fasta_download_name", ""),
      "run_data_preserved": True,
    })
  return pd.DataFrame(rows, columns=columns)


def antismash_run_zip_bytes(run_dir: Path | str) -> bytes:
  # Preserve every internal filename and byte exactly as stored in the run.
  return zip_directory(Path(run_dir))


def self_contained_antismash_html(run_dir: Path) -> str:
  run_dir = Path(run_dir)
  index = run_dir / "index.html"
  if not index.exists():
    return "<html><body><p>antiSMASH index.html not found.</p></body></html>"
  html = index.read_text(encoding="utf-8", errors="replace")
  # Inline local CSS/JS/image assets to make the viewer portable.
  pattern = re.compile(
    r"(?P<prefix>(?:src|href)=[\"'])(?P<path>[^\"']+)(?P<suffix>[\"'])"
  )

  def replace(match):
    relative = match.group("path")
    if relative.startswith(("http://", "https://", "data:", "#")):
      return match.group(0)
    asset = (run_dir / relative).resolve()
    try:
      asset.relative_to(run_dir.resolve())
    except Exception:
      return match.group(0)
    if not asset.is_file():
      return match.group(0)
    mime = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(asset.read_bytes()).decode("ascii")
    return (
      f"{match.group('prefix')}data:{mime};base64,{encoded}"
      f"{match.group('suffix')}"
    )

  return pattern.sub(replace, html)
