#!/usr/bin/env python3
"""Generate the canonical thematic three-state KEGG/KEMET module figures.

Scope
-----
This script preserves the approved Supplementary Figure 38 and Supplementary Figure 41 outputs. The complete source matrices are read-only and remain packaged.

Thematic selection rule
-----------------------
A curated, explicit module catalogue prioritises modules that either:
1. contain KO biomarkers analysed in Supplementary Table 8; or
2. represent nitrogen, phosphorus, carbon, methane, sulfur, photosynthesis,
   iron, or directly related biogeochemical processes.

Within that thematic catalogue, a row is drawn only when at least one displayed
record is ``Complete``. Every cell of every retained row is then displayed using
its original state: ``Complete``, ``1 block missing``, or ``Incomplete``. Original
``2 blocks missing`` values remain unchanged in supporting tables and use the red
``Incomplete`` visual class. Only true missing data are white.

The same retained matrices generate manuscript panels, application-integral
views and the S41 summary. No source values are modified.
"""
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import json
import math
import re
import shutil
import sys
import textwrap
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from PIL import Image

GREEN = "#2E7D32"
BLUE = "#1565C0"
RED = "#C62828"
WHITE = "#FFFFFF"
VISUAL_COLORS = {"Complete": GREEN, "1 block missing": BLUE, "Incomplete": RED}
VISUAL_CODES = {"Incomplete": 0, "1 block missing": 1, "Complete": 2}
LEGEND_ORDER = ("Complete", "1 block missing", "Incomplete")
CYCLE_ORDER = ("Nitrogen", "Phosphorus", "Carbon", "Methane", "Sulfur", "Photosynthesis", "Iron")

# Explicit presentation catalogue. This is deliberately human-readable and
# version-controlled so the figure-selection logic is not hidden in heuristics.
THEMATIC_MODULES: dict[str, tuple[str, ...]] = {
  "Nitrogen": ("M00175", "M00528", "M00529", "M00530", "M00531", "M00615", "M00804"),
  "Phosphorus": ("M00130", "M00131", "M00132"),
  "Carbon": ("M00165", "M00166", "M00173", "M00374", "M00375", "M00376", "M00377", "M00422", "M00579", "M00618", "M00620"),
  "Methane": ("M00174", "M00356", "M00357", "M00358", "M00378", "M00563", "M00567", "M00617"),
  "Sulfur": ("M00021", "M00176", "M00338", "M00595", "M00596", "M00609", "M00616"),
  "Photosynthesis": ("M00161", "M00162", "M00163", "M00597", "M00598", "M00611", "M00612", "M00613", "M00614"),
  "Iron": ("M00121", "M00144", "M00151", "M00152", "M00154", "M00155", "M00156", "M00847", "M00868", "M00926"),
}


@dataclass(frozen=True)
class FigureConfig:
  figure: int
  source_file: str
  stem: str
  title: str
  x_label: str
  rows_per_block: int
  cols_per_block: int
  x_font: float
  y_font: float
  x_wrap: int
  y_wrap: int


CONFIGS = (
  FigureConfig(
    37,
    "MAG_KEGG_module_completeness_STATUS_species_MAGnumber_3state.csv",
    "SupplementaryFigure37_MAG_KEGG_module_completeness_heatmap_species_MAGnumber_KEMET_style_3state",
    "Thematic MAG KEGG/KEMET module completeness",
    "Recovered MAGs",
    999,
    999,
    10.5,
    11.5,
    100,
    42,
  ),
  FigureConfig(
    38,
    "KEMET_lagoon_all_metagenomes_module_completeness_STATUS_3state.csv",
    "SupplementaryFigure38_metagenome_KEGG_module_completeness_heatmap",
    "Thematic Amazonian lagoon metagenome KEGG/KEMET module completeness",
    "Amazonian lagoon metagenomes",
    999,
    999,
    12.0,
    11.5,
    100,
    45,
  ),
  FigureConfig(
    40,
    "ST8_external_iron_rich_module_completeness_STATUS_3state_from_KO.csv",
    "SupplementaryFigure40_ST8_external_iron_rich_module_completeness_KEMET_style_3state_heatmap",
    "Thematic external iron-rich metagenome KEGG/KEMET module completeness",
    "External iron-rich metagenomes",
    24,
    999,
    11.5,
    11.0,
    100,
    42,
  ),
  FigureConfig(
    67,
    "Combined_lagoon_plus_external_iron_rich_module_completeness_STATUS_3state.csv",
    "SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_KEMET_style_3state_heatmap",
    "Amazonian plus external thematic module completeness",
    "Amazonian metagenomes and external iron-rich records",
    24,
    999,
    12.5,
    11.5,
    100,
    40,
  ),
)

def sha256(path: Path) -> str:
  h = hashlib.sha256()
  with path.open("rb") as handle:
    for block in iter(lambda: handle.read(1024 * 1024), b""):
      h.update(block)
  return h.hexdigest()


def clean_label(value: object) -> str:
  text = str(value if value is not None else "").strip()
  if not text or text.casefold() in {"nan", "none", "undefined", "null", "unnamed: 0"}:
    return "Unlabelled KEGG module"
  text = text.replace("_", " ").replace(" => ", " -> ")
  return re.sub(r"\s+", " ", text)


def get_module_id(value: object) -> str:
  match = re.search(r"\bM\d{5}\b", str(value or ""))
  return match.group(0) if match else "Not reported"


def normalise_status(value: object) -> str:
  if value is None or (isinstance(value, float) and np.isnan(value)):
    return "Missing data"
  text = re.sub(r"\s+", " ", str(value).strip()).casefold()
  if not text or text in {"nan", "none", "null", "undefined", "absent", "missing", "no data"}:
    return "Missing data"
  if text == "complete":
    return "Complete"
  if text in {"1 block missing", "one block missing"}:
    return "1 block missing"
  if text in {"2 blocks missing", "two blocks missing"}:
    return "2 blocks missing"
  if text == "incomplete":
    return "Incomplete"
  raise ValueError(f"Unsupported module status: {value!r}")


