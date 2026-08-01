from __future__ import annotations

"""Supplementary Figure 68 generated from packaged antiSMASH region files."""

import base64
import html
from pathlib import Path
import textwrap
from typing import Mapping, Any

import pandas as pd

from .antismash_metabolism_runtime import (
  bgc_metabolism_inventory,
  render_bgc_metabolism_panel as _render_bgc_metabolism_table,
)


SCRIPT_PATH = "scripts/final_publication_figures/09_generate_antismash_bgc_supplementary_figure.py"
INPUT_PATHS = [
  "data/kegg_modules/mags/gbk_antismash/**/region*.gbk",
  "data/antismash/**/region*.gbk",
  "outputs/antismash/**/region*.gbk",
]
OUTPUT_STEM = "SupplementaryFigure68_antiSMASH_BGC_iron_metals_carbon_evidence"
OUTPUT_FIGURE = f"outputs/app_supplementary_figures/{OUTPUT_STEM}.svg"
OUTPUT_TABLE = "data/final_publication_derived/antiSMASH_BGC_iron_metals_carbon_evidence.csv"
OUTPUT_REPORT = "reports/FINAL_ANTISMASH_BGC_SUPPLEMENTARY_FIGURE_REPORT.json"


def _svg_text_lines(
  text: object,
  *,
  x: float,
  y: float,
  width: int,
  line_height: int = 18,
  font_size: int = 14,
  weight: str = "normal",
  color: str = "#111827",
) -> str:
  cleaned = " ".join(str(text or "").split())
  lines = textwrap.wrap(cleaned, width=width) or [""]
  spans = []
  for index, line in enumerate(lines):
    dy = 0 if index == 0 else line_height
    spans.append(
      f'<tspan x="{x}" dy="{dy}">{html.escape(line)}</tspan>'
    )
  return (
    f'<text x="{x}" y="{y}" font-family="Arial,Helvetica,sans-serif" '
    f'font-size="{font_size}" font-weight="{weight}" fill="{color}">'
    + "".join(spans)
    + "</text>"
  )


def _cluster_uri(value: object) -> str:
  text = str(value or "").strip()
  return text if text.startswith("data:image/svg+xml;base64,") else ""


def bgc_supplementary_figure_svg(table: pd.DataFrame | None = None) -> bytes:
  data = bgc_metabolism_inventory() if table is None else table.copy()
  width = 1900
  row_height = 188
  header_height = 190
  footer_height = 170
  visible_rows = max(1, len(data))
  height = header_height + visible_rows * row_height + footer_height

  elements = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
    '<rect width="100%" height="100%" fill="white"/>',
    _svg_text_lines(
      "Supplementary Figure 68 — antiSMASH BGCs with iron/metal or carbon-skeleton evidence",
      x=28,
      y=42,
      width=125,
      font_size=25,
      weight="bold",
    ),
    _svg_text_lines(
      "BGC classes and gene annotations are read directly from packaged antiSMASH region GenBank files. Siderophore/metallophore calls are direct class-level evidence; other metal terms are candidates. PKS, NRPS and terpene classes denote specialized carbon-skeleton biosynthesis and do not alone demonstrate central carbon cycling.",
      x=28,
      y=78,
      width=190,
      line_height=19,
      font_size=14,
      color="#334155",
    ),
    '<line x1="28" y1="164" x2="1872" y2="164" stroke="#94A3B8" stroke-width="1"/>',
  ]

  if data.empty:
    elements.append(_svg_text_lines(
      "No qualifying BGC was detected in the packaged antiSMASH region files.",
      x=40,
      y=header_height + 80,
      width=140,
      font_size=20,
      weight="bold",
      color="#475569",
    ))
  else:
    for index, row in data.reset_index(drop=True).iterrows():
      top = header_height + index * row_height
      fill = "#F8FAFC" if index % 2 == 0 else "#FFFFFF"
      elements.append(
        f'<rect x="24" y="{top}" width="1852" height="{row_height - 8}" rx="8" fill="{fill}" stroke="#CBD5E1"/>'
      )
      title = f"{row.get('MAG', '')} — {row.get('BGC', '')} — {row.get('antiSMASH product class', '')}"
      elements.append(_svg_text_lines(title, x=42, y=top + 28, width=95, font_size=16, weight="bold"))
      uri = _cluster_uri(row.get("Cluster figure", ""))
      if uri:
        elements.append(
          f'<image href="{html.escape(uri, quote=True)}" x="38" y="{top + 38}" width="735" height="112" preserveAspectRatio="xMidYMid meet"/>'
        )
      else:
        elements.append(_svg_text_lines("Cluster geometry unavailable", x=48, y=top + 92, width=65, font_size=15))

      metal_title = f"Iron / metal — {row.get('metal evidence', '')}"
      carbon_title = f"Carbon — {row.get('carbon evidence', '')}"
      elements.append(_svg_text_lines(metal_title, x=805, y=top + 42, width=65, font_size=15, weight="bold", color="#9A3412"))
      elements.append(_svg_text_lines(row.get("iron / metal relevance", ""), x=805, y=top + 65, width=72, font_size=13, color="#334155"))
      elements.append(_svg_text_lines(carbon_title, x=1350, y=top + 42, width=52, font_size=15, weight="bold", color="#1D4ED8"))
      elements.append(_svg_text_lines(row.get("carbon relevance", ""), x=1350, y=top + 65, width=61, font_size=13, color="#334155"))
      elements.append(_svg_text_lines(
        f"Source: {row.get('source region file', '')}",
        x=805,
        y=top + 158,
        width=100,
        font_size=12,
        color="#64748B",
      ))

  footer_y = header_height + visible_rows * row_height + 22
  elements.extend([
    '<line x1="28" y1="{}" x2="1872" y2="{}" stroke="#94A3B8" stroke-width="1"/>'.format(footer_y - 10, footer_y - 10),
    _svg_text_lines(f"Script: {SCRIPT_PATH}", x=28, y=footer_y + 18, width=175, font_size=14, weight="bold"),
    _svg_text_lines("Input: " + "; ".join(INPUT_PATHS), x=28, y=footer_y + 48, width=195, font_size=13, color="#334155"),
    _svg_text_lines(f"Output figure: {OUTPUT_FIGURE}", x=28, y=footer_y + 88, width=190, font_size=13, color="#334155"),
    _svg_text_lines(f"Output table: {OUTPUT_TABLE}", x=28, y=footer_y + 116, width=190, font_size=13, color="#334155"),
    _svg_text_lines("No generative image model was used; cluster drawings derive from CDS coordinates in region*.gbk.", x=28, y=footer_y + 144, width=190, font_size=13, weight="bold", color="#166534"),
    "</svg>",
  ])
  return "".join(elements).encode("utf-8")


