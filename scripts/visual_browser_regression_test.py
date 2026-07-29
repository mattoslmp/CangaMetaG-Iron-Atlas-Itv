#!/usr/bin/env python3
"""Real Chromium regression test for the audited interactive scientific figures.

This test renders the exact Plotly RDA/NMDS figures plus 172-row and 448-row
full-label heatmaps with Plotly bundled inline.  It blocks HTTP(S), verifies the browser DOM,
checks vector endpoints and titles, and stores screenshots plus a JSON report.
It complements (but does not replace) the offline Streamlit navigation shim.
"""
from __future__ import annotations

import ast
import json
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.publication_rda import publication_nmds_figure, publication_rda_figure
from src.kegg_modules import kegg_sample_metadata, canonical_mag_id
from src.visual_qc import sparsify_heatmap_y_ticks

VALIDATION = ROOT / "validation"
ARTIFACTS = VALIDATION / "visual_browser_artifacts"
EXPECTED_GENERA = {
  "Bacteria": {
    "Anaeromyxobacter", "Mycobacterium", "Bradyrhizobium", "Geobacter",
    "Candidatus Sulfotelmatobacter", "Desulfobacca",
  },
  "Archaea": {
    "Methanoregula", "Methanoculleus", "Methanothrix", "Methanofollis",
    "Methanolinea", "Candidatus Methanoperedens",
  },
}


def full_label_heatmap(row_count: int, explicitly_marked: bool) -> go.Figure:
  labels = [f"K{i:05d} | complete pathway label {i:03d}" for i in range(1, row_count + 1)]
  samples = [f"S{i:02d}" for i in range(1, 13)]
  values = np.fromfunction(lambda i, j: ((i * 7 + j * 3) % 17) / 16.0, (len(labels), len(samples)))
  fig = go.Figure(go.Heatmap(z=values, x=samples, y=labels, colorscale="Viridis"))
  layout = {
    "title": f"Full-label heatmap browser regression ({row_count} rows)",
    "height": 900,
    "margin": {"l": 390, "r": 80, "t": 90, "b": 140},
  }
  if explicitly_marked:
    layout["meta"] = {
      "force_all_y_ticks": True,
      "all_y_labels_visible": True,
      "cell_height_px": 22,
      "y_tick_font_size": 10,
    }
  fig.update_layout(**layout)
  return sparsify_heatmap_y_ticks(fig, max_visible_ticks=90)



def actual_kegg_heatmap(dataset_type: str, filename: str) -> go.Figure:
  """Build the exact app KEGG figure from a packaged 448-row matrix."""
  app_path = ROOT / "app.py"
  tree = ast.parse(app_path.read_text(encoding="utf-8"))
  node = next(
    item for item in tree.body
    if isinstance(item, ast.FunctionDef) and item.name == "kegg_numeric_heatmap_figure"
  )
  module = ast.Module(body=[node], type_ignores=[])
  ast.fix_missing_locations(module)
  namespace = {
    "pd": pd,
    "np": np,
    "go": go,
    "kegg_sample_metadata": kegg_sample_metadata,
    "canonical_mag_id": canonical_mag_id,
  }
  exec(compile(module, str(app_path), "exec"), namespace, namespace)
  matrix = pd.read_csv(ROOT / "data/final_kegg_st8_update" / filename, index_col=0)
  maximum = float(matrix.max().max())
  if maximum > 1:
    matrix = matrix / maximum
  fig, exported = namespace["kegg_numeric_heatmap_figure"](
    matrix, dataset_type, f"Real 448-module KEGG completeness matrix — {dataset_type}", "Completeness", False,
  )
  if len(exported) != 448:
    raise RuntimeError(f"Expected 448 exported KEGG rows, found {len(exported)}")
  return sparsify_heatmap_y_ticks(fig, max_visible_ticks=90)

def html_for_figure(fig: go.Figure, div_id: str) -> str:
  body = fig.to_html(full_html=False, include_plotlyjs="inline", div_id=div_id, config={"displaylogo": False})
  return (
    "<!doctype html><html><head><meta charset='utf-8'>"
    "<style>html,body{margin:0;padding:0;background:white;font-family:Arial,sans-serif;}"
    ".plotly-graph-div{margin:0 auto;}</style></head><body>"
    + body + "</body></html>"
  )