def visual_class(status: str) -> str:
  if status in {"Complete", "1 block missing"}:
    return status
  if status in {"Incomplete", "2 blocks missing"}:
    return "Incomplete"
  if status == "Missing data":
    return "Missing data"
  raise ValueError(status)


def wrap(value: object, width: int) -> str:
  return "\n".join(textwrap.wrap(clean_label(value), width=max(8, width), break_long_words=False, break_on_hyphens=False))


def format_x_label(value: object, figure: int) -> str:
  text = clean_label(value)
  if figure in {37, 38}:
    # Preserve complete identifiers on a single line. Rotation and margins, not
    # automatic line splitting, provide the required separation.
    return text
  match = re.search(r"(\d{7,})$", text)
  if match:
    # The packaged accession is the complete unique plotted record identifier.
    return match.group(1)
  return text


def read_xlsx_sheet_three_columns(path: Path, sheet_name: str) -> list[dict[str, str]]:
  """Read the first three columns of a worksheet without altering the workbook."""
  ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
  rel_ns = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"

  def column_number(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    number = 0
    for char in match.group(1):
      number = number * 26 + ord(char) - 64
    return number

  with ZipFile(path) as archive:
    shared: list[str] = []
    if "xl/sharedStrings.xml" in archive.namelist():
      root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
      shared = ["".join(t.text or "" for t in item.iter(ns + "t")) for item in root.findall(ns + "si")]
    workbook = ET.fromstring(archive.read("xl/workbook.xml"))
    rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relation_map = {item.attrib["Id"]: item.attrib["Target"] for item in rels}
    target = None
    for sheet in workbook.find(ns + "sheets"):
      if sheet.attrib["name"] == sheet_name:
        target = "xl/" + relation_map[sheet.attrib[rel_ns]]
        break
    if target is None:
      raise KeyError(f"Worksheet not found: {sheet_name}")
    root = ET.fromstring(archive.read(target))
    rows: list[list[str]] = []
    for row in root.iter(ns + "row"):
      values: dict[int, str] = {}
      for cell in row.findall(ns + "c"):
        index = column_number(cell.attrib.get("r", "A1"))
        value_node = cell.find(ns + "v")
        if value_node is None:
          inline = cell.find(ns + "is")
          value = "".join(t.text or "" for t in inline.iter(ns + "t")) if inline is not None else ""
        else:
          value = value_node.text or ""
          if cell.attrib.get("t") == "s":
            value = shared[int(value)]
        values[index] = value
      if values:
        rows.append([values.get(i, "") for i in range(1, 4)])
  if not rows:
    return []
  headers = rows[0]
  return [dict(zip(headers, row)) for row in rows[1:] if any(str(x).strip() for x in row)]


def load_table_s8_biomarkers(table_path: Path) -> dict[str, list[dict[str, str]]]:
  ko_pattern = re.compile(r"\bK\d{5}\b")
  output: dict[str, list[dict[str, str]]] = {}
  sheets = (
    ("ST8 — all KO biomarkers", "KO", "Metabolism", "KO description", "General Table S8 biomarker"),
    ("ST8- Iron metabolism KO -marker", "Function Id", "Biologic Role", "Function Name", "Iron Table S8 biomarker"),
  )
  for sheet_name, id_col, category_col, description_col, source_label in sheets:
    for row in read_xlsx_sheet_three_columns(table_path, sheet_name):
      match = ko_pattern.search(str(row.get(id_col, "")))
      if not match:
        continue
      output.setdefault(match.group(0), []).append({
        "category": clean_label(row.get(category_col, "")),
        "description": clean_label(row.get(description_col, "")),
        "source": source_label,
        "worksheet": sheet_name,
      })
  return output


def build_thematic_catalog(root: Path) -> pd.DataFrame:
  module_path = root / "data" / "final_kegg_st8_update" / "KEMET_module_KO_sets_extracted_from_lagoon_reportKMC.csv"
  table_s8 = root / "tables" / "Supplementary_Table_8.xlsx"
  modules = pd.read_csv(module_path, keep_default_na=False).set_index("Module_id")
  biomarkers = load_table_s8_biomarkers(table_s8)
  rows: list[dict[str, object]] = []
  order = 0
  for cycle in CYCLE_ORDER:
    for module_id in THEMATIC_MODULES[cycle]:
      order += 1
      if module_id not in modules.index:
        raise KeyError(f"Thematic module absent from packaged module catalogue: {module_id}")
      module = modules.loc[module_id]
      ko_set = [x for x in str(module["KO_set"]).split(",") if x]
      matched = sorted(set(ko_set).intersection(biomarkers))
      biomarker_details = []
      categories = []
      for ko in matched:
        for item in biomarkers[ko]:
          categories.append(item["category"])
          biomarker_details.append(f"{ko}: {item['category']} — {item['description']}")
      iron_hits = [x for x in biomarker_details if re.search(r"iron|heme|siderophore|ferric|ferrous|magnetosome", x, re.I)]
      if matched:
        reason = "Contains one or more KO biomarkers analysed in Supplementary Table 8 and belongs to a requested biogeochemical theme."
      else:
        reason = f"Directly represents the requested {cycle.lower()} theme in the packaged KEGG/KEMET module catalogue."
      if cycle == "Phosphorus" and not matched:
        reason += " The Table S8 phosphorus biomarker K06163 (phnJ) has no module mapping in the packaged KEMET KO-set catalogue; inositol-phosphate modules were retained as the explicit phosphorus-associated module set without inventing a K06163 mapping."
      rows.append({
        "Selection_order": order,
        "Module_ID": module_id,
        "Module_name": clean_label(module["Module_name"]),
        "Biogeochemical_cycle": cycle,
        "Relation_to_iron": "Direct Table S8 iron-biomarker intersection" if iron_hits else ("Iron/heme-related module" if cycle == "Iron" else "No direct iron relation assigned"),
        "Table_S8_biomarker_KOs": "; ".join(matched) if matched else "None",
        "Table_S8_biomarker_categories": "; ".join(sorted(set(categories))) if categories else "None",
        "Table_S8_biomarker_details": " | ".join(biomarker_details) if biomarker_details else "None",
        "Reason_for_inclusion": reason,
        "Module_KO_count": int(module["KO_count"]),
        "Module_KO_set": str(module["KO_set"]),
        "Module_catalog_source": str(module_path.relative_to(root)),
        "Table_S8_source": str(table_s8.relative_to(root)),
        "Selection_script": "scripts/generate_s38_s41_module_figures.py",
        "Selection_rule": "Thematic catalogue (Table S8 biomarker intersection and/or requested cycle) followed by at least one Complete status in each displayed matrix; all original cell states are preserved.",
      })
  catalog = pd.DataFrame(rows).drop_duplicates("Module_ID", keep="first")
  return catalog.sort_values("Selection_order").reset_index(drop=True)


def load_thematic_matrix(path: Path, catalog: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
  source = pd.read_csv(path, keep_default_na=False)
  first = source.columns[0]
  source[first] = source[first].map(clean_label)
  source["__module_id__"] = source[first].map(get_module_id)
  if source["__module_id__"].duplicated().any():
    dup = source.loc[source["__module_id__"].duplicated(keep=False), "__module_id__"].tolist()
    raise ValueError(f"Duplicate module IDs in {path.name}: {dup[:10]}")
  source = source.set_index("__module_id__")
  module_labels = source[first].copy()
  statuses = source.drop(columns=[first]).map(normalise_status)
  selected_ids = [x for x in catalog["Module_ID"] if x in statuses.index]
  thematic = statuses.loc[selected_ids].copy()
  complete_mask = thematic.eq("Complete").any(axis=1)
  retained = thematic.loc[complete_mask].copy()
  visual = retained.map(visual_class)
  codes = visual.replace(VISUAL_CODES).astype(float)
  codes[visual.eq("Missing data")] = np.nan
  labels = pd.DataFrame({
    "Module_ID": retained.index,
    "Module_label": [module_labels.loc[x] for x in retained.index],
  }).set_index("Module_ID")
  return retained, visual, codes, labels


def save_png_pdf_svg(fig: plt.Figure, stem: Path, dpi: int = 300) -> dict[str, object]:
  stem.parent.mkdir(parents=True, exist_ok=True)
  png = stem.with_suffix(".png")
  pdf = stem.with_suffix(".pdf")
  svg = stem.with_suffix(".svg")
  fig.savefig(png, dpi=dpi, facecolor="white")
  with Image.open(png) as opened:
    image = opened.convert("RGB")
    dims = list(image.size)
    image.save(pdf, "PDF", resolution=float(dpi))
  payload = base64.b64encode(png.read_bytes()).decode("ascii")
  svg.write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{dims[0]}" height="{dims[1]}" viewBox="0 0 {dims[0]} {dims[1]}">'
    f'<image href="data:image/png;base64,{payload}" width="{dims[0]}" height="{dims[1]}"/></svg>',
    encoding="utf-8",
  )
  return {
    "png": {"path": str(png), "sha256": sha256(png), "size": png.stat().st_size, "dimensions": dims},
    "pdf": {"path": str(pdf), "sha256": sha256(pdf), "size": pdf.stat().st_size},
    "svg": {"path": str(svg), "sha256": sha256(svg), "size": svg.stat().st_size},
  }


def legend_handles() -> list[Patch]:
  return [Patch(facecolor=VISUAL_COLORS[x], edgecolor="none", label=x) for x in LEGEND_ORDER]


def render_panel(
  cfg: FigureConfig,
  visual: pd.DataFrame,
  codes: pd.DataFrame,
  labels: pd.DataFrame,
  panel_id: str,
  panel_total: int,
  row_block: tuple[int, int],
  col_block: tuple[int, int],
) -> tuple[plt.Figure, dict[str, object]]:
  r0, r1 = row_block
  c0, c1 = col_block
  sub_visual = visual.iloc[r0:r1, c0:c1]
  sub_codes = codes.iloc[r0:r1, c0:c1]
  n_rows, n_cols = sub_codes.shape

  if cfg.figure == 37:
    width, height = 20.5, 13.8
    left, right, top, bottom = 0.285, 0.990, 0.895, 0.485
    rotation, ha, x_font = 45, "right", 10.5
  elif cfg.figure == 38:
    # Twenty short sample identifiers do not require the former oversized lower
    # margin.  The compact geometry removes the large blank band while keeping
    # every label and the legend outside the matrix.
    width, height = 16.5, 10.6
    left, right, top, bottom = 0.300, 0.988, 0.900, 0.235
    rotation, ha, x_font = 35, "right", 11.5
  elif cfg.figure == 40:
    width, height = 18.5, 13.6
    left, right, top, bottom = 0.265, 0.988, 0.900, 0.455
    rotation, ha, x_font = 45, "right", 11.5
  else:
    width, height = 21.5, 15.8
    left, right, top, bottom = 0.250, 0.992, 0.905, 0.520
    rotation, ha, x_font = 45, "right", 12.5

  fig = plt.figure(figsize=(width, height), facecolor="white")
  ax = fig.add_axes([left, bottom, right - left, top - bottom])
  cmap = ListedColormap([RED, BLUE, GREEN])
  cmap.set_bad(WHITE)
  norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N)
  matrix = np.ma.masked_invalid(sub_codes.to_numpy(float))
  ax.pcolormesh(np.arange(n_cols + 1), np.arange(n_rows + 1), matrix, cmap=cmap, norm=norm, shading="flat", edgecolors="white", linewidth=0.28, rasterized=True)
  ax.set_xlim(0, n_cols)
  ax.set_ylim(n_rows, 0)
  ax.set_xticks(np.arange(n_cols) + 0.5)
  x_label_artists = []
  if cfg.figure in {37, 40, 67}:
    ax.set_xticklabels([])
    tier_count = {37: 5, 40: 4, 67: 5}[cfg.figure]
    tier_step = {37: 0.055, 40: 0.060, 67: 0.052}[cfg.figure]
    for index, value in enumerate(sub_visual.columns):
      tier = index % tier_count
      artist = ax.text(
        index + 0.5,
        -0.025 - tier * tier_step,
        format_x_label(value, cfg.figure),
        transform=ax.get_xaxis_transform(),
        rotation=45,
        ha="right",
        va="top",
        rotation_mode="anchor",
        fontsize=x_font,
        linespacing=0.94,
        clip_on=False,
      )
      x_label_artists.append(artist)
  else:
    ax.set_xticklabels([format_x_label(value, cfg.figure) for value in sub_visual.columns], rotation=rotation, ha=ha, va="top", rotation_mode="anchor", fontsize=x_font, linespacing=0.96)
    x_label_artists = list(ax.get_xticklabels())
  y_labels = [wrap(labels.loc[module_id, "Module_label"], cfg.y_wrap) for module_id in sub_visual.index]
  ax.set_yticks(np.arange(n_rows) + 0.5)
  ax.set_yticklabels(y_labels, fontsize=cfg.y_font, ha="right", va="center", linespacing=1.00)
  ax.tick_params(axis="both", length=0, pad=4)
  if cfg.figure == 37:
    ax.set_xlabel("")
    xlabel_artist = fig.text((left + right) / 2, 0.195, cfg.x_label, fontsize=14.0, fontweight="bold", ha="center", va="center")
  elif cfg.figure == 40:
    ax.set_xlabel("")
    xlabel_artist = fig.text((left + right) / 2, 0.185, cfg.x_label, fontsize=14.0, fontweight="bold", ha="center", va="center")
  elif cfg.figure == 67:
    ax.set_xlabel("")
    xlabel_artist = fig.text((left + right) / 2, 0.175, cfg.x_label, fontsize=14.0, fontweight="bold", ha="center", va="center")
  else:
    ax.set_xlabel(cfg.x_label, fontsize=14.0, fontweight="bold", labelpad=12)
    xlabel_artist = ax.xaxis.label
  ax.set_ylabel("")
  ylabel_artist = fig.text(0.014, (bottom + top) / 2, "KEGG/KEMET module and metabolic pathway", fontsize=13.5, fontweight="bold", rotation=90, ha="center", va="center")
  title = f"{cfg.title} — Panel {panel_id} of P{panel_total:03d}"
  title_artist = fig.text(0.035, 0.970, title, fontsize=16.0, fontweight="bold", ha="left", va="top")
  legend_y = 0.018 if cfg.figure == 38 else 0.012
  legend = fig.legend(handles=legend_handles(), title="KEMET module status", loc="lower center", bbox_to_anchor=(0.5, legend_y), ncol=3, frameon=False, fontsize=12.5, title_fontsize=13.0, handlelength=1.5, columnspacing=2.0)
  for spine in ax.spines.values():
    spine.set_visible(False)
  fig.canvas.draw()
  renderer = fig.canvas.get_renderer()
  fig_box = fig.bbox
  ax_box = ax.get_window_extent(renderer)
  legend_box = legend.get_window_extent(renderer)
  title_box = title_artist.get_window_extent(renderer)
  outside = []
  for artist in [title_artist, xlabel_artist, ylabel_artist, *x_label_artists, *ax.get_yticklabels(), *legend.get_texts()]:
    if not artist.get_visible() or not artist.get_text():
      continue
    box = artist.get_window_extent(renderer)
    if box.x0 < fig_box.x0 - 2 or box.y0 < fig_box.y0 - 2 or box.x1 > fig_box.x1 + 2 or box.y1 > fig_box.y1 + 2:
      outside.append({"text": artist.get_text().replace("\n", " | ")[:160], "bbox": [box.x0, box.y0, box.x1, box.y1]})
  layout = {
    "figure_inches": [width, height],
    "figure_pixels_at_300dpi": [round(width * 300), round(height * 300)],
    "rows": n_rows, "columns": n_cols,
    "row_range": [r0 + 1, r1], "column_range": [c0 + 1, c1],
    "x_font_pt": x_font, "y_font_pt": cfg.y_font, "x_rotation_deg": rotation,
    "title_font_pt": 16.0, "axis_title_font_pt": 14.0, "legend_font_pt": 12.5,
    "legend_below_heatmap": bool(legend_box.y1 < ax_box.y0),
    "legend_inside_figure": bool(legend_box.x0 >= fig_box.x0 and legend_box.y0 >= fig_box.y0 and legend_box.x1 <= fig_box.x1 and legend_box.y1 <= fig_box.y1),
    "title_above_heatmap": bool(title_box.y0 >= ax_box.y1 - 2),
    "all_text_inside_figure": not outside, "outside_texts": outside,
  }
  if not all([layout["legend_below_heatmap"], layout["legend_inside_figure"], layout["title_above_heatmap"], layout["all_text_inside_figure"]]):
    raise RuntimeError(f"Layout validation failed for S{cfg.figure} {panel_id}: {layout}")
  return fig, layout


