from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import re
import secrets
from typing import Any
from urllib.parse import unquote

import pandas as pd

from .runtime_paths import APP_STATE_DIR

VISITOR_LOG_PATH = APP_STATE_DIR / "visitor_analytics.jsonl"
GEOLOCATION_CACHE_PATH = APP_STATE_DIR / "visitor_geolocation_cache.json"
VISIT_SESSION_KEY = "_cangametag_visit_recorded"
VISITOR_SESSION_TOKEN_KEY = "_cangametag_visitor_session_token"

_LOCATION_HEADERS = {
  "country_code": (
    "CF-IPCountry",
    "X-Country-Code",
    "CloudFront-Viewer-Country",
    "X-Appengine-Country",
    "X-Vercel-IP-Country",
  ),
  "country_name": (
    "CF-IPCountry-Name",
    "X-Country-Name",
    "X-Vercel-IP-Country-Name",
  ),
  "region": (
    "CF-Region",
    "X-Region",
    "X-Region-Name",
    "CloudFront-Viewer-Country-Region-Name",
    "X-Vercel-IP-Country-Region",
  ),
  "city": (
    "CF-IPCity",
    "X-City",
    "X-Appengine-City",
    "CloudFront-Viewer-City",
    "X-Vercel-IP-City",
  ),
  "latitude": (
    "CF-IPLatitude",
    "X-Latitude",
    "CloudFront-Viewer-Latitude",
    "X-Vercel-IP-Latitude",
  ),
  "longitude": (
    "CF-IPLongitude",
    "X-Longitude",
    "CloudFront-Viewer-Longitude",
    "X-Vercel-IP-Longitude",
  ),
}


def _safe_headers(st) -> dict[str, str]:
  try:
    raw = dict(getattr(st.context, "headers", {}) or {})
  except Exception:
    raw = {}
  return {str(key): str(value) for key, value in raw.items()}


def _decode_header_value(value: object) -> str:
  text = str(value or "").strip()
  if not text:
    return ""
  try:
    return unquote(text).strip()
  except Exception:
    return text


def _header(headers: dict[str, str], *names: str) -> str:
  lookup = {str(key).casefold(): str(value) for key, value in headers.items()}
  for name in names:
    value = _decode_header_value(lookup.get(str(name).casefold(), ""))
    if value:
      return value
  return ""


def _public_ip(value: object) -> str:
  text = str(value or "").strip().strip('"[]')
  if not text:
    return ""
  text = re.sub(r"^for=", "", text, flags=re.IGNORECASE).strip().strip('"[]')
  if text.startswith("[") and "]" in text:
    text = text[1:text.index("]")]
  elif text.count(":") == 1 and "." in text:
    text = text.rsplit(":", 1)[0]
  try:
    address = ipaddress.ip_address(text)
  except ValueError:
    return ""
  if not address.is_global:
    return ""
  return str(address)


def _context_public_ip(st) -> str:
  """Return Streamlit's WebSocket connection IP when available."""
  try:
    return _public_ip(getattr(st.context, "ip_address", None))
  except Exception:
    return ""


def _extract_public_ip(headers: dict[str, str]) -> str:
  candidates: list[str] = []
  for name in (
    "CF-Connecting-IP",
    "True-Client-IP",
    "X-Real-IP",
    "X-Client-IP",
    "Fly-Client-IP",
    "X-Forwarded-For",
    "Forwarded",
  ):
    value = _header(headers, name)
    if not value:
      continue
    if name.casefold() == "forwarded":
      candidates.extend(re.findall(r"for=([^;,]+)", value, flags=re.IGNORECASE))
    else:
      candidates.extend(part.strip() for part in value.split(","))
  for candidate in candidates:
    ip = _public_ip(candidate)
    if ip:
      return ip
  return ""


def _load_geo_cache() -> dict[str, dict[str, Any]]:
  try:
    data = json.loads(GEOLOCATION_CACHE_PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}
  except Exception:
    return {}


def _save_geo_cache(cache: dict[str, dict[str, Any]]) -> None:
  try:
    GEOLOCATION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    GEOLOCATION_CACHE_PATH.write_text(
      json.dumps(cache, ensure_ascii=False, indent=2),
      encoding="utf-8",
    )
  except Exception:
    pass


