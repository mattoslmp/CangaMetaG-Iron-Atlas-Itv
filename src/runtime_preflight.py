from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any


_PATCH_STATE = {
  "overview_map_injected": False,
  "taxonomy_map_pending": False,
  "taxonomy_map_injected": False,
}


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
  if _PATCH_STATE["overview_map_injected"]:
    return
  _PATCH_STATE["overview_map_injected"] = True

  project_root = Path(__file__).resolve().parents[1]
  figure_path = project_root / "outputs" / "final_publication_figures" / "Figure1_sampling_map.png"
  root = getattr(st, "_main", st)
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

  root.markdown(f"### {title}")
  if figure_path.exists():
    root.image(str(figure_path), width="stretch", caption=caption)
  else:
    root.warning(missing)


def _render_taxonomy_sampling_map(st) -> None:
  if _PATCH_STATE["taxonomy_map_injected"]:
    return
  _PATCH_STATE["taxonomy_map_pending"] = False
  _PATCH_STATE["taxonomy_map_injected"] = True

  globals_dict, locals_dict = _caller_context()
  map_renderer = globals_dict.get("show_high_quality_sample_map")
  meta = locals_dict.get("meta")
  if callable(map_renderer) and meta is not None:
    map_renderer(meta, key="taxonomy_active_sampling_map")
    return

  message = (
    "Não foi possível carregar o mapa interativo das amostras nesta execução."
    if _is_portuguese()
    else "The interactive sampling map could not be loaded in this run."
  )
  st.warning(message)


def _install_streamlit_layout_hooks(st) -> None:
  if getattr(st, "_cangametag_sampling_layout_hooks", False):
    return

  original_download_button = st.download_button
  original_markdown = st.markdown
  original_expander = st.expander

  def download_button_wrapper(*args, **kwargs):
    result = original_download_button(*args, **kwargs)
    file_name = kwargs.get("file_name")
    if file_name is None and len(args) >= 3:
      file_name = args[2]
    file_name = str(file_name or "")
    if file_name == "article_sample_dates_coordinates.csv":
      _render_overview_sampling_figure(st)
    elif file_name == "taxonomy_sample_metadata.csv":
      _PATCH_STATE["taxonomy_map_pending"] = True
    return result

  def markdown_wrapper(*args, **kwargs):
    body = args[0] if args else kwargs.get("body", "")
    body_text = str(body)
    taxonomy_heading = (
      "Figuras taxonômicas finais usadas no artigo" in body_text
      or "Final taxonomy figures used in the article" in body_text
    )
    if _PATCH_STATE["taxonomy_map_pending"] and taxonomy_heading:
      _render_taxonomy_sampling_map(st)
    return original_markdown(*args, **kwargs)

  def expander_wrapper(label, *args, **kwargs):
    replacements = {
      "Amostras, datas, coordenadas e environment_feature": "Amostras, datas e coordenadas geográficas",
      "Samples, dates, coordinates and environment_feature": "Samples, collection dates and geographic coordinates",
    }
    return original_expander(replacements.get(str(label), label), *args, **kwargs)

  st.download_button = download_button_wrapper
  st.markdown = markdown_wrapper
  st.expander = expander_wrapper
  st._cangametag_sampling_layout_hooks = True


def streamlit_dependency_guard(st) -> None:
  """Validate optional packages and install the app-only sampling layout hooks."""
  _PATCH_STATE.update({
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