def render_integral(cfg: FigureConfig, visual: pd.DataFrame, codes: pd.DataFrame, labels: pd.DataFrame) -> tuple[plt.Figure, dict[str, object]]:
  n_rows, n_cols = codes.shape
  width = max(15.5, 5.8 + n_cols * 0.34)
  height = max(10.5, 5.2 + n_rows * 0.30)
  fig = plt.figure(figsize=(width, height), facecolor='white')
  left = min(0.34, max(0.18, 4.8 / width))
  bottom = min(0.30, max(0.12, 3.8 / height))
  ax = fig.add_axes([left, bottom, 0.985 - left, 0.93 - bottom])
  cmap = ListedColormap([RED, BLUE, GREEN])
  cmap.set_bad(WHITE)
  norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5], cmap.N)
  ax.pcolormesh(np.arange(n_cols + 1), np.arange(n_rows + 1), np.ma.masked_invalid(codes.to_numpy(float)), cmap=cmap, norm=norm, shading='flat', edgecolors='white', linewidth=0.2, rasterized=True)
  ax.set_xlim(0, n_cols); ax.set_ylim(n_rows, 0)
  x_width = 12 if cfg.figure == 38 else 10
  x_font = 10.5 if cfg.figure == 38 else (8.8 if cfg.figure == 40 else 8.4)
  ax.set_xticks(np.arange(n_cols) + 0.5)
  ax.set_xticklabels([format_x_label(x, x_width) for x in visual.columns], rotation=0, ha='center', va='top', fontsize=x_font, linespacing=0.94)
  ax.set_yticks(np.arange(n_rows) + 0.5)
  ax.set_yticklabels([wrap(labels.loc[x, 'Module_label'], cfg.y_wrap) for x in visual.index], fontsize=10.5)
  ax.tick_params(axis='both', length=0, pad=2)
  ax.set_xlabel(cfg.x_label, fontsize=15, fontweight='bold', labelpad=13)
  ax.set_ylabel('KEGG/KEMET module and metabolic pathway', fontsize=15, fontweight='bold', labelpad=8)
  fig.text(left, 0.985, f"{cfg.title} — integral application view", ha='left', va='top', fontsize=18, fontweight='bold')
  legend = fig.legend(handles=legend_handles(), title='KEMET module status', loc='lower center', bbox_to_anchor=(0.5, 0.012), ncol=3, frameon=False, fontsize=13, title_fontsize=14)
  for spine in ax.spines.values(): spine.set_visible(False)
  fig.canvas.draw()
  renderer = fig.canvas.get_renderer()
  layout = {'figure_inches': [width, height], 'rows': n_rows, 'columns': n_cols, 'legend_below_heatmap': bool(legend.get_window_extent(renderer).y1 < ax.get_window_extent(renderer).y0), 'minimum_axis_font_pt': min(10.5, x_font)}
  return fig, layout



