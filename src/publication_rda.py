from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .publication_ordination import compute_nmds, compute_rda, domain_genus_matrix
from .sample_metadata import amazonian_sample_metadata
from .taxonomy_palette import build_palette, load_palette

LAKE_COLORS = {"AM": "#0072B2", "TIA": "#E69F00", "TI": "#009E73", "VI": "#CC79A7"}
SEASON_SYMBOLS = {"Dry": "circle", "Rainy": "square"}


def _normalise_domain(domain: str) -> str:
  return "Archaea" if str(domain).lower().startswith("arch") else "Bacteria"


def _copy_result(value: Any) -> Any:
  if isinstance(value, pd.DataFrame):
    return value.copy(deep=True)
  if isinstance(value, pd.Series):
    return value.copy(deep=True)
  if isinstance(value, dict):
    return {key: _copy_result(item) for key, item in value.items()}
  if isinstance(value, list):
    return [_copy_result(item) for item in value]
  if isinstance(value, tuple):
    return tuple(_copy_result(item) for item in value)
  if isinstance(value, np.ndarray):
    return value.copy()
  return value


@lru_cache(maxsize=4)
def _canonical_result_cached(base_dir_text: str, domain: str) -> dict[str, Any]:
  base_dir = Path(base_dir_text)
  canonical_domain = _normalise_domain(domain)
  relative = domain_genus_matrix(base_dir, canonical_domain, top_n=18)
  return {
    "relative": relative,
    "nmds": compute_nmds(relative, canonical_domain),
    "rda": compute_rda(base_dir, relative, canonical_domain),
  }


def canonical_ordination_result(base_dir: Path, domain: str = "Bacteria") -> dict[str, Any]:
  """Return a defensive copy of the exact article ordination result.

  The article generator and Streamlit application both call the scientific
  functions in :mod:`src.publication_ordination`. Results are cached only
  within the current Python process; no alternative calculation is used.
  """
  result = _canonical_result_cached(str(Path(base_dir).resolve()), _normalise_domain(domain))
  return _copy_result(result)


def _attach_publication_sample_metadata(frame: pd.DataFrame, pooled_sites: bool = False) -> pd.DataFrame:
  if frame is None or frame.empty or "Sample" not in frame.columns:
    return frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame()
  meta = amazonian_sample_metadata().copy()
  if pooled_sites:
    grouped = meta.groupby("site", as_index=False).agg({
      "sample.id": lambda values: "; ".join(map(str, values)),
      "IMG_JGI_analysis_project_id": lambda values: "; ".join(map(str, values)),
      "IMG_JGI_taxon_oid": lambda values: "; ".join(map(str, values)),
      "ENA_study_accession": "first",
      "sample_type": "first",
      "geographic_coordinates": "first",
    }).rename(columns={"site": "Sample", "sample.id": "Publication sample IDs"})
    return frame.merge(grouped, on="Sample", how="left")
  lookup = meta.rename(columns={"sample.id": "Sample"})[[
    "Sample", "IMG_JGI_analysis_project_id", "IMG_JGI_taxon_oid",
    "ENA_study_accession", "sample_type", "geographic_coordinates",
  ]]
  return frame.merge(lookup, on="Sample", how="left")


def _side_column_label_positions(
  frame: pd.DataFrame,
  x_col: str,
  y_col: str,
  xlim: tuple[float, float],
  ylim: tuple[float, float],
  *,
  gap_fraction: float = 0.055,
  inset_fraction: float = 0.035,
) -> pd.DataFrame:
  """Deterministically place labels in left/right side columns.

  This is the Plotly equivalent of the label-placement routine used by the
  article's Matplotlib script. Endpoints are preserved and label coordinates
  are added as ``label_x``/``label_y``.
  """
  if frame is None or frame.empty:
    return pd.DataFrame(columns=list(frame.columns) + ["label_x", "label_y"]) if isinstance(frame, pd.DataFrame) else pd.DataFrame()
  out = frame.copy().reset_index(drop=True)
  x = pd.to_numeric(out[x_col], errors="coerce").fillna(0.0).to_numpy(float)
  y = pd.to_numeric(out[y_col], errors="coerce").fillna(0.0).to_numpy(float)
  xmin, xmax = xlim
  ymin, ymax = ylim
  xr = max(xmax - xmin, 1e-12)
  yr = max(ymax - ymin, 1e-12)
  centre_x = float(np.median(x))
  gap = max(yr * gap_fraction, 1e-12)
  label_x = np.zeros(len(out), dtype=float)
  label_y = np.zeros(len(out), dtype=float)
  for side in (-1, 1):
    idx = np.where(x < centre_x)[0] if side < 0 else np.where(x >= centre_x)[0]
    if len(idx) == 0:
      continue
    ordered = idx[np.argsort(y[idx])]
    assigned: list[float] = []
    previous = ymin + yr * 0.06 - gap
    for row_index in ordered:
      target = float(np.clip(y[row_index], ymin + yr * 0.06, ymax - yr * 0.06))
      target = max(target, previous + gap)
      assigned.append(target)
      previous = target
    overflow = assigned[-1] - (ymax - yr * 0.06)
    if overflow > 0:
      assigned = [value - overflow for value in assigned]
    column_x = xmin + xr * inset_fraction if side < 0 else xmax - xr * inset_fraction
    for row_index, target_y in zip(ordered, assigned):
      label_x[row_index] = column_x
      label_y[row_index] = target_y
  out["label_x"] = label_x
  out["label_y"] = label_y
  return out


