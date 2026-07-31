from __future__ import annotations

"""Route exact Figure 2/3 app views to freshly generated corrected SVGs."""

MARKER = "CANGAMETAG_EXACT_FIGURE2_3_GENERATED_SOURCE_V1 = 1"

if MARKER not in source:
  source = source.replace(
    "from src.article_exact_taxonomy_phylum import (\n"
    "  exact_article_phylum_interactive,\n"
    "  materialize_exact_article_phylum_static,\n"
    ")\n",
    "from src.article_exact_taxonomy_phylum_generated import (\n"
    "  exact_article_phylum_interactive,\n"
    "  materialize_exact_article_phylum_static,\n"
    ")\n",
    1,
  )
  source += f"\n\n{MARKER}\n"
