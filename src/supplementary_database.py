from __future__ import annotations

from pathlib import Path
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from .ncbi_taxonomy_harmonization import load_current_taxonomy_table

from ._helpers import BASE_DIR, empty_frame, heatmap, numeric_columns, read_table, row_zscore
from .sample_metadata import amazonian_sample_metadata, lake_column_metadata, publication_sample_id
from .taxonomy_palette import build_palette as build_taxonomy_palette, load_palette as load_taxonomy_palette

ASSETS_DIR = BASE_DIR / 'outputs' / 'app_supplementary_figures'
AUTHORS = 'Leandro de Mattos Pereira, José Augusto Pires Bittencourt, Vitor Cirilo Araujo Santos, Ronnie Alves, Eder Pires, Prafulla Kumar Sahoo, José Tasso Felix Guimarães, Bruno Garcia Simões, Renato R. Moreira-Oliveira, Guilherme Oliveira and Gisele Lopes Nunes'
AFFILIATION = 'Instituto Tecnológico Vale, Belém, PA, Brazil'
CORRESPONDENCE = 'Gisele Lopes Nunes, gisele.nunes@itv.org; Leandro de Mattos Pereira, leandro.pereira@pq.itv.org'
ARTICLE_CITATION = 'Pereira et al. Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling.'
SALAZAR_CITATION = 'Salazar et al. (2019), curated biogeochemical marker reference set.'
BIOGEOCHEMICAL_DISPLAY_NAME = 'Biogeochemical marker'
TAXONOMY_LEVELS = [
  'Domain', 'Phylum — Bacteria', 'Phylum — Archaea', 'Class', 'Order',
  'Family', 'Genus — Bacteria', 'Genus — Archaea', 'Species — Bacteria',
  'Species — Archaea',
]
ST8_ALL_KO_SHEET = 'ST8 — all KO biomarkers'
ST8_SELECTED_SEDIMENTS_SHEET = 'ST8 — selected sediments'
ST8_IRON_ALL_SHEET = 'ST8- Iron metabolism KO -marker'
ST8_IRON_SELECTED_SHEET = 'ST8-Iron metabolism - selected'

TABLE_FILES = {
  'table1': 'data/resultado.cds.otu.tab',
  'table2': 'data/Supplementary_table_7-MAGS-Quality-Genome_Lineage-Classification.xlsx',
  'table3': 'data/Supplementary_Table_11_antiSMASH_MAG_BGC_clusters.xlsx',
  'table4': 'tables/Supplementary_Table_4.xlsx',
  'table5': 'tables/Supplementary_Table_5.xlsx',
  'table6': 'tables/Supplementary_Table_6.xlsx',
  'table7': 'data/Supplementary_table_7-MAGS-Quality-Genome_Lineage-Classification.xlsx',
  'table8': 'tables/Supplementary_Table_8.xlsx',
  'table9': 'data/Supplementary_Table_11_antiSMASH_MAG_BGC_clusters.xlsx',
  'table11': 'data/Supplementary_Table_11_antiSMASH_MAG_BGC_clusters.xlsx',
}


def _table_path(key: str) -> Path:
  value = TABLE_FILES.get(str(key), str(key))
  path = BASE_DIR / value
  return path


def excel_sheet_names(key: str) -> list[str]:
  path = _table_path(key)
  if path.suffix.lower() not in {'.xlsx', '.xls'} or not path.exists():
    return []
  try:
    return pd.ExcelFile(path).sheet_names
  except Exception:
    return []


def load_sheet(key: str, sheet_name: str | int = 0) -> pd.DataFrame:
  path = _table_path(key)
  if not path.exists():
    return pd.DataFrame()
  if path.suffix.lower() in {'.xlsx', '.xls'}:
    try:
      return pd.read_excel(path, sheet_name=sheet_name)
    except Exception:
      try:
        return pd.read_excel(path, sheet_name=0)
      except Exception:
        return pd.DataFrame()
  return read_table(path)


def sheet_inventory() -> pd.DataFrame:
  rows = []
  for key, relative in TABLE_FILES.items():
    path = BASE_DIR / relative
    sheets = excel_sheet_names(key) if path.suffix.lower() in {'.xlsx', '.xls'} else ['file']
    if not sheets:
      sheets = ['unavailable']
    for sheet in sheets:
      rows.append({
        'table_key': key,
        'path': str(path.relative_to(BASE_DIR)) if path.exists() else relative,
        'sheet': sheet,
        'exists': path.exists(),
        'bytes': path.stat().st_size if path.exists() else 0,
      })
  return pd.DataFrame(rows)


