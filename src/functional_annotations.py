from __future__ import annotations

"""IMG/JGI functional-annotation matrices used by the Streamlit application.

The module keeps the two uploaded studies separate at source and merges them
only when the combined view is requested. Every sample column is linked to
curated metadata so study filters never silently discard records.
"""

import re
from pathlib import Path
import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ._helpers import BASE_DIR, row_zscore as _row_zscore
from .sample_metadata import lake_column_metadata
from .supplementary_database import iron_rich_environment_metadata, load_sheet

ANNOTATION_SHEETS = {
  'KO': {'table6': 'KO', 'table8': 'ko'},
  'EC number': {'table6': 'EC-numbers', 'table8': 'EC-number'},
  'PFAM': {'table6': 'PFAM', 'table8': 'pfam'},
}
EXPECTED_FEATURE_COUNTS = {
  ('table6', 'KO'): 8045,
  ('table6', 'EC number'): 2914,
  ('table6', 'PFAM'): 8238,
  ('table8', 'KO'): 12144,
  ('table8', 'EC number'): 3514,
  ('table8', 'PFAM'): 100,
}
EXPECTED_TABLE8_FEATURE_COUNTS = {
  key[1]: value for key, value in EXPECTED_FEATURE_COUNTS.items() if key[0] == 'table8'
}

SOURCE_LABELS = {
  'table6': 'Amazonian lake annotations (Supplementary Table 6)',
  'table8': 'External iron-rich environments (Supplementary Table 8)',
  'combined': 'Combined annotation matrix',
}


def row_zscore(frame: pd.DataFrame) -> pd.DataFrame:
  return _row_zscore(frame)


def _sheet_name(source: str, annotation_type: str) -> str:
  return ANNOTATION_SHEETS.get(annotation_type, {}).get(source, annotation_type)


def _load_source(source: str, annotation_type: str) -> pd.DataFrame:
  key = 'table6' if source == 'table6' else 'table8'
  frame = load_sheet(key, _sheet_name(source, annotation_type))
  if frame.empty:
    return frame
  out = frame.copy()
  out.columns = [str(c).strip() for c in out.columns]
  return out


def _id_name_columns(frame: pd.DataFrame, annotation_type: str) -> tuple[str, str]:
  if frame.empty:
    return 'annotation_id', 'annotation_name'
  id_candidates = {
    'KO': ['Function Id', 'Function ID', 'KO', 'ko', 'function_id'],
    'EC number': ['Function Id', 'Function ID', 'EC', 'EC number', 'ec_number'],
    'PFAM': ['Function Id', 'Function ID', 'PFAM', 'pfam'],
  }.get(annotation_type, [])
  name_candidates = ['Function Name', 'Description', 'Name', 'KO description', 'Biologic Role', 'Lineage']
  id_col = next((c for c in id_candidates if c in frame.columns), frame.columns[0])
  name_col = next((c for c in name_candidates if c in frame.columns and c != id_col), id_col)
  return str(id_col), str(name_col)


def _sample_columns(frame: pd.DataFrame, id_col: str, name_col: str) -> list[str]:
  metadata_cols = {
    id_col, name_col, 'Metabolism', 'KEGG MODULE', 'Biologic Role',
    'Lineage', 'phylo_level_val', 'General metabolism', 'KO description',
  }
  cols: list[str] = []
  for col in frame.columns:
    if col in metadata_cols:
      continue
    numeric = pd.to_numeric(frame[col], errors='coerce')
    if numeric.notna().sum() > 0:
      cols.append(str(col))
  return cols