def inspect_graph(page, div_id: str) -> dict:
  return page.evaluate(
    """(id) => {
      const gd = document.getElementById(id);
      const rect = gd.getBoundingClientRect();
      const layout = gd.layout || {};
      const full = gd._fullLayout || {};
      const annotations = (layout.annotations || []).map(a => String(a.text || ''));
      const shapes = layout.shapes || [];
      const xr = full.xaxis && full.xaxis.range ? full.xaxis.range.map(Number) : [];
      const yr = full.yaxis && full.yaxis.range ? full.yaxis.range.map(Number) : [];
      const vectorShapes = shapes.filter(s =>
        s.type === 'line' && Number.isFinite(Number(s.x1)) && Number.isFinite(Number(s.y1)) &&
        (s.xref === undefined || s.xref === 'x') && (s.yref === undefined || s.yref === 'y') &&
        Number(s.x0) === 0 && Number(s.y0) === 0 && !(Number(s.x1) === 0 && Number(s.y1) === 0)
      );
      const endpointsInside = vectorShapes.every(s =>
        xr.length === 2 && yr.length === 2 && Number(s.x1) >= Math.min(...xr) && Number(s.x1) <= Math.max(...xr) &&
        Number(s.y1) >= Math.min(...yr) && Number(s.y1) <= Math.max(...yr)
      );
      return {
        width: rect.width,
        height: rect.height,
        traceCount: (gd.data || []).length,
        title: String((layout.title && layout.title.text) || ''),
        annotations,
        shapeCount: shapes.length,
        vectorShapeCount: vectorShapes.length,
        endpointsInside,
        xRange: xr,
        yRange: yr,
        yTickText: (layout.yaxis && layout.yaxis.ticktext) ? Array.from(layout.yaxis.ticktext).map(String) : [],
        yDomTickCount: gd.querySelectorAll('.ytick text').length,
      };
    }""",
    div_id,
  )


