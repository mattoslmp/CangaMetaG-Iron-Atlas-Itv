from __future__ import annotations

"""Make the app display the same label-corrected frozen taxonomy figures."""

MARKER = "CANGAMETAG_CORRECTED_TAXONOMY_STATIC_ASSETS_V1 = 1"

if MARKER not in source:
  import_anchor = (
    "from src.current_taxonomy_display import harmonize_table as "
    "harmonize_current_taxonomy_table\n"
  )
  corrected_imports = '''from src.corrected_taxonomy_static_assets import (
  CORRECTED_TAXONOMY_STATIC_FILENAMES,
  build_corrected_taxonomy_publication_overlay,
  materialize_corrected_taxonomy_static,
)
'''
  if corrected_imports not in source:
    if import_anchor in source:
      source = source.replace(import_anchor, import_anchor + corrected_imports, 1)
    else:
      source = corrected_imports + source

  display_signature = (
    'def _display_static_publication_image(path: Path, title: str, caption: str = "", '
    'key_prefix: str = "static_publication_image") -> None:'
  )
  display_start = source.find(display_signature)
  if display_start >= 0:
    display_end = source.find("\ndef ", display_start + len(display_signature))
    if display_end < 0:
      display_end = len(source)
    original = source[display_start:display_end].replace(
      "def _display_static_publication_image(",
      "def _display_static_publication_image_original(",
      1,
    )
    wrapper = r'''
def _display_static_publication_image(path: Path, title: str, caption: str = "", key_prefix: str = "static_publication_image") -> None:
  corrected_path = materialize_corrected_taxonomy_static(path.name, APP_CACHE_DIR)
  if corrected_path is None:
    return _display_static_publication_image_original(path, title, caption, key_prefix)
  st.markdown(f"#### `{path.name}`")
  st.image(str(corrected_path), width="stretch", caption=caption or None)
  st.download_button(
    txt("Baixar SVG corrigido", "Download corrected SVG"),
    data=corrected_path.read_bytes(),
    file_name=corrected_path.name,
    mime="image/svg+xml",
    key=f"{key_prefix}_{safe_filename(path.stem)}_corrected_svg",
    width="stretch",
  )
  st.caption(txt(
    "Nomenclatura de filo atualizada; valores, ordem, cores e geometria são os da figura congelada do artigo.",
    "Phylum nomenclature updated; values, order, colours and geometry are those of the frozen article figure.",
  ))
'''
    source = source[:display_start] + original + "\n\n" + wrapper + source[display_end:]

  valid_signature = "def is_valid_display_image(path: Path) -> tuple[bool, str]:"
  valid_start = source.find(valid_signature)
  if valid_start >= 0:
    valid_end = source.find("\ndef ", valid_start + len(valid_signature))
    if valid_end < 0:
      valid_end = len(source)
    original = source[valid_start:valid_end].replace(
      "def is_valid_display_image(",
      "def is_valid_display_image_original(",
      1,
    )
    wrapper = r'''
def is_valid_display_image(path: Path) -> tuple[bool, str]:
  if path.suffix.lower() == ".svg":
    try:
      text = path.read_text(encoding="utf-8", errors="strict")
      if "<svg" not in text[:5000].lower():
        return False, "invalid SVG"
      return True, "validated corrected SVG"
    except Exception as exc:
      return False, f"unreadable SVG: {exc}"
  return is_valid_display_image_original(path)
'''
    source = source[:valid_start] + original + "\n\n" + wrapper + source[valid_end:]

  directory_block = '''  main_fig_dir = BASE_DIR / "outputs" / "final_publication_figures"
  supplementary_fig_dir = BASE_DIR / "outputs" / "app_supplementary_figures"
'''
  directory_replacement = '''  source_main_fig_dir = BASE_DIR / "outputs" / "final_publication_figures"
  source_supplementary_fig_dir = BASE_DIR / "outputs" / "app_supplementary_figures"
  main_fig_dir, supplementary_fig_dir = build_corrected_taxonomy_publication_overlay(
    source_main_fig_dir,
    source_supplementary_fig_dir,
    APP_CACHE_DIR,
  )
'''
  if directory_block in source:
    source = source.replace(directory_block, directory_replacement, 1)

  raster_candidate = (
    'fp.suffix.lower() in image_suffixes and not _is_prohibited_publication_figure(fp)'
  )
  corrected_candidate = (
    '(fp.suffix.lower() in image_suffixes or fp.name in '
    'CORRECTED_TAXONOMY_STATIC_FILENAMES) and not '
    '_is_prohibited_publication_figure(fp)'
  )
  source = source.replace(raster_candidate, corrected_candidate)
  source += f"\n\n{MARKER}\n"
