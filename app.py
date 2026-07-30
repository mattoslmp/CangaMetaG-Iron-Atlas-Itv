from __future__ import annotations

"""Streamlit entry point with two explicit layout insertions.

The complete application remains in ``app_core.py``.  This loader changes only
where the sampling maps are rendered; it does not monkeypatch Streamlit and does
not remove or replace any taxonomy analysis panel.
"""

from pathlib import Path


CORE_PATH = Path(__file__).with_name("app_core.py")
source = CORE_PATH.read_text(encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


taxonomy_anchor = '''    csv_button(meta, "taxonomy_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))

  st.markdown("### " + txt("Figuras taxonômicas finais usadas no artigo", "Final taxonomy figures used in the article"))'''

taxonomy_replacement = '''    csv_button(meta, "taxonomy_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))

  # Sampling maps are rendered once, after the metadata expander has closed.
  if {"lat", "lon"}.issubset(meta.columns):
    show_high_quality_sample_map(meta, key="taxonomy_sampling_map_after_metadata_v5")

  st.markdown("### " + txt("Figuras taxonômicas finais usadas no artigo", "Final taxonomy figures used in the article"))'''

source = replace_once(source, taxonomy_anchor, taxonomy_replacement, "Taxonomy sampling map")

overview_anchor = '''    csv_button(meta, "article_sample_dates_coordinates.csv", txt("Baixar datas/coordenadas", "Download dates/coordinates"))

  if st.session_state.get("admin_authenticated", False):'''

overview_replacement = '''    csv_button(meta, "article_sample_dates_coordinates.csv", txt("Baixar datas/coordenadas", "Download dates/coordinates"))

  # Canonical static Figure 1 follows the study-sample table on Article Atlas.
  figure1_sampling_path = BASE_DIR / "outputs" / "final_publication_figures" / "Figure1_sampling_map.png"
  st.markdown("### " + txt("Área de estudo e desenho amostral", "Study area and sampling design"))
  if figure1_sampling_path.exists():
    st.image(str(figure1_sampling_path), width="stretch")
    st.caption(txt(
      "Área de estudo e desenho amostral. Localização das lagoas lateríticas amazônicas Amendoim, Violão, Três Irmãs e Três Irmãs Adjacent. O estudo inclui 20 metagenomas de sedimento, compreendendo 10 amostras do período seco e 10 do período chuvoso.",
      "Study area and sampling design. Location of the Amazonian lateritic lakes Amendoim, Violão, Três Irmãs and Três Irmãs Adjacent. The study includes 20 sediment metagenomes, comprising 10 dry-season and 10 rainy-season samples.",
    ))
  else:
    st.warning(txt(
      "A Figura 1 do mapa amostral não foi encontrada no diretório canônico de figuras finais.",
      "Figure 1 sampling map was not found in the canonical final-figures directory.",
    ))

  if st.session_state.get("admin_authenticated", False):'''

source = replace_once(source, overview_anchor, overview_replacement, "Article Atlas Figure 1")

# Fail before execution if an edit ever introduces invalid Python.
code = compile(source, str(CORE_PATH), "exec")
exec(code, globals(), globals())