def save_contact_sheet(panel_pngs: list[Path], target: Path, dpi: int = 300) -> dict[str, object]:
  images = [Image.open(path).convert("RGB") for path in panel_pngs]
  try:
    width = max(image.width for image in images)
    gap = 30
    scaled = []
    for image in images:
      if image.width == width:
        scaled.append(image)
      else:
        scaled.append(image.resize((width, round(image.height * width / image.width)), Image.Resampling.LANCZOS))
    height = sum(image.height for image in scaled) + gap * (len(scaled) - 1)
    canvas = Image.new("RGB", (width, height), "white")
    y = 0
    for image in scaled:
      canvas.paste(image, (0, y))
      y += image.height + gap
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target, "PNG", dpi=(dpi, dpi), optimize=True)
  finally:
    for image in images:
      image.close()
  svg = target.with_suffix(".svg")
  payload = base64.b64encode(target.read_bytes()).decode("ascii")
  with Image.open(target) as opened:
    width, height = opened.size
  svg.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}"><image href="data:image/png;base64,{payload}" width="{width}" height="{height}"/></svg>', encoding="utf-8")
  return {
    "png": {"path": str(target), "sha256": sha256(target), "size": target.stat().st_size, "dimensions": [width, height]},
    "svg": {"path": str(svg), "sha256": sha256(svg), "size": svg.stat().st_size},
  }

