from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from scipy.spatial.distance import pdist, squareform
from scipy.stats import pearsonr
from sklearn.decomposition import PCA

from .publication_ordination import (
  _orient_axes, pcoa_bray_curtis_matrix, nmds_bray_curtis_matrix,
)
from .supplementary_database import counts_table, taxonomy_profile_table, ST8_ALL_KO_SHEET
from .visual_qc import repel_label_positions

SEED = 42
NMDS_N_INIT = 20
NMDS_MAX_ITER = 1000


def _numeric(frame: pd.DataFrame, id_col: str) -> tuple[pd.DataFrame, list[str]]:
  if frame is None or frame.empty:
    return pd.DataFrame(), []
  cols: list[str] = []
  out = frame.copy()
  for col in out.columns:
    if col == id_col:
      continue
    vals = pd.to_numeric(out[col], errors="coerce")
    if vals.notna().sum() > 1 and vals.nunique(dropna=True) > 1:
      out[col] = vals.fillna(vals.median())
      cols.append(col)
  return out, cols


def environmental_matrix(*frames: pd.DataFrame) -> pd.DataFrame:
  usable = [f.copy() for f in frames if isinstance(f, pd.DataFrame) and not f.empty]
  if not usable:
    return pd.DataFrame()
  result = usable[0]
  common_candidates = ["sample", "sample_id", "Sample", "group", "LakeSeason"]
  for frame in usable[1:]:
    key = next((c for c in common_candidates if c in result.columns and c in frame.columns), None)
    if key:
      result = result.merge(frame, on=key, how="outer", suffixes=("", "_extra"))
    else:
      result = pd.concat([result.reset_index(drop=True), frame.reset_index(drop=True)], axis=1)
  return result


def combined_omics_matrix(
  taxonomy_level: str = "Genus — Bacteria",
  include_taxonomy: bool = True,
  include_biogeochemical_ko: bool = True,
  include_biogeochemical_pathway: bool = True,
  include_iron_ko: bool = True,
  include_iron_role: bool = True,
  include_other_metals: bool = True,
  top_taxa: int = 30,
  top_ko: int = 40,
) -> tuple[pd.DataFrame, str]:
  """Build the integrated matrix and return the identifier column explicitly.

  The previous implementation returned only a DataFrame while the app expected
  ``(matrix, group_kind)``.  The stable group key is ``group``.
  """
  del include_biogeochemical_pathway, include_iron_role, include_other_metals
  blocks: list[pd.DataFrame] = []
  group_kind = "group"
  if include_taxonomy:
    tax = taxonomy_profile_table(taxonomy_level, view_mode="Aggregated lake-season groups")
    if not tax.empty:
      ranking = tax.groupby("taxon")["abundance"].mean().sort_values(ascending=False)
      keep = ranking.head(int(top_taxa)).index
      tax = tax[tax["taxon"].isin(keep)].pivot_table(
        index="group", columns="taxon", values="abundance", aggfunc="sum", fill_value=0.0,
      )
      tax.columns = [f"taxon::{c}" for c in tax.columns]
      tax.index.name = group_kind
      blocks.append(tax)
  if include_biogeochemical_ko or include_iron_ko:
    ko, _numeric_cols = counts_table("table8", ST8_ALL_KO_SHEET, ["KO", "Metabolism", "KO description"])
    if not ko.empty:
      meta = [c for c in ["KO", "Metabolism", "KO description"] if c in ko.columns]
      numeric = [c for c in ko.columns if c not in meta and pd.to_numeric(ko[c], errors="coerce").notna().sum()]
      ko[numeric] = ko[numeric].apply(pd.to_numeric, errors="coerce").fillna(0)
      ko["_total"] = ko[numeric].sum(axis=1)
      ko = ko.nlargest(int(top_ko), "_total")
      labels = ko[meta[0]].astype(str) if meta else ko.index.astype(str)
      matrix = ko[numeric].T
      matrix.columns = [f"KO::{x}" for x in labels]
      matrix.index.name = group_kind
      blocks.append(matrix)
  if not blocks:
    return pd.DataFrame(), group_kind
  merged = pd.concat(blocks, axis=1, join="outer").fillna(0.0)
  return merged.reset_index(), group_kind


def make_integrated_table(env: pd.DataFrame, omics: pd.DataFrame, group_kind: str = "group") -> pd.DataFrame:
  if omics is None or omics.empty:
    return env.copy() if isinstance(env, pd.DataFrame) else pd.DataFrame()
  if env is None or env.empty:
    return omics.copy()
  candidates = [group_kind, "group", "sample", "sample_id", "Sample", "LakeSeason"]
  key = next((c for c in candidates if c in env.columns and c in omics.columns), None)
  if key:
    return env.merge(omics, on=key, how="inner", suffixes=("_env", "_omics"))
  return pd.concat([env.reset_index(drop=True), omics.reset_index(drop=True)], axis=1)


