from __future__ import annotations

"""Show the canonical final figure scripts in the reproducibility page."""

MARKER = "CANGAMETAG_FINAL_SCRIPT_MANIFEST_V1 = 1"

if MARKER not in source:
  anchor = '''def code_reproducibility_tab():
  st.subheader(txt("Código reprodutível do banco e das figuras", "Reproducible code for the database and figures"))'''
  replacement = anchor + r'''
  final_manifest_path = BASE_DIR / "scripts" / "FINAL_SCRIPT_MANIFEST.json"
  if final_manifest_path.exists():
    try:
      final_manifest = json.loads(final_manifest_path.read_text(encoding="utf-8"))
      final_rows = []
      for record in final_manifest.get("canonical_scripts", []):
        final_rows.append({
          "Figure scope": record.get("figure_scope", ""),
          "Final script": record.get("path", ""),
          "Status": record.get("status", ""),
          "Command": record.get("command", ""),
          "Inputs": "; ".join(record.get("inputs", [])),
          "Outputs": "; ".join(record.get("outputs", [])),
        })
      if final_rows:
        st.markdown("### " + txt("Scripts canônicos finais", "Canonical final scripts"))
        st.caption(txt(
          "Estes são os pontos de entrada usados pelo app e reservados para o próximo pacote do artigo. Implementações anteriores permanecem apenas como wrappers de compatibilidade.",
          "These are the entry points used by the app and reserved for the next article package. Previous implementations remain only as compatibility wrappers.",
        ))
        final_table = pd.DataFrame(final_rows)
        show_table(final_table, "canonical_final_script_manifest", height=280)
        st.download_button(
          txt("Baixar manifesto dos scripts finais", "Download final-script manifest"),
          data=final_manifest_path.read_bytes(),
          file_name=final_manifest_path.name,
          mime="application/json",
          key="download_final_script_manifest_json",
        )
        for record in final_manifest.get("canonical_scripts", []):
          command = str(record.get("command", "") or "").strip()
          if command:
            st.code(command, language="bash")
    except Exception as exc:
      LOGGER.warning("Could not display final script manifest: %s", exc)'''
  if anchor in source:
    source = source.replace(anchor, replacement, 1)
  source += f"\n\n{MARKER}\n"
