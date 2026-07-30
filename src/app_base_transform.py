from __future__ import annotations


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


# Public-facing title for the ST8 source/reference module.
source = source.replace(
  'txt("Referências bibliográficas e links dos estudos ST8", "ST8 study references and links")',
  'txt("Metagenômica do ferro — fontes de dados, links e referências", "Iron Metagenomics — Data Source, Links & References")',
)
source = source.replace(
  'txt("Referências dos estudos ST8", "ST8 study references")',
  'txt("Metagenômica do ferro — fontes de dados, links e referências", "Iron Metagenomics — Data Source, Links & References")',
)


# Remove the empty bin-classification/ENA tab and blank terminal rows. Real ENA
# aliases and accessions in the quality table remain unchanged.
source = source.replace(
  '    ("bin.classification", txt("Classificação taxonômica dos bins e acessos ENA", "Bin taxonomic classification and ENA accessions")),\n',
  '',
  1,
)
source = source.replace(
  'st.markdown("#### " + txt("Classificação taxonômica e acessos ENA dos MAGs", "MAG taxonomic classification and ENA accessions"))',
  'st.markdown("#### " + txt("Classificação taxonômica dos MAGs", "MAG taxonomic classification"))',
  1,
)
classification_load_anchor = '      df = load_mag_classification_sheet(sheet_name)\n'
classification_load_replacement = '''      df = load_mag_classification_sheet(sheet_name)
      if not df.empty:
        df = df.replace(r"^\\s*$", np.nan, regex=True).dropna(how="all").dropna(axis=1, how="all")
        row_text = df.fillna("").astype(str).agg(" ".join, axis=1).str.strip().str.casefold()
        df = df.loc[~row_text.isin({"bin taxonomic classification", "ena accessions"})].copy()
'''
source = replace_once(
  source,
  classification_load_anchor,
  classification_load_replacement,
  "empty MAG classification row removal",
)


# Sampling map in the Taxonomy page, directly after the metadata table.
taxonomy_anchor = '''    csv_button(meta, "taxonomy_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))

  st.markdown("### " + txt("Figuras taxonômicas finais usadas no artigo", "Final taxonomy figures used in the article"))'''
taxonomy_replacement = '''    csv_button(meta, "taxonomy_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))

  if {"lat", "lon"}.issubset(meta.columns):
    show_high_quality_sample_map(meta, key="taxonomy_sampling_map_after_metadata_v8")

  st.markdown("### " + txt("Figuras taxonômicas finais usadas no artigo", "Final taxonomy figures used in the article"))'''
source = replace_once(source, taxonomy_anchor, taxonomy_replacement, "Taxonomy sampling map")


