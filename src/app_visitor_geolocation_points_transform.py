from __future__ import annotations

"""Add approximate city/region points to the visitor world map."""

MARKER = "CANGAMETAG_VISITOR_GEOLOCATION_POINTS_V1 = 1"

if MARKER not in source:
  anchor = "def site_access_gate"
  wrapper = r'''
_APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE = _visitor_world_map_figure


def _visitor_geolocation_point_frame() -> pd.DataFrame:
  visits = load_visitor_visits()
  columns = [
    "country_name", "region", "city", "latitude", "longitude",
    "Visits", "Unique visitors",
  ]
  if not isinstance(visits, pd.DataFrame) or visits.empty:
    return pd.DataFrame(columns=columns)
  work = visits.copy()
  for coordinate in ("latitude", "longitude"):
    if coordinate not in work.columns:
      work[coordinate] = np.nan
    work[coordinate] = pd.to_numeric(work[coordinate], errors="coerce")
  work = work.dropna(subset=["latitude", "longitude"])
  if work.empty:
    return pd.DataFrame(columns=columns)
  for column in ("country_name", "region", "city"):
    if column not in work.columns:
      work[column] = ""
    work[column] = work[column].fillna("").astype(str).str.strip()
  if "country_code" in work.columns:
    work["country_name"] = work["country_name"].where(
      work["country_name"].ne(""),
      work["country_code"].fillna("").astype(str),
    )
  if "visitor_id" not in work.columns:
    work["visitor_id"] = np.arange(len(work)).astype(str)
  grouped = work.groupby(
    ["country_name", "region", "city", "latitude", "longitude"],
    dropna=False,
  ).agg(
    **{
      "Visits": ("visitor_id", "size"),
      "Unique visitors": ("visitor_id", "nunique"),
    }
  ).reset_index()
  return grouped.sort_values(
    ["Visits", "country_name", "city"],
    ascending=[False, True, True],
  ).reset_index(drop=True)


def _visitor_world_map_figure(country_frame: pd.DataFrame):
  figure = _APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE(country_frame)
  points = _visitor_geolocation_point_frame()
  if points.empty:
    return figure
  marker_size = np.clip(
    7.0 + 3.0 * np.sqrt(points["Visits"].to_numpy(float)),
    9.0,
    28.0,
  )
  custom = points[[
    "city", "region", "country_name", "Visits", "Unique visitors"
  ]].astype(object).to_numpy()
  figure.add_trace(go.Scattergeo(
    lon=points["longitude"].astype(float),
    lat=points["latitude"].astype(float),
    mode="markers",
    name=txt("Localizações aproximadas", "Approximate locations"),
    marker={
      "size": marker_size,
      "color": "#D32F2F",
      "opacity": 0.78,
      "line": {"color": "white", "width": 1.1},
    },
    customdata=custom,
    hovertemplate=(
      "<b>%{customdata[0]}</b><br>"
      + txt("Região", "Region") + ": %{customdata[1]}<br>"
      + txt("País", "Country") + ": %{customdata[2]}<br>"
      + txt("Visitas", "Visits") + ": %{customdata[3]}<br>"
      + txt("Visitantes únicos", "Unique visitors") + ": %{customdata[4]}"
      + "<extra></extra>"
    ),
  ))
  figure.update_layout(
    legend={
      "orientation": "h",
      "x": 0.5,
      "xanchor": "center",
      "y": -0.02,
      "yanchor": "top",
    },
    margin={"l": 0, "r": 0, "t": 70, "b": 55},
    meta={
      "visitor_country_choropleth": True,
      "visitor_city_points": True,
      "raw_ip_stored": False,
    },
  )
  return figure
'''
  if anchor in source and "_APP_ORIGINAL_VISITOR_WORLD_MAP_FIGURE" not in source:
    source = source.replace(anchor, wrapper + "\n\n" + anchor, 1)
  source += f"\n\n{MARKER}\n"
