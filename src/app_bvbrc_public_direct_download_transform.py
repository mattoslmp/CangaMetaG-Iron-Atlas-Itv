from __future__ import annotations


MARKER = "def _bvbrc_public_workspace_inventory("

if MARKER not in source:
  local_name = "def repository_mag_download_panel("
  fallback_name = "def _repository_mag_download_panel_local_fallback("
  if local_name in source and fallback_name not in source:
    source = source.replace(local_name, fallback_name, 1)

  panel_start = source.find("def bvbrc_cli_sync_panel(mag_options: list[str]):\n")
  panel_end = source.find("\ndef mags_tab():", panel_start)
  if panel_start >= 0 and panel_end >= 0:
    replacement = r'''BVBRC_PUBLIC_WORKSPACE_ENDPOINTS = (
  "https://www.bv-brc.org/services/Workspace",
  "https://p3.theseed.org/services/Workspace",
)


def _bvbrc_public_rpc(method: str, parameters: dict, timeout: int = 60) -> tuple[bool, object, str, str]:
  """Call the public Workspace JSON-RPC API without an auth token."""
  body = {
    "method": f"Workspace.{method}",
    "params": [parameters],
    "version": "1.1",
    "id": hashlib.sha256(
      f"{method}:{json.dumps(parameters, sort_keys=True, default=str)}".encode("utf-8")
    ).hexdigest()[:20],
  }
  errors = []
  headers = {
    "Content-Type": "application/json",
    "User-Agent": "CangaMetaG-Iron-Atlas/1.0 public-workspace-client",
  }
  # Deliberately do not send Authorization. Globally readable Workspace objects
  # are exposed by the official API with optional authentication.
  for endpoint in BVBRC_PUBLIC_WORKSPACE_ENDPOINTS:
    try:
      response = requests.post(
        endpoint,
        json=body,
        headers=headers,
        timeout=timeout,
      )
      if response.status_code != 200:
        errors.append(f"{endpoint}: HTTP {response.status_code}")
        continue
      payload = response.json()
      if payload.get("error"):
        error = payload.get("error") or {}
        message = error.get("message") or error.get("error") or str(error)
        errors.append(f"{endpoint}: {message}")
        continue
      if "result" not in payload:
        errors.append(f"{endpoint}: response did not contain result")
        continue
      return True, payload["result"], endpoint, ""
    except Exception as exc:
      errors.append(f"{endpoint}: {type(exc).__name__}: {exc}")
  return False, None, "", " | ".join(errors)


def _bvbrc_unwrap_single(value: object) -> object:
  current = value
  while isinstance(current, list) and len(current) == 1:
    current = current[0]
  return current


@st.cache_data(ttl=300, show_spinner=False)
def _bvbrc_public_workspace_inventory(
  workspace_base: str = BVBRC_DEFAULT_WORKSPACE_BASE,
) -> tuple[pd.DataFrame, str]:
  base = "/" + str(workspace_base or "").strip().strip("/")
  ok, result, endpoint, error = _bvbrc_public_rpc(
    "ls",
    {
      "paths": [base],
      "excludeDirectories": False,
      "excludeObjects": False,
      "recursive": False,
      "fullHierachicalOutput": False,
      "query": {},
      "adminmode": False,
    },
  )
  columns = [
    "MAG",
    "remote_name",
    "remote_path",
    "object_type",
    "size_bytes",
    "size",
    "global_permission",
    "endpoint",
  ]
  if not ok:
    return pd.DataFrame(columns=columns), error

  mapping = _bvbrc_unwrap_single(result)
  if not isinstance(mapping, dict):
    return pd.DataFrame(columns=columns), "Unexpected Workspace listing response"

  rows = []
  for _parent, entries in mapping.items():
    if not isinstance(entries, list):
      continue
    for meta in entries:
      if not isinstance(meta, (list, tuple)) or len(meta) < 3:
        continue
      name = str(meta[0] or "").strip()
      object_type = str(meta[1] or "").strip()
      remote_path = str(meta[2] or "").strip()
      mag_id = canonical_mag_id(name)
      number = mag_number(mag_id)
      if number is None or not name.lower().startswith(("mag", "bin")):
        continue
      try:
        size_bytes = int(meta[6] or 0) if len(meta) > 6 else 0
      except Exception:
        size_bytes = 0
      global_permission = str(meta[10] or "") if len(meta) > 10 else ""
      error_text = str(meta[12] or "") if len(meta) > 12 else ""
      if error_text:
        continue
      rows.append({
        "MAG": mag_id,
        "remote_name": name,
        "remote_path": remote_path,
        "object_type": object_type,
        "size_bytes": size_bytes,
        "size": _repository_mag_size_text(size_bytes),
        "global_permission": global_permission,
        "endpoint": endpoint,
      })
  frame = pd.DataFrame(rows, columns=columns)
  if not frame.empty:
    frame = frame.drop_duplicates(subset=["MAG"], keep="first")
    frame["_number"] = frame["MAG"].map(lambda value: mag_number(value) or 10**9)
    frame = frame.sort_values("_number").drop(columns=["_number"]).reset_index(drop=True)
  return frame, ""


@st.cache_data(ttl=240, show_spinner=False)
def _bvbrc_public_archive_url(remote_path: str, mag_id: str) -> tuple[str, int, int, str]:
  ok, result, _endpoint, error = _bvbrc_public_rpc(
    "get_archive_url",
    {
      "objects": [str(remote_path)],
      "recursive": True,
      "archive_name": f"{canonical_mag_id(mag_id)}_BV-BRC.zip",
      "archive_type": "zip",
    },
    timeout=120,
  )
  if not ok:
    return "", 0, 0, error
  values = result
  if isinstance(values, list) and len(values) == 1 and isinstance(values[0], (list, tuple)):
    values = values[0]
  if not isinstance(values, (list, tuple)) or not values:
    return "", 0, 0, "Unexpected archive URL response"
  url = str(values[0] or "")
  try:
    file_count = int(values[1] or 0) if len(values) > 1 else 0
  except Exception:
    file_count = 0
  try:
    total_size = int(values[2] or 0) if len(values) > 2 else 0
  except Exception:
    total_size = 0
  return url, file_count, total_size, ""


@st.cache_data(ttl=240, show_spinner=False)
def _bvbrc_public_file_url(remote_path: str) -> tuple[str, str]:
  ok, result, _endpoint, error = _bvbrc_public_rpc(
    "get_download_url",
    {"objects": [str(remote_path)]},
  )
  if not ok:
    return "", error
  values = result
  while isinstance(values, list) and len(values) == 1:
    values = values[0]
  if isinstance(values, str):
    return values, ""
  if isinstance(values, (list, tuple)) and values:
    return str(values[0] or ""), ""
  return "", "Unexpected download URL response"


def _bvbrc_public_record_for_mag(selected_mag: str) -> tuple[dict | None, str]:
  inventory, error = _bvbrc_public_workspace_inventory(BVBRC_DEFAULT_WORKSPACE_BASE)
  if inventory.empty:
    return None, error
  mag_id = canonical_mag_id(selected_mag)
  matched = inventory.loc[inventory["MAG"].astype(str) == mag_id]
  if matched.empty:
    return None, error
  return matched.iloc[0].to_dict(), ""


def bvbrc_cli_sync_panel(mag_options: list[str]):
  st.markdown("#### " + txt(
    "Download público direto dos MAGs no BV-BRC",
    "Direct public MAG downloads from BV-BRC",
  ))
  st.info(txt(
    "Os dados são públicos. O app não usa token, senha, `p3-ls` ou `p3-cp`. Ele consulta anonimamente a API oficial do Workspace e entrega ao navegador uma URL temporária; o arquivo é transferido diretamente do BV-BRC para o computador do visitante.",
    "The data are public. The app uses no token, password, `p3-ls` or `p3-cp`. It queries the official Workspace API anonymously and gives the browser a temporary URL; the file is transferred directly from BV-BRC to the visitor's computer.",
  ))
  st.code(BVBRC_DEFAULT_WORKSPACE_BASE, language="text")
  inventory, error = _bvbrc_public_workspace_inventory(BVBRC_DEFAULT_WORKSPACE_BASE)
  if inventory.empty:
    st.warning(txt(
      "O diretório público não pôde ser listado anonimamente neste momento. Isso pode indicar indisponibilidade temporária do BV-BRC ou que a permissão global ainda não está sendo reconhecida pela API. Arquivos já incluídos no repositório continuam disponíveis como fallback.",
      "The public directory could not be listed anonymously at this time. This may indicate temporary BV-BRC unavailability or that the global permission is not yet recognized by the API. Files already included in the repository remain available as a fallback.",
    ))
    if error:
      st.caption(error[:1500])
    local_inventory = _repository_mag_inventory_frame()
    if not local_inventory.empty:
      show_table(
        local_inventory.drop(columns=["size_bytes"], errors="ignore"),
        "repository_mag_inventory_fallback",
        height=280,
      )
    return

  total_size = int(pd.to_numeric(inventory["size_bytes"], errors="coerce").fillna(0).sum())
  c1, c2 = st.columns(2)
  c1.metric(txt("MAGs públicos detectados", "Public MAGs detected"), len(inventory))
  c2.metric(txt("Volume remoto informado", "Reported remote volume"), _repository_mag_size_text(total_size))
  visible = inventory.drop(columns=["size_bytes", "endpoint"], errors="ignore")
  show_table(visible, "bvbrc_public_mag_inventory", height=320)
  csv_button(
    visible,
    "BV-BRC_public_MAG_inventory.csv",
    txt("Baixar inventário público", "Download public inventory"),
  )
  st.caption(txt(
    "Selecione um MAG específico abaixo. O botão de download será criado a partir de uma URL temporária do próprio BV-BRC, sem armazenar o arquivo no Streamlit.",
    "Select a specific MAG below. Its download button is created from a temporary BV-BRC URL without storing the file in Streamlit.",
  ))


def repository_mag_download_panel(
  selected_mag: str,
  folder: Path | None,
  public_link: dict | None = None,
  fasta: Path | None = None,
  gbk: Path | None = None,
) -> None:
  mag_id = canonical_mag_id(selected_mag)
  record, error = _bvbrc_public_record_for_mag(mag_id)
  if record:
    remote_path = str(record.get("remote_path", ""))
    object_type = str(record.get("object_type", "")).casefold()
    st.success(txt(
      f"{mag_id} localizado no Workspace público do BV-BRC. Nenhuma credencial pessoal será usada.",
      f"{mag_id} was found in the public BV-BRC Workspace. No personal credential will be used.",
    ))
    st.caption(txt(
      f"Origem remota: {remote_path}",
      f"Remote source: {remote_path}",
    ))
    if "director" in object_type or "folder" in object_type:
      url, file_count, total_size, link_error = _bvbrc_public_archive_url(remote_path, mag_id)
      label = txt(
        f"Baixar {mag_id} diretamente do BV-BRC",
        f"Download {mag_id} directly from BV-BRC",
      )
      if url:
        st.link_button(label, url, type="primary", width="stretch")
        details = []
        if file_count:
          details.append(txt(f"{file_count} arquivos", f"{file_count} files"))
        if total_size:
          details.append(_repository_mag_size_text(total_size))
        if details:
          st.caption(" | ".join(details))
      else:
        st.warning(txt(
          "O BV-BRC reconheceu o MAG, mas não forneceu a URL temporária do arquivo neste momento.",
          "BV-BRC recognized the MAG but did not provide a temporary file URL at this time.",
        ))
        if link_error:
          st.caption(link_error[:1500])
    else:
      url, link_error = _bvbrc_public_file_url(remote_path)
      if url:
        st.link_button(
          txt(f"Baixar {mag_id} diretamente do BV-BRC", f"Download {mag_id} directly from BV-BRC"),
          url,
          type="primary",
          width="stretch",
        )
      elif link_error:
        st.warning(link_error[:1500])
    st.caption(txt(
      "O navegador controla o destino: ele pode abrir a janela 'Salvar como' ou usar a pasta Downloads, conforme a configuração do visitante.",
      "The browser controls the destination: it may open a Save As dialog or use the Downloads folder, depending on the visitor's settings.",
    ))

    local_files = _repository_mag_files(folder)
    if local_files:
      with st.expander(txt(
        "Fallback: arquivos também presentes no repositório",
        "Fallback: files also present in the repository",
      ), expanded=False):
        _repository_mag_download_panel_local_fallback(
          selected_mag=selected_mag,
          folder=folder,
          public_link=public_link,
          fasta=fasta,
          gbk=gbk,
        )
    return

  local_files = _repository_mag_files(folder)
  if local_files:
    st.warning(txt(
      "O MAG não foi localizado anonimamente no BV-BRC; usando a cópia presente no repositório como fallback.",
      "The MAG was not located anonymously in BV-BRC; using the repository copy as a fallback.",
    ))
    _repository_mag_download_panel_local_fallback(
      selected_mag=selected_mag,
      folder=folder,
      public_link=public_link,
      fasta=fasta,
      gbk=gbk,
    )
    return

  st.info(txt(
    f"{mag_id} não foi encontrado no catálogo público nem em `Annotation/{mag_id}/`.",
    f"{mag_id} was not found in the public catalogue or under `Annotation/{mag_id}/`.",
  ))
  if error:
    st.caption(error[:1500])

'''
    source = source[:panel_start] + replacement + source[panel_end + 1:]
