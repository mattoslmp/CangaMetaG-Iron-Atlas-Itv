from __future__ import annotations

from pathlib import Path
import runpy

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_runtime_name_guard_transform.py"


def test_runtime_guard_restores_marker_table_before_page_header_call() -> None:
  synthetic = '''from __future__ import annotations

DEFAULT_ARTICLE_TITLE = "English title"
DEFAULT_ARTICLE_TITLE_EN = "English title"
DEFAULT_ARTICLE_TITLE_PT = "Título em português"
DEFAULT_ARTICLE_ABSTRACT = "English abstract"
DEFAULT_ARTICLE_ABSTRACT_EN = "English abstract"
DEFAULT_ARTICLE_ABSTRACT_PT = "Resumo em português"
IS_PT = True


def _localized_article_text(key, english_default, portuguese_default):
  return portuguese_default if IS_PT else english_default


def page_header():
  return title, abstract, catalogue

resolved_title, resolved_abstract, resolved_catalogue = page_header()
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

  assert namespace["resolved_title"] == "Título em português"
  assert namespace["resolved_abstract"] == "Resumo em português"
  assert isinstance(namespace["resolved_catalogue"], pd.DataFrame)
  assert callable(namespace["marker_table"])
  assert "_canonical_marker_table_runtime" in transformed
  assert "catalogue = _canonical_marker_table_runtime()" in transformed


def test_page_header_runtime_variables_are_initialized_before_use() -> None:
  transform_text = TRANSFORM.read_text(encoding="utf-8")
  title_position = transform_text.index("title = _localized_title_loader")
  abstract_position = transform_text.index("abstract = _localized_abstract_loader")
  catalogue_position = transform_text.index(
    "catalogue = _canonical_marker_table_runtime()"
  )
  body_end = transform_text.index(
    "source = source.replace(\n    \"_APP_ORIGINAL_ST8_HEATMAP_FIGURE"
  )
  assert title_position < body_end
  assert abstract_position < body_end
  assert catalogue_position < body_end


def test_marker_table_exists_in_canonical_data_module() -> None:
  from src.supplementary_database import marker_table

  catalogue = marker_table()
  assert callable(marker_table)
  assert isinstance(catalogue, pd.DataFrame)
  assert {"KO", "Study"}.issubset(catalogue.columns)


def test_runtime_guard_is_last_app_transform() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  guard = app.index("app_runtime_name_guard_transform.py")
  renderer = app.index("app_static_figure_renderer_recovery_transform.py")
  assert renderer < guard
