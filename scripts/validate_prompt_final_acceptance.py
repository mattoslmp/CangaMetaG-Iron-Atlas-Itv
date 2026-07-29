#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
checks: list[dict[str, object]] = []


def add(name: str, passed: bool, detail: str = "") -> None:
  checks.append({"check": name, "status": "PASS" if passed else "FAIL", "detail": detail})


app_text = (ROOT / "app.py").read_text(encoding="utf-8")
req = (ROOT / "requirements.txt").read_text(encoding="utf-8")
packages = (ROOT / "packages.txt").read_text(encoding="utf-8") if (ROOT / "packages.txt").exists() else ""

add("figure_reproduction_commands_preserved", (ROOT / "FIGURE_REPRODUCTION_COMMANDS.md").exists())
add("final_delivery_summary_removed", not (ROOT / "FINAL_DELIVERY_SUMMARY.md").exists())
add("redundant_root_markdown_removed", all(not (ROOT / name).exists() for name in [
  "CORRECTIONS_SUMMARY.md", "FIXES_COMPLETED.md", "CHANGES_APPLIED.md", "DELIVERY_REPORT.md",
  "PROMPT_IMPLEMENTATION.md", "FINAL_CHECKLIST.md", "VALIDATION_SUMMARY.md",
]))
add("kaleido_dependency_documented", "kaleido" in req.casefold())
add("playwright_dependency_documented", "playwright" in req.casefold())
add("chromium_system_dependency_documented", "chromium" in packages.casefold())
add("browser_discovery_implemented", "discover_browser" in app_text and (ROOT / "src/plotly_export.py").exists())
add("invalid_visible_text_validation_implemented", "validate_visible_text" in app_text)
add("figure_specific_audit_expander_implemented", "Source data for {figure_id}" in app_text and "Dados utilizados em {figure_id}" in app_text)
add("boxplot_missing_values_not_filled_with_zero", 'marker_normalized_count"] = pd.to_numeric(raw["marker_normalized_count"], errors="coerce")' in app_text)
add("boxplot_descriptive_statistics_implemented", "def _boxplot_descriptive_stats" in app_text)
add("boxplot_points_visible_by_default", 'Show individual sample points"), value=True' in app_text)

boxplot_json = json.loads((ROOT / "validation/boxplot_integrity_validation.json").read_text(encoding="utf-8"))
add("boxplot_quartile_whisker_validation", bool(boxplot_json.get("passed")), json.dumps(boxplot_json.get("checks", {}), ensure_ascii=False))

export_json = json.loads((ROOT / "validation/plotly_export_validation/validation.json").read_text(encoding="utf-8"))
export_results = export_json.get("results", [])
add("png_svg_pdf_exports_valid", len(export_results) == 3 and all(bool(item.get("valid")) for item in export_results), json.dumps(export_results, ensure_ascii=False))

labels = pd.read_csv(ROOT / "validation/PROMPT_FINAL_SAMPLE_LABEL_EXPORT_VALIDATION.tsv", sep="\t")
add("all_lake_sample_labels_in_exports", len(labels) == 3 and labels["pass"].astype(bool).all() and (labels["present_labels"] == 20).all(), labels.to_json(orient="records"))

browser = pd.read_csv(ROOT / "validation/LATEST_REQUESTED_VISUAL_BROWSER_VALIDATION.csv")
add("visual_browser_validation", browser["pass"].astype(bool).all(), browser.to_json(orient="records"))

navigation = pd.read_csv(ROOT / "validation/LATEST_APP_HEADLESS_NAVIGATION_TEST.tsv", sep="\t")
add("all_app_pages_navigate", len(navigation) == 14 and navigation["status"].eq("PASS").all(), navigation[["page", "status"]].to_json(orient="records"))

latest = pd.read_csv(ROOT / "validation/LATEST_REQUESTED_CORRECTIONS_VALIDATION.csv")
add("previous_requested_corrections_still_pass", latest["status"].eq("PASS").all(), f"{latest['status'].eq('PASS').sum()}/{len(latest)}")

static_regression = json.loads((ROOT / "validation/PROMPT_FINAL_STATIC_FIGURE_REGRESSION.json").read_text(encoding="utf-8"))
add("no_unrequested_static_figure_changes", static_regression.get("MODIFIED_UNREQUESTED", 1) == 0 and static_regression.get("MISSING", 1) == 0, json.dumps(static_regression))

for forbidden in ["FINAL_DELIVERY_SUMMARY.md", "PROMPT_IMPLEMENTATION.md", "VALIDATION_SUMMARY.md"]:
  found = list(ROOT.rglob(forbidden))
  add(f"forbidden_file_absent_{forbidden}", not found, "; ".join(str(p.relative_to(ROOT)) for p in found))

report = pd.DataFrame(checks)
report.to_csv(ROOT / "validation/PROMPT_FINAL_ACCEPTANCE.tsv", sep="\t", index=False)
payload = {
  "passed": bool(report["status"].eq("PASS").all()),
  "passed_checks": int(report["status"].eq("PASS").sum()),
  "total_checks": int(len(report)),
  "checks": checks,
}
(ROOT / "validation/PROMPT_FINAL_ACCEPTANCE.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
print(report.to_string(index=False))
print(f"PASS {payload['passed_checks']}/{payload['total_checks']}" if payload["passed"] else f"FAIL {payload['passed_checks']}/{payload['total_checks']}")
raise SystemExit(0 if payload["passed"] else 1)