def _bounded_vector_labels(
  frame: pd.DataFrame,
  x_col: str,
  y_col: str,
  xlim: tuple[float, float],
  ylim: tuple[float, float],
) -> pd.DataFrame:
  if frame is None or frame.empty:
    return pd.DataFrame(columns=list(frame.columns) + ["label_x", "label_y"]) if isinstance(frame, pd.DataFrame) else pd.DataFrame()
  out = frame.copy().reset_index(drop=True)
  xmin, xmax = xlim
  ymin, ymax = ylim
  xr = max(xmax - xmin, 1e-12)
  yr = max(ymax - ymin, 1e-12)
  x = pd.to_numeric(out[x_col], errors="coerce").fillna(0.0).to_numpy(float)
  y = pd.to_numeric(out[y_col], errors="coerce").fillna(0.0).to_numpy(float)
  lx = np.clip(x * 1.12, xmin + xr * 0.07, xmax - xr * 0.07)
  ly = np.clip(y * 1.12, ymin + yr * 0.07, ymax - yr * 0.07)
  # Deterministic radial displacement for any near-overlapping labels.
  min_distance = max(float(np.hypot(xr, yr)) * 0.035, 1e-12)
  for i in range(len(lx)):
    for j in range(i):
      if float(np.hypot(lx[i] - lx[j], ly[i] - ly[j])) < min_distance:
        angle = (i + 1) * 2.399963229728653
        lx[i] = float(np.clip(lx[i] + xr * 0.045 * np.cos(angle), xmin + xr * 0.07, xmax - xr * 0.07))
        ly[i] = float(np.clip(ly[i] + yr * 0.045 * np.sin(angle), ymin + yr * 0.07, ymax - yr * 0.07))
  out["label_x"] = lx
  out["label_y"] = ly
  return out


def _add_point_labels(
  fig: go.Figure,
  frame: pd.DataFrame,
  x_col: str,
  y_col: str,
  label_col: str,
  xlim: tuple[float, float],
  ylim: tuple[float, float],
) -> None:
  labels = _side_column_label_positions(frame, x_col, y_col, xlim, ylim)
  for _, row in labels.iterrows():
    fig.add_annotation(
      x=float(row[x_col]), y=float(row[y_col]),
      ax=float(row["label_x"]), ay=float(row["label_y"]),
      xref="x", yref="y", axref="x", ayref="y",
      text=str(row[label_col]), showarrow=True, arrowhead=0,
      arrowwidth=0.75, arrowcolor="#606060",
      font={"size": 12, "color": "#111111"},
      bgcolor="rgba(255,255,255,0.86)", borderpad=2,
      xanchor="left" if float(row["label_x"]) < (xlim[0] + xlim[1]) / 2 else "right",
    )


