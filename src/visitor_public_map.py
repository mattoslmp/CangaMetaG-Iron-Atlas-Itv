from __future__ import annotations

"""Canonical public visitor map and city table.

This module reads the persisted visitor log directly. It is intentionally
independent from the app's source-transform wrappers so the map, city points and
city table cannot disappear when another presentation transform is applied.
"""

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go


_UNKNOWN = {"", "unknown", "none", "nan", "xx", "zz", "n/a", "na"}


def _clean(value: object) -> str:
  text = str(value or "").strip()
  return "" if text.casefold() in _UNKNOWN else text


def _country_identity(name: object, code: object) -> tuple[str, str, str, str]:
  country_name = _clean(name)
  country_code = _clean(code).upper()
  alpha2 = country_code if len(country_code) == 2 else ""
  alpha3 = country_code if len(country_code) == 3 else ""
  try:
    import pycountry

    country = None
    if alpha2:
      country = pycountry.countries.get(alpha_2=alpha2)
    elif alpha3:
      country = pycountry.countries.get(alpha_3=alpha3)
    elif country_name:
      try:
        country = pycountry.countries.lookup(country_name)
      except LookupError:
        country = None
    if country is not None:
      alpha2 = str(country.alpha_2)
      alpha3 = str(country.alpha_3)
      country_name = str(country.name)
  except Exception:
    pass
  if not country_name:
    country_name = alpha2 or alpha3 or "Unknown"
  flag = "🌐"
  if len(alpha2) == 2 and alpha2.isalpha():
    try:
      flag = "".join(chr(127397 + ord(letter)) for letter in alpha2.upper())
    except Exception:
      flag = "🌐"
  return country_name, alpha2, alpha3, flag


def _visits_with_current_session(
  visits: pd.DataFrame,
  current_location: Mapping[str, Any] | None,
) -> pd.DataFrame:
  frame = visits.copy() if isinstance(visits, pd.DataFrame) else pd.DataFrame()
  location = dict(current_location or {})
  if not location:
    return frame
  recognised = any(
    _clean(location.get(field))
    for field in ("country_name", "country_code", "region", "city")
  ) or (
    location.get("latitude") is not None
    and location.get("longitude") is not None
  )
  if not recognised:
    return frame
  if not frame.empty:
    same_city = frame.get("city", pd.Series(dtype=str)).fillna("").astype(str).eq(
      str(location.get("city") or "")
    )
    same_country = frame.get(
      "country_code", pd.Series(dtype=str)
    ).fillna("").astype(str).str.upper().eq(
      str(location.get("country_code") or "").upper()
    )
    if bool((same_city & same_country).any()):
      return frame
  row = {
    "timestamp_utc": "current session",
    "visitor_id": "current-session",
    "page": "public_app",
    "country": location.get("country_name") or location.get("country_code") or "",
    "country_code": location.get("country_code") or "",
    "country_name": location.get("country_name") or "",
    "region": location.get("region") or "",
    "city": location.get("city") or "",
    "latitude": location.get("latitude"),
    "longitude": location.get("longitude"),
    "geolocation_source": location.get("geolocation_source") or "current session",
  }
  return pd.concat([frame, pd.DataFrame([row])], ignore_index=True, sort=False)


def visitor_country_frame(visits: pd.DataFrame) -> pd.DataFrame:
  columns = [
    "Country",
    "Country code",
    "ISO3",
    "Flag",
    "Visits",
    "Unique visitors",
    "Cities",
  ]
  if visits is None or visits.empty:
    return pd.DataFrame(columns=columns)
  work = visits.copy()
  for column in ("country_name", "country_code", "country", "city", "visitor_id"):
    if column not in work.columns:
      work[column] = ""
  identities = work.apply(
    lambda row: _country_identity(
      row.get("country_name") or row.get("country"),
      row.get("country_code"),
    ),
    axis=1,
    result_type="expand",
  )
  identities.columns = ["Country", "Country code", "ISO3", "Flag"]
  work = pd.concat([work.reset_index(drop=True), identities], axis=1)
  work = work[work["Country"].ne("Unknown")].copy()
  if work.empty:
    return pd.DataFrame(columns=columns)
  work["_city"] = work["city"].map(_clean)
  grouped = work.groupby(
    ["Country", "Country code", "ISO3", "Flag"],
    dropna=False,
  ).agg(
    Visits=("visitor_id", "size"),
    **{
      "Unique visitors": ("visitor_id", "nunique"),
      "Cities": ("_city", lambda values: int(pd.Series(values).replace("", np.nan).nunique(dropna=True))),
    },
  ).reset_index()
  return grouped[columns].sort_values(
    ["Visits", "Country"], ascending=[False, True]
  ).reset_index(drop=True)


