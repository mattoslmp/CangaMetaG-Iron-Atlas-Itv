from __future__ import annotations

MARKER = "CANGAMETAG_OFFICIAL_ORDINATION_METHOD_TEXT_V1 = 1"

if MARKER not in source:
  source = source.replace(
    'audit_script="src/article_frozen_taxonomy_panels.py; src/article_inference_statistics.py",',
    'audit_script="src/article_frozen_taxonomy_panels.py; src/article_official_ordination_statistics.py",',
  )
  source = source.replace(
    '"Método: distância Bray–Curtis sobre abundâncias relativas de gêneros. PERMANOVA com 999 permutações testou diferenças entre lagoas e estações; PERMDISP/betadisper testou homogeneidade da dispersão. " + inference_summary(beta_tests),',
    '"Método: proporções relativas dos gêneros transformadas pela raiz quadrada, seguidas de distância Bray–Curtis. PERMANOVA com 999 permutações testou diferenças entre lagoas, estações e combinações lagoa–estação; PERMDISP/betadisper testou homogeneidade da dispersão. " + inference_summary(beta_tests),',
  )
  source = source.replace(
    '"Method: Bray-Curtis distance on genus relative abundances. PERMANOVA with 999 permutations tested differences among lakes and seasons; PERMDISP/betadisper tested homogeneity of dispersion. " + inference_summary(beta_tests),',
    '"Method: square-root-transformed genus relative proportions followed by Bray-Curtis distances. PERMANOVA with 999 permutations tested differences among lakes, seasons and lake–season combinations; PERMDISP/betadisper tested homogeneity of dispersion. " + inference_summary(beta_tests),',
  )
  source += f"\n\n{MARKER}\n"