def read_text_file(path: Path | str, max_chars: int = 500_000) -> str:
  try:
    return Path(path).read_text(encoding='utf-8', errors='replace')[:max_chars]
  except Exception:
    return ''


def filter_by_text(frame: pd.DataFrame, columns: list[str], query: str) -> pd.DataFrame:
  if frame is None or frame.empty or not str(query).strip():
    return frame.copy() if isinstance(frame, pd.DataFrame) else pd.DataFrame()
  q = str(query).strip().lower()
  use = [c for c in columns if c in frame.columns]
  if not use:
    use = list(frame.columns)
  mask = pd.Series(False, index=frame.index)
  for col in use:
    mask |= frame[col].astype(str).str.lower().str.contains(re.escape(q), na=False)
  return frame.loc[mask].copy()


def infer_metadata_cols(frame: pd.DataFrame) -> list[str]:
  if frame is None or frame.empty:
    return []
  out = []
  for col in frame.columns:
    series = pd.to_numeric(frame[col], errors='coerce')
    if series.notna().sum() < max(1, int(0.5 * len(frame))):
      out.append(str(col))
  return out


def counts_table(key: str, sheet_name: str, metadata_cols: list[str]) -> tuple[pd.DataFrame, list[str]]:
  """Load one count matrix and return the matrix plus verified numeric columns.

  The public app consistently unpacks this function as ``frame, numeric_cols``.
  Numeric detection is performed per column so textual metadata never leaks into
  heatmaps or ordinations. Missing values in numeric columns are preserved as
  zero counts, matching the packaged source matrices.
  """
  frame = load_sheet(key, sheet_name)
  if frame.empty:
    return frame, []
  frame = frame.copy()
  frame.columns = [str(c).strip() for c in frame.columns]
  metadata = {str(c).strip() for c in (metadata_cols or [])}
  numeric_cols: list[str] = []
  for col in frame.columns:
    if col in metadata:
      continue
    values = pd.to_numeric(frame[col], errors='coerce')
    if values.notna().sum() > 0:
      frame[col] = values.fillna(0.0)
      numeric_cols.append(col)
  return frame, numeric_cols


def with_kegg_links(frame: pd.DataFrame, column: str) -> pd.DataFrame:
  if frame is None:
    return pd.DataFrame()
  out = frame.copy()
  if column not in out.columns:
    return out
  def link(value: object) -> str:
    text = str(value)
    match = re.search(r'K\d{5}', text)
    return f'https://www.kegg.jp/entry/{match.group(0)}' if match else ''
  out['KEGG link'] = out[column].map(link)
  return out


def _taxonomy_raw() -> tuple[pd.DataFrame, pd.DataFrame]:
  otu_path = BASE_DIR / 'data' / 'resultado.cds.otu.tab'
  tax_path = BASE_DIR / 'data' / 'resultado.cds.tax.tab'
  try:
    otu = pd.read_csv(otu_path, sep='\t', index_col=0)
  except Exception:
    otu = pd.DataFrame()
  try:
    tax = load_current_taxonomy_table(
      original_path=tax_path,
      current_path=BASE_DIR / 'data' / 'resultado.cds.tax.ncbi_current.tab',
      updates_path=BASE_DIR / 'data' / 'ncbi_taxonomy_name_updates.csv',
    )
  except Exception:
    tax = pd.DataFrame()
  otu.columns = [str(c).strip().strip('.') for c in otu.columns]
  tax.columns = [str(c).strip() for c in tax.columns]
  return otu, tax


def _taxonomy_column(level: str, tax: pd.DataFrame) -> str:
  raw = str(level).split('—')[0].strip()
  candidates = [raw, raw.capitalize(), raw.title()]
  for candidate in candidates:
    if candidate in tax.columns:
      return candidate
  return tax.columns[0] if len(tax.columns) else raw