def cleanup(stem: str, dirs: list[Path]) -> None:
  for directory in dirs:
    directory.mkdir(parents=True, exist_ok=True)
    for path in directory.glob(f"{stem}*"):
      if path.is_file():
        path.unlink()


def render_heatmap(cfg: FigureConfig, root: Path, article_root: Path | None, catalog: pd.DataFrame, dpi: int) -> tuple[dict[str, object], pd.DataFrame, pd.DataFrame]:
  source_path = root / "data" / "final_kegg_st8_update" / cfg.source_file
  retained, visual, codes, labels = load_thematic_matrix(source_path, catalog)
  # Semantic orientation is explicit and must never be changed by pagination.
  if any(re.match(r"^M\d{5}\b", str(col)) for col in retained.columns):
    raise RuntimeError(f"S{cfg.figure}: module identifiers found in columns; transposition is invalid")
  if not all(re.match(r"^M\d{5}\b", str(idx)) for idx in retained.index):
    raise RuntimeError(f"S{cfg.figure}: non-module identifiers found in rows")
  row_blocks = [(x, min(x + cfg.rows_per_block, len(retained))) for x in range(0, len(retained), cfg.rows_per_block)]
  col_blocks = [(x, min(x + cfg.cols_per_block, retained.shape[1])) for x in range(0, retained.shape[1], cfg.cols_per_block)]
  combinations = [(r, c) for r in row_blocks for c in col_blocks]
  final_dir = root / "outputs" / "final_publication_figures"
  app_dir = root / "outputs" / "app_supplementary_figures"
  article_dir = article_root / "03_Supplementary_Figures" if article_root else None
  sync_dirs = [final_dir, app_dir] + ([article_dir] if article_dir else [])
  cleanup(cfg.stem, sync_dirs)
  derived = root / "data" / "final_publication_derived"
  derived.mkdir(parents=True, exist_ok=True)
  orientation_audit = {
    "figure": f"S{cfg.figure}",
    "input_file": str(source_path.relative_to(root)),
    "rows": int(retained.shape[0]),
    "columns": int(retained.shape[1]),
    "row_semantics": "KEGG/KEMET modules and metabolic pathways",
    "column_semantics": cfg.x_label,
    "first_row_identifier": str(retained.index[0]),
    "last_row_identifier": str(retained.index[-1]),
    "first_column_identifier": str(retained.columns[0]),
    "last_column_identifier": str(retained.columns[-1]),
    "orientation": "observations on x-axis; modules on y-axis",
    "validation": "PASS",
  }
  (root / "validation").mkdir(parents=True, exist_ok=True)
  (root / "validation" / f"S{cfg.figure}_orientation_audit.json").write_text(json.dumps(orientation_audit, indent=2), encoding="utf-8")

  meta = catalog.set_index("Module_ID").loc[retained.index]
  status_table = pd.concat([meta[["Module_name", "Biogeochemical_cycle", "Relation_to_iron", "Table_S8_biomarker_KOs", "Reason_for_inclusion"]], retained], axis=1)
  status_table.to_csv(derived / f"{cfg.stem}_thematic_status.csv")
  app_status = retained.copy()
  app_status.insert(0, "KEGG module", [labels.loc[module_id, "Module_label"] for module_id in retained.index])
  app_status.to_csv(derived / f"{cfg.stem}_thematic_app_status.csv", index=False)
  visual.to_csv(derived / f"{cfg.stem}_thematic_visual_categories.csv")

  panels: list[dict[str, object]] = []
  panel_pngs: list[Path] = []
  for index, (row_block, col_block) in enumerate(combinations, start=1):
    panel_id = f"P{index:03d}"
    fig, layout = render_panel(cfg, visual, codes, labels, panel_id, len(combinations), row_block, col_block)
    outputs = save_png_pdf_svg(fig, final_dir / f"{cfg.stem}_{panel_id}", dpi)
    plt.close(fig)
    panel_png = final_dir / f"{cfg.stem}_{panel_id}.png"
    panel_pngs.append(panel_png)
    for ext in ("png", "pdf", "svg"):
      source = final_dir / f"{cfg.stem}_{panel_id}.{ext}"
      if article_dir: shutil.copy2(source, article_dir / source.name)
    panels.append({"panel": panel_id, "row_block": list(row_block), "column_block": list(col_block), "layout": layout, "outputs": outputs})

  # Multipage manuscript PDF.
  rgb = [Image.open(path).convert("RGB") for path in panel_pngs]
  multipage = final_dir / f"{cfg.stem}_multipage.pdf"
  rgb[0].save(multipage, save_all=True, append_images=rgb[1:], resolution=float(dpi))
  for image in rgb:
    image.close()

  # The base image shown in the application is one scrollable contact sheet
  # composed from the exact manuscript panels. The app therefore cannot show a
  # different static result from the article.
  contact_outputs = save_contact_sheet(panel_pngs, final_dir / f"{cfg.stem}.png", dpi)
  shutil.copy2(multipage, final_dir / f"{cfg.stem}.pdf")
  for directory in [app_dir] + ([article_dir] if article_dir else []):
    shutil.copy2(final_dir / f"{cfg.stem}.png", directory / f"{cfg.stem}.png")
    shutil.copy2(final_dir / f"{cfg.stem}.svg", directory / f"{cfg.stem}.svg")
    shutil.copy2(multipage, directory / f"{cfg.stem}.pdf")
    shutil.copy2(multipage, directory / multipage.name)
  app_outputs = contact_outputs
  app_layout = {"source": "exact manuscript panel contact sheet", "panel_count": len(panel_pngs), "same_panels_as_article": True}

  # Cell-level audit for every displayed state.
  audit_rows = []
  panel_lookup = {}
  for index, (rb, cb) in enumerate(combinations, start=1):
    pid = f"P{index:03d}"
    for ri in range(*rb):
      for ci in range(*cb):
        panel_lookup[(ri, ci)] = pid
  for ri, module_id in enumerate(retained.index):
    for ci, sample in enumerate(retained.columns):
      original = retained.iat[ri, ci]
      visual_value = visual.iat[ri, ci]
      audit_rows.append({
        "Figure": f"S{cfg.figure}",
        "Module_ID": module_id,
        "Module_name": meta.loc[module_id, "Module_name"],
        "Biogeochemical_cycle": meta.loc[module_id, "Biogeochemical_cycle"],
        "Relation_to_iron": meta.loc[module_id, "Relation_to_iron"],
        "Table_S8_biomarker_KOs": meta.loc[module_id, "Table_S8_biomarker_KOs"],
        "Reason_for_inclusion": meta.loc[module_id, "Reason_for_inclusion"],
        "Sample_or_MAG": sample,
        "Original_status": original,
        "Displayed_visual_class": visual_value,
        "Color_hex": VISUAL_COLORS.get(visual_value, WHITE),
        "Panel": panel_lookup[(ri, ci)],
        "Row_order": ri + 1,
        "Column_order": ci + 1,
        "Source_file": cfg.source_file,
        "Selection_script": "scripts/generate_s38_s41_module_figures.py",
        "Selection_rule": "Thematic catalogue then at least one Complete; display every original state in retained rows.",
      })
  audit = pd.DataFrame(audit_rows)
  audit.to_csv(derived / f"{cfg.stem}_thematic_cell_classifications.csv", index=False)
  counts = visual.stack(dropna=False).value_counts().to_dict()
  original_counts = retained.stack(dropna=False).value_counts().to_dict()
  record = {
    "figure": f"S{cfg.figure}",
    "config": asdict(cfg),
    "source": str(source_path.relative_to(root)),
    "source_sha256": sha256(source_path),
    "thematic_catalog_rows": int(len(catalog)),
    "thematic_rows_available": int(len(catalog[catalog.Module_ID.isin(pd.read_csv(source_path).iloc[:, 0].astype(str).str.extract(r'(M\d{5})', expand=False))])),
    "rows_displayed_after_complete_rule": int(len(retained)),
    "columns_displayed": int(retained.shape[1]),
    "panel_count": int(len(combinations)),
    "panels": panels,
    "application_integral": {"layout": app_layout, "outputs": app_outputs},
    "visual_counts": {x: int(counts.get(x, 0)) for x in (*LEGEND_ORDER, "Missing data")},
    "original_counts": {str(k): int(v) for k, v in original_counts.items()},
    "audit_rows": int(len(audit)),
    "multipage_pdf": {"path": str(multipage.relative_to(root)), "sha256": sha256(multipage)},
  }
  return record, visual, status_table


