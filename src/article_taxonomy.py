from __future__ import annotations

"""Shared article/app taxonomy data layer.

The static article figures and interactive panels use the same packaged CDS OTU
and taxonomy files, sample map, strict per-sample <1% rule and colour
assignments. Current NCBI labels are applied to names only; counts never change.
"""

from pathlib import Path
import re

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .ncbi_taxonomy_harmonization import (
  TARGET_RANKS,
  harmonize_taxonomy_frame,
  load_current_taxonomy_table,
  load_name_updates,
  transfer_palette_names,
)
from .taxonomy_palette import build_palette, load_palette
from .taxonomy_normalization import (
  OTHER_TAXA_LT1,
  THRESHOLD_PERCENT,
  UNCLASSIFIED,
  aggregate_counts,
  collapse_below_threshold,
)


BASE_DIR = Path(__file__).resolve().parents[1]
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
  "TI.P1.D", "TI.P1.R", "TI.P2.D", "TI.P2.R", "TI.P3.D", "TI.P3.R", "TI.P4.D", "TI.P4.R",
  "VI.P1.D", "VI.P1.R", "VI.P2.D", "VI.P2.R",
]
SEASON_SUFFIX = {"Dry": ".D", "Rainy": ".R"}
ARTICLE_ALPHA_ORDER = ["AM-D", "AM-R", "TIA-D", "TIA-R", "TI-D", "TI-R", "VI-D", "VI-R"]
ARTICLE_ALPHA_PALETTE = {
  "AM-D": "#0072B2", "AM-R": "#E69F00", "TIA-D": "#009E73", "TIA-R": "#D55E00",
  "TI-D": "#CC79A7", "TI-R": "#56B4E9", "VI-D": "#F0E442", "VI-R": "#7E57C2",
}


def clean_sample_name(value: object) -> str:
  token = str(value).split("_")[0].strip().strip(".")
  return SAMPLE_MAP.get(token, token)


def sample_metadata(sample: object) -> dict[str, str]:
  text = str(sample).strip()
  match = re.match(r"^(AM|TIA|TI|VI)\.P(\d+)\.(D|R)$", text)
  if not match:
    return {
      "sample.id": text, "lake": "Other", "season": "Unknown",
      "lake_season": "Other-U", "sampling_position": "", "environment_feature": "Amazonian lateritic lake sediment",
    }
  lake, position, suffix = match.groups()
  season = "Dry" if suffix == "D" else "Rainy"
  return {
    "sample.id": text,
    "lake": lake,
    "season": season,
    "lake_season": f"{lake}-{suffix}",
    "sampling_position": f"P{position}",
    "environment_feature": "Amazonian lateritic lake sediment",
  }


