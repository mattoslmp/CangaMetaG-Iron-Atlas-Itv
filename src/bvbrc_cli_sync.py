from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import re
import shutil
import subprocess

import pandas as pd

from ._helpers import canonical_mag


DEFAULT_WORKSPACE_BASE = "/mattoslmp@patricbrc.org/Lakes-Canga/metagenomas"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


@dataclass
class BvbrcSyncResult:
  mag: str
  ok: bool
  status: str
  command: str = ""
  stdout: str = ""
  stderr: str = ""
  local_path: str = ""
  remote_path: str = ""

  def as_row(self) -> dict:
    return asdict(self)


def _safe_local_root(local_annotation_dir: str | Path = "Annotation") -> Path:
  requested = Path(local_annotation_dir).expanduser()
  root = requested if requested.is_absolute() else PROJECT_ROOT / requested
  try:
    resolved = root.resolve()
    project = PROJECT_ROOT.resolve()
    if not resolved.is_relative_to(project):
      return project / "Annotation"
    return resolved
  except Exception:
    return PROJECT_ROOT / "Annotation"


def _displayable_file_count(folder: Path) -> int:
  if not folder.exists():
    return 0
  suffixes = {
    ".fa", ".faa", ".fasta", ".fna", ".ffn", ".gb", ".gbk", ".genbank",
    ".txt", ".tsv", ".csv", ".xls", ".xlsx", ".html", ".json",
  }
  return sum(1 for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in suffixes)


