from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_visitor_map_city_final_transform.py"


def test_empty_city_geolocation_notice_is_filtered_from_public_app() -> None:
  source = TRANSFORM.read_text(encoding="utf-8")
  assert "CANGAMETAG_VISITOR_MAP_CITY_FINAL_V3" in source
  assert "As visitas foram contadas, mas ainda não há uma cidade reconhecida" in source
  assert "Visits were counted, but no city has yet been recognized" in source
  assert "return None" in source
  assert "finally:" in source
  assert "st.info = original_info" in source
