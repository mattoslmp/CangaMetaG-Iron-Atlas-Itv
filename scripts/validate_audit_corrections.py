#!/usr/bin/env python3
"""Validate every correction requested by the independent visual/scientific audit."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
from scipy.spatial.distance import pdist, squareform

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.integrated_omics import nmds_bray_curtis, pcoa_bray_curtis
from src.kegg_modules import kegg_sample_metadata, canonical_mag_id
from src.publication_ordination import (
  _new_nonmetric_mds,
  _orient_axes,
  betadisper_test,
  permanova,
  beta_transform_matrix,
  pcoa_bray_curtis_matrix,
  nmds_bray_curtis_matrix,
)
from src.publication_rda import (
  publication_nmds_data,
  publication_nmds_figure,
  publication_rda_data,
  publication_rda_figure,
)
from src.visual_qc import repel_label_positions, sparsify_heatmap_y_ticks

APP_PATH = ROOT / "app.py"
APP_TEXT = APP_PATH.read_text(encoding="utf-8")
TREE = ast.parse(APP_TEXT)
VALIDATION = ROOT / "validation"


def extract_functions(names: set[str], namespace: dict) -> dict:
  nodes = [node for node in TREE.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in names]
  found = {node.name for node in nodes}
  missing = names - found
  if missing:
    raise RuntimeError(f"Missing app functions for validation: {sorted(missing)}")
  module = ast.Module(body=nodes, type_ignores=[])
  ast.fix_missing_locations(module)
  exec(compile(module, str(APP_PATH), "exec"), namespace, namespace)
  return namespace


def record(rows: list[dict], audit_ids: str, area: str, condition: bool, evidence: str) -> None:
  rows.append({
    "audit_ids": audit_ids,
    "area": area,
    "status": "PASS" if condition else "FAIL",
    "evidence": evidence,
  })


def main() -> int:
  rows: list[dict] = []

  # 1–3: all labels retained globally and in the real 448-module builder.
  import plotly.graph_objects as go
  labels = [f"M{i:05d} | pathway {i}" for i in range(448)]
  unmarked = go.Figure(go.Heatmap(z=np.zeros((448, 4)), x=["A", "B", "C", "D"], y=labels))
  sparsify_heatmap_y_ticks(unmarked, max_visible_ticks=90)
  unmarked_ticks = list(unmarked.layout.yaxis.ticktext or [])

  kegg_ns = {
    "pd": pd, "np": np, "go": go,
    "kegg_sample_metadata": kegg_sample_metadata,
    "canonical_mag_id": canonical_mag_id,
  }
  extract_functions({"kegg_numeric_heatmap_figure", "_figure_export_size"}, kegg_ns)
  kegg_matrix = pd.read_csv(
    ROOT / "data/final_kegg_st8_update/KEMET_lagoon_all_metagenomes_module_completeness_SCORE_3state.csv",
    index_col=0,
  )
  maximum = float(kegg_matrix.max().max())
  if maximum > 1:
    kegg_matrix = kegg_matrix / maximum
  kegg_fig, kegg_export = kegg_ns["kegg_numeric_heatmap_figure"](
    kegg_matrix, "Metagenomes", "Complete KEGG matrix", "Completeness", False,
  )
  sparsify_heatmap_y_ticks(kegg_fig, max_visible_ticks=90)
  kegg_ticks = list(kegg_fig.layout.yaxis.ticktext or [])
  kegg_meta = dict(kegg_fig.layout.meta or {})
  export_width, export_height = kegg_ns["_figure_export_size"](kegg_fig)
  record(
    rows, "1-3", "Heatmap labels",
    len(unmarked_ticks) == 448 and unmarked_ticks == labels and
    len(kegg_ticks) == 448 and kegg_ticks == kegg_matrix.index.astype(str).tolist() and len(kegg_export) == 448 and
    bool(kegg_meta.get("preserve_cell_geometry")) and bool(kegg_meta.get("force_all_y_ticks")) and
    int(kegg_fig.layout.height) >= 448 * 20 and export_height >= int(kegg_fig.layout.height) and
    {"canonical_id", "axis_label", "lake_sample", "IMG_JGI_ID"}.issubset(kegg_sample_metadata("Metagenomes", kegg_matrix.columns).columns),
    f"generic ticks={len(unmarked_ticks)}; real KEGG ticks={len(kegg_ticks)}; rows={len(kegg_export)}; display height={kegg_fig.layout.height}; export={export_width}x{export_height}",
  )

  # 4–11: exact article RDA/NMDS data and rendering for both domains.
  for domain in ("Bacteria", "Archaea"):
    rda = publication_rda_data(ROOT, domain)
    nmds = publication_nmds_data(ROOT, domain)
    rfig, *_ = publication_rda_figure(ROOT, domain, show_taxa=True)
    nfig, *_ = publication_nmds_figure(ROOT, domain)
    xrange = list(map(float, rfig.layout.xaxis.range))
    yrange = list(map(float, rfig.layout.yaxis.range))
    vector_shapes = []
    for shape in list(rfig.layout.shapes or []):
      try:
        if shape.type == "line" and shape.xref in (None, "x") and shape.yref in (None, "y") and float(shape.x0) == 0 and float(shape.y0) == 0:
          vector_shapes.append(shape)
      except Exception:
        pass
    inside = all(
      min(xrange) <= float(shape.x1) <= max(xrange) and min(yrange) <= float(shape.y1) <= max(yrange)
      for shape in vector_shapes
    )
    stats_row = rda["model_statistics"].iloc[0]
    record(rows, "4-9", f"RDA {domain}",
           len(rda["sites"]) == 10 and len(rda["environment_vectors"]) == 6 and len(rda["taxon_vectors"]) == 6 and len(vector_shapes) >= 12 and inside and
           all(token in rfig.layout.title.text for token in ("R²", "adjusted R²", "pseudo-F", "P =")) and
           "axis P" in rfig.layout.xaxis.title.text and "axis P" in rfig.layout.yaxis.title.text and
           not rda["vif"].empty,
           f"sites={len(rda['sites'])}; env={len(rda['environment_vectors'])}; genera={len(rda['taxon_vectors'])}; vectors={len(vector_shapes)}; global P={stats_row.global_permutation_p}")
    raw_nmds = nmds["raw_result"]
    record(rows, "10-12", f"NMDS {domain}",
           len(nmds["scores"]) == 20 and int(raw_nmds["parameters"].get("n_init", -1)) == 20 and int(raw_nmds["parameters"].get("max_iter", -1)) == 1000 and int(raw_nmds["parameters"].get("seed", -1)) == 42 and "Stress-1" in nfig.layout.title.text,
           f"samples={len(nmds['scores'])}; stress={raw_nmds['stress']:.6f}; parameters={raw_nmds['parameters']}")

  canonical_script = ROOT / "scripts/figures/generate_ordinations_revision4.py"
  shared_import_article = "from src.publication_ordination import" in canonical_script.read_text(encoding="utf-8")
  shared_import_app = "from .publication_ordination import compute_nmds, compute_rda, domain_genus_matrix" in (ROOT / "src/publication_rda.py").read_text(encoding="utf-8")
  shared_import_exploratory = all(token in APP_TEXT for token in ("canonical_pcoa_bray_curtis_matrix", "canonical_nmds_bray_curtis_matrix"))
  integrated_text = (ROOT / "src/integrated_omics.py").read_text(encoding="utf-8")
  shared_import_integrated = "pcoa_bray_curtis_matrix, nmds_bray_curtis_matrix" in integrated_text
  manifest_ok = True
  manifest_evidence = []
  for manifest_path in (
    ROOT / "data/final_figure_script_manifest.csv",
    ROOT / "Final_Figures_and_Scripts/final_figure_script_manifest.csv",
    ROOT / "data/figure_script_manifest.csv",
  ):
    manifest = pd.read_csv(manifest_path)
    target = manifest[manifest["Figure"].astype(str).isin(["Figure 4", "Figure 5", "Supplementary Figure 17"])]
    ok = len(target) == 3 and target["Script"].eq("scripts/figures/generate_ordinations_revision4.py").all()
    manifest_ok = manifest_ok and ok
    manifest_evidence.append(f"{manifest_path.name}:{ok}")
  legacy_text = (ROOT / "scripts/generate_final_domain_taxonomy_figures.py").read_text(encoding="utf-8")
  legacy_is_wrapper = "canonical_compute_nmds" in legacy_text and "canonical_compute_rda" in legacy_text
  record(
    rows, "4-12", "Single shared article/app ordination implementation",
    shared_import_article and shared_import_app and shared_import_exploratory and shared_import_integrated and manifest_ok and legacy_is_wrapper,
    "canonical article manifest, interactive RDA/NMDS, exploratory and integrated ordinations all delegate to src.publication_ordination; " + "; ".join(manifest_evidence),
  )

  # 13: standard Gower-centred PERMANOVA and dispersion diagnostics.
  distance = squareform(pdist(np.array([[0, 0], [0, 1], [4, 4], [4, 5]], dtype=float), metric="euclidean"))
  groups = np.array(["A", "A", "B", "B"])
  pm = permanova(distance, groups, permutations=99, seed=42)
  bd = betadisper_test(distance, groups, permutations=99, seed=42)

  def independent_permanova_f(dmat, labels):
    labels = np.asarray(labels)
    n = len(labels)
    levels = pd.unique(labels)
    total = sum(float(dmat[i, j] ** 2) for i in range(n) for j in range(i + 1, n)) / n
    within = 0.0
    for level in levels:
      idx = np.where(labels == level)[0]
      within += sum(float(dmat[i, j] ** 2) for pos, i in enumerate(idx) for j in idx[pos + 1:]) / len(idx)
    between = total - within
    return (between / (len(levels) - 1)) / (within / (n - len(levels)))

  reference_f = independent_permanova_f(distance, groups)
  record(rows, "13", "PERMANOVA / dispersion",
         np.isclose(pm["pseudo_F"], reference_f, rtol=1e-10, atol=1e-12) and
         0 <= pm["p_value"] <= 1 and np.isfinite(bd["F"]) and 0 <= bd["p_value"] <= 1,
         f"Gower pseudo-F={pm['pseudo_F']:.12f}; independent distance-partition pseudo-F={reference_f:.12f}; P={pm['p_value']:.4f}; dispersion F={bd['F']:.6f}; dispersion P={bd['p_value']:.4f}")

  # 14: PCoA diagnostics and Lingoes handling in both exploratory implementations.
  toy = pd.DataFrame(
    [[5, 0, 1, 0], [0, 4, 0, 1], [3, 1, 0, 2], [0, 1, 5, 1], [4, 0, 2, 1]],
    index=[f"G{i}" for i in range(5)], columns=[f"F{i}" for i in range(4)],
  )
  ns = {
    "pd": pd, "np": np,
    "canonical_beta_transform_matrix": beta_transform_matrix,
    "canonical_pcoa_bray_curtis_matrix": pcoa_bray_curtis_matrix,
    "canonical_nmds_bray_curtis_matrix": nmds_bray_curtis_matrix,
  }
  extract_functions({"_canonical_beta_transform", "pcoa_from_matrix", "nmds_from_matrix"}, ns)
  app_pcoa = ns["pcoa_from_matrix"](toy)
  app_nmds = ns["nmds_from_matrix"](toy)
  integrated_input = toy.reset_index().rename(columns={"index": "group"})
  int_pcoa, int_var = pcoa_bray_curtis(integrated_input, "group")
  int_nmds = nmds_bray_curtis(integrated_input, "group")
  record(rows, "12,14", "Exploratory PCoA/NMDS alignment",
         {"PCoA1_explained_%", "PCoA2_explained_%", "negative_eigenvalue_count_before_correction", "distance_correction"}.issubset(app_pcoa.columns) and
         int_var["axis"].tolist() == ["PCoA1", "PCoA2"] and
         int(app_nmds["n_init"].iloc[0]) == 20 and int(app_nmds["max_iter"].iloc[0]) == 1000 and int_nmds["n_init"].iloc[0] == 20,
         f"app correction={app_pcoa['distance_correction'].iloc[0]}; integrated correction={int_var['correction'].iloc[0]}; NMDS starts=20")

  # 15: labels added without changing vector endpoints.
  vector_df = pd.DataFrame({"endpoint_x": [0.1, 0.11, 0.12], "endpoint_y": [0.1, 0.11, 0.12]})
  repelled = repel_label_positions(vector_df, "endpoint_x", "endpoint_y", min_distance=0.2, radial_offset=0.24)
  record(rows, "15", "Biplot labels",
         {"label_x", "label_y"}.issubset(repelled.columns) and np.allclose(repelled["endpoint_x"], vector_df["endpoint_x"]) and np.allclose(repelled["endpoint_y"], vector_df["endpoint_y"]),
         "label_x/label_y present and endpoint coordinates unchanged")

  # 16–17: one independent observation per sample × category.
  box_ns = {"pd": pd, "np": np, "re": re}
  extract_functions({"_article_lake_sample_columns", "_lake_code_from_sample", "_season_from_sample", "_long_marker_counts_for_boxplot"}, box_ns)
  box_source = pd.DataFrame({
    "KO": ["K1", "K2", "K3"], "Pathway": ["P1", "P1", "P2"],
    "AM.P1.D": [10, 20, 5], "AM.P1.R": [4, 6, 10], "TI.P1.D": [3, 7, 2], "TI.P1.R": [8, 2, 4],
  })
  box_long = box_ns["_long_marker_counts_for_boxplot"](box_source, ["KO", "Pathway"], "Pathway", True)
  p1_am_d = box_long[(box_long.Pathway == "P1") & (box_long["sample"] == "AM.P1.D")]
  record(rows, "16-17", "Boxplot independent units",
         not box_long.duplicated(["Pathway", "sample"]).any() and len(p1_am_d) == 1 and int(p1_am_d["distinct_markers"].iloc[0]) == 2 and
         'points="all" if show_raw_points else False' in APP_TEXT[APP_TEXT.find("def publication_boxplot_panel"):APP_TEXT.find("def publication_boxplot_panel") + 3500] and
         'value=False' in APP_TEXT[APP_TEXT.find("def publication_boxplot_panel"):APP_TEXT.find("def publication_boxplot_panel") + 3500] and
         '190 * max(1, len(selected_categories))' in APP_TEXT,
         f"rows={len(box_long)}; unique sample×pathway={box_long[['Pathway','sample']].drop_duplicates().shape[0]}; P1/AM.P1.D markers={int(p1_am_d['distinct_markers'].iloc[0])}")

  # 18–20: no undefined variables in formatter, errors retained, no external Plotly script dependency.
  formatter_text = APP_TEXT[APP_TEXT.find("def prepare_plotly_for_publication_export"):APP_TEXT.find("def _barplot_method_summary")]
  record(rows, "18-20", "Plotly formatting/export/offline",
         "domain, rank, view_label" not in formatter_text and "LOGGER.exception" in formatter_text and "LAST_PLOTLY_EXPORT_ERRORS" in formatter_text and
         'include_plotlyjs="cdn"' not in APP_TEXT and "cdn.plot.ly" not in APP_TEXT and "PLOTLY_JS_INLINE" in APP_TEXT,
         "formatter has no undefined domain/rank/view_label; real errors logged; Plotly bundled inline")

  # 21: real browser report must already exist and pass.
  browser_report_path = VALIDATION / "VISUAL_BROWSER_REGRESSION_TEST.json"
  browser_report = json.loads(browser_report_path.read_text(encoding="utf-8")) if browser_report_path.exists() else {}
  record(rows, "21", "Real visual browser test", browser_report.get("overall_status") == "PASS" and len(browser_report.get("cases", [])) >= 6,
         f"browser status={browser_report.get('overall_status')}; cases={len(browser_report.get('cases', []))}")

  # 22–23: page-level display and corrected S37/S38 geometry.
  s37_pages = sorted((ROOT / "outputs/app_supplementary_figures").glob("SupplementaryFigure37*_P*.png"))
  s32_pages = sorted((ROOT / "outputs/app_supplementary_figures").glob("SupplementaryFigure32*_P*.png"))
  s33_pages = sorted((ROOT / "outputs/app_supplementary_figures").glob("SupplementaryFigure33*_P*.png"))
  s38 = next(iter((ROOT / "outputs/app_supplementary_figures").glob("SupplementaryFigure38*.png")), None)
  from PIL import Image
  s38_dims = Image.open(s38).size if s38 else (0, 0)
  s32_base = next(iter((ROOT / "outputs/app_supplementary_figures").glob("SupplementaryFigure32*_heatmap.png")), None)
  s33_base = next(iter((ROOT / "outputs/app_supplementary_figures").glob("SupplementaryFigure33*_heatmap.png")), None)
  s32_dims = Image.open(s32_base).size if s32_base else (0, 0)
  s33_dims = Image.open(s33_base).size if s33_base else (0, 0)
  record(rows, "22-23", "Long supplementary heatmaps",
         len(s32_pages) == 6 and len(s33_pages) == 6 and len(s37_pages) == 2 and
         s32_dims == (4800, 20880) and s33_dims == (4800, 20880) and s38_dims == (4950, 3180) and
         "SupplementaryFigure(?:32|33|37|38)" in APP_TEXT,
         f"S32 pages={len(s32_pages)}, composite={s32_dims}; S33 pages={len(s33_pages)}, composite={s33_dims}; S37 pages={len(s37_pages)}; S38={s38_dims}")

  # 24: canonical composition preserved plus a named-genus detail view.
  tax_panel = APP_TEXT[APP_TEXT.find("def taxonomic_rda_panel"):APP_TEXT.find("def _season_from_sample")]
  record(rows, "24", "Named-genus detail",
         "Unclassified" in tax_panel and "Other genera" in tax_panel and "renormal" in tax_panel.lower(),
         "complementary named-genus view excludes Unclassified/Other only in the detail panel and renormalizes")

  # 25: deterministic rarefaction and no inferential testing of pooled summaries.
  alpha_ns = {"pd": pd, "np": np, "hashlib": hashlib}
  extract_functions({"_rarefy_count_vector"}, alpha_ns)
  rare1 = alpha_ns["_rarefy_count_vector"](pd.Series([100, 50, 25, 5]), 100, "sample-A")
  rare2 = alpha_ns["_rarefy_count_vector"](pd.Series([100, 50, 25, 5]), 100, "sample-A")
  alpha_text = APP_TEXT[APP_TEXT.find("def _alpha_from_profile_final"):APP_TEXT.find("def _canonical_beta_transform")]
  record(rows, "25", "Alpha diversity rarefaction",
         int(rare1.sum()) == 100 and np.array_equal(rare1, rare2) and "descriptive mean ± SD" in alpha_text and "not treated as pseudoreplicates" in alpha_text,
         f"rarefied total={int(rare1.sum())}; deterministic={np.array_equal(rare1, rare2)}")

  frame = pd.DataFrame(rows)
  overall = "PASS" if frame["status"].eq("PASS").all() else "FAIL"
  VALIDATION.mkdir(parents=True, exist_ok=True)
  frame.to_csv(VALIDATION / "AUDIT_CORRECTIONS_VALIDATION.csv", index=False)
  report = {
    "validation": "Independent audit corrections",
    "executed_utc": datetime.now(timezone.utc).isoformat(),
    "overall_status": overall,
    "checks": rows,
  }
  (VALIDATION / "AUDIT_CORRECTIONS_VALIDATION.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
  md = [
    "# Audit corrections validation",
    "",
    f"Overall status: **{overall}**",
    "",
    "| Audit IDs | Area | Status | Evidence |",
    "|---|---|---:|---|",
  ]
  for row in rows:
    md.append(f"| {row['audit_ids']} | {row['area']} | {row['status']} | {row['evidence'].replace('|', '/')} |")
  (VALIDATION / "AUDIT_CORRECTIONS_VALIDATION.md").write_text("\n".join(md) + "\n", encoding="utf-8")
  print(frame.to_string(index=False))
  print("AUDIT_CORRECTIONS_VALIDATION_" + overall)
  return 0 if overall == "PASS" else 1


if __name__ == "__main__":
  raise SystemExit(main())
