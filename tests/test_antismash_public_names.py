from __future__ import annotations

from io import BytesIO
from pathlib import Path
import zipfile

from src.antismash_viewer import (
  antismash_run_zip_bytes,
  clean_antismash_name,
)


def test_clean_name_does_not_rename_source_file(tmp_path: Path) -> None:
  source = tmp_path / "MAG12.repaired.region001.gbk"
  payload = b"LOCUS       MAG12\nORIGIN\n//\n"
  source.write_bytes(payload)

  public_name = clean_antismash_name(source.name)

  assert public_name == "MAG12.region001.gbk"
  assert source.exists()
  assert source.name == "MAG12.repaired.region001.gbk"
  assert source.read_bytes() == payload


def test_clean_name_is_case_insensitive() -> None:
  assert clean_antismash_name("MAG7.REPAIRED.gbk") == "MAG7.gbk"
  assert clean_antismash_name("bin-8.RePaIrEd") == "bin-8"


def test_complete_run_zip_preserves_internal_names_and_bytes(tmp_path: Path) -> None:
  run_dir = tmp_path / "MAG12.repaired"
  run_dir.mkdir()
  index_payload = b"<html><body>antiSMASH</body></html>"
  gbk_payload = b"LOCUS       MAG12\nORIGIN\n//\n"
  (run_dir / "index.html").write_bytes(index_payload)
  (run_dir / "MAG12.repaired.region001.gbk").write_bytes(gbk_payload)

  archive = antismash_run_zip_bytes(run_dir)

  with zipfile.ZipFile(BytesIO(archive)) as handle:
    members = set(handle.namelist())
    index_member = "MAG12.repaired/index.html"
    gbk_member = "MAG12.repaired/MAG12.repaired.region001.gbk"
    assert index_member in members
    assert gbk_member in members
    assert handle.read(index_member) == index_payload
    assert handle.read(gbk_member) == gbk_payload