def taxonomy_table(level: str) -> pd.DataFrame:
  otu, tax = _taxonomy_raw()
  if otu.empty or tax.empty:
    return empty_frame(['taxon'])
  col = _taxonomy_column(level, tax)
  joined = tax[[col]].join(otu, how='inner')
  joined[col] = joined[col].fillna('Unclassified').astype(str).str.strip().replace('', 'Unclassified')
  numeric = joined.drop(columns=[col]).apply(pd.to_numeric, errors='coerce').fillna(0.0)
  grouped = numeric.groupby(joined[col]).sum()
  grouped.index.name = 'taxon'
  return grouped.reset_index()


def _sample_labels(columns: list[str]) -> pd.DataFrame:
  """Map IMG/JGI matrix columns to the sample identifiers used in the article."""
  meta = lake_column_metadata(columns, source_dataset='Taxonomic profiles (Supplementary Table 1)')
  if meta.empty:
    return empty_frame([
      'matrix_column', 'sample.id', 'lake', 'season', 'group', 'lake_season_group',
      'IMG_JGI_analysis_project_id', 'IMG_JGI_taxon_oid', 'ENA_study_accession',
      'lat', 'lon', 'environment_feature', 'sample_type',
    ])
  # ``group`` is the publication sample ID for individual-sample figures.
  meta['group'] = meta['sample.id'].astype(str)
  return meta.reset_index(drop=True)


def taxonomy_samples_metadata() -> pd.DataFrame:
  otu, _ = _taxonomy_raw()
  return _sample_labels(list(otu.columns))


def taxonomy_profile_table(level: str, view_mode: str = 'Individual samples') -> pd.DataFrame:
  table = taxonomy_table(level)
  columns = [
    'group', 'taxon', 'count', 'abundance', 'level', 'source_sheet',
    'environment_feature', 'lake', 'season', 'sample.id', 'matrix_column',
    'sampling_position', 'site', 'IMG_JGI_analysis_project_id',
    'IMG_JGI_taxon_oid', 'ENA_study_accession', 'sample_type',
  ]
  if table.empty:
    return empty_frame(columns)
  value_cols = [c for c in table.columns if c != 'taxon']
  long = table.melt(id_vars='taxon', value_vars=value_cols, var_name='matrix_column', value_name='count')
  long['count'] = pd.to_numeric(long['count'], errors='coerce').fillna(0.0)
  meta = taxonomy_samples_metadata()
  if not meta.empty:
    long = long.merge(meta, on='matrix_column', how='left', validate='many_to_one')
  if 'sample.id' not in long.columns:
    long['sample.id'] = long['matrix_column'].map(publication_sample_id)
  for col, default in [
    ('lake', 'Other'), ('season', 'Unknown'),
    ('environment_feature', 'Amazonian lateritic lake sediment'),
    ('sample_type', 'Sediment'),
  ]:
    if col not in long.columns:
      long[col] = default
    long[col] = long[col].fillna(default).astype(str)
  mode = str(view_mode).lower()
  if 'aggregated' in mode or 'lake-season' in mode or 'lake–season' in mode:
    if 'lake_season_group' not in long.columns:
      long['lake_season_group'] = long['lake'].astype(str) + '-' + long['season'].astype(str).str[:1]
    long['group'] = long['lake_season_group'].astype(str)
    grouped = long.groupby(['group', 'taxon'], as_index=False)['count'].sum()
    lookup_cols = [c for c in ['lake', 'season', 'environment_feature', 'sample_type'] if c in long.columns]
    lookup = long.groupby('group', as_index=False)[lookup_cols].first()
    long = grouped.merge(lookup, on='group', how='left')
    long['sample.id'] = long['group']
    long['matrix_column'] = long['group']
    long['sampling_position'] = 'Aggregated'
    long['site'] = long['group']
    long['IMG_JGI_analysis_project_id'] = 'Multiple records; see individual-sample view'
    long['IMG_JGI_taxon_oid'] = 'Multiple records; see individual-sample view'
    long['ENA_study_accession'] = 'ERP137391'
  else:
    long['group'] = long['sample.id'].astype(str)
  totals = long.groupby('group')['count'].transform('sum').replace(0, np.nan)
  long['abundance'] = long['count'].div(totals).fillna(0.0) * 100.0
  long['level'] = str(level)
  long['source_sheet'] = 'resultado.cds.otu.tab + resultado.cds.tax.tab'
  for col in columns:
    if col not in long.columns:
      long[col] = ''
  return long[columns]