def render_s41(root: Path, article_root: Path | None, s40_visual: pd.DataFrame, dpi: int) -> dict[str, object]:
  stem = "SupplementaryFigure41_ST8_external_iron_rich_module_status_summary_3state_barplot"
  final_dir = root / "outputs" / "final_publication_figures"
  app_dir = root / "outputs" / "app_supplementary_figures"
  article_dir = article_root / "03_Supplementary_Figures" if article_root else None
  cleanup(stem, [final_dir, app_dir] + ([article_dir] if article_dir else []))
  summary = []
  for sample in s40_visual.columns:
    counts = s40_visual[sample].value_counts()
    summary.append({"Record": sample, "Complete": int(counts.get("Complete", 0)), "1 block missing": int(counts.get("1 block missing", 0)), "Incomplete": int(counts.get("Incomplete", 0)), "Missing data": int(counts.get("Missing data", 0))})
  summary_df = pd.DataFrame(summary)
  derived = root / "data" / "final_publication_derived"
  derived.mkdir(parents=True, exist_ok=True)
  source_path = derived / f"{stem}_source.csv"
  summary_df.to_csv(source_path, index=False)
  blocks = [(x, min(x + 34, len(summary_df))) for x in range(0, len(summary_df), 34)]
  panel_pngs = []
  panel_records = []
  for index, (start, end) in enumerate(blocks, 1):
    panel_id = f"P{index:03d}"
    part = summary_df.iloc[start:end].reset_index(drop=True)
    fig = plt.figure(figsize=(15.20, 9.45), facecolor="white")
    ax = fig.add_axes([0.285, 0.19, 0.685, 0.68])
    y = np.arange(len(part)); left = np.zeros(len(part))
    for state in ("Incomplete", "1 block missing", "Complete"):
      vals = part[state].to_numpy(float)
      ax.barh(y, vals, left=left, color=VISUAL_COLORS[state], edgecolor="white", linewidth=0.35, height=0.76)
      left += vals
    # Preserve each complete record label on one line. Wrapping these short (<=42-character)
    # labels created two-line tick labels that overlapped vertically at 100% zoom.
    ax.set_yticks(y, labels=[str(x) for x in part.Record], fontsize=11.5)
    ax.invert_yaxis()
    ax.set_xlabel("Number of displayed thematic\nKEGG/KEMET modules", fontsize=13.5, fontweight="bold", labelpad=10)
    ax.tick_params(axis="x", labelsize=11.0)
    ax.spines[["top", "right"]].set_visible(False)
    title = fig.text(0.035, 0.965, f"External iron-rich record module-status summary — Panel {panel_id} of P{len(blocks):03d}", fontsize=16.0, fontweight="bold", ha="left", va="top", wrap=True)
    legend = fig.legend(handles=legend_handles(), title="KEMET module status", loc="lower center", bbox_to_anchor=(0.5, 0.025), ncol=3, frameon=False, fontsize=12.5, title_fontsize=13.0)
    fig.canvas.draw(); renderer = fig.canvas.get_renderer(); figbox=fig.bbox; axbox=ax.get_window_extent(renderer); legbox=legend.get_window_extent(renderer); titlebox=title.get_window_extent(renderer)
    outside=[]
    for artist in [title,ax.xaxis.label,*ax.get_xticklabels(),*ax.get_yticklabels(),*legend.get_texts()]:
      if not artist.get_text(): continue
      b=artist.get_window_extent(renderer)
      if b.x0 < figbox.x0-2 or b.y0 < figbox.y0-2 or b.x1 > figbox.x1+2 or b.y1 > figbox.y1+2: outside.append(artist.get_text()[:100])
    ytick_boxes = [tick.get_window_extent(renderer) for tick in ax.get_yticklabels() if tick.get_visible() and tick.get_text()]
    ytick_nonoverlap = all(
      not (a.x0 < b.x1 and a.x1 > b.x0 and a.y0 < b.y1 and a.y1 > b.y0)
      for i, a in enumerate(ytick_boxes) for b in ytick_boxes[i + 1:]
    )
    layout={"figure_inches":[15.20,9.45],"x_font_pt":11.0,"y_font_pt":11.5,"title_font_pt":16.0,"legend_font_pt":12.5,"legend_below_plot":bool(legbox.y1<axbox.y0),"title_above_plot":bool(titlebox.y0>=axbox.y1-2),"all_text_inside_figure":not outside,"ytick_labels_nonoverlapping":ytick_nonoverlap,"outside_texts":outside}
    if not all([layout["legend_below_plot"],layout["title_above_plot"],layout["all_text_inside_figure"],layout["ytick_labels_nonoverlapping"]]): raise RuntimeError(f"S41 layout failed: {layout}")
    outputs=save_png_pdf_svg(fig, final_dir/f"{stem}_{panel_id}", dpi); plt.close(fig)
    panel_png=final_dir/f"{stem}_{panel_id}.png";panel_pngs.append(panel_png)
    for ext in ("png","pdf","svg"):
      if article_dir: shutil.copy2(final_dir/f"{stem}_{panel_id}.{ext}",article_dir/f"{stem}_{panel_id}.{ext}")
    panel_records.append({"panel":panel_id,"records":[start+1,end],"layout":layout,"outputs":outputs})
  for ext in ("png","pdf","svg"):
    shutil.copy2(final_dir/f"{stem}_P001.{ext}", final_dir/f"{stem}.{ext}")
    shutil.copy2(final_dir/f"{stem}_P001.{ext}", app_dir/f"{stem}.{ext}")
    if article_dir: shutil.copy2(final_dir/f"{stem}_P001.{ext}",article_dir/f"{stem}.{ext}")
  rgb=[Image.open(x).convert('RGB') for x in panel_pngs]; mp=final_dir/f"{stem}_multipage.pdf"; rgb[0].save(mp,save_all=True,append_images=rgb[1:],resolution=float(dpi)); [x.close() for x in rgb]
  if article_dir: shutil.copy2(mp,article_dir/mp.name)
  return {"figure":"S41","source":str(source_path.relative_to(root)),"rows_displayed":int(s40_visual.shape[0]),"records_displayed":int(s40_visual.shape[1]),"panel_count":len(blocks),"panels":panel_records,"multipage_pdf":{"path":str(mp.relative_to(root)),"sha256":sha256(mp)}}


