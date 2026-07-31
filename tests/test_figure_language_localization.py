from __future__ import annotations

from pathlib import Path
import runpy

import numpy as np
import plotly.graph_objects as go

from src.figure_language_localization import localize_plotly_figure


ROOT = Path(__file__).resolve().parents[1]


def test_plotly_localization_changes_only_display_text() -> None:
  original = go.Figure()
  original.add_trace(go.Bar(
    x=[12.5, 87.5],
    y=["AM.P1.D", "AM.P1.R"],
    name="Other taxa (<5% each)",
    hovertemplate=(
      "Sample: %{y}<br>Relative abundance: %{x:.2f}%"
      "<br>Season: Dry<extra></extra>"
    ),
  ))
  original.update_layout(
    title="Bacteria phylum-level taxonomic profiles",
    xaxis_title="Relative abundance (%)",
    yaxis_title="CDS-classified sediment sample",
    legend_title="Phylum",
    annotations=[dict(
      x=0.5,
      y=1.1,
      xref="paper",
      yref="paper",
      text="A  Dry season",
      showarrow=False,
    )],
  )

  localized = localize_plotly_figure(original, "pt")

  assert np.array_equal(np.asarray(localized.data[0].x), np.asarray(original.data[0].x))
  assert np.array_equal(np.asarray(localized.data[0].y), np.asarray(original.data[0].y))
  assert original.layout.title.text == "Bacteria phylum-level taxonomic profiles"
  assert localized.layout.title.text == "Perfis taxonômicos de Bacteria em nível de filo"
  assert localized.layout.xaxis.title.text == "Abundância relativa (%)"
  assert localized.layout.yaxis.title.text == "Amostra de sedimento classificada por CDS"
  assert localized.layout.legend.title.text == "Filo"
  assert localized.data[0].name == "Outros táxons (<5% cada)"
  assert "Amostra:" in localized.data[0].hovertemplate
  assert "Estação: Seca" in localized.data[0].hovertemplate
  assert "Estação seca" in localized.layout.annotations[0].text
  assert localized.layout.meta["display_text_translated_only"] is True
  assert localized.layout.meta["scientific_values_translated"] is False


def test_english_localization_returns_original_figure() -> None:
  figure = go.Figure(go.Scatter(x=[1.0, 2.0], y=[3.0, 4.0]))
  returned = localize_plotly_figure(figure, "en")
  assert returned is figure


def test_full_language_transform_compiles() -> None:
  synthetic = '''from __future__ import annotations


def render_plotly_downloadable(fig, *args, **kwargs):
  return fig


def exact_article_phylum_interactive(domain, language="en"):
  return figure, table, svg


def article_frozen_taxonomy_figure(domain):
  return figure, tables


def _static_figure_manifest_record(path):
  return {}

page_handler = page_handlers.get(selected_page)
'''
  transformed = runpy.run_path(
    str(ROOT / "src" / "app_full_figure_language_transform.py"),
    init_globals={"source": synthetic},
  )["source"]
  compile(transformed, "synthetic_full_language.py", "exec")
  assert "final_localize_plotly_figure" in transformed
  assert 'return "pt" if IS_PT else "en"' in transformed
  assert "Bacteria — Figura 4" in transformed or "_selected_figure_language" in transformed


def test_static_generators_include_both_language_labels() -> None:
  phylum = (
    ROOT / "src" / "article_exact_taxonomy_phylum_other_percentage.py"
  ).read_text(encoding="utf-8")
  ordination = (
    ROOT / "src" / "article_frozen_taxonomy_static_bilingual.py"
  ).read_text(encoding="utf-8")
  assert "Outros táxons" in phylum
  assert "Other taxa" in phylum
  assert "Perfis taxonômicos de Bacteria" in phylum
  assert "Bacteria phylum-level taxonomic profiles" in phylum
  assert "Vetores da RDA" in ordination
  assert "RDA vectors" in ordination
  assert "Abundância relativa (%)" in ordination
  assert "Relative abundance (%)" in ordination
