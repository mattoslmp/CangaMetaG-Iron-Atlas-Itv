from __future__ import annotations

"""Display-only localization helpers for scientific figures.

The functions in this module translate titles, axes, legends, annotations,
hover text and control labels. Numeric arrays, coordinates, statistics, colours,
trace order and source tables are never changed.
"""

from copy import deepcopy
import base64
import re

import plotly.graph_objects as go


_PT_REPLACEMENTS = {
  "Bacteria phylum-level taxonomic profiles": "Perfis taxonômicos de Bacteria em nível de filo",
  "Archaea phylum-level taxonomic profiles": "Perfis taxonômicos de Archaea em nível de filo",
  "Bacteria genus-level taxonomic profiles and ordination": "Perfis taxonômicos de Bacteria em nível de gênero e ordenação",
  "Archaea genus-level taxonomic profiles and ordination": "Perfis taxonômicos de Archaea em nível de gênero e ordenação",
  "Dry-season genus profiles": "Perfis de gêneros — estação seca",
  "Rainy-season genus profiles": "Perfis de gêneros — estação chuvosa",
  "Dry season": "Estação seca",
  "Rainy season": "Estação chuvosa",
  "Relative abundance (%)": "Abundância relativa (%)",
  "Relative abundance": "Abundância relativa",
  "CDS-classified sediment sample": "Amostra de sedimento classificada por CDS",
  "Bray-Curtis NMDS": "NMDS de Bray–Curtis",
  "RDA biplot": "Biplot de RDA",
  "constrained variation": "variação restrita",
  "Lake / season": "Lagoa / estação",
  "Lake/season": "Lagoa/estação",
  "RDA vectors": "Vetores da RDA",
  "Environmental variable": "Variável ambiental",
  "Representative genus vector": "Vetor de gênero representativo",
  "representative genus": "gênero representativo",
  "environmental variable": "variável ambiental",
  "NMDS symbols": "Símbolos do NMDS",
  "Other taxa (<5% each)": "Outros táxons (<5% cada)",
  "Other genera (<5% each)": "Outros gêneros (<5% cada)",
  "Other taxa": "Outros táxons",
  "Other genera": "Outros gêneros",
  "Unclassified": "Não classificado",
  "Relative abundance heatmap": "Heatmap de abundância relativa",
  "Barplot by individual sample": "Gráfico de barras por amostra individual",
  "Individual samples": "Amostras individuais",
  "Aggregated lake-season groups": "Grupos agregados por lagoa–estação",
  "Aggregated lake–season": "Lagoa–estação agregada",
  "Alpha diversity": "Diversidade alfa",
  "Plotted values": "Valores plotados",
  "Processed": "Processado",
  "Source": "Fonte",
  "Output": "Saída",
  "Figure": "Figura",
  "Supplementary Figure": "Figura Suplementar",
  "Phylum": "Filo",
  "Class": "Classe",
  "Order": "Ordem",
  "Family": "Família",
  "Genus": "Gênero",
  "Species": "Espécie",
  "Sample": "Amostra",
  "Site": "Sítio",
  "Lake": "Lagoa",
  "Season": "Estação",
  "Dry": "Seca",
  "Rainy": "Chuvosa",
  "solid": "contínuo",
  "dashed": "tracejado",
  "Download": "Baixar",
}


def normalize_language(language: object) -> str:
  value = str(language or "en").strip().casefold()
  return "pt" if value.startswith("pt") or "portugu" in value else "en"


def translate_figure_text(value: object, language: object = "en") -> object:
  """Translate only known presentation phrases, preserving scientific names."""
  if normalize_language(language) != "pt" or value is None:
    return value
  text = str(value)
  # Longer phrases must be replaced before their component words.
  for english, portuguese in sorted(
    _PT_REPLACEMENTS.items(), key=lambda item: len(item[0]), reverse=True
  ):
    text = text.replace(english, portuguese)
  # Remaining standalone UI words. Word boundaries avoid changing taxon names.
  standalone = {
    "Dry": "Seca",
    "Rainy": "Chuvosa",
    "Figure": "Figura",
    "Sample": "Amostra",
    "Lake": "Lagoa",
    "Season": "Estação",
    "Site": "Sítio",
  }
  for english, portuguese in standalone.items():
    text = re.sub(rf"\b{re.escape(english)}\b", portuguese, text)
  return text


