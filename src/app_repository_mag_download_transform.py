from __future__ import annotations


MARKER = "def repository_mag_download_panel("

if MARKER not in source:
  panel_start = source.find("def bvbrc_cli_sync_panel(mag_options: list[str]):\n")
  panel_end = source.find("\ndef mags_tab():", panel_start)
  if panel_start >= 0 and panel_end >= 0:
    replacement = r'''def _repository_mag_files(folder: Path | None) -> list[Path]:
  if folder is None:
    return []
  folder = Path(folder)
  if not folder.exists() or not folder.is_dir():
    return []
  return sorted(path for path in folder.rglob("*") if path.is_file())


def _repository_mag_relative_folder(folder: Path) -> str:
  try:
    return str(folder.resolve().relative_to(BASE_DIR.resolve()))
  except Exception:
    return folder.name


def _repository_mag_size_text(size_bytes: int) -> str:
  size = float(max(int(size_bytes or 0), 0))
  for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
    if size < 1024.0 or unit == "TiB":
      return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
    size /= 1024.0
  return f"{int(size_bytes)} B"


def _repository_mag_signature(folder: Path, files: list[Path]) -> tuple[tuple[str, int, int], ...]:
  signature = []
  for path in files:
    try:
      stat = path.stat()
      signature.append((str(path.relative_to(folder)), int(stat.st_size), int(stat.st_mtime_ns)))
    except Exception:
      continue
  return tuple(signature)


@st.cache_data(show_spinner=False)
def _repository_mag_zip_bytes(
  folder_text: str,
  signature: tuple[tuple[str, int, int], ...],
) -> bytes:
  from io import BytesIO

  folder = Path(folder_text)
  buffer = BytesIO()
  with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for relative, _size, _mtime in signature:
      path = folder / relative
      try:
        resolved = path.resolve()
        resolved.relative_to(folder.resolve())
      except Exception:
        continue
      if resolved.is_file():
        archive.write(resolved, arcname=str(Path(folder.name) / relative))
  return buffer.getvalue()


def _repository_mag_inventory_frame() -> pd.DataFrame:
  preferred: dict[str, dict] = {}
  annotation_root = ANNOTATION_DIR.resolve()
  for folder in list_annotation_folders():
    folder = Path(folder)
    files = _repository_mag_files(folder)
    if not files:
      continue
    mag_id = canonical_mag_id(folder.name)
    total_bytes = sum(path.stat().st_size for path in files)
    record = {
      "MAG": mag_id,
      "repository_folder": _repository_mag_relative_folder(folder),
      "files": len(files),
      "size_bytes": total_bytes,
      "size": _repository_mag_size_text(total_bytes),
      "FASTA": "yes" if fasta_path_for_mag(mag_id, folder) else "no",
      "GBK/GenBank": "yes" if genbank_path_for_mag(mag_id, folder) else "no",
    }
    current = preferred.get(mag_id)
    try:
      is_annotation_folder = folder.resolve().is_relative_to(annotation_root)
    except Exception:
      is_annotation_folder = False
    if current is None or is_annotation_folder:
      preferred[mag_id] = record
  rows = list(preferred.values())
  rows.sort(key=lambda row: mag_number(row.get("MAG")) or 10**9)
  return pd.DataFrame(rows)


def repository_mag_download_panel(
  selected_mag: str,
  folder: Path | None,
  public_link: dict | None = None,
  fasta: Path | None = None,
  gbk: Path | None = None,
) -> None:
  mag_id = canonical_mag_id(selected_mag)
  folder = Path(folder) if folder is not None else ANNOTATION_DIR / mag_id
  files = _repository_mag_files(folder)
  if not files:
    st.info(txt(
      f"{mag_id} ainda não possui uma pasta com arquivos no repositório. Quando `Annotation/{mag_id}/` for enviado ao GitHub e o app for reiniciado, os downloads aparecerão aqui automaticamente.",
      f"{mag_id} does not yet have a file folder in the repository. After `Annotation/{mag_id}/` is uploaded to GitHub and the app is rebooted, its downloads will appear here automatically.",
    ))
    if public_link:
      st.caption(txt(
        "Existe uma referência pública BV-BRC registrada para este MAG, mas o aplicativo não tentará copiar arquivos do Workspace remoto.",
        "A public BV-BRC reference is registered for this MAG, but the application will not try to copy files from the remote Workspace.",
      ))
    return

  total_bytes = sum(path.stat().st_size for path in files)
  st.success(txt(
    f"{mag_id} disponível no repositório. O aplicativo funciona somente como intermediário de download e não modifica esta pasta.",
    f"{mag_id} is available in the repository. The application acts only as a download intermediary and does not modify this folder.",
  ))

  m1, m2, m3 = st.columns(3)
  m1.metric(txt("Arquivos disponíveis", "Available files"), len(files))
  m2.metric(txt("Tamanho total", "Total size"), _repository_mag_size_text(total_bytes))
  m3.metric(txt("Pasta no repositório", "Repository folder"), _repository_mag_relative_folder(folder))

  manifest = file_manifest(folder).copy()
  if not manifest.empty:
    manifest["size_MiB"] = pd.to_numeric(manifest["bytes"], errors="coerce").fillna(0).div(1024**2).round(3)
    show_table(manifest, f"repository_manifest_{safe_filename(mag_id)}", height=320)
    csv_button(
      manifest,
      f"{mag_id}_repository_file_manifest.csv",
      txt("Baixar inventário de arquivos", "Download file inventory"),
    )

  common1, common2 = st.columns(2)
  with common1:
    if fasta and Path(fasta).is_file():
      fasta_path = Path(fasta)
      st.download_button(
        txt("Baixar FASTA/contigs", "Download FASTA/contigs"),
        data=fasta_path.read_bytes(),
        file_name=fasta_path.name,
        mime="application/octet-stream",
        key=f"repository_fasta_{safe_filename(mag_id)}",
        width="stretch",
      )
    else:
      st.caption(txt("FASTA não disponível nesta pasta.", "FASTA is not available in this folder."))
  with common2:
    if gbk and Path(gbk).is_file():
      gbk_path = Path(gbk)
      st.download_button(
        txt("Baixar GenBank/GBK", "Download GenBank/GBK"),
        data=gbk_path.read_bytes(),
        file_name=gbk_path.name,
        mime="application/octet-stream",
        key=f"repository_gbk_{safe_filename(mag_id)}",
        width="stretch",
      )
    else:
      st.caption(txt("GBK/GenBank não disponível nesta pasta.", "GBK/GenBank is not available in this folder."))

  relative_options = [str(path.relative_to(folder)) for path in files]
  selected_relative = st.selectbox(
    txt("Escolha qualquer arquivo do MAG", "Choose any MAG file"),
    relative_options,
    key=f"repository_file_select_{safe_filename(mag_id)}",
  )
  selected_path = (folder / selected_relative).resolve()
  try:
    selected_path.relative_to(folder.resolve())
    selected_is_safe = selected_path.is_file()
  except Exception:
    selected_is_safe = False
  if selected_is_safe:
    selected_size = selected_path.stat().st_size
    if selected_size > 750 * 1024**2:
      st.warning(txt(
        "Este arquivo ultrapassa 750 MiB e não será carregado na memória do Streamlit. Divida-o ou disponibilize-o por um armazenamento externo.",
        "This file exceeds 750 MiB and will not be loaded into Streamlit memory. Split it or provide it through external storage.",
      ))
    else:
      st.download_button(
        txt("Baixar arquivo selecionado", "Download selected file"),
        data=selected_path.read_bytes(),
        file_name=selected_path.name,
        mime="application/octet-stream",
        key=f"repository_file_download_{safe_filename(mag_id)}_{safe_filename(selected_relative)}",
        width="stretch",
      )

  prepare_zip = st.checkbox(
    txt(
      "Preparar pacote ZIP completo deste MAG",
      "Prepare the complete ZIP package for this MAG",
    ),
    value=False,
    key=f"repository_prepare_zip_{safe_filename(mag_id)}",
    help=txt(
      "A estrutura e o conteúdo dos arquivos são preservados. A compactação ocorre somente após marcar esta opção.",
      "File structure and contents are preserved. Compression runs only after this option is selected.",
    ),
  )
  if prepare_zip:
    if total_bytes > 750 * 1024**2:
      st.warning(txt(
        "Esta pasta ultrapassa 750 MiB. Para proteger a memória do servidor, faça o download dos arquivos individualmente.",
        "This folder exceeds 750 MiB. To protect server memory, download its files individually.",
      ))
    else:
      signature = _repository_mag_signature(folder, files)
      with st.spinner(txt("Preparando o ZIP sem alterar os arquivos...", "Preparing the ZIP without changing any files...")):
        package = _repository_mag_zip_bytes(str(folder.resolve()), signature)
      st.download_button(
        txt("Baixar pacote completo do MAG", "Download complete MAG package"),
        data=package,
        file_name=f"{mag_id}_Annotation.zip",
        mime="application/zip",
        key=f"repository_zip_download_{safe_filename(mag_id)}",
        type="primary",
        width="stretch",
      )


def bvbrc_cli_sync_panel(mag_options: list[str]):
  st.markdown("#### " + txt(
    "Arquivos de anotação dos MAGs disponíveis para download",
    "MAG annotation files available for download",
  ))
  st.info(txt(
    "Esta implantação é somente leitura. O app não executa `p3-ls`, `p3-cp`, download remoto, sincronização automática ou gravação em `Annotation/`. Ele disponibiliza aos visitantes apenas os arquivos que já estiverem versionados nas pastas `Annotation/MAGx/` do repositório.",
    "This deployment is read-only. The app does not run `p3-ls`, `p3-cp`, remote downloads, automatic synchronization or writes to `Annotation/`. It offers visitors only the files already versioned under the repository's `Annotation/MAGx/` folders.",
  ))

  inventory = _repository_mag_inventory_frame()
  if inventory.empty:
    st.warning(txt(
      "Nenhuma pasta de MAG com arquivos foi encontrada no repositório. Envie cada conjunto para `Annotation/MAG1/`, `Annotation/MAG2/`, etc., e reinicie o app.",
      "No MAG folder containing files was found in the repository. Upload each set to `Annotation/MAG1/`, `Annotation/MAG2/`, etc., and reboot the app.",
    ))
    return

  total_files = int(pd.to_numeric(inventory["files"], errors="coerce").fillna(0).sum())
  total_bytes = int(pd.to_numeric(inventory["size_bytes"], errors="coerce").fillna(0).sum())
  a1, a2, a3 = st.columns(3)
  a1.metric(txt("MAGs disponíveis", "Available MAGs"), len(inventory))
  a2.metric(txt("Arquivos disponíveis", "Available files"), total_files)
  a3.metric(txt("Volume disponível", "Available volume"), _repository_mag_size_text(total_bytes))
  show_table(inventory.drop(columns=["size_bytes"], errors="ignore"), "repository_mag_inventory", height=300)
  csv_button(
    inventory,
    "repository_MAG_download_inventory.csv",
    txt("Baixar inventário dos MAGs", "Download MAG inventory"),
  )
  st.caption(txt(
    "Selecione um MAG específico abaixo para baixar FASTA, GBK, qualquer arquivo individual ou o pacote ZIP completo.",
    "Select a specific MAG below to download FASTA, GBK, any individual file or the complete ZIP package.",
  ))

'''
    source = source[:panel_start] + replacement + source[panel_end + 1:]

  mags_start = source.find("def mags_tab():\n")
  auto_start = source.find(
    '    selected_local_status = bvbrc_local_annotation_status(selected_mag, st.session_state.get("bvbrc_local_annotation_dir", "Annotation"))\n',
    mags_start,
  )
  public_link_anchor = source.find(
    "    public_link = public_link_for_mag(selected_mag)\n",
    auto_start,
  )
  if auto_start >= 0 and public_link_anchor >= 0:
    source = source[:auto_start] + source[public_link_anchor:]

  mags_start = source.find("def mags_tab():\n")
  selected_assets_start = source.find(
    "    public_link = public_link_for_mag(selected_mag)\n",
    mags_start,
  )
  downloads_start = source.find(
    "    d1, d2, d3 = st.columns(3)\n",
    selected_assets_start,
  )
  downloads_end = source.find("\n\n  st.divider()", downloads_start)
  if selected_assets_start >= 0 and downloads_start >= 0 and downloads_end >= 0:
    downloads = '''    repository_mag_download_panel(
      selected_mag=selected_mag,
      folder=folder,
      public_link=public_link,
      fasta=fasta,
      gbk=gbk,
    )
'''
    source = source[:downloads_start] + downloads + source[downloads_end:]