def taxonomy_heatmap(level: str, top_n: int = 30, groups=None, zscore_rows: bool = False,
                     view_mode: str = 'Individual samples'):
  profile = taxonomy_profile_table(level, view_mode=view_mode)
  if profile.empty:
    return heatmap(pd.DataFrame(), title=str(level))
  if groups:
    profile = profile[profile['group'].astype(str).isin({str(x) for x in groups})]
  ranking = profile.groupby('taxon')['abundance'].mean().sort_values(ascending=False)
  keep = ranking.head(max(1, int(top_n))).index
  selected = profile[profile['taxon'].isin(keep)]
  matrix = selected.pivot_table(index='taxon', columns='group', values='abundance', aggfunc='sum', fill_value=0.0)
  if zscore_rows:
    matrix = row_zscore(matrix)
  return heatmap(matrix, title=f'{level} taxonomic profile', x_title='Sample/group', y_title='Taxon')


def taxonomy_stacked_bar(level: str, top_n: int = 20, groups=None,
                         view_mode: str = 'Individual samples', display_factor: float = 1.0):
  profile = taxonomy_profile_table(level, view_mode=view_mode)
  if profile.empty:
    return go.Figure()
  if groups:
    profile = profile[profile['group'].astype(str).isin({str(x) for x in groups})]
  ranking = profile.groupby('taxon')['abundance'].mean().sort_values(ascending=False)
  keep = set(ranking.head(max(1, int(top_n))).index)
  long = profile.copy()
  long['taxon'] = long['taxon'].where(long['taxon'].isin(keep), 'Other taxa')
  long = long.groupby(['group', 'taxon'], as_index=False)['abundance'].sum()
  long['relative_abundance'] = long['abundance'] * float(display_factor)
  taxon_order = [str(value) for value in ranking.index if str(value) in set(long['taxon'].astype(str))]
  if 'Other taxa' in set(long['taxon'].astype(str)):
    taxon_order.append('Other taxa')
  palette = build_taxonomy_palette(taxon_order, load_taxonomy_palette())
  color_map = {taxon: palette[taxon] for taxon in taxon_order}
  fig = px.bar(
    long,
    x='group',
    y='relative_abundance',
    color='taxon',
    title=f'{level} relative abundance',
    color_discrete_map=color_map,
    category_orders={'taxon': taxon_order},
  )
  fig.update_layout(
    barmode='stack',
    xaxis_title='Sample/group',
    yaxis_title='Relative abundance (%)',
    height=650,
    meta={
      'taxonomy_palette_source': 'data/taxonomy_palette.json',
      'matches_article_taxonomy_palette': True,
    },
  )
  return fig


def marker_table() -> pd.DataFrame:
  """Return the KO-marker catalogue with one stable public schema.

  Supplementary Table 8 uses different metadata names for the general and
  iron-focused matrices. The Streamlit interface, however, intentionally
  presents one catalogue. This normalizer maps both source schemas without
  changing the scientific values in the workbook.
  """
  frames: list[pd.DataFrame] = []
  sheets = [
    (ST8_ALL_KO_SHEET, 'Salazar et al.'),
    (ST8_IRON_ALL_SHEET, 'New marker'),
    (ST8_SELECTED_SEDIMENTS_SHEET, 'Salazar et al.'),
    (ST8_IRON_SELECTED_SHEET, 'New marker'),
  ]
  canonical = [
    'KO', 'Study', 'General metabolism', 'KO description',
    'Marker for:', 'KEGG MODULE', 'source_sheet',
  ]
  for sheet, study in sheets:
    frame = load_sheet('table8', sheet)
    if frame.empty:
      continue
    source = frame.copy()
    source.columns = [str(c).strip() for c in source.columns]
    out = pd.DataFrame(index=source.index)
    ko_col = next((c for c in ['KO', 'Function Id', 'Function ID'] if c in source.columns), None)
    metabolism_col = next((c for c in ['Metabolism', 'Biologic Role', 'General metabolism'] if c in source.columns), None)
    description_col = next((c for c in ['KO description', 'Function Name', 'Description'] if c in source.columns), None)
    marker_col = next((c for c in ['Marker for:', 'Marker for', 'Biologic Role', 'Metabolism'] if c in source.columns), None)
    module_col = next((c for c in ['KEGG MODULE', 'KEGG Module', 'Module'] if c in source.columns), None)
    out['KO'] = source[ko_col].astype(str).str.strip() if ko_col else ''
    out['Study'] = study
    out['General metabolism'] = source[metabolism_col].fillna('Unclassified').astype(str).str.strip() if metabolism_col else 'Unclassified'
    out['KO description'] = source[description_col].fillna('').astype(str).str.strip() if description_col else ''
    out['Marker for:'] = source[marker_col].fillna('').astype(str).str.strip() if marker_col else out['General metabolism']
    out['KEGG MODULE'] = source[module_col].fillna('').astype(str).str.strip() if module_col else ''
    out['source_sheet'] = sheet
    out = out[out['KO'].str.contains(r'K\d{5}', regex=True, na=False)]
    frames.append(out[canonical])
  if not frames:
    return empty_frame(canonical)
  catalogue = pd.concat(frames, ignore_index=True, sort=False)
  # Repeated selected/all-matrix entries are the same KO records. Preserve all
  # genuinely distinct source/study annotations while avoiding duplicate UI rows.
  catalogue = catalogue.drop_duplicates(
    subset=['KO', 'Study', 'General metabolism', 'KO description', 'Marker for:', 'KEGG MODULE'],
    keep='first',
  ).reset_index(drop=True)
  return catalogue


