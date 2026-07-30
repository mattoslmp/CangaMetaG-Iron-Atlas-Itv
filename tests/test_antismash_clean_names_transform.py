from __future__ import annotations

from pathlib import Path
import runpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = PROJECT_ROOT / "src" / "app_antismash_clean_names_transform.py"

OLD_GBK = (
  'file_name=gbk_path.name, mime="text/plain", '
  'key=f"download_antismash_gbk_{selected_run_label}"'
)
NEW_GBK = (
  'file_name=str(run.get("gbk_download_name") or gbk_path.name), '
  'mime="text/plain", key=f"download_antismash_gbk_{selected_run_label}"'
)


def apply_transform(source: str) -> str:
  namespace = runpy.run_path(str(TRANSFORM), init_globals={"source": source})
  return str(namespace["source"])


def test_transform_updates_old_download_name() -> None:
  assert apply_transform(OLD_GBK) == NEW_GBK


def test_transform_is_idempotent_when_already_updated() -> None:
  assert apply_transform(NEW_GBK) == NEW_GBK


def test_transform_does_not_fail_on_unrelated_source() -> None:
  source = "print('antiSMASH data remain unchanged')\n"
  assert apply_transform(source) == source
