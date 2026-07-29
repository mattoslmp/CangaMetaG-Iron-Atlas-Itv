from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import pandas as pd

from ._helpers import canonical_mag

DEFAULT_WORKSPACE_BASE = '/Leandro/CangaMetaG'


def bvbrc_cli_status() -> dict:
  executable = shutil.which('p3-ls')
  return {'installed': bool(executable), 'p3_ls': executable or '', 'authenticated': bool(executable)}


def install_commands_ubuntu() -> str:
  return 'curl -O https://raw.githubusercontent.com/BV-BRC/BV-BRC-CLI/master/cli-install.sh\nbash cli-install.sh'


def inventory_local_annotations(local_annotation_dir='Annotation') -> pd.DataFrame:
  root = Path(local_annotation_dir).expanduser()
  if not root.is_absolute():
    root = Path.cwd() / root
  rows = []
  if root.exists():
    for folder in sorted([p for p in root.iterdir() if p.is_dir()]):
      rows.append({'MAG': canonical_mag(folder.name), 'folder': str(folder), 'files': sum(1 for p in folder.rglob('*') if p.is_file()), 'exists': True})
  return pd.DataFrame(rows)


def local_annotation_status(mag_id, local_annotation_dir='Annotation') -> dict:
  root = Path(local_annotation_dir).expanduser()
  if not root.is_absolute():
    root = Path.cwd() / root
  cid = canonical_mag(mag_id)
  candidates = [root / cid] + [p for p in root.glob('*') if canonical_mag(p.name) == cid]
  folder = next((p for p in candidates if p.exists()), root / cid)
  return {'MAG': cid, 'folder': str(folder), 'exists': folder.exists(), 'files': sum(1 for p in folder.rglob('*') if p.is_file()) if folder.exists() else 0}


def list_remote_path(workspace_base=DEFAULT_WORKSPACE_BASE, timeout=180) -> pd.DataFrame:
  exe = shutil.which('p3-ls')
  if not exe:
    return pd.DataFrame([{'remote_path': workspace_base, 'status': 'BV-BRC CLI not installed'}])
  try:
    proc = subprocess.run([exe, workspace_base], text=True, capture_output=True, timeout=timeout, check=True)
    return pd.DataFrame({'remote_entry': [line for line in proc.stdout.splitlines() if line.strip()]})
  except Exception as exc:
    return pd.DataFrame([{'remote_path': workspace_base, 'status': 'error', 'message': str(exc)}])


def sync_mag_annotation(mag_id, workspace_base=DEFAULT_WORKSPACE_BASE, local_annotation_dir='Annotation', overwrite=False, timeout=3600) -> dict:
  return {
    'MAG': canonical_mag(mag_id), 'workspace_base': workspace_base,
    'local_annotation_dir': str(local_annotation_dir), 'overwrite': bool(overwrite),
    'status': 'manual_sync_required',
    'message': 'Use the BV-BRC CLI in an authenticated shell to download workspace annotations.',
  }
