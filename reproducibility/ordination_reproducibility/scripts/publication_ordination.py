#!/usr/bin/env python3
"""Canonical ordination calculations shared by the article and application.

This module is the single scientific implementation for the genus-level
Bray-Curtis NMDS and physicochemical RDA displayed in Main Figures 4-5,
Supplementary Figure 17, and the corresponding Streamlit panels.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import platform
from typing import Iterable

import numpy as np
import pandas as pd
from scipy.spatial.distance import pdist, squareform
from scipy.stats import spearmanr
from sklearn.manifold import MDS
import sklearn
import scipy

SAMPLE_MAP = {
  "Ga0540489": "AM.P1.D", "Ga0541010": "AM.P1.R", "Ga0541011": "AM.P2.D", "Ga0541012": "AM.P2.R",
  "Ga0541013": "TIA.P1.D", "Ga0541014": "TIA.P1.R", "Ga0541015": "TIA.P2.D", "Ga0541016": "TIA.P2.R",
  "Ga0541017": "TI.P1.D", "Ga0541018": "TI.P1.R", "Ga0541019": "TI.P2.D", "Ga0541020": "TI.P2.R",
  "Ga0541021": "TI.P3.D", "Ga0541022": "TI.P3.R", "Ga0541023": "TI.P4.D", "Ga0541024": "TI.P4.R",
  "Ga0541025": "VI.P1.D", "Ga0541026": "VI.P1.R", "Ga0541027": "VI.P2.D", "Ga0541028": "VI.P2.R",
}
SAMPLE_ORDER = [
  "AM.P1.D", "AM.P1.R", "AM.P2.D", "AM.P2.R",
  "TIA.P1.D", "TIA.P1.R", "TIA.P2.D", "TIA.P2.R",
  "TI.P1.D", "TI.P1.R", "TI.P2.D", "TI.P2.R",
  "TI.P3.D", "TI.P3.R", "TI.P4.D", "TI.P4.R",
  "VI.P1.D", "VI.P1.R", "VI.P2.D", "VI.P2.R",
]
POSITION_ORDER = ["AM.P1", "AM.P2", "TIA.P1", "TIA.P2", "TI.P1", "TI.P2", "TI.P3", "TI.P4", "VI.P1", "VI.P2"]
RDA_VARIABLES = ["LOI", "SiO2", "Al2O3", "TOT/S", "Cu", "Pb"]
SEED = 42
N_PERMUTATIONS = 999


def _normalise_taxon(value: object) -> str:
  text = str(value if value is not None else "").strip()
  if not text or text.casefold() in {"nan", "none", "na", "n/a", "unknown", "undefined", "null"}:
    return "Unclassified"
  return text


def load_cds(base_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
  base = Path(base_dir)
  otu = pd.read_csv(base / "data/resultado.cds.otu.tab", sep="\t", index_col=0)
  tax = pd.read_csv(base / "data/resultado.cds.tax.tab", sep="\t", index_col=0)
  otu.index = otu.index.astype(str).str.strip()
  tax.index = tax.index.astype(str).str.strip()
  otu.columns = [SAMPLE_MAP.get(str(c).split("_")[0].strip("."), str(c).split("_")[0].strip(".")) for c in otu.columns]
  otu = otu.reindex(columns=[s for s in SAMPLE_ORDER if s in otu.columns]).apply(pd.to_numeric, errors="coerce").fillna(0)
  tax.columns = [str(c).strip() for c in tax.columns]
  for col in tax.columns:
    tax[col] = tax[col].map(_normalise_taxon)
  return otu, tax


def domain_genus_matrix(base_dir: Path, domain: str, top_n: int = 18) -> pd.DataFrame:
  otu, tax = load_cds(base_dir)
  shared = otu.index.intersection(tax.index)
  mask = tax.loc[shared, "Domain"].astype(str).str.casefold().eq(domain.casefold())
  ids = shared[mask.to_numpy()]
  labels = tax.loc[ids, "Genus"].map(_normalise_taxon)
  counts = otu.loc[ids].copy()
  counts["__genus__"] = labels.to_numpy()
  agg = counts.groupby("__genus__", sort=False).sum(numeric_only=True)
  rel = agg.div(agg.sum(axis=0).replace(0, np.nan), axis=1).fillna(0) * 100.0
  totals = rel.sum(axis=1).sort_values(ascending=False)
  keep = list(totals.head(min(top_n, len(totals))).index)
  out = rel.loc[keep].copy()
  remainder = rel.drop(index=keep, errors="ignore").sum(axis=0)
  if float(remainder.sum()) > 0:
    out.loc["Other genera"] = remainder
  return out


def _orient_axes(coords: np.ndarray) -> np.ndarray:
  coords = np.asarray(coords, dtype=float).copy()
  weights = np.arange(1, coords.shape[0] + 1, dtype=float)
  for axis in range(coords.shape[1]):
    if float(np.dot(coords[:, axis], weights)) < 0:
      coords[:, axis] *= -1
  return coords


def _new_nonmetric_mds(random_state: int = SEED, n_init: int = 20, max_iter: int = 1000):
  try:
    return MDS(
      n_components=2,
      metric_mds=False,
      metric="precomputed",
      random_state=random_state,
      n_init=n_init,
      init="random",
      max_iter=max_iter,
      eps=1e-6,
      normalized_stress=True,
    )
  except TypeError:
    return MDS(
      n_components=2,
      metric=False,
      dissimilarity="precomputed",
      random_state=random_state,
      n_init=n_init,
      max_iter=max_iter,
      eps=1e-6,
      normalized_stress=True,
    )


def _distance_gower(distance: np.ndarray) -> np.ndarray:
  n = distance.shape[0]
  J = np.eye(n) - np.ones((n, n)) / n
  return -0.5 * J @ (distance ** 2) @ J


def permanova(distance: np.ndarray, groups: Iterable[str], permutations: int = N_PERMUTATIONS, seed: int = SEED) -> dict:
  groups = np.asarray(list(groups), dtype=str)
  n = len(groups)
  levels = pd.unique(groups)
  if len(levels) < 2:
    return {"pseudo_F": np.nan, "p_value": np.nan, "df_between": 0, "df_within": n - 1, "permutations": permutations}
  B = _distance_gower(distance)
  I = np.eye(n)
  H0 = np.ones((n, n)) / n

  def statistic(labels: np.ndarray) -> float:
    lev = pd.unique(labels)
    X = np.column_stack([(labels == level).astype(float) for level in lev])
    H = X @ np.linalg.pinv(X.T @ X) @ X.T
    ss_between = float(np.trace((H - H0) @ B))
    ss_within = float(np.trace((I - H) @ B))
    df_between = len(lev) - 1
    df_within = n - len(lev)
    if df_between <= 0 or df_within <= 0 or ss_within <= 0:
      return np.nan
    return (ss_between / df_between) / (ss_within / df_within)

  observed = statistic(groups)
  rng = np.random.default_rng(seed)
  permuted = np.asarray([statistic(rng.permutation(groups)) for _ in range(permutations)], dtype=float)
  valid = np.isfinite(permuted)
  p = (1 + int(np.sum(permuted[valid] >= observed))) / (1 + int(valid.sum())) if np.isfinite(observed) else np.nan
  return {
    "pseudo_F": float(observed),
    "p_value": float(p),
    "df_between": int(len(levels) - 1),
    "df_within": int(n - len(levels)),
    "permutations": int(permutations),
  }


def betadisper_test(distance: np.ndarray, groups: Iterable[str], permutations: int = N_PERMUTATIONS, seed: int = SEED) -> dict:
  groups = np.asarray(list(groups), dtype=str)
  levels = pd.unique(groups)
  n = len(groups)
  B = _distance_gower(distance)
  eigvals, eigvecs = np.linalg.eigh(B)
  positive = eigvals > 1e-12
  coords = eigvecs[:, positive] * np.sqrt(eigvals[positive]) if positive.any() else np.zeros((n, 1))

  def distances_to_centroids(labels: np.ndarray) -> np.ndarray:
    result = np.zeros(n, dtype=float)
    for level in pd.unique(labels):
      idx = np.where(labels == level)[0]
      centroid = coords[idx].mean(axis=0)
      result[idx] = np.sqrt(((coords[idx] - centroid) ** 2).sum(axis=1))
    return result

  def statistic(labels: np.ndarray) -> float:
    d = distances_to_centroids(labels)
    grand = float(d.mean())
    ss_between = sum(int((labels == lev).sum()) * (float(d[labels == lev].mean()) - grand) ** 2 for lev in pd.unique(labels))
    ss_within = sum(float(((d[labels == lev] - d[labels == lev].mean()) ** 2).sum()) for lev in pd.unique(labels))
    df_between = len(pd.unique(labels)) - 1
    df_within = n - len(pd.unique(labels))
    if df_between <= 0 or df_within <= 0 or ss_within <= 0:
      return np.nan
    return (ss_between / df_between) / (ss_within / df_within)

  observed = statistic(groups)
  rng = np.random.default_rng(seed)
  permuted = np.asarray([statistic(rng.permutation(groups)) for _ in range(permutations)], dtype=float)
  valid = np.isfinite(permuted)
  p = (1 + int(np.sum(permuted[valid] >= observed))) / (1 + int(valid.sum())) if np.isfinite(observed) else np.nan
  return {
    "F": float(observed),
    "p_value": float(p),
    "df_between": int(len(levels) - 1),
    "df_within": int(n - len(levels)),
    "permutations": int(permutations),
  }


def compute_nmds(rel: pd.DataFrame, domain: str, random_state: int = SEED) -> dict:
  samples = [s for s in SAMPLE_ORDER if s in rel.columns]
  x = rel.T.loc[samples].copy()
  x = x.div(x.sum(axis=1).replace(0, np.nan), axis=0).fillna(0)
  transformed = np.sqrt(x)
  distance = squareform(pdist(transformed.to_numpy(float), metric="braycurtis"))
  distance = np.nan_to_num(distance, nan=0.0, posinf=1.0, neginf=0.0)
  model = _new_nonmetric_mds(random_state=random_state, n_init=20, max_iter=1000)
  coords = _orient_axes(model.fit_transform(distance))
  scores = pd.DataFrame(coords, columns=["NMDS1", "NMDS2"], index=samples)
  scores["Sample"] = scores.index
  scores["Lake"] = scores.index.to_series().str.split(".").str[0].to_numpy()
  scores["Season"] = np.where(scores.index.to_series().str.endswith(".D"), "Dry", "Rainy")
  scores["LakeSeason"] = scores["Lake"] + "-" + scores["Season"].str[0]
  ord_dist = squareform(pdist(coords, metric="euclidean"))
  upper = np.triu_indices_from(distance, k=1)
  rho = spearmanr(distance[upper], ord_dist[upper]).statistic
  diagonal = float(np.hypot(np.ptp(coords[:, 0]), np.ptp(coords[:, 1])))
  threshold = max(diagonal * 0.01, 1e-12)
  pair_rows = []
  for i in range(len(samples)):
    for j in range(i + 1, len(samples)):
      dd = float(np.linalg.norm(coords[i] - coords[j]))
      if dd <= threshold:
        pair_rows.append({"sample_1": samples[i], "sample_2": samples[j], "ordination_distance": dd, "threshold": threshold})
  tests = []
  for factor in ["Lake", "Season", "LakeSeason"]:
    pm = permanova(distance, scores[factor], permutations=N_PERMUTATIONS, seed=SEED)
    bd = betadisper_test(distance, scores[factor], permutations=N_PERMUTATIONS, seed=SEED)
    tests.append({"domain": domain, "factor": factor, **{f"PERMANOVA_{k}": v for k, v in pm.items()}, **{f"dispersion_{k}": v for k, v in bd.items()}})
  sample_audit = pd.DataFrame({
    "domain": domain,
    "original_sample_id": samples,
    "standardized_sample_id": samples,
    "present_in_abundance": [s in rel.columns for s in samples],
    "included_in_NMDS": True,
    "exclusion_reason": "",
    "NMDS1": scores.loc[samples, "NMDS1"].to_numpy(),
    "NMDS2": scores.loc[samples, "NMDS2"].to_numpy(),
    "point_drawn": True,
  })
  return {
    "scores": scores.reset_index(drop=True),
    "transformed": transformed,
    "distance": pd.DataFrame(distance, index=samples, columns=samples),
    "stress": float(model.stress_),
    "n_iter": int(getattr(model, "n_iter_", -1)),
    "converged": bool(getattr(model, "n_iter_", 1000) < 1000),
    "rank_correlation": float(rho),
    "tests": pd.DataFrame(tests),
    "sample_audit": sample_audit,
    "near_overlap_pairs": pd.DataFrame(pair_rows, columns=["sample_1", "sample_2", "ordination_distance", "threshold"]),
    "parameters": {
      "domain": domain,
      "n_samples": len(samples),
      "transformation": "square root of sample-wise relative proportions",
      "dissimilarity": "Bray-Curtis",
      "dimensions": 2,
      "nonmetric": True,
      "n_init": 20,
      "max_iter": 1000,
      "seed": random_state,
      "normalized_stress": True,
    },
  }


def _vif_table(Z: pd.DataFrame) -> pd.DataFrame:
  rows = []
  for column in Z.columns:
    y = Z[column].to_numpy(float)
    other = Z.drop(columns=[column])
    X = np.column_stack([np.ones(len(other)), other.to_numpy(float)])
    fitted = X @ np.linalg.pinv(X.T @ X) @ X.T @ y
    ss_res = float(((y - fitted) ** 2).sum())
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    vif = 1.0 / max(1.0 - r2, 1e-12)
    rows.append({"variable": column, "R2_against_other_predictors": r2, "VIF": vif})
  return pd.DataFrame(rows)


def compute_rda(base_dir: Path, rel: pd.DataFrame, domain: str) -> dict:
  base = Path(base_dir)
  position_map = {c: ".".join(c.split(".")[:2]) for c in rel.columns}
  gpos = pd.DataFrame({
    pos: rel[[c for c, mapped in position_map.items() if mapped == pos]].sum(axis=1)
    for pos in POSITION_ORDER if pos in set(position_map.values())
  }).T
  Y = np.sqrt(gpos.div(gpos.sum(axis=1).replace(0, np.nan), axis=0).fillna(0))

  env = pd.read_excel(base / "data/fiqui2.xlsx")
  env.columns = [str(c).strip() for c in env.columns]
  env["SampleMM"] = env["SampleMM"].astype(str).str.strip().replace({"V1.P1": "VI.P1"})
  for col in env.columns[3:]:
    env[col] = pd.to_numeric(env[col], errors="coerce")
  envagg = env.groupby("SampleMM").mean(numeric_only=True)
  common = [pos for pos in POSITION_ORDER if pos in Y.index and pos in envagg.index]
  Y = Y.loc[common]
  envagg = envagg.loc[common]
  missing = [c for c in RDA_VARIABLES if c not in envagg.columns or envagg[c].notna().sum() != len(common)]
  if missing:
    raise RuntimeError(f"Missing complete RDA predictors: {missing}")
  Z = envagg[RDA_VARIABLES].copy()
  Zs = (Z - Z.mean()) / Z.std(ddof=0).replace(0, 1)
  X = np.column_stack([np.ones(len(Zs)), Zs.to_numpy(float)])
  rank_x = int(np.linalg.matrix_rank(X))
  H = X @ np.linalg.pinv(X.T @ X) @ X.T
  Yarr = Y.to_numpy(float)
  Yc = Yarr - Yarr.mean(axis=0, keepdims=True)
  Yhat = H @ Yc
  u, singular, _ = np.linalg.svd(Yhat, full_matrices=False)
  site = u[:, :2] * singular[:2]
  site = _orient_axes(site)
  eig = singular ** 2
  pct = 100 * eig[:2] / max(float(eig.sum()), 1e-12)
  vectors = np.asarray([[np.corrcoef(Zs[col], site[:, axis])[0, 1] for axis in range(2)] for col in Zs.columns])
  ss_fit = float((Yhat ** 2).sum())
  ss_total = float((Yc ** 2).sum())
  r2 = ss_fit / ss_total if ss_total > 0 else np.nan
  pnum = rank_x - 1
  n = len(common)
  df_model = pnum
  df_residual = n - rank_x
  ss_residual = max(ss_total - ss_fit, 1e-12)
  pseudo_f = (ss_fit / df_model) / (ss_residual / df_residual)
  adjusted_r2 = 1 - (1 - r2) * (n - 1) / max(n - pnum - 1, 1)

  rng = np.random.default_rng(SEED)
  perm_f = []
  perm_eig = []
  for _ in range(N_PERMUTATIONS):
    permuted = Yc[rng.permutation(n), :]
    fitted = H @ permuted
    ss_perm = float((fitted ** 2).sum())
    ss_res_perm = max(float((permuted ** 2).sum()) - ss_perm, 1e-12)
    perm_f.append((ss_perm / df_model) / (ss_res_perm / df_residual))
    sval = np.linalg.svd(fitted, compute_uv=False)
    pe = np.zeros(2, dtype=float)
    pe[:min(2, len(sval))] = sval[:2] ** 2
    perm_eig.append(pe)
  perm_f = np.asarray(perm_f)
  perm_eig = np.asarray(perm_eig)
  p_global = (1 + int((perm_f >= pseudo_f).sum())) / (N_PERMUTATIONS + 1)
  axis_p = [(1 + int((perm_eig[:, axis] >= eig[axis]).sum())) / (N_PERMUTATIONS + 1) for axis in range(2)]

  scores = pd.DataFrame(site, columns=["RDA1", "RDA2"], index=common)
  scores.index.name = "Sample"
  scores["Lake"] = [pos.split(".")[0] for pos in common]
  env_vectors = pd.DataFrame(vectors, index=Zs.columns, columns=["RDA1", "RDA2"])
  env_vectors.index.name = "Variable"

  neutral = {"Other genera", "Other taxa", "Others", "Unclassified", "Unclassified taxa", "Unassigned", "Unknown"}
  genus_rows = []
  for genus in Y.columns:
    values = pd.to_numeric(Y[genus], errors="coerce").to_numpy(float)
    if np.nanstd(values) <= 1e-12:
      corr1 = corr2 = 0.0
    else:
      corr1 = float(np.corrcoef(values, site[:, 0])[0, 1])
      corr2 = float(np.corrcoef(values, site[:, 1])[0, 1])
      corr1 = corr1 if np.isfinite(corr1) else 0.0
      corr2 = corr2 if np.isfinite(corr2) else 0.0
    mean_abundance = float(gpos[genus].mean()) if genus in gpos.columns else 0.0
    strength = float(np.hypot(corr1, corr2))
    selection = strength * float(np.log1p(max(mean_abundance, 0.0)))
    genus_rows.append({"Genus": str(genus), "RDA1": corr1, "RDA2": corr2, "Vector_strength": strength, "Mean_relative_abundance_percent": mean_abundance, "Selection_score": selection})
  all_taxa = pd.DataFrame(genus_rows).set_index("Genus")
  eligible = all_taxa.loc[~all_taxa.index.isin(neutral)].copy()
  eligible = eligible[(eligible["Vector_strength"] >= 0.20) & (eligible["Mean_relative_abundance_percent"] > 0)]
  representative = eligible.sort_values(["Selection_score", "Vector_strength"], ascending=False).head(6)

  sample_rows = []
  for sample in SAMPLE_ORDER:
    position = ".".join(sample.split(".")[:2])
    included = position in common
    row = {
      "domain": domain,
      "original_sample_id": sample,
      "standardized_sample_id": sample,
      "pooled_sampling_position": position,
      "present_in_abundance": sample in rel.columns,
      "present_in_environmental_metadata": position in envagg.index,
      "included_in_RDA": included,
      "exclusion_reason": "" if included else "No matched abundance/environmental record",
      "RDA1": float(scores.loc[position, "RDA1"]) if included else np.nan,
      "RDA2": float(scores.loc[position, "RDA2"]) if included else np.nan,
      "panel": "Figure 4D / S17A" if domain == "Bacteria" else "Figure 5D / S17B",
      "point_drawn": bool(included),
      "note": "Dry and rainy metagenomes pooled at the sampling-position level because physicochemical measurements are position-level." if included else "",
    }
    sample_rows.append(row)
  sample_audit = pd.DataFrame(sample_rows)
  site_pair_rows = []
  coords = scores[["RDA1", "RDA2"]].to_numpy(float)
  diagonal = float(np.hypot(np.ptp(coords[:, 0]), np.ptp(coords[:, 1])))
  threshold = max(diagonal * 0.01, 1e-12)
  for i in range(len(common)):
    for j in range(i + 1, len(common)):
      dd = float(np.linalg.norm(coords[i] - coords[j]))
      if dd <= threshold:
        site_pair_rows.append({"position_1": common[i], "position_2": common[j], "ordination_distance": dd, "threshold": threshold})

  model_stats = {
    "domain": domain,
    "n_raw_metagenomes": len([s for s in SAMPLE_ORDER if s in rel.columns]),
    "n_sampling_positions": n,
    "n_predictors": pnum,
    "df_model": df_model,
    "df_residual": df_residual,
    "R2": float(r2),
    "adjusted_R2": float(adjusted_r2),
    "pseudo_F": float(pseudo_f),
    "global_permutation_p": float(p_global),
    "RDA1_eigenvalue": float(eig[0]),
    "RDA2_eigenvalue": float(eig[1]),
    "RDA1_constrained_variance_percent": float(pct[0]),
    "RDA2_constrained_variance_percent": float(pct[1]),
    "RDA1_axis_permutation_p": float(axis_p[0]),
    "RDA2_axis_permutation_p": float(axis_p[1]),
    "permutations": N_PERMUTATIONS,
    "seed": SEED,
    "variables": "; ".join(RDA_VARIABLES),
    "community_transformation": "Hellinger: square root of pooled position-level relative proportions",
    "predictor_standardization": "z-score, population standard deviation (ddof=0)",
  }
  return {
    "scores": scores,
    "vectors": env_vectors,
    "taxon_vectors": representative,
    "taxon_vectors_all": all_taxa,
    "pct": pct,
    "r2": float(r2),
    "adjusted_r2": float(adjusted_r2),
    "F": float(pseudo_f),
    "p": float(p_global),
    "axis_p": axis_p,
    "eigenvalues": eig,
    "variables": list(RDA_VARIABLES),
    "n": n,
    "vif": _vif_table(Zs),
    "sample_audit": sample_audit,
    "near_overlap_pairs": pd.DataFrame(site_pair_rows, columns=["position_1", "position_2", "ordination_distance", "threshold"]),
    "model_stats": pd.DataFrame([model_stats]),
    "transformed_community": Y,
    "standardized_environment": Zs,
    "pooled_abundance": gpos,
  }


def library_versions() -> dict:
  return {
    "python": platform.python_version(),
    "numpy": np.__version__,
    "pandas": pd.__version__,
    "scipy": scipy.__version__,
    "scikit_learn": sklearn.__version__,
  }


def write_json(path: Path, value: object) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(json.dumps(value, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
