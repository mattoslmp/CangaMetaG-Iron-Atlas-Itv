#!/usr/bin/env python3
"""Prepare a deterministic Docker Space folder without secrets or runtime state."""
from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path

INCLUDE = [
  "app.py", "src", "assets", "data", "database", "outputs/app_supplementary_figures",
  "tables", "requirements.txt", "run_app_no_root.sh",
]
EXCLUDED_NAMES = {
  ".git", ".venv", "__pycache__", ".pytest_cache", ".streamlit", "logs",
  ".env", "secrets.toml", "admin_credentials.json",
}


def sha256(path: Path) -> str:
  h = hashlib.sha256()
  with path.open("rb") as handle:
    for block in iter(lambda: handle.read(1024 * 1024), b""):
      h.update(block)
  return h.hexdigest()


def ignored(path: Path) -> bool:
  return any(part in EXCLUDED_NAMES for part in path.parts) or path.name.endswith((".key", ".pem"))


def copy_item(source: Path, target: Path) -> None:
  if source.is_dir():
    for path in source.rglob("*"):
      rel = path.relative_to(source)
      if ignored(rel) or path.is_dir():
        continue
      destination = target / rel
      destination.parent.mkdir(parents=True, exist_ok=True)
      shutil.copy2(path, destination)
  elif source.is_file():
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--app-root", type=Path, default=Path("."))
  parser.add_argument("--output-dir", type=Path, required=True)
  args = parser.parse_args()
  root = args.app_root.resolve()
  output = args.output_dir.resolve()
  if output.exists():
    shutil.rmtree(output)
  output.mkdir(parents=True)

  for relative in INCLUDE:
    source = root / relative
    if source.exists():
      copy_item(source, output / relative)

  (output / "README.md").write_text(
    "---\n"
    "title: CangaMetaG Iron Metagenomic Atlas\n"
    "emoji: 🧬\n"
    "colorFrom: blue\n"
    "colorTo: green\n"
    "sdk: docker\n"
    "app_port: 7860\n"
    "---\n\n"
    "Validated Docker deployment of the CangaMetaG Streamlit application.\n",
    encoding="utf-8",
  )
  (output / "Dockerfile").write_text(
    "FROM python:3.11-slim\n"
    "ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1\n"
    "WORKDIR /app\n"
    "COPY requirements.txt /app/requirements.txt\n"
    "RUN python -m pip install --upgrade pip && python -m pip install -r requirements.txt\n"
    "COPY . /app\n"
    "EXPOSE 7860\n"
    "CMD [\"streamlit\", \"run\", \"app.py\", \"--server.address\", \"0.0.0.0\", \"--server.port\", \"7860\", \"--server.headless\", \"true\"]\n",
    encoding="utf-8",
  )
  (output / ".dockerignore").write_text(
    ".git\n.venv\n__pycache__\n*.pyc\n.env\n.streamlit/secrets.toml\nlogs\n",
    encoding="utf-8",
  )

  rows = []
  for path in sorted(p for p in output.rglob("*") if p.is_file()):
    rows.append((str(path.relative_to(output)), path.stat().st_size, sha256(path)))
  manifest = output / "SPACE_FILE_MANIFEST_SHA256.csv"
  with manifest.open("w", newline="", encoding="utf-8") as handle:
    writer = csv.writer(handle)
    writer.writerow(["path", "size_bytes", "sha256"])
    writer.writerows(rows)
  print(output)
  print(f"files={len(rows)}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
