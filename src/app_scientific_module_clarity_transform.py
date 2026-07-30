from __future__ import annotations

from pathlib import Path


REVISION_PATH = Path(__file__).with_name("app_scientific_module_clarity_v2_transform.py")
revision_code = compile(
  REVISION_PATH.read_text(encoding="utf-8"),
  str(REVISION_PATH),
  "exec",
)
exec(revision_code, globals(), globals())
