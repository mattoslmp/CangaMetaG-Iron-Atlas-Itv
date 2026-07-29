from __future__ import annotations

from io import BytesIO
from pathlib import Path
import re
import zipfile

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from ._helpers import BASE_DIR, canonical_mag, heatmap, read_table, row_zscore, zip_directory

KEMET_OUTPUT_DIR = BASE_DIR / 'outputs' / 'kegg_modules'
MAG_COMPLETENESS_TABLE = BASE_DIR / 'data' / 'final_kegg_st8_update' / 'MAG_KEGG_module_completeness_STATUS_species_MAGnumber_3state.csv'
DATASET_DIRS = {
  'MAGs': BASE_DIR / 'data' / 'kegg_modules' / 'mags',
  'Metagenomes': BASE_DIR / 'data' / 'kegg_modules' / 'metagenomes',
  'External iron-rich': BASE_DIR / 'data' / 'final_kegg_st8_update',
}
METAGENOME_SAMPLE_MAP = {}


def canonical_mag_id(value: object) -> str:
  return canonical_mag(value)


def mag_display_label(value: object) -> str:
  return canonical_mag_id(value)


def metagenome_display_label(value: object) -> str:
  text = str(value).strip().strip('.')
  return METAGENOME_SAMPLE_MAP.get(text.split('_')[0], text)


def ensure_kegg_module_directories() -> dict[str, str]:
  KEMET_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
  for path in DATASET_DIRS.values():
    path.mkdir(parents=True, exist_ok=True)
  return {key: str(path) for key, path in DATASET_DIRS.items()}


def _matrix_candidates(dataset_type: str) -> tuple[Path, Path]:
  lower = str(dataset_type).lower()
  if 'mag' in lower:
    status = BASE_DIR / 'data' / 'final_kegg_st8_update' / 'MAG_KEGG_module_completeness_STATUS_species_MAGnumber_3state.csv'
    score = BASE_DIR / 'data' / 'final_kegg_st8_update' / 'MAG_KEGG_module_completeness_SCORE_species_MAGnumber_3state.csv'
  elif 'external' in lower or 'iron' in lower:
    status = BASE_DIR / 'data' / 'final_kegg_st8_update' / 'ST8_external_iron_rich_module_completeness_STATUS_3state_from_KO.csv'
    score = BASE_DIR / 'data' / 'final_kegg_st8_update' / 'ST8_external_iron_rich_module_completeness_SCORE_3state_from_KO.csv'
  elif 'combined' in lower or 'lagoon plus' in lower:
    status = BASE_DIR / 'data' / 'final_kegg_st8_update' / 'Combined_lagoon_plus_external_iron_rich_module_completeness_STATUS_3state.csv'
    score = BASE_DIR / 'data' / 'final_kegg_st8_update' / 'Combined_lagoon_plus_external_iron_rich_module_completeness_SCORE_3state.csv'
  else:
    status = BASE_DIR / 'data' / 'final_kegg_st8_update' / 'KEMET_lagoon_all_metagenomes_module_completeness_STATUS_3state.csv'
    score = BASE_DIR / 'data' / 'final_kegg_st8_update' / 'KEMET_lagoon_all_metagenomes_module_completeness_SCORE_3state.csv'
  return status, score


def load_module_matrices(dataset_type: str = 'Metagenomes'):
  status_path, score_path = _matrix_candidates(dataset_type)
  status = read_table(status_path)
  score = read_table(score_path)
  if not status.empty:
    status = status.set_index(status.columns[0])
  if not score.empty:
    score = score.set_index(score.columns[0])
  return status, score


def completion_heatmap(matrix: pd.DataFrame, title: str = 'KEGG module completeness', zscore_rows: bool = False):
  if matrix is None or matrix.empty:
    return heatmap(pd.DataFrame(), title=title)
  numeric = matrix.apply(pd.to_numeric, errors='coerce')
  if numeric.notna().sum().sum() == 0:
    mapping = {'Complete': 2, '1 block missing': 1, 'Incomplete': 0, 'Absent': 0}
    numeric = matrix.replace(mapping).apply(pd.to_numeric, errors='coerce').fillna(0)
  else:
    numeric = numeric.fillna(0)
  if zscore_rows:
    numeric = row_zscore(numeric)
  return heatmap(numeric, title=title, x_title='Sample/MAG', y_title='KEGG module')


