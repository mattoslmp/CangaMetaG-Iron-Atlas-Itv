from __future__ import annotations

import ast
from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]


def generated_source_through_public_release() -> str:
  source = (ROOT / "app_core.py").read_text(encoding="utf-8")
  for transform in [
    "app_base_transform.py",
    "app_summary_transform.py",
    "app_map_transform.py",
    "app_bvbrc_transform.py",
    "app_kegg_mtx_transform.py",
    "app_ko_mtx_transform.py",
    "app_public_ui_transform.py",
    "app_public_runtime_defaults_transform.py",
    "app_environment_details_transform.py",
    "app_environment_reference_fix_transform.py",
    "app_remove_static_overview_map_transform.py",
    "app_scientific_contact_recipient_transform.py",
    "app_bvbrc_cli_runtime_transform.py",
    "app_antismash_clean_names_transform.py",
    "app_repository_mag_download_transform.py",
    "app_bvbrc_public_direct_download_transform.py",
    "app_visitor_world_map_transform.py",
    "app_scientific_module_clarity_transform.py",
    "app_kegg_interactive_explanation_transform.py",
    "app_public_release_v1_transform.py",
    "app_release_date_localization_transform.py",
    "app_visit_footer_position_fix_transform.py",
    "app_traceability_heatmap_repair_transform.py",
    "app_taxonomy_article_alignment_transform.py",
    "app_kegg_s67_axis_readability_transform.py",
  ]:
    source = runpy.run_path(
      str(ROOT / "src" / transform),
      init_globals={"source": source},
    )["source"]
  return source


def test_scientific_contact_constant_survives_public_release_transform() -> None:
  source = generated_source_through_public_release()
  tree = ast.parse(source)
  assignments = {
    target.id
    for node in tree.body
    if isinstance(node, ast.Assign)
    for target in node.targets
    if isinstance(target, ast.Name)
  }
  assert "SCIENTIFIC_COLLABORATION_RECIPIENT" in assignments
  assert source.index("SCIENTIFIC_COLLABORATION_RECIPIENT =") < source.index(
    "def contact_recipients_from_settings"
  )


def test_contact_function_returns_the_fixed_recipient_without_name_error() -> None:
  source = generated_source_through_public_release()
  tree = ast.parse(source)
  wanted = [
    node for node in tree.body
    if (
      isinstance(node, ast.Assign)
      and any(
        isinstance(target, ast.Name)
        and target.id == "SCIENTIFIC_COLLABORATION_RECIPIENT"
        for target in node.targets
      )
    )
    or (
      isinstance(node, ast.FunctionDef)
      and node.name == "contact_recipients_from_settings"
    )
  ]
  namespace: dict[str, object] = {}
  exec(compile(ast.Module(body=wanted, type_ignores=[]), "<contact-test>", "exec"), namespace)
  assert namespace["contact_recipients_from_settings"]() == ["gilopesnunes@gmail.com"]