old_intro_pt = (
  "Esta é a seção principal da base: ela conecta os MAGs/bins do artigo às classificações taxonômicas, métricas de qualidade, FASTA, GenBank/GBK e resultados de anotação BV-BRC/PATRIC. Prefira usar os Genome IDs públicos do BV-BRC em `data/bvbrc_public_links.csv`; pastas locais `Annotation/MAG1`, `Annotation/MAG2`, ... continuam funcionando como fallback."
)
new_intro_pt = (
  "Esta é a seção principal da base: ela conecta os MAGs/bins do artigo às classificações taxonômicas, métricas de qualidade, FASTA, GenBank/GBK e demais arquivos de anotação. Os conjuntos enviados para `Annotation/MAG1`, `Annotation/MAG2`, ... são disponibilizados pelo app em modo somente leitura para download no computador do usuário."
)
old_intro_en = (
  "This is the main database section: it connects article MAGs/bins to taxonomic classifications, quality metrics, FASTA, GenBank/GBK and BV-BRC/PATRIC annotation outputs. Prefer public BV-BRC Genome IDs in `data/bvbrc_public_links.csv`; local `Annotation/MAG1`, `Annotation/MAG2`, ... folders remain supported as a fallback."
)
new_intro_en = (
  "This is the main database section: it connects article MAGs/bins to taxonomic classifications, quality metrics, FASTA, GenBank/GBK and other annotation files. Sets uploaded to `Annotation/MAG1`, `Annotation/MAG2`, ... are offered by the read-only app for download to the user's computer."
)
source = source.replace(old_intro_pt, new_intro_pt, 1)
source = source.replace(old_intro_en, new_intro_en, 1)
