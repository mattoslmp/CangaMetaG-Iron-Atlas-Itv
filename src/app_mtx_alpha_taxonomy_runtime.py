from __future__ import annotations

"""Runtime helpers for complete MTX display and article taxonomy overlap.

The helpers use the app's existing renderers and packaged source tables. They do
not alter scientific values. They are kept outside the source-transform file so
ordinary Python tests can exercise the data selection and categorical handling.
"""

from collections.abc import Callable, Mapping, Sequence
from typing import Any

import numpy as np
import pandas as pd


def install_categorical_group_guard() -> None:
  """Allow statistical grouping columns backed by pandas Categorical.

  Only the grouping labels are converted to object/string. Numeric observations,
  group membership, test families and multiple-testing correction are unchanged.
  """
  from src import article_inference_statistics as statistics

  if getattr(statistics, "_categorical_group_guard_installed", False):
    return

  original = statistics.group_comparison_tests

  def categorical_safe_group_comparison_tests(
    frame: pd.DataFrame,
    value_column: str,
    group_column: str,
    feature_column: str | None = None,
    *,
    minimum_group_size: int = 2,
  ) -> pd.DataFrame:
    safe_frame = frame.copy() if isinstance(frame, pd.DataFrame) else frame
    if isinstance(safe_frame, pd.DataFrame) and group_column in safe_frame.columns:
      labels = safe_frame[group_column].astype(object)
      safe_frame[group_column] = labels.where(pd.notna(labels), "Unclassified").astype(str)
    return original(
      safe_frame,
      value_column,
      group_column,
      feature_column,
      minimum_group_size=minimum_group_size,
    )

  statistics.group_comparison_tests = categorical_safe_group_comparison_tests
  statistics._categorical_group_guard_installed = True


def article_overlap_broad_group(value: object) -> str:
  text = str(value or "")
  if any(token in text for token in ("AMD", "Akron", "Richmond")):
    return "AMD systems"
  if any(token in text for token in ("Lake Towuti", "Lake Matano", "Lake Superior")):
    return "Ferruginous lakes/sediments"
  if "Hydrothermal" in text:
    return "Hydrothermal Fe-rich mats"
  return "Other/unassigned"


def metatranscriptome_matrix_columns(
  metadata: pd.DataFrame,
  numeric_columns: Sequence[str],
  data_columns: Sequence[str],
) -> tuple[pd.DataFrame, list[str]]:
  """Return every MTX metadata record and its matching ST8 matrix column."""
  if metadata is None or metadata.empty:
    return pd.DataFrame(), []
  layer = metadata.get("data_layer", pd.Series("", index=metadata.index)).astype(str)
  mtx_metadata = metadata[layer.str.casefold().str.contains("metatranscript", na=False)].copy()
  numeric = {str(column) for column in numeric_columns}
  available = {str(column) for column in data_columns}
  fields = [
    field for field in (
      "ST8_matrix_column",
      "matrix_column_all_KO",
      "matrix_column_iron_KO",
      "matrix_column_selected",
      "matrix_column",
    )
    if field in mtx_metadata.columns
  ]
  selected: list[str] = []
  for _, row in mtx_metadata.iterrows():
    for field in fields:
      candidate = str(row.get(field, "")).strip()
      if candidate and candidate in numeric and candidate in available:
        selected.append(candidate)
        break
  # Defensive fallback for packages whose metadata mapping field was renamed.
  if not selected:
    selected = [
      str(column) for column in numeric_columns
      if str(column) in available
      and any(token in str(column).casefold() for token in ("mtx", "metatranscript"))
    ]
  return mtx_metadata, list(dict.fromkeys(selected))


