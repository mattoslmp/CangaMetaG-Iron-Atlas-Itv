from __future__ import annotations


source = source.replace(
  '  with st.expander(txt("Baixar automaticamente resultados BV-BRC para Annotation/MAGx", "Automatically download BV-BRC results to Annotation/MAGx"), expanded=False):\n',
  '  with st.expander(txt("Baixar automaticamente resultados BV-BRC para Annotation/MAGx", "Automatically download BV-BRC results to Annotation/MAGx"), expanded=True):\n',
  1,
)
source = source.replace(
  '      value=bool(st.session_state.get("bvbrc_auto_sync_selected", False)),\n',
  '      value=bool(st.session_state.get("bvbrc_auto_sync_selected", True)),\n',
  1,
)
