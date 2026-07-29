from __future__ import annotations

from pathlib import Path
import re
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from ._helpers import BASE_DIR, canonical_mag

ANNOTATION_DIR = BASE_DIR / 'Annotation'


def canonical_mag_id(value: object) -> str:
  return canonical_mag(value)


def mag_number(value: object) -> int | None:
  match = re.search(r'\d+', str(value))
  return int(match.group(0)) if match else None


def list_annotation_folders() -> list[Path]:
  roots = [ANNOTATION_DIR, BASE_DIR / 'data' / 'annotations', BASE_DIR / 'data' / 'mags']
  out = []
  for root in roots:
    if root.exists():
      out.extend([p for p in root.iterdir() if p.is_dir()])
  return sorted(set(out), key=lambda p: p.name)


def annotation_folder(mag_id: object) -> Path:
  cid = canonical_mag_id(mag_id)
  number = mag_number(cid)
  candidates = [ANNOTATION_DIR / cid, ANNOTATION_DIR / f'MAG{number}' if number is not None else ANNOTATION_DIR / cid]
  for folder in list_annotation_folders():
    if canonical_mag_id(folder.name) == cid:
      return folder
  return candidates[0]


def _first(folder: Path, suffixes: tuple[str, ...]) -> Path | None:
  if not folder.exists():
    return None
  for path in sorted(folder.rglob('*')):
    if path.is_file() and path.suffix.lower() in suffixes:
      return path
  return None


def fasta_path_for_mag(mag_id: object, folder: Path | None = None) -> Path | None:
  folder = Path(folder) if folder is not None else annotation_folder(mag_id)
  found = _first(folder, ('.fa', '.fasta', '.fna'))
  if found:
    return found
  token = str(mag_number(mag_id) or '')
  matches = sorted([p for p in (BASE_DIR / 'data').rglob('*') if p.is_file() and p.suffix.lower() in {'.fa', '.fasta', '.fna'} and token in p.name])
  return matches[0] if matches else None


def genbank_path_for_mag(mag_id: object, folder: Path | None = None) -> Path | None:
  folder = Path(folder) if folder is not None else annotation_folder(mag_id)
  found = _first(folder, ('.gbk', '.gbff', '.gb'))
  if found:
    return found
  token = str(mag_number(mag_id) or '')
  matches = sorted([p for p in (BASE_DIR / 'data').rglob('*') if p.is_file() and p.suffix.lower() in {'.gbk', '.gbff', '.gb'} and token in p.name])
  return matches[0] if matches else None


def file_manifest(folder: Path) -> pd.DataFrame:
  folder = Path(folder)
  if not folder.exists():
    return pd.DataFrame(columns=['file', 'relative_path', 'bytes', 'format'])
  rows = []
  for path in sorted(folder.rglob('*')):
    if path.is_file():
      rows.append({'file': path.name, 'relative_path': str(path.relative_to(folder)), 'bytes': path.stat().st_size, 'format': path.suffix.lower().lstrip('.')})
  return pd.DataFrame(rows)


def feature_table(folder: Path) -> pd.DataFrame:
  folder = Path(folder)
  candidates = []
  if folder.exists():
    candidates = [p for p in folder.rglob('*') if p.is_file() and p.suffix.lower() in {'.csv', '.tsv', '.tab'} and any(k in p.name.lower() for k in ['feature', 'gene', 'annotation'])]
  for path in sorted(candidates):
    try:
      sep = '\t' if path.suffix.lower() in {'.tsv', '.tab'} else ','
      frame = pd.read_csv(path, sep=sep)
      if not frame.empty:
        return frame
    except Exception:
      continue
  return pd.DataFrame(columns=['contig', 'start', 'end', 'strand', 'feature_id', 'product'])


