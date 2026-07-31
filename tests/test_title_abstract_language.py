from __future__ import annotations

from pathlib import Path
import runpy


ROOT = Path(__file__).resolve().parents[1]
TRANSFORM = ROOT / "src" / "app_title_abstract_language_transform.py"


def _synthetic_source() -> str:
  return '''from __future__ import annotations

DEFAULT_ARTICLE_TITLE = 'Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling'
DEFAULT_ARTICLE_ABSTRACT = 'Amazonian lateritic lakes developed on ferruginous canga are seasonally variable, metal-rich systems whose sediment microbiomes remain poorly characterized.'

def article_field(key: str, default: str) -> str:
  return default

APP_TITLE = 'Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling'
st.set_page_config(page_title=APP_TITLE, page_icon="🧬", layout="wide")

def overview():
  title = article_field("title", DEFAULT_ARTICLE_TITLE)
  abstract = article_field("abstract", DEFAULT_ARTICLE_ABSTRACT)
  return title, abstract

page_handler = page_handlers.get(selected_page)
'''


def test_transform_localizes_page_title_article_title_and_abstract() -> None:
  transformed = runpy.run_path(
    str(TRANSFORM),
    init_globals={"source": _synthetic_source()},
  )["source"]
  compile(transformed, "synthetic_title_abstract_language.py", "exec")

  assert "DEFAULT_ARTICLE_TITLE_EN" in transformed
  assert "DEFAULT_ARTICLE_TITLE_PT" in transformed
  assert "DEFAULT_ARTICLE_ABSTRACT_EN" in transformed
  assert "DEFAULT_ARTICLE_ABSTRACT_PT" in transformed
  assert "Sedimentos de lagoas lateríticas amazônicas ricas em ferro" in transformed
  assert "As lagoas lateríticas amazônicas desenvolvidas sobre canga ferruginosa" in transformed
  assert "st.set_page_config(page_title=APP_TITLE" in transformed
  assert '_localized_article_text("title", DEFAULT_ARTICLE_TITLE_EN, DEFAULT_ARTICLE_TITLE_PT)' in transformed
  assert '_localized_article_text("abstract", DEFAULT_ARTICLE_ABSTRACT_EN, DEFAULT_ARTICLE_ABSTRACT_PT)' in transformed


def test_portuguese_abstract_preserves_scientific_results() -> None:
  transformed = runpy.run_path(
    str(TRANSFORM),
    init_globals={"source": _synthetic_source()},
  )["source"]

  for expected in (
    "171 de 195",
    "132 marcadores",
    "50 genomas",
    "NMDS",
    "RDA",
    "Acidobacteria",
    "Methanoperedens",
  ):
    assert expected in transformed


def test_custom_admin_text_is_not_overwritten() -> None:
  transform_text = TRANSFORM.read_text(encoding="utf-8")
  assert "if current in (None, \"\", english_default, portuguese_default):" in transform_text
  assert "return str(current)" in transform_text


def test_app_loads_title_abstract_layer_before_final_renderer() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  language = app.index("app_complete_plotly_language_transform.py")
  title_abstract = app.index("app_title_abstract_language_transform.py")
  renderer = app.index("app_static_figure_renderer_recovery_transform.py")
  assert language < title_abstract < renderer
