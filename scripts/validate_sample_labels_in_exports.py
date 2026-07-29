#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ["CANGAMETAG_DISABLE_NETWORK"] = "1"

from scripts.headless_navigation_test import FakeStreamlit, StopExecution

fake = FakeStreamlit(0)
components = types.ModuleType("streamlit.components")
v1 = types.ModuleType("streamlit.components.v1")
v1.html = lambda *args, **kwargs: None
components.v1 = v1
components.__path__ = []
v1.__path__ = []
fake.__path__ = []
fake.components = components
sys.modules["streamlit"] = fake
sys.modules["streamlit.components"] = components
sys.modules["streamlit.components.v1"] = v1

namespace = {"__name__": "__main__", "__file__": str(ROOT / "app.py")}
try:
  exec(compile((ROOT / "app.py").read_text(encoding="utf-8"), str(ROOT / "app.py"), "exec"), namespace, namespace)
except StopExecution:
  pass

from src.functional_annotations import build_annotation_dataset, functional_annotation_heatmap, SOURCE_LABELS
from src.plotly_export import export_plotly_bytes

expected = [
  "AM.P1.D", "AM.P1.R", "AM.P2.D", "AM.P2.R",
  "TIA.P1.D", "TIA.P1.R", "TIA.P2.D", "TIA.P2.R",
  "TI.P1.D", "TI.P1.R", "TI.P2.D", "TI.P2.R",
  "TI.P3.D", "TI.P3.R", "TI.P4.D", "TI.P4.R",
  "VI.P1.D", "VI.P1.R", "VI.P2.D", "VI.P2.R",
]

rows = []
out_dir = ROOT / "validation" / "sample_label_export_validation"
out_dir.mkdir(parents=True, exist_ok=True)
for annotation_type in ["KO", "EC number", "PFAM"]:
  matrix, metadata, id_col, name_col = build_annotation_dataset("table6", annotation_type)
  columns = metadata["matrix_column"].astype(str).tolist()
  figure, _, _ = functional_annotation_heatmap(
    matrix, metadata, id_col, name_col, columns,
    annotation_type, SOURCE_LABELS["table6"], top_n=80,
    ranking_metric="Source table order", zscore_rows=False,
  )
  svg, backend = export_plotly_bytes(figure, "svg", width=2200, height=2800, scale=1)
  text = unquote(svg.decode("utf-8", errors="replace"))
  missing = [label for label in expected if label not in text]
  path = out_dir / f"{annotation_type.replace(' ', '_')}.svg"
  path.write_bytes(svg)
  rows.append({
    "annotation_type": annotation_type,
    "expected_labels": len(expected),
    "present_labels": len(expected) - len(missing),
    "missing_labels": ";".join(missing),
    "backend": backend,
    "pass": not missing,
  })

import pandas as pd
report = pd.DataFrame(rows)
report.to_csv(ROOT / "validation" / "PROMPT_FINAL_SAMPLE_LABEL_EXPORT_VALIDATION.tsv", sep="\t", index=False)
print(report.to_string(index=False))
if not report["pass"].all():
  raise SystemExit(1)
