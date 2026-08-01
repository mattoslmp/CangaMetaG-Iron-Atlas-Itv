from __future__ import annotations

"""Self-contained visitor map that requires no tiles, Mapbox or topojson CDN."""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from .visitor_public_map import visitor_city_frame, visitor_country_frame


# Simplified deterministic continent outlines in longitude/latitude space. They
# are presentation geometry only; visitor markers always use persisted latitude
# and longitude values from the application log.
CONTINENTS = {
  "North America": [
    (-168, 15), (-160, 55), (-140, 72), (-105, 82), (-55, 60), (-52, 45),
    (-80, 25), (-98, 15), (-118, 22), (-130, 42), (-168, 15),
  ],
  "South America": [
    (-82, 12), (-66, 10), (-48, -5), (-35, -22), (-54, -56), (-72, -48),
    (-80, -15), (-82, 12),
  ],
  "Europe Asia": [
    (-12, 35), (5, 72), (42, 72), (80, 78), (135, 70), (178, 52),
    (155, 24), (115, 5), (78, 8), (55, 28), (28, 40), (8, 36), (-12, 35),
  ],
  "Africa": [
    (-18, 36), (10, 38), (35, 31), (52, 11), (42, -12), (28, -35),
    (7, -35), (-8, -5), (-18, 20), (-18, 36),
  ],
  "Australia": [
    (112, -11), (154, -10), (153, -39), (132, -44), (113, -35), (112, -11),
  ],
  "Greenland": [
    (-74, 59), (-18, 60), (-20, 83), (-55, 84), (-74, 59),
  ],
  "Antarctica": [
    (-180, -62), (-120, -72), (-60, -68), (0, -75), (60, -68),
    (120, -72), (180, -62), (180, -90), (-180, -90), (-180, -62),
  ],
}


def _add_background(figure: go.Figure) -> None:
  for name, points in CONTINENTS.items():
    figure.add_trace(go.Scatter(
      x=[point[0] for point in points],
      y=[point[1] for point in points],
      mode="lines",
      fill="toself",
      fillcolor="#E2E8F0" if name != "Antarctica" else "#F1F5F9",
      line={"color": "#94A3B8", "width": 0.8},
      hoverinfo="skip",
      showlegend=False,
      name=name,
    ))


def visitor_world_map_figure(visits: pd.DataFrame, txt) -> go.Figure:
  """Render a reliable Cartesian world map with real visitor coordinates."""
  countries = visitor_country_frame(visits)
  cities = visitor_city_frame(visits)
  figure = go.Figure()
  _add_background(figure)

  city_points = cities.dropna(subset=["Latitude", "Longitude"]).copy()
  if not city_points.empty:
    sizes = np.clip(
      10.0 + 4.0 * np.sqrt(city_points["Visits"].to_numpy(float)),
      12.0,
      36.0,
    )
    custom = city_points[[
      "City", "Region", "Country", "Flag", "Visits", "Unique visitors",
    ]].astype(object).to_numpy()
    figure.add_trace(go.Scatter(
      x=city_points["Longitude"].astype(float),
      y=city_points["Latitude"].astype(float),
      mode="markers",
      name=txt("Cidades dos visitantes", "Visitor cities"),
      marker={
        "size": sizes,
        "color": city_points["Visits"].astype(float),
        "colorscale": "YlOrRd",
        "showscale": True,
        "colorbar": {
          "title": {"text": txt("Visitas", "Visits")},
          "thickness": 14,
          "len": 0.62,
        },
        "opacity": 0.88,
        "line": {"color": "white", "width": 1.2},
      },
      customdata=custom,
      hovertemplate=(
        "<b>%{customdata[3]} %{customdata[0]}</b><br>"
        + txt("Região", "Region") + ": %{customdata[1]}<br>"
        + txt("País", "Country") + ": %{customdata[2]}<br>"
        + txt("Longitude", "Longitude") + ": %{x:.3f}<br>"
        + txt("Latitude", "Latitude") + ": %{y:.3f}<br>"
        + txt("Visitas", "Visits") + ": %{customdata[4]}<br>"
        + txt("Visitantes únicos", "Unique visitors") + ": %{customdata[5]}"
        + "<extra></extra>"
      ),
    ))

  if city_points.empty:
    figure.add_annotation(
      text=txt(
        "O mapa está ativo. Os marcadores aparecerão quando latitude e longitude forem registradas.",
        "The map is active. Markers will appear when latitude and longitude are recorded.",
      ),
      x=0.5,
      y=0.08,
      xref="paper",
      yref="paper",
      showarrow=False,
      bgcolor="rgba(255,255,255,0.88)",
      bordercolor="#CBD5E1",
      borderwidth=1,
      font={"size": 14, "color": "#334155"},
    )

  country_summary = " · ".join(
    f"{row['Flag']} {row['Country']}: {int(row['Visits'])}"
    for _, row in countries.head(8).iterrows()
  )
  if country_summary:
    figure.add_annotation(
      text=country_summary,
      x=0.5,
      y=-0.08,
      xref="paper",
      yref="paper",
      showarrow=False,
      font={"size": 12, "color": "#475569"},
    )

  figure.update_xaxes(
    range=[-180, 180],
    title=txt("Longitude", "Longitude"),
    tickmode="linear",
    dtick=30,
    showgrid=True,
    gridcolor="rgba(148,163,184,0.22)",
    zeroline=False,
    fixedrange=False,
  )
  figure.update_yaxes(
    range=[-90, 90],
    title=txt("Latitude", "Latitude"),
    tickmode="linear",
    dtick=30,
    showgrid=True,
    gridcolor="rgba(148,163,184,0.22)",
    zeroline=False,
    scaleanchor="x",
    scaleratio=1.0,
    fixedrange=False,
  )
  figure.update_layout(
    title={
      "text": txt(
        "Origem geográfica dos visitantes — mapa vetorial autônomo",
        "Visitor geographic origin — self-contained vector map",
      ),
      "x": 0.5,
      "xanchor": "center",
    },
    height=610,
    margin={"l": 35, "r": 35, "t": 75, "b": 95},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="#EFF6FF",
    hovermode="closest",
    legend={
      "orientation": "h",
      "x": 0.5,
      "xanchor": "center",
      "y": 1.01,
      "yanchor": "bottom",
    },
    meta={
      "self_contained_vector_map": True,
      "external_tiles_required": False,
      "external_topojson_required": False,
      "visitor_coordinates_from_persisted_log": True,
      "raw_ip_stored": False,
    },
  )
  return figure
