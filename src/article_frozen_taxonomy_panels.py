from __future__ import annotations

"""Interactive Figure 4/5 panels loaded from frozen article source tables.

No NMDS or RDA is recomputed here. The module renders the exact matrices,
coordinates, vectors and statistics packaged with the authoritative article
submission, so interactive panels and downloads stay tied to the manuscript.
"""

import json
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATHS = {
  "Bacteria": BASE_DIR / "data" / "article_frozen_taxonomy_bacteria.json",
  "Archaea": BASE_DIR / "data" / "article_frozen_taxonomy_archaea.json",
}
LAKE_COLORS = {"AM": "#0072B2", "TIA": "#E69F00", "TI": "#009E73", "VI": "#CC79A7"}
SEASON_SYMBOLS = {"Dry": "circle", "Rainy": "square"}
AUTHORITY = "ARTICLE_FINAL_ISME_SUBMISSION_Leandrov27-julho FINAL_SUBMISSION_FILES"


@lru_cache(maxsize=2)
def _payload(domain: str) -> dict:
  canonical = "Archaea" if str(domain).casefold().startswith("arch") else "Bacteria"
  data = json.loads(DATA_PATHS[canonical].read_text(encoding="utf-8"))
  if data.get("authority") != AUTHORITY or data.get("domain") != canonical:
    raise RuntimeError("Unexpected frozen taxonomy authority or domain")
  return data


def frozen_taxonomy_domain_data(domain: str) -> dict[str, object]:
  raw = _payload(domain)
  return {
    "domain": raw["domain"],
    "profile": pd.DataFrame(raw["profile"], columns=raw["profile_columns"]),
    "nmds": pd.DataFrame(raw["nmds"]),
    "rda_sites": pd.DataFrame(raw["rda_sites"]),
    "rda_environment_vectors": pd.DataFrame(raw["rda_environment_vectors"]),
    "rda_taxon_vectors": pd.DataFrame(raw["rda_taxon_vectors"]),
    "statistics": pd.DataFrame([raw["statistics"]]),
    "display": dict(raw["display"]),
    "palette": dict(raw["palette"]),
    "source_files": list(raw["source_files"]),
  }


def _bar_traces(fig: go.Figure, profile: pd.DataFrame, samples: list[str], palette: dict[str, str], col: int) -> None:
  for _, record in profile.iterrows():
    taxon = str(record["taxon"])
    values = [float(record[sample]) for sample in samples]
    fig.add_trace(
      go.Bar(
        x=values, y=samples, orientation="h", name=taxon,
        legendgroup=f"genus::{taxon}", showlegend=col == 1,
        marker={"color": palette.get(taxon, "#666666"), "line": {"color": "white", "width": 0.35}},
        hovertemplate=("<b>%{y}</b><br>Genus: " + taxon + "<br>Relative abundance: %{x:.8f}%<extra></extra>"),
      ),
      row=1, col=col,
    )


def _nmds_traces(fig: go.Figure, scores: pd.DataFrame) -> None:
  for lake in ["AM", "TIA", "TI", "VI"]:
    for season in ["Dry", "Rainy"]:
      subset = scores[(scores["Lake"].astype(str) == lake) & (scores["Season"].astype(str) == season)]
      if subset.empty:
        continue
      fig.add_trace(
        go.Scatter(
          x=subset["NMDS1"].astype(float), y=subset["NMDS2"].astype(float),
          mode="markers+text", text=subset["Sample"].astype(str), textposition="top right",
          textfont={"size": 12, "family": "Arial Black"}, name=f"{lake} — {season}",
          legendgroup=f"ordination::{lake}::{season}",
          marker={"size": 11, "color": LAKE_COLORS[lake], "symbol": SEASON_SYMBOLS[season], "line": {"color": "black", "width": 1}},
          customdata=subset[["Sample", "Lake", "Season"]].astype(str).to_numpy(),
          hovertemplate=("Sample: %{customdata[0]}<br>Lake: %{customdata[1]}<br>Season: %{customdata[2]}"
                         "<br>NMDS1: %{x:.12g}<br>NMDS2: %{y:.12g}<extra></extra>"),
        ),
        row=2, col=1,
      )


