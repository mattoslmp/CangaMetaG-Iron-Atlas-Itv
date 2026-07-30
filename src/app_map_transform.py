from __future__ import annotations


def _replace_required(text: str, old: str, new: str, label: str) -> str:
  if old not in text:
    raise RuntimeError(f"Could not apply {label}: expected anchor was not found")
  return text.replace(old, new, 1)


def _replace_block(text: str, start_marker: str, end_marker: str, replacement: str, label: str) -> str:
  start = text.find(start_marker)
  if start < 0:
    raise RuntimeError(f"Could not apply {label}: start marker was not found")
  end = text.find(end_marker, start)
  if end < 0:
    raise RuntimeError(f"Could not apply {label}: end marker was not found")
  return text[:start] + replacement + text[end:]


# Replace the complete map wrapper by function boundaries rather than matching a
# long presentation paragraph. This remains stable when captions are rewrapped.
map_function_start = 'def show_high_quality_sample_map('
map_function_end = '\ndef _clean_link_text'
map_function = '''def show_high_quality_sample_map(
  meta: pd.DataFrame,
  key: str = "article_samples_map",
  overview_mode: bool = False,
):
  if not {"lat", "lon"}.issubset(meta.columns):
    return
  map_df = apply_amazonian_lake_coordinate_overrides(meta.copy())
  map_df["lat"] = pd.to_numeric(map_df["lat"], errors="coerce")
  map_df["lon"] = pd.to_numeric(map_df["lon"], errors="coerce")
  valid = map_df.dropna(subset=["lat", "lon"]).copy()
  if valid.empty:
    st.warning(txt("Nenhuma coordenada válida para exibir no mapa.", "No valid coordinates to display on the map."))
    return

  title = txt("Mapa Google das amostras e ambientes", "Google map of samples and environments")
  high_resolution_title = txt(
    "Mapa Google/satélite de alta resolução com pontos separados e clicáveis",
    "High-resolution Google / satellite map with clickable separated points",
  )

  if overview_mode:
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
  else:
    st.markdown("#### " + title)
    st.caption(txt(
      "O mapa rápido abaixo aparece primeiro e usa somente as coordenadas das planilhas suplementares. O mapa Google/satélite fica em uma seção opcional para evitar atraso quando os tiles externos demoram a carregar.",
      "The fast map below is rendered first and uses only coordinates from the supplementary spreadsheets. The Google/satellite map is optional to avoid delays when external tiles are slow to load.",
    ))
    show_reliable_plotly_map(
      map_df,
      key=key,
      title=txt(
        "Mapa de checagem de coordenadas — amostras, ambientes e pontos das lagoas",
        "Coordinate-check map — samples, environments and lake points",
      ),
      height=820,
    )

  with st.expander(high_resolution_title, expanded=True):
    st.caption(txt(
      "Quando pontos têm coordenadas idênticas ou quase idênticas, o marcador é ligeiramente deslocado apenas na visualização para evitar sobreposição; a coordenada original aparece no popup e na tabela.",
      "When points have identical or nearly identical coordinates, the marker is slightly offset only in the visualization to avoid overlap; the original coordinate appears in the popup and in the table.",
    ))
    show_leaflet_satellite_map(
      valid,
      key=f"{key}_google",
      title=high_resolution_title if overview_mode else title,
      height=820,
    )

  coordinate_cols = [c for c in [
    "Map source", "matrix_order", "matrix_column", "sample_id", "sample.id", "lake",
    "dataset_group", "sample_description", "environment_feature", "environment_biome",
    "environment_feature2", "geographic_location", "habitat", "isolation",
    "isolation_country", "collection_date_raw", "lat", "lon", "google_maps_url",
    "google_earth_url", "environment_reference_url", "img_jgi_url",
  ] if c in valid.columns]
  coordinate_table = valid[coordinate_cols].drop_duplicates().copy()
  coordinate_caption = txt(
    "Cada linha mantém a coordenada original disponível. Os links abrem Google Maps/Earth e a fonte ambiental ou IMG/JGI quando ela está registrada nos dados.",
    "Each row keeps the available original coordinate. Links open Google Maps/Earth and the environmental or IMG/JGI source when it is recorded in the data.",
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
    csv_button(
      coordinate_table,
      f"{key}_map_source_table.csv",
      txt("Baixar Map source table", "Download Map source table"),
    )
  else:
    with st.expander(
      txt(
        "Coordenadas, pontos das lagoas e links de referência ambiental",
        "Coordinates, lake points and environment reference links",
      ),
      expanded=True,
    ):
      st.caption(coordinate_caption)
      show_table(coordinate_table, f"{key}_coordinates_reference_links", height=360)
      csv_button(
        coordinate_table,
        f"{key}_coordinates_reference_links.csv",
        txt("Baixar coordenadas e links", "Download coordinates and links"),
      )

  center_lat = float(valid["lat"].mean())
  center_lon = float(valid["lon"].mean())
  c1, c2, c3 = st.columns(3)
  with c1:
    st.download_button(
      "KML Google Earth",
      data=kml_from_metadata(valid).encode("utf-8"),
      file_name=f"{key}.kml",
      mime="application/vnd.google-earth.kml+xml",
      key=f"{key}_kml",
    )
  with c2:
    st.link_button(
      txt("Abrir área no Google Earth Web", "Open area in Google Earth Web"),
      f"https://earth.google.com/web/search/{center_lat:.6f},{center_lon:.6f}",
    )
  with c3:
    st.link_button(
      txt("Abrir centro no Google Maps", "Open center in Google Maps"),
      f"https://www.google.com/maps/search/?api=1&query={center_lat:.6f},{center_lon:.6f}",
    )

'''
source = _replace_block(
  source,
  map_function_start,
  map_function_end,
  map_function,
  "high-quality map function",
)