def _table6_column_metadata(sample_cols: list[str]) -> pd.DataFrame:
  meta = lake_column_metadata(
    sample_cols,
    source_dataset=SOURCE_LABELS['table6'],
  )
  if meta.empty:
    return meta
  meta['source_dataset_key'] = 'table6'
  meta['source_dataset'] = SOURCE_LABELS['table6']
  meta['environmental_group'] = 'Amazonian lateritic lakes'
  meta['ST8_group'] = 'Amazonian lateritic lakes'
  meta['data_layer'] = 'Metagenomics'
  meta['study_name'] = 'Freshwater microbial communities from South-Eastern Amazon Lakes, Para, Brazil'
  meta['sample_id'] = meta['sample.id'].astype(str)
  meta['display_label'] = meta['sample.id'].astype(str)
  meta['publication_order'] = np.arange(len(meta), dtype=int)
  meta['hover_label'] = (
    meta['sample.id'].astype(str)
    + '<br>IMG/JGI project: ' + meta['IMG_JGI_analysis_project_id'].astype(str)
    + '<br>IMG taxon OID: ' + meta['IMG_JGI_taxon_oid'].astype(str)
    + '<br>Site: ' + meta['site'].astype(str)
    + '<br>Season: ' + meta['season'].astype(str)
    + '<br>Sample type: ' + meta['sample_type'].astype(str)
  )
  return meta


def _external_column_metadata(sample_cols: list[str]) -> pd.DataFrame:
  external = iron_rich_environment_metadata().copy()
  if external.empty:
    return pd.DataFrame()
  oid_lookup: dict[str, pd.Series] = {}
  for _, row in external.iterrows():
    oid = re.sub(r'\.0$', '', str(row.get('taxon_oid', row.get('sample_id', ''))).strip())
    if oid:
      oid_lookup[oid] = row
  rows: list[dict[str, object]] = []
  for col in sample_cols:
    text = str(col)
    match = re.search(r'(?<!\d)(3\d{9})(?!\d)', text)
    oid = match.group(1) if match else ''
    row = oid_lookup.get(oid)
    if row is None:
      rows.append({
        'matrix_column': text,
        'sample_id': text,
        'display_label': text,
        'taxon_oid': oid,
        'ST8_group': 'External iron-rich environment',
        'environmental_group': 'External iron-rich environment',
        'data_layer': 'Functional annotation',
        'study_name': 'Metadata match not found',
        'sample_type': 'Other / not explicitly reported',
        'source_dataset_key': 'table8',
        'source_dataset': SOURCE_LABELS['table8'],
        'hover_label': text,
      })
      continue
    record = row.to_dict()
    short_group = str(row.get('ST8_short_group', '') or '').strip()
    layer = str(row.get('data_layer_abbrev', row.get('data_layer', '')) or '').strip()
    sid = str(row.get('sample_id_created_this_study', '') or '').strip()
    concise = ' | '.join(v for v in [sid, short_group, layer] if v)
    if not concise:
      concise = str(row.get('ST8_matrix_column', text) or text)
    record.update({
      'matrix_column': text,
      'display_label': concise,
      'taxon_oid': oid,
      'source_dataset_key': 'table8',
      'source_dataset': SOURCE_LABELS['table8'],
      'study_name': str(row.get('Study Name', '') or ''),
      'environmental_group': str(row.get('environmental_group', row.get('ST8_group', 'External iron-rich environment')) or 'External iron-rich environment'),
      'hover_label': '<br>'.join([
        f"{concise}",
        f"Matrix column: {text}",
        f"Study: {row.get('Study Name', '')}",
        f"Environmental group: {row.get('ST8_group', '')}",
        f"Data layer: {row.get('data_layer', '')}",
        f"Sample type: {row.get('sample_type', '')}",
        f"IMG taxon OID: {oid}",
        f"GOLD analysis project: {row.get('GOLD Analysis Project ID', '')}",
        f"NCBI BioProject: {row.get('NCBI Bioproject Accession', '')}",
        f"NCBI BioSample: {row.get('NCBI Biosample Accession', '')}",
      ]),
    })
    rows.append(record)
  return pd.DataFrame(rows)


def _column_metadata(matrix: pd.DataFrame, id_col: str, name_col: str, source: str) -> pd.DataFrame:
  sample_cols = _sample_columns(matrix, id_col, name_col)
  return _table6_column_metadata(sample_cols) if source == 'table6' else _external_column_metadata(sample_cols)


