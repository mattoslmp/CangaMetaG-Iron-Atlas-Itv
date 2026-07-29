#!/usr/bin/env python3
"""Upload a prepared folder to a Hugging Face Space using environment secrets."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from huggingface_hub import HfApi


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--folder", type=Path, required=True)
  parser.add_argument("--repo-id", help="HF_USERNAME/HF_SPACE_NAME; defaults to environment values")
  parser.add_argument("--private", action="store_true")
  args = parser.parse_args()
  token = os.environ.get("HF_TOKEN", "").strip()
  if not token:
    raise SystemExit("HF_TOKEN is required in the environment")
  repo_id = args.repo_id or f"{os.environ.get('HF_USERNAME', '').strip()}/{os.environ.get('HF_SPACE_NAME', '').strip()}"
  if repo_id.startswith("/") or repo_id.endswith("/") or "/" not in repo_id:
    raise SystemExit("Set --repo-id or HF_USERNAME and HF_SPACE_NAME")
  folder = args.folder.resolve()
  if not folder.is_dir():
    raise SystemExit(f"Folder not found: {folder}")
  api = HfApi(token=token)
  api.create_repo(repo_id=repo_id, repo_type="space", space_sdk="docker", private=args.private, exist_ok=True)
  api.upload_folder(
    folder_path=str(folder),
    repo_id=repo_id,
    repo_type="space",
    commit_message="Deploy validated CangaMetaG application",
    ignore_patterns=["**/.env", "**/secrets.toml", "**/__pycache__/**", "**/*.pyc"],
  )
  print(f"Uploaded to https://huggingface.co/spaces/{repo_id}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
