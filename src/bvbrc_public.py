from __future__ import annotations

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


def public_link_for_mag(mag_id: object) -> str:
  digits = re.search(r'\d+', str(mag_id))
  return workspace_mag_url(f'MAG{digits.group(0)}' if digits else str(mag_id))


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
