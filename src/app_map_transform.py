from __future__ import annotations


def replace_once(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


# Keep the existing complete map component for the other application pages,
# while allowing the overview to display only the high-resolution interactive
# map and one consolidated source table.
source = replace_once(
  source,
  'def show_high_quality_sample_map(meta: pd.DataFrame, key: str = "article_samples_map"):\n',
  'def show_high_quality_sample_map(meta: pd.DataFrame, key: str = "article_samples_map", overview_mode: bool = False):\n',
  "overview map mode",
)

map_intro_anchor = '''  title = txt("Mapa Google das amostras e ambientes", "Google map of samples and environments")
  st.markdown("#### " + title)
  st.caption(txt(
    "O mapa rápido abaixo aparece primeiro e usa somente as coordenadas das planilhas suplementares. O mapa Google/satélite fica em uma seção opcional para evitar atraso quando os tiles externos demoram a carregar.",
    "The fast map below is rendered first and uses only coordinates from the supplementary spreadsheets. The Google/satellite map is optional to avoid delays when external tiles are slow to load."
  ))
  show_reliable_plotly_map(map_df, key=key, title=txt("Coordinate-check map — samples, environments and lake points", "Coordinate-check map — samples, environments and lake points"), height=820)

  with st.expander(txt("High-resolution Google / satellite map with clickable separated points", "High-resolution Google / satellite map with clickable separated points"), expanded=True):
    st.caption(txt("Quando pontos têm coordenadas idênticas ou quase idênticas, o marcador é ligeiramente deslocado apenas na visualização para evitar sobreposição; a coordenada original aparece no popup e na tabela.", "When points have identical or nearly identical coordinates, the marker is slightly offset only in the visualization to avoid overlap; the original coordinate appears in the popup and in the table."))
    show_leaflet_satellite_map(valid, key=f"{key}_google", title=title, height=820)
'''
map_intro_replacement = '''  title = txt("Mapa Google das amostras e ambientes", "Google map of samples and environments")
  high_resolution_title = txt(
    "Mapa Google/satélite de alta resolução com pontos separados e clicáveis",
    "High-resolution Google / satellite map with clickable separated points",
  )
  if not overview_mode:
    st.markdown("#### " + title)
    st.caption(txt(
      "O mapa rápido abaixo aparece primeiro e usa somente as coordenadas das planilhas suplementares. O mapa Google/satélite fica em uma seção opcional para evitar atraso quando os tiles externos demoram a carregar.",
      "The fast map below is rendered first and uses only coordinates from the supplementary spreadsheets. The Google/satellite map is optional to avoid delays when external tiles are slow to load."
    ))
    show_reliable_plotly_map(map_df, key=key, title=txt("Coordinate-check map — samples, environments and lake points", "Coordinate-check map — samples, environments and lake points"), height=820)
  else:
    st.markdown(
      f'''<div style="margin:0.8rem 0 0.75rem 0;padding:1rem 1.15rem;border-radius:18px;
      background:linear-gradient(135deg,#E6F4F1,#EEF6FF);border:2px solid #0F766E;
      box-shadow:0 10px 24px rgba(15,118,110,.14);">
      <div style="font-size:1.12rem;font-weight:900;color:#064E3B;">🗺️ {high_resolution_title}</div>
      <div style="margin-top:.35rem;color:#244744;line-height:1.45;">
      {txt('Explore os pontos das lagoas brasileiras do estudo e dos ambientes externos ricos em ferro. Clique nos marcadores para visualizar identificação, ambiente, localização e coordenadas originais.', 'Explore the Brazilian study-lake points and the external iron-rich environments. Click each marker to view its identification, environment, location and original coordinates.')}
      </div></div>''',
      unsafe_allow_html=True,
    )

  with st.expander(high_resolution_title, expanded=True):
    st.caption(txt("Quando pontos têm coordenadas idênticas ou quase idênticas, o marcador é ligeiramente deslocado apenas na visualização para evitar sobreposição; a coordenada original aparece no popup e na tabela.", "When points have identical or nearly identical coordinates, the marker is slightly offset only in the visualization to avoid overlap; the original coordinate appears in the popup and in the table."))
    show_leaflet_satellite_map(valid, key=f"{key}_google", title=high_resolution_title if overview_mode else title, height=820)
'''
source = replace_once(source, map_intro_anchor, map_intro_replacement, "overview high-resolution map")

# Make the reference stored for each point directly accessible from its popup.
source = replace_once(
  source,
  "      marker.bindPopup(`<b>${p.sample}</b><br><b>Environment:</b> ${p.environment}<br><b>Location:</b> ${p.location}<br><b>Date:</b> ${p.date || 'NA'}<br><b>Group:</b> ${p.category || 'NA'}<br><b>Original Lat/Lon:</b> ${p.original_lat.toFixed(6)}, ${p.original_lon.toFixed(6)}<br><b>Map display:</b> ${p.offset_note}`);\n",
  "      const referenceLink = p.reference_url ? `<br><a href=\"${p.reference_url}\" target=\"_blank\" rel=\"noopener noreferrer\"><b>Open source/reference</b></a>` : '';\n      marker.bindPopup(`<b>${p.sample}</b><br><b>Environment:</b> ${p.environment}<br><b>Location:</b> ${p.location}<br><b>Date:</b> ${p.date || 'NA'}<br><b>Group:</b> ${p.category || 'NA'}<br><b>Original Lat/Lon:</b> ${p.original_lat.toFixed(6)}, ${p.original_lon.toFixed(6)}<br><b>Map display:</b> ${p.offset_note}${referenceLink}`);\n",
  "map popup reference link",
)

coordinate_anchor = '''  coordinate_cols = [c for c in [
    "matrix_order", "matrix_column", "sample_id", "sample.id", "dataset_group", "sample_description",
    "environment_feature", "environment_biome", "environment_feature2", "geographic_location",
    "habitat", "isolation", "isolation_country", "collection_date_raw", "lat", "lon",
    "google_maps_url", "google_earth_url", "environment_reference_url", "img_jgi_url"
  ] if c in valid.columns]
  with st.expander(txt("Coordinates, lake points and environment reference links", "Coordinates, lake points and environment reference links"), expanded=True):
    st.caption(txt(
      "Cada linha mantém a coordenada original disponível. Os links abrem Google Maps/Earth e uma consulta de referência sobre o ambiente/amostra quando houver texto suficiente.",
      "Each row keeps the available original coordinate. Links open Google Maps/Earth and a reference search for the environment/sample when enough text is available."
    ))
    show_table(valid[coordinate_cols].drop_duplicates(), f"{key}_coordinates_reference_links", height=360)
    csv_button(valid[coordinate_cols].drop_duplicates(), f"{key}_coordinates_reference_links.csv", txt("Baixar coordenadas e links", "Download coordinates and links"))
'''
coordinate_replacement = '''  coordinate_cols = [c for c in [
    "Map source", "matrix_order", "matrix_column", "sample_id", "sample.id", "lake", "dataset_group", "sample_description",
    "environment_feature", "environment_biome", "environment_feature2", "geographic_location",
    "habitat", "isolation", "isolation_country", "collection_date_raw", "lat", "lon",
    "google_maps_url", "google_earth_url", "environment_reference_url", "img_jgi_url"
  ] if c in valid.columns]
  coordinate_table = valid[coordinate_cols].drop_duplicates().copy()
  coordinate_caption = txt(
    "Cada linha mantém a coordenada original disponível. Os links abrem Google Maps/Earth e a fonte ambiental ou IMG/JGI quando ela está registrada nos dados.",
    "Each row keeps the available original coordinate. Links open Google Maps/Earth and the environmental or IMG/JGI source when it is recorded in the data."
  )
  if overview_mode:
    st.markdown(
      '''<div style="margin:1rem 0 .45rem 0;padding:.78rem 1rem;border-radius:14px;
      background:#FFF7D6;border-left:7px solid #D97706;border-top:1px solid #F2C94C;
      border-right:1px solid #F2C94C;border-bottom:1px solid #F2C94C;
      font-size:1.08rem;font-weight:900;color:#7C2D12;">★ Map source table</div>''',
      unsafe_allow_html=True,
    )
    st.caption(coordinate_caption)
    show_table(coordinate_table, f"{key}_map_source_table", height=520)
    csv_button(coordinate_table, f"{key}_map_source_table.csv", txt("Baixar Map source table", "Download Map source table"))
  else:
    with st.expander(txt("Coordinates, lake points and environment reference links", "Coordinates, lake points and environment reference links"), expanded=True):
      st.caption(coordinate_caption)
      show_table(coordinate_table, f"{key}_coordinates_reference_links", height=360)
      csv_button(coordinate_table, f"{key}_coordinates_reference_links.csv", txt("Baixar coordenadas e links", "Download coordinates and links"))
'''
source = replace_once(source, coordinate_anchor, coordinate_replacement, "consolidated map source table")

# Replace the overview's external-only nested map with one combined interactive
# map containing the article's Brazilian lake samples and the external records.
overview_map_anchor = '''  external_map_meta = load_external_environment_coordinates(BASE_DIR)
  if external_map_meta.empty:
    external_map_meta = figure11_environment_metadata()
  with st.expander(txt(
    "Mapa dos outros ambientes ricos em ferro",
    "Map of the other iron-rich environments",
  ), expanded=False):
    if external_map_meta.empty:
      st.info(txt(
        "Não há coordenadas externas disponíveis nos metadados empacotados.",
        "No external coordinates are available in the packaged metadata."
      ))
    else:
      show_high_quality_sample_map(external_map_meta, key="overview_other_iron_rich_environment_map_v1")
      st.markdown("###### " + txt("Tabela-fonte do mapa", "Map source table"))
      show_table(external_map_meta, "overview_other_iron_rich_environment_map_source", height=460)
      csv_button(
        external_map_meta,
        "other_iron_rich_environment_map_source.csv",
        txt("Baixar tabela-fonte", "Download source table"),
      )
'''
overview_map_replacement = '''  external_map_meta = load_external_environment_coordinates(BASE_DIR)
  if external_map_meta.empty:
    external_map_meta = figure11_environment_metadata()

  lake_map_meta = meta.copy()
  if not lake_map_meta.empty and {"lat", "lon"}.issubset(lake_map_meta.columns):
    lake_map_meta = apply_amazonian_lake_coordinate_overrides(lake_map_meta)
    lake_map_meta["dataset_group"] = "Brazil — Amazonian lateritic lakes"
    lake_map_meta["Map source"] = "Study area and sampling design — Brazil"
    if "sample_description" not in lake_map_meta.columns:
      lake_map_meta["sample_description"] = lake_map_meta.get("sample.id", lake_map_meta.get("lake", pd.Series("", index=lake_map_meta.index)))
    if "environment_feature" not in lake_map_meta.columns:
      lake_map_meta["environment_feature"] = "Ferruginous lateritic lake sediment"
    else:
      lake_map_meta["environment_feature"] = lake_map_meta["environment_feature"].replace("", np.nan).fillna("Ferruginous lateritic lake sediment")
    if "geographic_location" not in lake_map_meta.columns:
      lake_map_meta["geographic_location"] = "Carajás, Pará, Brazil"
    else:
      lake_map_meta["geographic_location"] = lake_map_meta["geographic_location"].replace("", np.nan).fillna("Carajás, Pará, Brazil")
    lake_map_meta["isolation_country"] = "Brazil"
  else:
    lake_map_meta = pd.DataFrame()

  if not external_map_meta.empty:
    external_map_meta = external_map_meta.copy()
    external_map_meta["Map source"] = "Supplementary Table 8 — external iron-rich environments"

  def _map_links(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty or not {"lat", "lon"}.issubset(frame.columns):
      return pd.DataFrame() if frame is None else frame.copy()
    out = frame.copy()
    out["lat"] = pd.to_numeric(out["lat"], errors="coerce")
    out["lon"] = pd.to_numeric(out["lon"], errors="coerce")
    valid_coords = out["lat"].notna() & out["lon"].notna()
    generated_maps = pd.Series("", index=out.index, dtype=object)
    generated_earth = pd.Series("", index=out.index, dtype=object)
    generated_maps.loc[valid_coords] = [
      f"https://www.google.com/maps/search/?api=1&query={lat:.6f},{lon:.6f}"
      for lat, lon in zip(out.loc[valid_coords, "lat"], out.loc[valid_coords, "lon"])
    ]
    generated_earth.loc[valid_coords] = [
      f"https://earth.google.com/web/search/{lat:.6f},{lon:.6f}"
      for lat, lon in zip(out.loc[valid_coords, "lat"], out.loc[valid_coords, "lon"])
    ]
    if "google_maps_url" not in out.columns:
      out["google_maps_url"] = generated_maps
    else:
      out["google_maps_url"] = out["google_maps_url"].fillna("").astype(str).where(out["google_maps_url"].fillna("").astype(str).str.strip().ne(""), generated_maps)
    if "google_earth_url" not in out.columns:
      out["google_earth_url"] = generated_earth
    else:
      out["google_earth_url"] = out["google_earth_url"].fillna("").astype(str).where(out["google_earth_url"].fillna("").astype(str).str.strip().ne(""), generated_earth)
    return out

  combined_map_meta = pd.concat(
    [_map_links(lake_map_meta), _map_links(external_map_meta)],
    ignore_index=True,
    sort=False,
  )
  if combined_map_meta.empty:
    st.info(txt(
      "Não há coordenadas disponíveis para o mapa integrado.",
      "No coordinates are available for the integrated map."
    ))
  else:
    show_high_quality_sample_map(
      combined_map_meta,
      key="overview_brazil_and_external_iron_rich_map_v2",
      overview_mode=True,
    )
'''
source = replace_once(source, overview_map_anchor, overview_map_replacement, "overview Brazil and external interactive map")