def heatmap_figure(frame: pd.DataFrame, numeric_cols: list[str], label_col: str, title: str,
                   top_n: int = 30, zscore_rows: bool = False, x_label_map=None):
  if frame is None or frame.empty:
    return heatmap(pd.DataFrame(), title=title)
  cols = [c for c in numeric_cols if c in frame.columns]
  if not cols:
    cols = numeric_columns(frame, excluded=[label_col])
  work = frame.copy()
  work[label_col] = work[label_col].astype(str) if label_col in work else work.index.astype(str)
  work[cols] = work[cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)
  work['_total'] = work[cols].abs().sum(axis=1)
  work = work.nlargest(max(1, int(top_n)), '_total').drop(columns='_total')
  matrix = work.set_index(label_col)[cols]
  if zscore_rows:
    matrix = row_zscore(matrix)
  if isinstance(x_label_map, dict):
    matrix = matrix.rename(columns=x_label_map)
  fig = heatmap(matrix, title=title, x_title='Sample/group', y_title=label_col)
  # Match the article palettes: Viridis for raw values and RdBu_r for row z-scores.
  if zscore_rows:
    vmax = float(np.nanmax(np.abs(matrix.to_numpy(dtype=float)))) if matrix.size else 0.0
    vmax = max(vmax, 2.5)
    fig.update_traces(colorscale='RdBu_r', zmid=0.0, zmin=-vmax, zmax=vmax)
    fig.update_coloraxes(cmid=0.0, cmin=-vmax, cmax=vmax)
  else:
    fig.update_traces(colorscale='Viridis')
  meta = getattr(fig.layout, 'meta', None)
  if not isinstance(meta, dict):
    meta = {}
  meta.update({
    'data_provenance': 'Supplementary Table 8 / packaged source tables',
    'no_synthetic_values': True,
    'article_palette': 'RdBu_r' if zscore_rows else 'Viridis',
  })
  fig.update_layout(meta=meta)
  return fig


def _classify_external_sample_type(row: pd.Series) -> str:
  """Classify one ST8 record from its documented habitat/ecosystem fields."""
  fields = [
    row.get('Habitat', ''), row.get('Specific Ecosystem', ''),
    row.get('Ecosystem Type', ''), row.get('Ecosystem Subtype', ''),
    row.get('Genome Name / Sample Name', ''), row.get('Study Name', ''),
    row.get('Isolation', ''),
  ]
  text = ' '.join(str(v) for v in fields if pd.notna(v)).lower()
  if any(token in text for token in ['sediment', 'benthic', 'sedimentary']):
    return 'Sediment'
  if any(token in text for token in ['marine', 'sea water', 'seawater', 'ocean', 'hydrothermal vent']):
    return 'Marine water / hydrothermal fluid'
  if any(token in text for token in ['biofilm', 'microbial mat', 'mat community']):
    return 'Biofilm / microbial mat'
  if any(token in text for token in ['water', 'groundwater', 'mine drainage', 'leachate', 'fluid']):
    return 'Freshwater / mine water'
  if any(token in text for token in ['enrich', 'incubat', 'bioreactor', 'laboratory', 'lab ']):
    return 'Laboratory enrichment'
  return 'Other / not explicitly reported'


