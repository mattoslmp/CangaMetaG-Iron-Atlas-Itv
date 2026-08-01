from __future__ import annotations

"""Expose canonical final figure scripts and their shared modules in the app."""

MARKER = "CANGAMETAG_FINAL_SCRIPT_MANIFEST_V2_DOWNLOADABLE = 1"

if MARKER not in source:
  anchor = '''def code_reproducibility_tab():
  st.subheader(txt("Código reprodutível do banco e das figuras", "Reproducible code for the database and figures"))'''
  replacement = anchor + r'''
  final_manifest_path = BASE_DIR / "scripts" / "FINAL_SCRIPT_MANIFEST.json"
  if final_manifest_path.exists():
    try:
      import io as _final_script_io
      import zipfile as _final_script_zipfile

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
          "Generative image model": "No" if record.get("generative_image_model_used") is False else "Not applicable",
        })
      if final_rows:
        st.markdown("### " + txt(
          "Figuras finais e scripts",
          "Final figures and scripts",
        ))
        st.caption(txt(
          "Todos os arquivos abaixo são scripts determinísticos executados sobre os dados científicos empacotados. O app disponibiliza o ponto de entrada canônico e os módulos compartilhados usados por cada figura; nenhuma figura científica é produzida por IA generativa.",
          "Every file below is deterministic code executed against the packaged scientific data. The app provides the canonical entry point and the shared modules used by each figure; no scientific figure is produced with generative AI.",
        ))
        final_table = pd.DataFrame(final_rows)
        show_table(final_table, "canonical_final_script_manifest", height=390)
        st.download_button(
          txt("Baixar manifesto dos scripts finais", "Download final-script manifest"),
          data=final_manifest_path.read_bytes(),
          file_name=final_manifest_path.name,
          mime="application/json",
          key="download_final_script_manifest_json",
        )

        for record_index, record in enumerate(final_manifest.get("canonical_scripts", []), start=1):
          scope = str(record.get("figure_scope", "") or f"Script {record_index}")
          script_relative = str(record.get("path", "") or "").strip()
          script_path = BASE_DIR / script_relative if script_relative else None
          shared = [
            str(item).strip()
            for item in record.get("app_shared_modules", [])
            if str(item).strip()
          ]
          source_paths = [script_relative, *shared]
          source_paths = list(dict.fromkeys(path for path in source_paths if path))
          existing_sources = [
            (relative, BASE_DIR / relative)
            for relative in source_paths
            if (BASE_DIR / relative).is_file()
          ]

          with st.expander(scope, expanded=False):
            st.markdown(f"**{txt('Script canônico', 'Canonical script')}:** `{script_relative}`")
            command = str(record.get("command", "") or "").strip()
            if command:
              st.code(command, language="bash")
            st.markdown(f"**{txt('Dados de entrada', 'Input data')}**")
            st.code("\n".join(record.get("inputs", [])) or "—", language="text")
            st.markdown(f"**{txt('Arquivos de saída', 'Output files')}**")
            st.code("\n".join(record.get("outputs", [])) or "—", language="text")

            if script_path is not None and script_path.is_file():
              script_text = script_path.read_text(encoding="utf-8", errors="replace")
              st.markdown(f"**{txt('Código-fonte', 'Source code')}**")
              st.code(script_text, language="python")
              st.download_button(
                txt("Baixar script canônico", "Download canonical script"),
                data=script_path.read_bytes(),
                file_name=script_path.name,
                mime="text/x-python",
                key=f"download_final_script_{record_index}_{safe_filename(script_path.stem)}",
              )

            if existing_sources:
              archive_buffer = _final_script_io.BytesIO()
              with _final_script_zipfile.ZipFile(
                archive_buffer,
                mode="w",
                compression=_final_script_zipfile.ZIP_DEFLATED,
              ) as archive:
                for relative, absolute in existing_sources:
                  archive.writestr(relative, absolute.read_bytes())
              st.download_button(
                txt(
                  "Baixar script e módulos compartilhados (ZIP)",
                  "Download script and shared modules (ZIP)",
                ),
                data=archive_buffer.getvalue(),
                file_name=f"final_figure_script_{record_index:02d}.zip",
                mime="application/zip",
                key=f"download_final_script_bundle_{record_index}",
              )
              module_table = pd.DataFrame({
                "Source file": [relative for relative, _ in existing_sources],
                "Role": [
                  "Canonical entry point" if relative == script_relative else "Shared figure module"
                  for relative, _ in existing_sources
                ],
              })
              show_table(
                module_table,
                f"final_script_modules_{record_index}",
                height=min(360, 92 + 38 * len(module_table)),
              )
    except Exception as exc:
      LOGGER.warning("Could not display final script manifest: %s", exc)'''
  if anchor in source:
    source = source.replace(anchor, replacement, 1)
  source += f"\n\n{MARKER}\n"
