from __future__ import annotations

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_runtime_name_guard_transform.py"


def test_runtime_guard_restores_marker_table_before_page_header_call() -> None:
  synthetic = '''from __future__ import annotations


def page_header():
  return marker_table

resolved_marker_table = page_header()
'''
  transformed = runpy.run_path(
    str(TRANSFORM),
    init_globals={"source": synthetic},
  )["source"]
  compiled = compile(
    transformed,
    "synthetic_marker_table_runtime_guard.py",
    "exec",
  )
  namespace: dict[str, object] = {}
  exec(compiled, namespace, namespace)

  assert callable(namespace["resolved_marker_table"])
  assert namespace["marker_table"] is namespace["resolved_marker_table"]
  assert "_canonical_marker_table_runtime" in transformed


def test_marker_table_exists_in_canonical_data_module() -> None:
  from src.supplementary_database import marker_table

  assert callable(marker_table)


def test_runtime_guard_is_last_app_transform() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  guard = app.index("app_runtime_name_guard_transform.py")
  renderer = app.index("app_static_figure_renderer_recovery_transform.py")
  assert renderer < guard
