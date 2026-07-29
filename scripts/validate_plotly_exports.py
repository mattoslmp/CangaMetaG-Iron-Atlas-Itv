#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

import plotly.graph_objects as go
from PIL import Image
from pypdf import PdfReader
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.plotly_export import (
  configure_browser_environment,
  discover_browser,
  export_plotly_bytes,
  validate_export_bytes,
  validate_visible_text,
)


def main() -> int:
  out_dir = ROOT / "validation" / "plotly_export_validation"
  out_dir.mkdir(parents=True, exist_ok=True)
  fig = go.Figure(
    go.Box(
      y=[1.0, 2.0, 3.0, 4.0, 10.0],
      boxpoints="all",
      name="Observed values",
    )
  )
  fig.update_layout(
    title="Plotly static export validation",
    xaxis_title="Group",
    yaxis_title="Measured value",
    width=1400,
    height=900,
    template="plotly_white",
    meta={"require_nonempty_title": True},
  )
  validate_visible_text(fig, require_title=True)
  browser = configure_browser_environment()
  results = []
  for fmt, scale in (("png", 2), ("svg", 1), ("pdf", 1)):
    data, backend = export_plotly_bytes(fig, fmt, width=1400, height=900, scale=scale)
    validate_export_bytes(data, fmt)
    path = out_dir / f"plotly_export_validation.{fmt}"
    path.write_bytes(data)
    details: dict[str, object] = {}
    if fmt == "png":
      with Image.open(path) as image:
        image.verify()
      with Image.open(path) as image:
        details["dimensions"] = [int(image.width), int(image.height)]
        if image.width < 1400 or image.height < 900:
          raise RuntimeError(f"Unexpected PNG dimensions: {image.width} × {image.height}")
    elif fmt == "svg":
      root = ET.fromstring(data.decode("utf-8"))
      if not root.tag.lower().endswith("svg"):
        raise RuntimeError("SVG root element is missing")
      svg_text = " ".join("".join(root.itertext()).split())
      details["contains_required_title"] = "Plotly static export validation" in svg_text
      details["contains_required_axis_label"] = "Measured value" in svg_text
      if not details["contains_required_title"] or not details["contains_required_axis_label"]:
        raise RuntimeError("SVG does not contain the required title/axis label")
    elif fmt == "pdf":
      reader = PdfReader(str(path))
      details["pages"] = len(reader.pages)
      if len(reader.pages) != 1:
        raise RuntimeError(f"Expected one PDF page, found {len(reader.pages)}")
      page = reader.pages[0]
      details["media_box_points"] = [float(page.mediabox.width), float(page.mediabox.height)]
      if float(page.mediabox.width) <= 0 or float(page.mediabox.height) <= 0:
        raise RuntimeError("Invalid PDF page dimensions")
    results.append({
      "format": fmt,
      "path": str(path.relative_to(ROOT)),
      "bytes": len(data),
      "backend": backend,
      "valid": True,
      **details,
    })
  payload = {
    "browser": browser or discover_browser(),
    "results": results,
  }
  (out_dir / "validation.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
  print(json.dumps(payload, indent=2))
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