def iron_rich_environment_metadata() -> pd.DataFrame:
  frame = load_sheet('table8', 'metadata')
  if frame.empty:
    frame = read_table(BASE_DIR / 'data' / 'st8_metadata_curated.csv')
  if frame.empty:
    return empty_frame(['sample_id', 'environmental_group', 'sample_type'])
  out = frame.copy()
  out.columns = [str(c).strip() for c in out.columns]
  sample_candidates = ['taxon_oid', 'IMG Genome ID', 'sample_id', 'Genome Name / Sample Name']
  sample_col = next((c for c in sample_candidates if c in out.columns), out.columns[0])
  out['sample_id'] = out[sample_col].astype(str).str.replace(r'\.0$', '', regex=True)
  if 'environmental_group' not in out.columns:
    group_candidates = ['ST8_group', 'NCBI Family', 'NCBI Class', 'Ecosystem Category', 'environment_feature']
    group_col = next((c for c in group_candidates if c in out.columns), None)
    out['environmental_group'] = out[group_col].astype(str) if group_col else 'External iron-rich environment'
  out['sample_type'] = out.apply(_classify_external_sample_type, axis=1)
  out['is_sediment_sample'] = out['sample_type'].eq('Sediment')
  out['matrix_column'] = out.get('ST8_matrix_column', out.get('matrix_column_all_KO', out['sample_id'])).astype(str)
  out['study_name'] = out.get('Study Name', pd.Series('', index=out.index)).fillna('').astype(str)
  out['IMG_JGI_taxon_oid'] = out.get('taxon_oid', out['sample_id']).astype(str).str.replace(r'\.0$', '', regex=True)
  out['IMG_JGI_analysis_project_id'] = out.get('GOLD Analysis Project ID', pd.Series('', index=out.index)).fillna('').astype(str)
  out['NCBI_BioProject_accession'] = out.get('NCBI Bioproject Accession', pd.Series('', index=out.index)).fillna('').astype(str)
  out['NCBI_BioSample_accession'] = out.get('NCBI Biosample Accession', pd.Series('', index=out.index)).fillna('').astype(str)
  return out


def figure11_environment_metadata() -> pd.DataFrame:
  """Return one harmonised coordinate/date table for article and ST8 records."""
  article = taxonomy_samples_metadata().copy()
  if not article.empty:
    article['dataset_group'] = 'Amazonian lateritic lakes'
    article['sample_id'] = article.get('sample.id', pd.Series('', index=article.index)).astype(str)
    article['collection_date_precision'] = np.where(
      article.get('collection_date', pd.Series('', index=article.index)).astype(str).str.strip().ne(''),
      'reported', 'not reported',
    )
  external = iron_rich_environment_metadata().copy()
  if not external.empty:
    external['dataset_group'] = external.get(
      'ST8_group', pd.Series('Other iron-rich environments', index=external.index)
    ).fillna('Other iron-rich environments').astype(str)
    external['sample.id'] = external.get('ST8_matrix_column', external.get('sample_id', pd.Series('', index=external.index))).astype(str)
    external['sample_id'] = external['sample.id']
    external['collection_date'] = pd.to_datetime(
      external.get('Public Release Date', external.get('Add Date', pd.Series(pd.NaT, index=external.index))),
      errors='coerce',
    )
    external['collection_date_precision'] = np.where(
      external['collection_date'].notna(), 'database release/add date', 'not reported'
    )
    external['lat'] = pd.to_numeric(external.get('Latitude'), errors='coerce')
    external['lon'] = pd.to_numeric(external.get('Longitude'), errors='coerce')
    external['environment_feature'] = external.get(
      'Specific Ecosystem', external.get('Habitat', pd.Series('Iron-rich environment', index=external.index))
    ).fillna('Iron-rich environment').astype(str)
  return pd.concat([article, external], ignore_index=True, sort=False)


