from __future__ import annotations

from pathlib import Path

import numpy as np
import plotly.graph_objects as go

from src.figure_language_localization_complete import localize_plotly_figure


ROOT = Path(__file__).resolve().parents[1]


def test_complete_localization_preserves_scientific_arrays() -> None:
  figure = go.Figure()
  figure.add_trace(go.Bar(
    x=[12.5, 87.5],
    y=["AM.P1.D", "AM.P1.R"],
    text=["Dry", "Rainy"],
    hovertext=["Dry season", "Rainy season"],
    name="Other taxa (<5% each)",
    hovertemplate=(
      "Sample: %{y}<br>Relative abundance: %{x:.2f}%"
      "<br>Season: Dry<extra></extra>"
    ),
  ))
  figure.update_layout(
    title="Bray-Curtis NMDS (stress = 0.123)",
    xaxis_title="Relative abundance (%)",
    legend_title="Phylum",
    coloraxis_colorbar_title="Percentage",
  )

  localized = localize_plotly_figure(figure, "pt")

  assert np.array_equal(np.asarray(localized.data[0].x), np.asarray(figure.data[0].x))
  assert np.array_equal(np.asarray(localized.data[0].y), np.asarray(figure.data[0].y))
  assert list(localized.data[0].text) == ["Seca", "Chuvosa"]
  assert list(localized.data[0].hovertext) == ["Estação seca", "Estação chuvosa"]
  assert localized.data[0].name == "Outros táxons (<5% cada)"
  assert "estresse = 0.123" in localized.layout.title.text
  assert localized.layout.xaxis.title.text == "Abundância relativa (%)"
  assert localized.layout.legend.title.text == "Filo"
  assert localized.layout.coloraxis.colorbar.title.text == "Porcentagem"
  assert localized.layout.meta["complete_display_localization"] is True
  assert localized.layout.meta["scientific_values_translated"] is False


def test_complete_language_transform_is_loaded_after_base_language_layer() -> None:
  app = (ROOT / "app.py").read_text(encoding="utf-8")
  base = app.index("app_full_figure_language_transform.py")
  complete = app.index("app_complete_plotly_language_transform.py")
  static = app.index("app_static_figure_renderer_recovery_transform.py")
  runtime = app.index("app_runtime_name_guard_transform.py")
  assert base < complete < static < runtime


def test_complete_transform_sets_selected_plotly_locale() -> None:
  transform = (
    ROOT / "src" / "app_complete_plotly_language_transform.py"
  ).read_text(encoding="utf-8")
  assert '"pt-BR" if IS_PT else "en"' in transform
  assert "complete_localize_plotly_figure" in transform