def _normalise_location(payload: dict[str, Any], source: str) -> dict[str, Any]:
  country_code = str(
    payload.get("country_code")
    or payload.get("country_code2")
    or payload.get("countryCode")
    or ""
  ).strip().upper()
  country_name = str(
    payload.get("country_name")
    or payload.get("country")
    or payload.get("country_name_official")
    or ""
  ).strip()
  city = _decode_header_value(payload.get("city") or "")
  region = _decode_header_value(
    payload.get("region")
    or payload.get("region_name")
    or payload.get("regionName")
    or ""
  )

  latitude_value = payload.get("latitude", payload.get("lat"))
  longitude_value = payload.get("longitude", payload.get("lon"))
  location_text = str(payload.get("loc") or "").strip()
  if location_text and "," in location_text:
    loc_lat, loc_lon = location_text.split(",", 1)
    if latitude_value in (None, ""):
      latitude_value = loc_lat
    if longitude_value in (None, ""):
      longitude_value = loc_lon

  latitude = pd.to_numeric(latitude_value, errors="coerce")
  longitude = pd.to_numeric(longitude_value, errors="coerce")
  if pd.notna(latitude) and not (-90 <= float(latitude) <= 90):
    latitude = float("nan")
  if pd.notna(longitude) and not (-180 <= float(longitude) <= 180):
    longitude = float("nan")

  return {
    "country_code": country_code,
    "country_name": country_name,
    "country": country_name or country_code,
    "region": region,
    "city": city,
    "latitude": None if pd.isna(latitude) else float(latitude),
    "longitude": None if pd.isna(longitude) else float(longitude),
    "geolocation_source": source,
  }


def _header_location(headers: dict[str, str]) -> dict[str, Any]:
  payload: dict[str, Any] = {}
  for field, names in _LOCATION_HEADERS.items():
    payload[field] = _header(headers, *names)
  return _normalise_location(payload, "proxy headers")


def _location_is_useful(location: dict[str, Any]) -> bool:
  return bool(
    location.get("country_name")
    or location.get("country_code")
    or location.get("city")
    or (
      location.get("latitude") is not None
      and location.get("longitude") is not None
    )
  )


def _location_needs_enrichment(location: dict[str, Any]) -> bool:
  return not (
    location.get("city")
    and location.get("latitude") is not None
    and location.get("longitude") is not None
  )


def _lookup_ip_location(ip: str) -> dict[str, Any]:
  if not ip:
    return _normalise_location({}, "unavailable")
  cache_key = hashlib.sha256(ip.encode("utf-8")).hexdigest()
  cache = _load_geo_cache()
  cached = cache.get(cache_key)
  if isinstance(cached, dict) and _location_is_useful(cached):
    result = dict(cached)
    result["geolocation_source"] = "local IP geolocation cache"
    return result

  try:
    import requests
  except Exception:
    return _normalise_location({}, "geolocation dependency unavailable")

  providers = (
    (f"https://ipwho.is/{ip}", "ipwho.is"),
    (f"https://ipapi.co/{ip}/json/", "ipapi.co"),
    (f"https://ipinfo.io/{ip}/json", "ipinfo.io"),
  )
  headers = {
    "User-Agent": "CangaMetaG-Iron-Atlas visitor geography/2.0",
    "Accept": "application/json",
  }
  for url, provider in providers:
    try:
      response = requests.get(url, headers=headers, timeout=4.0)
      response.raise_for_status()
      payload = response.json()
      if not isinstance(payload, dict):
        continue
      if payload.get("error") is True or payload.get("success") is False:
        continue
      result = _normalise_location(payload, provider)
      if _location_is_useful(result):
        cache[cache_key] = result
        _save_geo_cache(cache)
        return result
    except Exception:
      continue
  return _normalise_location({}, "geolocation lookup unavailable")


