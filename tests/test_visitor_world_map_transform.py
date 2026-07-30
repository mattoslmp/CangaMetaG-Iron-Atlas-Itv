from __future__ import annotations

from pathlib import Path
import runpy


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = PROJECT_ROOT / "src" / "app_visitor_world_map_transform.py"

SOURCE = '''def visitor_counter_public_footer(key: str = "public_footer"):\n  return key\n\n\ndef visitor_counter_compact():\n  return None\n'''


def apply_transform(source: str) -> str:
  namespace = runpy.run_path(str(TRANSFORM), init_globals={"source": source})
  return str(namespace["source"])


def test_transform_adds_total_and_world_map() -> None:
  transformed = apply_transform(SOURCE)
  compile(transformed, "generated_visitor_footer.py", "exec")
  assert "def _visitor_world_map_frame(" in transformed
  assert "def _visitor_world_map_figure(" in transformed
  assert "<b>Visits:</b>" in transformed
  assert "Mapa-múndi detalhado de visitas" in transformed
  assert "Visit details by country, region and city" in transformed


def test_transform_preserves_following_function() -> None:
  transformed = apply_transform(SOURCE)
  assert "def visitor_counter_compact():" in transformed


def test_transform_is_idempotent() -> None:
  once = apply_transform(SOURCE)
  twice = apply_transform(once)
  assert twice == once
