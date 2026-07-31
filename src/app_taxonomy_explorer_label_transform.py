from __future__ import annotations

"""Keep taxonomy explorer labels concise and scientifically neutral."""

MARKER = "CANGAMETAG_TAXONOMY_EXPLORER_LABEL_V1 = 1"

if MARKER not in source:
  replacements = {
    "Explorador taxonômico interativo com nomenclatura NCBI atual": (
      "Explorador taxonômico interativo"
    ),
    "Interactive taxonomy explorer with current NCBI nomenclature": (
      "Interactive taxonomy explorer"
    ),
    (
      "As figuras estáticas e os painéis interativos usam os mesmos arquivos "
      "`data/resultado.cds.otu.tab` e `data/resultado.cds.tax.tab`. A classificação "
      "é separada por domínio antes da agregação; a nomenclatura atual do NCBI "
      "altera somente os rótulos de Phylum, Order, Family e Genus, nunca as contagens."
    ): (
      "As figuras estáticas e os painéis interativos usam os mesmos arquivos "
      "`data/resultado.cds.otu.tab` e `data/resultado.cds.tax.tab`. A classificação "
      "é separada por domínio antes da agregação, sem alterar as contagens."
    ),
    (
      "Static figures and interactive panels use the same "
      "`data/resultado.cds.otu.tab` and `data/resultado.cds.tax.tab` files. "
      "Classification is separated by domain before aggregation; current NCBI "
      "nomenclature changes Phylum, Order, Family and Genus labels only, never counts."
    ): (
      "Static figures and interactive panels use the same "
      "`data/resultado.cds.otu.tab` and `data/resultado.cds.tax.tab` files. "
      "Classification is separated by domain before aggregation without changing counts."
    ),
  }
  for old_text, new_text in replacements.items():
    source = source.replace(old_text, new_text)
  source += f"\n\n{MARKER}\n"
