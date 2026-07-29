from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pandas as pd

from .runtime_paths import APP_STATE_DIR

VISITOR_LOG_PATH = APP_STATE_DIR / 'visitor_analytics.jsonl'


def _safe_headers(st) -> dict:
  try:
    return dict(getattr(st.context, 'headers', {}) or {})
  except Exception:
    return {}


def record_visit(st, app_version='', database_version='', page='session_entry') -> None:
  VISITOR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
  headers = _safe_headers(st)
  forwarded = headers.get('X-Forwarded-For') or headers.get('x-forwarded-for') or ''
  ip = str(forwarded).split(',')[0].strip()
  user_agent = headers.get('User-Agent') or headers.get('user-agent') or ''
  fingerprint = hashlib.sha256(f'{ip}|{user_agent}'.encode()).hexdigest()[:20]
  row = {
    'timestamp_utc': datetime.now(timezone.utc).isoformat(),
    'visitor_id': fingerprint,
    'page': page,
    'app_version': app_version,
    'database_version': database_version,
    'country': headers.get('CF-IPCountry', ''),
    'city': headers.get('CF-IPCity', ''),
    'user_agent': str(user_agent)[:500],
  }
  try:
    with VISITOR_LOG_PATH.open('a', encoding='utf-8') as handle:
      handle.write(json.dumps(row, ensure_ascii=False) + '\n')
  except Exception:
    pass


def load_visits() -> pd.DataFrame:
  if not VISITOR_LOG_PATH.exists():
    return pd.DataFrame(columns=['timestamp_utc', 'visitor_id', 'page', 'country', 'city'])
  rows = []
  for line in VISITOR_LOG_PATH.read_text(encoding='utf-8', errors='ignore').splitlines():
    try:
      rows.append(json.loads(line))
    except Exception:
      continue
  return pd.DataFrame(rows)


def summary_metrics() -> dict:
  visits = load_visits()
  if visits.empty:
    return {'visits': 0, 'unique_visitors': 0, 'countries': 0, 'cities': 0}
  return {
    'visits': len(visits),
    'unique_visitors': visits.get('visitor_id', pd.Series(dtype=str)).nunique(),
    'countries': visits.get('country', pd.Series(dtype=str)).replace('', pd.NA).nunique(),
    'cities': visits.get('city', pd.Series(dtype=str)).replace('', pd.NA).nunique(),
  }


def country_summary() -> pd.DataFrame:
  visits = load_visits()
  if visits.empty or 'country' not in visits:
    return pd.DataFrame(columns=['country', 'visits', 'unique_visitors'])
  out = visits.assign(country=visits['country'].replace('', 'Unknown')).groupby('country').agg(visits=('country', 'size'), unique_visitors=('visitor_id', 'nunique')).reset_index()
  return out.sort_values('visits', ascending=False)


def city_summary() -> pd.DataFrame:
  visits = load_visits()
  if visits.empty or 'city' not in visits:
    return pd.DataFrame(columns=['city', 'visits', 'unique_visitors'])
  out = visits.assign(city=visits['city'].replace('', 'Unknown')).groupby('city').agg(visits=('city', 'size'), unique_visitors=('visitor_id', 'nunique')).reset_index()
  return out.sort_values('visits', ascending=False)


def clear_visitor_data() -> None:
  try:
    VISITOR_LOG_PATH.unlink(missing_ok=True)
  except Exception:
    pass
