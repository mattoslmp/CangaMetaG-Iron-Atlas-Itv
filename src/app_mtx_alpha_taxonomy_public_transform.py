from __future__ import annotations

"""Attach MTX, alpha-diversity and taxonomy presentation fixes safely.

This transform uses only exact, indentation-preserving replacements. It never
removes a multi-line Streamlit call by scanning parentheses, because doing so
can leave continuation lines orphaned and make the generated app invalid.
"""

MARKER = "CANGAMETAG_MTX_ALPHA_TAXONOMY_PUBLIC_V4 = 1"


if MARKER not in source:
  candidate = source

  future_anchor = "from __future__ import annotations\n"
  runtime_imports = '''from src.app_mtx_alpha_taxonomy_runtime import (
  install_categorical_group_guard,
  render_complete_metatranscriptome_panel,
  render_taxonomy_article_overlap_panel,
)
install_categorical_group_guard()
'''
  if runtime_imports not in candidate:
    if future_anchor not in candidate:
      raise RuntimeError("Could not install the MTX/taxonomy runtime imports")
    candidate = candidate.replace(
      future_anchor,
      future_anchor + runtime_imports,
      1,
    )

  taxonomy_anchor = (
    '  st.markdown("### " + txt("Visualização taxonômica interativa", '
    '"Interactive taxonomic visualization"))'
  )
  taxonomy_call = "  render_taxonomy_article_overlap_panel(globals())\n\n"
  if (
    taxonomy_anchor in candidate
    and taxonomy_call.strip() not in candidate
  ):
    candidate = candidate.replace(
      taxonomy_anchor,
      taxonomy_call + taxonomy_anchor,
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
  if old_caption in candidate:
    candidate = candidate.replace(old_caption, new_caption, 1)

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
  if (
    mtx_anchor in candidate
    and "metadata=meta,\n    numeric_columns=numeric_cols," not in candidate
  ):
    candidate = candidate.replace(mtx_anchor, mtx_call, 1)

  replacements = {
    "Tabela taxonômica completa para auditoria e download": "Tabela taxonômica completa e download",
    "Complete taxonomic table for audit and download": "Complete taxonomic table and download",
    "Auditoria das amostras": "Amostras incluídas",
    "Sample audit": "Included samples",
    "Tabela científica": "Tabela",
    "Scientific table": "Table",
  }
  for old, new in replacements.items():
    candidate = candidate.replace(old, new)

  candidate += f"\n\n{MARKER}\n"

  try:
    compile(candidate, "app_core_after_mtx_alpha_taxonomy_transform.py", "exec")
  except (SyntaxError, IndentationError) as exc:
    line_number = int(getattr(exc, "lineno", 0) or 0)
    lines = candidate.splitlines()
    start = max(0, line_number - 4)
    end = min(len(lines), line_number + 3)
    context = "\n".join(
      f"{index + 1}: {lines[index]}"
      for index in range(start, end)
    )
    raise RuntimeError(
      "The MTX/taxonomy transform generated invalid Python at "
      f"line {line_number}: {exc}.\n{context}"
    ) from exc

  source = candidate
