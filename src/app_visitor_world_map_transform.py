from __future__ import annotations


MARKER = "def _visitor_world_map_frame("

if MARKER not in source:
  footer_start = source.find("def visitor_counter_public_footer(")
  footer_end = source.find("\ndef visitor_counter_compact(", footer_start)
  if footer_start >= 0 and footer_end >= 0:
    replacement = r'''VISITOR_COUNTRY_NAME_OVERRIDES = {
  "Bolivia, Plurinational State of": "Bolivia",
  "Brunei Darussalam": "Brunei",
  "Congo": "Republic of the Congo",
  "Congo, The Democratic Republic of the": "Democratic Republic of the Congo",
  "Iran, Islamic Republic of": "Iran",
  "Korea, Democratic People's Republic of": "North Korea",
  "Korea, Republic of": "South Korea",
  "Lao People's Democratic Republic": "Laos",
  "Moldova, Republic of": "Moldova",
  "Palestine, State of": "Palestine",
  "Russian Federation": "Russia",
  "Syrian Arab Republic": "Syria",
  "Taiwan, Province of China": "Taiwan",
  "Tanzania, United Republic of": "Tanzania",
  "United States of America": "United States",
  "Venezuela, Bolivarian Republic of": "Venezuela",
  "Viet Nam": "Vietnam",
}


def _visitor_pick_column(frame: pd.DataFrame, candidates: tuple[str, ...]) -> str | None:
  if frame is None or frame.empty:
    return None
  lookup = {
    re.sub(r"[^a-z0-9]+", "", str(column).casefold()): str(column)
    for column in frame.columns
  }
  for candidate in candidates:
    normalized = re.sub(r"[^a-z0-9]+", "", str(candidate).casefold())
    if normalized in lookup:
      return lookup[normalized]
  return None


def _visitor_country_name(value: object) -> str:
  text = str(value or "").strip()
  if not text or text.casefold() in {"unknown", "none", "nan", "xx", "zz"}:
    return "Unknown"
  upper = text.upper()
  if len(upper) == 2 and upper.isalpha():
    try:
      import pycountry

      country = pycountry.countries.get(alpha_2=upper)
      if country is not None:
        text = str(country.name)
    except Exception:
      text = upper
  return VISITOR_COUNTRY_NAME_OVERRIDES.get(text, text)


def _visitor_world_map_frame() -> pd.DataFrame:
  country_df = visitor_country_summary()
  visits_df = load_visitor_visits()
  rows: list[dict] = []

  if isinstance(country_df, pd.DataFrame) and not country_df.empty:
    name_col = _visitor_pick_column(
      country_df,
      ("Country", "country_name", "country", "Country name"),
    )
    code_col = _visitor_pick_column(
      country_df,
      ("country_code", "Country code", "ISO2", "code"),
    )
    visits_col = _visitor_pick_column(country_df, ("Visits", "visits", "count"))
    unique_col = _visitor_pick_column(
      country_df,
      ("Unique visitors", "unique_visitors", "visitors"),
    )
    flag_col = _visitor_pick_column(country_df, ("Flag", "country_flag", "flag"))
    for _, row in country_df.iterrows():
      country = _visitor_country_name(row.get(name_col, "") if name_col else "")
      if country == "Unknown":
        country = _visitor_country_name(row.get(code_col, "") if code_col else "")
      visits = pd.to_numeric(row.get(visits_col, 0), errors="coerce") if visits_col else 0
      unique = pd.to_numeric(row.get(unique_col, 0), errors="coerce") if unique_col else 0
      rows.append({
        "Country": country,
        "Visits": int(0 if pd.isna(visits) else visits),
        "Unique visitors": int(0 if pd.isna(unique) else unique),
        "Flag": str(row.get(flag_col, "🌐") or "🌐") if flag_col else "🌐",
      })

  if not rows and isinstance(visits_df, pd.DataFrame) and not visits_df.empty:
    name_col = _visitor_pick_column(
      visits_df,
      ("country_name", "Country", "country", "country_code"),
    )
    code_col = _visitor_pick_column(visits_df, ("country_code", "Country code"))
    visitor_col = _visitor_pick_column(visits_df, ("visitor_id", "Visitor ID"))
    flag_col = _visitor_pick_column(visits_df, ("country_flag", "Flag"))
    if name_col or code_col:
      work = visits_df.copy()
      work["_country"] = work.apply(
        lambda row: _visitor_country_name(
          row.get(name_col, "") if name_col else row.get(code_col, "")
        ),
        axis=1,
      )
      work["_flag"] = work[flag_col].fillna("🌐").astype(str) if flag_col else "🌐"
      for country, group in work.groupby("_country", dropna=False):
        rows.append({
          "Country": str(country),
          "Visits": int(len(group)),
          "Unique visitors": int(group[visitor_col].astype(str).nunique()) if visitor_col else int(len(group)),
          "Flag": str(group["_flag"].iloc[0]),
        })

  frame = pd.DataFrame(rows, columns=["Country", "Visits", "Unique visitors", "Flag"])
  if frame.empty:
    return pd.DataFrame(columns=["Country", "Visits", "Unique visitors", "Flag", "Cities"])

  frame["Country"] = frame["Country"].map(_visitor_country_name)
  frame["Visits"] = pd.to_numeric(frame["Visits"], errors="coerce").fillna(0).astype(int)
  frame["Unique visitors"] = pd.to_numeric(frame["Unique visitors"], errors="coerce").fillna(0).astype(int)
  frame = frame.groupby("Country", as_index=False).agg(
    Visits=("Visits", "sum"),
    **{"Unique visitors": ("Unique visitors", "sum")},
    Flag=("Flag", "first"),
  )

  city_counts: dict[str, int] = {}
  if isinstance(visits_df, pd.DataFrame) and not visits_df.empty:
    visit_country_col = _visitor_pick_column(
      visits_df,
      ("country_name", "Country", "country", "country_code"),
    )
    visit_code_col = _visitor_pick_column(visits_df, ("country_code", "Country code"))
    city_col = _visitor_pick_column(visits_df, ("city", "City"))
    if (visit_country_col or visit_code_col) and city_col:
      city_work = visits_df.copy()
      city_work["_country"] = city_work.apply(
        lambda row: _visitor_country_name(
          row.get(visit_country_col, "") if visit_country_col else row.get(visit_code_col, "")
        ),
        axis=1,
      )
      city_work["_city"] = city_work[city_col].fillna("").astype(str).str.strip()
      city_work = city_work[
        city_work["_city"].ne("")
        & ~city_work["_city"].str.casefold().isin({"unknown", "none", "nan"})
      ]
      if not city_work.empty:
        city_counts = city_work.groupby("_country")["_city"].nunique().astype(int).to_dict()
  frame["Cities"] = frame["Country"].map(city_counts).fillna(0).astype(int)
  return frame.sort_values(["Visits", "Country"], ascending=[False, True]).reset_index(drop=True)


def _visitor_world_map_figure(country_frame: pd.DataFrame):
  map_frame = country_frame.copy()
  if not map_frame.empty:
    map_frame = map_frame[
      map_frame["Country"].astype(str).ne("Unknown")
      & pd.to_numeric(map_frame["Visits"], errors="coerce").fillna(0).gt(0)
    ].copy()

  fig = go.Figure()
  if not map_frame.empty:
    custom = np.column_stack([
      map_frame["Unique visitors"].to_numpy(),
      map_frame["Cities"].to_numpy(),
      map_frame["Flag"].astype(str).to_numpy(),
    ])
    fig.add_trace(go.Choropleth(
      locations=map_frame["Country"],
      locationmode="country names",
      z=map_frame["Visits"],
      customdata=custom,
      colorscale="Blues",
      autocolorscale=False,
      marker_line_color="rgba(71, 85, 105, 0.55)",
      marker_line_width=0.5,
      colorbar={"title": {"text": txt("Visitas", "Visits")}, "thickness": 14, "len": 0.70},
      hovertemplate=(
        "<b>%{customdata[2]} %{location}</b><br>"
        + txt("Visitas", "Visits") + ": %{z}<br>"
        + txt("Visitantes únicos", "Unique visitors") + ": %{customdata[0]}<br>"
        + txt("Cidades registradas", "Recorded cities") + ": %{customdata[1]}"
        + "<extra></extra>"
      ),
    ))
  else:
    fig.add_annotation(
      text=txt("Nenhuma visita geolocalizada registrada ainda", "No geolocated visits recorded yet"),
      x=0.5,
      y=0.5,
      xref="paper",
      yref="paper",
      showarrow=False,
      font={"size": 16},
    )

  fig.update_geos(
    projection_type="natural earth",
    showframe=False,
    showcoastlines=True,
    coastlinecolor="rgba(71, 85, 105, 0.55)",
    showcountries=True,
    countrycolor="rgba(100, 116, 139, 0.40)",
    showland=True,
    landcolor="rgba(226, 232, 240, 0.60)",
    showocean=True,
    oceancolor="rgba(219, 234, 254, 0.45)",
    bgcolor="rgba(0,0,0,0)",
  )
  fig.update_layout(
    title={"text": txt("Mapa-múndi detalhado de visitas", "Detailed world map of visits"), "x": 0.5, "xanchor": "center"},
    height=520,
    margin={"l": 0, "r": 0, "t": 70, "b": 10},
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font={"family": "Arial, Helvetica, sans-serif"},
  )
  return fig


def visitor_counter_public_footer(key: str = "public_footer"):
  metrics = visitor_summary_metrics()
  visits_df = load_visitor_visits()
  total = int(
    metrics.get(
      "total_visits",
      metrics.get("visits", len(visits_df) if isinstance(visits_df, pd.DataFrame) else 0),
    )
    or 0
  )
  country_frame = _visitor_world_map_frame()
  mapped_visits = int(pd.to_numeric(country_frame["Visits"], errors="coerce").fillna(0).sum()) if not country_frame.empty else 0
  unknown_visits = (
    int(pd.to_numeric(country_frame.loc[country_frame["Country"].astype(str).eq("Unknown"), "Visits"], errors="coerce").fillna(0).sum())
    if not country_frame.empty
    else 0
  )

  st.divider()
  st.markdown(
    f"""
<div class="public-visitor-footer" style="text-align:center;padding:0.85rem 0 0.45rem;">
  <span style="font-size:1.05rem;"><b>Visits:</b> <strong>{total:,}</strong> &nbsp; 🌐</span>
</div>
""",
    unsafe_allow_html=True,
  )
  st.caption(txt(
    "Distribuição geográfica das visitas registradas nesta instalação.",
    "Geographic distribution of visits recorded by this deployment.",
  ))

  st.plotly_chart(
    _visitor_world_map_figure(country_frame),
    use_container_width=True,
    key=f"{key}_world_visit_map",
    config={"displaylogo": False, "responsive": True, "scrollZoom": False},
  )

  if total == 0:
    st.info(txt(
      "O mapa será preenchido automaticamente quando as primeiras visitas forem registradas.",
      "The map will be populated automatically after the first visits are recorded.",
    ))
  elif mapped_visits == 0:
    st.info(txt(
      "As visitas foram contadas, mas o provedor ainda não informou países reconhecíveis para o mapa.",
      "Visits were counted, but the provider has not yet supplied recognizable countries for the map.",
    ))
  elif unknown_visits:
    st.caption(txt(
      f"Visitas sem localização reconhecida: {unknown_visits}.",
      f"Visits without a recognized location: {unknown_visits}.",
    ))

  with st.expander(
    txt("Detalhes de visitas por país, região e cidade", "Visit details by country, region and city"),
    expanded=False,
  ):
    if country_frame.empty:
      st.info(txt("Ainda não há localizações registradas.", "No locations have been recorded yet."))
    else:
      detail = country_frame.rename(columns={
        "Country": txt("País/região", "Country/region"),
        "Visits": txt("Visitas", "Visits"),
        "Unique visitors": txt("Visitantes únicos", "Unique visitors"),
        "Cities": txt("Cidades", "Cities"),
        "Flag": txt("Bandeira", "Flag"),
      })
      show_table(detail, f"{key}_visitor_country_region_detail", height=min(520, 120 + 36 * len(detail)))
      csv_button(
        detail,
        "visitor_country_region_detail.csv",
        txt("Baixar detalhes geográficos", "Download geographic details"),
      )

    city_frame = visitor_city_summary()
    if isinstance(city_frame, pd.DataFrame) and not city_frame.empty:
      st.markdown("##### " + txt("Localizações por cidade", "Locations by city"))
      show_table(city_frame, f"{key}_visitor_city_detail", height=min(520, 120 + 36 * len(city_frame)))
'''
    source = source[:footer_start] + replacement + source[footer_end + 1:]