def render_complete_metatranscriptome_panel(
  namespace: Mapping[str, Any],
  *,
  metadata: pd.DataFrame,
  numeric_columns: Sequence[str],
  data: pd.DataFrame,
  render_pair: Callable[..., Any],
  base_key: str,
) -> None:
  """Render all packaged MTX samples with the full KO matrix by default."""
  st = namespace["st"]
  txt = namespace["txt"]
  show_table = namespace["show_table"]
  csv_button = namespace["csv_button"]

  mtx_metadata, mtx_columns = metatranscriptome_matrix_columns(
    metadata,
    numeric_columns,
    data.columns,
  )
  if not mtx_columns:
    st.info(txt(
      "Nenhuma coluna de metatranscriptoma foi vinculada à matriz ST8.",
      "No metatranscriptome column was linked to the ST8 matrix.",
    ))
    return

  with st.expander(
    txt(
      "Metatranscriptomas — estudos e identificadores",
      "Metatranscriptomes — studies and identifiers",
    ),
    expanded=True,
  ):
    display_columns = [
      column for column in (
        "sample_id_created_this_study",
        "taxon_oid",
        "ST8_matrix_column",
        "matrix_column_all_KO",
        "Study Name",
        "Genome Name / Sample Name",
        "ST8_group",
        "data_layer",
        "NCBI Bioproject Accession",
        "SRA Run",
      )
      if column in mtx_metadata.columns
    ]
    show_table(
      mtx_metadata[display_columns],
      f"{base_key}_all_metatranscriptome_metadata",
      height=430,
    )
    csv_button(
      mtx_metadata[display_columns],
      f"{base_key}_all_metatranscriptomes_metadata.csv",
      txt(
        "Baixar metadados dos metatranscriptomas",
        "Download metatranscriptome metadata",
      ),
    )

  render_pair(
    "Metatranscriptomas — todas as amostras, estudos e identificadores",
    "Metatranscriptomes — all samples, studies and identifiers",
    mtx_columns,
    "metatranscriptomics_all_samples",
    (
      f"Todas as {len(mtx_columns)} amostras de metatranscriptoma presentes na "
      f"ST8 são exibidas com a matriz completa de {len(data)} KOs/marcadores por padrão."
    ),
    (
      f"All {len(mtx_columns)} metatranscriptome samples present in ST8 are "
      f"displayed with the complete {len(data)}-KO/marker matrix by default."
    ),
  )