def _canonicalize_source(frame: pd.DataFrame, source: str, annotation_type: str) -> tuple[pd.DataFrame, pd.DataFrame]:
  id_col, name_col = _id_name_columns(frame, annotation_type)
  work = frame.copy()
  rename = {id_col: 'annotation_id', name_col: 'annotation_name'}
  work = work.rename(columns=rename)
  work['annotation_id'] = work['annotation_id'].astype(str).str.strip()
  work['annotation_name'] = work['annotation_name'].fillna('').astype(str).str.strip()
  sample_cols = _sample_columns(work, 'annotation_id', 'annotation_name')
  for col in sample_cols:
    work[col] = pd.to_numeric(work[col], errors='coerce').fillna(0.0)
  keep_meta = [c for c in ['annotation_id', 'annotation_name', 'Metabolism', 'Biologic Role', 'KEGG MODULE'] if c in work.columns]
  work = work[keep_meta + sample_cols]
  metadata = _table6_column_metadata(sample_cols) if source == 'table6' else _external_column_metadata(sample_cols)
  return work, metadata


def build_annotation_dataset(source: str, annotation_type: str):
  """Return complete source rows and align studies without silent truncation.

  Rows are aligned by annotation identifier plus within-source occurrence.  The
  occurrence key preserves genuine duplicate identifiers (Table 6 has two
  distinct K13625 descriptions) while matching the first occurrence of an ID
  across Table 6 and Table 8 in the combined view.
  """
  source = str(source)
  requested = ['table6', 'table8'] if source == 'combined' else [source]
  matrices: list[pd.DataFrame] = []
  metadata: list[pd.DataFrame] = []
  for source_name in requested:
    frame = _load_source(source_name, annotation_type)
    if frame.empty:
      continue
    canonical, meta = _canonicalize_source(frame, source_name, annotation_type)
    canonical = canonical.copy()
    canonical['_source_occurrence'] = canonical.groupby('annotation_id', sort=False).cumcount()
    matrices.append(canonical)
    metadata.append(meta)
  if not matrices:
    return pd.DataFrame(), pd.DataFrame(), 'annotation_id', 'annotation_name'
  merged = matrices[0].copy()
  for other in matrices[1:]:
    right_samples = [c for c in other.columns if c not in {'annotation_id', 'annotation_name', '_source_occurrence', 'Metabolism', 'Biologic Role', 'KEGG MODULE'}]
    right = other[['annotation_id', '_source_occurrence', 'annotation_name'] + right_samples].copy()
    merged = merged.merge(
      right,
      on=['annotation_id', '_source_occurrence'],
      how='outer',
      suffixes=('', '_right'),
      validate='one_to_one',
    )
    if 'annotation_name_right' in merged.columns:
      merged['annotation_name'] = merged['annotation_name'].replace('', np.nan).fillna(merged['annotation_name_right']).fillna('')
      merged = merged.drop(columns=['annotation_name_right'])
  merged = merged.drop(columns=['_source_occurrence'], errors='ignore')
  sample_cols = [c for c in merged.columns if c not in {'annotation_id', 'annotation_name', 'Metabolism', 'Biologic Role', 'KEGG MODULE'}]
  for col in sample_cols:
    merged[col] = pd.to_numeric(merged[col], errors='coerce').fillna(0.0)
  merged = merged.reset_index(drop=True)
  meta_out = pd.concat(metadata, ignore_index=True, sort=False) if metadata else pd.DataFrame()
  if not meta_out.empty and 'matrix_column' in meta_out.columns:
    meta_out = meta_out.drop_duplicates('matrix_column', keep='first').reset_index(drop=True)
  return merged, meta_out, 'annotation_id', 'annotation_name'