def _translate_svg_data_uri(source: object, language: str) -> object:
  if normalize_language(language) != "pt" or not isinstance(source, str):
    return source
  prefix = "data:image/svg+xml;base64,"
  if not source.startswith(prefix):
    return source
  try:
    payload = base64.b64decode(source[len(prefix):]).decode("utf-8")
    localized = translate_figure_text(payload, "pt")
    return prefix + base64.b64encode(localized.encode("utf-8")).decode("ascii")
  except Exception:
    return source


def localize_plotly_figure(fig, language: object = "en"):
  """Return a translated Plotly copy without modifying scientific values."""
  lang = normalize_language(language)
  if lang != "pt" or fig is None:
    return fig
  localized = go.Figure(fig)

  title = getattr(getattr(localized.layout, "title", None), "text", None)
  if title is not None:
    localized.layout.title.text = translate_figure_text(title, lang)
  legend_title = getattr(getattr(localized.layout, "legend", None), "title", None)
  if legend_title is not None and getattr(legend_title, "text", None) is not None:
    localized.layout.legend.title.text = translate_figure_text(legend_title.text, lang)

  for axis_prefix in ("xaxis", "yaxis"):
    for index in range(1, 100):
      axis_name = axis_prefix if index == 1 else f"{axis_prefix}{index}"
      axis = getattr(localized.layout, axis_name, None)
      if axis is None:
        continue
      axis_title = getattr(getattr(axis, "title", None), "text", None)
      if axis_title is not None:
        axis.title.text = translate_figure_text(axis_title, lang)

  for annotation in list(localized.layout.annotations or []):
    if getattr(annotation, "text", None) is not None:
      annotation.text = translate_figure_text(annotation.text, lang)

  for image in list(localized.layout.images or []):
    image.source = _translate_svg_data_uri(getattr(image, "source", None), lang)

  for menu in list(localized.layout.updatemenus or []):
    for button in list(getattr(menu, "buttons", None) or []):
      if getattr(button, "label", None) is not None:
        button.label = translate_figure_text(button.label, lang)
  for slider in list(localized.layout.sliders or []):
    current = getattr(slider, "currentvalue", None)
    if current is not None and getattr(current, "prefix", None) is not None:
      current.prefix = translate_figure_text(current.prefix, lang)
    for step in list(getattr(slider, "steps", None) or []):
      if getattr(step, "label", None) is not None:
        step.label = translate_figure_text(step.label, lang)

  for trace in localized.data:
    if getattr(trace, "name", None) is not None:
      trace.name = translate_figure_text(trace.name, lang)
    if getattr(trace, "hovertemplate", None) is not None:
      trace.hovertemplate = translate_figure_text(trace.hovertemplate, lang)
    if getattr(trace, "texttemplate", None) is not None:
      trace.texttemplate = translate_figure_text(trace.texttemplate, lang)
    colorbar = getattr(trace, "colorbar", None)
    if colorbar is not None:
      colorbar_title = getattr(getattr(colorbar, "title", None), "text", None)
      if colorbar_title is not None:
        colorbar.title.text = translate_figure_text(colorbar_title, lang)
    marker = getattr(trace, "marker", None)
    marker_colorbar = getattr(marker, "colorbar", None) if marker is not None else None
    if marker_colorbar is not None:
      marker_title = getattr(getattr(marker_colorbar, "title", None), "text", None)
      if marker_title is not None:
        marker_colorbar.title.text = translate_figure_text(marker_title, lang)

  meta = dict(localized.layout.meta) if isinstance(localized.layout.meta, dict) else {}
  meta.update({
    "display_language": "pt",
    "scientific_values_translated": False,
    "display_text_translated_only": True,
  })
  localized.update_layout(meta=meta)
  return localized
