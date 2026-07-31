from __future__ import annotations

from pathlib import Path

from src import visitor_analytics


class FakeContext:
  def __init__(self, headers: dict[str, str]):
    self.headers = headers


class FakeStreamlit:
  def __init__(self, headers: dict[str, str]):
    self.context = FakeContext(headers)
    self.session_state: dict[str, object] = {}


def test_one_geolocated_visit_per_streamlit_session(tmp_path: Path, monkeypatch) -> None:
  log_path = tmp_path / "visitor_analytics.jsonl"
  cache_path = tmp_path / "visitor_geolocation_cache.json"
  monkeypatch.setattr(visitor_analytics, "VISITOR_LOG_PATH", log_path)
  monkeypatch.setattr(visitor_analytics, "GEOLOCATION_CACHE_PATH", cache_path)
  monkeypatch.setattr(
    visitor_analytics,
    "_lookup_ip_location",
    lambda ip: {
      "country_code": "BR",
      "country_name": "Brazil",
      "country": "Brazil",
      "region": "Rio de Janeiro",
      "city": "Itaperuna",
      "latitude": -21.2,
      "longitude": -41.9,
      "geolocation_source": "test provider",
    },
  )
  st = FakeStreamlit({
    "X-Forwarded-For": "8.8.8.8, 10.0.0.1",
    "User-Agent": "pytest-browser",
  })
  visitor_analytics.record_visit(st, app_version="test", page="session_entry")
  visitor_analytics.record_visit(st, app_version="test", page="session_entry")

  visits = visitor_analytics.load_visits()
  assert len(visits) == 1
  assert visits.iloc[0]["country_name"] == "Brazil"
  assert visits.iloc[0]["city"] == "Itaperuna"
  assert visits.iloc[0]["geolocation_source"] == "test provider"
  assert "8.8.8.8" not in log_path.read_text(encoding="utf-8")
  assert st.session_state[visitor_analytics.VISIT_SESSION_KEY] is True

  metrics = visitor_analytics.summary_metrics()
  assert metrics["total_visits"] == 1
  assert metrics["unique_visitors"] == 1
  assert metrics["countries"] == 1
  assert metrics["cities"] == 1


def test_proxy_location_avoids_external_lookup(tmp_path: Path, monkeypatch) -> None:
  monkeypatch.setattr(visitor_analytics, "VISITOR_LOG_PATH", tmp_path / "visits.jsonl")
  monkeypatch.setattr(visitor_analytics, "GEOLOCATION_CACHE_PATH", tmp_path / "geo.json")

  def fail_lookup(ip: str):
    raise AssertionError("external lookup should not run when proxy geography exists")

  monkeypatch.setattr(visitor_analytics, "_lookup_ip_location", fail_lookup)
  st = FakeStreamlit({
    "CF-IPCountry": "BR",
    "CF-IPCountry-Name": "Brazil",
    "CF-Region": "Rio de Janeiro",
    "CF-IPCity": "Itaperuna",
    "User-Agent": "pytest-browser",
  })
  visitor_analytics.record_visit(st)
  row = visitor_analytics.load_visits().iloc[0]
  assert row["country_code"] == "BR"
  assert row["country_name"] == "Brazil"
  assert row["region"] == "Rio de Janeiro"
  assert row["city"] == "Itaperuna"
  assert row["geolocation_source"] == "proxy headers"