def amazonia_vs_iron_marker_summary() -> pd.DataFrame:
  """Summarise exact ST8 KO counts for Amazonian versus external samples.

  The result schema matches the interactive comparison panel. Values are
  calculated directly from the packaged ``ST8 — all KO biomarkers`` matrix;
  no simulated or imputed observations are introduced. A pseudocount of one is
  used only in the descriptive log2 ratio so zero-count groups remain defined.
  """
  frame, numeric_cols = counts_table(
    'table8', ST8_ALL_KO_SHEET, ['KO', 'Metabolism', 'KO description']
  )
  columns = [
    'KO', 'Metabolism', 'Function',
    'Mean count — Amazonian lateritic lakes',
    'Mean count — other iron-rich environments',
    'log2 ratio — Amazonia vs other', 'Highlighted side',
    'Compared external groups', 'Method', 'Source table',
    'Interpretation', 'kegg_url',
  ]
  if frame.empty or not numeric_cols:
    return empty_frame(columns)
  lake_prefixes = ('AM.', 'TI.', 'TIA.', 'VI.')
  lake_cols = [c for c in numeric_cols if str(c).startswith(lake_prefixes)]
  external_cols = [c for c in numeric_cols if c not in lake_cols]
  if not lake_cols or not external_cols:
    return empty_frame(columns)
  out = pd.DataFrame({
    'KO': frame['KO'].astype(str),
    'Metabolism': frame.get('Metabolism', pd.Series('Unclassified', index=frame.index)).fillna('Unclassified').astype(str),
    'Function': frame.get('KO description', pd.Series('', index=frame.index)).fillna('').astype(str),
  })
  lake_values = frame[lake_cols].apply(pd.to_numeric, errors='coerce')
  external_values = frame[external_cols].apply(pd.to_numeric, errors='coerce')
  out['Mean count — Amazonian lateritic lakes'] = lake_values.mean(axis=1, skipna=True)
  out['Mean count — other iron-rich environments'] = external_values.mean(axis=1, skipna=True)
  out['log2 ratio — Amazonia vs other'] = np.log2(
    (out['Mean count — Amazonian lateritic lakes'] + 1.0) /
    (out['Mean count — other iron-rich environments'] + 1.0)
  )
  out['Highlighted side'] = np.where(
    out['log2 ratio — Amazonia vs other'] >= 0,
    'Amazonian lateritic lakes',
    'Other iron-rich environments',
  )
  meta = iron_rich_environment_metadata()
  if not meta.empty and 'environmental_group' in meta.columns:
    groups = sorted({str(x) for x in meta['environmental_group'].dropna() if str(x).strip()})
    compared = '; '.join(groups)
  else:
    compared = f'{len(external_cols)} packaged external ST8 records'
  out['Compared external groups'] = compared
  out['Method'] = 'Descriptive log2 ratio of group means with pseudocount 1'
  out['Source table'] = 'Supplementary Table 8 — ST8 — all KO biomarkers'
  out['Interpretation'] = np.where(
    out['log2 ratio — Amazonia vs other'] >= 0,
    'Positive value: higher mean count in Amazonian lateritic lakes',
    'Negative value: higher mean count in the external iron-rich panel',
  )
  out['kegg_url'] = out['KO'].str.extract(r'(K\d{5})', expand=False).fillna('').map(
    lambda ko: f'https://www.kegg.jp/entry/{ko}' if ko else ''
  )
  out['_abs_ratio'] = out['log2 ratio — Amazonia vs other'].abs()
  return out.sort_values('_abs_ratio', ascending=False).drop(columns='_abs_ratio').reset_index(drop=True)[columns]


def res_ko_fe_reduzido_table() -> tuple[pd.DataFrame, list[str]]:
  return counts_table(
    'table8', ST8_IRON_ALL_SHEET,
    ['Function Id', 'Biologic Role', 'Function Name'],
  )


def res_ko_fe_selected_table() -> tuple[pd.DataFrame, list[str]]:
  return counts_table(
    'table8', ST8_IRON_SELECTED_SHEET,
    ['Function Id', 'Biologic Role', 'Function Name'],
  )


