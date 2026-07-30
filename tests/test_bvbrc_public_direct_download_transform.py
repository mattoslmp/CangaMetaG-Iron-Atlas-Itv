from __future__ import annotations

from pathlib import Path
import runpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = PROJECT_ROOT / "src" / "app_bvbrc_public_direct_download_transform.py"

BASE_SOURCE = '''def repository_mag_download_panel(
  selected_mag: str,
  folder,
  public_link=None,
  fasta=None,
  gbk=None,
):
  return "local"


def bvbrc_cli_sync_panel(mag_options: list[str]):
  return "legacy"


def mags_tab():
  return None
'''


def apply_transform(source: str) -> str:
  namespace = runpy.run_path(str(TRANSFORM), init_globals={"source": source})
  return str(namespace["source"])


def test_transform_adds_public_workspace_downloads() -> None:
  generated = apply_transform(BASE_SOURCE)

  assert "def _repository_mag_download_panel_local_fallback(" in generated
  assert "def _bvbrc_public_workspace_inventory(" in generated
  assert '"get_archive_url"' in generated
  assert '"get_download_url"' in generated
  assert "def repository_mag_download_panel(" in generated
  assert 'headers["Authorization"]' not in generated
  assert "headers['Authorization']" not in generated


def test_transform_is_idempotent() -> None:
  once = apply_transform(BASE_SOURCE)
  twice = apply_transform(once)
  assert twice == once


def test_public_rpc_has_no_authorization_header() -> None:
  generated = apply_transform(BASE_SOURCE)
  direct_start = generated.index("def _bvbrc_public_rpc")
  direct_end = generated.index("def mags_tab():", direct_start)
  direct_layer = generated[direct_start:direct_end]

  assert "without an auth token" in direct_layer
  assert "Deliberately do not send Authorization" in direct_layer
  assert '"Content-Type": "application/json"' in direct_layer
