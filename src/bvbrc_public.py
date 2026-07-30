from __future__ import annotations

from pathlib import Path
import re
from urllib.parse import quote

import pandas as pd
import requests


def genome_url_from_id(genome_id: object) -> str:
  gid = quote(str(genome_id).strip())
  return f'https://www.bv-brc.org/view/Genome/{gid}'


def genome_tab_url(genome_id: object, tab: str = 'overview') -> str:
  gid = quote(str(genome_id).strip())
  return f'https://www.bv-brc.org/view/Genome/{gid}#{quote(str(tab))}'


def genome_tab_links(genome_id: object) -> dict[str, str]:
  return {
    'Overview': genome_tab_url(genome_id, 'overview'),
    'Features': genome_tab_url(genome_id, 'features'),
    'Pathways': genome_tab_url(genome_id, 'pathways'),
    'Subsystems': genome_tab_url(genome_id, 'subsystems'),
  }


def feature_browser_url(genome_id: object) -> str:
  return genome_tab_url(genome_id, 'features')


def workspace_mag_url(mag_id: object) -> str:
  return f'https://www.bv-brc.org/workspace/{quote(str(mag_id).strip())}'


def _canonical_mag_id(mag_id: object) -> str:
  digits = re.search(r'\d+', str(mag_id))
  return f'MAG{int(digits.group(0))}' if digits else str(mag_id).strip()


def _public_link_candidates() -> list[Path]:
  project_root = Path(__file__).resolve().parents[1]
  return [
    project_root / 'data' / 'bvbrc_public_links.csv',
    project_root / 'tables' / 'bvbrc_public_links.csv',
  ]


def public_link_for_mag(mag_id: object) -> dict[str, str]:
  """Return the available BV-BRC record for one MAG.

  Every MAG receives its deterministic workspace URL. When a packaged mapping
  table contains a public BV-BRC Genome/Annotation ID, the exact record fields
  are merged and the official genome and feature links are derived from that ID.
  No Genome ID is inferred from the MAG number.
  """
  canonical = _canonical_mag_id(mag_id)
  record: dict[str, str] = {
    'MAG': canonical,
    'Workspace MAG URL': workspace_mag_url(canonical),
  }

  for candidate in _public_link_candidates():
    if not candidate.exists():
      continue
    try:
      frame = pd.read_csv(candidate, dtype=str).fillna('')
    except Exception:
      continue
    mag_column = next(
      (column for column in frame.columns if str(column).strip().casefold() in {'mag', 'mag id', 'mag_id'}),
      None,
    )
    if mag_column is None:
      continue
    normalized = frame[mag_column].map(_canonical_mag_id)
    selected = frame.loc[normalized.eq(canonical)]
    if selected.empty:
      continue
    row = selected.iloc[0]
    for column, value in row.items():
      clean = str(value).strip()
      if clean and clean.casefold() not in {'nan', 'none', 'na', 'n/a'}:
        record[str(column)] = clean
    break

  genome_id = str(record.get('BV-BRC Genome ID', '')).strip()
  if genome_id:
    record.setdefault('Genome Browser URL', feature_browser_url(genome_id))
    record.setdefault('BV-BRC genome URL', genome_url_from_id(genome_id))
  return record


def api_url(resource: str, query: str = '') -> str:
  resource = str(resource).strip('/ ')
  base = f'https://www.bv-brc.org/api/{resource}/'
  return base + (f'?{query}' if query else '')


def fetch_bvbrc_json(url: str, timeout: int = 60):
  response = requests.get(url, headers={'Accept': 'application/json'}, timeout=timeout)
  response.raise_for_status()
  return response.json()


def normalize_public_feature_table(payload) -> pd.DataFrame:
  if isinstance(payload, pd.DataFrame):
    frame = payload.copy()
  elif isinstance(payload, dict):
    rows = payload.get('response', {}).get('docs') or payload.get('docs') or payload.get('data') or []
    frame = pd.DataFrame(rows)
  elif isinstance(payload, list):
    frame = pd.DataFrame(payload)
  else:
    frame = pd.DataFrame()
  rename = {
    'patric_id': 'feature_id', 'refseq_locus_tag': 'locus_tag', 'product': 'product',
    'start': 'start', 'end': 'end', 'strand': 'strand', 'sequence_id': 'contig',
  }
  return frame.rename(columns={k: v for k, v in rename.items() if k in frame.columns})
