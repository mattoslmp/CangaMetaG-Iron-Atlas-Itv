from __future__ import annotations

import os
from pathlib import Path
import pandas as pd
import requests

EARTHDATA_PRODUCT_REGISTRY = {
  'imerg_daily': {'label': 'GPM IMERG daily precipitation', 'short_name': 'GPM_3IMERGDF'},
  'merra2_slv': {'label': 'MERRA-2 single-level diagnostics', 'short_name': 'M2T1NXSLV'},
  'merra2_flx': {'label': 'MERRA-2 surface flux diagnostics', 'short_name': 'M2T1NXFLX'},
  'merra2_lnd': {'label': 'MERRA-2 land diagnostics', 'short_name': 'M2T1NXLND'},
  'modis_ndvi': {'label': 'MODIS vegetation indices', 'short_name': 'MOD13Q1'},
  'modis_lst': {'label': 'MODIS land surface temperature', 'short_name': 'MOD11A2'},
  'smap_soil_moisture': {'label': 'SMAP soil moisture', 'short_name': 'SPL3SMP_E'},
  'podaac_sentinel6': {'label': 'Sentinel-6/Jason-CS altimetry', 'short_name': 'JASON_CS_S6A_L2_ALT_HR_STD'},
}


def earthdata_auth_status() -> dict:
  token = os.environ.get('EARTHDATA_TOKEN', '').strip()
  netrc = Path.home() / '.netrc'
  has_urs = False
  try:
    has_urs = netrc.exists() and 'urs.earthdata.nasa.gov' in netrc.read_text(errors='ignore')
  except Exception:
    pass
  return {
    'configured': bool(token or has_urs),
    'token_present': bool(token),
    'netrc_has_urs': bool(has_urs),
    'method': 'token' if token else 'netrc' if has_urs else 'not configured',
  }


def earthdata_product_table() -> pd.DataFrame:
  return pd.DataFrame([{'product_key': key, **value} for key, value in EARTHDATA_PRODUCT_REGISTRY.items()])


def search_earthdata_collections(product_key: str, max_collections: int = 10, use_cache=True) -> pd.DataFrame:
  registry = EARTHDATA_PRODUCT_REGISTRY.get(product_key, {'short_name': product_key, 'label': product_key})
  try:
    response = requests.get('https://cmr.earthdata.nasa.gov/search/collections.json', params={'short_name': registry['short_name'], 'page_size': int(max_collections)}, timeout=60)
    response.raise_for_status()
    entries = response.json().get('feed', {}).get('entry', [])
    rows = [{'product_key': product_key, 'short_name': item.get('short_name'), 'version_id': item.get('version_id'), 'title': item.get('title'), 'concept_id': item.get('id'), 'query_status': 'ok'} for item in entries]
    return pd.DataFrame(rows)
  except Exception as exc:
    return pd.DataFrame([{'product_key': product_key, 'short_name': registry['short_name'], 'query_status': 'error', 'message': str(exc)}])


def search_earthdata_granules(product_key: str, lat, lon, start_date, end_date, buffer_m=1000, max_granules=20, use_cache=True) -> pd.DataFrame:
  registry = EARTHDATA_PRODUCT_REGISTRY.get(product_key, {'short_name': product_key})
  delta = max(float(buffer_m) / 111_000.0, 0.001)
  bbox = f'{float(lon)-delta},{float(lat)-delta},{float(lon)+delta},{float(lat)+delta}'
  temporal = f'{pd.to_datetime(start_date).isoformat()},{pd.to_datetime(end_date).isoformat()}'
  try:
    response = requests.get('https://cmr.earthdata.nasa.gov/search/granules.json', params={'short_name': registry['short_name'], 'bounding_box': bbox, 'temporal': temporal, 'page_size': int(max_granules)}, timeout=60)
    response.raise_for_status()
    entries = response.json().get('feed', {}).get('entry', [])
    return pd.DataFrame([{
      'product_key': product_key, 'granule_id': item.get('producer_granule_id') or item.get('title'),
      'time_start': item.get('time_start'), 'time_end': item.get('time_end'),
      'coverage_status': 'covered', 'download_status': 'metadata_only',
    } for item in entries])
  except Exception as exc:
    return pd.DataFrame([{'product_key': product_key, 'coverage_status': 'query_error', 'download_status': 'not_downloaded', 'message': str(exc)}])


def earthaccess_download_product(product_key: str, lat, lon, start_date, end_date,
                                 buffer_m=1000, max_granules=20, use_cache=True,
                                 force_update=False) -> pd.DataFrame:
  frame = search_earthdata_granules(product_key, lat, lon, start_date, end_date, buffer_m=buffer_m, max_granules=max_granules, use_cache=use_cache)
  if not frame.empty and 'download_status' not in frame.columns:
    frame['download_status'] = 'metadata_only'
  return frame