# Add the recorded source/reference URL to Leaflet popups when the current core
# still contains the canonical popup statement. This is optional presentation
# enrichment and must never prevent the app from starting.
popup_old = "      marker.bindPopup(`<b>${{p.sample}}</b><br><b>Environment:</b> ${{p.environment}}<br><b>Location:</b> ${{p.location}}<br><b>Date:</b> ${{p.date || 'NA'}}<br><b>Group:</b> ${{p.category || 'NA'}}<br><b>Original Lat/Lon:</b> ${{p.original_lat.toFixed(6)}}, ${{p.original_lon.toFixed(6)}}<br><b>Map display:</b> ${{p.offset_note}}`);\n"
popup_new = "      const referenceLink = p.reference_url ? `<br><a href=\"${{p.reference_url}}\" target=\"_blank\" rel=\"noopener noreferrer\"><b>Open source/reference</b></a>` : '';\n      marker.bindPopup(`<b>${{p.sample}}</b><br><b>Environment:</b> ${{p.environment}}<br><b>Location:</b> ${{p.location}}<br><b>Date:</b> ${{p.date || 'NA'}}<br><b>Group:</b> ${{p.category || 'NA'}}<br><b>Original Lat/Lon:</b> ${{p.original_lat.toFixed(6)}}, ${{p.original_lon.toFixed(6)}}<br><b>Map display:</b> ${{p.offset_note}}${{referenceLink}}`);\n"
if popup_old in source:
  source = source.replace(popup_old, popup_new, 1)


# Replace the external-only overview block by structural boundaries. The map is
# assembled exclusively from the article lake metadata and the packaged ST8
# environmental-coordinate table.
overview_start = '  external_map_meta = load_external_environment_coordinates(BASE_DIR)\n'
overview_end = '  st.markdown("### " + txt("Workflow do atlas", "Atlas workflow"))'
overview_replacement = '''  external_map_meta = load_external_environment_coordinates(BASE_DIR)
  if external_map_meta.empty:
    external_map_meta = figure11_environment_metadata()

  lake_map_meta = meta.copy()
  if not lake_map_meta.empty and {"lat", "lon"}.issubset(lake_map_meta.columns):
    lake_map_meta = apply_amazonian_lake_coordinate_overrides(lake_map_meta)
    lake_map_meta["dataset_group"] = "Brazil — Amazonian lateritic lakes"
    lake_map_meta["Map source"] = "Study area and sampling design — Brazil"
    if "sample_description" not in lake_map_meta.columns:
      lake_map_meta["sample_description"] = lake_map_meta.get(
        "sample.id",
        lake_map_meta.get("lake", pd.Series("", index=lake_map_meta.index)),
      )
    if "environment_feature" not in lake_map_meta.columns:
      lake_map_meta["environment_feature"] = "Ferruginous lateritic lake sediment"
    else:
      lake_map_meta["environment_feature"] = (
        lake_map_meta["environment_feature"].replace("", np.nan)
        .fillna("Ferruginous lateritic lake sediment")
      )
    if "geographic_location" not in lake_map_meta.columns:
      lake_map_meta["geographic_location"] = "Carajás, Pará, Brazil"
    else:
      lake_map_meta["geographic_location"] = (
        lake_map_meta["geographic_location"].replace("", np.nan)
        .fillna("Carajás, Pará, Brazil")
      )
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
      existing_maps = out["google_maps_url"].fillna("").astype(str)
      out["google_maps_url"] = existing_maps.where(existing_maps.str.strip().ne(""), generated_maps)
    if "google_earth_url" not in out.columns:
      out["google_earth_url"] = generated_earth
    else:
      existing_earth = out["google_earth_url"].fillna("").astype(str)
      out["google_earth_url"] = existing_earth.where(existing_earth.str.strip().ne(""), generated_earth)
    return out

  combined_map_meta = pd.concat(
    [_map_links(lake_map_meta), _map_links(external_map_meta)],
    ignore_index=True,
    sort=False,
  )
  if combined_map_meta.empty:
    st.info(txt(
      "Não há coordenadas disponíveis para o mapa integrado.",
      "No coordinates are available for the integrated map.",
    ))
  else:
    show_high_quality_sample_map(
      combined_map_meta,
      key="overview_brazil_and_external_iron_rich_map_v3",
      overview_mode=True,
    )

'''
source = _replace_block(
  source,
  overview_start,
  overview_end,
  overview_replacement,
  "overview Brazil and external interactive map",
)