def render_taxonomy_article_overlap_panel(namespace: Mapping[str, Any]) -> None:
  """Render article Venn diagrams and common-taxa heatmaps inside Taxonomy."""
  st = namespace["st"]
  txt = namespace["txt"]
  px = namespace["px"]
  load_st8_csv = namespace["_load_st8_csv"]
  load_sheet = namespace["load_sheet"]
  venn_region_sets = namespace["venn_region_sets"]
  simple_venn_figure = namespace["simple_venn_figure"]
  render_plotly_downloadable = namespace["render_plotly_downloadable"]
  show_table = namespace["show_table"]
  csv_button = namespace["csv_button"]

  taxonomy, _ = load_st8_csv("st8_taxonomy_summary_by_group.csv")
  if taxonomy.empty:
    try:
      taxonomy = load_sheet("table8", "Taxonomy_summary_by_group")
    except Exception:
      taxonomy = pd.DataFrame()
  required = {
    "taxonomy_level",
    "ST8_group",
    "data_layer",
    "matrix_column",
    "taxon",
    "count_or_abundance",
  }
  if taxonomy.empty or not required.issubset(taxonomy.columns):
    st.info(txt(
      "As tabelas taxonômicas de sobreposição do artigo não estão disponíveis.",
      "The article taxonomic-overlap tables are not available.",
    ))
    return

  st.markdown("### " + txt(
    "Táxons compartilhados entre metagenomas — Venn e heatmap do artigo",
    "Taxa shared across metagenomes — article Venn and heatmap",
  ))
  level = st.radio(
    txt("Nível taxonômico da comparação", "Taxonomic rank for comparison"),
    ["Phylum", "Order", "Family"],
    horizontal=True,
    key="taxonomy_article_overlap_level_v2",
  )
  work = taxonomy[
    taxonomy["taxonomy_level"].astype(str).eq(level)
    & taxonomy["data_layer"].astype(str).str.casefold().str.contains(
      "metagenomic", na=False
    )
  ].copy()
  work["count_or_abundance"] = pd.to_numeric(
    work["count_or_abundance"], errors="coerce"
  ).fillna(0.0)
  work = work[work["count_or_abundance"] > 0].copy()
  work["article_environment_group"] = work["ST8_group"].map(
    article_overlap_broad_group
  )
  article_groups = [
    "AMD systems",
    "Ferruginous lakes/sediments",
    "Hydrothermal Fe-rich mats",
  ]
  work = work[work["article_environment_group"].isin(article_groups)].copy()
  if work.empty:
    st.info(txt(
      "Nenhum táxon positivo foi encontrado para esta seleção.",
      "No positive taxon was found for this selection.",
    ))
    return

  set_map = {
    group: set(
      work.loc[work["article_environment_group"].eq(group), "taxon"]
      .dropna().astype(str)
    )
    for group in article_groups
  }
  set_map = {name: values for name, values in set_map.items() if values}
  if len(set_map) < 2:
    st.info(txt(
      "São necessários pelo menos dois grupos para o diagrama.",
      "At least two groups are required for the diagram.",
    ))
    return

  regions = venn_region_sets(set_map)
  region_summary = pd.DataFrame([
    {
      "region_key": key,
      "region": region["label"],
      "description": region["description"],
      "compared_sets": "; ".join(region["sets"]),
      "n_taxa": len(region["members"]),
    }
    for key, region in regions.items()
  ])
  common_taxa = sorted(set.intersection(*set_map.values()))
  common_table = pd.DataFrame({
    "taxonomy_level": level,
    "taxon_common_to_all_article_groups": common_taxa,
  })

  venn = simple_venn_figure(
    set_map,
    txt(
      f"Sobreposição de {level} entre grupos metagenômicos do artigo",
      f"{level} overlap among article metagenomic groups",
    ),
  )
  if venn is not None:
    render_plotly_downloadable(
      venn,
      key=f"taxonomy_article_mgx_venn_{level}",
      basename=f"SupplementaryFigure30_{level}_metagenomic_Venn",
      audit_input_table=work[[
        "taxonomy_level", "ST8_group", "data_layer", "matrix_column",
        "taxon", "count_or_abundance",
      ]],
      audit_processed_table=work[[
        "taxonomy_level", "article_environment_group", "matrix_column",
        "taxon", "count_or_abundance",
      ]],
      audit_output_table=region_summary,
      audit_method=(
        "Presence defined by count_or_abundance > 0; article sets: AMD systems, "
        "ferruginous lakes/sediments and hydrothermal Fe-rich mats."
      ),
      audit_input_source="data/st8_taxonomy_summary_by_group.csv",
      audit_script="scripts/generate_core_taxonomy_overlap_figure.py",
      audit_instructions="python scripts/generate_core_taxonomy_overlap_figure.py",
    )

  if common_taxa:
    common_work = work[work["taxon"].astype(str).isin(common_taxa)].copy()
    abundance = common_work.pivot_table(
      index="taxon",
      columns="matrix_column",
      values="count_or_abundance",
      aggfunc="sum",
      fill_value=0.0,
    )
    abundance = abundance.loc[
      abundance.sum(axis=1).sort_values(ascending=False).index
    ]
    means = abundance.mean(axis=1)
    standard = abundance.std(axis=1, ddof=0).replace(0.0, np.nan)
    zscore = abundance.sub(means, axis=0).div(standard, axis=0).fillna(0.0)
    heatmap = px.imshow(
      zscore,
      aspect="auto",
      color_continuous_scale="RdBu_r",
      color_continuous_midpoint=0,
      title=txt(
        f"{level} compartilhados pelos três grupos — todas as amostras metagenômicas",
        f"{level} shared by all three groups — all metagenomic samples",
      ),
      labels={
        "x": txt("Amostra metagenômica", "Metagenomic sample"),
        "y": level,
        "color": "Row z-score",
      },
    )
    heatmap.update_layout(
      height=max(620, 28 * len(zscore) + 240),
      width=max(1500, 42 * len(zscore.columns) + 520),
      margin=dict(l=260, r=100, t=105, b=250),
      meta={
        "preserve_cell_geometry": True,
        "force_all_y_ticks": True,
        "no_synthetic_values": True,
      },
    )
    heatmap.update_xaxes(tickangle=-55, automargin=True)
    heatmap.update_yaxes(automargin=True)
    render_plotly_downloadable(
      heatmap,
      key=f"taxonomy_article_mgx_common_heatmap_{level}",
      basename=f"SupplementaryFigure31_{level}_common_taxa_metagenomic_heatmap",
      audit_input_table=common_work,
      audit_processed_table=zscore.reset_index(),
      audit_output_table=common_table,
      audit_method=(
        "Taxa present in all three article environmental groups; exact "
        "per-metagenome abundance followed by row z-score."
      ),
      audit_input_source="data/st8_taxonomy_summary_by_group.csv",
      audit_script="scripts/figures/generate_s31_taxonomic_levels_revision3.py",
      audit_instructions=(
        "python scripts/figures/generate_s31_taxonomic_levels_revision3.py "
        "--base-dir . --article-root ."
      ),
    )
  else:
    st.info(txt(
      f"Nenhum {level.lower()} foi detectado simultaneamente nos três grupos.",
      f"No {level.lower()} was detected simultaneously in all three groups.",
    ))

  with st.expander(
    txt("Táxons compartilhados e regiões do Venn", "Shared taxa and Venn regions"),
    expanded=False,
  ):
    show_table(common_table, f"taxonomy_article_common_{level}", height=320)
    show_table(region_summary, f"taxonomy_article_regions_{level}", height=320)
    csv_button(
      common_table,
      f"taxonomy_article_common_{level}.csv",
      txt("Baixar táxons compartilhados", "Download shared taxa"),
    )
