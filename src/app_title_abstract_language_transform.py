from __future__ import annotations

"""Synchronize the public title and abstract with the selected UI language.

This transform deliberately edits only single assignment lines and explicit
article-field calls. It never uses a DOTALL expression and never rewrites CSS or
HTML string delimiters. Scientific claims, numbers, taxonomic names and results
remain identical between languages. Custom administrator text is preserved.
"""

import re


MARKER = "CANGAMETAG_TITLE_ABSTRACT_LANGUAGE_V2 = 1"

TITLE_EN = (
  "Iron-rich Amazonian lateritic lake sediments harbor diverse microbial "
  "communities with biogeochemical potential relevant to carbon and methane cycling"
)
TITLE_PT = (
  "Sedimentos de lagoas lateríticas amazônicas ricas em ferro abrigam "
  "comunidades microbianas diversas com potencial biogeoquímico relevante "
  "para os ciclos do carbono e do metano"
)

ABSTRACT_EN = (
  "Amazonian lateritic lakes developed on ferruginous canga are seasonally variable, "
  "metal-rich systems whose sediment microbiomes remain poorly characterized. We used "
  "shotgun metagenomics to investigate microbial communities in sediments from Amendoim, "
  "Violão, Três Irmãs and Três Irmãs Adjacent lakes during dry and rainy periods. "
  "Coding-sequence taxonomic profiles revealed diverse bacterial and archaeal assemblages "
  "and a large unclassified fraction, indicating substantial underexplored diversity. "
  "Lake- and season-associated contrasts involved methanogenic, ammonia-oxidizing and "
  "anaerobic sediment lineages. Non-metric multidimensional scaling showed partial community "
  "overlap, whereas an exploratory, non-significant redundancy analysis placed genus-level "
  "variation along loss-on-ignition, aluminium, silica, sulfur and trace-metal gradients. "
  "Functional reconstruction identified genetic potential for carbon fixation, methane "
  "metabolism, nitrogen and sulfur cycling, photosynthesis, anaerobic respiration and iron "
  "metabolism. A curated Kyoto Encyclopedia of Genes and Genomes orthology framework detected "
  "171 of 195 biogeochemical markers and 132 iron-associated markers. Descriptive cross-study "
  "contrasts distinguished Amazonian canga-lake profiles from external iron-rich records, but "
  "were not treated as inferential tests. We recovered 50 non-redundant metagenome-assembled "
  "genomes spanning medium- to high-quality bins, including lineages related to Acidobacteria, "
  "Dehalococcoidia, Nitrospirales, Burkholderiales, Bathyarchaeia, Thermoplasmatota and "
  "Methanoperedens. These results establish a genome-resolved iron metagenomic atlas for "
  "tropical lateritic-lake sediments and a basis for testing how seasonal hydrology and "
  "ferruginous geochemistry shape microbial biogeochemical functions."
)

ABSTRACT_PT = (
  "As lagoas lateríticas amazônicas desenvolvidas sobre canga ferruginosa são sistemas ricos "
  "em metais e sazonalmente variáveis, cujos microbiomas dos sedimentos permanecem pouco "
  "caracterizados. Utilizamos metagenômica shotgun para investigar as comunidades microbianas "
  "dos sedimentos das lagoas Amendoim, Violão, Três Irmãs e Três Irmãs Adjacente durante os "
  "períodos seco e chuvoso. Os perfis taxonômicos baseados em sequências codificadoras "
  "revelaram assembleias bacterianas e arqueanas diversas e uma grande fração não classificada, "
  "indicando diversidade substancial ainda pouco explorada. Os contrastes associados às lagoas "
  "e às estações envolveram linhagens metanogênicas, oxidantes de amônia e anaeróbias dos "
  "sedimentos. O escalonamento multidimensional não métrico mostrou sobreposição parcial das "
  "comunidades, enquanto uma análise de redundância exploratória e não significativa posicionou "
  "a variação em nível de gênero ao longo de gradientes de perda ao fogo, alumínio, sílica, "
  "enxofre e metais-traço. A reconstrução funcional identificou potencial genético para fixação "
  "de carbono, metabolismo do metano, ciclos do nitrogênio e do enxofre, fotossíntese, respiração "
  "anaeróbia e metabolismo do ferro. Uma estrutura curada de ortologias da Kyoto Encyclopedia "
  "of Genes and Genomes detectou 171 de 195 marcadores biogeoquímicos e 132 marcadores associados "
  "ao ferro. Contrastes descritivos entre estudos distinguiram os perfis das lagoas de canga "
  "amazônicas de registros externos de ambientes ricos em ferro, mas não foram tratados como "
  "testes inferenciais. Recuperamos 50 genomas montados a partir de metagenomas, não redundantes, "
  "abrangendo bins de qualidade média a alta, incluindo linhagens relacionadas a Acidobacteria, "
  "Dehalococcoidia, Nitrospirales, Burkholderiales, Bathyarchaeia, Thermoplasmatota e "
  "Methanoperedens. Esses resultados estabelecem um atlas metagenômico do ferro, resolvido em "
  "nível genômico, para sedimentos de lagoas lateríticas tropicais e uma base para testar como "
  "a hidrologia sazonal e a geoquímica ferruginosa moldam as funções biogeoquímicas microbianas."
)