def _rda_traces(fig: go.Figure, sites: pd.DataFrame, env: pd.DataFrame, taxa: pd.DataFrame, palette: dict[str, str]) -> tuple[float, float, float, float]:
  for lake in ["AM", "TIA", "TI", "VI"]:
    subset = sites[sites["Lake"].astype(str) == lake]
    if subset.empty:
      continue
    fig.add_trace(
      go.Scatter(
        x=subset["RDA1"].astype(float), y=subset["RDA2"].astype(float),
        mode="markers+text", text=subset["Sample"].astype(str), textposition="top right",
        textfont={"size": 12, "family": "Arial Black"}, name=f"RDA — {lake}",
        legendgroup=f"rda::{lake}", showlegend=False,
        marker={"size": 12, "color": LAKE_COLORS[lake], "line": {"color": "black", "width": 1}},
        customdata=subset[["Sample", "Lake"]].astype(str).to_numpy(),
        hovertemplate=("Site: %{customdata[0]}<br>Lake: %{customdata[1]}"
                       "<br>RDA1: %{x:.12g}<br>RDA2: %{y:.12g}<extra></extra>"),
      ),
      row=2, col=2,
    )

  extent = max(float(np.nanmax(np.abs(sites[["RDA1", "RDA2"]].to_numpy(float)))), 1e-6)
  env_scale, tax_scale = extent * 0.80, extent * 0.68
  xvals = sites["RDA1"].astype(float).tolist() + [0.0]
  yvals = sites["RDA2"].astype(float).tolist() + [0.0]

  for _, item in env.iterrows():
    x, y = float(item["RDA1"]) * env_scale, float(item["RDA2"]) * env_scale
    fig.add_annotation(
      x=x, y=y, ax=0, ay=0, xref="x4", yref="y4", axref="x4", ayref="y4",
      text=str(item["Variable"]), showarrow=True, arrowhead=2, arrowsize=1,
      arrowwidth=1.6, arrowcolor="#333333",
      font={"size": 13, "color": "#222222", "family": "Arial Black"},
      bgcolor="rgba(255,255,255,0.78)", borderpad=1,
    )
    xvals.append(x * 1.28); yvals.append(y * 1.28)

  items: list[tuple[str, float, float, str]] = []
  for _, item in taxa.iterrows():
    name = str(item["Genus"])
    items.append((name, float(item["RDA1"]) * tax_scale, float(item["RDA2"]) * tax_scale, palette.get(name, "#333333")))

  gap = max(extent * 0.14, 0.010)
  for side in (-1, 1):
    selected = sorted([item for item in items if (item[1] < 0) == (side < 0)], key=lambda value: value[2])
    previous: float | None = None
    for name, x, y, color in selected:
      label_y = y * 1.18
      if previous is not None and label_y - previous < gap:
        label_y = previous + gap
      previous = label_y
      label_x = x * 1.22 + side * extent * 0.05
      fig.add_annotation(
        x=x, y=y, ax=label_x, ay=label_y, xref="x4", yref="y4", axref="x4", ayref="y4",
        text=name, showarrow=True, arrowhead=0, arrowwidth=0.8, arrowcolor=color,
        font={"size": 12, "color": color, "family": "Arial Black"},
        bgcolor="rgba(255,255,255,0.86)", borderpad=1,
        xanchor="left" if label_x >= 0 else "right",
      )
      xvals.extend([x, label_x]); yvals.extend([y, label_y])

  xmin, xmax, ymin, ymax = min(xvals), max(xvals), min(yvals), max(yvals)
  return (
    xmin - max((xmax - xmin) * 0.16, extent * 0.22),
    xmax + max((xmax - xmin) * 0.16, extent * 0.22),
    ymin - max((ymax - ymin) * 0.18, extent * 0.22),
    ymax + max((ymax - ymin) * 0.18, extent * 0.22),
  )


