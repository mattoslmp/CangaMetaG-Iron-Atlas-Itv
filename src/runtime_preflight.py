from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any, Callable


_PATCH_STATE = {
  "overview_map_pending": False,
  "overview_map_injected": False,
  "taxonomy_map_pending": False,
  "taxonomy_map_injected": False,
}


class _ExitHookContext:
  """Proxy a Streamlit context and run a callback after its container closes."""

  def __init__(self, context: Any, after_exit: Callable[[], None] | None = None) -> None:
    self._context = context
    self._after_exit = after_exit

  def __enter__(self):
    return self._context.__enter__()

  def __exit__(self, exc_type, exc_value, traceback):
    result = self._context.__exit__(exc_type, exc_value, traceback)
    if exc_type is None and self._after_exit is not None:
      self._after_exit()
    return result

  def __getattr__(self, name: str):
    return getattr(self._context, name)


def _caller_context() -> tuple[dict[str, Any], dict[str, Any]]:
  """Return the nearest application globals and locals on the current stack."""
  frame = inspect.currentframe()
  try:
    frame = frame.f_back if frame is not None else None
    while frame is not None:
      globals_dict = frame.f_globals
      if "show_high_quality_sample_map" in globals_dict or "IS_PT" in globals_dict:
        return globals_dict, frame.f_locals
      frame = frame.f_back
  finally:
    del frame
  return {}, {}


def _is_portuguese() -> bool:
  globals_dict, _ = _caller_context()
  return bool(globals_dict.get("IS_PT", False))


def _render_overview_sampling_figure(st) -> None:
  if not _PATCH_STATE["overview_map_pending"] or _PATCH_STATE["overview_map_injected"]:
    return
  _PATCH_STATE["overview_map_pending"] = False
  _PATCH_STATE["overview_map_injected"] = True

  project_root = Path(__file__).resolve().parents[1]
  figure_path = project_root / "outputs" / "final_publication_figures" / "Figure1_sampling_map.png"
  if _is_portuguese():
    title = "Área de estudo e desenho amostral"
    caption = (
      "Área de estudo e desenho amostral. Localização das lagoas lateríticas "
      "amazônicas Amendoim, Violão, Três Irmãs e Três Irmãs Adjacent. O estudo "
      "inclui 20 metagenomas de sedimento, compreendendo 10 amostras do período "
      "seco e 10 do período chuvoso."
    )
    missing = "A Figura 1 do mapa amostral não foi encontrada no diretório canônico de figuras finais."
  else:
    title = "Study area and sampling design"
    caption = (
      "Study area and sampling design. Location of the Amazonian lateritic lakes "
      "Amendoim, Violão, Três Irmãs and Três Irmãs Adjacent. The study includes "
      "20 sediment metagenomes, comprising 10 dry-season and 10 rainy-season samples."
    )
    missing = "Figure 1 sampling map was not found in the canonical final-figures directory."

  st.markdown(f"### {title}")
  if figure_path.exists():
    st.image(str(figure_path), width="stretch", caption=caption)
  else:
    st.warning(missing)


def _render_taxonomy_sampling_map(st) -> None:
  if not _PATCH_STATE["taxonomy_map_pending"] or _PATCH_STATE["taxonomy_map_injected"]:
    return
  _PATCH_STATE["taxonomy_map_pending"] = False
  _PATCH_STATE["taxonomy_map_injected"] = True

  globals_dict, locals_dict = _caller_context()
  map_renderer = globals_dict.get("show_high_quality_sample_map")
  meta = locals_dict.get("meta")
  if callable(map_renderer) and meta is not None:
    map_renderer(meta, key="taxonomy_sampling_map_after_metadata_v3")
    return

  message = (
    "Não foi possível carregar o mapa interativo das amostras nesta execução."
    if _is_portuguese()
    else "The interactive sampling map could not be loaded in this run."
  )
  st.warning(message)


def _root_streamlit_callable(st, name: str):
  """Return an unwrapped DeltaGenerator method whenever Streamlit exposes it."""
  root = getattr(st, "_main", None)
  candidate = getattr(root, name, None) if root is not None else None
  if callable(candidate):
    return candidate
  return getattr(st, name)


def _install_streamlit_layout_hooks(st) -> None:
  """Install exactly one hook layer, even after Streamlit hot reloads.

  Older app revisions replaced module-level Streamlit functions without restoring
  them. During a hot reload, a new wrapper could therefore wrap the previous
  wrapper and render the Taxonomy map twice with the same Plotly key. Rebinding
  from ``st._main`` first discards every stale wrapper before the current hooks
  are installed.
  """
  original_markdown = _root_streamlit_callable(st, "markdown")
  original_download_button = _root_streamlit_callable(st, "download_button")
  original_expander = _root_streamlit_callable(st, "expander")
  original_columns = _root_streamlit_callable(st, "columns")

  # Remove wrappers left in the Streamlit module by previous hot-loaded code.
  st.markdown = original_markdown
  st.download_button = original_download_button
  st.expander = original_expander
  st.columns = original_columns

  def download_button_wrapper(*args, **kwargs):
    result = original_download_button(*args, **kwargs)
    file_name = kwargs.get("file_name")
    if file_name is None and len(args) >= 3:
      file_name = args[2]
    file_name = str(file_name or "")
    if file_name == "article_sample_dates_coordinates.csv":
      _PATCH_STATE["overview_map_pending"] = True
    elif file_name == "taxonomy_sample_metadata.csv":
      _PATCH_STATE["taxonomy_map_pending"] = True
    return result

  def expander_wrapper(label, *args, **kwargs):
    replacements = {
      "Amostras, datas, coordenadas e environment_feature": "Amostras, datas e coordenadas geográficas",
      "Samples, dates, coordinates and environment_feature": "Samples, collection dates and geographic coordinates",
    }
    visible_label = replacements.get(str(label), label)
    context = original_expander(visible_label, *args, **kwargs)
    if str(visible_label) in replacements.values():
      return _ExitHookContext(context, lambda: _render_taxonomy_sampling_map(st))
    return context

  def columns_wrapper(*args, **kwargs):
    columns = original_columns(*args, **kwargs)
    return [
      _ExitHookContext(column, lambda: _render_overview_sampling_figure(st))
      for column in columns
    ]

  st.download_button = download_button_wrapper
  st.expander = expander_wrapper
  st.columns = columns_wrapper
  st._cangametag_sampling_layout_hook_version = 3


def streamlit_dependency_guard(st) -> None:
  """Validate optional packages and install non-duplicating layout hooks."""
  _PATCH_STATE.update({
    "overview_map_pending": False,
    "overview_map_injected": False,
    "taxonomy_map_pending": False,
    "taxonomy_map_injected": False,
  })
  _install_streamlit_layout_hooks(st)

  optional = {
    "openpyxl": "Excel previews",
    "Bio": "FASTA/GenBank parsing",
    "statsmodels": "some statistical summaries",
  }
  missing = [label for module, label in optional.items() if importlib.util.find_spec(module) is None]
  if missing:
    try:
      st.warning("Optional components unavailable: " + ", ".join(missing))
    except Exception:
      pass
