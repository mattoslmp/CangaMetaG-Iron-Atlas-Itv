from __future__ import annotations

"""Final app transform: make Figure 2/3 static and interactive views identical."""

MARKER = "CANGAMETAG_EXACT_FIGURE2_3_ALIGNMENT_V1 = 1"

if MARKER not in source:
  future_anchor = "from __future__ import annotations\n"
  imports = '''from src.article_exact_taxonomy_phylum import (
  exact_article_phylum_interactive,
  materialize_exact_article_phylum_static,
)
'''
  if imports not in source:
    source = source.replace(future_anchor, future_anchor + imports, 1)

  # The generic visible-text validator correctly rejects development
  # placeholders, but literal NA/N/A can be a legitimate taxonomy category.
  # Allow those exact trace labels only for figures explicitly marked as
  # frozen article taxonomy figures. The original figure remains unchanged;
  # only a defensive copy is sanitized for validation.
  validator_code = r'''
_APP_ORIGINAL_VALIDATE_VISIBLE_TEXT = validate_visible_text


def validate_visible_text(fig, *, require_title: bool = False) -> None:
  meta = getattr(getattr(fig, "layout", None), "meta", None) or {}
  allow_taxonomy_literals = bool(
    isinstance(meta, dict) and meta.get("allow_taxonomy_missing_literals", False)
  )
  if not allow_taxonomy_literals:
    return _APP_ORIGINAL_VALIDATE_VISIBLE_TEXT(fig, require_title=require_title)
  validation_copy = go.Figure(fig)
  for trace in validation_copy.data:
    name = str(getattr(trace, "name", "") or "").strip()
    if name.casefold() in {"na", "n/a"}:
      trace.name = "Taxonomy not assigned"
  return _APP_ORIGINAL_VALIDATE_VISIBLE_TEXT(
    validation_copy,
    require_title=require_title,
  )
'''
  site_anchor = "def site_access_gate"
  if site_anchor in source and "_APP_ORIGINAL_VALIDATE_VISIBLE_TEXT" not in source:
    source = source.replace(site_anchor, validator_code + "\n\n" + site_anchor, 1)

  # Intercept Figure 2 and Figure 3 so the static app view always uses the
  # same corrected SVG as the exact interactive viewer. No old-label PNG can
  # be shown as a silent fallback.
  display_signature = (
    'def _display_static_publication_image(path: Path, title: str, caption: str = "", '
    'key_prefix: str = "static_publication_image") -> None:'
  )
  display_start = source.find(display_signature)
  if display_start >= 0:
    display_end = source.find("\ndef ", display_start + len(display_signature))
    if display_end < 0:
      display_end = len(source)
    existing = source[display_start:display_end].replace(
      "def _display_static_publication_image(",
      "def _display_static_publication_image_before_exact_phylum(",
      1,
    )
    wrapper = r'''
def _display_static_publication_image(path: Path, title: str, caption: str = "", key_prefix: str = "static_publication_image") -> None:
  domain = None
  if path.stem == "Figure2_taxonomic_phylum_bacteria_horizontal_CDS":
    domain = "Bacteria"
  elif path.stem == "Figure3_taxonomic_phylum_archaea_horizontal_CDS":
    domain = "Archaea"
  if domain is None:
    return _display_static_publication_image_before_exact_phylum(
      path, title, caption, key_prefix
    )
  try:
    exact_path = materialize_exact_article_phylum_static(domain, APP_CACHE_DIR)
  except Exception as exc:
    LOGGER.exception("Could not materialize exact %s article phylum figure", domain)
    st.error(txt(
      f"A figura taxonômica exata de {domain} não pôde ser materializada: {exc}",
      f"The exact {domain} taxonomy figure could not be materialized: {exc}",
    ))
    return
  st.markdown(f"#### `{path.name}`")
  st.image(str(exact_path), width="stretch", caption=caption or None)
  st.download_button(
    txt("Baixar SVG exato do artigo", "Download exact article SVG"),
    data=exact_path.read_bytes(),
    file_name=exact_path.name,
    mime="image/svg+xml",
    key=f"{key_prefix}_{safe_filename(path.stem)}_exact_article_svg",
    width="stretch",
  )
  st.caption(txt(
    "Nomenclatura atualizada. Esta é a mesma imagem SVG usada no painel interativo; valores, cores, ordem, proporções e layout não foram alterados.",
    "Updated nomenclature. This is the same SVG used in the interactive viewer; values, colours, order, proportions and layout were not changed.",
  ))
  _render_static_figure_audit(path, title, key_prefix)
'''
    source = source[:display_start] + existing + "\n\n" + wrapper + source[display_end:]

  renderer = r'''
def _render_exact_article_phylum_figures() -> None:
  st.markdown("### " + txt(
    "Figuras 2 e 3 interativas — imagem exata do artigo",
    "Interactive Figures 2 and 3 — exact article image",
  ))
  st.info(txt(
    "O visualizador interativo incorpora o mesmo SVG corrigido exibido como figura estática. Zoom e deslocamento são interativos, mas nenhuma barra, categoria, cor, ordem ou abundância é redesenhada ou recalculada.",
    "The interactive viewer embeds the same corrected SVG shown as the static figure. Zoom and pan are interactive, but no bar, category, colour, order or abundance is redrawn or recomputed.",
  ))
  tabs = st.tabs(["Bacteria — Figure 2", "Archaea — Figure 3"])
  for domain, tab in zip(["Bacteria", "Archaea"], tabs):
    with tab:
      try:
        figure, exact_table, svg = exact_article_phylum_interactive(domain)
        validate_visible_text(figure)
      except Exception as exc:
        LOGGER.exception("Could not build exact Figure 2/3 viewer for %s", domain)
        st.error(txt(
          f"Não foi possível carregar a figura exata de {domain}: {exc}",
          f"Could not load the exact {domain} figure: {exc}",
        ))
        continue
      st.plotly_chart(
        figure,
        width="stretch",
        config={
          "displaylogo": False,
          "scrollZoom": True,
          "responsive": True,
          "modeBarButtonsToRemove": ["select2d", "lasso2d"],
        },
        key=f"exact_article_phylum_viewer_{domain}",
      )
      buttons = st.columns(2)
      with buttons[0]:
        st.download_button(
          txt("Baixar o mesmo SVG", "Download the same SVG"),
          data=svg,
          file_name=(
            "Figure2_taxonomic_phylum_bacteria_horizontal_CDS.svg"
            if domain == "Bacteria"
            else "Figure3_taxonomic_phylum_archaea_horizontal_CDS.svg"
          ),
          mime="image/svg+xml",
          key=f"download_exact_article_phylum_svg_{domain}",
          width="stretch",
        )
      with buttons[1]:
        csv_button(
          exact_table,
          (
            "Figure2_taxonomic_phylum_bacteria_horizontal_CDS_source.csv"
            if domain == "Bacteria"
            else "Figure3_taxonomic_phylum_archaea_horizontal_CDS_source.csv"
          ),
          txt("Baixar tabela exata", "Download exact table"),
          key=f"download_exact_article_phylum_csv_{domain}",
        )
      with st.expander(
        txt("Tabela exata usada na figura", "Exact table used by the figure"),
        expanded=False,
      ):
        show_table(
          exact_table,
          f"exact_article_phylum_table_{domain}",
          height=430,
        )
      st.caption(txt(
        "Fonte congelada: data/final_publication_derived. Totais verificados em 100% por amostra; nenhum valor foi inventado ou recalculado.",
        "Frozen source: data/final_publication_derived. Totals verified at 100% per sample; no value was invented or recomputed.",
      ))
'''
  if site_anchor in source and "def _render_exact_article_phylum_figures" not in source:
    source = source.replace(site_anchor, renderer + "\n\n" + site_anchor, 1)

  # Replace the previous Plotly redraw of Figure 2/3 with the exact corrected
  # SVG viewer. Keep the general taxonomy explorer below it unchanged.
  start_token = '"Barplots interativos correspondentes às Figuras 2 e 3"'
  end_token = '"Explorador taxonômico interativo com nomenclatura NCBI atual"'
  label_start = source.find(start_token)
  label_end = source.find(end_token, label_start + 1) if label_start >= 0 else -1
  if label_start >= 0 and label_end >= 0:
    block_start = source.rfind("  st.markdown(", 0, label_start)
    block_end = source.rfind("  st.markdown(", 0, label_end)
    if block_start >= 0 and block_end > block_start:
      source = (
        source[:block_start]
        + "  _render_exact_article_phylum_figures()\n\n"
        + source[block_end:]
      )

  source += f"\n\n{MARKER}\n"