def kegg_sample_metadata(dataset_type: str, columns) -> pd.DataFrame:
  """Return the complete metadata contract required by KEGG heatmaps.

  The function retains the historical ``matrix_column``/``display_label``
  fields and also provides the canonical identifiers and hover fields consumed
  by ``app.kegg_numeric_heatmap_figure``.
  """
  is_mag = 'mag' in str(dataset_type).lower()
  taxonomy_lookup = {}
  if is_mag:
    table_path = BASE_DIR / 'tables' / 'MAG_taxonomic_label_key_for_Supplementary_Figure_37.csv'
    if table_path.exists():
      table = pd.read_csv(table_path)
      if 'Original matrix column' in table.columns:
        taxonomy_lookup = table.set_index('Original matrix column').to_dict('index')
  rows = []
  for col in columns:
    source = str(col)
    if is_mag:
      record = taxonomy_lookup.get(source, {})
      mag_id = str(record.get('MAG identifier') or canonical_mag_id(source))
      tax_label = str(record.get('Taxonomic label used in figure') or source.rsplit(' - ', 1)[0]).strip()
      full_taxonomy = str(record.get('Full source taxonomic classification') or tax_label).strip()
      canonical = canonical_mag_id(mag_id)
      axis_label = f"{tax_label}<br>{mag_id}"
      rows.append({
        'matrix_column': source,
        'display_label': axis_label,
        'dataset_type': dataset_type,
        'canonical_id': canonical,
        'axis_label': axis_label,
        'Genus': tax_label,
        'Species': full_taxonomy,
        'GTDB_lineage': full_taxonomy,
        'lake_sample': '',
        'IMG_JGI_ID': '',
      })
    else:
      sample = metagenome_display_label(source)
      rows.append({
        'matrix_column': source,
        'display_label': sample,
        'dataset_type': dataset_type,
        'canonical_id': source,
        'axis_label': sample,
        'Genus': '',
        'Species': '',
        'GTDB_lineage': '',
        'lake_sample': sample,
        'IMG_JGI_ID': source,
      })
  return pd.DataFrame(rows)


def mag_taxonomy_metadata() -> pd.DataFrame:
  path = BASE_DIR / 'tables' / 'MAG_taxonomic_label_key_for_Supplementary_Figure_37.csv'
  return read_table(path)


def metagenome_sample_coverage() -> pd.DataFrame:
  path = KEMET_OUTPUT_DIR / 'metagenomes_KEMET_sample_coverage.csv'
  return read_table(path)


def report_files(dataset_type: str = 'MAGs') -> list[Path]:
  root = DATASET_DIRS.get(dataset_type, DATASET_DIRS.get('MAGs'))
  return sorted([p for p in root.rglob('*') if p.is_file() and ('report' in p.name.lower() or p.suffix.lower() in {'.tsv', '.csv'})]) if root.exists() else []


def fasta_inventory(dataset_type: str = 'MAGs') -> pd.DataFrame:
  root = DATASET_DIRS.get(dataset_type, DATASET_DIRS.get('MAGs'))
  rows = []
  if root.exists():
    for path in sorted(root.rglob('*')):
      if path.is_file() and path.suffix.lower() in {'.fa', '.fasta', '.fna'}:
        rows.append({'file': path.name, 'path': str(path), 'bytes': path.stat().st_size})
  return pd.DataFrame(rows)


def input_name_inventory(dataset_type: str = 'MAGs') -> pd.DataFrame:
  reports = report_files(dataset_type)
  return pd.DataFrame([{'input_name': p.stem, 'path': str(p)} for p in reports])


def module_component_figure(frame: pd.DataFrame, *args, **kwargs):
  if frame is None or frame.empty:
    return go.Figure()
  work = frame.copy()
  label_col = next((c for c in ['KO', 'component', 'Detected_KOs', 'Missing_or_alternative_KOs'] if c in work.columns), work.columns[0])
  work['status'] = work.get('status', 'Detected')
  values = work.groupby([label_col, 'status']).size().rename('count').reset_index()
  import plotly.express as px
  return px.bar(values, x=label_col, y='count', color='status', title='KEGG module KO components')


def build_kegg_outputs(*args, **kwargs) -> dict:
  ensure_kegg_module_directories()
  return {'status': 'ready', 'output_dir': str(KEMET_OUTPUT_DIR)}


def zip_directory_bytes(path: Path | str) -> bytes:
  return zip_directory(Path(path))