if MARKER not in source:
  title_assignment = (
    f"DEFAULT_ARTICLE_TITLE_EN = {TITLE_EN!r}\n"
    f"DEFAULT_ARTICLE_TITLE_PT = {TITLE_PT!r}\n"
    "DEFAULT_ARTICLE_TITLE = (\n"
    "  DEFAULT_ARTICLE_TITLE_PT if IS_PT else DEFAULT_ARTICLE_TITLE_EN\n"
    ")"
  )
  source, title_count = re.subn(
    r"^DEFAULT_ARTICLE_TITLE\s*=\s*.*$",
    title_assignment,
    source,
    count=1,
    flags=re.MULTILINE,
  )

  abstract_assignment = (
    f"DEFAULT_ARTICLE_ABSTRACT_EN = {ABSTRACT_EN!r}\n"
    f"DEFAULT_ARTICLE_ABSTRACT_PT = {ABSTRACT_PT!r}\n"
    "DEFAULT_ARTICLE_ABSTRACT = (\n"
    "  DEFAULT_ARTICLE_ABSTRACT_PT if IS_PT else DEFAULT_ARTICLE_ABSTRACT_EN\n"
    ")"
  )
  source, abstract_count = re.subn(
    r"^DEFAULT_ARTICLE_ABSTRACT\s*=\s*.*$",
    abstract_assignment,
    source,
    count=1,
    flags=re.MULTILINE,
  )

  anchor = "page_handler = page_handlers.get(selected_page)"
  layer = r'''
def _localized_article_text(
  key: str,
  english_default: str,
  portuguese_default: str,
) -> str:
  """Switch public defaults with language while preserving custom edits."""
  session_key = f"article_{key}"
  target = portuguese_default if IS_PT else english_default
  current = st.session_state.get(session_key)
  if current in (None, "", english_default, portuguese_default):
    st.session_state[session_key] = target
    return target
  return str(current)
'''
  if anchor in source:
    source = source.replace(anchor, layer + "\n\n" + anchor, 1)

  replacements = {
    'article_field("title", DEFAULT_ARTICLE_TITLE)': (
      '_localized_article_text("title", DEFAULT_ARTICLE_TITLE_EN, DEFAULT_ARTICLE_TITLE_PT)'
    ),
    "article_field('title', DEFAULT_ARTICLE_TITLE)": (
      "_localized_article_text('title', DEFAULT_ARTICLE_TITLE_EN, DEFAULT_ARTICLE_TITLE_PT)"
    ),
    'article_field("abstract", DEFAULT_ARTICLE_ABSTRACT)': (
      '_localized_article_text("abstract", DEFAULT_ARTICLE_ABSTRACT_EN, DEFAULT_ARTICLE_ABSTRACT_PT)'
    ),
    "article_field('abstract', DEFAULT_ARTICLE_ABSTRACT)": (
      "_localized_article_text('abstract', DEFAULT_ARTICLE_ABSTRACT_EN, DEFAULT_ARTICLE_ABSTRACT_PT)"
    ),
    "<h1>{APP_TITLE}</h1>": "<h1>{html_lib.escape(str(title))}</h1>",
  }
  for old, new in replacements.items():
    source = source.replace(old, new)

  if title_count != 1 or abstract_count != 1:
    raise RuntimeError(
      "Could not install title/abstract localization safely: "
      f"title_count={title_count}, abstract_count={abstract_count}"
    )

  source += f"\n\n{MARKER}\n"
