from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
import hashlib
import json

import pandas as pd
import requests

from .runtime_paths import APP_CACHE_DIR

NASA_POWER_DEFAULT_PARAMS = ['T2M', 'T2M_MAX', 'T2M_MIN', 'RH2M', 'PRECTOTCORR', 'WS2M']
NASA_POWER_PARAMETER_DICTIONARY = {
  'T2M': 'Temperature at 2 m (°C)',
  'T2M_MAX': 'Maximum temperature at 2 m (°C)',
  'T2M_MIN': 'Minimum temperature at 2 m (°C)',
  'RH2M': 'Relative humidity at 2 m (%)',
  'PRECTOTCORR': 'Corrected precipitation (mm day−1)',
  'WS2M': 'Wind speed at 2 m (m s−1)',
}


def _date(value) -> str:
  return pd.to_datetime(value).strftime('%Y%m%d')


def _iso(value) -> str:
  return pd.to_datetime(value).strftime('%Y-%m-%d')


def _cache_path(prefix: str, payload: dict) -> Path:
  digest = hashlib.sha256(json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()[:20]
  path = APP_CACHE_DIR / 'api' / f'{prefix}_{digest}.csv'
  path.parent.mkdir(parents=True, exist_ok=True)
  return path


def fetch_nasa_power_daily(lat, lon, start_date, end_date, parameters=None, use_cache=True) -> pd.DataFrame:
  parameters = list(parameters or NASA_POWER_DEFAULT_PARAMS)
  payload = {'lat': float(lat), 'lon': float(lon), 'start': _date(start_date), 'end': _date(end_date), 'parameters': parameters}
  cache = _cache_path('nasa_power', payload)
  if use_cache and cache.exists():
    return pd.read_csv(cache)
  url = 'https://power.larc.nasa.gov/api/temporal/daily/point'
  response = requests.get(url, params={
    'parameters': ','.join(parameters), 'community': 'AG', 'longitude': float(lon),
    'latitude': float(lat), 'start': payload['start'], 'end': payload['end'], 'format': 'JSON',
  }, timeout=60)
  response.raise_for_status()
  data = response.json().get('properties', {}).get('parameter', {})
  dates = sorted({d for values in data.values() for d in values})
  frame = pd.DataFrame({'date': pd.to_datetime(dates, format='%Y%m%d', errors='coerce')})
  for parameter in parameters:
    values = data.get(parameter, {})
    frame[parameter] = [values.get(d) for d in dates]
  frame['latitude'] = float(lat)
  frame['longitude'] = float(lon)
  frame['source'] = 'NASA POWER'
  frame.to_csv(cache, index=False)
  return frame


def test_chirps_climateserv_connection(lat, lon, start_date, buffer_m=1000, timeout_s=90) -> dict:
  endpoint = 'https://climateserv.servirglobal.net/api/submitDataRequest/'
  try:
    response = requests.get('https://climateserv.servirglobal.net', timeout=min(int(timeout_s), 30))
    return {'ok': response.status_code < 500, 'message': f'HTTP {response.status_code}', 'endpoint_submit': endpoint, 'rows_returned': 0}
  except Exception as exc:
    return {'ok': False, 'message': str(exc), 'endpoint_submit': endpoint, 'rows_returned': 0}


def fetch_chirps_daily_climateserv(lat, lon, start_date, end_date, buffer_m=1000, use_cache=True, timeout_s=300) -> pd.DataFrame:
  # ClimateSERV is asynchronous and frequently unavailable. Return an explicit
  # metadata row rather than inventing precipitation values.
  status = test_chirps_climateserv_connection(lat, lon, start_date, buffer_m=buffer_m, timeout_s=timeout_s)
  return pd.DataFrame([{
    'date_start': _iso(start_date), 'date_end': _iso(end_date), 'latitude': float(lat),
    'longitude': float(lon), 'coverage_status': 'endpoint_reachable' if status['ok'] else 'unavailable',
    'source': 'CHIRPS / ClimateSERV', 'message': status['message'],
  }])


def _copernicus_token() -> str:
  client_id = os.environ.get('COPERNICUS_CLIENT_ID', '').strip()
  secret = os.environ.get('COPERNICUS_CLIENT_SECRET', '').strip()
  if not client_id or not secret:
    raise RuntimeError('COPERNICUS_CLIENT_ID and COPERNICUS_CLIENT_SECRET are required.')
  response = requests.post(
    'https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token',
    data={'grant_type': 'client_credentials', 'client_id': client_id, 'client_secret': secret}, timeout=60,
  )
  response.raise_for_status()
  return str(response.json().get('access_token', ''))


def _coverage_row(source, lat, lon, start_date, end_date, status='metadata_only', **extra) -> pd.DataFrame:
  row = {
    'source': source, 'latitude': float(lat), 'longitude': float(lon),
    'start_date': _iso(start_date), 'end_date': _iso(end_date),
    'coverage_status': status,
  }
  row.update(extra)
  return pd.DataFrame([row])


def fetch_sentinel2_catalog_coverage(lat, lon, start_date, end_date, buffer_m=1000, max_cloud_coverage=80, use_cache=True):
  return _coverage_row('Copernicus Sentinel-2 L2A', lat, lon, start_date, end_date,
                       status='credentials_required', buffer_m=buffer_m, max_cloud_coverage=max_cloud_coverage)


def fetch_sentinel1_catalog_coverage(lat, lon, start_date, end_date, buffer_m=1000, use_cache=True):
  return _coverage_row('Copernicus Sentinel-1 GRD', lat, lon, start_date, end_date,
                       status='credentials_required', buffer_m=buffer_m)


def fetch_sentinel6_altimetry_granules(lat, lon, start_date, end_date, buffer_m=1000, use_cache=True):
  return _coverage_row('NASA CMR / Sentinel-6', lat, lon, start_date, end_date,
                       status='metadata_only', buffer_m=buffer_m)


def fetch_sentinelhub_monthly_indices(lat, lon, start_date, end_date, buffer_m=1000, max_cloud_coverage=80, use_cache=True):
  _copernicus_token()
  return _coverage_row('Copernicus Sentinel-2 statistical API', lat, lon, start_date, end_date,
                       status='authenticated_no_download', buffer_m=buffer_m, max_cloud_coverage=max_cloud_coverage)


def fetch_sentinel1_monthly_backscatter(lat, lon, start_date, end_date, buffer_m=1000, use_cache=True):
  _copernicus_token()
  return _coverage_row('Copernicus Sentinel-1 statistical API', lat, lon, start_date, end_date,
                       status='authenticated_no_download', buffer_m=buffer_m)


def fetch_soilgrids_point(lat, lon, properties=None, depths=None, use_cache=True) -> pd.DataFrame:
  properties = list(properties or ['clay', 'sand', 'silt', 'soc', 'phh2o'])
  depths = list(depths or ['0-5cm'])
  url = 'https://rest.isric.org/soilgrids/v2.0/properties/query'
  response = requests.get(url, params=[('lon', float(lon)), ('lat', float(lat))] + [('property', p) for p in properties] + [('depth', d) for d in depths] + [('value', 'mean')], timeout=60)
  response.raise_for_status()
  payload = response.json()
  rows = []
  for layer in payload.get('properties', {}).get('layers', []):
    prop = layer.get('name')
    for depth in layer.get('depths', []):
      values = depth.get('values', {})
      rows.append({'property': prop, 'depth': depth.get('label'), 'mean': values.get('mean'), 'latitude': float(lat), 'longitude': float(lon), 'source': 'SoilGrids'})
  return pd.DataFrame(rows)


def fetch_mapbiomas_gee_landcover(lat, lon, year=None, buffer_m=1000, use_cache=True) -> pd.DataFrame:
  return pd.DataFrame([{
    'source': 'MapBiomas / Google Earth Engine', 'latitude': float(lat), 'longitude': float(lon),
    'year': int(year or datetime.now().year), 'buffer_m': int(buffer_m),
    'coverage_status': 'earth_engine_authentication_required',
  }])
