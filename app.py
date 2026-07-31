from __future__ import annotations

from pathlib import Path
import runpy

CORE_PATH = Path(__file__).with_name("app_core.py")
TRANSFORMS = [
  Path(__file__).with_name("src") / "app_base_transform.py",
  Path(__file__).with_name("src") / "app_summary_transform.py",
  Path(__file__).with_name("src") / "app_map_transform.py",
  Path(__file__).with_name("src") / "app_bvbrc_transform.py",
  Path(__file__).with_name("src") / "app_kegg_mtx_transform.py",
  Path(__file__).with_name("src") / "app_ko_mtx_transform.py",
  Path(__file__).with_name("src") / "app_public_ui_transform.py",
  Path(__file__).with_name("src") / "app_public_runtime_defaults_transform.py",
  Path(__file__).with_name("src") / "app_environment_details_transform.py",
  Path(__file__).with_name("src") / "app_environment_reference_fix_transform.py",
  Path(__file__).with_name("src") / "app_remove_static_overview_map_transform.py",
  Path(__file__).with_name("src") / "app_scientific_contact_recipient_transform.py",
  Path(__file__).with_name("src") / "app_bvbrc_cli_runtime_transform.py",
  Path(__file__).with_name("src") / "app_antismash_clean_names_transform.py",
  Path(__file__).with_name("src") / "app_repository_mag_download_transform.py",
  Path(__file__).with_name("src") / "app_bvbrc_public_direct_download_transform.py",
  Path(__file__).with_name("src") / "app_visitor_world_map_transform.py",
  Path(__file__).with_name("src") / "app_scientific_module_clarity_transform.py",
  Path(__file__).with_name("src") / "app_kegg_interactive_explanation_transform.py",
  Path(__file__).with_name("src") / "app_public_release_v1_transform.py",
  Path(__file__).with_name("src") / "app_release_date_localization_transform.py",
  Path(__file__).with_name("src") / "app_visit_footer_position_fix_transform.py",
  Path(__file__).with_name("src") / "app_traceability_heatmap_repair_transform.py",
  Path(__file__).with_name("src") / "app_taxonomy_article_alignment_transform.py",
  Path(__file__).with_name("src") / "app_kegg_s67_axis_readability_transform.py",
  Path(__file__).with_name("src") / "app_public_scientific_traceability_only_transform.py",
  Path(__file__).with_name("src") / "app_corrected_taxonomy_static_assets_transform.py",
  Path(__file__).with_name("src") / "app_exact_figure2_3_alignment_transform.py",
  Path(__file__).with_name("src") / "app_exact_figure2_3_generated_source_transform.py",
  Path(__file__).with_name("src") / "app_taxonomy_na_literal_transform.py",
  Path(__file__).with_name("src") / "app_taxonomy_explorer_label_transform.py",
  Path(__file__).with_name("src") / "app_st8_biomarker_heatmap_transform.py",
  Path(__file__).with_name("src") / "app_visitor_footer_final_transform.py",
]

source = CORE_PATH.read_text(encoding="utf-8")
for transform_path in TRANSFORMS:
  namespace = runpy.run_path(str(transform_path), init_globals={"source": source})
  source = namespace["source"]

code = compile(source, str(CORE_PATH), "exec")
exec(code, globals(), globals())
