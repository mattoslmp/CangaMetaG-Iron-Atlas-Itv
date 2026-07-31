from __future__ import annotations

"""Attach final MTX, alpha-diversity and taxonomy presentation fixes.

Optional presentation anchors are handled defensively: a wording change in an
earlier transform must never prevent the Streamlit app from compiling.
"""

MARKER = "CANGAMETAG_MTX_ALPHA_TAXONOMY_PUBLIC_V3 = 1"


def _remove_public_call_containing(text: str, phrase: str) -> str:
  """Remove one public Streamlit prose call containing an internal phrase."""
  while phrase in text:
    position = text.find(phrase)
    starts = [
      text.rfind("st.caption(txt(", 0, position),
      text.rfind("st.info(txt(", 0, position),
      text.rfind("st.markdown(txt(", 0, position),
      text.rfind("st.warning(txt(", 0, position),
    ]
    start = max(starts)
    if start < 0:
      return text.replace(phrase, "")
    line_start = text.rfind("\n", 0, start) + 1
    cursor = start
    depth = 0
    seen_open = False
    while cursor < len(text):
      character = text[cursor]
      if character == "(":
        depth += 1
        seen_open = True
      elif character == ")":
        depth -= 1
      if seen_open and depth <= 0:
        line_end = text.find("\n", cursor)
        if line_end < 0:
          line_end = len(text)
        text = text[:line_start] + text[line_end + (1 if line_end < len(text) else 0):]
        break
      cursor += 1
    else:
      return text.replace(phrase, "")
  return text


if MARKER not in source:
  taxonomy_anchor = (
    '  st.markdown("### " + txt("Visualização taxonômica interativa", '
    '"Interactive taxonomic visualization"))'
  )
  if taxonomy_anchor in source and "render_taxonomy_article_overlap_panel(globals())" not in source:
    source = source.replace(
      taxonomy_anchor,
      "  render_taxonomy_article_overlap_panel(globals())\n\n" + taxonomy_anchor,
      1,
    )

  old_caption = '''    st.caption(txt(
      f"Composição exibida: {len(pair_lakes)}/20 amostras das lagoas + {len(pair_external)} colunas externas; {len(cols)} colunas no total.",
      f"Displayed composition: {len(pair_lakes)}/20 lake samples + {len(pair_external)} external columns; {len(cols)} columns in total.",
    ))'''
  new_caption = '''    if pair_lakes:
      st.caption(txt(
        f"Composição exibida: {len(pair_lakes)}/20 amostras das lagoas + {len(pair_external)} colunas externas; {len(cols)} colunas no total.",
        f"Displayed composition: {len(pair_lakes)}/20 lake samples + {len(pair_external)} external columns; {len(cols)} columns in total.",
      ))
    elif "metatranscript" in (scope_name_pt + " " + scope_name_en).casefold():
      st.caption(txt(
        f"Composição exibida: {len(pair_external)}/{len(pair_external)} amostras de metatranscriptoma; todos os {len(df)} KOs/marcadores estão selecionados por padrão.",
        f"Displayed composition: {len(pair_external)}/{len(pair_external)} metatranscriptome samples; all {len(df)} KOs/markers are selected by default.",
      ))
    else:
      st.caption(txt(
        f"Composição exibida: {len(pair_external)} colunas externas; {len(cols)} colunas no total.",
        f"Displayed composition: {len(pair_external)} external columns; {len(cols)} columns in total.",
      ))'''
  if old_caption in source:
    source = source.replace(old_caption, new_caption, 1)

  mtx_anchor = '''  render_pair(
    "2B. Lagoas amazônicas + todos os ambientes externos",'''
  mtx_call = '''  render_complete_metatranscriptome_panel(
    globals(),
    metadata=meta,
    numeric_columns=numeric_cols,
    data=df,
    render_pair=render_pair,
    base_key=base_key,
  )

  render_pair(
    "2B. Lagoas amazônicas + todos os ambientes externos",'''
  if mtx_anchor in source and "render_complete_metatranscriptome_panel(" not in source:
    source = source.replace(mtx_anchor, mtx_call, 1)

  for phrase in (
    "O visualizador interativo incorpora o mesmo SVG corrigido exibido como figura estática.",
    "The interactive viewer embeds the same corrected SVG displayed as the static figure.",
    "Integridade confirmada: 189/189 KOs",
    "Integrity confirmed: 189/189 KOs",
  ):
    source = _remove_public_call_containing(source, phrase)

  replacements = {
    "Tabela taxonômica completa para auditoria e download": "Tabela taxonômica completa e download",
    "Complete taxonomic table for audit and download": "Complete taxonomic table and download",
    "Auditoria das amostras": "Amostras incluídas",
    "Sample audit": "Included samples",
    "Tabela científica": "Tabela",
    "Scientific table": "Table",
  }
  for old, new in replacements.items():
    source = source.replace(old, new)

  page_anchor = "page_handler = page_handlers.get(selected_page)"
  runtime_imports = '''from src.app_mtx_alpha_taxonomy_runtime import (
  install_categorical_group_guard,
  render_complete_metatranscriptome_panel,
  render_taxonomy_article_overlap_panel,
)
install_categorical_group_guard()

'''
  if page_anchor in source and runtime_imports not in source:
    source = source.replace(page_anchor, runtime_imports + page_anchor, 1)

  source += f"\n\n{MARKER}\n"