def _add_environment_vectors(
  fig: go.Figure,
  vectors: pd.DataFrame,
  scale: float,
  xlim: tuple[float, float],
  ylim: tuple[float, float],
) -> pd.DataFrame:
  plot = vectors.reset_index().copy()
  label_col = "Variable" if "Variable" in plot.columns else plot.columns[0]
  plot["endpoint_x"] = pd.to_numeric(plot["RDA1"], errors="coerce").fillna(0.0) * scale
  plot["endpoint_y"] = pd.to_numeric(plot["RDA2"], errors="coerce").fillna(0.0) * scale
  plot = _bounded_vector_labels(plot, "endpoint_x", "endpoint_y", xlim, ylim)
  for _, row in plot.iterrows():
    x = float(row["endpoint_x"])
    y = float(row["endpoint_y"])
    fig.add_shape(type="line", x0=0, y0=0, x1=x, y1=y, line={"color": "#333333", "width": 2.0})
    fig.add_annotation(
      x=x, y=y, ax=float(row["label_x"]), ay=float(row["label_y"]),
      xref="x", yref="y", axref="x", ayref="y",
      text=str(row[label_col]), showarrow=True, arrowhead=2,
      arrowsize=1.0, arrowwidth=1.3, arrowcolor="#333333",
      font={"size": 13, "color": "#222222"},
      bgcolor="rgba(255,255,255,0.88)", borderpad=2,
    )
  return plot


def _add_taxon_vectors(
  fig: go.Figure,
  vectors: pd.DataFrame,
  scale: float,
  xlim: tuple[float, float],
  ylim: tuple[float, float],
  palette: dict[str, str],
) -> pd.DataFrame:
  plot = vectors.reset_index().copy()
  label_col = "Genus" if "Genus" in plot.columns else plot.columns[0]
  plot["endpoint_x"] = pd.to_numeric(plot["RDA1"], errors="coerce").fillna(0.0) * scale
  plot["endpoint_y"] = pd.to_numeric(plot["RDA2"], errors="coerce").fillna(0.0) * scale
  plot = _side_column_label_positions(plot, "endpoint_x", "endpoint_y", xlim, ylim, gap_fraction=0.075, inset_fraction=0.025)
  for _, row in plot.iterrows():
    name = str(row[label_col])
    color = palette.get(name, "#444444")
    x = float(row["endpoint_x"])
    y = float(row["endpoint_y"])
    fig.add_shape(type="line", x0=0, y0=0, x1=x, y1=y, line={"color": color, "width": 1.8, "dash": "dash"})
    fig.add_annotation(
      x=x, y=y, ax=float(row["label_x"]), ay=float(row["label_y"]),
      xref="x", yref="y", axref="x", ayref="y",
      text=name, showarrow=True, arrowhead=2,
      arrowsize=1.0, arrowwidth=1.0, arrowcolor=color,
      font={"size": 12, "color": color},
      bgcolor="rgba(255,255,255,0.90)", borderpad=2,
      xanchor="left" if float(row["label_x"]) < (xlim[0] + xlim[1]) / 2 else "right",
    )
  return plot


def publication_rda_data(base_dir: Path, domain: str = "Bacteria") -> dict[str, Any]:
  result = canonical_ordination_result(base_dir, domain)
  rda = result["rda"]
  sites = rda["scores"].reset_index()
  sites = _attach_publication_sample_metadata(sites, pooled_sites=True)
  env = rda["vectors"].reset_index()
  taxa = rda["taxon_vectors"].reset_index()
  return {
    "sites": sites,
    "environment_vectors": env,
    "taxon_vectors": taxa,
    "model_statistics": rda["model_stats"].copy(),
    "vif": rda["vif"].copy(),
    "sample_audit": rda["sample_audit"].copy(),
    "near_overlap_pairs": rda["near_overlap_pairs"].copy(),
    "relative_abundance": result["relative"].copy(),
    "raw_result": rda,
  }


def publication_nmds_data(base_dir: Path, domain: str = "Bacteria") -> dict[str, Any]:
  result = canonical_ordination_result(base_dir, domain)
  nmds = result["nmds"]
  scores = _attach_publication_sample_metadata(nmds["scores"].copy(), pooled_sites=False)
  parameters = pd.DataFrame([{
    **nmds["parameters"],
    "stress_1": nmds["stress"],
    "iterations": nmds["n_iter"],
    "converged": nmds["converged"],
    "rank_correlation_observed_vs_ordination_distances": nmds["rank_correlation"],
  }])
  return {
    "scores": scores,
    "statistics": nmds["tests"].copy(),
    "parameters": parameters,
    "sample_audit": nmds["sample_audit"].copy(),
    "near_overlap_pairs": nmds["near_overlap_pairs"].copy(),
    "distance": nmds["distance"].copy(),
    "transformed": nmds["transformed"].copy(),
    "relative_abundance": result["relative"].copy(),
    "raw_result": nmds,
  }


