#!/usr/bin/env python3
from __future__ import annotations

import json
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def patch_generated_combined_script() -> dict[str, object]:
  path = ROOT / "scripts" / "final_publication_figures" / "03_generate_combined_community_figures.py"
  text = path.read_text(encoding="utf-8")
  text = text.replace(
    'ax.boxplot(groups, labels=["AM","TIA","TI","VI"], showfliers=False)',
    'ax.boxplot(groups, tick_labels=["AM","TIA","TI","VI"], showfliers=False)',
  )
  if "tick_labels=" not in text:
    raise RuntimeError("Could not patch Matplotlib boxplot compatibility")
  path.write_text(text, encoding="utf-8")
  return {
    "path": str(path.relative_to(ROOT)),
    "matplotlib_tick_labels": True,
  }


def patch_existing_percentage_label_transform() -> dict[str, object]:
  path = ROOT / "src" / "app_other_taxa_percentage_label_transform.py"
  text = path.read_text(encoding="utf-8")
  text = text.replace("declared 5% cutoff", "declared 1% cutoff")
  text = text.replace("_OTHER_TAXA_THRESHOLD_PERCENT = 5.0", "_OTHER_TAXA_THRESHOLD_PERCENT = 1.0")
  text = text.replace("5% denotes the per-taxon cutoff", "1% denotes the per-taxon cutoff")
  path.write_text(text, encoding="utf-8")
  if "_OTHER_TAXA_THRESHOLD_PERCENT = 1.0" not in text:
    raise RuntimeError("Could not update the existing aggregate-label threshold")
  return {
    "path": str(path.relative_to(ROOT)),
    "threshold_percent": 1.0,
  }


def patch_app_transform_chain() -> dict[str, object]:
  app_path = ROOT / "app.py"
  transform_path = ROOT / "src" / "app_genus_lt1_transform.py"
  if not transform_path.is_file():
    raise FileNotFoundError(transform_path)
  text = app_path.read_text(encoding="utf-8")
  entry = '  Path(__file__).with_name("src") / "app_genus_lt1_transform.py",\n'
  if "app_genus_lt1_transform.py" not in text:
    anchor = "]\n\n\ndef _compile_final_source"
    if anchor not in text:
      raise RuntimeError("Could not locate the end of the app transform list")
    text = text.replace(anchor, entry + anchor, 1)
    app_path.write_text(text, encoding="utf-8")

  source = (ROOT / "app_core.py").read_text(encoding="utf-8")
  namespace = runpy.run_path(str(app_path), run_name="_delivery_chain_probe")
  # app.py executes the final application, so the line above is not suitable for
  # validation in a headless build. Rebuild only the transform chain below.
  source = (ROOT / "app_core.py").read_text(encoding="utf-8")
  transform_files = []
  for line in text.splitlines():
    if 'Path(__file__).with_name("src") / "' not in line:
      continue
    name = line.split('/ "', 1)[1].rsplit('"', 1)[0]
    transform_files.append(ROOT / "src" / name)
  for transform in transform_files:
    result = runpy.run_path(str(transform), init_globals={"source": source})
    source = result["source"]
  compile(source, str(ROOT / "app_core.py"), "exec")
  required = [
    "CANGAMETAG_GENUS_LT1_CANONICAL_V1",
    "_CANGAMETAG_GENUS_OTHER_THRESHOLD_PERCENT = 1.0",
    "Other taxa (<1% each)",
  ]
  missing = [token for token in required if token not in source]
  if missing:
    raise RuntimeError(f"Final app source lacks genus <1% contract: {missing}")
  return {
    "path": "app.py",
    "transform_count": len(transform_files),
    "last_transform": str(transform_files[-1].relative_to(ROOT)),
    "compiled_final_source": True,
    "contract_tokens": required,
  }


def main() -> int:
  # Patch the wrapper before rebuilding the source. Avoid importing or executing
  # Streamlit itself; validation compiles the fully transformed source only.
  app_path = ROOT / "app.py"
  text = app_path.read_text(encoding="utf-8")
  entry = '  Path(__file__).with_name("src") / "app_genus_lt1_transform.py",\n'
  if "app_genus_lt1_transform.py" not in text:
    anchor = "]\n\n\ndef _compile_final_source"
    if anchor not in text:
      raise RuntimeError("Could not locate the end of the app transform list")
    app_path.write_text(text.replace(anchor, entry + anchor, 1), encoding="utf-8")

  generator_report = patch_generated_combined_script()
  label_report = patch_existing_percentage_label_transform()

  # Compile the complete transform chain without executing the Streamlit app.
  wrapper = app_path.read_text(encoding="utf-8")
  source = (ROOT / "app_core.py").read_text(encoding="utf-8")
  transform_files = []
  for line in wrapper.splitlines():
    marker = 'Path(__file__).with_name("src") / "'
    if marker not in line:
      continue
    name = line.split(marker, 1)[1].split('"', 1)[0]
    transform_files.append(ROOT / "src" / name)
  for transform in transform_files:
    namespace = runpy.run_path(str(transform), init_globals={"source": source})
    source = namespace["source"]
  compile(source, str(ROOT / "app_core.py"), "exec")
  required = [
    "CANGAMETAG_GENUS_LT1_CANONICAL_V1",
    "_CANGAMETAG_GENUS_OTHER_THRESHOLD_PERCENT = 1.0",
    "Other taxa (<1% each)",
  ]
  missing = [token for token in required if token not in source]
  if missing:
    raise RuntimeError(f"Final app source lacks genus <1% contract: {missing}")

  report = {
    "combined_generator": generator_report,
    "existing_label_transform": label_report,
    "app": {
      "path": "app.py",
      "transform_count": len(transform_files),
      "last_transform": str(transform_files[-1].relative_to(ROOT)),
      "compiled_final_source": True,
      "contract_tokens": required,
    },
  }
  report_path = ROOT / "reports" / "DELIVERY_20260802_WORKSPACE_FIX_REPORT.json"
  report_path.parent.mkdir(parents=True, exist_ok=True)
  report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
  print(json.dumps(report, indent=2, ensure_ascii=False))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