def annotation_row_details(frame: pd.DataFrame, id_col: str, name_col: str, annotation_type: str) -> pd.DataFrame:
  if frame is None or frame.empty:
    return pd.DataFrame()
  out = pd.DataFrame(index=frame.index)
  ids = frame[id_col].astype(str) if id_col in frame else frame.index.astype(str)
  names = frame[name_col].astype(str) if name_col in frame else ids
  pathway_col = next((c for c in ['Metabolism', 'Biologic Role', 'KEGG pathway', 'Pathway'] if c in frame.columns), None)
  module_col = next((c for c in ['KEGG MODULE', 'KEGG module', 'Module'] if c in frame.columns), None)
  pathway = frame[pathway_col].astype(str) if pathway_col else pd.Series('', index=frame.index)
  module = frame[module_col].astype(str) if module_col else pd.Series('', index=frame.index)
  out['Heatmap label'] = ids + ' — ' + names
  out['Full annotation label'] = out['Heatmap label']
  out['Gene symbol'] = ids.str.extract(r':\s*([^;\s]+)', expand=False).fillna('')
  out['KEGG pathway / metabolic role'] = pathway
  out['KEGG module'] = module
  out['Annotation information'] = names
  out['Annotation detail type'] = annotation_type
  out['Local annotation source'] = 'Supplementary Tables 6 and 8 / packaged data'
  out['Reference URL'] = ids.map(lambda x: f'https://www.kegg.jp/entry/{m.group(0)}' if (m := re.search(r'K\d{5}', x)) else '')
  return out


def _ordered_selected_columns(column_meta: pd.DataFrame, selected_cols: list[str]) -> tuple[list[str], list[str], list[str]]:
  if column_meta is None or column_meta.empty:
    cols = list(dict.fromkeys(selected_cols))
    return cols, cols, cols
  work = column_meta[column_meta['matrix_column'].astype(str).isin({str(c) for c in selected_cols})].copy()
  if work.empty:
    cols = list(dict.fromkeys(selected_cols))
    return cols, cols, cols
  for col in ['source_dataset_key', 'environmental_group', 'study_name', 'sample_id', 'matrix_column']:
    if col not in work.columns:
      work[col] = ''
  if 'publication_order' not in work.columns:
    work['publication_order'] = np.arange(len(work), dtype=int)
  work['publication_order'] = pd.to_numeric(work['publication_order'], errors='coerce').fillna(10**9)
  work['_source_order'] = work['source_dataset_key'].map({'table6': 0, 'table8': 1}).fillna(2)
  work = work.sort_values(['_source_order', 'publication_order', 'environmental_group', 'study_name', 'sample_id', 'matrix_column'], kind='stable')
  work = work.drop_duplicates('matrix_column', keep='first')
  cols = work['matrix_column'].astype(str).tolist()
  display = work.get('display_label', work['matrix_column']).fillna(work['matrix_column']).astype(str).tolist()
  hover = work.get('hover_label', work['matrix_column']).fillna(work['matrix_column']).astype(str).tolist()
  return cols, display, hover