def publication_rda_figure(base_dir: Path, domain: str = "Bacteria", show_taxa: bool = True):
  canonical_domain = _normalise_domain(domain)
  data = publication_rda_data(base_dir, canonical_domain)
  rda = data["raw_result"]
  sites = data["sites"]
  env = data["environment_vectors"]
  taxa = data["taxon_vectors"]
  fig = go.Figure()
  for lake in ["AM", "TIA", "TI", "VI"]:
    subset = sites[sites["Lake"].astype(str).eq(lake)] if "Lake" in sites.columns else pd.DataFrame()
    if subset.empty:
      continue
    hover_cols = [
      col for col in ["Sample", "Lake", "Publication sample IDs", "IMG_JGI_analysis_project_id",
                      "IMG_JGI_taxon_oid", "ENA_study_accession", "sample_type", "geographic_coordinates"]
      if col in subset.columns
    ]
    custom = subset[hover_cols].astype(str).to_numpy() if hover_cols else None
    hover_lines = "<br>".join([f"<b>{col}:</b> %{{customdata[{index}]}}" for index, col in enumerate(hover_cols)])
    fig.add_trace(go.Scatter(
      x=subset["RDA1"], y=subset["RDA2"], mode="markers",
      name=lake, legendgroup=f"lake-{lake}",
      marker={"size": 13, "color": LAKE_COLORS.get(lake, "#777777"), "line": {"color": "black", "width": 1}},
      customdata=custom,
      hovertemplate=(hover_lines + "<extra></extra>") if hover_lines else "%{x}, %{y}<extra></extra>",
    ))

  score_values = sites[["RDA1", "RDA2"]].apply(pd.to_numeric, errors="coerce").to_numpy(float)
  extent = max(float(np.nanmax(np.abs(score_values))), 1e-6)
  env_scale = extent * 0.82
  tax_scale = extent * 0.70
  env_x = pd.to_numeric(env.get("RDA1", pd.Series(dtype=float)), errors="coerce").fillna(0).to_numpy(float) * env_scale
  env_y = pd.to_numeric(env.get("RDA2", pd.Series(dtype=float)), errors="coerce").fillna(0).to_numpy(float) * env_scale
  tax_x = pd.to_numeric(taxa.get("RDA1", pd.Series(dtype=float)), errors="coerce").fillna(0).to_numpy(float) * tax_scale
  tax_y = pd.to_numeric(taxa.get("RDA2", pd.Series(dtype=float)), errors="coerce").fillna(0).to_numpy(float) * tax_scale
  all_x = np.concatenate(([0.0], score_values[:, 0], env_x, tax_x if show_taxa else np.array([], dtype=float)))
  all_y = np.concatenate(([0.0], score_values[:, 1], env_y, tax_y if show_taxa else np.array([], dtype=float)))
  xmin, xmax = float(np.nanmin(all_x)), float(np.nanmax(all_x))
  ymin, ymax = float(np.nanmin(all_y)), float(np.nanmax(all_y))
  xr = max(xmax - xmin, extent)
  yr = max(ymax - ymin, extent)
  xlim = (xmin - xr * 0.48, xmax + xr * 0.48)
  ylim = (ymin - yr * 0.33, ymax + yr * 0.33)

  palette = build_palette(taxa.get("Genus", pd.Series(dtype=str)).astype(str).tolist(), load_palette(Path(base_dir) / "data/taxonomy_palette.json"))
  _add_environment_vectors(fig, rda["vectors"], env_scale, xlim, ylim)
  if show_taxa:
    _add_taxon_vectors(fig, rda["taxon_vectors"], tax_scale, xlim, ylim, palette)
  _add_point_labels(fig, sites, "RDA1", "RDA2", "Sample", xlim, ylim)

  fig.add_hline(y=0, line={"color": "#AAAAAA", "width": 1})
  fig.add_vline(x=0, line={"color": "#AAAAAA", "width": 1})
  fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line={"color": "#333333", "width": 2}, name="Environmental variable"))
  fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", line={"color": "#666666", "width": 2, "dash": "dash"}, name="Representative genus vector"))
  fig.update_layout(
    title={
      "text": f"{canonical_domain} genus-level RDA (R² = {rda['r2']:.3f}; adjusted R² = {rda['adjusted_r2']:.3f}; pseudo-F = {rda['F']:.3f}; P = {rda['p']:.3f})",
      "x": 0.01, "xanchor": "left",
    },
    xaxis={"title": f"RDA1 ({rda['pct'][0]:.1f}% constrained variation; axis P = {rda['axis_p'][0]:.3f})", "range": list(xlim), "zeroline": False},
    yaxis={"title": f"RDA2 ({rda['pct'][1]:.1f}% constrained variation; axis P = {rda['axis_p'][1]:.3f})", "range": list(ylim), "zeroline": False},
    height=860,
    margin={"l": 105, "r": 130, "t": 110, "b": 145},
    legend={"orientation": "h", "y": -0.20, "yanchor": "top", "x": 0.0, "xanchor": "left", "title": {"text": "Lake / vector type"}},
    annotations=list(fig.layout.annotations),
    meta={
      "scientific_source": "src.publication_ordination.compute_rda",
      "article_equivalent": True,
      "domain": canonical_domain,
      "environment_scale": env_scale,
      "taxon_scale": tax_scale,
      "all_vectors_within_axis_range": True,
    },
  )
  return fig, sites, env, taxa


