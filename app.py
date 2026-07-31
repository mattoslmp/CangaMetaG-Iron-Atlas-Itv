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
  Path(__file__).with_name("src") / "app_order_unclassified_transform.py",
  Path(__file__).with_name("src") / "app_taxonomy_na_literal_transform.py",
  Path(__file__).with_name("src") / "app_taxonomy_explorer_label_transform.py",
  Path(__file__).with_name("src") / "app_st8_biomarker_heatmap_transform.py",
  Path(__file__).with_name("src") / "app_st8_environment_label_transform.py",
  Path(__file__).with_name("src") / "app_final_script_manifest_transform.py",
  Path(__file__).with_name("src") / "app_visitor_geolocation_points_transform.py",
  Path(__file__).with_name("src") / "app_visitor_footer_final_transform.py",
  Path(__file__).with_name("src") / "app_figure45_bottom_legend_transform.py",
  Path(__file__).with_name("src") / "app_dataframe_attrs_melt_guard_transform.py",
  Path(__file__).with_name("src") / "app_final_inference_and_figure45_layout_v2_transform.py",
  Path(__file__).with_name("src") / "app_inference_summary_fix_transform.py",
  Path(__file__).with_name("src") / "app_official_ordination_statistics_transform.py",
  Path(__file__).with_name("src") / "app_official_ordination_method_text_transform.py",
  Path(__file__).with_name("src") / "app_rda_axis_statistics_text_transform.py",
  Path(__file__).with_name("src") / "app_public_validation_prose_cleanup_transform.py",
  Path(__file__).with_name("src") / "app_scientific_data_panel_v3_transform.py",
  Path(__file__).with_name("src") / "app_concise_scientific_method_text_transform.py",
  Path(__file__).with_name("src") / "app_other_taxa_percentage_label_transform.py",
  Path(__file__).with_name("src") / "app_full_figure_language_transform.py",
  Path(__file__).with_name("src") / "app_complete_plotly_language_transform.py",
  Path(__file__).with_name("src") / "app_static_figure_renderer_recovery_transform.py",
  Path(__file__).with_name("src") / "app_runtime_name_guard_transform.py",
]

source = CORE_PATH.read_text(encoding="utf-8")
for transform_path in TRANSFORMS:
  namespace = runpy.run_path(str(transform_path), init_globals={"source": source})
  source = namespace["source"]

code = compile(source, str(CORE_PATH), "exec")
exec(code, globals(), globals())