def _merge_locations(primary: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
  merged = dict(primary)
  for key in (
    "country_code",
    "country_name",
    "country",
    "region",
    "city",
    "latitude",
    "longitude",
  ):
    value = merged.get(key)
    if value in (None, ""):
      merged[key] = fallback.get(key)
  sources = [
    str(primary.get("geolocation_source") or "").strip(),
    str(fallback.get("geolocation_source") or "").strip(),
  ]
  merged["geolocation_source"] = " + ".join(
    value for value in dict.fromkeys(sources) if value
  ) or "unavailable"
  return merged


def _session_token(st) -> str:
  try:
    token = str(st.session_state.get(VISITOR_SESSION_TOKEN_KEY, "") or "")
    if not token:
      token = secrets.token_urlsafe(18)
      st.session_state[VISITOR_SESSION_TOKEN_KEY] = token
    return token
  except Exception:
    return secrets.token_urlsafe(18)


def record_visit(
  st,
  app_version: str = "",
  database_version: str = "",
  page: str = "session_entry",
) -> None:
  """Record one visit per Streamlit session and geolocate it when possible.

  Raw client IP addresses are never written to disk. The IP is used only during
  the current request to derive an irreversible visitor hash and an approximate
  country/city through Streamlit context, proxy headers or a cached public
  geolocation lookup.
  """
  try:
    if bool(st.session_state.get(VISIT_SESSION_KEY, False)):
      return
  except Exception:
    pass

  VISITOR_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
  headers = _safe_headers(st)
  ip = _context_public_ip(st) or _extract_public_ip(headers)
  user_agent = _header(headers, "User-Agent")
  token = _session_token(st)
  fingerprint_basis = f"{ip}|{user_agent}" if ip else f"session|{token}|{user_agent}"
  fingerprint = hashlib.sha256(fingerprint_basis.encode("utf-8")).hexdigest()[:20]

  location = _header_location(headers)
  if ip and _location_needs_enrichment(location):
    location = _merge_locations(location, _lookup_ip_location(ip))

  row = {
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "visitor_id": fingerprint,
    "page": page,
    "app_version": app_version,
    "database_version": database_version,
    "user_agent": str(user_agent)[:500],
    **location,
  }
  try:
    with VISITOR_LOG_PATH.open("a", encoding="utf-8") as handle:
      handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
      st.session_state[VISIT_SESSION_KEY] = True
      st.session_state["_visitor_last_location"] = location
    except Exception:
      pass
  except Exception:
    pass


def load_visits() -> pd.DataFrame:
  columns = [
    "timestamp_utc",
    "visitor_id",
    "page",
    "country",
    "country_code",
    "country_name",
    "region",
    "city",
    "latitude",
    "longitude",
    "geolocation_source",
    "app_version",
    "database_version",
    "user_agent",
  ]
  if not VISITOR_LOG_PATH.exists():
    return pd.DataFrame(columns=columns)
  rows: list[dict[str, Any]] = []
  try:
    lines = VISITOR_LOG_PATH.read_text(
      encoding="utf-8", errors="ignore"
    ).splitlines()
  except Exception:
    return pd.DataFrame(columns=columns)
  for line in lines:
    try:
      value = json.loads(line)
      if isinstance(value, dict):
        rows.append(value)
    except Exception:
      continue
  frame = pd.DataFrame(rows)
  for column in columns:
    if column not in frame.columns:
      frame[column] = ""
  return frame[columns]


def _recognised(series: pd.Series) -> pd.Series:
  text = series.fillna("").astype(str).str.strip()
  return text.mask(
    text.str.casefold().isin({"", "unknown", "none", "nan", "xx", "zz"})
  )


def _country_series(visits: pd.DataFrame) -> pd.Series:
  return (
    _recognised(visits["country_name"])
    .fillna(_recognised(visits["country_code"]))
    .fillna(_recognised(visits["country"]))
  )


def summary_metrics() -> dict[str, int]:
  visits = load_visits()
  if visits.empty:
    return {
      "visits": 0,
      "total_visits": 0,
      "unique_visitors": 0,
      "countries": 0,
      "cities": 0,
    }
  country = _country_series(visits)
  city = _recognised(visits["city"])
  total = int(len(visits))
  return {
    "visits": total,
    "total_visits": total,
    "unique_visitors": int(visits["visitor_id"].astype(str).nunique()),
    "countries": int(country.nunique(dropna=True)),
    "cities": int(city.nunique(dropna=True)),
  }


def country_summary() -> pd.DataFrame:
  visits = load_visits()
  columns = ["country_name", "country_code", "visits", "unique_visitors"]
  if visits.empty:
    return pd.DataFrame(columns=columns)
  work = visits.copy()
  work["country_name"] = _country_series(work).fillna("Unknown")
  work["country_code"] = _recognised(work["country_code"]).fillna("")
  out = work.groupby(
    ["country_name", "country_code"], dropna=False
  ).agg(
    visits=("visitor_id", "size"),
    unique_visitors=("visitor_id", "nunique"),
  ).reset_index()
  return out.sort_values(
    ["visits", "country_name"], ascending=[False, True]
  ).reset_index(drop=True)


def city_summary() -> pd.DataFrame:
  visits = load_visits()
  columns = [
    "country_name",
    "country_code",
    "region",
    "city",
    "latitude",
    "longitude",
    "visits",
    "unique_visitors",
  ]
  if visits.empty:
    return pd.DataFrame(columns=columns)
  work = visits.copy()
  work["country_name"] = _country_series(work).fillna("Unknown")
  work["country_code"] = _recognised(work["country_code"]).fillna("")
  work["region"] = _recognised(work["region"]).fillna("Unknown")
  work["city"] = _recognised(work["city"])
  work["latitude"] = pd.to_numeric(work["latitude"], errors="coerce")
  work["longitude"] = pd.to_numeric(work["longitude"], errors="coerce")
  work = work[work["city"].notna()].copy()
  if work.empty:
    return pd.DataFrame(columns=columns)
  out = work.groupby(
    ["country_name", "country_code", "region", "city"], dropna=False
  ).agg(
    latitude=("latitude", "mean"),
    longitude=("longitude", "mean"),
    visits=("visitor_id", "size"),
    unique_visitors=("visitor_id", "nunique"),
  ).reset_index()
  return out.sort_values(
    ["visits", "country_name", "city"],
    ascending=[False, True, True],
  ).reset_index(drop=True)


def clear_visitor_data() -> None:
  for path in (VISITOR_LOG_PATH, GEOLOCATION_CACHE_PATH):
    try:
      path.unlink(missing_ok=True)
    except Exception:
      pass
