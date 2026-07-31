from __future__ import annotations

import re
import runpy
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.py"
CORE = ROOT / "app_core.py"


def generated_source() -> str:
  app_text = APP.read_text(encoding="utf-8")
  transform_names = re.findall(r'with_name\("src"\) / "([^"]+\.py)"', app_text)
  assert transform_names
  source = CORE.read_text(encoding="utf-8")
  for transform_name in transform_names:
    namespace = runpy.run_path(
      str(ROOT / "src" / transform_name),
      init_globals={"source": source},
    )
    source = namespace["source"]
  return source


def function_block(source: str, start: str, end: str) -> str:
  start_index = source.index(start)
  end_index = source.index(end, start_index)
  return source[start_index:end_index]


def test_generated_public_source_compiles() -> None:
  source = generated_source()
  compile(source, str(CORE), "exec")
  assert "CANGAMETAG_PUBLIC_SCIENTIFIC_TRACEABILITY_ONLY_V2 = 1" in source


def test_scientific_traceability_contains_results_not_internal_metadata() -> None:
  source = generated_source()
  block = function_block(
    source,
    "def render_figure_audit_expander(",
    "def render_plotly_downloadable(",
  )
  for label in [
    "Scientific data used in this figure",
    "Scientific source table",
    "Processed table",
    "Result/statistics table",
    "Exact figure values",
  ]:
    assert label in block
  for public_internal_label in [
    "Final script",
    "Instructions",
    "Data policy",
    "figure-script manifest",
  ]:
    assert public_internal_label not in block


def test_regression_and_integrity_controls_are_not_public() -> None:
  source = generated_source()
  taxonomy = function_block(source, "def taxonomy_tab():", "def site_access_gate")
  assert "Validação figura–app" not in taxonomy
  assert "Figure–app validation" not in taxonomy
  assert "Validation passed for" not in taxonomy

  final_figures = function_block(
    source,
    "def final_publication_figures_tab()",
    "def contact_recipients_from_settings",
  )
  assert 'qa1.metric("Main figures"' not in final_figures
  assert "Integrity check passed" not in final_figures
  assert "Integrity check: missing scripts" not in final_figures


def test_other_internal_audit_panels_are_disabled() -> None:
  source = generated_source()
  assert "if False and (comparison_tsv.exists() or comparison_md.exists()):" in source
  assert 'show_table(recent, "visitor_recent_audit"' not in source
  assert 'csv_button(recent, "visitor_recent_audit_public_fields.csv"' not in source
  assert 'if False and st.session_state.get("admin_authenticated", False):' in source


def test_unrelated_prompt_rows_are_filtered_before_display() -> None:
  source = generated_source()
  filter_block = function_block(
    source,
    "def _public_scientific_result_table(",
    "def render_figure_audit_expander(",
  )
  assert 'r"parkinson"' in filter_block
  assert 'r"tell\\s+us\\s+about\\s+your\\s+connection"' in filter_block
  assert '"prompt"' in filter_block
  assert '"test_fixture"' in filter_block