def _feature_scope_columns(cols: list[str], feature_scope: str) -> list[str]:
  scope = str(feature_scope).casefold()
  tax = [c for c in cols if str(c).startswith("taxon::")]
  biomarkers = [c for c in cols if str(c).startswith(("KO::", "ko_", "metab_", "role_"))]
  if "taxa only" in scope:
    return tax
  if "biomarker" in scope or "metabolic" in scope:
    return biomarkers
  if "environment" in scope:
    excluded = set(tax + biomarkers)
    return [c for c in cols if c not in excluded]
  return cols


def pca_integrated(
  frame: pd.DataFrame,
  id_col: str = "group",
  feature_scope: str = "All integrated variables",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
  work, all_cols = _numeric(frame, id_col)
  cols = _feature_scope_columns(all_cols, feature_scope)
  if len(work) < 3 or len(cols) < 2:
    return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
  x = work[cols].to_numpy(float)
  means = x.mean(axis=0)
  sd = np.where(x.std(axis=0, ddof=0) == 0, 1, x.std(axis=0, ddof=0))
  z = (x - means) / sd
  model = PCA(n_components=2, random_state=SEED)
  scores = _orient_axes(model.fit_transform(z))
  score_df = pd.DataFrame({"PC1": scores[:, 0], "PC2": scores[:, 1]})
  score_df[id_col] = work[id_col].astype(str).to_numpy() if id_col in work else work.index.astype(str)
  loadings = model.components_.T.copy()
  # Apply the same deterministic axis signs as the oriented scores.
  raw_scores = model.transform(z)
  for axis in range(2):
    if float(np.dot(raw_scores[:, axis], np.arange(1, len(raw_scores) + 1, dtype=float))) < 0:
      loadings[:, axis] *= -1
  loading_df = pd.DataFrame({
    "feature": cols,
    "PC1_loading": loadings[:, 0],
    "PC2_loading": loadings[:, 1],
    "loading_magnitude": np.hypot(loadings[:, 0], loadings[:, 1]),
  }).sort_values("loading_magnitude", ascending=False)
  variance = pd.DataFrame({
    "axis": ["PC1", "PC2"],
    "explained_variance_percent": model.explained_variance_ratio_[:2] * 100.0,
    "eigenvalue": model.explained_variance_[:2],
  })
  return score_df, loading_df.reset_index(drop=True), variance


def pcoa_bray_curtis(frame: pd.DataFrame, id_col: str = "group") -> tuple[pd.DataFrame, pd.DataFrame]:
  """Delegate to the same Bray–Curtis PCoA implementation used by the article."""
  work, columns = _numeric(frame, id_col)
  if len(work) < 3 or len(columns) < 2:
    return pd.DataFrame(), pd.DataFrame()
  identifiers = work[id_col].astype(str).to_numpy() if id_col in work else work.index.astype(str)
  matrix = work[columns].copy()
  matrix.index = identifiers
  result = pcoa_bray_curtis_matrix(matrix)
  scores = result.get("scores", pd.DataFrame()).copy()
  if scores.empty:
    return pd.DataFrame(), pd.DataFrame()
  scores[id_col] = scores.index.astype(str)
  variance = result["variance"].copy()
  lookup = variance.set_index("axis")["explained_variance_percent"]
  scores["PCoA1_explained_percent"] = float(lookup.loc["PCoA1"])
  scores["PCoA2_explained_percent"] = float(lookup.loc["PCoA2"])
  scores["distance_correction"] = str(result["correction"])
  scores["negative_eigenvalue_count_before_correction"] = int(result["negative_eigenvalue_count"])
  scores["negative_eigenvalue_absolute_sum_before_correction"] = float(result["negative_eigenvalue_absolute_sum"])
  scores["lingoes_constant"] = float(result["lingoes_constant"])
  return scores.reset_index(drop=True), variance


def nmds_bray_curtis(frame: pd.DataFrame, id_col: str = "group") -> pd.DataFrame:
  """Delegate to the same non-metric MDS implementation used by the article."""
  work, columns = _numeric(frame, id_col)
  if len(work) < 4 or len(columns) < 2:
    return pd.DataFrame()
  identifiers = work[id_col].astype(str).to_numpy() if id_col in work else work.index.astype(str)
  matrix = work[columns].copy()
  matrix.index = identifiers
  result = nmds_bray_curtis_matrix(matrix, random_state=SEED, n_init=NMDS_N_INIT, max_iter=NMDS_MAX_ITER)
  scores = result.get("scores", pd.DataFrame()).copy()
  if scores.empty:
    return pd.DataFrame()
  scores[id_col] = scores.index.astype(str)
  scores["stress"] = float(result["stress"])
  scores["stress_1"] = float(result["stress"])
  scores["iterations"] = int(result["n_iter"])
  scores["converged"] = bool(result["converged"])
  scores["n_init"] = NMDS_N_INIT
  scores["max_iter"] = NMDS_MAX_ITER
  scores["seed"] = SEED
  scores["transformation"] = "square root of row-wise relative proportions"
  return scores.reset_index(drop=True)


def ordination_figure(scores: pd.DataFrame, x_col: str, y_col: str, id_col: str, title: str):
  if scores is None or scores.empty:
    return px.scatter(title=title)
  fig = go.Figure(go.Scatter(
    x=scores[x_col], y=scores[y_col], mode="markers",
    marker={"size": 11, "line": {"color": "black", "width": 0.8}},
    customdata=scores[[id_col]].astype(str).to_numpy() if id_col in scores else None,
    hovertemplate=f"<b>{id_col}:</b> %{{customdata[0]}}<br>{x_col}: %{{x:.4f}}<br>{y_col}: %{{y:.4f}}<extra></extra>" if id_col in scores else None,
    name="Units",
  ))
  x_range = max(float(np.ptp(pd.to_numeric(scores[x_col], errors="coerce"))), 0.05)
  y_range = max(float(np.ptp(pd.to_numeric(scores[y_col], errors="coerce"))), 0.05)
  labels = repel_label_positions(scores, x_col, y_col, min_distance=y_range * 0.08, radial_offset=y_range * 0.10)
  if id_col in labels:
    for _, row in labels.iterrows():
      fig.add_annotation(
        x=float(row[x_col]), y=float(row[y_col]), ax=float(row["label_x"]), ay=float(row["label_y"]),
        xref="x", yref="y", axref="x", ayref="y", text=str(row[id_col]), showarrow=True,
        arrowhead=0, arrowwidth=0.7, arrowcolor="#666666", bgcolor="rgba(255,255,255,0.86)",
        borderpad=2, font={"size": 11},
      )
  fig.update_layout(
    title={"text": title, "x": 0.01, "xanchor": "left"}, height=700,
    xaxis={"title": x_col, "range": [float(scores[x_col].min() - x_range * 0.25), float(scores[x_col].max() + x_range * 0.25)]},
    yaxis={"title": y_col, "range": [float(scores[y_col].min() - y_range * 0.25), float(scores[y_col].max() + y_range * 0.25)]},
    margin={"l": 90, "r": 120, "t": 100, "b": 90},
  )
  return fig


def omics_environment_correlations(
  frame: pd.DataFrame,
  id_col: str = "group",
  max_omics_features: int = 80,
  max_env_features: int = 80,
) -> pd.DataFrame:
  work, cols = _numeric(frame, id_col)
  rows = []
  for i, a in enumerate(cols[:max_env_features]):
    for b in cols[i + 1:i + 1 + max_omics_features]:
      try:
        r, p = pearsonr(work[a], work[b])
      except Exception:
        continue
      rows.append({"feature_a": a, "feature_b": b, "correlation": r, "p_value": p})
  return pd.DataFrame(rows).sort_values("p_value") if rows else pd.DataFrame()


def env_axis_correlations(integrated: pd.DataFrame, scores: pd.DataFrame, id_col: str, axes: list[str]) -> pd.DataFrame:
  if integrated is None or scores is None or integrated.empty or scores.empty or id_col not in integrated or id_col not in scores:
    return pd.DataFrame()
  merged = integrated.merge(scores[[id_col] + axes], on=id_col, how="inner")
  work, cols = _numeric(merged, id_col)
  features = [c for c in cols if c not in axes]
  rows = []
  for feature in features:
    for axis in axes:
      try:
        r, p = pearsonr(work[feature], work[axis])
      except Exception:
        continue
      rows.append({"feature": feature, "axis": axis, "correlation": r, "p_value": p})
  return pd.DataFrame(rows).sort_values("p_value") if rows else pd.DataFrame()


def feature_axis_vectors(*args, **kwargs):
  return env_axis_correlations(*args, **kwargs)


def correlation_heatmap(frame: pd.DataFrame, *args, **kwargs):
  if frame is None or frame.empty:
    return px.imshow(np.zeros((1, 1)), title="No correlation data")
  numeric = frame.select_dtypes(include=[np.number])
  return px.imshow(numeric.corr(), text_auto=".2f", title="Correlation heatmap")