def article_frozen_taxonomy_figure(domain: str) -> tuple[go.Figure, dict[str, pd.DataFrame]]:
  data = frozen_taxonomy_domain_data(domain)
  canonical = str(data["domain"])
  profile, scores = data["profile"], data["nmds"]
  sites, env, taxa = data["rda_sites"], data["rda_environment_vectors"], data["rda_taxon_vectors"]
  stats, display, palette = data["statistics"].iloc[0], data["display"], data["palette"]
  samples = [column for column in profile.columns if column != "taxon"]
  dry, rainy = [s for s in samples if s.endswith(".D")], [s for s in samples if s.endswith(".R")]

  fig = make_subplots(
    rows=2, cols=2, vertical_spacing=0.16, horizontal_spacing=0.13,
    subplot_titles=(
      "<b>A  Dry-season genus profiles</b>", "<b>B  Rainy-season genus profiles</b>",
      f"<b>C  Bray-Curtis NMDS (stress = {float(stats['NMDS_stress']):.3f})</b>",
      f"<b>D  RDA biplot (R² = {float(stats['RDA_R2']):.2f}; P = {float(stats['RDA_p']):.3f})</b>",
    ),
  )
  _bar_traces(fig, profile, dry, palette, 1)
  _bar_traces(fig, profile, rainy, palette, 2)
  _nmds_traces(fig, scores)
  rda_range = _rda_traces(fig, sites, env, taxa, palette)

  fig.update_xaxes(range=[0, 100], title_text="Relative abundance (%)", row=1, col=1)
  fig.update_xaxes(range=[0, 100], title_text="Relative abundance (%)", row=1, col=2)
  fig.update_yaxes(categoryorder="array", categoryarray=dry, autorange="reversed", row=1, col=1)
  fig.update_yaxes(categoryorder="array", categoryarray=rainy, autorange="reversed", row=1, col=2)
  fig.update_xaxes(title_text="NMDS1", zeroline=True, zerolinecolor="#AAAAAA", row=2, col=1)
  fig.update_yaxes(title_text="NMDS2", zeroline=True, zerolinecolor="#AAAAAA", row=2, col=1)
  fig.update_xaxes(title_text=f"RDA1 ({float(display['rda1_percent']):.1f}% constrained variation)",
                   range=[rda_range[0], rda_range[1]], zeroline=True, zerolinecolor="#AAAAAA", row=2, col=2)
  fig.update_yaxes(title_text=f"RDA2 ({float(display['rda2_percent']):.1f}% constrained variation)",
                   range=[rda_range[2], rda_range[3]], zeroline=True, zerolinecolor="#AAAAAA", row=2, col=2)
  fig.update_layout(
    barmode="stack", height=1350, width=1750,
    margin={"l": 115, "r": 330, "t": 100, "b": 210},
    font={"family": "Arial, Helvetica, sans-serif", "size": 13, "color": "#111111"},
    legend={"title": {"text": "Genus / lake-season"}, "x": 1.01, "y": 1.0, "font": {"size": 11}},
    meta={"authority": AUTHORITY, "domain": canonical, "recomputed": False,
          "source_files": data["source_files"],
          "static_article_figure": "Figure4" if canonical == "Bacteria" else "Figure5"},
  )
  for annotation in fig.layout.annotations:
    annotation.font = {"size": 17, "family": "Arial Black", "color": "#111111"}
    annotation.xanchor = "left"

  return fig, {
    "genus_relative_abundance": profile.copy(), "nmds_scores": scores.copy(),
    "rda_site_scores": sites.copy(), "rda_environment_vectors": env.copy(),
    "rda_representative_genus_vectors": taxa.copy(),
    "ordination_statistics": data["statistics"].copy(),
  }
