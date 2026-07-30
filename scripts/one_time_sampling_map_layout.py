from __future__ import annotations

from pathlib import Path


APP_PATH = Path("app.py")
VALIDATE_RDA_PATH = Path(".github/workflows/validate-rda.yml")

ORIGINAL_VALIDATE_RDA = """name: Validate article RDA

on:
  push:
    branches: [main]
  pull_request:

jobs:
  rda:
    runs-on: ubuntu-latest
    steps:
      - name: Check out repository
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install compact RDA dependencies
        run: |
          python -m pip install --upgrade pip
          python -m pip install numpy pandas

      - name: Reproduce the article RDA from derived source matrices
        run: python scripts/run_article_rda_from_derived.py

      - name: Verify article statistics and trace-metal predictors
        run: |
          python - <<'PY'
          import json
          import subprocess

          output = subprocess.check_output(
            ['python', 'scripts/run_article_rda_from_derived.py'],
            text=True,
          )
          result = json.loads(output)
          expected_predictors = ['Fe2O3', 'SiO2', 'Al2O3', 'TOT/S', 'Cu', 'Pb']
          assert result['n_positions'] == 10
          assert result['predictors'] == expected_predictors
          assert abs(result['constrained_R2'] - 0.6605827831733045) < 1e-12
          assert abs(result['pseudo_F'] - 0.9731132518103737) < 1e-12
          assert abs(result['permutation_P'] - 0.534) < 1e-12
          print('Article RDA validation: PASS')
          PY
"""


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if new in text:
    return text
  if old not in text:
    raise RuntimeError(f"Could not find the {label} anchor in app.py")
  return text.replace(old, new, 1)


def update_app() -> None:
  text = APP_PATH.read_text(encoding="utf-8")

  text = replace_once(
    text,
    '  with st.expander(txt("Amostras, datas, coordenadas e environment_feature", "Samples, dates, coordinates and environment_feature"), expanded=True):',
    '  with st.expander(txt("Amostras, datas e coordenadas geográficas", "Samples, collection dates and geographic coordinates"), expanded=True):',
    "active taxonomy metadata title",
  )

  taxonomy_anchor = '''    csv_button(meta, "taxonomy_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))

  st.markdown("### " + txt("Figuras taxonômicas finais usadas no artigo", "Final taxonomy figures used in the article"))'''
  taxonomy_replacement = '''    csv_button(meta, "taxonomy_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))

  # App-only interactive map placement requested for the active taxonomy page.
  # Canonical Figure 1 files in outputs/final_publication_figures are not modified.
  if {"lat", "lon"}.issubset(meta.columns):
    show_high_quality_sample_map(meta, key="taxonomy_active_sampling_map")
  else:
    st.warning(txt(
      "As colunas de latitude e longitude não estão disponíveis para o mapa interativo.",
      "Latitude and longitude columns are not available for the interactive sampling map."
    ))

  st.markdown("### " + txt("Figuras taxonômicas finais usadas no artigo", "Final taxonomy figures used in the article"))'''
  if "taxonomy_active_sampling_map" not in text:
    text = replace_once(
      text,
      taxonomy_anchor,
      taxonomy_replacement,
      "active taxonomy interactive-map insertion",
    )

  overview_anchor = '''    csv_button(meta, "article_sample_dates_coordinates.csv", txt("Baixar datas/coordenadas", "Download dates/coordinates"))

  if st.session_state.get("admin_authenticated", False):'''
  overview_replacement = '''    csv_button(meta, "article_sample_dates_coordinates.csv", txt("Baixar datas/coordenadas", "Download dates/coordinates"))

  # Display the canonical static Figure 1 after the study-sample section.
  # The interactive Google/satellite map remains outside the Article Atlas page.
  st.markdown("### " + txt("Área de estudo e desenho amostral", "Study area and sampling design"))
  figure1_path = BASE_DIR / "outputs" / "final_publication_figures" / "Figure1_sampling_map.png"
  figure1_caption = txt(
    "Área de estudo e desenho amostral. Localização das lagoas lateríticas amazônicas Amendoim, Violão, Três Irmãs e Três Irmãs Adjacent. O estudo inclui 20 metagenomas de sedimento, compreendendo 10 amostras do período seco e 10 do período chuvoso.",
    "Study area and sampling design. Location of the Amazonian lateritic lakes Amendoim, Violão, Três Irmãs and Três Irmãs Adjacent. The study includes 20 sediment metagenomes, comprising 10 dry-season and 10 rainy-season samples."
  )
  if figure1_path.exists():
    st.image(str(figure1_path), width="stretch", caption=figure1_caption)
  else:
    st.warning(txt(
      "A Figura 1 do mapa amostral não foi encontrada no diretório canônico de figuras finais.",
      "Figure 1 sampling map was not found in the canonical final-figures directory."
    ))

  if st.session_state.get("admin_authenticated", False):'''
  if "figure1_caption = txt(" not in text:
    text = replace_once(
      text,
      overview_anchor,
      overview_replacement,
      "Article Atlas static Figure 1 insertion",
    )

  compile(text, str(APP_PATH), "exec")
  APP_PATH.write_text(text, encoding="utf-8")


def restore_ci() -> None:
  VALIDATE_RDA_PATH.write_text(ORIGINAL_VALIDATE_RDA, encoding="utf-8")


def main() -> None:
  update_app()
  restore_ci()
  print("Sampling-map layout patch applied and CI workflow restored.")


if __name__ == "__main__":
  main()