def functional_annotation_heatmap(matrix_df: pd.DataFrame, column_meta: pd.DataFrame,
                                  id_col: str, name_col: str, selected_cols: list[str],
                                  annotation_type: str, source_label: str,
                                  top_n: int = 200, ranking_metric: str = 'Total count',
                                  zscore_rows: bool = False,
                                  order_by_annotation_group: bool = True,
                                  include_group_in_label: bool = True,
                                  page_start: int = 0, page_size: int | None = None,
                                  force_all_y_labels: bool = True):
  if matrix_df is None or matrix_df.empty:
    return None, pd.DataFrame(), pd.DataFrame()
  cols, x_labels, x_hover = _ordered_selected_columns(column_meta, selected_cols)
  cols = [c for c in cols if c in matrix_df.columns]
  if not cols:
    return None, pd.DataFrame(), pd.DataFrame()
  x_labels = x_labels[:len(cols)]
  x_hover = x_hover[:len(cols)]
  work = matrix_df.copy()
  work[cols] = work[cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)
  details = annotation_row_details(work, id_col, name_col, annotation_type)
  work['_heatmap_label'] = details['Heatmap label'].values
  metric = str(ranking_metric).lower()
  if 'mean' in metric:
    work['_rank'] = work[cols].mean(axis=1)
  elif 'detection' in metric:
    work['_rank'] = (work[cols] > 0).mean(axis=1)
  elif 'variance' in metric:
    work['_rank'] = work[cols].var(axis=1)
  elif 'source table order' in metric:
    work['_rank'] = -np.arange(len(work))
  else:
    work['_rank'] = work[cols].sum(axis=1)
  n_keep = min(max(1, int(top_n)), len(work))
  selected = work.head(n_keep) if 'source table order' in metric else work.nlargest(n_keep, '_rank')
  raw = selected.drop(columns=['_rank']).copy()
  raw_values = raw[cols].copy()
  z_values = _row_zscore(raw_values)
  z_out = raw.copy()
  z_out[cols] = z_values
  start = max(0, int(page_start))
  end = len(raw) if page_size is None else min(len(raw), start + int(page_size))
  display = (z_values if zscore_rows else raw_values).iloc[start:end].copy()
  y_labels = raw['_heatmap_label'].iloc[start:end].astype(str).tolist()
  display.index = y_labels
  custom = np.empty((len(display), len(cols)), dtype=object)
  for i, y in enumerate(y_labels):
    for j, x_info in enumerate(x_hover):
      custom[i, j] = f"{y}<br>{x_info}"
  n_rows, n_cols = display.shape
  is_amazonian_table6 = str(source_label).startswith('Amazonian lake annotations')
  # Table 6 contains the 20 study samples; keep every sample label visible.
  cell_w = 58 if is_amazonian_table6 else 42 if n_cols <= 30 else 34 if n_cols <= 90 else 28
  cell_h = 28 if n_rows <= 80 else 24
  width = max(1350, min(16000, 650 + cell_w * n_cols))
  height = max(720, min(26000, 300 + cell_h * n_rows))
  fig = go.Figure(go.Heatmap(
    z=display.to_numpy(float),
    x=x_labels,
    y=y_labels,
    customdata=custom,
    colorscale='RdBu_r' if zscore_rows else 'Viridis',
    zmid=0 if zscore_rows else None,
    colorbar=dict(title='Row z-score' if zscore_rows else 'Count', thickness=20, len=0.82),
    hovertemplate='%{customdata}<br>Value: %{z:.4g}<extra></extra>',
    xgap=0.35,
    ygap=0.35,
  ))
  fig.update_layout(
    title=f'{source_label} — {annotation_type}',
    width=width,
    height=height,
    margin=dict(l=520, r=180, t=100, b=360),
    font=dict(family='Arial, Helvetica, sans-serif', size=13, color='#111827'),
    meta={
      'preserve_cell_geometry': True,
      'force_all_y_ticks': bool(force_all_y_labels),
      'all_y_labels_visible': bool(force_all_y_labels),
      'force_all_x_ticks': True,
      'all_x_labels_visible': True,
      'cell_width_px': cell_w,
      'cell_height_px': cell_h,
      'source_sample_count': n_cols,
      'source_table': 'Supplementary Table 6' if is_amazonian_table6 else 'Supplementary Table 8 / combined source',
      'no_synthetic_values': True,
      'scientific_script': 'src/functional_annotations.py',
    },
  )
  fig.update_xaxes(
    tickangle=-45 if is_amazonian_table6 else -60,
    tickfont=dict(size=12 if is_amazonian_table6 else 11),
    automargin=True,
    tickmode='array', tickvals=x_labels, ticktext=x_labels,
    title='Amazonian lake samples' if is_amazonian_table6 else 'Study sample / external record',
  )
  fig.update_yaxes(tickfont=dict(size=11), automargin=True, tickmode='array', tickvals=y_labels, ticktext=y_labels, title=annotation_type)
  return fig, raw, z_out


def add_annotation_links(frame: pd.DataFrame, id_col: str, annotation_type: str) -> pd.DataFrame:
  if frame is None:
    return pd.DataFrame()
  out = frame.copy()
  if id_col not in out.columns:
    return out
  def link(value: object) -> str:
    text = str(value)
    if annotation_type == 'KO' and (m := re.search(r'K\d{5}', text)):
      return f'https://www.kegg.jp/entry/{m.group(0)}'
    if annotation_type == 'EC number':
      return f'https://enzyme.expasy.org/EC/{text.replace("EC:", "")}'
    if annotation_type == 'PFAM':
      return f'https://www.ebi.ac.uk/interpro/entry/pfam/{text}'
    return ''
  out['Reference hyperlink'] = out[id_col].map(link)
  return out