def visitor_city_frame(visits: pd.DataFrame) -> pd.DataFrame:
  columns = [
    "Country",
    "Country code",
    "Flag",
    "Region",
    "City",
    "Latitude",
    "Longitude",
    "Visits",
    "Unique visitors",
  ]
  if visits is None or visits.empty:
    return pd.DataFrame(columns=columns)
  work = visits.copy()
  for column in (
    "country_name",
    "country_code",
    "country",
    "region",
    "city",
    "latitude",
    "longitude",
    "visitor_id",
  ):
    if column not in work.columns:
      work[column] = ""
  work["City"] = work["city"].map(_clean)
  work["Region"] = work["region"].map(_clean)
  work = work[work["City"].ne("")].copy()
  if work.empty:
    return pd.DataFrame(columns=columns)
  identities = work.apply(
    lambda row: _country_identity(
      row.get("country_name") or row.get("country"),
      row.get("country_code"),
    ),
    axis=1,
    result_type="expand",
  )
  identities.columns = ["Country", "Country code", "ISO3", "Flag"]
  work = pd.concat([work.reset_index(drop=True), identities], axis=1)
  work["Latitude"] = pd.to_numeric(work["latitude"], errors="coerce")
  work["Longitude"] = pd.to_numeric(work["longitude"], errors="coerce")
  grouped = work.groupby(
    ["Country", "Country code", "Flag", "Region", "City"],
    dropna=False,
  ).agg(
    Latitude=("Latitude", "mean"),
    Longitude=("Longitude", "mean"),
    Visits=("visitor_id", "size"),
    **{"Unique visitors": ("visitor_id", "nunique")},
  ).reset_index()
  return grouped[columns].sort_values(
    ["Visits", "Country", "City"],
    ascending=[False, True, True],
  ).reset_index(drop=True)


def visitor_world_map_figure(
  visits: pd.DataFrame,
  txt,
) -> go.Figure:
  countries = visitor_country_frame(visits)
  cities = visitor_city_frame(visits)
  figure = go.Figure()

  mapped_countries = countries[countries["ISO3"].astype(str).str.len().eq(3)].copy()
  if not mapped_countries.empty:
    custom = mapped_countries[[
      "Country",
      "Flag",
      "Unique visitors",
      "Cities",
    ]].astype(object).to_numpy()
    figure.add_trace(go.Choropleth(
      locations=mapped_countries["ISO3"],
      locationmode="ISO-3",
      z=mapped_countries["Visits"],
      customdata=custom,
      colorscale="Blues",
      autocolorscale=False,
      marker_line_color="rgba(71,85,105,0.55)",
      marker_line_width=0.55,
      colorbar={
        "title": {"text": txt("Visitas", "Visits")},
        "thickness": 14,
        "len": 0.68,
      },
      hovertemplate=(
        "<b>%{customdata[1]} %{customdata[0]}</b><br>"
        + txt("Visitas", "Visits") + ": %{z}<br>"
        + txt("Visitantes únicos", "Unique visitors") + ": %{customdata[2]}<br>"
        + txt("Cidades", "Cities") + ": %{customdata[3]}"
        + "<extra></extra>"
      ),
      name=txt("Visitas por país", "Visits by country"),
    ))

  city_points = cities.dropna(subset=["Latitude", "Longitude"]).copy()
  if not city_points.empty:
    sizes = np.clip(
      8.0 + 3.2 * np.sqrt(city_points["Visits"].to_numpy(float)),
      10.0,
      30.0,
    )
    custom = city_points[[
      "City",
      "Region",
      "Country",
      "Flag",
      "Visits",
      "Unique visitors",
    ]].astype(object).to_numpy()
    figure.add_trace(go.Scattergeo(
      lon=city_points["Longitude"],
      lat=city_points["Latitude"],
      mode="markers",
      name=txt("Cidades dos visitantes", "Visitor cities"),
      marker={
        "size": sizes,
        "color": "#D32F2F",
        "opacity": 0.82,
        "line": {"color": "white", "width": 1.1},
      },
      customdata=custom,
      hovertemplate=(
        "<b>%{customdata[3]} %{customdata[0]}</b><br>"
        + txt("Região", "Region") + ": %{customdata[1]}<br>"
        + txt("País", "Country") + ": %{customdata[2]}<br>"
        + txt("Visitas", "Visits") + ": %{customdata[4]}<br>"
        + txt("Visitantes únicos", "Unique visitors") + ": %{customdata[5]}"
        + "<extra></extra>"
      ),
    ))

  if mapped_countries.empty and city_points.empty:
    figure.add_annotation(
      text=txt(
        "O mapa será preenchido quando uma localização reconhecida for registrada.",
        "The map will be populated when a recognized location is recorded.",
      ),
      x=0.5,
      y=0.5,
      xref="paper",
      yref="paper",
      showarrow=False,
      font={"size": 16},
    )

  figure.update_geos(
    projection_type="natural earth",
    showframe=False,
    showcoastlines=True,
    coastlinecolor="rgba(71,85,105,0.55)",
    showcountries=True,
    countrycolor="rgba(100,116,139,0.42)",
    showland=True,
    landcolor="rgba(226,232,240,0.68)",
    showocean=True,
    oceancolor="rgba(219,234,254,0.48)",
    bgcolor="rgba(0,0,0,0)",
  )
  figure.update_layout(
    title={
      "text": txt(
        "Mapa de países e cidades dos visitantes",
        "Visitor country and city map",
      ),
      "x": 0.5,
      "xanchor": "center",
    },
    height=570,
    margin={"l": 0, "r": 0, "t": 74, "b": 62},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    legend={
      "orientation": "h",
      "x": 0.5,
      "xanchor": "center",
      "y": -0.03,
      "yanchor": "top",
    },
    meta={
      "visitor_country_choropleth": True,
      "visitor_city_points": True,
      "raw_ip_stored": False,
    },
  )
  return figure


