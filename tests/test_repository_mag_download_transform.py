from __future__ import annotations

from pathlib import Path
import runpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = PROJECT_ROOT / "src" / "app_repository_mag_download_transform.py"


def apply_transform(source: str) -> str:
  namespace = runpy.run_path(str(TRANSFORM), init_globals={"source": source})
  return str(namespace["source"])


def legacy_source() -> str:
  return '''from __future__ import annotations
from pathlib import Path
import zipfile


def bvbrc_cli_sync_panel(mag_options: list[str]):
  workspace_base = st.text_input(
    txt("Diretório remoto BV-BRC metagenomas", "Remote BV-BRC metagenomes directory")
  )
  st.markdown("Batch download MAG2–MAG50")
  st.info("Downloading with p3-cp")


def mags_tab():
  """MAG page."""
  if selected_mag:
    folder = annotation_folder(selected_mag)
    selected_local_status = bvbrc_local_annotation_status(selected_mag, st.session_state.get("bvbrc_local_annotation_dir", "Annotation"))
    if bool(selected_local_status.get("ready_for_app")):
      pass
    elif is_admin_authenticated() and not folder and bool(st.session_state.get("bvbrc_auto_sync_selected", False)):
      auto_result = bvbrc_sync_mag_annotation(selected_mag)
    public_link = public_link_for_mag(selected_mag)
    fasta = fasta_path_for_mag(selected_mag, folder)
    gbk = genbank_path_for_mag(selected_mag, folder)
    d1, d2, d3 = st.columns(3)
    with d1:
      st.write("legacy FASTA")
    with d2:
      st.write("legacy GBK")
    with d3:
      st.write("legacy folder")

  st.divider()
  st.write("classification section")
'''


def test_transform_removes_server_side_sync_controls() -> None:
  transformed = apply_transform(legacy_source())

  assert "def repository_mag_download_panel(" in transformed
  assert "Remote BV-BRC metagenomes directory" not in transformed
  assert "Batch download MAG2–MAG50" not in transformed
  assert "Downloading with p3-cp" not in transformed
  assert "bvbrc_sync_mag_annotation(selected_mag)" not in transformed
  assert "repository_mag_download_panel(" in transformed
  assert 'st.write("classification section")' in transformed
  compile(transformed, "synthetic_app_core.py", "exec")


def test_transform_is_idempotent() -> None:
  once = apply_transform(legacy_source())
  twice = apply_transform(once)
  assert twice == once


def test_transform_does_not_change_unrelated_source() -> None:
  source = "from __future__ import annotations\nprint('unrelated page')\n"
  assert apply_transform(source) == source