def main() -> int:
  chromium = shutil.which("chromium") or shutil.which("chromium-browser")
  if not chromium:
    raise RuntimeError("System Chromium was not found")
  VALIDATION.mkdir(parents=True, exist_ok=True)
  ARTIFACTS.mkdir(parents=True, exist_ok=True)

  cases: list[tuple[str, go.Figure, dict]] = []
  for domain in ("Bacteria", "Archaea"):
    rda, *_ = publication_rda_figure(ROOT, domain, show_taxa=True)
    nmds, *_ = publication_nmds_figure(ROOT, domain)
    cases.append((f"rda_{domain.lower()}", rda, {"kind": "RDA", "domain": domain}))
    cases.append((f"nmds_{domain.lower()}", nmds, {"kind": "NMDS", "domain": domain}))
  cases.append(("heatmap_all_172_labels", full_label_heatmap(172, True), {"kind": "heatmap", "expected_rows": 172, "min_height": 3800}))
  # Deliberately omit force_all_y_ticks: global policy must still preserve all 448 labels.
  cases.append(("heatmap_all_448_labels_unmarked", full_label_heatmap(448, False), {"kind": "heatmap", "expected_rows": 448, "min_height": 9000}))
  cases.append((
    "heatmap_real_kegg_metagenomes_448_modules",
    actual_kegg_heatmap("Metagenomes", "KEMET_lagoon_all_metagenomes_module_completeness_SCORE_3state.csv"),
    {"kind": "heatmap", "expected_rows": 448, "min_height": 9000, "min_width": 1500},
  ))
  cases.append((
    "heatmap_real_kegg_mags_448_modules",
    actual_kegg_heatmap("MAGs", "MAG_KEGG_module_completeness_SCORE_species_MAGnumber_3state.csv"),
    {"kind": "heatmap", "expected_rows": 448, "min_height": 9000, "min_width": 2200},
  ))

  results = []
  with tempfile.TemporaryDirectory(prefix="cangametag-browser-") as tmp_text, sync_playwright() as playwright:
    tmp = Path(tmp_text)
    browser = playwright.chromium.launch(
      headless=True,
      executable_path=chromium,
      args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
    )
    try:
      for name, fig, meta in cases:
        div_id = f"plot_{name}"
        html_path = tmp / f"{name}.html"
        html_path.write_text(html_for_figure(fig, div_id), encoding="utf-8")
        page = browser.new_page(viewport={"width": 1800, "height": 1000}, device_scale_factor=1)
        console_errors: list[str] = []
        failed_requests: list[str] = []
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.on("requestfailed", lambda request: failed_requests.append(request.url))
        page.route("http://**/*", lambda route: route.abort())
        page.route("https://**/*", lambda route: route.abort())
        page.set_content(html_path.read_text(encoding="utf-8"), wait_until="load", timeout=30000)
        page.wait_for_function("id => document.getElementById(id) && document.getElementById(id)._fullLayout", arg=div_id, timeout=30000)
        info = inspect_graph(page, div_id)
        screenshot = ARTIFACTS / f"{name}.png"
        page.screenshot(path=str(screenshot), full_page=True)
        page.close()

        checks = {
          "positive_geometry": info["width"] > 500 and info["height"] > 400,
          "has_traces": info["traceCount"] > 0,
          "no_browser_console_errors": not console_errors,
          "no_external_request_failures": not failed_requests,
          "offline_inline_plotly": re.search(r'<script[^>]+src=["\']https?://', html_path.read_text(encoding="utf-8"), flags=re.I) is None,
        }
        if meta["kind"] == "RDA":
          expected = EXPECTED_GENERA[meta["domain"]]
          checks.update({
            "all_expected_genera_present": expected.issubset(set(info["annotations"])),
            "at_least_12_scientific_vectors": info["vectorShapeCount"] >= 12,
            "all_vector_endpoints_inside_axes": bool(info["endpointsInside"]),
            "complete_rda_statistics_in_title": all(token in info["title"] for token in ("R²", "adjusted R²", "pseudo-F", "P =")),
          })
        elif meta["kind"] == "NMDS":
          checks.update({
            "stress_1_in_title": "Stress-1" in info["title"],
            "twenty_sample_annotations": len([x for x in info["annotations"] if ".P" in x]) >= 20,
          })
        else:
          expected_rows = int(meta["expected_rows"])
          checks.update({
            f"all_{expected_rows}_ticktext_values_retained": len(info["yTickText"]) == expected_rows and all(info["yTickText"]),
            f"all_{expected_rows}_dom_tick_labels_rendered": info["yDomTickCount"] == expected_rows,
            "expanded_scrollable_height": info["height"] >= int(meta["min_height"]),
            "readable_declared_width": info["width"] >= int(meta.get("min_width", 500)),
          })
        status = "PASS" if all(checks.values()) else "FAIL"
        results.append({
          "case": name,
          "kind": meta["kind"],
          "domain": meta.get("domain"),
          "status": status,
          "checks": checks,
          "browser_measurements": info,
          "console_errors": console_errors,
          "failed_requests": failed_requests,
          "screenshot": str(screenshot.relative_to(ROOT)),
        })
    finally:
      browser.close()

  report = {
    "test": "real Chromium visual regression for critical interactive scientific figures",
    "executed_utc": datetime.now(timezone.utc).isoformat(),
    "chromium": chromium,
    "network_policy": "all HTTP(S) blocked; Plotly bundled inline",
    "cases": results,
    "overall_status": "PASS" if all(row["status"] == "PASS" for row in results) else "FAIL",
  }
  json_path = VALIDATION / "VISUAL_BROWSER_REGRESSION_TEST.json"
  json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
  md_lines = [
    "# Visual browser regression test",
    "",
    f"Overall status: **{report['overall_status']}**",
    "",
    "Real headless Chromium rendered each critical Plotly figure with all HTTP(S) requests blocked. Plotly JavaScript was bundled inline.",
    "",
    "| Case | Status | Main checks | Screenshot |",
    "|---|---:|---|---|",
  ]
  for row in results:
    failed = [key for key, value in row["checks"].items() if not value]
    summary = "all checks passed" if not failed else "failed: " + ", ".join(failed)
    md_lines.append(f"| {row['case']} | {row['status']} | {summary} | `{row['screenshot']}` |")
  (VALIDATION / "VISUAL_BROWSER_REGRESSION_TEST.md").write_text("\n".join(md_lines) + "\n", encoding="utf-8")
  print(json_path)
  for row in results:
    print(row["case"], row["status"])
    if row["status"] != "PASS":
      print(json.dumps(row["checks"], indent=2))
  print("VISUAL_BROWSER_REGRESSION_" + report["overall_status"])
  return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
  raise SystemExit(main())