def render_public_visitor_footer(
  namespace: Mapping[str, Any],
  key: str = "public_footer",
) -> None:
  st = namespace["st"]
  txt = namespace["txt"]
  show_table = namespace["show_table"]
  csv_button = namespace["csv_button"]
  record_visit = namespace["record_visit"]
  load_visits = namespace["load_visitor_visits"]

  try:
    record_visit(
      st,
      str(namespace.get("APP_VERSION", "")),
      str(namespace.get("DATABASE_VERSION", "")),
      page="public_app",
    )
  except Exception:
    pass

  try:
    current_location = dict(
      st.session_state.get("_visitor_last_location", {}) or {}
    )
  except Exception:
    current_location = {}
  visits = _visits_with_current_session(load_visits(), current_location)
  countries = visitor_country_frame(visits)
  cities = visitor_city_frame(visits)
  total_visits = int(len(visits))
  unique_visitors = (
    int(visits["visitor_id"].astype(str).nunique())
    if not visits.empty and "visitor_id" in visits.columns
    else 0
  )

  st.divider()
  st.markdown(
    "### " + txt(
      "Origem geográfica dos visitantes",
      "Visitor geographic origin",
    )
  )
  m1, m2, m3, m4 = st.columns(4)
  m1.metric(txt("Visitas", "Visits"), total_visits)
  m2.metric(txt("Visitantes únicos", "Unique visitors"), unique_visitors)
  m3.metric(txt("Países", "Countries"), len(countries))
  m4.metric(txt("Cidades", "Cities"), len(cities))

  st.plotly_chart(
    visitor_world_map_figure(visits, txt),
    width="stretch",
    key=f"{key}_canonical_world_city_map",
    config={
      "displaylogo": False,
      "responsive": True,
      "scrollZoom": False,
    },
  )

  st.markdown("#### " + txt("Cidades dos visitantes", "Visitor cities"))
  if cities.empty:
    st.info(txt(
      "As visitas foram contadas, mas ainda não há uma cidade reconhecida nos cabeçalhos ou na geolocalização por IP. Novas visitas serão consultadas automaticamente por múltiplos provedores.",
      "Visits were counted, but no city has yet been recognized from headers or IP geolocation. New visits will be checked automatically through multiple providers.",
    ))
  else:
    city_display = cities.rename(columns={
      "Country": txt("País", "Country"),
      "Country code": txt("Código do país", "Country code"),
      "Flag": txt("Bandeira", "Flag"),
      "Region": txt("Região", "Region"),
      "City": txt("Cidade", "City"),
      "Latitude": "Latitude",
      "Longitude": "Longitude",
      "Visits": txt("Visitas", "Visits"),
      "Unique visitors": txt("Visitantes únicos", "Unique visitors"),
    })
    show_table(
      city_display,
      f"{key}_canonical_visitor_cities",
      height=min(560, 120 + 38 * len(city_display)),
    )
    csv_button(
      city_display,
      "visitor_cities.csv",
      txt("Baixar cidades dos visitantes", "Download visitor cities"),
      key=f"{key}_download_visitor_cities",
    )

  with st.expander(
    txt("Visitas por país", "Visits by country"),
    expanded=False,
  ):
    if countries.empty:
      st.info(txt(
        "Ainda não há países reconhecidos.",
        "No countries have been recognized yet.",
      ))
    else:
      country_display = countries.rename(columns={
        "Country": txt("País", "Country"),
        "Country code": txt("Código do país", "Country code"),
        "ISO3": "ISO3",
        "Flag": txt("Bandeira", "Flag"),
        "Visits": txt("Visitas", "Visits"),
        "Unique visitors": txt("Visitantes únicos", "Unique visitors"),
        "Cities": txt("Cidades", "Cities"),
      })
      show_table(
        country_display,
        f"{key}_canonical_visitor_countries",
        height=min(520, 120 + 38 * len(country_display)),
      )
      csv_button(
        country_display,
        "visitor_countries.csv",
        txt("Baixar visitas por país", "Download visits by country"),
        key=f"{key}_download_visitor_countries",
      )

  location_bits = [
    _clean(current_location.get("city")),
    _clean(current_location.get("region")),
    _clean(
      current_location.get("country_name")
      or current_location.get("country_code")
    ),
  ]
  location_bits = [value for value in location_bits if value]
  if location_bits:
    st.caption(txt(
      "Localização aproximada desta sessão: " + ", ".join(location_bits) + ".",
      "Approximate location for this session: " + ", ".join(location_bits) + ".",
    ))