def contig_table(folder: Path) -> pd.DataFrame:
  features = feature_table(folder)
  contig_col = next((c for c in ['contig', 'sequence_id', 'accession', 'seq_id'] if c in features.columns), None)
  if contig_col:
    return features.groupby(contig_col).size().rename('feature_count').reset_index().rename(columns={contig_col: 'contig'})
  fasta = _first(Path(folder), ('.fa', '.fasta', '.fna'))
  if fasta:
    rows = []
    name = None
    length = 0
    for line in fasta.read_text(errors='ignore').splitlines():
      if line.startswith('>'):
        if name is not None:
          rows.append({'contig': name, 'length': length})
        name = line[1:].split()[0]
        length = 0
      else:
        length += len(line.strip())
    if name is not None:
      rows.append({'contig': name, 'length': length})
    return pd.DataFrame(rows)
  return pd.DataFrame(columns=['contig', 'length'])


def taxonomy_summary(folder: Path) -> pd.DataFrame:
  manifest = file_manifest(folder)
  tax_files = manifest[manifest['file'].astype(str).str.contains('tax', case=False, na=False)] if not manifest.empty else manifest
  return tax_files


def annotation_summary_table(mag_id: object) -> pd.DataFrame:
  folder = annotation_folder(mag_id)
  features = feature_table(folder)
  contigs = contig_table(folder)
  return pd.DataFrame([{
    'MAG': canonical_mag_id(mag_id), 'folder': str(folder), 'folder_exists': folder.exists(),
    'feature_count': len(features), 'contig_count': len(contigs),
    'fasta_available': fasta_path_for_mag(mag_id, folder) is not None,
    'genbank_available': genbank_path_for_mag(mag_id, folder) is not None,
  }])


def feature_stats(features: pd.DataFrame) -> dict:
  if features is None or features.empty:
    return {'features': 0, 'coding_sequences': 0, 'hypothetical_proteins': 0}
  product_col = next((c for c in ['product', 'function', 'annotation'] if c in features.columns), None)
  hypothetical = int(features[product_col].astype(str).str.contains('hypothetical', case=False, na=False).sum()) if product_col else 0
  return {'features': len(features), 'coding_sequences': len(features), 'hypothetical_proteins': hypothetical}


def genome_report_metrics(folder: Path) -> dict:
  contigs = contig_table(folder)
  length = pd.to_numeric(contigs.get('length', pd.Series(dtype=float)), errors='coerce').sum() if not contigs.empty else 0
  return {'contigs': len(contigs), 'total_length_bp': int(length or 0), 'files': len(file_manifest(folder))}


def genome_organization_figure(features: pd.DataFrame, contigs: pd.DataFrame, selected_contig: object, max_features: int = 500):
  if features is None or features.empty:
    fig = go.Figure()
    fig.add_annotation(text='No feature annotation available', x=0.5, y=0.5, showarrow=False)
    return fig
  contig_col = next((c for c in ['contig', 'sequence_id', 'accession', 'seq_id'] if c in features.columns), None)
  work = features.copy()
  if contig_col and selected_contig is not None:
    work = work[work[contig_col].astype(str) == str(selected_contig)]
  work = work.head(int(max_features)).copy()
  start_col = next((c for c in ['start', 'begin', 'feature_start'] if c in work.columns), None)
  end_col = next((c for c in ['end', 'stop', 'feature_end'] if c in work.columns), None)
  if not start_col or not end_col:
    work['start'] = range(len(work))
    work['end'] = work['start'] + 1
    start_col, end_col = 'start', 'end'
  work['length'] = pd.to_numeric(work[end_col], errors='coerce').fillna(0) - pd.to_numeric(work[start_col], errors='coerce').fillna(0)
  work['label'] = work.get('product', work.get('feature_id', pd.Series(work.index.astype(str), index=work.index))).astype(str)
  fig = px.bar(work, x='length', y='label', orientation='h', title=f'Genome organization — {selected_contig}')
  fig.update_layout(height=max(500, min(1800, 20 * len(work) + 160)))
  return fig
