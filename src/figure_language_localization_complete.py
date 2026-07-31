from __future__ import annotations

"""Complete display-only localization for Plotly scientific figures.

This module extends the core localization layer to presentation fields that are
not covered by the basic helper, including trace text arrays, hover-text arrays,
pie labels, 3D scenes, polar/ternary axes and shared color axes. Scientific
arrays, custom data, coordinates, statistics, colours and trace order are never
modified.
"""

from collections.abc import Iterable

import plotly.graph_objects as go

from .figure_language_localization import (
  localize_plotly_figure as _base_localize_plotly_figure,
  normalize_language,
  translate_figure_text,
)


def _localized_sequence(value: object, language: str) -> object:
  """Translate strings in a presentation sequence without touching numbers."""
  if value is None or isinstance(value, str):
    return translate_figure_text(value, language)
  if not isinstance(value, Iterable) or isinstance(value, (bytes, bytearray, dict)):
    return value
  try:
    values = list(value)
  except TypeError:
    return value
  return [
    translate_figure_text(item, language) if isinstance(item, str) else item
    for item in values
  ]


def _translate_axis_title(axis: object, language: str) -> None:
  title = getattr(axis, "title", None)
  if title is not None and getattr(title, "text", None) is not None:
    title.text = translate_figure_text(title.text, language)


def _translate_colorbar_title(colorbar: object, language: str) -> None:
  title = getattr(colorbar, "title", None)
  if title is not None and getattr(title, "text", None) is not None:
    title.text = translate_figure_text(title.text, language)


def localize_plotly_figure(fig, language: object = "en"):
  """Return a fully localized Plotly copy while preserving scientific values."""
  lang = normalize_language(language)
  localized = _base_localize_plotly_figure(fig, lang)
  if lang != "pt" or localized is None:
    return localized

  localized = go.Figure(localized)

  # Trace-level visible strings. Numeric arrays and customdata are untouched.
  for trace in localized.data:
    for attribute in ("text", "hovertext", "labels"):
      current = getattr(trace, attribute, None)
      if current is not None:
        setattr(trace, attribute, _localized_sequence(current, lang))

  # Shared continuous color scales.
  for index in range(1, 30):
    name = "coloraxis" if index == 1 else f"coloraxis{index}"
    coloraxis = getattr(localized.layout, name, None)
    if coloraxis is not None:
      _translate_colorbar_title(getattr(coloraxis, "colorbar", None), lang)

  # Three-dimensional scenes.
  for index in range(1, 30):
    name = "scene" if index == 1 else f"scene{index}"
    scene = getattr(localized.layout, name, None)
    if scene is None:
      continue
    for axis_name in ("xaxis", "yaxis", "zaxis"):
      _translate_axis_title(getattr(scene, axis_name, None), lang)

  # Polar plots.
  for index in range(1, 30):
    name = "polar" if index == 1 else f"polar{index}"
    polar = getattr(localized.layout, name, None)
    if polar is None:
      continue
    _translate_axis_title(getattr(polar, "radialaxis", None), lang)
    _translate_axis_title(getattr(polar, "angularaxis", None), lang)

  # Ternary plots.
  for index in range(1, 30):
    name = "ternary" if index == 1 else f"ternary{index}"
    ternary = getattr(localized.layout, name, None)
    if ternary is None:
      continue
    for axis_name in ("aaxis", "baxis", "caxis"):
      _translate_axis_title(getattr(ternary, axis_name, None), lang)

  meta = dict(localized.layout.meta) if isinstance(localized.layout.meta, dict) else {}
  meta.update({
    "display_language": "pt",
    "complete_display_localization": True,
    "scientific_values_translated": False,
    "display_text_translated_only": True,
  })
  localized.update_layout(meta=meta)
  return localized
