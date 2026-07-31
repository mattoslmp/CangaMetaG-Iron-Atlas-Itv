from __future__ import annotations

"""Install a final, bilingual and self-contained static-figure renderer."""


MARKER = "CANGAMETAG_STATIC_FIGURE_RENDERER_RECOVERY_V3 = 1"

if MARKER not in source:
  future_anchor = "from __future__ import annotations\n"
  imports = '''from src.article_exact_taxonomy_phylum_generated import materialize_exact_article_phylum_static as final_materialize_exact_article_phylum_static
from src.article_frozen_taxonomy_static_bilingual import materialize_frozen_article_static_bilingual as final_materialize_frozen_article_static
from src.figure_language_localization import translate_figure_text as final_translate_figure_text
'''
  if imports not in source and future_anchor in source:
    source = source.replace(future_anchor, future_anchor + imports, 1)

  anchor = "page_handler = page_handlers.get(selected_page)"
  replacement = r'''
def _final_static_publication_path(path: Path) -> Path | None:
  """Resolve the final generated display asset in the selected language."""
  language = "pt" if IS_PT else "en"
  try:
    if path.stem == "Figure2_taxonomic_phylum_bacteria_horizontal_CDS":
      return final_materialize_exact_article_phylum_static(
        "Bacteria",
        APP_CACHE_DIR,
        language=language,
      )
    if path.stem == "Figure3_taxonomic_phylum_archaea_horizontal_CDS":
      return final_materialize_exact_article_phylum_static(
        "Archaea",
        APP_CACHE_DIR,
        language=language,
      )
    if path.stem == "Figure4_taxonomic_bacteria_genus_profiles":
      return final_materialize_frozen_article_static(
        "Bacteria",
        APP_CACHE_DIR,
        language=language,
      )
    if path.stem == "Figure5_taxonomic_archaea_genus_profiles":
      return final_materialize_frozen_article_static(
        "Archaea",
        APP_CACHE_DIR,
        language=language,
      )
    generator = globals().get("materialize_corrected_taxonomy_static")
    if callable(generator):
      corrected = generator(path.name, APP_CACHE_DIR)
      if corrected is not None:
        return Path(corrected)
  except Exception as exc:
    LOGGER.warning("Could not materialize corrected static figure %s: %s", path, exc)
  return path if path.exists() else None


def _display_static_publication_image(
  path: Path,
  title: str,
  caption: str = "",
  key_prefix: str = "static_publication_image",
) -> None:
  """Render one static figure and its retractable scientific-data panel."""
  requested = Path(path)
  display_path = _final_static_publication_path(requested)
  localized_title = final_translate_figure_text(title, "pt" if IS_PT else "en")
  localized_caption = final_translate_figure_text(caption, "pt" if IS_PT else "en")
  st.markdown(f"#### {localized_title}")
  if display_path is None or not display_path.exists():
    st.warning(txt(
      f"Figura indisponível: {requested.name}",
      f"Figure unavailable: {requested.name}",
    ))
    return

  st.image(str(display_path), width="stretch", caption=localized_caption or None)

  candidates: list[Path] = []
  raw_candidates = [display_path] if IS_PT else [
    display_path,
    requested,
    requested.with_suffix(".png"),
    requested.with_suffix(".svg"),
    requested.with_suffix(".pdf"),
    requested.with_suffix(".tiff"),
  ]
  for candidate in raw_candidates:
    candidate = Path(candidate)
    if candidate.exists() and candidate.is_file() and candidate not in candidates:
      candidates.append(candidate)

  mime_by_suffix = {
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".pdf": "application/pdf",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
  }
  if candidates:
    columns = st.columns(min(4, len(candidates)))
    for index, candidate in enumerate(candidates):
      with columns[index % len(columns)]:
        suffix = candidate.suffix.lower()
        label = suffix.lstrip(".").upper() or "FILE"
        st.download_button(
          f"{txt('Baixar', 'Download')} {label}",
          data=candidate.read_bytes(),
          file_name=candidate.name,
          mime=mime_by_suffix.get(suffix, "application/octet-stream"),
          key=(
            f"download_{key_prefix}_{safe_filename(requested.stem)}_"
            f"{index}_{safe_filename(candidate.name)}"
          ),
          width="stretch",
        )

  audit = globals().get("_render_static_figure_audit")
  if callable(audit):
    audit(requested, localized_title, key_prefix)
'''
  if anchor in source:
    source = source.replace(anchor, replacement + "\n\n" + anchor, 1)
  source += f"\n\n{MARKER}\n"
