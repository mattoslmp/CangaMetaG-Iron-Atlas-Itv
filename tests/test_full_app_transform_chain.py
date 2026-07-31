from __future__ import annotations

from pathlib import Path
import re
import runpy


ROOT = Path(__file__).resolve().parents[1]


def _transformed_app_source() -> tuple[str, list[str]]:
  launcher = (ROOT / "app.py").read_text(encoding="utf-8")
  transform_names = re.findall(
    r'Path\(__file__\)\.with_name\("src"\)\s*/\s*"([^"]+_transform\.py)"',
    launcher,
  )
  assert transform_names, "No app transforms were discovered in app.py"

  source = (ROOT / "app_core.py").read_text(encoding="utf-8")
  for name in transform_names:
    source = runpy.run_path(
      str(ROOT / "src" / name),
      init_globals={"source": source},
    )["source"]
  return source, transform_names


def test_complete_transform_chain_compiles() -> None:
  source, _ = _transformed_app_source()
  compile(source, str(ROOT / "app_core.py"), "exec")


def test_global_publication_css_is_not_an_f_string() -> None:
  source, names = _transformed_app_source()
  assert "app_css_literal_guard_transform.py" in names
  broken = re.search(
    r"st\.markdown\(\s*(?:f|fr|rf)(?:\"\"\"|''')\s*<style>\s*"
    r"/\* Publication-style interface",
    source,
    flags=re.IGNORECASE,
  )
  assert broken is None
  assert re.search(
    r"st\.markdown\(\s*(?:\"\"\"|''')\s*<style>\s*"
    r"/\* Publication-style interface",
    source,
    flags=re.IGNORECASE,
  )


def test_title_and_abstract_localization_survive_full_chain() -> None:
  source, _ = _transformed_app_source()
  assert "DEFAULT_ARTICLE_TITLE_EN" in source
  assert "DEFAULT_ARTICLE_TITLE_PT" in source
  assert "DEFAULT_ARTICLE_ABSTRACT_EN" in source
  assert "DEFAULT_ARTICLE_ABSTRACT_PT" in source
  assert '<h1>{html_lib.escape(str(title))}</h1>' in source
  assert "171 de 195 marcadores biogeoquímicos" in source
  assert "132 marcadores associados ao ferro" in source
  assert "50 genomas montados a partir de metagenomas" in source