def public_bgc_table(table: pd.DataFrame) -> pd.DataFrame:
  return table.drop(columns=["Cluster figure", "source values changed"], errors="ignore").copy()


def render_bgc_metabolism_panel_with_supplementary(namespace: Mapping[str, Any]) -> None:
  st = namespace["st"]
  txt = namespace["txt"]
  _render_bgc_metabolism_table(dict(namespace))

  table = bgc_metabolism_inventory()
  svg = bgc_supplementary_figure_svg(table)
  st.markdown("#### " + txt(
    "Figura Suplementar 68 — BGCs antiSMASH relacionados a ferro/metais e carbono",
    "Supplementary Figure 68 — antiSMASH BGCs related to iron/metals and carbon",
  ))
  st.image(svg, width="stretch")
  st.caption(txt(
    f"Script: {SCRIPT_PATH} | Entrada: {'; '.join(INPUT_PATHS)} | Saídas: {OUTPUT_FIGURE}; {OUTPUT_TABLE}",
    f"Script: {SCRIPT_PATH} | Input: {'; '.join(INPUT_PATHS)} | Outputs: {OUTPUT_FIGURE}; {OUTPUT_TABLE}",
  ))
  st.download_button(
    txt("Baixar Figura Suplementar 68 em SVG", "Download Supplementary Figure 68 as SVG"),
    data=svg,
    file_name=f"{OUTPUT_STEM}.svg",
    mime="image/svg+xml",
    key="download_supplementary_figure68_antismash_svg",
    width="stretch",
  )
  with st.expander(txt("Dados científicos usados nesta figura", "Scientific data used in this figure"), expanded=False):
    st.markdown(f"**{txt('Fonte', 'Source')}**")
    st.code("\n".join(INPUT_PATHS), language="text")
    st.markdown(f"**{txt('Processado', 'Processed')}**")
    st.dataframe(public_bgc_table(table), width="stretch", hide_index=True)
    st.markdown(f"**{txt('Saída', 'Output')}**")
    st.code(f"{OUTPUT_FIGURE}\n{OUTPUT_TABLE}\n{OUTPUT_REPORT}", language="text")
    st.markdown(f"**{txt('Script', 'Script')}**")
    st.code(SCRIPT_PATH, language="text")