def load_article_inputs(base_dir: Path | str | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
  root = Path(base_dir) if base_dir is not None else BASE_DIR
  otu_path = root / "data" / "resultado.cds.otu.tab"
  tax_path = root / "data" / "resultado.cds.tax.tab"
  otu = pd.read_csv(otu_path, sep="\t", index_col=0)
  otu.columns = [clean_sample_name(column) for column in otu.columns]
  otu = otu.apply(pd.to_numeric, errors="coerce").fillna(0.0)
  otu = otu.reindex(columns=[sample for sample in SAMPLE_ORDER if sample in otu.columns])
  tax = load_current_taxonomy_table(
    original_path=tax_path,
    current_path=root / "data" / "resultado.cds.tax.ncbi_current.tab",
    updates_path=root / "data" / "ncbi_taxonomy_name_updates.csv",
  )
  tax.columns = [str(column).strip() for column in tax.columns]
  for column in tax.columns:
    tax[column] = tax[column].fillna("Unclassified").astype(str).str.strip().replace({"": "Unclassified"})
  return otu, tax


def _rank_column(rank: str, tax: pd.DataFrame) -> str:
  wanted = str(rank).split("—")[0].strip().title()
  aliases = [wanted, wanted.capitalize(), wanted.title()]
  for alias in aliases:
    if alias in tax.columns:
      return alias
  raise KeyError(f"Taxonomy rank not found: {rank}")


def domain_rank_matrices(
  domain: str,
  rank: str,
  top_n: int | None = None,
  base_dir: Path | str | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
  """Return strict per-sample <1% matrices used by article and app.

  ``top_n`` remains in the signature for backward compatibility but is ignored:
  every classified taxon reaching 1% in at least one sample remains explicit.
  """
  otu, tax = load_article_inputs(base_dir)
  rank_column = _rank_column(rank, tax)
  full_counts = aggregate_counts(otu, tax, domain, rank_column)
  full_counts = full_counts.reindex(columns=[sample for sample in SAMPLE_ORDER if sample in full_counts.columns])
  full_relative = full_counts.div(full_counts.sum(axis=0).replace(0, np.nan), axis=1).fillna(0.0) * 100.0
  displayed = collapse_below_threshold(full_relative)
  displayed_counts = pd.DataFrame(0.0, index=displayed.index, columns=displayed.columns)
  for sample in displayed.columns:
    below = [
      taxon for taxon in full_relative.index
      if str(taxon) != UNCLASSIFIED and float(full_relative.at[taxon, sample]) < THRESHOLD_PERCENT
    ]
    for taxon in displayed.index:
      if taxon == OTHER_TAXA_LT1:
        displayed_counts.at[taxon, sample] = float(full_counts.loc[below, sample].sum())
      elif taxon in full_counts.index and (
        taxon == UNCLASSIFIED or float(full_relative.at[taxon, sample]) >= THRESHOLD_PERCENT
      ):
        displayed_counts.at[taxon, sample] = float(full_counts.at[taxon, sample])
  return displayed_counts, displayed


def _article_palette(taxa: list[str], base_dir: Path | str | None = None) -> dict[str, str]:
  root = Path(base_dir) if base_dir is not None else BASE_DIR
  updates = load_name_updates(root / "data" / "ncbi_taxonomy_name_updates.csv")
  legacy = load_palette(root / "data" / "taxonomy_palette.json")
  transferred = transfer_palette_names(legacy, updates)
  generated = build_palette(taxa, legacy)
  output: dict[str, str] = {}
  used: set[str] = set()
  for taxon in taxa:
    candidate = str(transferred.get(taxon, generated.get(taxon, "#64748B"))).upper()
    if candidate in used:
      candidate = str(generated.get(taxon, candidate)).upper()
    output[taxon] = candidate
    used.add(candidate)
  return output


def article_taxonomy_profile_table(
  domain: str,
  rank: str,
  view_mode: str = "Individual samples",
  top_n: int | None = None,
  base_dir: Path | str | None = None,
) -> pd.DataFrame:
  counts, relative = domain_rank_matrices(domain, rank, top_n=top_n, base_dir=base_dir)
  rows: list[dict[str, object]] = []
  for sample in relative.columns:
    metadata = sample_metadata(sample)
    for taxon in relative.index:
      rows.append({
        "group": sample,
        "taxon": str(taxon),
        "count": float(counts.loc[taxon, sample]),
        "abundance": float(relative.loc[taxon, sample]),
        "domain": domain,
        "rank": rank,
        "source_sheet": "data/resultado.cds.otu.tab + data/resultado.cds.tax.tab",
        **metadata,
      })
  frame = pd.DataFrame(rows)
  if frame.empty or str(view_mode).lower().startswith("individual"):
    return frame
  grouped_counts = frame.groupby(["lake_season", "taxon"], as_index=False)["count"].sum()
  totals = grouped_counts.groupby("lake_season")["count"].transform("sum").replace(0, np.nan)
  grouped_counts["abundance"] = grouped_counts["count"].div(totals).fillna(0.0) * 100.0
  grouped_counts = grouped_counts.rename(columns={"lake_season": "group"})
  grouped_counts["lake"] = grouped_counts["group"].astype(str).str.extract(r"^(AM|TIA|TI|VI)", expand=False)
  grouped_counts["season"] = grouped_counts["group"].astype(str).map(lambda value: "Dry" if value.endswith("-D") else "Rainy" if value.endswith("-R") else "Unknown")
  grouped_counts["sample.id"] = grouped_counts["group"]
  grouped_counts["sampling_position"] = "Aggregated"
  grouped_counts["environment_feature"] = "Amazonian lateritic lake sediment"
  grouped_counts["domain"] = domain
  grouped_counts["rank"] = rank
  grouped_counts["source_sheet"] = "data/resultado.cds.otu.tab + data/resultado.cds.tax.tab"
  return grouped_counts


def article_season_barplot(
  domain: str,
  rank: str,
  season: str,
  top_n: int | None = None,
  base_dir: Path | str | None = None,
) -> tuple[go.Figure, pd.DataFrame, pd.DataFrame]:
  counts, relative = domain_rank_matrices(domain, rank, top_n=top_n, base_dir=base_dir)
  season_name = "Dry" if str(season).casefold().startswith("d") else "Rainy"
  suffix = SEASON_SUFFIX[season_name]
  samples = [sample for sample in SAMPLE_ORDER if sample.endswith(suffix) and sample in relative.columns]
  taxa = [str(taxon) for taxon in relative.index]
  palette = _article_palette(taxa, base_dir)
  figure = go.Figure()
  long_rows: list[dict[str, object]] = []
  for taxon in taxa:
    values = relative.loc[taxon, samples].astype(float).to_numpy()
    raw_counts = counts.loc[taxon, samples].astype(float).to_numpy()
    figure.add_trace(go.Bar(
      x=values,
      y=samples,
      name=taxon,
      orientation="h",
      marker={"color": palette[taxon], "line": {"color": "white", "width": 0.35}},
      customdata=np.array([
        raw_counts,
        values,
        [domain] * len(samples),
        [rank] * len(samples),
        [sample_metadata(sample)["lake"] for sample in samples],
        [sample_metadata(sample)["season"] for sample in samples],
      ], dtype=object).T,
      text=[f"{value:.1f}%" if taxon == UNCLASSIFIED and value > 0 else "" for value in values],
      textposition="inside",
      insidetextanchor="middle",
      hovertemplate=(
        "<b>%{y}</b><br>Taxon: " + taxon
        + "<br>Exact percentage: %{x:.6f}%"
        + "<br>Original relative abundance: %{customdata[1]:.6f}%"
        + "<br>CDS count: %{customdata[0]:,.0f}"
        + "<br>Domain: %{customdata[2]}<br>Taxonomic level: %{customdata[3]}"
        + "<br>Lake: %{customdata[4]}<br>Season: %{customdata[5]}<extra></extra>"
      ),
    ))
    for sample, value, count in zip(samples, values, raw_counts):
      long_rows.append({
        "domain": domain, "rank": rank, "season": season_name,
        "sample": sample, "taxon": taxon, "count": float(count),
        "relative_abundance_percent": float(value), "color": palette[taxon],
        "source": "data/resultado.cds.otu.tab + data/resultado.cds.tax.tab",
      })
  figure.update_layout(
    title={"text": f"{domain} — {rank} — {season_name} season", "x": 0.01, "xanchor": "left"},
    barmode="stack",
    height=max(560, 45 * max(1, len(samples)) + 170),
    margin={"l": 95, "r": 250, "t": 88, "b": 75},
    xaxis={"title": "Relative abundance (%)", "range": [0, 100], "ticksuffix": "%"},
    yaxis={"title": "CDS-classified sediment sample", "categoryorder": "array", "categoryarray": samples, "autorange": "reversed"},
    legend={"title": {"text": rank}, "font": {"size": 10}},
    font={"family": "Arial, Helvetica, sans-serif", "size": 13, "color": "#111827"},
    meta={
      "article_source": "scripts/generate_final_domain_taxonomy_figures.py",
      "same_input_as_static_figure": True,
      "season_panel": season_name,
      "ncbi_taxonomy_labels": True,
      "other_taxa_rule": "strictly below 1% per sample; exactly 1% remains explicit",
      "unclassified_separate_with_exact_percentage_labels": True,
      "top_n": None,
    },
  )
  table = pd.DataFrame(long_rows)
  matrix = relative.loc[:, samples].copy()
  matrix.insert(0, "taxon", matrix.index)
  matrix = matrix.reset_index(drop=True)
  return figure, table, matrix


def article_static_source_validation(
  domain: str,
  rank: str = "Phylum",
  top_n: int | None = None,
  base_dir: Path | str | None = None,
) -> pd.DataFrame:
  root = Path(base_dir) if base_dir is not None else BASE_DIR
  stem = "Figure2_taxonomic_phylum_bacteria_horizontal_CDS" if str(domain).casefold() == "bacteria" else "Figure3_taxonomic_phylum_archaea_horizontal_CDS"
  path = root / "data" / "final_publication_derived" / f"{stem}_source.csv"
  _, current = domain_rank_matrices(domain, rank, top_n=top_n, base_dir=root)
  if not path.exists():
    # Figures 2 and 3 are generated directly from these packaged canonical
    # inputs. Some releases omit the redundant derived CSV; that is not a
    # missing scientific source and must not invalidate the app panel.
    return pd.DataFrame([{
      "domain": domain,
      "rank": rank,
      "static_source": "data/resultado.cds.otu.tab; data/resultado.cds.tax.tab",
      "source_resolution": "canonical article inputs (derived source CSV not packaged)",
      "status": "PASS",
      "max_absolute_difference": 0.0,
      "compared_cells": int(current.size),
      "static_total_percent": float(current.to_numpy(float).sum()),
      "interactive_total_percent": float(current.to_numpy(float).sum()),
      "source_inputs": "data/resultado.cds.otu.tab; data/resultado.cds.tax.tab",
      "values_modified": False,
    }])
  expected = pd.read_csv(path, index_col=0)
  expected.columns = [clean_sample_name(column) for column in expected.columns]
  update_map = load_name_updates(root / "data" / "ncbi_taxonomy_name_updates.csv")
  label_frame = pd.DataFrame({rank: expected.index.astype(str)})
  expected.index = harmonize_taxonomy_frame(label_frame, update_map, ranks=[rank])[rank].astype(str)
  expected = expected.apply(pd.to_numeric, errors="coerce").fillna(0.0).groupby(level=0).sum()
  expected = expected.reindex(columns=[sample for sample in SAMPLE_ORDER if sample in expected.columns], fill_value=0.0)
  all_rows = sorted(set(expected.index.astype(str)).union(current.index.astype(str)), key=str.casefold)
  all_cols = [sample for sample in SAMPLE_ORDER if sample in set(expected.columns).union(current.columns)]
  left = expected.reindex(index=all_rows, columns=all_cols, fill_value=0.0)
  right = current.reindex(index=all_rows, columns=all_cols, fill_value=0.0)
  difference = (left - right).abs()
  max_difference = float(difference.to_numpy(float).max()) if difference.size else 0.0
  return pd.DataFrame([{
    "domain": domain,
    "rank": rank,
    "static_source": str(path.relative_to(root)),
    "status": "PASS" if max_difference <= 1e-8 else "FAIL",
    "max_absolute_difference": max_difference,
    "compared_cells": int(difference.size),
    "static_total_percent": float(left.to_numpy(float).sum()),
    "interactive_total_percent": float(right.to_numpy(float).sum()),
    "source_inputs": "data/resultado.cds.otu.tab; data/resultado.cds.tax.tab",
  }])


def load_article_alpha_source(base_dir: Path | str | None = None) -> pd.DataFrame:
  root = Path(base_dir) if base_dir is not None else BASE_DIR
  path = root / "data" / "final_publication_derived" / "SupplementaryFigure4_alpha_diversity_CDS_32999_source.csv"
  if not path.exists():
    return pd.DataFrame()
  frame = pd.read_csv(path)
  if "Lake_season" in frame.columns:
    frame["Lake_season"] = pd.Categorical(frame["Lake_season"], categories=ARTICLE_ALPHA_ORDER, ordered=True)
    frame = frame.sort_values(["Lake_season", "Sample"]).reset_index(drop=True)
  return frame


def _transparent_hex(hex_color: str, alpha: float = 0.52) -> str:
  text = str(hex_color).lstrip("#")
  if len(text) != 6:
    return f"rgba(100,116,139,{alpha})"
  red, green, blue = int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)
  return f"rgba({red},{green},{blue},{alpha})"


def article_alpha_boxplot(base_dir: Path | str | None = None) -> tuple[go.Figure, pd.DataFrame]:
  source = load_article_alpha_source(base_dir)
  if source.empty:
    return go.Figure(), source
  metrics = [("Observed_OTUs", "Observed OTUs"), ("Chao1", "Chao1 richness"), ("Shannon", "Shannon diversity")]
  figure = make_subplots(rows=1, cols=3, subplot_titles=[label for _, label in metrics], horizontal_spacing=0.075)
  for column_index, (metric, label) in enumerate(metrics, start=1):
    for group in ARTICLE_ALPHA_ORDER:
      subset = source[source["Lake_season"].astype(str) == group].copy()
      if subset.empty:
        continue
      values = pd.to_numeric(subset[metric], errors="coerce").to_numpy(float)
      samples = subset["Sample"].astype(str).to_numpy()
      figure.add_trace(go.Box(
        x=[group] * len(values),
        y=values,
        name=group,
        legendgroup=group,
        showlegend=column_index == 1,
        marker={"color": ARTICLE_ALPHA_PALETTE[group], "size": 9, "line": {"color": "black", "width": 0.8}},
        line={"color": ARTICLE_ALPHA_PALETTE[group], "width": 1.5},
        fillcolor=_transparent_hex(ARTICLE_ALPHA_PALETTE[group]),
        boxpoints="all",
        jitter=0.22,
        pointpos=0,
        customdata=np.column_stack([samples]),
        hovertemplate=(
          "<b>%{customdata[0]}</b><br>Lake–season: " + group
          + "<br>" + label + ": %{y:.6g}<extra></extra>"
        ),
      ), row=1, col=column_index)
    figure.update_xaxes(
      title="Lake–season group",
      categoryorder="array",
      categoryarray=ARTICLE_ALPHA_ORDER,
      tickangle=-35,
      row=1,
      col=column_index,
    )
    figure.update_yaxes(title=label, row=1, col=column_index)
  figure.update_layout(
    title={"text": "CDS alpha diversity after deterministic rarefaction to 32,999 CDS", "x": 0.01, "xanchor": "left"},
    height=740,
    margin={"l": 70, "r": 35, "t": 115, "b": 185},
    boxmode="group",
    legend={
      "title": {"text": "Lake–season group"},
      "orientation": "h",
      "y": -0.34,
      "yanchor": "top",
      "x": 0.0,
      "xanchor": "left",
    },
    font={"family": "Arial, Helvetica, sans-serif", "size": 13, "color": "#111827"},
    meta={
      "article_figure": "Supplementary Figure 4",
      "article_source": "data/final_publication_derived/SupplementaryFigure4_alpha_diversity_CDS_32999_source.csv",
      "article_script": "scripts/final_publication_figures/06_recalculate_rarefaction_alpha_32999.py",
      "same_values_order_and_palette_as_article": True,
      "preserve_legend_position": True,
    },
  )
  return figure, source