def _run(command: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
  return subprocess.run(
    command,
    text=True,
    capture_output=True,
    timeout=timeout,
    check=False,
  )


def bvbrc_cli_status() -> pd.DataFrame:
  p3_ls = shutil.which("p3-ls")
  p3_cp = shutil.which("p3-cp")
  rows = [
    {
      "component": "p3-ls",
      "installed": bool(p3_ls),
      "path": p3_ls or "",
      "purpose": "List BV-BRC workspace entries",
    },
    {
      "component": "p3-cp",
      "installed": bool(p3_cp),
      "path": p3_cp or "",
      "purpose": "Copy BV-BRC workspace results into Annotation/MAGx",
    },
  ]
  return pd.DataFrame(rows)


def install_commands_ubuntu() -> str:
  return (
    "curl -O https://raw.githubusercontent.com/BV-BRC/BV-BRC-CLI/master/cli-install.sh\n"
    "bash cli-install.sh\n"
    "p3-login mattoslmp"
  )


def inventory_local_annotations(local_annotation_dir: str | Path = "Annotation") -> pd.DataFrame:
  root = _safe_local_root(local_annotation_dir)
  rows = []
  if root.exists():
    for folder in sorted(path for path in root.iterdir() if path.is_dir()):
      status = local_annotation_status(folder.name, root)
      rows.append({
        "MAG": status["MAG"],
        "folder": status["local_path"],
        "files": status["files"],
        "displayable_files": status["displayable_files"],
        "ready_for_app": status["ready_for_app"],
      })
  return pd.DataFrame(rows)


def local_annotation_status(
  mag_id: object,
  local_annotation_dir: str | Path = "Annotation",
) -> dict:
  root = _safe_local_root(local_annotation_dir)
  cid = canonical_mag(mag_id)
  candidates = [root / cid]
  if root.exists():
    candidates.extend(path for path in root.iterdir() if path.is_dir() and canonical_mag(path.name) == cid)
  folder = next((path for path in candidates if path.exists()), root / cid)
  files = sum(1 for path in folder.rglob("*") if path.is_file()) if folder.exists() else 0
  displayable = _displayable_file_count(folder)
  ready = bool(folder.exists() and displayable > 0)
  return {
    "MAG": cid,
    "folder": str(folder),
    "local_path": str(folder),
    "exists": folder.exists(),
    "files": files,
    "displayable_files": displayable,
    "ready_for_app": ready,
    "reason": "local_annotation_available" if ready else "local_annotation_missing_or_empty",
  }


def list_remote_path(
  workspace_base: str = DEFAULT_WORKSPACE_BASE,
  timeout: int = 180,
) -> BvbrcSyncResult:
  executable = shutil.which("p3-ls")
  if not executable:
    return BvbrcSyncResult(
      mag="",
      ok=False,
      status="cli_not_installed",
      stderr="p3-ls was not found in PATH.",
      remote_path=str(workspace_base),
    )
  command = [executable, str(workspace_base).strip()]
  try:
    process = _run(command, timeout=timeout)
  except subprocess.TimeoutExpired as exc:
    return BvbrcSyncResult(
      mag="",
      ok=False,
      status="remote_listing_timeout",
      command=" ".join(command),
      stdout=str(exc.stdout or ""),
      stderr=str(exc.stderr or ""),
      remote_path=str(workspace_base),
    )
  except Exception as exc:
    return BvbrcSyncResult(
      mag="",
      ok=False,
      status="remote_listing_error",
      command=" ".join(command),
      stderr=str(exc),
      remote_path=str(workspace_base),
    )
  return BvbrcSyncResult(
    mag="",
    ok=process.returncode == 0,
    status="remote_directory_listed" if process.returncode == 0 else "remote_listing_failed",
    command=" ".join(command),
    stdout=process.stdout or "",
    stderr=process.stderr or "",
    remote_path=str(workspace_base),
  )


def _remote_entry_for_mag(listing: str, mag: str) -> str:
  for line in str(listing).splitlines():
    tokens = [token.strip().strip("'") for token in re.split(r"\s+", line.strip()) if token.strip()]
    for token in reversed(tokens):
      clean = token.rstrip("/")
      basename = clean.rsplit("/", 1)[-1]
      if canonical_mag(basename) == mag:
        return basename
  return mag


def sync_mag_annotation(
  mag_id: object,
  workspace_base: str = DEFAULT_WORKSPACE_BASE,
  local_annotation_dir: str | Path = "Annotation",
  overwrite: bool = False,
  timeout: int = 3600,
) -> BvbrcSyncResult:
  mag = canonical_mag(mag_id)
  root = _safe_local_root(local_annotation_dir)
  local_status = local_annotation_status(mag, root)
  if local_status["ready_for_app"] and not overwrite:
    return BvbrcSyncResult(
      mag=mag,
      ok=True,
      status="already_local_no_download",
      local_path=local_status["local_path"],
      remote_path=str(workspace_base),
    )

  p3_cp = shutil.which("p3-cp")
  if not p3_cp:
    return BvbrcSyncResult(
      mag=mag,
      ok=False,
      status="cli_not_installed",
      stderr="p3-cp was not found in PATH.",
      local_path=local_status["local_path"],
      remote_path=str(workspace_base),
    )

  listing = list_remote_path(workspace_base, timeout=min(timeout, 240))
  if not listing.ok:
    return BvbrcSyncResult(
      mag=mag,
      ok=False,
      status=listing.status,
      command=listing.command,
      stdout=listing.stdout,
      stderr=listing.stderr,
      local_path=local_status["local_path"],
      remote_path=str(workspace_base),
    )

  remote_entry = _remote_entry_for_mag(listing.stdout, mag)
  remote_path = f"{str(workspace_base).rstrip('/')}/{remote_entry}".replace("//", "/")
  target = root / mag
  root.mkdir(parents=True, exist_ok=True)
  if overwrite and target.exists():
    shutil.rmtree(target)
  target.mkdir(parents=True, exist_ok=True)

  source = f"ws:{remote_path.rstrip('/')}/"
  command = [p3_cp, "-r"]
  if overwrite:
    command.append("-f")
  command.extend([source, str(target)])

  try:
    process = _run(command, timeout=timeout)
  except subprocess.TimeoutExpired as exc:
    return BvbrcSyncResult(
      mag=mag,
      ok=False,
      status="download_timeout",
      command=" ".join(command),
      stdout=str(exc.stdout or ""),
      stderr=str(exc.stderr or ""),
      local_path=str(target),
      remote_path=remote_path,
    )
  except Exception as exc:
    return BvbrcSyncResult(
      mag=mag,
      ok=False,
      status="download_error",
      command=" ".join(command),
      stderr=str(exc),
      local_path=str(target),
      remote_path=remote_path,
    )

  refreshed = local_annotation_status(mag, root)
  ok = process.returncode == 0 and refreshed["ready_for_app"]
  return BvbrcSyncResult(
    mag=mag,
    ok=ok,
    status="downloaded" if ok else "download_failed_or_empty",
    command=" ".join(command),
    stdout=process.stdout or "",
    stderr=process.stderr or "",
    local_path=str(target),
    remote_path=remote_path,
  )