def iron_fe_marker_summary() -> pd.DataFrame:
  """Build descriptive rankings from the packaged iron-KO count matrix."""
  frame, numeric_cols = res_ko_fe_reduzido_table()
  columns = [
    'Function Id', 'Biologic Role', 'Function Name',
    'Detection fraction — all environments',
    'Total count — all iron-rich environments', 'Broad iron-rich score',
    'Mean count — Amazonian lateritic lakes',
    'Mean count — other iron-rich environments',
    'log2 ratio — Amazonia vs other',
    'Detection fraction — Amazonian lakes', 'Amazonian-lake score',
    'kegg_url',
  ]
  if frame.empty or not numeric_cols:
    return empty_frame(columns)
  lake_prefixes = ('AM.', 'TI.', 'TIA.', 'VI.')
  lake_cols = [c for c in numeric_cols if str(c).startswith(lake_prefixes)]
  external_cols = [c for c in numeric_cols if c not in lake_cols]
  if not lake_cols or not external_cols:
    return empty_frame(columns)
  all_values = frame[numeric_cols].apply(pd.to_numeric, errors='coerce')
  lake_values = frame[lake_cols].apply(pd.to_numeric, errors='coerce')
  external_values = frame[external_cols].apply(pd.to_numeric, errors='coerce')
  out = frame[['Function Id', 'Biologic Role', 'Function Name']].copy()
  out['Detection fraction — all environments'] = all_values.gt(0).mean(axis=1)
  out['Total count — all iron-rich environments'] = all_values.sum(axis=1, skipna=True)
  out['Broad iron-rich score'] = (
    np.log10(out['Total count — all iron-rich environments'] + 1.0) *
    out['Detection fraction — all environments']
  )
  out['Mean count — Amazonian lateritic lakes'] = lake_values.mean(axis=1, skipna=True)
  out['Mean count — other iron-rich environments'] = external_values.mean(axis=1, skipna=True)
  out['log2 ratio — Amazonia vs other'] = np.log2(
    (out['Mean count — Amazonian lateritic lakes'] + 1.0) /
    (out['Mean count — other iron-rich environments'] + 1.0)
  )
  out['Detection fraction — Amazonian lakes'] = lake_values.gt(0).mean(axis=1)
  positive_ratio = out['log2 ratio — Amazonia vs other'].clip(lower=0.0)
  out['Amazonian-lake score'] = (
    positive_ratio *
    np.log10(out['Mean count — Amazonian lateritic lakes'] + 1.0) *
    out['Detection fraction — Amazonian lakes']
  )
  out['kegg_url'] = out['Function Id'].astype(str).str.extract(r'(K\d{5})', expand=False).fillna('').map(
    lambda ko: f'https://www.kegg.jp/entry/{ko}' if ko else ''
  )
  return out[columns].sort_values(
    ['Broad iron-rich score', 'Amazonian-lake score'], ascending=False
  ).reset_index(drop=True)


def iron_fe_zscore_table(selected: bool = False) -> pd.DataFrame:
  sheet = ST8_IRON_SELECTED_SHEET if selected else ST8_IRON_ALL_SHEET
  frame, numeric_cols = counts_table(
    'table8', sheet, ['Function Id', 'Biologic Role', 'Function Name']
  )
  if frame.empty or not numeric_cols:
    return frame
  meta = [c for c in ['Function Id', 'Biologic Role', 'Function Name'] if c in frame.columns]
  z = row_zscore(frame[numeric_cols])
  return pd.concat([frame[meta].reset_index(drop=True), z.reset_index(drop=True)], axis=1)


def available_fasta_count() -> int:
  patterns = ['data/**/*.fa', 'data/**/*.fasta', 'data/**/*.fna']
  return sum(1 for pattern in patterns for _ in BASE_DIR.glob(pattern))


def available_gbk_count() -> int:
  patterns = ['data/**/*.gbk', 'data/**/*.gbff', 'Annotation/**/*.gbk', 'Annotation/**/*.gbff']
  return sum(1 for pattern in patterns for _ in BASE_DIR.glob(pattern))


def get_fasta_path(mag_id: object) -> Path | None:
  token = re.sub(r'\D+', '', str(mag_id))
  patterns = [f'data/**/*{token}*.fasta', f'data/**/*{token}*.fna', f'data/**/*{token}*.fa']
  for pattern in patterns:
    matches = sorted(BASE_DIR.glob(pattern))
    if matches:
      return matches[0]
  return None


def get_gbk_path(mag_id: object) -> Path | None:
  token = re.sub(r'\D+', '', str(mag_id))
  patterns = [f'data/**/*{token}*.gbk', f'data/**/*{token}*.gbff', f'Annotation/**/*{token}*.gbk']
  for pattern in patterns:
    matches = sorted(BASE_DIR.glob(pattern))
    if matches:
      return matches[0]
  return None