def write_supplementary_sources(root: Path, catalog: pd.DataFrame, status_tables: dict[int, pd.DataFrame]) -> None:
  tables = root / "tables"
  tables.mkdir(parents=True, exist_ok=True)
  catalog.to_csv(tables / "Supplementary_Table_14_thematic_module_subset_catalog.csv", index=False)
  for figure, frame in status_tables.items():
    frame.to_csv(tables / f"Supplementary_Table_14_S{figure}_thematic_module_status.csv")
  metadata = pd.DataFrame([
    {"Field":"Purpose","Value":"Additional supplementary data documenting the thematic module subset used only for presentation in S37, S38, S40, S41 and S67."},
    {"Field":"Original matrices","Value":"Preserved unchanged under data/final_kegg_st8_update/."},
    {"Field":"Selection stage 1","Value":"Explicit thematic catalogue based on Table S8 KO biomarkers and requested nitrogen, phosphorus, carbon, methane, sulfur, photosynthesis and iron themes."},
    {"Field":"Selection stage 2","Value":"Within each matrix, retain a thematic module only when at least one displayed record is Complete."},
    {"Field":"Cell display rule","Value":"Display every original state in each retained row: Complete, 1 block missing, and Incomplete; original 2 blocks missing uses the red Incomplete visual class; only true missing data are white."},
    {"Field":"Script","Value":"scripts/generate_s38_s41_module_figures.py"},
  ])
  metadata.to_csv(tables / "Supplementary_Table_14_selection_metadata.csv", index=False)