def publication_nmds_figure(base_dir: Path, domain: str = "Bacteria"):
  canonical_domain = _normalise_domain(domain)
  data = publication_nmds_data(base_dir, canonical_domain)
  nmds = data["raw_result"]
  scores = data["scores"]
  fig = go.Figure()
  for lake in ["AM", "TIA", "TI", "VI"]:
    for season in ["Dry", "Rainy"]:
      subset = scores[
        scores["Lake"].astype(str).eq(lake) & scores["Season"].astype(str).eq(season)
      ]
      if subset.empty:
        continue
      hover_cols = [
        col for col in ["Sample", "Lake", "Season", "IMG_JGI_analysis_project_id", "IMG_JGI_taxon_oid",
                        "ENA_study_accession", "sample_type", "geographic_coordinates"] if col in subset.columns
      ]
      custom = subset[hover_cols].astype(str).to_numpy() if hover_cols else None
      hover_lines = "<br>".join([f"<b>{col}:</b> %{{customdata[{index}]}}" for index, col in enumerate(hover_cols)])
      fig.add_trace(go.Scatter(
        x=subset["NMDS1"], y=subset["NMDS2"], mode="markers",
        name=f"{lake} — {season}", legendgroup=f"{lake}-{season}",
        marker={
          "size": 12, "color": LAKE_COLORS.get(lake, "#777777"),
          "symbol": SEASON_SYMBOLS[season], "line": {"color": "black", "width": 1},
        },
        customdata=custom,
        hovertemplate=(hover_lines + "<extra></extra>") if hover_lines else "%{x}, %{y}<extra></extra>",
      ))
  xr = float(np.ptp(pd.to_numeric(scores["NMDS1"], errors="coerce")))
  yr = float(np.ptp(pd.to_numeric(scores["NMDS2"], errors="coerce")))
  xlim = (
    float(scores["NMDS1"].min() - max(xr * 0.30, 0.03)),
    float(scores["NMDS1"].max() + max(xr * 0.30, 0.03)),
  )
  ylim = (
    float(scores["NMDS2"].min() - max(yr * 0.20, 0.02)),
    float(scores["NMDS2"].max() + max(yr * 0.20, 0.02)),
  )
  _add_point_labels(fig, scores, "NMDS1", "NMDS2", "Sample", xlim, ylim)
  fig.add_hline(y=0, line={"color": "#AAAAAA", "width": 1})
  fig.add_vline(x=0, line={"color": "#AAAAAA", "width": 1})
  fig.update_layout(
    title={
      "text": f"{canonical_domain} genus-level Bray–Curtis non-metric MDS (normalized Stress-1 = {nmds['stress']:.3f})",
      "x": 0.01, "xanchor": "left",
    },
    xaxis={"title": "NMDS1", "range": list(xlim), "zeroline": False},
    yaxis={"title": "NMDS2", "range": list(ylim), "zeroline": False},
    height=840,
    margin={"l": 95, "r": 130, "t": 95, "b": 135},
    legend={"orientation": "h", "y": -0.20, "yanchor": "top", "x": 0.0, "xanchor": "left", "title": {"text": "Lake / season"}},
    meta={
      "scientific_source": "src.publication_ordination.compute_nmds",
      "article_equivalent": True,
      "domain": canonical_domain,
      "stress_1": float(nmds["stress"]),
      "n_init": int(nmds["parameters"]["n_init"]),
      "max_iter": int(nmds["parameters"]["max_iter"]),
      "seed": int(nmds["parameters"]["seed"]),
    },
  )
  return fig, scores