def parse_args() -> argparse.Namespace:
  parser=argparse.ArgumentParser()
  parser.add_argument('--base-dir',type=Path,default=Path(__file__).resolve().parents[1])
  parser.add_argument('--article-root',type=Path)
  parser.add_argument('--png-dpi',type=int,default=300)
  parser.add_argument('--only',choices=['38','41'],action='append')
  return parser.parse_args()


def main() -> int:
  args=parse_args(); root=args.base_dir.resolve(); article_root=args.article_root.resolve() if args.article_root else None
  selected={int(x) for x in args.only} if args.only else {38,41}
  catalog=build_thematic_catalog(root)
  derived=root/'data'/'final_publication_derived'; derived.mkdir(parents=True,exist_ok=True)
  catalog.to_csv(derived/'thematic_module_selection_catalog.csv',index=False)
  records=[]; matrices={}; status_tables={}
  for cfg in CONFIGS:
    if cfg.figure not in selected and not (cfg.figure==40 and 41 in selected): continue
    print(f"Generating S{cfg.figure} from {cfg.source_file}",flush=True)
    record,visual,status=render_heatmap(cfg,root,article_root,catalog,args.png_dpi)
    matrices[cfg.figure]=visual; status_tables[cfg.figure]=status
    if cfg.figure in selected: records.append(record)
  if 41 in selected:
    if 40 not in matrices:
      cfg=next(x for x in CONFIGS if x.figure==40);_,matrices[40],_,_=load_thematic_matrix(root/'data'/'final_kegg_st8_update'/cfg.source_file,catalog)
    print('Generating S41 from the thematic S40 matrix',flush=True)
    records.append(render_s41(root,article_root,matrices[40],args.png_dpi))
  if selected=={38,41}: pass
  validation=root/'validation';validation.mkdir(parents=True,exist_ok=True)
  report={"script":"scripts/generate_s38_s41_module_figures.py","executed_utc":datetime.now(timezone.utc).isoformat(),"python":sys.version,"matplotlib":matplotlib.__version__,"pandas":pd.__version__,"numpy":np.__version__,"thematic_module_count":int(len(catalog)),"thematic_cycles":list(CYCLE_ORDER),"row_rule":"thematic catalogue then at least one Complete in the displayed matrix","cell_rule":"all original states displayed; no valid state blanked","colors":VISUAL_COLORS,"records":records}
  path=validation/'module_figures_v11_execution.json';path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(path)
  return 0

if __name__=='__main__':
  raise SystemExit(main())
