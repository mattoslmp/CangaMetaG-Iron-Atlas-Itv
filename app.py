from __future__ import annotations

import json
import os
import pickle
import re
import time
import html as html_lib
import hashlib
import secrets as py_secrets
import smtplib
import zipfile
import textwrap
import logging
from email.message import EmailMessage
from urllib.parse import quote_plus
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import List
import sys

# Ensure the packaged project root is importable even when Streamlit is
# launched from another working directory. The complete distribution must keep
# app.py beside the src/, data/, tables/, outputs/ and scripts/ directories.
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
  sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.offline import get_plotlyjs, get_plotlyjs_version
import streamlit as st
import streamlit.components.v1 as components
try:
  from PIL import Image, ImageFile
  ImageFile.LOAD_TRUNCATED_IMAGES = False
except Exception:
  Image = None
from src.runtime_preflight import streamlit_dependency_guard
from src.streamlit_compat import arrow_safe_dataframe
from src.runtime_paths import (
  APP_CACHE_DIR,
  APP_CONFIG_DIR,
  APP_DATA_DIR,
  APP_STATE_DIR,
  ensure_runtime_layout,
  runtime_summary,
)
streamlit_dependency_guard(st)
import requests
from scipy.spatial.distance import pdist, squareform
from scipy import stats
from sklearn.manifold import MDS

from src.publication_rda import (
  publication_rda_figure, publication_nmds_figure,
  publication_rda_data, publication_nmds_data,
)
from src.publication_ordination import (
  permanova as canonical_permanova,
  betadisper_test as canonical_betadisper_test,
  _new_nonmetric_mds as canonical_nonmetric_mds,
  _orient_axes as canonical_orient_axes,
  beta_transform_matrix as canonical_beta_transform_matrix,
  pcoa_bray_curtis_matrix as canonical_pcoa_bray_curtis_matrix,
  nmds_bray_curtis_matrix as canonical_nmds_bray_curtis_matrix,
)
from src.environment_map_data import load_external_environment_coordinates
from src.plotly_export import (
  configure_browser_environment,
  discover_browser,
  export_plotly_bytes,
  validate_visible_text,
)

LOGGER = logging.getLogger("cangametag.app")
PLOTLY_JS_INLINE = get_plotlyjs().replace("</script>", "<\\/script>")
LAST_PLOTLY_EXPORT_ERRORS: dict[str, str] = {}


from src.visual_qc import (
  adaptive_heatmap_geometry,
  compact_heatmap_colorbars,
  compact_significance_summary,
  polish_heatmap_layout,
  sparsify_heatmap_y_ticks,
  repel_label_positions,
)


from src.supplementary_database import (
  ARTICLE_CITATION,
  AUTHORS,
  BIOGEOCHEMICAL_DISPLAY_NAME,
  SALAZAR_CITATION,
  ASSETS_DIR,
  BASE_DIR,
  TAXONOMY_LEVELS,
  TABLE_FILES,
  available_fasta_count,
  available_gbk_count,
  amazonia_vs_iron_marker_summary,
  counts_table,
  excel_sheet_names,
  filter_by_text,
  get_fasta_path,
  get_gbk_path,
  heatmap_figure,
  infer_metadata_cols,
  iron_rich_environment_metadata,
  figure11_environment_metadata,
  res_ko_fe_reduzido_table,
  res_ko_fe_selected_table,
  iron_fe_zscore_table,
  iron_fe_marker_summary,
  ST8_ALL_KO_SHEET,
  ST8_SELECTED_SEDIMENTS_SHEET,
  ST8_IRON_ALL_SHEET,
  ST8_IRON_SELECTED_SHEET,
  load_sheet,
  marker_table,
  read_text_file,
  sheet_inventory,
  taxonomy_heatmap,
  taxonomy_samples_metadata,
  taxonomy_stacked_bar,
  taxonomy_profile_table,
  taxonomy_table,
  with_kegg_links,
)

from src.taxonomy_palette import build_palette as build_canonical_taxonomy_palette, load_palette as load_canonical_taxonomy_palette

from src.data_sources import (
  NASA_POWER_DEFAULT_PARAMS,
  NASA_POWER_PARAMETER_DICTIONARY,
  fetch_chirps_daily_climateserv,
  test_chirps_climateserv_connection,
  fetch_mapbiomas_gee_landcover,
  fetch_nasa_power_daily,
  fetch_sentinel1_monthly_backscatter,
  fetch_sentinel1_catalog_coverage,
  fetch_sentinel2_catalog_coverage,
  fetch_sentinel6_altimetry_granules,
  fetch_sentinelhub_monthly_indices,
  fetch_soilgrids_point,
  _copernicus_token,
)

from src.earthdata_nasa import (
  EARTHDATA_PRODUCT_REGISTRY,
  earthaccess_download_product,
  earthdata_auth_status,
  earthdata_product_table,
  search_earthdata_collections,
  search_earthdata_granules,
)

from src.bvbrc_public import (
  api_url as bvbrc_api_url,
  feature_browser_url as bvbrc_feature_browser_url,
  fetch_bvbrc_json,
  genome_tab_links as bvbrc_genome_tab_links,
  genome_tab_url as bvbrc_genome_tab_url,
  genome_url_from_id as bvbrc_genome_url_from_id,
  workspace_mag_url as bvbrc_workspace_mag_url,
  normalize_public_feature_table,
  public_link_for_mag,
)

from src.mag_annotations import (
  ANNOTATION_DIR,
  annotation_folder,
  annotation_summary_table,
  canonical_mag_id,
  contig_table,
  fasta_path_for_mag,
  feature_stats,
  feature_table,
  file_manifest,
  genbank_path_for_mag,
  genome_organization_figure,
  genome_report_metrics,
  list_annotation_folders,
  mag_number,
  taxonomy_summary,
)

from src.bvbrc_cli_sync import (
  DEFAULT_WORKSPACE_BASE as BVBRC_DEFAULT_WORKSPACE_BASE,
  bvbrc_cli_status,
  install_commands_ubuntu as bvbrc_install_commands_ubuntu,
  inventory_local_annotations as bvbrc_inventory_local_annotations,
  local_annotation_status as bvbrc_local_annotation_status,
  list_remote_path as bvbrc_list_remote_path,
  sync_mag_annotation as bvbrc_sync_mag_annotation,
)

from src.integrated_omics import (
  combined_omics_matrix,
  correlation_heatmap,
  environmental_matrix,
  env_axis_correlations,
  feature_axis_vectors,
  make_integrated_table,
  nmds_bray_curtis,
  omics_environment_correlations,
  ordination_figure,
  pca_integrated,
  pcoa_bray_curtis,
)

from src.functional_annotations import (
  ANNOTATION_SHEETS,
  EXPECTED_TABLE8_FEATURE_COUNTS,
  SOURCE_LABELS as FUNCTIONAL_SOURCE_LABELS,
  add_annotation_links,
  annotation_row_details,
  build_annotation_dataset,
  functional_annotation_heatmap,
  row_zscore as functional_row_zscore,
)

from src.kegg_modules import (
  DATASET_DIRS as KEGG_DATASET_DIRS,
  KEMET_OUTPUT_DIR,
  MAG_COMPLETENESS_TABLE,
  build_kegg_outputs,
  canonical_mag_id,
  completion_heatmap,
  ensure_kegg_module_directories,
  fasta_inventory as kegg_fasta_inventory,
  input_name_inventory as kegg_input_name_inventory,
  load_module_matrices,
  metagenome_display_label,
  mag_display_label,
  METAGENOME_SAMPLE_MAP,
  mag_taxonomy_metadata,
  kegg_sample_metadata,
  metagenome_sample_coverage,
  module_component_figure,
  report_files as kegg_report_files,
  zip_directory_bytes,
)

from src.antismash_viewer import (
  antismash_inventory,
  antismash_run_zip_bytes,
  discover_antismash_runs,
  self_contained_antismash_html,
)

from src.visitor_analytics import (
  VISITOR_LOG_PATH,
  city_summary as visitor_city_summary,
  clear_visitor_data,
  country_summary as visitor_country_summary,
  load_visits as load_visitor_visits,
  record_visit,
  summary_metrics as visitor_summary_metrics,
)



def runtime_setting(key: str, default: str = "") -> str:
  """Return a value from the current UI session or environment variables.

  Sensitive API credentials can be entered in the administrator interface
  and are copied into ``st.session_state``; deployment automation may instead
  provide ordinary environment variables. No external credential file is read.
  """
  try:
    value = st.session_state.get(key)
    if value not in (None, ""):
      return str(value)
  except Exception:
    pass
  value = os.environ.get(key, default)
  return default if value is None else str(value)

def ensure_runtime_dirs() -> None:
  # Runtime files must never be written inside the application package.
  ensure_runtime_layout([RUNTIME_STATE_DIR, API_CACHE_DIR])


def safe_path_exists(path: Path) -> bool:
  """Return False instead of crashing when a legacy path is unreadable."""
  try:
    return path.exists()
  except OSError:
    return False




def _row_zscore_frame(frame: pd.DataFrame) -> pd.DataFrame:
  if frame is None or frame.empty:
    return pd.DataFrame()
  numeric = frame.copy()
  for col in numeric.columns:
    numeric[col] = pd.to_numeric(numeric[col], errors="coerce")
  means = numeric.mean(axis=1)
  stds = numeric.std(axis=1, ddof=0).replace(0, np.nan)
  return numeric.sub(means, axis=0).div(stds, axis=0).fillna(0.0)


def kegg_numeric_heatmap_figure(matrix: pd.DataFrame, dataset_type: str, title: str, colorbar_title: str, zscore_mode: bool = False):
  if matrix is None or matrix.empty:
    return None, pd.DataFrame()
  display = matrix.copy()
  sample_meta = kegg_sample_metadata(dataset_type, display.columns)
  meta_by_id = sample_meta.set_index("canonical_id").to_dict("index") if not sample_meta.empty else {}
  x_labels, hover_bits, original_samples = [], [], [str(x) for x in display.columns]
  for sid in original_samples:
    canonical = canonical_mag_id(sid) if dataset_type == "mags" else sid
    canonical = canonical or sid
    rec = meta_by_id.get(canonical, {})
    x_labels.append(str(rec.get("axis_label", canonical)))
    if dataset_type == "mags":
      hover_bits.append(f"Genus: {rec.get('Genus','') or 'not assigned'}<br>Species: {rec.get('Species','') or 'not assigned'}<br>GTDB lineage: {rec.get('GTDB_lineage','') or 'not assigned'}")
    else:
      hover_bits.append(f"Study sample: {rec.get('lake_sample', canonical)}<br>IMG/JGI identifier: {rec.get('IMG_JGI_ID', canonical)}")
  y_labels = [str(i) for i in display.index]
  custom = np.empty((display.shape[0], display.shape[1], 3), dtype=object)
  for i, row_name in enumerate(display.index):
    for j, sid in enumerate(original_samples):
      custom[i, j, 0] = sid
      custom[i, j, 1] = x_labels[j].replace('<br>', ' | ')
      custom[i, j, 2] = hover_bits[j]
  # Preserve readable column geometry as well as every row label. The figure
  # is shown inside a two-directional scroll viewport, so it must not be
  # compressed to the browser width.
  row_cell_px = 24 if display.shape[0] > 300 else 30
  column_cell_px = 40 if display.shape[1] > 30 else 48
  width = int(650 + column_cell_px * max(display.shape[1], 1))
  height = int(280 + row_cell_px * max(display.shape[0], 1))
  if zscore_mode:
    zmin, zmax, colorscale = -3, 3, 'RdBu_r'
  else:
    zmin, zmax, colorscale = 0, 1, 'Viridis'
  fig = go.Figure(data=go.Heatmap(
    z=display.to_numpy(), x=x_labels, y=y_labels, colorscale=colorscale, zmin=zmin, zmax=zmax,
    colorbar={"title": {"text": colorbar_title, "font": {"size": 11}}, "thickness": 14, "len": 0.44, "y": 1.0, "yanchor": "top"},
    customdata=custom,
    hovertemplate=("<b>%{y}</b><br><b>Visible label:</b> %{customdata[1]}<br><b>Canonical ID:</b> %{customdata[0]}<br>%{customdata[2]}<br><b>Value:</b> %{z:.3f}<extra></extra>"),
    xgap=0.4, ygap=0.4))
  fig.update_layout(
    title=title,
    width=min(16000, max(width, 1200)),
    height=min(30000, max(height, 280 + row_cell_px * max(len(y_labels), 1))),
    margin={"l": 620, "r": 150, "t": 110, "b": 300},
    font={"family": "Arial, Helvetica, sans-serif", "size": 12, "color": "#111111"},
    meta={
      "preserve_cell_geometry": True,
      "force_all_y_ticks": True,
      "all_y_labels_visible": True,
      "cell_height_px": row_cell_px,
      "y_tick_font_size": 10,
      "source_row_count": len(y_labels),
    },
  )
  fig.update_xaxes(tickangle=-55, tickfont={"size": 11}, automargin=True, title={"text": "MAGs" if dataset_type == "mags" else "Metagenome samples", "standoff": 82})
  fig.update_yaxes(
    tickmode="array", tickvals=y_labels, ticktext=y_labels,
    tickfont={"size": 10}, automargin=True,
    title={"text": "KEGG modules", "standoff": 30},
  )
  export = display.copy(); export.insert(0, 'Module', export.index); export = export.reset_index(drop=True)
  return fig, export

def _json_default(value):
  if isinstance(value, (pd.Timestamp, date)):
    return str(value)
  if isinstance(value, (np.integer,)):
    return int(value)
  if isinstance(value, (np.floating,)):
    return float(value)
  return str(value)


def load_persistent_ui_state() -> dict:
  ensure_runtime_dirs()
  if not safe_path_exists(PERSISTENT_UI_STATE_PATH):
    return {}
  try:
    data = json.loads(PERSISTENT_UI_STATE_PATH.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}
  except Exception:
    return {}


def save_persistent_ui_state(**updates) -> None:
  ensure_runtime_dirs()
  state = load_persistent_ui_state()
  state.update({k: v for k, v in updates.items() if v is not None})
  state["updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
  PERSISTENT_UI_STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")


def save_persistent_env_results(results: dict, *, status: str = "completed", note: str = "") -> None:
  """Persist environmental download results beyond tab changes, reruns and browser reloads.

  The file is local runtime state, not a public/static dataset. It is removed by
  the explicit clear-data/cache controls below.
  """
  ensure_runtime_dirs()
  metadata = dict(results.get("metadata", {})) if isinstance(results, dict) else {}
  metadata.update({
    "status": status,
    "note": note,
    "saved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "app_version": APP_VERSION,
    "database_version": DATABASE_VERSION,
    "database_release_date": DATABASE_RELEASE_DATE,
  })
  results["metadata"] = metadata
  with PERSISTENT_ENV_RESULTS_PATH.open("wb") as handle:
    pickle.dump(results, handle, protocol=pickle.HIGHEST_PROTOCOL)
  PERSISTENT_ENV_METADATA_PATH.write_text(json.dumps(metadata, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")


def load_persistent_env_results() -> dict | None:
  if "env_download_results" in st.session_state and isinstance(st.session_state.get("env_download_results"), dict):
    return st.session_state["env_download_results"]
  ensure_runtime_dirs()
  if not safe_path_exists(PERSISTENT_ENV_RESULTS_PATH):
    return None
  try:
    with PERSISTENT_ENV_RESULTS_PATH.open("rb") as handle:
      results = pickle.load(handle)
    if isinstance(results, dict):
      st.session_state["env_download_results"] = results
      st.session_state["env_download_results_loaded_from_disk"] = True
      return results
  except Exception as exc:
    st.warning(f"Could not load persistent environmental results: {exc}")
  return None


def clear_persistent_env_results() -> int:
  removed = 0
  for path in [PERSISTENT_ENV_RESULTS_PATH, PERSISTENT_ENV_METADATA_PATH]:
    try:
      if path.exists():
        path.unlink()
        removed += 1
    except Exception:
      pass
  st.session_state.pop("env_download_results", None)
  st.session_state.pop("env_download_results_loaded_from_disk", None)
  return removed


def clear_api_cache_and_runtime_results() -> int:
  removed = clear_persistent_env_results()
  try:
    if safe_path_exists(API_CACHE_DIR):
      for child in API_CACHE_DIR.glob("**/*"):
        if child.is_file():
          child.unlink()
          removed += 1
      # Remove empty subdirectories, deepest first.
      for child in sorted(API_CACHE_DIR.glob("**/*"), key=lambda x: len(x.parts), reverse=True):
        if child.is_dir():
          try:
            child.rmdir()
          except OSError:
            pass
    API_CACHE_DIR.mkdir(parents=True, exist_ok=True)
  except Exception as exc:
    st.error(f"Could not clear API cache: {exc}")
  try:
    st.cache_data.clear()
  except Exception:
    pass
  return removed


def restore_persistent_runtime_state() -> None:
  ensure_runtime_dirs()
  load_persistent_env_results()


ADMIN_USERS_PATH = APP_CONFIG_DIR / "admin_users.json"
APP_SETTINGS_PATH = APP_CONFIG_DIR / "app_settings.json"
ADMIN_PRIVATE_CREDENTIALS_PATH = APP_CONFIG_DIR / "admin_private_credentials.json"
RUNTIME_STATE_DIR = APP_STATE_DIR / "runtime"
PERSISTENT_ENV_RESULTS_PATH = RUNTIME_STATE_DIR / "environmental_download_results.pkl"
PERSISTENT_ENV_METADATA_PATH = RUNTIME_STATE_DIR / "environmental_download_results.metadata.json"
PERSISTENT_UI_STATE_PATH = RUNTIME_STATE_DIR / "ui_state.json"
API_CACHE_DIR = APP_CACHE_DIR / "api"
CONTACT_LOG_PATH = RUNTIME_STATE_DIR / "contact_messages.jsonl"
ST8_STUDY_REFERENCES_PATH = BASE_DIR / "data" / "st8_study_references.csv"
APP_VERSION = "1.3"
PUBLIC_PROGRAM_NAME = 'Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling'
PUBLIC_PROGRAM_VERSION = "1"
DATABASE_VERSION = "1.5"
DATABASE_RELEASE_DATE = "2026-07-13"
DATABASE_RELEASE_LABEL = "13 July 2026"
def datetime_now_iso() -> str:
  return datetime.now().isoformat(timespec="seconds")

DATABASE_VERSION_LABEL = "GangaMetaG Iron Metagenomic Atlas"
DEFAULT_ADMIN_USER = os.environ.get("CANGAMETAG_ADMIN_USER", "admin").strip() or "admin"
DEFAULT_ADMIN_PASSWORD = os.environ.get("CANGAMETAG_ADMIN_PASSWORD", "").strip()
DEFAULT_SITE_GATE_USER = "admin"
DEFAULT_SITE_GATE_PASSWORD = ""

PUBLIC_MODULE_CATALOG = {
  "article_atlas": ("Atlas do artigo", "Article Atlas"),
  "mags_genomes": ("MAGs e genomas", "MAGs & genomes"),
  "kegg_modules": ("Módulos KEGG — MAGs e metagenomas", "KEGG Modules — MAGs & Metagenomes"),
  "taxonomy": ("Perfis taxonômicos", "Taxonomic profiles"),
  "ko_biomarkers": ("Biomarcadores KO", "KO Biogeochemical Cycles Biomarkers"),
  "iron_metals": ("Ferro e metais", "Iron & metals"),
  "differential_abundance": ("Abundância diferencial", "Differential abundance"),
  "iron_environment_comparison": ("Lagoas amazônicas vs outros ambientes ricos em ferro", "Amazonian Lateritic Lakes vs Other Iron-Rich Environments"),
  "img_functional": ("Anotações funcionais IMG/JGI", "IMG/JGI functional annotations"),
  "st8_references": ("Referências dos estudos ST8", "ST8 study references"),
  "code_reproducibility": ("Códigos e reprodutibilidade", "Code & reproducibility"),
  "final_figures": ("Figuras finais e scripts", "Final figures & scripts"),
  "methods_references": ("Métodos e referências", "Methods & references"),
}


def normalize_username(username: str) -> str:
  return str(username or "").strip().casefold()


def _truthy_setting(value: object) -> bool | None:
  text = str(value if value is not None else "").strip().casefold()
  if text in {"1", "true", "yes", "on", "enabled", "protected"}:
    return True
  if text in {"0", "false", "no", "off", "disabled", "public", ""}:
    return False
  return None


def admin_auth_enabled() -> bool:
  """Return whether a configured administrator account protects the panel.

  The scientific atlas is public by default. Administrator access is enabled
  only when a local hashed account exists or when CANGAMETAG_ADMIN_PASSWORD is
  supplied at first launch. No password or token is embedded in the package.
  """
  try:
    return bool(load_app_settings().get("admin_auth_enabled", True)) and bool(load_admin_users())
  except Exception:
    return False

def hash_password(password: str, salt: str | None = None) -> str:
  salt = salt or py_secrets.token_hex(16)
  digest = hashlib.sha256((salt + str(password or "")).encode("utf-8")).hexdigest()
  return f"sha256${salt}${digest}"


def verify_password(password: str, stored_hash: str) -> bool:
  stored_hash = str(stored_hash or "")
  if stored_hash.startswith("sha256$"):
    try:
      _, salt, expected = stored_hash.split("$", 2)
      digest = hashlib.sha256((salt + str(password or "")).encode("utf-8")).hexdigest()
      return digest == expected
    except Exception:
      return False
  return str(password or "") == stored_hash


def default_admin_user_record() -> dict | None:
  """Create a first-run administrator only from an explicit environment secret."""
  if len(DEFAULT_ADMIN_PASSWORD) < 8:
    return None
  return {
    "username": DEFAULT_ADMIN_USER,
    "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
    "role": "admin",
    "can_edit": True,
    "created_by": "CANGAMETAG_ADMIN_PASSWORD",
    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
  }

def load_admin_users() -> list[dict]:
  """Load local admin/editor users without requiring Streamlit secrets.

  The file is created locally on first use and is ignored by Git. It allows the
  project owner to add additional users capable of editing article metadata and
  technical data-display settings from the Streamlit interface.
  """
  if safe_path_exists(ADMIN_USERS_PATH):
    try:
      data = json.loads(ADMIN_USERS_PATH.read_text(encoding="utf-8"))
      users = data.get("users", data if isinstance(data, list) else [])
      users = [u for u in users if isinstance(u, dict) and normalize_username(u.get("username"))]
      if users:
        return users
    except Exception:
      pass
  default_user = default_admin_user_record()
  if default_user:
    users = [default_user]
    save_admin_users(users, silent=True)
    return users
  return []


def save_admin_users(users: list[dict], silent: bool = False) -> bool:
  try:
    ADMIN_USERS_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": 1, "users": users}
    ADMIN_USERS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
  except Exception as exc:
    if not silent:
      st.error(f"Could not save admin users locally: {exc}")
    return False


def authenticate_user(username: str, password: str) -> dict | None:
  """Authenticate only against the local hashed user database."""
  uname = normalize_username(username)
  for user in load_admin_users():
    if normalize_username(user.get("username")) == uname and verify_password(password, user.get("password_hash", "")):
      return user
  return None

def is_admin_authenticated() -> bool:
  """Return whether admin tools are available in the current session.

  The atlas is public by default, while administrator tools require the local
  administrator password on first run. The administrator may disable this
  protection later from the interface.
  """
  if not admin_auth_enabled():
    return False
  return bool(st.session_state.get("admin_authenticated", False))


def render_admin_only_download_notice(feature_label: str) -> None:
  st.info(txt(
    f"{feature_label} é uma operação restrita ao admin. Usuários públicos visualizam apenas os arquivos e resultados já persistidos localmente.",
    f"{feature_label} is restricted to admin users. Public users only view files and results already persisted locally.",
  ))


def upsert_admin_user(username: str, password: str, role: str = "editor", created_by: str = "admin") -> tuple[bool, str]:
  username = str(username or "").strip()
  if not username:
    return False, "Username is required."
  if not password or len(str(password)) < 4:
    return False, "Password must have at least 4 characters."
  users = load_admin_users()
  uname = normalize_username(username)
  record = {
    "username": username,
    "password_hash": hash_password(password),
    "role": role,
    "can_edit": True,
    "created_by": created_by,
    "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
  }
  for idx, user in enumerate(users):
    if normalize_username(user.get("username")) == uname:
      users[idx] = {**user, **record}
      ok = save_admin_users(users)
      return ok, "User updated." if ok else "Could not update user."
  users.append(record)
  ok = save_admin_users(users)
  return ok, "User added." if ok else "Could not add user."


def change_admin_password(username: str, current_password: str, new_password: str) -> tuple[bool, str]:
  if not new_password or len(str(new_password)) < 4:
    return False, "New password must have at least 4 characters."
  if not admin_auth_enabled():
    target_user = str(username or DEFAULT_ADMIN_USER).strip() or DEFAULT_ADMIN_USER
    ok, message = upsert_admin_user(target_user, new_password, role="admin", created_by="optional_local_setup")
    if not ok:
      return ok, message
    settings = load_app_settings()
    settings["admin_auth_enabled"] = True
    settings["admin_auth_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
    if not save_app_settings(settings):
      return False, "Password was saved, but admin protection could not be enabled in app settings."
    st.session_state["admin_authenticated"] = True
    st.session_state["admin_username"] = target_user
    st.session_state["admin_role"] = "admin"
    return True, "Optional admin password protection enabled successfully."
  auth_user = authenticate_user(username, current_password)
  if auth_user is None:
    return False, "Current password is invalid."
  return upsert_admin_user(username, new_password, role=auth_user.get("role", "admin"), created_by=username)


def delete_admin_user(username: str) -> tuple[bool, str]:
  uname = normalize_username(username)
  current = normalize_username(st.session_state.get("admin_username", ""))
  if uname == current:
    return False, "You cannot remove the currently logged-in user."
  users = load_admin_users()
  remaining = [u for u in users if normalize_username(u.get("username")) != uname]
  if len(remaining) == len(users):
    return False, "User not found."
  if not remaining:
    return False, "At least one admin/editor user is required."
  ok = save_admin_users(remaining)
  return ok, "User removed." if ok else "Could not remove user."

APP_TITLE = 'Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling'

st.set_page_config(page_title=APP_TITLE, page_icon="🧬", layout="wide")

st.markdown(
  """
<style>
  /* Publication-style interface: hide Streamlit developer/browser controls. */
  header[data-testid="stHeader"],
  div[data-testid="stToolbar"],
  div[data-testid="stDecoration"],
  div[data-testid="stStatusWidget"],
  #MainMenu, footer {
    display: none !important;
    visibility: hidden !important;
    height: 0 !important;
  }
  button[title="Rerun"], button[title*="Rerun"],
  button[title="Settings"], button[title*="Settings"],
  button[title="Print"], button[title*="Print"] {
    display: none !important;
    visibility: hidden !important;
  }
  :root {
    --itv-teal: #008a83;
    --itv-teal-dark: #005f5b;
    --itv-teal-bright: #00b6aa;
    --itv-yellow: #f2b705;
    --itv-gold: #ffd166;
    --itv-forest: #0f3f3c;
    --itv-gray: #60666c;
    --itv-soft: #f5faf9;
    --itv-ink: #0f172a;
  }
  .stApp {
    background:
      radial-gradient(circle at 8% -8%, rgba(0,182,170,.22), transparent 34rem),
      radial-gradient(circle at 86% 0%, rgba(255,209,102,.24), transparent 31rem),
      linear-gradient(180deg, #ffffff 0%, #f5fffd 46%, #f2f8f7 100%);
  }
  .block-container {padding-top: 1.25rem; padding-bottom: 2.4rem; max-width: 1580px;}
  .itv-topbar {
    display:flex; align-items:center; justify-content:center; gap:.55rem; flex-wrap:wrap;
    padding:.72rem .85rem; margin-bottom:.95rem; border-radius:1.15rem;
    background:rgba(255,255,255,.88); border:1px solid rgba(0,138,131,.18);
    box-shadow:0 10px 30px rgba(15,23,42,.06); backdrop-filter: blur(8px);
  }
  .itv-kicker {
    font-size:.78rem; letter-spacing:.16em; text-transform:uppercase; color:var(--itv-teal-dark);
    font-weight:800; margin-bottom:.45rem;
  }
  .hero {
    position:relative; overflow:hidden; padding:1.55rem 1.65rem 1.45rem; border-radius:1.45rem;
    background:linear-gradient(135deg, rgba(255,255,255,.98), rgba(238,250,248,.96));
    color:var(--itv-ink); margin-bottom:1.1rem;
    border:1px solid rgba(0,138,131,.22); box-shadow:0 28px 70px rgba(15,23,42,.13), 0 0 0 1px rgba(255,255,255,.70) inset;
  }
  .hero:before {
    content:""; position:absolute; inset:0 auto 0 0; width:9px;
    background:linear-gradient(180deg, var(--itv-yellow), var(--itv-teal));
  }
  .hero:after {
    content:""; position:absolute; width:340px; height:340px; right:-150px; top:-170px;
    background:radial-gradient(circle, rgba(0,138,131,.17), transparent 70%);
  }
  .hero h1 {font-size:clamp(1.75rem, 3.2vw, 2.65rem); line-height:1.08; margin:.05rem 0 .65rem; color:#123534; overflow-wrap:anywhere;}
  .hero p {font-size:1.03rem; margin:.25rem 0; color:#334155; max-width:980px;}
  .hero .authors {
    margin-top:.85rem; padding:.85rem 1rem; border-radius:1rem;
    background:rgba(255,255,255,.72); border:1px solid rgba(0,138,131,.16); color:#1f2937;
  }
  .hero .authors b {color:var(--itv-teal-dark);}
  .brand-card {
    min-height:100%; display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding:1.05rem; border-radius:1.35rem; background:#fff;
    border:1px solid rgba(0,138,131,.20); box-shadow:0 18px 46px rgba(15,23,42,.09);
  }
  .brand-caption {font-size:.82rem; color:var(--itv-gray); text-align:center; margin-top:.35rem;}
  .card {
    padding:1rem; border-radius:1rem; border:1px solid rgba(0,138,131,.18);
    background:rgba(255,255,255,.82); box-shadow:0 8px 22px rgba(15,23,42,.06);
  }
  .section-title {
    display:inline-flex; align-items:center; gap:.55rem; padding:.35rem .75rem; margin:.25rem 0 .75rem;
    color:var(--itv-teal-dark); background:rgba(0,138,131,.08); border:1px solid rgba(0,138,131,.18);
    border-radius:999px; font-weight:800;
  }
  .pill {
    display:inline-block; padding:.25rem .65rem; margin:.15rem .18rem .15rem 0; border-radius:999px;
    background:rgba(0,138,131,.09); color:#075e5a; border:1px solid rgba(0,138,131,.16);
    font-size:.85rem; font-weight:650; white-space:normal;
  }
  .small-note {font-size:.88rem; color:#475569;}
  div[data-testid="stMetric"] {
    background:rgba(255,255,255,.92); border:1px solid rgba(0,138,131,.16); padding:.75rem;
    border-radius:1rem; box-shadow:0 8px 20px rgba(15,23,42,.05);
  }
  div[data-testid="stMetricValue"] {color:#075e5a;}
  .stTabs [data-baseweb="tab-list"] {
    gap:.45rem;
    overflow-x:auto !important;
    scrollbar-width:auto;
    scrollbar-color:#008a83 #e5f4f2;
    padding-bottom:.45rem;
  }
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {height:24px;}
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-track {background:#e5f4f2; border-radius:999px;}
  .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar-thumb {background:#008a83; border-radius:999px; border:3px solid #e5f4f2;}
  .stTabs [data-baseweb="tab"] {
    border-radius:999px; padding:.72rem 1.28rem; background:rgba(255,255,255,.78);
    border:1px solid rgba(0,138,131,.13); min-width:max-content;
  }
  .stTabs [aria-selected="true"] {
    background:linear-gradient(90deg, rgba(0,138,131,.16), rgba(242,183,5,.13));
    color:#075e5a; font-weight:800;
  }
  .stButton > button, .stDownloadButton > button {
    border-radius:999px; border:1px solid rgba(0,138,131,.30);
    background:linear-gradient(90deg, #008a83, #08756f); color:white; font-weight:800;
  }
  .stButton > button:hover, .stDownloadButton > button:hover {
    border-color:#f2b705; color:white; box-shadow:0 10px 24px rgba(0,138,131,.20);
  }

  .block-container {
    padding-top: 1.25rem !important;
    padding-bottom: 3.5rem !important;
  }
  .itv-topbar {
    row-gap: .45rem;
    min-height: 3.4rem;
    margin-top: .25rem;
  }
  .hero {
    overflow: visible;
  }
  .hero h1 {
    overflow-wrap: anywhere;
    line-height: 1.05;
  }
  @media (max-width: 900px) {
    .block-container { padding-top: 1.0rem !important; }
    .itv-topbar { padding-right: 0; }
  }

  .stTabs [data-baseweb="tab-list"] {
    min-height: 64px;
    border-radius: 1.25rem;
    background: rgba(255,255,255,.72);
    border: 1px solid rgba(0,138,131,.12);
    box-shadow: 0 12px 28px rgba(15,23,42,.06) inset;
  }
  .stDataFrame, div[data-testid="stDataFrame"] {
    border-radius: 1rem !important;
    overflow: hidden;
    border: 1px solid rgba(0,138,131,.15);
    box-shadow: 0 12px 30px rgba(15,23,42,.06);
  }
  .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] > div {
    border-radius: .85rem !important;
  }
  .admin-user-card {
    padding: .85rem 1rem;
    border-radius: 1rem;
    border: 1px solid rgba(0,138,131,.18);
    background: linear-gradient(135deg, rgba(255,255,255,.96), rgba(239,255,252,.88));
    box-shadow: 0 10px 28px rgba(15,23,42,.06);
  }
  .gate-shell {
    min-height: 78vh; display:flex; align-items:center; justify-content:center;
    padding: 2rem 1rem;
  }
  .gate-card {
    width:min(920px, 100%); padding:2.2rem; border-radius:1.8rem;
    background:
      radial-gradient(circle at 12% 0%, rgba(242,183,5,.22), transparent 28rem),
      radial-gradient(circle at 100% 20%, rgba(0,138,131,.22), transparent 28rem),
      linear-gradient(135deg, rgba(255,255,255,.97), rgba(237,255,251,.94));
    border:1px solid rgba(0,138,131,.22); box-shadow:0 34px 90px rgba(15,23,42,.16);
  }
  .gate-card h1 {font-size:clamp(2rem, 4.2vw, 3.25rem); line-height:1.04; color:#123534; margin:.2rem 0 .85rem;}
  .gate-card p {font-size:1.08rem; color:#334155; max-width:760px;}
  .gate-kicker {font-size:.82rem; letter-spacing:.18em; text-transform:uppercase; font-weight:900; color:#075e5a;}
  .source-audit-ok {color:#047857; font-weight:800;}
  .source-audit-missing {color:#b45309; font-weight:800;}

  div[data-testid="stProgress"] > div > div > div > div {
    height: 1.05rem !important;
    border-radius: 999px !important;
    background: linear-gradient(90deg, #008a83, #f2b705) !important;
  }
  div[data-testid="stProgress"] > div > div > div {
    height: 1.05rem !important;
    border-radius: 999px !important;
    background: rgba(0,138,131,.12) !important;
  }
  .download-status-card {
    padding: 1rem 1.15rem;
    margin: .65rem 0;
    border-radius: 1rem;
    border: 1px solid rgba(0,138,131,.20);
    background: linear-gradient(135deg, rgba(255,255,255,.96), rgba(232,255,251,.92));
    box-shadow: 0 12px 30px rgba(15,23,42,.08);
  }
  .download-status-card b { color: #005f5b; }
  .version-card {
    padding:.75rem .95rem; border-radius:1rem; border:1px solid rgba(0,138,131,.20);
    background:linear-gradient(135deg, rgba(255,255,255,.94), rgba(239,255,252,.86));
    box-shadow:0 8px 22px rgba(15,23,42,.05); font-size:.88rem; color:#334155;
  }
  .version-card b { color:#075e5a; }
  .persistent-state-note {
    padding:.75rem .95rem; border-radius:1rem; border:1px solid rgba(0,138,131,.20);
    background:rgba(237,255,251,.86); color:#1f3f46; margin:.55rem 0;
  }
  .visitor-counter-card {
    padding:.75rem .95rem; margin-top:.65rem; border-radius:1rem;
    border:1px solid rgba(0,138,131,.18);
    background:linear-gradient(135deg, rgba(255,255,255,.95), rgba(238,255,251,.90));
    box-shadow:0 8px 22px rgba(15,23,42,.05); color:#263b3d; font-size:.88rem;
  }
  .visitor-counter-card b { color:#075e5a; }
  .visitor-chip {
    display:inline-flex; align-items:center; gap:.25rem; padding:.20rem .48rem; margin:.12rem .10rem;
    border-radius:999px; background:rgba(0,138,131,.08); border:1px solid rgba(0,138,131,.14);
    white-space:nowrap;
  }
  .public-visitor-footer {
    margin:1.2rem 0 .4rem; padding:.7rem .9rem; border-radius:1rem;
    background:rgba(255,255,255,.90); border:1px solid rgba(0,138,131,.16);
    box-shadow:0 8px 20px rgba(15,23,42,.05); font-size:.88rem; color:#263b3d;
  }
  .contact-card {
    margin:1.2rem 0; padding:1rem 1.1rem; border-radius:1.1rem;
    background:linear-gradient(135deg, rgba(255,255,255,.97), rgba(237,255,251,.90));
    border:1px solid rgba(0,138,131,.18); box-shadow:0 10px 24px rgba(15,23,42,.06);
  }
  div[role="radiogroup"] {
    gap:.35rem;
  }


/* Every image/Plotly block owns its vertical space and cannot overlap the next figure. */
div[data-testid="stImage"], div[data-testid="stPlotlyChart"], div[data-testid="stVegaLiteChart"] {
  position: relative !important;
  display: block !important;
  clear: both !important;
  width: 100% !important;
  max-width: 100% !important;
  overflow-x: auto !important;
  margin-bottom: 1.1rem !important;
}
div[data-testid="stImage"] img {
  max-width: 100% !important;
  height: auto !important;
  object-fit: contain !important;
}
</style>
""",
  unsafe_allow_html=True,
)


LANGUAGE_LABEL = st.sidebar.selectbox(
  "Language / Idioma",
  ["Português", "English"],
  index=1,
  help="Choose the interface language. Data columns keep the original names from the supplementary tables.",
  key="sidebar_language_idioma",
)
IS_PT = LANGUAGE_LABEL == "Português"

PLOTLY_CONFIG = {
  "displaylogo": False,
  "responsive": True,
  "toImageButtonOptions": {
    "format": "png",
    "filename": "amazonian_lateritic_lakes_figure_high_resolution",
    "height": 1600,
    "width": 2400,
    "scale": 3,
  },
}


def safe_filename(value: object, default: str = "figure") -> str:
  name = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value or default)).strip("_")
  return name[:140] or default






# -----------------------------------------------------------------------------
# Robust Streamlit widget-key and table helpers
# -----------------------------------------------------------------------------
_WIDGET_KEY_COUNTER: dict[str, int] = {}


def _safe_key_text(value: object) -> str:
  """Return a compact Streamlit-safe key component for arbitrary values."""
  text = str(value) if value is not None else "none"
  text = re.sub(r"[^A-Za-z0-9_\-]+", "_", text)
  text = re.sub(r"_+", "_", text).strip("_")
  return (text[:80] or "widget")


def unique_widget_key(base: object = None, shape: object = None, *extra: object, prefix: str = "widget") -> str:
  """Create a unique, stable and Streamlit-safe key for any widget.

  The function is intentionally tolerant: it accepts None, non-tuple shapes,
  empty DataFrames, repeated calls inside tabs/expanders/loops, and legacy calls
  that pass additional context values before the prefix keyword. A deterministic
  digest keeps keys short while a per-run counter disambiguates repeated widgets
  with the same semantic context.
  """
  prefix_txt = _safe_key_text(prefix)
  base_txt = _safe_key_text(base)

  if shape is None:
    shape_txt = "noshape"
  else:
    try:
      if isinstance(shape, tuple):
        shape_items = shape
      elif isinstance(shape, list):
        shape_items = tuple(shape)
      elif hasattr(shape, "__iter__") and not isinstance(shape, (str, bytes, dict)):
        shape_items = tuple(shape)
      else:
        shape_items = (shape,)
      shape_txt = "x".join(_safe_key_text(x) for x in shape_items) or "shape"
    except Exception:
      shape_txt = _safe_key_text(shape)

  extra_txt = "_".join(_safe_key_text(x) for x in extra if x is not None)
  raw_parts = [prefix_txt, base_txt, shape_txt]
  if extra_txt:
    raw_parts.append(extra_txt)
  raw = "|".join(raw_parts)
  digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:10]
  candidate = _safe_key_text("_".join(raw_parts + [digest]))

  count = _WIDGET_KEY_COUNTER.get(candidate, 0)
  _WIDGET_KEY_COUNTER[candidate] = count + 1
  if count:
    candidate = f"{candidate}_{count}"
  return candidate


def dataframe_map_compat(df: pd.DataFrame, func):
  """Element-wise DataFrame transform compatible with pandas 1.x, 2.x and newer."""
  if df is None:
    return df
  if hasattr(df, "map"):
    return df.map(func)
  return df.applymap(func)


def _clean_table_cell(value: object) -> object:
  """Make nested values displayable in st.dataframe without destroying scalars."""
  if isinstance(value, (list, tuple, set)):
    return "; ".join(map(str, value))
  if isinstance(value, dict):
    return "; ".join(f"{k}: {v}" for k, v in value.items())
  return value


def admin_code_access_enabled(key: str = "global") -> bool:
  """Return True only when the admin explicitly enables code preview/download."""
  if not is_admin_authenticated():
    return False
  return st.checkbox(
    txt("Admin: habilitar visualização/download de códigos nesta seção", "Admin: enable code preview/download in this section"),
    value=False,
    key=f"admin_enable_code_access_{key}",
    help=txt("Quando desmarcado, usuários veem apenas nomes, inputs e métodos; o código completo fica oculto.", "When unchecked, users see only names, inputs and methods; full code remains hidden."),
  )


def bold_axis_layout(fig, *, x_size: int = 14, y_size: int = 14, title_size: int = 16):
  """Make axes and tick labels readable in both app and static exports."""
  try:
    fig.update_xaxes(
      title_font=dict(size=title_size, family="Arial Black, Arial", color="#111827"),
      tickfont=dict(size=x_size, family="Arial Black, Arial", color="#111827"),
      automargin=True,
    )
    fig.update_yaxes(
      title_font=dict(size=title_size, family="Arial Black, Arial", color="#111827"),
      tickfont=dict(size=y_size, family="Arial Black, Arial", color="#111827"),
      automargin=True,
    )
    fig.update_layout(font=dict(family="Arial, Helvetica, sans-serif", size=max(12, min(x_size, y_size)), color="#111827"))
  except Exception:
    pass
  return fig


def show_plot_source_table(df: pd.DataFrame, key: str, label: str = "Source table"):
  """Show an explicitly identified exact source table below a plot."""
  if isinstance(df, pd.DataFrame) and not df.empty:
    panel_id = str(key).replace("_", " ").replace("-", " ").strip()
    expander_label = txt(
      f"Dados utilizados no painel {panel_id} — {label}",
      f"Source data for panel {panel_id} — {label}",
    )
    with st.expander(expander_label, expanded=False):
      st.markdown(f"**{panel_id} — {label}**")
      show_table(df, f"{key}_source_table", height=360)
      csv_button(df, f"{safe_filename(key)}_source_table.csv", txt("Baixar tabela", "Download table"))

def _figure_export_size(fig, min_width: int = 2400, min_height: int = 1600) -> tuple[int, int]:
  """Estimate a safe static-export size from a Plotly figure.

  Plotly/kaleido can clip long tick labels when the browser-rendered chart uses
  container width but the exported image uses a fixed canvas. This helper makes
  export dimensions follow the figure layout and the number of category labels.
  """
  width = int(getattr(fig.layout, "width", None) or min_width)
  height = int(getattr(fig.layout, "height", None) or min_height)
  width = max(width, min_width)
  height = max(height, min_height)
  # Extra space for many traces/legends or long category axes.
  try:
    n_traces = len(fig.data)
    if n_traces > 18:
      width = max(width, 3000)
      height = max(height, 1800)
    if n_traces > 35:
      width = max(width, 3600)
  except Exception:
    pass
  meta = getattr(fig.layout, "meta", None)
  preserve_cell_geometry = isinstance(meta, dict) and bool(meta.get("preserve_cell_geometry"))
  if preserve_cell_geometry:
    return min(width, 16000), min(height, 30000)
  return min(width, 7600), min(height, 7600)


def prepare_plotly_for_publication_export(fig):
  """Apply publication-safe styling while preserving declared heatmap labels."""
  try:
    top_margin = max(70, int(getattr(fig.layout.margin, "t", 70) or 70))
    legend = getattr(fig.layout, "legend", None)
    title_obj = getattr(fig.layout, "title", None)
    title_text = str(getattr(title_obj, "text", "") or "").strip()
    if title_text.casefold() in {"undefined", "none", "null", "nan", "na", "n/a"}:
      title_text = ""
      fig.update_layout(title=dict(text=""))
    layout_meta = getattr(fig.layout, "meta", None)
    layout_meta = dict(layout_meta) if isinstance(layout_meta, dict) else {}
    preserve_legend_position = bool(layout_meta.get("preserve_legend_position", False))
    if getattr(legend, "orientation", None) == "h" and not preserve_legend_position:
      if title_text:
        top_margin = max(top_margin, 145)
        fig.update_layout(
          title=dict(y=0.985, x=0.01, xanchor="left", yanchor="top"),
          legend=dict(orientation="h", y=1.005, yanchor="bottom", x=0.0, xanchor="left"),
        )
      else:
        top_margin = max(55, min(top_margin, 72))
        fig.update_layout(
          legend=dict(orientation="h", y=0.995, yanchor="bottom", x=0.0, xanchor="left"),
        )
    fig.update_layout(
      template="plotly_white",
      paper_bgcolor="white",
      plot_bgcolor="white",
      font=dict(family="Arial, Helvetica, sans-serif", size=12, color="#263238"),
      margin=dict(
        l=max(10, int(getattr(fig.layout.margin, "l", 10) or 10)),
        r=max(30, int(getattr(fig.layout.margin, "r", 10) or 10)),
        t=top_margin,
        b=max(90, int(getattr(fig.layout.margin, "b", 90) or 90)),
      ),
    )
    bold_axis_layout(fig, x_size=14, y_size=14, title_size=17)
    heatmap = next((trace for trace in fig.data if str(getattr(trace, "type", "")).lower() in {"heatmap", "image"}), None)
    if heatmap is not None:
      heatmap_labels = [str(value) for value in list(getattr(heatmap, "y", []) or [])]
      heatmap_meta = getattr(fig.layout, "meta", None)
      heatmap_meta = dict(heatmap_meta) if isinstance(heatmap_meta, dict) else {}
      if not bool(heatmap_meta.get("allow_sparse_y_ticks", False)):
        heatmap_meta.update({
          "preserve_cell_geometry": True,
          "force_all_y_ticks": True,
          "all_y_labels_visible": True,
          "cell_height_px": int(heatmap_meta.get("cell_height_px", 20 if len(heatmap_labels) > 300 else 24)),
          "source_row_count": len(heatmap_labels),
        })
        fig.update_layout(meta=heatmap_meta)
    fig = polish_heatmap_layout(fig, min_column_px=22.0, title_chars=54)
    fig = sparsify_heatmap_y_ticks(fig, min_label_gap_px=16.0, max_visible_ticks=90)
    meta = getattr(fig.layout, "meta", None)
    meta = meta if isinstance(meta, dict) else {}
    if bool(meta.get("force_all_y_ticks") or meta.get("all_y_labels_visible")):
      heatmap = next((trace for trace in fig.data if str(getattr(trace, "type", "")).lower() == "heatmap"), None)
      labels = [str(value) for value in list(getattr(heatmap, "y", []) or [])] if heatmap is not None else []
      if labels:
        longest = max(len(value) for value in labels)
        required_left = min(1100, max(280, 12 * min(longest, 82)))
        fig.update_layout(margin=dict(l=max(required_left, int(getattr(fig.layout.margin, "l", 0) or 0))))
  except Exception as exc:
    LOGGER.exception("Plotly publication formatting failed: %s", exc)
  return fig


def plotly_image_bytes(fig, fmt: str, width: int | None = None, height: int | None = None, scale: int = 3):
  """Return validated image bytes through Kaleido or local Chromium fallback."""
  if str(os.environ.get("CANGAMETAG_DISABLE_STATIC_EXPORT", "")).strip().casefold() in {"1", "true", "yes", "on"}:
    LAST_PLOTLY_EXPORT_ERRORS[str(fmt).lower()] = "Static export disabled for the current validation run."
    return None
  try:
    f = go.Figure(fig)
    f = prepare_plotly_for_publication_export(f)
    meta = getattr(f.layout, "meta", None)
    require_title = isinstance(meta, dict) and bool(meta.get("require_nonempty_title", False))
    validate_visible_text(f, require_title=require_title)
    w, h = _figure_export_size(f, min_width=2400, min_height=1600)
    width = int(width or w)
    height = int(height or h)
    preserve_cell_geometry = isinstance(meta, dict) and bool(meta.get("preserve_cell_geometry"))
    effective_scale = 1 if preserve_cell_geometry else int(scale)
    result, backend = export_plotly_bytes(
      f, str(fmt).lower(), width=width, height=height, scale=effective_scale,
    )
    LAST_PLOTLY_EXPORT_ERRORS.pop(str(fmt).lower(), None)
    LAST_PLOTLY_EXPORT_ERRORS[f"{str(fmt).lower()}_backend"] = backend
    return result
  except Exception as exc:
    message = f"{type(exc).__name__}: {exc}"
    LAST_PLOTLY_EXPORT_ERRORS[str(fmt).lower()] = message
    LOGGER.exception("Plotly %s export failed: %s", fmt, exc)
    return None


def _barplot_method_summary(fig) -> tuple[str, str] | None:
  """Return a concise post-figure method/result explanation for every barplot."""
  try:
    if not any(str(getattr(t, "type", "")).lower() == "bar" for t in fig.data):
      return None
    title_obj = getattr(fig.layout, "title", None)
    title = str(getattr(title_obj, "text", "") or "").lower()
    if "contrast" in title or "contraste" in title:
      pt = (
        "Método: contraste descritivo calculado como log2((média nas lagoas amazônicas + 1) / "
        "(média no grupo externo + 1)). Os marcadores classificados como mais fortes são os que apresentam "
        "maior valor absoluto desse log2 ratio após os filtros ativos; valores positivos favorecem as lagoas "
        "amazônicas e valores negativos favorecem os ambientes externos. Este ranking é descritivo e não implica "
        "significância inferencial sem p/q explicitamente reportado."
      )
      en = (
        "Method: descriptive contrast calculated as log2((Amazonian-lake mean + 1) / "
        "(external-group mean + 1)). Markers classified as strongest are those with the largest absolute log2 ratio "
        "after the active filters; positive values favor Amazonian lakes and negative values favor external "
        "environments. This ranking is descriptive and does not imply inferential significance unless p/q values "
        "are explicitly reported."
      )
      return pt, en
    if "taxonom" in title or "abundance" in title or "abundância" in title:
      return (
        "Método: as barras representam contagens ou abundâncias relativas da tabela-fonte após os filtros ativos; "
        "a ordenação segue o valor exibido. Diferença estatística só é concluída quando os testes e valores de p/q "
        "associados são explicitamente apresentados abaixo da figura.",
        "Method: bars represent counts or relative abundances from the source table after active filters; ordering "
        "follows the displayed value. Statistical difference is concluded only when the associated tests and p/q "
        "values are explicitly reported below the figure."
      )
    return (
      "Método: o barplot foi construído com os valores da tabela-fonte após os filtros ativos; o comprimento de cada "
      "barra corresponde ao valor numérico exibido e a ordenação segue essa métrica. O resultado é descritivo, salvo "
      "quando testes estatísticos e valores de p/q são explicitamente reportados abaixo da figura.",
      "Method: the barplot was built from source-table values after active filters; each bar length corresponds to "
      "the displayed numeric value and ordering follows that metric. The result is descriptive unless statistical "
      "tests and p/q values are explicitly reported below the figure."
    )
  except Exception:
    return None



def _infer_figure_audit_context(chart_key: str, fig) -> dict[str, str]:
  key = str(chart_key or "").lower()
  if "functional" in key:
    return {"input": "Supplementary Table 6 and/or Supplementary Table 8 packaged workbooks", "method": "Exact annotation counts or row-wise z-scores; no synthetic values.", "script": "src/functional_annotations.py; app.py:functional_annotations_tab"}
  if "boxplot" in key:
    return {"input": "Exact packaged supplementary-table rows and biological sample columns", "method": "Boxplot from one aggregated biological-sample value per displayed category; parametric and non-parametric results are reported when available.", "script": "app.py:publication_boxplot_panel"}
  if "taxonomy" in key or "alpha" in key or "beta" in key:
    return {"input": "Supplementary Table 1 and packaged CDS taxonomy files", "method": "Taxonomic abundance/diversity values computed from packaged study data; no simulated observations.", "script": "app.py:taxonomy_tab/taxonomy_diversity_panel"}
  if "rda" in key or "nmds" in key:
    return {"input": "Packaged genus abundance and environmental study tables", "method": "Canonical article ordination implementation shared by static and interactive figures.", "script": "src/publication_ordination.py; src/publication_rda.py"}
  if "kegg" in key or "module" in key:
    return {"input": "Packaged KEMET/KEGG module matrices", "method": "Exact module-status or completeness values from source matrices; missing data remain missing.", "script": "src/kegg_modules.py; app.py"}
  return {"input": "Packaged supplementary tables or derived tables identified by the active module", "method": "Exact plotted values after the active filters; no synthetic or invented observations.", "script": "app.py and the final module script listed in Code & reproducibility"}


def _plotly_exact_value_table(fig) -> pd.DataFrame:
  traces = list(getattr(fig, "data", []) or [])
  heat = next((trace for trace in traces if str(getattr(trace, "type", "")).lower() == "heatmap"), None)
  if heat is not None:
    raw_z = getattr(heat, "z", None)
    z = np.asarray([] if raw_z is None else raw_z, dtype=object)
    if z.ndim == 2:
      raw_x, raw_y = getattr(heat, "x", None), getattr(heat, "y", None)
      x = [str(v) for v in (list(raw_x) if raw_x is not None else range(z.shape[1]))]
      y = [str(v) for v in (list(raw_y) if raw_y is not None else range(z.shape[0]))]
      if len(x) == z.shape[1] and len(y) == z.shape[0]:
        out = pd.DataFrame(z, columns=x)
        out.insert(0, "row_label", y)
        return out
  rows = []
  for trace_index, trace in enumerate(traces):
    trace_type = str(getattr(trace, "type", "") or "")
    name = str(getattr(trace, "name", "") or f"trace_{trace_index + 1}")
    raw_x, raw_y = getattr(trace, "x", None), getattr(trace, "y", None)
    x = list(raw_x) if raw_x is not None else []
    y = list(raw_y) if raw_y is not None else []
    for i in range(max(len(x), len(y))):
      rows.append({"trace": name, "trace_type": trace_type, "point_index": i,
                   "x": x[i] if i < len(x) else None, "y": y[i] if i < len(y) else None})
  return pd.DataFrame(rows)


def _audit_table_block(frame: pd.DataFrame | None, label: str, key: str) -> None:
  if frame is None or not isinstance(frame, pd.DataFrame) or frame.empty:
    st.caption(txt(f"{label}: não fornecida para esta figura.", f"{label}: not supplied for this figure."))
    return
  st.caption(f"{label}: {len(frame):,} rows × {len(frame.columns):,} columns")
  show_table(frame.head(1500), f"{key}_{safe_filename(label)}_preview", height=420)
  csv_button(frame, f"{safe_filename(key)}_{safe_filename(label)}.csv", txt("Baixar tabela completa", "Download complete table"), key=f"{key}_{safe_filename(label)}_csv")


def _figure_display_identity(fig, chart_key: str) -> tuple[str, str]:
  """Return a specific, user-facing figure/panel identifier and title."""
  title = str(getattr(getattr(fig.layout, "title", None), "text", "") or "").strip()
  title = re.sub(r"<[^>]+>", "", title).strip()
  if title.casefold() in {"undefined", "none", "null", "nan", "na", "n/a"}:
    title = ""
  key = str(chart_key or "interactive_panel").strip()
  match = re.search(r"(?i)\b((?:supplementary\s*)?figure\s*[A-Za-z]?\d+[A-Za-z]?)\b", title)
  if not match:
    match = re.search(r"(?i)\b((?:supplementary[_-]?)?figure[_-]?[A-Za-z]?\d+[A-Za-z]?)\b", key)
  if match:
    identifier = re.sub(r"[_-]+", " ", match.group(1)).strip()
  else:
    identifier = "Interactive panel " + key
  if not title:
    title = key.replace("_", " ").replace("-", " ").strip()
  return identifier, title


def render_figure_audit_expander(
  fig, chart_key: str, *, input_table: pd.DataFrame | None = None,
  processed_table: pd.DataFrame | None = None, output_table: pd.DataFrame | None = None,
  method: str | None = None, input_source: str | None = None,
  script: str | None = None, instructions: str | None = None,
) -> None:
  context = _infer_figure_audit_context(chart_key, fig)
  plotted = _plotly_exact_value_table(fig)
  figure_id, figure_title = _figure_display_identity(fig, chart_key)
  expander_label = txt(
    f"Dados utilizados em {figure_id} — {figure_title}",
    f"Source data for {figure_id} — {figure_title}",
  )
  with st.expander(expander_label, expanded=False):
    st.markdown(f"**{figure_id} — {figure_title}**")
    st.markdown(f"**{txt('Método', 'Method')}:** {method or context['method']}")
    st.markdown(f"**{txt('Input/fonte', 'Input/source')}:** {input_source or context['input']}")
    final_script = script or context['script']
    st.markdown(f"**{txt('Script final', 'Final script')}:** `{final_script}`")
    if instructions:
      st.markdown(f"**{txt('Instruções', 'Instructions')}:** {instructions}")
    st.caption(txt(
      "Política de dados: somente valores reais das tabelas e arquivos empacotados são usados; ausências não são substituídas por valores sintéticos.",
      "Data policy: only real values from packaged tables and files are used; missing values are not replaced by synthetic values."
    ))
    tabs = st.tabs([txt("Fonte", "Source"), txt("Processada", "Processed"), txt("Output", "Output"), txt("Valores plotados", "Plotted values")])
    with tabs[0]: _audit_table_block(input_table, txt("Tabela-fonte", "Source table"), f"{chart_key}_source")
    with tabs[1]: _audit_table_block(processed_table, txt("Tabela processada", "Processed table"), f"{chart_key}_processed")
    with tabs[2]: _audit_table_block(output_table, txt("Tabela de output/estatística", "Output/statistics table"), f"{chart_key}_output")
    with tabs[3]: _audit_table_block(plotted, txt("Valores exatos da figura", "Exact figure values"), f"{chart_key}_plotted")

def render_plotly_downloadable(
  fig, key: str, basename: str | None = None, height_note: bool = False,
  *, audit_input_table: pd.DataFrame | None = None,
  audit_processed_table: pd.DataFrame | None = None,
  audit_output_table: pd.DataFrame | None = None,
  audit_method: str | None = None,
  audit_input_source: str | None = None,
  audit_script: str | None = None,
  audit_instructions: str | None = None,
):
  """Render a Plotly figure and provide high-resolution PNG/PDF/SVG/HTML downloads.

  The explicit export path uses white backgrounds, dynamic canvas sizes and
  SVG/HTML fallbacks, which fixes the previous taxonomy PDF/PNG problem where
  labels and legends were clipped or exported as unreadable black blocks.
  """
  chart_key = str(key)
  base = safe_filename(basename or chart_key)
  fig = prepare_plotly_for_publication_export(fig)
  fig = compact_heatmap_colorbars(fig, length=None, thickness=12, top=None)
  layout_meta_initial = getattr(fig.layout, "meta", None)
  require_title = isinstance(layout_meta_initial, dict) and bool(layout_meta_initial.get("require_nonempty_title", False))
  try:
    validate_visible_text(fig, require_title=require_title)
  except ValueError as exc:
    LOGGER.error("Figure text validation failed for %s: %s", chart_key, exc)
    st.error(txt(f"A figura não foi gerada porque contém um título/rótulo inválido: {exc}", f"The figure was not generated because it contains an invalid title/label: {exc}"))
    return
  layout_meta = getattr(fig.layout, "meta", None)
  preserve_cell_geometry = isinstance(layout_meta, dict) and bool(layout_meta.get("preserve_cell_geometry"))
  chart_config = dict(PLOTLY_CONFIG)
  chart_config["toImageButtonOptions"] = dict(PLOTLY_CONFIG.get("toImageButtonOptions", {}))
  if preserve_cell_geometry:
    # A responsive Plotly canvas can silently shrink a wide heatmap to the
    # browser viewport, flattening its columns. Keep the declared figure width
    # and let the Streamlit container provide horizontal scrolling instead.
    chart_config["responsive"] = False
    chart_config["toImageButtonOptions"]["width"] = min(16000, max(1200, int(getattr(fig.layout, "width", 2400) or 2400)))
    chart_config["toImageButtonOptions"]["height"] = min(30000, max(1600, int(getattr(fig.layout, "height", 1600) or 1600)))
  article_scroll_viewport = isinstance(layout_meta, dict) and bool(layout_meta.get("article_scroll_viewport"))
  if preserve_cell_geometry:
    # Keep the complete matrix available, but display it in a compact article-
    # sized viewport. Horizontal and vertical scrolling preserve every row and
    # column without making the Streamlit page several thousand pixels tall.
    plot_width = int(max(900, getattr(fig.layout, "width", 1800) or 1800))
    plot_height = int(max(650, getattr(fig.layout, "height", 1000) or 1000))
    viewport_height = int(min(plot_height, 860))
    dom_suffix = hashlib.sha1(chart_key.encode("utf-8")).hexdigest()[:12]
    plot_id = f"plot_{dom_suffix}"
    top_id = f"topscroll_{dom_suffix}"
    body_id = f"bodyscroll_{dom_suffix}"
    fig_json = fig.to_json()
    config_json = json.dumps(chart_config, ensure_ascii=False)
    html_payload = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <script>{PLOTLY_JS_INLINE}</script>
  <style>
    html, body {{ margin:0; padding:0; overflow:hidden; background:white; }}
    .heatmap-top-scroll {{ width:100%; height:18px; overflow-x:auto; overflow-y:hidden; }}
    .heatmap-top-spacer {{ width:{plot_width}px; height:1px; }}
    .heatmap-body-scroll {{ width:100%; height:{viewport_height}px; overflow:auto; }}
    #{plot_id} {{ width:{plot_width}px; height:{plot_height}px; min-width:{plot_width}px; }}
  </style>
</head>
<body>
  <div id="{top_id}" class="heatmap-top-scroll"><div class="heatmap-top-spacer"></div></div>
  <div id="{body_id}" class="heatmap-body-scroll"><div id="{plot_id}"></div></div>
  <script>
    const figure = {fig_json};
    figure.layout = figure.layout || {{}};
    figure.layout.width = {plot_width};
    figure.layout.height = {plot_height};
    figure.layout.autosize = false;
    const config = {config_json};
    config.responsive = false;
    Plotly.newPlot("{plot_id}", figure.data, figure.layout, config).then(function() {{
      const topScroll = document.getElementById("{top_id}");
      const bodyScroll = document.getElementById("{body_id}");
      let syncing = false;
      const sync = function(source, target) {{
        if (syncing) return;
        syncing = true;
        target.scrollLeft = source.scrollLeft;
        syncing = false;
      }};
      topScroll.addEventListener("scroll", function() {{ sync(topScroll, bodyScroll); }});
      bodyScroll.addEventListener("scroll", function() {{ sync(bodyScroll, topScroll); }});
    }});
  </script>
</body>
</html>
"""
    components.html(html_payload, height=viewport_height + 28, scrolling=False)
    st.caption(txt(
      "O heatmap mantém todas as linhas, colunas e todos os rótulos do eixo Y. A altura fixa por célula e a rolagem vertical/horizontal evitam sobreposição sem ocultar nomes.",
      "The heatmap retains every row, column and every y-axis label. Fixed cell height plus vertical/horizontal scrolling prevents overlap without hiding names."
    ))
  elif article_scroll_viewport:
    plot_width = int(max(1400, getattr(fig.layout, "width", 1800) or 1800))
    plot_height = int(max(850, getattr(fig.layout, "height", 1200) or 1200))
    viewport_height = int(min(plot_height, int(layout_meta.get("article_viewport_height", 1050))))
    dom_suffix = hashlib.sha1(chart_key.encode("utf-8")).hexdigest()[:12]
    plot_id = f"plot_{dom_suffix}"
    body_id = f"bodyscroll_{dom_suffix}"
    fig_json = fig.to_json()
    config_json = json.dumps(chart_config, ensure_ascii=False)
    html_payload = f"""
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <script>{PLOTLY_JS_INLINE}</script>
  <style>
    html, body {{ margin:0; padding:0; overflow:hidden; background:white; }}
    .article-plot-scroll {{ width:100%; height:{viewport_height}px; overflow:auto; }}
    #{plot_id} {{ width:{plot_width}px; height:{plot_height}px; min-width:{plot_width}px; }}
  </style>
</head>
<body>
  <div id="{body_id}" class="article-plot-scroll"><div id="{plot_id}"></div></div>
  <script>
    const figure = {fig_json};
    figure.layout = figure.layout || {{}};
    figure.layout.width = {plot_width};
    figure.layout.height = {plot_height};
    figure.layout.autosize = false;
    const config = {config_json};
    config.responsive = false;
    Plotly.newPlot("{plot_id}", figure.data, figure.layout, config);
  </script>
</body>
</html>
"""
    components.html(html_payload, height=viewport_height + 8, scrolling=False)
  else:
    st.plotly_chart(fig, width="stretch", config=chart_config, key=chart_key)
  bar_summary = _barplot_method_summary(fig)
  if bar_summary is not None:
    st.caption(txt(bar_summary[0], bar_summary[1]))
  with st.container():
    c1, c2, c3, c4 = st.columns([0.18, 0.18, 0.18, 0.46])
    width, height = _figure_export_size(fig)
    png_bytes = plotly_image_bytes(fig, "png", width=width, height=height, scale=3)
    pdf_bytes = plotly_image_bytes(fig, "pdf", width=width, height=height, scale=1)
    svg_bytes = plotly_image_bytes(fig, "svg", width=width, height=height, scale=1)
    html_bytes = fig.to_html(include_plotlyjs=True, full_html=True).encode("utf-8")
    with c1:
      if png_bytes:
        st.download_button("Download PNG 300 dpi", data=png_bytes, file_name=f"{base}.png", mime="image/png", key=f"{chart_key}_download_png")
      else:
        st.caption(f"PNG export failed: {LAST_PLOTLY_EXPORT_ERRORS.get('png', 'unknown export error')}")
    with c2:
      if pdf_bytes:
        st.download_button("Download PDF", data=pdf_bytes, file_name=f"{base}.pdf", mime="application/pdf", key=f"{chart_key}_download_pdf")
      else:
        st.caption(f"PDF export failed: {LAST_PLOTLY_EXPORT_ERRORS.get('pdf', 'unknown export error')}")
    with c3:
      if svg_bytes:
        st.download_button("Download SVG", data=svg_bytes, file_name=f"{base}.svg", mime="image/svg+xml", key=f"{chart_key}_download_svg")
      else:
        st.caption(f"SVG export failed: {LAST_PLOTLY_EXPORT_ERRORS.get('svg', 'unknown export error')}")
    with c4:
      st.download_button("Download interactive HTML", data=html_bytes, file_name=f"{base}.html", mime="text/html", key=f"{chart_key}_download_html")
      backends = sorted({str(LAST_PLOTLY_EXPORT_ERRORS.get(f"{fmt}_backend", "")) for fmt in ("png", "pdf", "svg")} - {""})
      browser_path = discover_browser() or "not detected"
      st.caption(f"Static export canvas: {width} × {height} px; backend(s): {', '.join(backends) or 'unavailable'}; browser: {browser_path}.")
  render_figure_audit_expander(
    fig, chart_key, input_table=audit_input_table,
    processed_table=audit_processed_table, output_table=audit_output_table,
    method=audit_method, input_source=audit_input_source,
    script=audit_script, instructions=audit_instructions,
  )


def load_taxonomy_palette_map() -> dict[str, str]:
  """Load the one canonical taxonomy palette shared by app and publication figures."""
  return load_canonical_taxonomy_palette()


def publication_taxonomy_color_map(taxa: list[str]) -> dict[str, str]:
  """Return deterministic, order-independent colours from the canonical palette."""
  palette = build_canonical_taxonomy_palette(taxa, load_taxonomy_palette_map())
  return {str(taxon): palette[str(taxon)] for taxon in taxa}



def default_app_settings() -> dict:
  """Return first-run settings for a public atlas and protected admin panel."""
  return {
    "version": 7,
    "app_version": APP_VERSION,
    "program_name": PUBLIC_PROGRAM_NAME,
    "program_version": PUBLIC_PROGRAM_VERSION,
    "database_version": DATABASE_VERSION,
    "site_gate_enabled": False,
    "site_gate_user": DEFAULT_SITE_GATE_USER,
    "site_gate_password_hash": "",
    "site_gate_updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "site_gate_disabled_by_admin": True,
    "site_gate_disabled_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    "site_gate_last_action": "public_by_default",
    "admin_auth_enabled": True,
    "optional_user_login_enabled": False,
    "hidden_modules": [],
    "public_database_access_enabled": True,
    "contact_recipients": "leandro.pereira@pq.itv.org; Gisele.Nunes@itv.org",
    "contact_subject_prefix": "Amazonian Lateritic Lakes Metagenomic Atlas collaboration contact",
  }

def load_app_settings() -> dict:
  defaults = default_app_settings()
  if safe_path_exists(APP_SETTINGS_PATH):
    try:
      data = json.loads(APP_SETTINGS_PATH.read_text(encoding="utf-8"))
      if isinstance(data, dict):
        loaded_version = int(data.get("version", 0) or 0)
        settings = {**defaults, **data}
        # Migrate legacy runtime settings once. The new release is public by
        # default, starts with every module visible and protects only the admin
        # panel. Subsequent version-6 choices are preserved exactly.
        if loaded_version < 7:
          settings.update({
            "version": 7,
            "site_gate_enabled": False,
            "public_database_access_enabled": True,
            "optional_user_login_enabled": False,
            "admin_auth_enabled": True,
            "hidden_modules": [],
            "site_gate_last_action": "migrated_to_public_v7",
          })
          save_app_settings(settings, silent=True)
        return settings
    except Exception:
      pass
  save_app_settings(defaults, silent=True)
  return defaults

def save_app_settings(settings: dict, silent: bool = False) -> bool:
  try:
    APP_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    APP_SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
  except Exception as exc:
    if not silent:
      st.error(f"Could not save app settings locally: {exc}")
    return False


ADMIN_CREDENTIAL_KEYS = [
  "COPERNICUS_CLIENT_ID",
  "COPERNICUS_CLIENT_SECRET",
  "COPERNICUS_TOKEN_URL",
  "EARTHDATA_TOKEN",
  "EARTHDATA_USERNAME",
  "EARTHDATA_PASSWORD",
]


def load_admin_private_credentials() -> dict:
  """Load persisted API credentials for admin sessions only.

  The file is intentionally local and gitignored. Public users never see these
  values, and they are copied into Streamlit session_state only after admin login.
  """
  if not safe_path_exists(ADMIN_PRIVATE_CREDENTIALS_PATH):
    return {}
  try:
    data = json.loads(ADMIN_PRIVATE_CREDENTIALS_PATH.read_text(encoding="utf-8"))
    creds = data.get("credentials", data if isinstance(data, dict) else {})
    if not isinstance(creds, dict):
      return {}
    return {k: str(v) for k, v in creds.items() if k in ADMIN_CREDENTIAL_KEYS and v not in [None, ""]}
  except Exception:
    return {}


def save_admin_private_credentials(creds: dict, silent: bool = False) -> bool:
  try:
    payload = {
      "version": 1,
      "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
      "updated_by": st.session_state.get("admin_username", "admin"),
      "credentials": {k: str(v) for k, v in creds.items() if k in ADMIN_CREDENTIAL_KEYS and str(v).strip()},
    }
    ADMIN_PRIVATE_CREDENTIALS_PATH.parent.mkdir(parents=True, exist_ok=True)
    ADMIN_PRIVATE_CREDENTIALS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return True
  except Exception as exc:
    if not silent:
      st.error(f"Could not save private admin credentials: {exc}")
    return False


def apply_persisted_admin_credentials_to_session(overwrite: bool = False) -> None:
  if not is_admin_authenticated():
    return
  for key, value in load_admin_private_credentials().items():
    if overwrite or not st.session_state.get(key):
      st.session_state[key] = value


def clear_persisted_admin_credentials() -> bool:
  try:
    if safe_path_exists(ADMIN_PRIVATE_CREDENTIALS_PATH):
      ADMIN_PRIVATE_CREDENTIALS_PATH.unlink()
    for key in ADMIN_CREDENTIAL_KEYS:
      st.session_state.pop(key, None)
    return True
  except Exception as exc:
    st.error(f"Could not remove private admin credentials: {exc}")
    return False


def site_gate_enabled() -> bool:
  return bool(load_app_settings().get("site_gate_enabled", False))


def authenticate_site_gate(username: str, password: str) -> bool:
  return authenticate_user(username, password) is not None


# -----------------------------------------------------------------------------
# Final taxonomy dashboard override

# -----------------------------------------------------------------------------
# Final taxonomy dashboard override (2026-07-05)
# -----------------------------------------------------------------------------
# This definition intentionally overrides the earlier taxonomy_tab() so the
# public app always renders the requested taxonomic heatmaps, barplots, alpha
# diversity, beta ordination and RDA panels before the audit/download tables.

def _taxonomy_count_profile_final(level_name: str, view_mode: str) -> pd.DataFrame:
  if str(view_mode).lower().startswith("individual"):
    df = taxonomy_profile_table(level_name, view_mode="Individual samples").copy()
  else:
    df = taxonomy_profile_table(level_name, view_mode="Aggregated lake-season groups").copy()
  if df is None or df.empty:
    return pd.DataFrame(columns=["group", "taxon", "count", "abundance", "level", "source_sheet", "environment_feature", "lake", "season"])
  if "count" not in df.columns:
    df["count"] = pd.to_numeric(df.get("abundance", 0), errors="coerce").fillna(0)
  df["count"] = pd.to_numeric(df["count"], errors="coerce").fillna(0)
  df["abundance"] = pd.to_numeric(df.get("abundance", 0), errors="coerce").fillna(0)
  return df


def _taxonomy_matrix_from_profile_final(
  df: pd.DataFrame,
  value_col: str,
  top_n: int | None,
  min_display_pct: float | None = None,
  include_other: bool = True,
) -> pd.DataFrame:
  """Create the displayed taxonomy matrix with an effective Top-N control.

  The previous implementation first removed every taxon below 1% mean
  abundance and only then applied ``top_n``. At genus/species level this left
  only a handful of taxa, so increasing the slider did not change the chart.
  The interactive view now ranks every observed taxon and retains exactly the
  requested number (up to the number available). An optional abundance
  threshold remains available for non-interactive callers, but is not applied
  by default. All non-selected taxa are combined in one explicit category.
  """
  if df is None or df.empty:
    return pd.DataFrame()
  work = df.copy()
  work["taxon"] = work.get("taxon", "Unclassified taxa").map(clean_taxon_display_label)
  work["count"] = pd.to_numeric(work.get("count", 0), errors="coerce").fillna(0)
  work["abundance"] = pd.to_numeric(work.get("abundance", 0), errors="coerce").fillna(0)
  agg = work.groupby(["group", "taxon"], as_index=False)[["count", "abundance"]].sum()
  totals = agg.groupby("group")["abundance"].transform("sum").replace(0, np.nan)
  agg["abundance"] = (agg["abundance"] / totals * 100.0).fillna(0)
  ranked = agg.groupby("taxon", as_index=True)[value_col].mean().sort_values(ascending=False)
  if min_display_pct is not None and value_col == "abundance":
    ranked = ranked[ranked >= float(min_display_pct)]
  requested = len(ranked) if top_n is None or int(top_n) <= 0 else min(int(top_n), len(ranked))
  keep = ranked.index.tolist()[:requested]
  display = agg[agg["taxon"].isin(keep)].copy()
  if include_other and len(display) < len(agg):
    other = agg[~agg["taxon"].isin(keep)].groupby("group", as_index=False)[["count", "abundance"]].sum()
    if not other.empty:
      other["taxon"] = "Other taxa"
      display = pd.concat([display, other], ignore_index=True, sort=False)
  matrix = display.pivot_table(index="group", columns="taxon", values=value_col, aggfunc="sum", fill_value=0)
  if matrix.empty:
    return matrix
  if value_col == "abundance":
    row_totals = matrix.sum(axis=1).replace(0, np.nan)
    matrix = matrix.div(row_totals, axis=0).fillna(0) * 100.0
  preferred = keep + (["Other taxa"] if "Other taxa" in matrix.columns else [])
  matrix = matrix.reindex(columns=[c for c in preferred if c in matrix.columns])
  return matrix


def _filter_taxonomy_profile_final(df: pd.DataFrame, text_filter: str = "") -> pd.DataFrame:
  """Apply the visible taxon/sample text filter to both chart and table."""
  query = str(text_filter or "").strip()
  if df is None or df.empty or not query:
    return df
  work = df.copy()
  taxon_match = work.get("taxon", pd.Series("", index=work.index)).astype(str).str.contains(query, case=False, regex=False, na=False)
  group_match = work.get("group", pd.Series("", index=work.index)).astype(str).str.contains(query, case=False, regex=False, na=False)
  return work[taxon_match | group_match].copy()


def _taxonomy_selection_parts(level_name: str) -> tuple[str, str]:
  parts = [part.strip() for part in str(level_name or "").split("—") if part.strip()]
  rank = parts[0] if parts and parts[0] in {"Phylum", "Class", "Order", "Family", "Genus", "Species", "Domain"} else "Phylum"
  domain = next((part for part in parts if part in {"Bacteria", "Archaea"}), "Bacteria")
  return domain, rank


def _taxonomy_heatmap_final(level_name: str, view_mode: str, top_n: int | None, zscore_rows: bool = False, key_suffix: str = "active", text_filter: str = "") -> tuple[pd.DataFrame, pd.DataFrame]:
  df = _filter_taxonomy_profile_final(_taxonomy_count_profile_final(level_name, view_mode), text_filter)
  # Use relative abundance (%) for the heatmap scale in both individual and aggregated lake-season views.
  # Exact summed counts remain visible in the table below each figure.
  value_col = "abundance"
  matrix = _taxonomy_matrix_from_profile_final(df, value_col=value_col, top_n=top_n)
  if matrix.empty:
    return df, matrix
  raw_matrix = matrix.T.copy()
  plot_matrix = np.log10(raw_matrix.clip(lower=0).astype(float) + 1.0)
  domain, rank = _taxonomy_selection_parts(level_name)
  view_label = "individual samples" if str(view_mode).lower().startswith("individual") else "aggregated lake–season groups"
  # Reversed coolwarm: low values are red, intermediate values are pale and
  # high values are blue, as requested. The downloaded table remains the exact
  # untransformed relative abundance matrix.
  coolwarm_red_to_blue = [
    [0.00, "#B40426"], [0.20, "#E36A53"], [0.40, "#F7B89C"],
    [0.50, "#DDDDDD"], [0.60, "#B9D0F9"], [0.80, "#7295F4"], [1.00, "#3B4CC0"],
  ]
  fig = px.imshow(
    plot_matrix,
    aspect="auto",
    color_continuous_scale=coolwarm_red_to_blue,
    zmin=0,
    zmax=max(0.01, float(np.nanmax(plot_matrix.to_numpy(float)))),
    labels={"x": "Sample / lake-season group", "y": "Taxon", "color": "log10(relative abundance [%] + 1)"},
  )
  hover_meta_cols = [c for c in ["IMG_JGI_analysis_project_id", "IMG_JGI_taxon_oid", "ENA_study_accession", "sample_type", "sampling_position", "site"] if c in df.columns]
  group_meta = df[["group"] + hover_meta_cols].drop_duplicates("group").set_index("group") if hover_meta_cols else pd.DataFrame()
  hover_meta = []
  for group in raw_matrix.columns:
    if not group_meta.empty and group in group_meta.index:
      row = group_meta.loc[group]
      hover_meta.append("<br>".join(f"{col}: {row.get(col, '')}" for col in hover_meta_cols))
    else:
      hover_meta.append("")
  custom = np.empty((raw_matrix.shape[0], raw_matrix.shape[1], 2), dtype=object)
  custom[:, :, 0] = raw_matrix.to_numpy(float)
  custom[:, :, 1] = np.tile(np.asarray(hover_meta, dtype=object), (raw_matrix.shape[0], 1))
  fig.update_traces(
    customdata=custom,
    hovertemplate=(
      "<b>%{y}</b><br>Publication sample/group: %{x}"
      + "<br>Relative abundance: %{customdata[0]:.4f}%"
      + "<br>%{customdata[1]}"
      + "<br>log10(x + 1): %{z:.4f}"
      + "<extra></extra>"
    ),
    xgap=0,
    ygap=0,
  )
  n_rows, n_cols = plot_matrix.shape
  fig.update_layout(
    title=None,
    width=max(980, min(7600, 360 + 38 * n_cols)),
    height=max(620, min(9000, 230 + 22 * n_rows)),
    margin=dict(l=max(210, min(620, 18 * max((len(str(x)) for x in plot_matrix.index), default=10))), r=130, t=105, b=210),
    font=dict(color="#111827", size=12),
  )
  fig.update_xaxes(tickangle=-55, automargin=True, tickmode="array", tickvals=list(plot_matrix.columns), ticktext=list(plot_matrix.columns))
  fig.update_yaxes(automargin=True, ticklabelposition="outside", ticks="")
  render_plotly_downloadable(fig, key=f"taxonomy_heatmap_final_{safe_filename(level_name)}_{safe_filename(view_mode)}_{key_suffix}", basename=f"taxonomy_heatmap_{safe_filename(level_name)}_{safe_filename(view_mode)}")
  st.caption(txt(
    f"Heatmap taxonômico ({level_name}; {view_mode}). Fonte: Supplementary Table 1/resultado.cds.otu.tab + resultado.cds.tax.tab. Exibição: log10(abundância relativa [%] + 1), com paleta coolwarm invertida do vermelho ao azul para evidenciar diferenças de baixa abundância. Os valores exatos não transformados permanecem no hover e na tabela para download. A matriz original de abundância relativa alimenta os testes PERMANOVA/ordenação abaixo.",
    f"Taxonomic heatmap ({level_name}; {view_mode}). Source: Supplementary Table 1/resultado.cds.otu.tab + resultado.cds.tax.tab. Display: log10(relative abundance [%] + 1), using the reversed coolwarm red-to-blue palette to reveal low-abundance differences. Exact untransformed values remain in hover text and in the downloadable table. The original relative-abundance matrix feeds the PERMANOVA/ordination tests below."
  ))
  return df, matrix


def clean_taxon_display_label(value: object) -> str:
  raw = str(value or "").strip()
  if not raw or raw.casefold() in {"undefined", "unknown", "unclassified", "nan", "none", "na", "n/a"}:
    return "Unclassified taxa"
  return raw

def _taxonomy_barplot_final(level_name: str, view_mode: str, top_n: int | None, key_suffix: str, text_filter: str = "") -> tuple[pd.DataFrame, pd.DataFrame]:
  df = _filter_taxonomy_profile_final(_taxonomy_count_profile_final(level_name, view_mode), text_filter)
  if df.empty:
    return df, pd.DataFrame()
  base = df.copy()
  if "taxon" in base.columns:
    base["taxon"] = base["taxon"].map(clean_taxon_display_label)
  base["count"] = pd.to_numeric(base.get("count", 0), errors="coerce").fillna(0)
  base["abundance"] = pd.to_numeric(base.get("abundance", 0), errors="coerce").fillna(0)
  hover_meta_cols = [c for c in ["sample.id", "IMG_JGI_analysis_project_id", "IMG_JGI_taxon_oid", "ENA_study_accession", "sample_type", "sampling_position", "site"] if c in base.columns]
  if hover_meta_cols:
    group_metadata = base.groupby("group", as_index=False)[hover_meta_cols].agg(
      lambda values: "; ".join(dict.fromkeys(str(v) for v in values if str(v).strip()))
    )
  else:
    group_metadata = pd.DataFrame({"group": base["group"].drop_duplicates()})
  agg = base.groupby(["group", "taxon"], as_index=False)[["count", "abundance"]].sum()
  totals = agg.groupby("group")["abundance"].transform("sum").replace(0, np.nan)
  agg["abundance"] = (agg["abundance"] / totals * 100.0).fillna(0)
  ranked = agg.groupby("taxon")["abundance"].mean().sort_values(ascending=False)
  requested = len(ranked) if top_n is None or int(top_n) <= 0 else min(int(top_n), len(ranked))
  keep = ranked.index.tolist()[:requested]
  plot = agg[agg["taxon"].isin(keep)].copy()
  if len(plot) < len(agg):
    other = agg[~agg["taxon"].isin(keep)].groupby("group", as_index=False)[["count", "abundance"]].sum()
    if not other.empty:
      other["taxon"] = "Other taxa"
      plot = pd.concat([plot, other], ignore_index=True, sort=False)
  plot["abundance"] = plot["abundance"].clip(lower=0)
  renorm = plot.groupby("group")["abundance"].transform("sum").replace(0, np.nan)
  plot["abundance"] = (plot["abundance"] / renorm * 100.0).fillna(0)
  taxon_order = keep + (["Other taxa"] if "Other taxa" in plot["taxon"].astype(str).values else [])
  color_map = publication_taxonomy_color_map(taxon_order)
  if len(set(color_map.values())) != len(color_map):
    raise RuntimeError("Repeated colours detected in the canonical taxonomy barplot palette")
  domain, rank = _taxonomy_selection_parts(level_name)
  view_label = "individual samples" if str(view_mode).lower().startswith("individual") else "aggregated lake–season groups"
  plot = plot.merge(group_metadata, on="group", how="left")
  fig = px.bar(
    plot, x="group", y="abundance", color="taxon",
    color_discrete_map=color_map, category_orders={"taxon": taxon_order},
    hover_data=[c for c in hover_meta_cols if c in plot.columns],
    labels={"group": "Publication sample / lake-season group", "abundance": "Relative abundance (%)", "taxon": rank},
  )
  fig.update_layout(title=dict(text=f"{domain} — {rank} — Barplot ({view_label})", x=0.01, xanchor="left"), barmode="stack", height=720, margin=dict(l=80, r=260, t=100, b=180), legend=dict(font=dict(size=10)))
  fig.update_xaxes(tickangle=-45, automargin=True)
  fig.update_yaxes(range=[0, 100], ticksuffix="%")
  render_plotly_downloadable(fig, key=f"taxonomy_barplot_final_{safe_filename(level_name)}_{safe_filename(view_mode)}_{key_suffix}", basename=f"taxonomy_barplot_{safe_filename(level_name)}_{safe_filename(view_mode)}")
  stats_df, tested, displayed = taxonomy_barplot_statistics(level_name, selected_groups=df["group"].drop_duplicates().tolist(), view_mode=view_mode, top_n=top_n, grouping_factor="lake")
  st.caption(txt(
    f"Barplot taxonômico ({level_name}; {view_mode}). A abundância relativa foi renormalizada para 100% em cada amostra/grupo. O controle Top N retém os {len(keep)} táxons mais abundantes entre {len(ranked)} disponíveis; todos os demais são somados em 'Other taxa'. Táxons testados: {tested}/{displayed}. Testes: ANOVA/Kruskal-Wallis globais e Welch/Mann-Whitney pareados com FDR quando há replicação suficiente.",
    f"Taxonomic barplot ({level_name}; {view_mode}). Relative abundance was renormalized to 100% for each sample/group. The Top-N control retains the {len(keep)} most abundant taxa among {len(ranked)} available; all remaining taxa are summed as 'Other taxa'. Tested taxa: {tested}/{displayed}. Tests: global ANOVA/Kruskal-Wallis and pairwise Welch/Mann-Whitney with FDR when replication is sufficient."
  ))
  if not stats_df.empty:
    show_table(stats_df, f"taxonomy_barplot_stats_final_{safe_filename(level_name)}_{safe_filename(view_mode)}", height=280)
    csv_button(stats_df, f"taxonomy_barplot_stats_{safe_filename(level_name)}_{safe_filename(view_mode)}.csv", txt("Baixar estatísticas do barplot", "Download barplot statistics"))
  return df, plot


def _rarefy_count_vector(counts: pd.Series, depth: int, seed_text: str) -> np.ndarray:
  values = np.rint(pd.to_numeric(counts, errors="coerce").fillna(0).clip(lower=0).to_numpy(float)).astype(np.int64)
  total = int(values.sum())
  if total < int(depth):
    raise ValueError(f"Sample total {total} is below rarefaction depth {depth}")
  seed = (42 + int(hashlib.sha256(str(seed_text).encode("utf-8")).hexdigest()[:8], 16)) % (2**32)
  return np.random.default_rng(seed).multivariate_hypergeometric(values, int(depth))


def _alpha_from_profile_final(level_name: str, view_mode: str) -> pd.DataFrame:
  """Alpha diversity after deterministic equal-depth rarefaction.

  Individual samples are the biological units. Lake–season results are
  descriptive summaries of those individual metrics and are never treated as
  independent replicates.
  """
  if not str(view_mode).lower().startswith("individual"):
    individual = _alpha_from_profile_final(level_name, "Individual samples")
    if individual.empty:
      return individual
    summary = individual.groupby(["lake", "season", "lake_season"], as_index=False).agg(
      **{
        "Observed OTUs": ("Observed OTUs", "mean"),
        "Observed OTUs SD": ("Observed OTUs", "std"),
        "Shannon": ("Shannon", "mean"),
        "Shannon SD": ("Shannon", "std"),
        "Chao1": ("Chao1", "mean"),
        "Chao1 SD": ("Chao1", "std"),
        "n_samples": ("group", "nunique"),
        "Rarefaction depth": ("Rarefaction depth", "first"),
      }
    )
    summary = summary.rename(columns={"lake_season": "group"})
    summary["summary_type"] = "descriptive mean ± SD of individual rarefied samples"
    return summary

  df = _taxonomy_count_profile_final(level_name, "Individual samples")
  matrix = _taxonomy_matrix_from_profile_final(df, value_col="count", top_n=None)
  if matrix.empty:
    return pd.DataFrame()
  integer_totals = matrix.apply(pd.to_numeric, errors="coerce").fillna(0).clip(lower=0).sum(axis=1)
  positive_totals = integer_totals[integer_totals > 0]
  if positive_totals.empty:
    return pd.DataFrame()
  depth = int(min(32999, np.floor(positive_totals.min())))
  if depth <= 0:
    return pd.DataFrame()
  rows = []
  for group, vals in matrix.iterrows():
    rarefied = _rarefy_count_vector(vals, depth, str(group))
    positive = rarefied[rarefied > 0]
    proportions = positive / float(depth) if len(positive) else np.asarray([], dtype=float)
    f1 = int(np.sum(rarefied == 1))
    f2 = int(np.sum(rarefied == 2))
    observed = int(np.sum(rarefied > 0))
    chao1 = observed + (f1 * f1) / (2.0 * f2) if f2 > 0 else observed + f1 * (f1 - 1) / 2.0
    group_text = str(group)
    lake = re.match(r"^([A-Z]+)", group_text)
    season = "Rainy" if group_text.endswith((".R", "-R")) else "Dry" if group_text.endswith((".D", "-D")) else "Unknown"
    rows.append({
      "group": group_text,
      "lake": lake.group(1) if lake else "Unknown",
      "season": season,
      "lake_season": f"{lake.group(1) if lake else 'Unknown'}-{'R' if season == 'Rainy' else 'D' if season == 'Dry' else 'U'}",
      "Observed OTUs": observed,
      "Shannon": float(-(proportions * np.log(proportions)).sum()) if len(proportions) else 0.0,
      "Chao1": float(chao1),
      "Singletons": f1,
      "Doubletons": f2,
      "Original total count": float(integer_totals.loc[group]),
      "Rarefaction depth": depth,
      "rarefaction_method": "deterministic multivariate-hypergeometric subsampling; sample-specific seed derived from seed 42",
    })
  return pd.DataFrame(rows)


def _render_alpha_final(level_name: str) -> None:
  st.markdown("### " + txt("Diversidade alfa", "Alpha diversity"))
  individual = _alpha_from_profile_final(level_name, "Individual samples")
  summary = _alpha_from_profile_final(level_name, "Aggregated lake-season groups")
  if individual.empty:
    st.info(txt("Não há tabela suficiente para diversidade alfa.", "No sufficient alpha-diversity table is available."))
    return
  depth = int(individual["Rarefaction depth"].iloc[0])
  st.info(txt(
    f"Todas as métricas foram calculadas após rarefação determinística à mesma profundidade ({depth:,} contagens) em cada amostra individual. Grupos lake–season são apenas médias ± DP das amostras individuais e não entram como pseudorreplicatas em testes.",
    f"All metrics were calculated after deterministic equal-depth rarefaction ({depth:,} counts) in each individual sample. Lake–season groups are descriptive means ± SD of individual samples and are not treated as pseudoreplicates in tests."
  ))
  metrics = ["Observed OTUs", "Shannon", "Chao1"]
  tabs = st.tabs(metrics)
  for metric, tab in zip(metrics, tabs):
    with tab:
      view = st.radio(
        txt("Visualização das amostras individuais", "Individual-sample view"),
        ["Barplot", "Boxplot"], horizontal=True,
        key=f"alpha_view_corrected_{safe_filename(level_name)}_{safe_filename(metric)}",
      )
      if view == "Barplot":
        fig = px.bar(individual, x="group", y=metric, color="season", hover_data=individual.columns)
        fig.update_layout(title=dict(text=f"Alpha diversity — {metric} (individual samples; barplot)", x=0.01), height=560, margin=dict(l=80, r=40, t=85, b=175))
        fig.update_xaxes(tickangle=-45, automargin=True, title="Individual sample")
      else:
        factor = st.selectbox(
          txt("Fator de comparação", "Comparison factor"), ["lake", "season"],
          key=f"alpha_factor_corrected_{safe_filename(level_name)}_{safe_filename(metric)}",
        )
        fig = px.box(individual, x=factor, y=metric, color="season" if factor != "season" else "lake", points="all", hover_data=individual.columns)
        fig.update_layout(title=dict(text=f"Alpha diversity — {metric} (individual samples; boxplot by {factor})", x=0.01), height=560, margin=dict(l=80, r=40, t=85, b=120))
        stat = _numeric_group_stats(individual, metric, factor, category=f"Rarefied individual samples — {metric}")
        if not stat.empty:
          show_table(stat, f"alpha_stats_corrected_{safe_filename(level_name)}_{safe_filename(metric)}_{factor}", height=240)
          csv_button(stat, f"alpha_stats_rarefied_{safe_filename(level_name)}_{safe_filename(metric)}_{factor}.csv", txt("Baixar testes", "Download tests"))
      fig.update_yaxes(title=metric)
      render_plotly_downloadable(fig, key=f"alpha_corrected_{safe_filename(level_name)}_{safe_filename(metric)}_{view}", basename=f"alpha_rarefied_{safe_filename(level_name)}_{safe_filename(metric)}_{view}")

      if view == "Barplot" and not summary.empty:
        sd_col = f"{metric} SD"
        summary_fig = px.bar(summary, x="group", y=metric, color="lake", error_y=sd_col if sd_col in summary.columns else None, hover_data=summary.columns)
        summary_fig.update_layout(title=dict(text="Lake–season descriptive mean ± SD", x=0.01), height=500, margin=dict(l=80, r=40, t=90, b=130))
        summary_fig.update_xaxes(tickangle=-35, automargin=True, title="Lake–season group")
        summary_fig.update_yaxes(title=metric)
        render_plotly_downloadable(summary_fig, key=f"alpha_summary_{safe_filename(level_name)}_{safe_filename(metric)}", basename=f"alpha_lake_season_summary_{safe_filename(level_name)}_{safe_filename(metric)}")
      show_table(individual, f"alpha_individual_table_{safe_filename(level_name)}_{safe_filename(metric)}", height=300)
      csv_button(individual, f"alpha_diversity_rarefied_individual_{safe_filename(level_name)}.csv", txt("Baixar métricas individuais", "Download individual metrics"))
      if not summary.empty:
        csv_button(summary, f"alpha_diversity_lake_season_summary_{safe_filename(level_name)}.csv", txt("Baixar resumo lake–season", "Download lake–season summary"))


def _permanova_final(matrix: pd.DataFrame, meta: pd.DataFrame, factor: str, n_perm: int = 999) -> pd.DataFrame:
  """Validated distance-based PERMANOVA plus a permutation dispersion test."""
  if matrix.empty or meta.empty or factor not in meta.columns:
    return pd.DataFrame()
  common = [index for index in matrix.index if index in meta.index]
  if len(common) < 3:
    return pd.DataFrame()
  groups = meta.loc[common, factor].astype(str)
  if groups.dropna().nunique() < 2:
    return pd.DataFrame()
  transformed = _canonical_beta_transform(matrix.loc[common])
  distance = squareform(pdist(transformed.to_numpy(float), metric="braycurtis"))
  distance = np.nan_to_num(distance, nan=0.0, posinf=1.0, neginf=0.0)
  pm = canonical_permanova(distance, groups.to_numpy(), permutations=int(n_perm), seed=42)
  dispersion = canonical_betadisper_test(distance, groups.to_numpy(), permutations=int(n_perm), seed=42)
  return pd.DataFrame([{
    "factor": factor,
    "distance": "Bray-Curtis",
    "transformation": "square root of sample-wise relative proportions",
    "PERMANOVA_method": "Gower-centred distance-matrix sums of squares",
    "PERMANOVA_permutations": int(n_perm),
    "PERMANOVA_pseudo_F": pm.get("pseudo_F"),
    "PERMANOVA_p_value": pm.get("p_value"),
    "PERMANOVA_df_between": pm.get("df_between"),
    "PERMANOVA_df_within": pm.get("df_within"),
    "dispersion_method": "permutation test of distances to group centroids",
    "dispersion_F": dispersion.get("F"),
    "dispersion_p_value": dispersion.get("p_value"),
    "dispersion_df_between": dispersion.get("df_between"),
    "dispersion_df_within": dispersion.get("df_within"),
    "PERMANOVA_significant_p_lt_0_05": bool(pd.notna(pm.get("p_value")) and float(pm["p_value"]) < 0.05),
    "dispersion_significant_p_lt_0_05": bool(pd.notna(dispersion.get("p_value")) and float(dispersion["p_value"]) < 0.05),
  }])


def _render_beta_final(level_name: str) -> None:
  st.markdown("### " + txt("PCoA/NMDS beta diversidade", "PCoA/NMDS beta diversity"))
  st.caption(txt(
    "Este painel é exploratório quando o nível taxonômico ou a agregação diferem das Figuras 4–5. Mesmo assim, ele usa o mesmo pré-processamento NMDS do artigo: proporções por amostra, raiz quadrada, Bray–Curtis, 20 inicializações, máximo de 1.000 iterações e semente 42.",
    "This panel is exploratory when the taxonomic rank or aggregation differs from Figures 4–5. It nevertheless uses the article NMDS preprocessing: sample-wise proportions, square root, Bray–Curtis, 20 starts, a 1,000-iteration maximum and seed 42."
  ))
  view_mode = st.radio(txt("Unidades da ordenação", "Ordination units"), ["Individual samples", "Aggregated lake-season groups"], horizontal=True, key=f"beta_units_final_{safe_filename(level_name)}")
  use_all_taxa = st.checkbox(txt("Usar todos os táxons da matriz", "Use all taxa in the matrix"), value=True, key=f"beta_all_taxa_final_{safe_filename(level_name)}")
  top_n = None
  if not use_all_taxa:
    top_n = int(st.slider(txt("Top táxons usados na ordenação", "Top taxa used in ordination"), 10, 200, 60, step=10, key=f"beta_top_final_{safe_filename(level_name)}"))
  ord_kind = st.radio(txt("Método", "Method"), ["PCoA", "NMDS"], horizontal=True, key=f"beta_kind_final_{safe_filename(level_name)}")
  show_biplot = st.checkbox(txt("Mostrar biplot de táxons", "Show taxon biplot"), value=True, key=f"beta_biplot_final_{safe_filename(level_name)}")
  n_biplot = int(st.slider(txt("Número de táxons no biplot", "Number of taxa in biplot"), 2, 30, 10, step=2, key=f"beta_biplot_n_final_{safe_filename(level_name)}"))
  df = _taxonomy_count_profile_final(level_name, view_mode)
  matrix = _taxonomy_matrix_from_profile_final(df, value_col="abundance", top_n=top_n)
  if matrix.shape[0] < 3 or matrix.shape[1] < 2:
    st.info(txt("Matriz insuficiente para PCoA/NMDS.", "Matrix is insufficient for PCoA/NMDS."))
    return
  beta_meta_cols = [c for c in ["group", "lake", "season", "environment_feature", "sample.id", "sampling_position", "site", "IMG_JGI_analysis_project_id", "IMG_JGI_taxon_oid", "ENA_study_accession", "sample_type"] if c in df.columns]
  meta = df[beta_meta_cols].drop_duplicates("group").set_index("group").reindex(matrix.index)
  ord_df = pcoa_from_matrix(matrix) if ord_kind == "PCoA" else nmds_from_matrix(matrix)
  if ord_df.empty:
    st.info(txt("A ordenação não pôde ser calculada para esta seleção.", "Ordination could not be calculated for this selection."))
    return
  ord_df = ord_df.merge(meta.reset_index(), on="group", how="left")
  xcol, ycol = ("PCoA1", "PCoA2") if ord_kind == "PCoA" else ("NMDS1", "NMDS2")
  if ord_kind == "PCoA":
    x_title = f"PCoA1 ({float(ord_df['PCoA1_explained_%'].iloc[0]):.2f}% explained)"
    y_title = f"PCoA2 ({float(ord_df['PCoA2_explained_%'].iloc[0]):.2f}% explained)"
    correction = str(ord_df["distance_correction"].iloc[0])
    title = f"PCoA — Bray–Curtis ({correction} correction)"
  else:
    x_title, y_title = "NMDS1", "NMDS2"
    title = f"NMDS — Bray–Curtis (normalized Stress-1 = {float(ord_df['stress_1'].iloc[0]):.3f})"
  fig = px.scatter(ord_df, x=xcol, y=ycol, color="lake", symbol="season", hover_data=ord_df.columns)
  fig.update_traces(marker=dict(size=12, line=dict(color="black", width=0.8)))
  label_positions = repel_label_positions(ord_df, xcol, ycol, min_distance=max(float(np.ptp(ord_df[ycol])) * 0.08, 0.03), radial_offset=max(float(np.ptp(ord_df[ycol])) * 0.10, 0.04))
  for _, row in label_positions.iterrows():
    fig.add_annotation(x=float(row[xcol]), y=float(row[ycol]), ax=float(row["label_x"]), ay=float(row["label_y"]), xref="x", yref="y", axref="x", ayref="y", text=str(row["group"]), showarrow=True, arrowhead=0, arrowwidth=0.7, arrowcolor="#666666", bgcolor="rgba(255,255,255,0.86)", borderpad=2, font=dict(size=11))
  if show_biplot:
    vectors = ordination_taxon_vectors(matrix, ord_df, xcol, ycol, top_n=n_biplot)
    vectors = vectors.rename(columns={"Taxon": "Taxon"})
    fig = add_taxon_biplot_vectors(fig, vectors, xcol, ycol, ord_df)
  fig.update_layout(title=dict(text=title, x=0.01), height=760, margin=dict(l=95, r=120, t=110, b=120))
  fig.update_xaxes(title=x_title)
  fig.update_yaxes(title=y_title)
  render_plotly_downloadable(fig, key=f"beta_ord_final_{safe_filename(level_name)}_{safe_filename(view_mode)}_{ord_kind}", basename=f"beta_{ord_kind}_{safe_filename(level_name)}_{safe_filename(view_mode)}")
  stats_rows = []
  for factor in ["lake", "season", "environment_feature"]:
    stat = _permanova_final(matrix, meta, factor)
    if not stat.empty:
      stats_rows.append(stat)
  stats_df = pd.concat(stats_rows, ignore_index=True) if stats_rows else pd.DataFrame()
  if ord_kind == "PCoA":
    negative_count = int(ord_df["negative_eigenvalue_count_before_correction"].iloc[0])
    if negative_count:
      st.warning(txt(
        f"A matriz Bray–Curtis produziu {negative_count} autovalor(es) negativo(s); a correção de Lingoes foi aplicada e documentada na tabela de escores.",
        f"The Bray–Curtis matrix produced {negative_count} negative eigenvalue(s); Lingoes correction was applied and documented in the score table."
      ))
  show_table(ord_df, f"beta_scores_{safe_filename(level_name)}_{safe_filename(view_mode)}", height=320)
  csv_button(ord_df, f"beta_scores_{safe_filename(level_name)}_{safe_filename(view_mode)}.csv", txt("Baixar scores da ordenação", "Download ordination scores"))
  if not stats_df.empty:
    show_table(stats_df, f"beta_stats_{safe_filename(level_name)}_{safe_filename(view_mode)}", height=260)
    csv_button(stats_df, f"beta_permanova_dispersion_{safe_filename(level_name)}_{safe_filename(view_mode)}.csv", txt("Baixar PERMANOVA e dispersão", "Download PERMANOVA and dispersion"))


def _read_tabular_input_for_audit(path: Path) -> pd.DataFrame:
  """Read one tabular source without altering NA values."""
  suffix = path.suffix.lower()
  if suffix == ".csv":
    return pd.read_csv(path, keep_default_na=True)
  if suffix in {".tsv", ".tab"}:
    return pd.read_csv(path, sep="\t", keep_default_na=True)
  if suffix in {".xlsx", ".xls"}:
    return pd.read_excel(path, sheet_name=0)
  return pd.DataFrame()


def _static_figure_manifest_record(path: Path) -> dict:
  manifest_path = BASE_DIR / "data" / "figure_script_manifest.csv"
  if not manifest_path.exists():
    return {}
  try:
    manifest = pd.read_csv(manifest_path).fillna("")
    for column in ["PNG", "PDF", "SVG"]:
      if column in manifest.columns:
        match = manifest[manifest[column].astype(str).map(lambda value: Path(value).name == path.name)]
        if not match.empty:
          return match.iloc[0].to_dict()
  except Exception as exc:
    LOGGER.warning("Could not read figure manifest for %s: %s", path.name, exc)
  return {}


def _render_static_figure_audit(path: Path, title: str, key_prefix: str) -> None:
  record = _static_figure_manifest_record(path)
  figure_id = str(record.get("Figure", "") or "").strip() or f"Static figure {path.stem}"
  figure_title = str(record.get("Description", "") or record.get("Title", "") or title or path.stem).strip()
  with st.expander(
    txt(
      f"Dados utilizados em {figure_id} — {figure_title}",
      f"Source data for {figure_id} — {figure_title}",
    ),
    expanded=False,
  ):
    st.markdown(f"**{figure_id} — {figure_title}**")
    st.markdown(f"**{txt('Script final', 'Final script')}:** `{record.get('Script', 'See FIGURE_REPRODUCTION_COMMANDS.md')}`")
    st.markdown(f"**{txt('Comando', 'Command')}:** `{record.get('Command', '')}`")
    st.markdown(f"**{txt('Método', 'Method')}:** {record.get('Statistical_methods', '') or record.get('Purpose', '') or record.get('Description', '')}")
    st.markdown(f"**{txt('Inputs declarados', 'Declared inputs')}:** {record.get('Inputs', 'See figure script header and reproduction guide')}")
    st.caption(txt(
      "A figura estática não é recalculada nesta tela. Os arquivos abaixo são as fontes declaradas pelo manifesto figura-script; valores ausentes permanecem ausentes.",
      "The static figure is not recalculated on this screen. The files below are the sources declared by the figure-script manifest; missing values remain missing.",
    ))
    inputs = [item.strip() for item in str(record.get("Inputs", "")).split(";") if item.strip()]
    displayed = 0
    for index, input_name in enumerate(inputs):
      candidate = BASE_DIR / input_name
      if not candidate.exists() or not candidate.is_file():
        continue
      st.markdown(f"**{txt('Tabela/arquivo-fonte', 'Source table/file')} {index + 1}:** `{input_name}`")
      table = _read_tabular_input_for_audit(candidate)
      if not table.empty:
        show_table(table.head(1500), f"{key_prefix}_{path.stem}_static_source_{index}", height=380)
        csv_button(table, f"{safe_filename(path.stem)}_source_{index + 1}.csv", txt("Baixar tabela-fonte em CSV", "Download source table as CSV"), key=f"{key_prefix}_{path.stem}_static_source_csv_{index}")
      st.download_button(
        txt("Baixar arquivo-fonte original", "Download original source file"),
        data=candidate.read_bytes(), file_name=candidate.name,
        mime="application/octet-stream",
        key=f"{key_prefix}_{path.stem}_static_source_original_{index}",
      )
      displayed += 1
    if displayed == 0:
      st.info(txt(
        "Os inputs estão documentados no manifesto e no script, mas nenhum arquivo tabular direto foi resolvido automaticamente para esta figura.",
        "Inputs are documented in the manifest and script, but no direct tabular file was automatically resolved for this figure.",
      ))


def _display_static_publication_image(path: Path, title: str, caption: str = "", key_prefix: str = "static_publication_image") -> None:
  """Render one canonical static manuscript/app figure with download buttons."""
  st.markdown(f"#### `{path.name}`")
  if not path.exists():
    st.warning(txt(f"Figura indisponível: {path.name}", f"Figure unavailable: {path.name}"))
    return
  if Image is not None:
    try:
      from PIL import ImageFile as _ImageFile
      _ImageFile.LOAD_TRUNCATED_IMAGES = True
      with Image.open(path) as img:
        img.load()
    except Exception as exc:
      st.warning(txt(f"Figura não exibida porque falhou na validação: {path.name} — {exc}", f"Image not displayed because validation failed: {path.name} — {exc}"))
      return
  st.image(str(path), width="stretch")
  if caption:
    st.caption(caption)
  cols = st.columns(4)
  siblings = [path.with_suffix(ext) for ext in [".png", ".svg", ".pdf", ".tiff"]]
  labels = {
    ".png": ("PNG", "image/png"),
    ".svg": ("SVG", "image/svg+xml"),
    ".pdf": ("PDF", "application/pdf"),
    ".tiff": ("TIFF", "image/tiff"),
  }
  for col, fp in zip(cols, siblings):
    with col:
      if fp.exists():
        label, mime = labels.get(fp.suffix.lower(), (fp.suffix.upper().lstrip('.'), "application/octet-stream"))
        st.download_button(
          f"Download {label}",
          data=fp.read_bytes(),
          file_name=fp.name,
          mime=mime,
          key=f"download_{key_prefix}_{path.stem}_{fp.suffix.lower().lstrip('.')}",
          width="stretch",
        )
  _render_static_figure_audit(path, title, key_prefix)



def render_section_script_inventory(section_title: str, keywords: list[str], key_prefix: str) -> None:
  """Show scripts linked to the current biological/result section."""
  script_roots = [BASE_DIR / "scripts", BASE_DIR / "src", BASE_DIR / "docs" / "code"]
  rows = []
  key_lowers = [k.casefold() for k in keywords]
  for root in script_roots:
    if not root.exists():
      continue
    for fp in sorted(root.rglob("*")):
      if not fp.is_file() or fp.suffix.lower() not in {".py", ".r", ".sh", ".md", ".txt", ".csv", ".yml", ".yaml"}:
        continue
      rel = str(fp.relative_to(BASE_DIR))
      haystack = rel.casefold()
      try:
        preview = fp.read_text(encoding="utf-8", errors="replace")[:4000]
        haystack += " " + preview.casefold()
      except Exception:
        preview = ""
      if any(k in haystack for k in key_lowers):
        rows.append({
          "script": rel,
          "objective": section_title,
          "input_data": "See script header, figure manifest and adjacent data/outputs folders.",
          "output_data": "Figures/tables displayed in this app section and synchronized with the article package.",
          "command": f"python {rel}" if fp.suffix.lower() == ".py" else (f"Rscript {rel}" if fp.suffix.lower() == ".r" else f"bash {rel}" if fp.suffix.lower() == ".sh" else f"cat {rel}"),
          "main_dependencies": "Python/R packages listed in requirements.txt, environment.yml or script header.",
          "sha256": hashlib.sha256(fp.read_bytes()).hexdigest(),
        })
  if rows:
    with st.expander(txt("Scripts desta seção", "Scripts for this section"), expanded=False):
      manifest = pd.DataFrame(rows).drop_duplicates("script")
      show_table(manifest, f"{key_prefix}_script_manifest", height=360)
      csv_button(manifest, f"{key_prefix}_script_manifest.csv", txt("Baixar manifesto de scripts", "Download script manifest"), context=key_prefix)
      selected_script = st.selectbox(txt("Visualizar script", "View script"), manifest["script"].tolist(), key=f"{key_prefix}_script_select")
      script_path = BASE_DIR / selected_script
      if script_path.exists():
        st.code(script_path.read_text(encoding="utf-8", errors="replace")[:50000], language="python" if script_path.suffix.lower()==".py" else "text")
        st.download_button(txt("Baixar script", "Download script"), data=script_path.read_bytes(), file_name=script_path.name, mime="text/plain", key=f"download_{key_prefix}_{safe_filename(selected_script)}")

def taxonomy_tab():
  st.subheader(txt("Perfis taxonômicos da Supplementary Table 1", "Taxonomic profiles from Supplementary Table 1"))
  st.markdown(txt(
    "Esta versão mantém juntos os barplots, heatmaps, tabelas, diversidade alfa, PCoA/NMDS, downloads e scripts taxonômicos, evitando resultados dispersos ou duplicados.",
    "This version keeps taxonomic barplots, heatmaps, tables, alpha diversity, PCoA/NMDS, downloads and scripts together, avoiding dispersed or duplicated results."
  ))
  render_section_script_inventory("Taxonomy", ["taxonomy", "taxonomic", "kaiju", "resultado.cds.tax", "resultado.cds.otu"], "taxonomy_section")
  meta = taxonomy_samples_metadata()
  with st.expander(txt("Amostras, datas, coordenadas e environment_feature", "Samples, dates, coordinates and environment_feature"), expanded=True):
    cols = [c for c in ["sample.id", "Sample", "collection.date", "collection_date", "latitude", "longitude", "lat", "lon", "environment_feature", "lake", "season", "depth"] if c in meta.columns]
    show_table(meta[cols], "taxonomy_metadata_final", height=300)
    csv_button(meta, "taxonomy_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))

  st.markdown("### " + txt("Figuras taxonômicas finais usadas no artigo", "Final taxonomy figures used in the article"))
  taxonomy_figures = [
    ("Figure2_taxonomic_phylum_bacteria_horizontal_CDS.png", txt("Perfis de filos de Bacteria nas estações seca e chuvosa.", "Bacteria phylum profiles in dry and rainy seasons.")),
    ("Figure3_taxonomic_phylum_archaea_horizontal_CDS.png", txt("Perfis de filos de Archaea nas estações seca e chuvosa.", "Archaea phylum profiles in dry and rainy seasons.")),
    ("Figure4_taxonomic_bacteria_genus_profiles.png", txt("Perfis de gêneros, NMDS e biplot RDA de Bacteria.", "Bacteria genus profiles, NMDS and RDA biplot.")),
    ("Figure5_taxonomic_archaea_genus_profiles.png", txt("Perfis de gêneros, NMDS e biplot RDA de Archaea.", "Archaea genus profiles, NMDS and RDA biplot.")),
  ]
  for fig_name, fig_caption in taxonomy_figures:
    _display_static_publication_image(BASE_DIR / "outputs" / "final_publication_figures" / fig_name, fig_name, fig_caption, key_prefix="taxonomy_direct_final")

  st.markdown("### " + txt("Visualização taxonômica interativa", "Interactive taxonomic visualization"))
  selector_cols = st.columns(3)
  with selector_cols[0]:
    domain = st.selectbox("Domain", ["Bacteria", "Archaea"], index=0, key="taxonomy_final_domain")
  with selector_cols[1]:
    rank = st.selectbox(txt("Nível taxonômico", "Taxonomic level"), ["Phylum", "Class", "Order", "Family", "Genus", "Species"], index=0, key="taxonomy_final_rank")
  with selector_cols[2]:
    visualization = st.selectbox(txt("Visualização", "Visualization"), ["Barplot by individual sample", "Relative-abundance heatmap"], index=0, key="taxonomy_final_visualization")
  level = f"{rank} — {domain}"
  if level not in TAXONOMY_LEVELS:
    level = f"Phylum — {domain}"
    rank = "Phylum"
  selected_title = f"{domain} — {rank} — {visualization}"
  st.markdown(f"#### {selected_title}")
  q = st.text_input(txt("Filtro textual de táxon/amostra", "Text filter for taxon/sample"), "", key=f"taxonomy_final_filter_{safe_filename(level)}")
  taxonomy_preview = _filter_taxonomy_profile_final(
    _taxonomy_count_profile_final(level, "Individual samples"),
    q,
  )
  available_taxa = int(taxonomy_preview["taxon"].map(clean_taxon_display_label).nunique()) if not taxonomy_preview.empty and "taxon" in taxonomy_preview.columns else 1
  available_taxa = max(1, available_taxa)
  if available_taxa == 1:
    top_n = 1
    st.caption(txt("Um táxon está disponível para esta seleção.", "One taxon is available for this selection."))
  else:
    top_n = int(st.slider(
      txt("Top táxons mostrados nas figuras", "Top taxa shown in figures"),
      min_value=1,
      max_value=available_taxa,
      value=min(40, available_taxa),
      step=1,
      key=f"taxonomy_final_topn_{safe_filename(level)}",
    ))
  st.caption(txt(
    f"Exibindo {min(top_n, available_taxa)} dos {available_taxa} táxons disponíveis; os demais são somados em Other taxa.",
    f"Displaying {min(top_n, available_taxa)} of {available_taxa} available taxa; the remainder is summed into Other taxa."
  ))

  tabs = st.tabs([txt("Amostras individuais", "Individual samples"), txt("Lake–season agregado", "Aggregated lake–season"), txt("Diversidade alfa", "Alpha diversity"), txt("PCoA/NMDS", "PCoA/NMDS"), "RDA"])
  all_tables_for_audit = []
  for view_mode, tab in zip(["Individual samples", "Aggregated lake-season groups"], tabs[:2]):
    with tab:
      view_suffix = "individual samples" if view_mode.startswith("Individual") else "aggregated lake–season groups"
      st.markdown(f"#### {domain} — {rank} — {visualization.replace('by individual sample', '').strip()} ({view_suffix})")
      if visualization == "Relative-abundance heatmap":
        df, matrix = _taxonomy_heatmap_final(level, view_mode, top_n, False, "active", text_filter=q)
      else:
        df, matrix = _taxonomy_barplot_final(level, view_mode, top_n, "active", text_filter=q)
      st.markdown("#### " + txt("Tabela usada para o heatmap/barplot", "Table used for the heatmap/barplot"))
      show_table(df, f"taxonomy_exact_table_final_{safe_filename(level)}_{safe_filename(view_mode)}", height=460)
      csv_button(df, f"taxonomy_exact_{safe_filename(level)}_{safe_filename(view_mode)}.csv", txt("Baixar tabela", "Download table"))
      all_tables_for_audit.append(df.assign(view_mode=view_mode, domain=domain, taxonomic_level=rank, visualization=visualization))
  with tabs[2]:
    _render_alpha_final(level)
  with tabs[3]:
    _render_beta_final(level)
  with tabs[4]:
    taxonomic_rda_panel()

  if all_tables_for_audit:
    complete = pd.concat(all_tables_for_audit, ignore_index=True, sort=False)
    st.markdown("### " + txt("Tabela taxonômica completa para auditoria e download", "Complete taxonomic table for audit and download"))
    show_table(complete, f"taxonomy_complete_audit_{safe_filename(level)}", height=520)
    csv_button(complete, f"taxonomy_complete_audit_{safe_filename(level)}.csv", txt("Baixar tabela completa", "Download complete table"))


def site_access_gate() -> None:
  """Keep the atlas public unless the admin explicitly enables account login.

  The legacy shared review password is intentionally removed. When optional
  user login is disabled (the default), every visitor enters directly. Admin
  authentication remains available in the separate administration panel.
  """
  settings = load_app_settings()
  if not bool(settings.get("optional_user_login_enabled", False)):
    st.session_state["site_gate_authenticated"] = True
    return
  if st.session_state.get("site_gate_authenticated", False) or is_admin_authenticated():
    return

  st.markdown("""
  <div class="gate-shell">
    <div class="gate-card">
      <div class="gate-kicker">Instituto Tecnológico Vale • Environmental genomics</div>
      <h1>Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling</h1>
      <p>Account access was enabled by an administrator. There is no shared public password.</p>
    </div>
  </div>
  """, unsafe_allow_html=True)
  with st.form("optional_user_access_form", clear_on_submit=False):
    c1, c2 = st.columns([0.50, 0.50])
    with c1:
      username = st.text_input(txt("Usuário", "Username"), value="")
    with c2:
      password = st.text_input(txt("Senha", "Password"), value="", type="password")
    submitted = st.form_submit_button(txt("Entrar", "Sign in"), type="primary", width="stretch")
  if submitted:
    user = authenticate_user(username, password)
    if user is not None:
      st.session_state["site_gate_authenticated"] = True
      st.session_state["site_username"] = user.get("username", username)
      st.session_state["site_role"] = user.get("role", "viewer")
      st.success(txt("Acesso liberado.", "Access granted."))
      st.rerun()
    else:
      st.error(txt("Usuário ou senha inválidos.", "Invalid username or password."))
  st.stop()


def site_gate_admin_panel() -> None:
  """Admin controls for optional login and each public module independently."""
  settings = load_app_settings()
  with st.expander(txt("Acesso público e módulos — admin", "Public access and modules — admin"), expanded=False):
    st.success(txt(
      "O atlas abre publicamente por padrão. O login administrativo é separado e não bloqueia a leitura pública.",
      "The atlas opens publicly by default. Administrator login is separate and does not block public reading.",
    ))
    optional_login = st.checkbox(
      txt("Fechar o atlas e exigir conta cadastrada", "Close the atlas and require a registered account"),
      value=bool(settings.get("optional_user_login_enabled", False)),
      key="optional_user_login_enabled_checkbox",
      help=txt(
        "Desativado por padrão. Quando ativado, somente contas viewer/editor/admin cadastradas entram no atlas.",
        "Disabled by default. When enabled, only registered viewer/editor/admin accounts can open the atlas.",
      ),
    )

    st.markdown("##### " + txt("Ativar ou desativar cada módulo público", "Enable or disable each public module"))
    hidden = set(settings.get("hidden_modules", []) or [])
    module_state_keys = {module_id: f"public_module_enabled_{module_id}" for module_id in PUBLIC_MODULE_CATALOG}
    c_all, c_none = st.columns(2)
    with c_all:
      if st.button(txt("Ativar todos os módulos", "Enable all modules"), key="enable_all_public_modules", width="stretch"):
        for key in module_state_keys.values():
          st.session_state[key] = True
        st.rerun()
    with c_none:
      if st.button(txt("Desativar todos os módulos", "Disable all modules"), key="disable_all_public_modules", width="stretch"):
        for key in module_state_keys.values():
          st.session_state[key] = False
        st.rerun()

    enabled_by_id: dict[str, bool] = {}
    module_columns = st.columns(2)
    for idx, (module_id, labels) in enumerate(PUBLIC_MODULE_CATALOG.items()):
      with module_columns[idx % 2]:
        enabled_by_id[module_id] = st.checkbox(
          txt(*labels),
          value=module_id not in hidden,
          key=module_state_keys[module_id],
        )

    if st.button(txt("Salvar acesso e módulos", "Save access and modules"), key="save_public_access_visibility", type="primary", width="stretch"):
      settings["site_gate_enabled"] = False
      settings["public_database_access_enabled"] = True
      settings["optional_user_login_enabled"] = bool(optional_login)
      settings["hidden_modules"] = [module_id for module_id, enabled in enabled_by_id.items() if not enabled]
      settings["site_gate_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
      settings["site_gate_last_action"] = f"module_controls_saved_by_{st.session_state.get('admin_username', 'admin')}"
      if save_app_settings(settings):
        st.success(txt("Configuração salva.", "Settings saved."))
        st.rerun()

    current_hidden = set(settings.get("hidden_modules", []) or [])
    status_rows = [
      {
        "module_id": module_id,
        "module": txt(*labels),
        "publicly_enabled": module_id not in current_hidden,
      }
      for module_id, labels in PUBLIC_MODULE_CATALOG.items()
    ]
    show_table(pd.DataFrame(status_rows), "admin_public_module_visibility", height=440)
    st.info(txt(
      "Administradores sempre enxergam todos os módulos. A seleção acima controla somente a interface pública.",
      "Administrators always see every module. The selection above controls only the public interface.",
    ))


def txt(pt: str, en: str) -> str:
  return pt if IS_PT else en


SECOND_ROUND_FIGURE_NUMBERING_NOTE = "All app figures are mirrored in the numbered supplementary figure archive."

LAKE_CODE_NOTE = "AM = Amendoim; TI = Três Irmãs; TIA = Três Irmãs Adjacent; VI = Violão"
LAKE_CODE_NOTE_PT = "AM = Amendoim; TI = Três Irmãs; TIA = Três Irmãs Adjacent; VI = Violão"


DEFAULT_ARTICLE_TITLE = 'Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling'

DEFAULT_ARTICLE_AUTHORS = (
  'Leandro de Mattos Pereira, José Augusto Pires Bittencourt, Vitor Cirilo Araujo Santos, Ronnie Alves, Eder Pires, Prafulla Kumar Sahoo, José Tasso Felix Guimarães, Bruno Garcia Simões, Renato R. Moreira-Oliveira, Guilherme Oliveira and Gisele Lopes Nunes'
)
DEFAULT_ARTICLE_AFFILIATION = "Instituto Tecnológico Vale, Belém, PA, Brazil"
DEFAULT_ARTICLE_CORRESPONDENCE = "Gisele Lopes Nunes, gisele.nunes@itv.org; Leandro de Mattos Pereira, leandro.pereira@pq.itv.org"



def normalize_authors_string(authors_text: str) -> str:
  raw = (authors_text or '').strip()
  if not raw:
    return raw
  items = [part.strip() for part in raw.replace(' and ', ', ').split(',') if part.strip()]
  cleaned = []
  seen = set()
  for item in items:
    key = re.sub(r'\s+', ' ', item).strip().lower()
    key = key.replace('aa', 'a') if key == 'aa' else key
    if key and key not in seen:
      seen.add(key)
      cleaned.append(re.sub(r'\s+', ' ', item).strip())
  if not cleaned:
    return raw
  if len(cleaned) == 1:
    return cleaned[0]
  if len(cleaned) == 2:
    return f"{cleaned[0]} and {cleaned[1]}"
  return ', '.join(cleaned[:-1]) + f", and {cleaned[-1]}"
DEFAULT_ARTICLE_ABSTRACT = 'Amazonian lateritic lakes developed on ferruginous canga are seasonally variable, metal-rich systems whose sediment microbiomes remain poorly characterized. We used shotgun metagenomics to investigate microbial communities in sediments from Amendoim, Violão, Três Irmãs and Três Irmãs Adjacent lakes during dry and rainy periods. Coding-sequence taxonomic profiles revealed diverse bacterial and archaeal assemblages and a large unclassified fraction, indicating substantial underexplored diversity. Lake- and season-associated contrasts involved methanogenic, ammonia-oxidizing and anaerobic sediment lineages. Non-metric multidimensional scaling showed partial community overlap, whereas an exploratory, non-significant redundancy analysis placed genus-level variation along loss-on-ignition, aluminium, silica, sulfur and trace-metal gradients. Functional reconstruction identified genetic potential for carbon fixation, methane metabolism, nitrogen and sulfur cycling, photosynthesis, anaerobic respiration and iron metabolism. A curated Kyoto Encyclopedia of Genes and Genomes orthology framework detected 171 of 195 biogeochemical markers and 132 iron-associated markers. Descriptive cross-study contrasts distinguished Amazonian canga-lake profiles from external iron-rich records, but were not treated as inferential tests. We recovered 50 non-redundant metagenome-assembled genomes spanning medium- to high-quality bins, including lineages related to Acidobacteria, Dehalococcoidia, Nitrospirales, Burkholderiales, Bathyarchaeia, Thermoplasmatota and Methanoperedens. These results establish a genome-resolved iron metagenomic atlas for tropical lateritic-lake sediments and a basis for testing how seasonal hydrology and ferruginous geochemistry shape microbial biogeochemical functions.'

def article_field(key: str, default: str) -> str:
  session_key = f"article_{key}"
  if session_key not in st.session_state:
    st.session_state[session_key] = default
  return st.session_state[session_key]


AMAZONIAN_LAKE_COORDINATE_OVERRIDES = {
  "AM.P1": {"lake": "Amendoim", "lat": -(6 + 23/60 + 54.1/3600), "lon": -(50 + 22/60 + 17.6/3600)},
  "AM.P2": {"lake": "Amendoim", "lat": -(6 + 24/60 + 3.0/3600),  "lon": -(50 + 22/60 + 18.8/3600)},
  "VI.P1": {"lake": "Violão",   "lat": -(6 + 24/60 + 2.5/3600),  "lon": -(50 + 21/60 + 6.7/3600)},
  "VI.P2": {"lake": "Violão",   "lat": -(6 + 23/60 + 52.3/3600), "lon": -(50 + 21/60 + 14.0/3600)},
  "TIA.P1": {"lake": "Três Irmãs - Adjacent", "lat": -(6 + 20/60 + 51.7/3600), "lon": -(50 + 26/60 + 52.3/3600)},
  "TIA.P2": {"lake": "Três Irmãs - Adjacent", "lat": -(6 + 20/60 + 47.7/3600), "lon": -(50 + 26/60 + 48.2/3600)},
  "TI.P1": {"lake": "Três Irmãs Lake 2", "lat": -(6 + 21/60 + 9.6/3600),  "lon": -(50 + 27/60 + 1.9/3600)},
  "TI.P2": {"lake": "Três Irmãs Lake 3", "lat": -(6 + 21/60 + 12.7/3600), "lon": -(50 + 26/60 + 39.5/3600)},
  "TI.P3": {"lake": "Três Irmãs Lake 4", "lat": -(6 + 21/60 + 19.4/3600), "lon": -(50 + 26/60 + 44.2/3600)},
  "TI.P4": {"lake": "Três Irmãs Lake 5", "lat": -(6 + 21/60 + 23.5/3600), "lon": -(50 + 26/60 + 53.6/3600)},
}


def apply_amazonian_lake_coordinate_overrides(meta: pd.DataFrame) -> pd.DataFrame:
  """Apply verified article coordinates for Amazonian lake samples when their IDs are present.

  Robustness note: Streamlit deployments that read CSV/XLSX metadata with the
  pandas Arrow backend can keep latitude/longitude columns as Arrow/string
  arrays. Directly assigning Python floats into those arrays raises
  ``TypeError``. This function now creates numeric coordinate columns before
  any override assignment and mirrors the values back to all supported latitude
  and longitude aliases.
  """
  if meta is None or meta.empty:
    return meta
  out = meta.copy()

  lat_aliases = [c for c in ["lat", "latitude", "Latitude"] if c in out.columns]
  lon_aliases = [c for c in ["lon", "longitude", "Longitude"] if c in out.columns]
  if "lat" not in out.columns:
    out["lat"] = np.nan
    lat_aliases.insert(0, "lat")
  if "lon" not in out.columns:
    out["lon"] = np.nan
    lon_aliases.insert(0, "lon")

  # Convert every coordinate alias to a normal numeric dtype before assigning
  # overrides. This avoids pandas Arrow/string assignment failures and also
  # cleans comma decimal separators and empty strings.
  for col in sorted(set(lat_aliases + lon_aliases)):
    cleaned = out[col].astype("string").str.replace(",", ".", regex=False)
    out[col] = pd.to_numeric(cleaned, errors="coerce").astype("float64")

  sample_cols = [c for c in [
    "sample.id", "sample_id", "Sample", "sample_label", "matrix_column", "sample_display_id",
    "sample_description", "linked_st8_all_ko_column", "linked_res_ko_biomarkers_cns_column"
  ] if c in out.columns]
  if not sample_cols:
    return out

  def _row_ids(row) -> list[str]:
    ids = []
    for col in sample_cols:
      value = row.get(col, "")
      if pd.isna(value):
        continue
      text = str(value)
      for key in AMAZONIAN_LAKE_COORDINATE_OVERRIDES:
        if key in text:
          ids.append(key)
    return ids

  for idx, row in out.iterrows():
    ids = _row_ids(row)
    if not ids:
      continue
    sid = ids[0]
    override = AMAZONIAN_LAKE_COORDINATE_OVERRIDES[sid]
    lat_value = float(override["lat"])
    lon_value = float(override["lon"])
    for col in lat_aliases:
      out.loc[idx, col] = lat_value
    for col in lon_aliases:
      out.loc[idx, col] = lon_value
    if "lake" in out.columns and is_missing_value(out.loc[idx, "lake"]):
      out.loc[idx, "lake"] = override["lake"]
    if "geographic_location" in out.columns and is_missing_value(out.loc[idx, "geographic_location"]):
      out.loc[idx, "geographic_location"] = f"Carajás, Pará, Brazil — {override['lake']}"
    if "coordinate_status" in out.columns:
      out.loc[idx, "coordinate_status"] = "verified_author_coordinates"
  return out

def ko_entry_from_label(value: object) -> str:
  m = re.search(r"(K\d{5})", str(value))
  return m.group(1) if m else ""


def is_missing_value(value) -> bool:
  """Treat pandas NA, empty strings and textual NaN/None as missing for labels."""
  try:
    if pd.isna(value):
      return True
  except Exception:
    pass
  text = str(value).strip()
  return text == "" or text.lower() in {"nan", "none", "nat", "<na>", "null"}


def first_present(row, candidates, default: str = "") -> str:
  """Return the first non-missing value from a Series/dict using candidate column names."""
  for col in candidates:
    try:
      value = row.get(col, None)
    except Exception:
      value = None
    if not is_missing_value(value):
      return str(value).strip()
  return default


def sample_display_id(row, fallback_prefix: str = "Sample") -> str:
  """Stable label for article samples and Figure 11 environments without displaying NaN."""
  label = first_present(row, ["matrix_column", "sample.id", "sample_id", "Sample", "Genome Name / Sample Name", "sample_description"])
  if label:
    return label
  try:
    idx = int(getattr(row, "name", 0)) + 1
  except Exception:
    idx = 1
  return f"{fallback_prefix} {idx}"


def display_text(row, candidates, default: str = "") -> str:
  return first_present(row, candidates, default=default)


def significance_legend():
  st.markdown(
    txt(
      """
**Legenda de significância:** `ns` = não significativo (*p* ≥ 0,05); `*` = *p* < 0,05; `**` = *p* < 0,01; `***` = *p* < 0,001; `****` = *p* < 0,0001.  
Quando a planilha traz *adjusted p-value*, ele é mostrado em coluna própria; o app não cria significância artificial quando a tabela original não traz esse campo.
""",
      """
**Significance legend:** `ns` = not significant (*p* ≥ 0.05); `*` = *p* < 0.05; `**` = *p* < 0.01; `***` = *p* < 0.001; `****` = *p* < 0.0001.  
When the spreadsheet includes an adjusted p-value, it is displayed in its own column; the app does not invent significance when the original table does not provide it.
""",
    )
  )


def p_to_stars(pvalue):
  try:
    p = float(pvalue)
  except Exception:
    return ""
  if pd.isna(p):
    return ""
  if p < 0.0001:
    return "****"
  if p < 0.001:
    return "***"
  if p < 0.01:
    return "**"
  if p < 0.05:
    return "*"
  return "ns"


def kml_from_metadata(meta: pd.DataFrame, name: str = "Amazonian lateritic lakes samples") -> str:
  rows = []
  rows.append('<?xml version="1.0" encoding="UTF-8"?>')
  rows.append('<kml xmlns="http://www.opengis.net/kml/2.2"><Document>')
  rows.append(f'<name>{name}</name>')
  for _, r in meta.dropna(subset=["lat", "lon"]).iterrows():
    sample = sample_display_id(r)
    env = display_text(r, ["environment_feature", "habitat", "specific_ecosystem"], "NA")
    loc = display_text(r, ["geographic_location", "sample_description", "study_name"], "NA")
    date_val = r.get("collection_date_raw", r.get("collection_date", r.get("collection.date", "")))
    date_str = "" if pd.isna(date_val) else str(pd.to_datetime(date_val).date()) if not isinstance(date_val, str) and pd.notna(pd.to_datetime(date_val, errors="coerce")) else str(date_val)
    desc = f"Sample: {sample}; Environment: {env}; Location: {loc}; Collection date: {date_str}"
    rows.append("<Placemark>")
    rows.append(f"<name>{sample} | {env}</name>")
    rows.append(f"<description>{desc}</description>")
    rows.append(f"<Point><coordinates>{float(r['lon'])},{float(r['lat'])},0</coordinates></Point>")
    rows.append("</Placemark>")
  rows.append("</Document></kml>")
  return "\n".join(rows)



def add_visual_offsets_for_map(map_df: pd.DataFrame, cluster_round: int = 3) -> pd.DataFrame:
  """Add display-only offsets for overlapping or nearly overlapping coordinates.

  The original latitude/longitude columns are preserved for tables, downloads and
  hover text. Only __visual_lat__/__visual_lon__ are used by map markers, so
  points from the same lake/sample coordinate can be inspected instead of being
  hidden under one another.
  """
  out = map_df.copy()
  if out.empty or not {"lat", "lon"}.issubset(out.columns):
    return out
  out["__original_lat__"] = pd.to_numeric(out["lat"], errors="coerce")
  out["__original_lon__"] = pd.to_numeric(out["lon"], errors="coerce")
  out["__visual_lat__"] = out["__original_lat__"]
  out["__visual_lon__"] = out["__original_lon__"]
  valid = out.dropna(subset=["__original_lat__", "__original_lon__"])
  if valid.empty:
    return out
  lat_span = float(valid["__original_lat__"].max() - valid["__original_lat__"].min()) if len(valid) > 1 else 0.0
  lon_span = float(valid["__original_lon__"].max() - valid["__original_lon__"].min()) if len(valid) > 1 else 0.0
  max_span = max(lat_span, lon_span)
  if max_span < 0.05:
    radius = 0.0035
  elif max_span < 0.5:
    radius = 0.006
  elif max_span < 5:
    radius = 0.018
  else:
    radius = 0.05
  cluster_key = valid.apply(lambda r: f"{round(float(r['__original_lat__']), cluster_round)}|{round(float(r['__original_lon__']), cluster_round)}", axis=1)
  groups = {}
  for idx, group_key in zip(valid.index, cluster_key):
    groups.setdefault(group_key, []).append(idx)
  for _, indices in groups.items():
    n = len(indices)
    if n <= 1:
      continue
    for i, idx in enumerate(indices):
      angle = 2.0 * np.pi * i / n
      # Keep visual offsets small and deterministic. Longitude adjustment accounts roughly for latitude.
      lat0 = float(out.at[idx, "__original_lat__"])
      cos_lat = max(np.cos(np.deg2rad(lat0)), 0.25)
      out.at[idx, "__visual_lat__"] = lat0 + radius * np.sin(angle)
      out.at[idx, "__visual_lon__"] = float(out.at[idx, "__original_lon__"]) + (radius * np.cos(angle) / cos_lat)
  out["__map_offset_note__"] = np.where(
    (out["__visual_lat__"].round(8) != out["__original_lat__"].round(8)) | (out["__visual_lon__"].round(8) != out["__original_lon__"].round(8)),
    "Marker slightly offset on the map to separate overlapping points; original coordinates are preserved below.",
    "Marker plotted at original coordinates.",
  )
  return out


def show_leaflet_satellite_map(meta: pd.DataFrame, key: str, title: str | None = None, height: int = 680):
  """Interactive Google-tile map with points from supplementary-table coordinates.

  The app does not invent or correct coordinates. Rows without lat/lon are not
  plotted and remain visible in the metadata tables.
  """
  if not {"lat", "lon"}.issubset(meta.columns):
    st.warning(txt("As colunas lat/lon não estão disponíveis para o mapa.", "lat/lon columns are not available for the map."))
    return
  map_df = apply_amazonian_lake_coordinate_overrides(meta.copy())
  map_df["lat"] = pd.to_numeric(map_df["lat"], errors="coerce")
  map_df["lon"] = pd.to_numeric(map_df["lon"], errors="coerce")
  map_df = map_df.dropna(subset=["lat", "lon"]).copy()
  map_df = add_visual_offsets_for_map(map_df)
  if map_df.empty:
    st.warning(txt("Nenhuma coordenada válida para exibir no mapa.", "No valid coordinates to display on the map."))
    return

  color_field = "dataset_group" if "dataset_group" in map_df.columns else (
    "environment_feature" if "environment_feature" in map_df.columns else (
      "habitat" if "habitat" in map_df.columns else "lake"
    )
  )
  palette = ["#00796B", "#F9A825", "#1565C0", "#6A1B9A", "#C62828", "#2E7D32", "#00838F", "#8D6E63", "#AD1457", "#3949AB"]
  categories = sorted(map_df[color_field].fillna("Samples").astype(str).unique()) if color_field in map_df.columns else ["Samples"]
  colors = {cat: palette[i % len(palette)] for i, cat in enumerate(categories)}

  points = []
  for _, r in map_df.iterrows():
    sample = sample_display_id(r, fallback_prefix="Point")
    env = display_text(r, ["environment_feature", "habitat", "specific_ecosystem", "environment_biome"], "NA")
    loc = display_text(r, ["geographic_location", "sample_description", "study_name", "isolation_country"], "NA")
    raw_date = r.get("collection_date_raw", r.get("collection.date", r.get("collection_date", "")))
    if pd.isna(raw_date):
      raw_date = ""
    category = str(r.get(color_field, "Samples")) if color_field in r.index else "Samples"
    ref_url = display_text(r, ["environment_reference_url", "img_jgi_url", "google_maps_url"], "")
    points.append({
      "lat": float(r["__visual_lat__"]),
      "lon": float(r["__visual_lon__"]),
      "original_lat": float(r["__original_lat__"]),
      "original_lon": float(r["__original_lon__"]),
      "offset_note": html_lib.escape(str(r.get("__map_offset_note__", ""))),
      "sample": html_lib.escape(str(sample)),
      "environment": html_lib.escape(str(env)),
      "location": html_lib.escape(str(loc)),
      "date": html_lib.escape(str(raw_date)),
      "category": html_lib.escape(str(category)),
      "reference_url": html_lib.escape(str(ref_url)),
      "color": colors.get(category, "#00796B"),
    })

  center_lat = float(map_df["lat"].mean())
  center_lon = float(map_df["lon"].mean())
  div_id = re.sub(r"[^A-Za-z0-9_]", "_", key)
  legend_html = "".join(
    f"<span class='legend-item'><i style='background:{colors[cat]}'></i>{html_lib.escape(str(cat))}</span>"
    for cat in categories
  )
  title_text = html_lib.escape(title or txt("Mapa das amostras e ambientes", "Samples and environments map"))
  map_html = f"""
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    #{div_id} {{ height:{height}px; width:100%; border-radius:24px; overflow:hidden; border:1px solid rgba(0,138,131,.28); box-shadow:0 18px 44px rgba(15,23,42,.16); }}
    .map-title-{div_id} {{font-family:Inter,Arial,sans-serif; font-weight:850; color:#123534; margin:0 0 10px 0; font-size:19px;}}
    .legend-{div_id} {{font-family:Inter,Arial,sans-serif; background:rgba(255,255,255,.93); padding:10px 12px; border-radius:14px; border:1px solid rgba(15,23,42,.13); box-shadow:0 8px 18px rgba(0,0,0,.12); max-width:520px;}}
    .legend-{div_id} .legend-item {{display:inline-flex; align-items:center; gap:6px; margin:3px 10px 3px 0; font-size:12px; color:#243b3a;}}
    .legend-{div_id} i {{display:inline-block; width:12px; height:12px; border-radius:50%; border:1px solid rgba(0,0,0,.24);}}
    .leaflet-popup-content {{font-family:Inter,Arial,sans-serif; font-size:13px; line-height:1.35;}}
  </style>
  <div class="map-title-{div_id}">{title_text}</div>
  <div id="{div_id}"></div>
  <script>
    const points_{div_id} = {json.dumps(points, ensure_ascii=False)};
    const map_{div_id} = L.map('{div_id}', {{scrollWheelZoom: true, worldCopyJump: true, preferCanvas: true, zoomControl: true}}).setView([{center_lat}, {center_lon}], 4);

    const googleSat_{div_id} = L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={{x}}&y={{y}}&z={{z}}', {{
      attribution: 'Imagery © Google', maxZoom: 20
    }});
    const googleHybrid_{div_id} = L.tileLayer('https://mt1.google.com/vt/lyrs=y&x={{x}}&y={{y}}&z={{z}}', {{
      attribution: 'Imagery © Google', maxZoom: 20
    }});
    const osm_{div_id} = L.tileLayer('https://tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '© OpenStreetMap contributors', maxZoom: 19, detectRetina: true
    }});

    googleHybrid_{div_id}.addTo(map_{div_id});
    L.control.layers({{
      'Google hybrid': googleHybrid_{div_id},
      'Google satellite': googleSat_{div_id},
      'OpenStreetMap fallback': osm_{div_id}
    }}, null, {{position:'topright'}}).addTo(map_{div_id});

    const bounds_{div_id} = [];
    points_{div_id}.forEach(p => {{
      const marker = L.circleMarker([p.lat, p.lon], {{
        radius: 10, fillColor: p.color, color: '#ffffff', weight: 2,
        fillOpacity: 0.96
      }}).addTo(map_{div_id});
      marker.bindPopup(`<b>${{p.sample}}</b><br><b>Environment:</b> ${{p.environment}}<br><b>Location:</b> ${{p.location}}<br><b>Date:</b> ${{p.date || 'NA'}}<br><b>Group:</b> ${{p.category || 'NA'}}<br><b>Original Lat/Lon:</b> ${{p.original_lat.toFixed(6)}}, ${{p.original_lon.toFixed(6)}}<br><b>Map display:</b> ${{p.offset_note}}`);
      marker.bindTooltip(p.sample, {{permanent:false, direction:'top'}});
      bounds_{div_id}.push([p.lat, p.lon]);
    }});
    if (bounds_{div_id}.length > 1) {{
      map_{div_id}.fitBounds(bounds_{div_id}, {{padding:[54,54], maxZoom: 14}});
    }}
    const legend_{div_id} = L.control({{position:'bottomleft'}});
    legend_{div_id}.onAdd = function() {{
      const div = L.DomUtil.create('div', 'legend-{div_id}');
      div.innerHTML = `{legend_html}`;
      return div;
    }};
    legend_{div_id}.addTo(map_{div_id});
  </script>
  """
  components.html(map_html, height=height + 70, scrolling=False)


def show_reliable_plotly_map(meta: pd.DataFrame, key: str, title: str | None = None, height: int = 660):
  """Always-visible coordinate check map rendered without external map tiles.

  This figure intentionally uses only latitude/longitude values from the
  supplementary spreadsheets. It does not depend on Google/OSM/Esri tiles, so it
  remains visible when external tile servers are slow or blocked. A separate
  Google/satellite map is still shown below as an optional high-resolution view.
  """
  if not {"lat", "lon"}.issubset(meta.columns):
    st.warning(txt("As colunas lat/lon não estão disponíveis nos metadados.", "lat/lon columns are not available in the metadata."))
    return
  map_df = apply_amazonian_lake_coordinate_overrides(meta.copy())
  map_df["lat"] = pd.to_numeric(map_df["lat"], errors="coerce")
  map_df["lon"] = pd.to_numeric(map_df["lon"], errors="coerce")
  missing_df = map_df[map_df[["lat", "lon"]].isna().any(axis=1)].copy()
  map_df = map_df.dropna(subset=["lat", "lon"]).copy()
  map_df = add_visual_offsets_for_map(map_df)
  if map_df.empty:
    st.warning(txt("Nenhuma linha possui coordenadas completas para o mapa.", "No row has complete coordinates for the map."))
    if not missing_df.empty:
      cols = [c for c in ["matrix_order", "matrix_column", "sample_id", "sample_description", "geographic_location", "habitat", "isolation", "collection_date_raw", "coordinate_status"] if c in missing_df.columns]
      show_table(missing_df[cols], f"{key}_missing_coordinates", height=260)
    return

  map_df["__label__"] = [sample_display_id(r, fallback_prefix="Point") for _, r in map_df.iterrows()]
  color_col = next((c for c in ["dataset_group", "ST8_group", "environment_feature", "lake", "habitat"] if c in map_df.columns), None)
  if color_col is None:
    map_df["__group__"] = "Samples"
    color_col = "__group__"

  for c in ["geographic_location", "sample_description", "habitat", "isolation", "isolation_country", "environment_feature", "collection_date_raw", "collection_date_precision", "coordinate_status"]:
    if c not in map_df.columns:
      map_df[c] = ""
  map_df["__hover__"] = [
    f"<b>{r['__label__']}</b>"
    f"<br>Group: {r.get(color_col, '')}"
    f"<br>Location: {r.get('geographic_location') or r.get('sample_description') or ''}"
    f"<br>Habitat/environment: {r.get('habitat') or r.get('environment_feature') or ''}"
    f"<br>Isolation: {r.get('isolation') or ''}"
    f"<br>Country: {r.get('isolation_country') or ''}"
    f"<br>Date: {r.get('collection_date_raw') or r.get('collection_date') or ''}"
    f"<br>Original Lat/Lon: {float(r['__original_lat__']):.6f}, {float(r['__original_lon__']):.6f}"
    f"<br>Map note: {r.get('__map_offset_note__', '')}"
    for _, r in map_df.iterrows()
  ]

  fig = px.scatter(
    map_df,
    x="__visual_lon__",
    y="__visual_lat__",
    color=color_col,
    text="__label__",
    hover_name="__label__",
    hover_data={"__visual_lon__": False, "__visual_lat__": False, color_col: True},
    title=title or txt("Mapa de checagem de coordenadas — amostras e ambientes", "Coordinate-check map — samples and environments"),
    labels={"__visual_lon__": "Longitude", "__visual_lat__": "Latitude", color_col: "Group"},
  )
  fig.update_traces(
    marker=dict(size=15, line=dict(width=1.8, color="white"), opacity=0.94),
    textposition="top center",
    customdata=map_df[["__hover__"]].values,
    hovertemplate="%{customdata[0]}<extra></extra>",
  )
  lon_span = float(map_df["__visual_lon__"].max() - map_df["__visual_lon__"].min()) if len(map_df) > 1 else 0.1
  lat_span = float(map_df["__visual_lat__"].max() - map_df["__visual_lat__"].min()) if len(map_df) > 1 else 0.1
  pad_lon = max(0.04, lon_span * 0.18)
  pad_lat = max(0.04, lat_span * 0.18)
  fig.update_xaxes(range=[float(map_df["__visual_lon__"].min()) - pad_lon, float(map_df["__visual_lon__"].max()) + pad_lon], zeroline=False, gridcolor="rgba(38,50,56,.15)")
  fig.update_yaxes(range=[float(map_df["__visual_lat__"].min()) - pad_lat, float(map_df["__visual_lat__"].max()) + pad_lat], scaleanchor="x", scaleratio=1, zeroline=False, gridcolor="rgba(38,50,56,.15)")
  fig.update_layout(
    height=max(height, 780),
    margin=dict(l=10, r=10, t=92, b=128),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(245,250,250,.70)",
    legend=dict(orientation="h", yanchor="top", y=-0.16, xanchor="left", x=0, title_text=txt("Grupos", "Groups")),
    title=dict(font=dict(size=21), y=0.98),
    font=dict(size=13),
  )
  render_plotly_downloadable(fig, key=f"{key}_plotly_geo_map", basename=f"{key}_coordinate_check_map")
  st.caption(txt(
    "Legenda: este mapa rápido usa apenas latitude/longitude das planilhas suplementares. Pontos com coordenadas iguais podem ser deslocados levemente somente para visualização; as coordenadas originais aparecem no hover e na tabela.",
    "Legend: this fast map uses only latitude/longitude from the supplementary spreadsheets. Points with identical coordinates may be slightly offset only for visualization; original coordinates are shown in hover text and in the table."
  ))

  if not missing_df.empty:
    with st.expander(txt("Linhas sem coordenadas na planilha", "Rows without coordinates in the spreadsheet"), expanded=False):
      cols = [c for c in ["matrix_order", "matrix_column", "sample_id", "sample_description", "geographic_location", "habitat", "isolation", "collection_date_raw", "coordinate_status"] if c in missing_df.columns]
      st.caption(txt(
        "Estas linhas permanecem fora do mapa e dos downloads ambientais porque latitude/longitude não estão disponíveis na tabela suplementar.",
        "These rows remain outside the map and environmental downloads because latitude/longitude are not available in the supplementary table."
      ))
      show_table(missing_df[cols], f"{key}_missing_coordinates", height=260)


def show_high_quality_sample_map(meta: pd.DataFrame, key: str = "article_samples_map"):
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
  st.markdown("#### " + title)
  st.caption(txt(
    "O mapa rápido abaixo aparece primeiro e usa somente as coordenadas das planilhas suplementares. O mapa Google/satélite fica em uma seção opcional para evitar atraso quando os tiles externos demoram a carregar.",
    "The fast map below is rendered first and uses only coordinates from the supplementary spreadsheets. The Google/satellite map is optional to avoid delays when external tiles are slow to load."
  ))
  show_reliable_plotly_map(map_df, key=key, title=txt("Coordinate-check map — samples, environments and lake points", "Coordinate-check map — samples, environments and lake points"), height=820)

  with st.expander(txt("High-resolution Google / satellite map with clickable separated points", "High-resolution Google / satellite map with clickable separated points"), expanded=True):
    st.caption(txt("Quando pontos têm coordenadas idênticas ou quase idênticas, o marcador é ligeiramente deslocado apenas na visualização para evitar sobreposição; a coordenada original aparece no popup e na tabela.", "When points have identical or nearly identical coordinates, the marker is slightly offset only in the visualization to avoid overlap; the original coordinate appears in the popup and in the table."))
    show_leaflet_satellite_map(valid, key=f"{key}_google", title=title, height=820)

  coordinate_cols = [c for c in [
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


def _clean_link_text(value: object) -> str:
  text = str(value).strip()
  if text.lower() in {"", "nan", "none", "na", "n/a", "null", "-"}:
    return ""
  return text


def _extract_ko_entry(value: object) -> str:
  m = re.search(r"(K\d{5})", str(value))
  return m.group(1) if m else ""


def _extract_kegg_module(value: object) -> str:
  m = re.search(r"(M\d{5})", str(value))
  return m.group(1) if m else ""


def _kegg_pathway_or_module_url(value: object) -> str:
  """Return an official KEGG URL for a pathway/module text only when usable information exists."""
  text = _clean_link_text(value)
  if not text:
    return ""
  module = _extract_kegg_module(text)
  if module:
    return f"https://www.kegg.jp/entry/{module}"
  pathway_match = re.search(r"(map\d{5}|ko\d{5})", text, flags=re.I)
  if pathway_match:
    return f"https://www.kegg.jp/entry/{pathway_match.group(1)}"
  # For named roles/pathways without an explicit KEGG module/pathway identifier, use KEGG's
  # official pathway text-search endpoint. This is still data-driven: it is created only when
  # the table contains a non-empty pathway/metabolic-role value.
  return "https://www.kegg.jp/kegg-bin/search_pathway_text?map=map00000&keyword=" + quote_plus(text)


def _first_existing_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
  lower_map = {str(c).lower().strip(): c for c in df.columns}
  for cand in candidates:
    if cand.lower().strip() in lower_map:
      return lower_map[cand.lower().strip()]
  # fuzzy fallback for common exported columns
  for col in df.columns:
    low = str(col).lower()
    if any(cand.lower() in low for cand in candidates):
      return col
  return None


def augment_ko_pathway_links(df: pd.DataFrame) -> pd.DataFrame:
  """Add KO and pathway/function hyperlinks to every displayed/downloaded KO table.

  The app does not invent annotations. KO links are generated only when a KEGG KO
  identifier (Kxxxxx) is present in the row. Pathway/module links are generated only
  when a non-empty pathway/module/metabolic-role field exists; explicit KEGG module
  IDs (Mxxxxx) link directly to the module entry, and descriptive pathway names link
  to the official KEGG pathway text search.
  """
  if df is None or df.empty:
    return df
  out = df.copy()
  ko_col = _first_existing_column(out, ["KO", "Function Id", "Function ID", "KO_entry", "OTU", "K number"])
  if ko_col is not None and "KO hyperlink" not in out.columns:
    links = out[ko_col].apply(lambda v: f"https://www.kegg.jp/entry/{_extract_ko_entry(v)}" if _extract_ko_entry(v) else "")
    if links.astype(str).str.startswith("http").any():
      insert_at = min(list(out.columns).index(ko_col) + 1, len(out.columns))
      out.insert(insert_at, "KO hyperlink", links)
  desc_col = _first_existing_column(out, ["KO description", "Function Name", "Function", "description", "Biologic Role"])
  if desc_col is not None and "KO function / role" not in out.columns:
    values = out[desc_col].apply(_clean_link_text)
    if values.astype(bool).any():
      # Keep the functional explanation next to the link so the reader can understand the role without leaving the app.
      out.insert(min((list(out.columns).index(desc_col) + 1), len(out.columns)), "KO function / role", values)
  pathway_col = _first_existing_column(out, [
    "KEGG MODULE", "KEGG Module", "Metabolism", "Marker for:", "Marker for",
    "General metabolism", "Biologic Role", "Pathway", "pathway", "category",
    "metabolic_pathway", "metabolism_category"
  ])
  if pathway_col is not None and "Pathway / metabolic role hyperlink" not in out.columns:
    pathway_values = out[pathway_col].apply(_clean_link_text)
    pathway_links = pathway_values.apply(_kegg_pathway_or_module_url)
    if pathway_links.astype(str).str.startswith("http").any():
      idx = min(list(out.columns).index(pathway_col) + 1, len(out.columns))
      out.insert(idx, "Pathway / metabolic role hyperlink", pathway_links)

  ec_col = _first_existing_column(out, ["EC-number", "EC number", "EC", "Enzyme / EC", "Function Id"])
  if ec_col is not None and "KEGG enzyme hyperlink" not in out.columns:
    def ec_url(value):
      match = re.search(r"(?:EC:)?(\d+\.\d+\.\d+\.(?:\d+|-))", str(value or ""), flags=re.I)
      return f"https://www.kegg.jp/entry/ec:{match.group(1)}" if match else ""
    links = out[ec_col].map(ec_url)
    if links.astype(str).str.startswith("http").any():
      out.insert(min(list(out.columns).index(ec_col) + 1, len(out.columns)), "KEGG enzyme hyperlink", links)

  pfam_col = _first_existing_column(out, ["PFAM", "Pfam", "PFAM ID", "Function Id"])
  if pfam_col is not None and "PFAM hyperlink" not in out.columns:
    def pfam_url(value):
      match = re.search(r"PF(?:AM)?(\d{5})", str(value or ""), flags=re.I)
      return f"https://www.ebi.ac.uk/interpro/entry/pfam/PF{match.group(1)}/" if match else ""
    links = out[pfam_col].map(pfam_url)
    if links.astype(str).str.startswith("http").any():
      out.insert(min(list(out.columns).index(pfam_col) + 1, len(out.columns)), "PFAM hyperlink", links)
  return out


def csv_button(df: pd.DataFrame, filename: str, label: str, key: str | None = None, context: str | None = None):
  """Download a CSV with a unique stable Streamlit key.

  Streamlit generates element IDs from labels/filenames when no key is supplied.
  The app reuses the same label and filename in several loops, tabs and
  expanders, so every download button must receive a key derived from its
  semantic context plus a deterministic disambiguator.
  """
  if df is None or df.empty:
    return
  export_df = augment_ko_pathway_links(df)
  button_key = key or unique_widget_key(context or "csv", (len(export_df), len(export_df.columns)), filename, label, tuple(map(str, export_df.columns[:8])), prefix="download_csv")
  st.download_button(
    label,
    data=export_df.to_csv(index=False).encode("utf-8"),
    file_name=filename,
    mime="text/csv",
    key=button_key,
  )


def sort_if_mag_like(df: pd.DataFrame) -> pd.DataFrame:
  if df is None or df.empty:
    return df
  out = df.copy()
  # Prefer explicit MAG columns, then user_genome/bin columns, then row-wide detection.
  candidate_cols = [c for c in out.columns if re.search(r"(^|[^a-z])mag($|[^a-z])|user_genome|bin", str(c), flags=re.I)]
  if candidate_cols:
    col = candidate_cols[0]
    order = out[col].map(mag_number)
  else:
    def row_order(row):
      nums = []
      for v in row.astype(str).tolist()[:8]:
        n = mag_number(v)
        if n is not None:
          nums.append(n)
      return min(nums) if nums else None
    order = out.apply(row_order, axis=1)
  if order.notna().sum() > 0:
    out["__MAG_order__"] = order
    sort_cols = ["__MAG_order__"]
    if candidate_cols:
      sort_cols.append(candidate_cols[0])
    out = out.sort_values(sort_cols, na_position="last").drop(columns=["__MAG_order__"]).reset_index(drop=True)
  return out


def heatmap_row_limit_control(
  df: pd.DataFrame,
  key: str,
  *,
  noun_pt: str = "linhas",
  noun_en: str = "rows",
  default_top: int = 60,
) -> int:
  """Return all rows by default, with an optional Top-N abundance filter."""
  total = max(int(len(df)), 0)
  if total <= 1:
    return total
  show_all = st.checkbox(
    txt(f"Mostrar todos os {total} {noun_pt}", f"Show all {total} {noun_en}"),
    value=True,
    key=f"{key}_show_all_rows",
  )
  if show_all:
    st.caption(txt(
      f"O heatmap contém todos os {total} {noun_pt}; use rolagem vertical/horizontal quando necessário.",
      f"The heatmap contains all {total} {noun_en}; use vertical/horizontal scrolling when needed."
    ))
    return total
  top_n = int(st.number_input(
    txt(f"Top {noun_pt} por abundância total", f"Top {noun_en} by total abundance"),
    min_value=1, max_value=total, value=min(int(default_top), total), step=1,
    key=f"{key}_top_n_{total}",
  ))
  return top_n


def complete_table_note(df: pd.DataFrame, noun_pt: str = "linhas", noun_en: str = "rows") -> None:
  st.caption(txt(
    f"Tabela completa: {len(df)} {noun_pt}. Todas estão carregadas; role verticalmente ou use o download CSV.",
    f"Complete table: {len(df)} {noun_en}. All are loaded; scroll vertically or use the CSV download."
  ))


def show_table(data, key: str | None = None, height: int = 460, width: str = "stretch"):
  """Render an Arrow-safe interactive table with a deterministic unique key."""
  try:
    if data is None:
      st.info(txt("Nenhum dado disponível para esta tabela.", "No data available for this table."))
      return
    try:
      df = pd.DataFrame(data).copy() if not isinstance(data, pd.DataFrame) else data.copy()
    except Exception as exc:
      st.warning(txt(f"Não foi possível renderizar a tabela: {exc}", f"Could not render table: {exc}"))
      return
    if df.empty:
      st.info(txt("Nenhum registro disponível para esta tabela.", "No records available for this table."))
      return
    try:
      df = dataframe_map_compat(df, _clean_table_cell)
    except Exception:
      pass
    try:
      df = sort_if_mag_like(df)
    except Exception:
      pass
    try:
      df = augment_ko_pathway_links(df)
    except Exception:
      pass
    df = arrow_safe_dataframe(df)

    column_config = {}
    try:
      for col in df.columns:
        low = str(col).lower()
        sample_values = df[col].dropna().astype(str).head(50)
        has_http = sample_values.str.startswith(("http://", "https://")).any() if not sample_values.empty else False
        if has_http or low in {"kegg_url", "url", "link"} or low.endswith("_url") or "hyperlink" in low or ("kegg" in low and "url" in low):
          label = str(col).replace("kegg_url", "KEGG link").replace("_url", " URL")
          column_config[col] = st.column_config.LinkColumn(label, display_text="Open")
        elif any(token in low for token in ["classification", "function", "description", "taxonomy", "location", "habitat", "isolation", "study", "interpretation", "role", "pathway"]):
          column_config[col] = st.column_config.TextColumn(str(col), width="large")
    except Exception:
      column_config = {}

    st.dataframe(
      df,
      width=width,
      hide_index=True,
      height=height,
      column_config=column_config,
      key=unique_widget_key(key or "table", getattr(df, "shape", None), tuple(map(str, df.columns[:8])), prefix="dataframe"),
    )
  except Exception as exc:
    st.error(txt(f"A versão interativa não pôde ser gerada: {exc}", f"Interactive version could not be generated: {exc}"))
    try:
      st.table(arrow_safe_dataframe(data))
    except Exception:
      st.warning(txt("A tabela não pôde ser exibida.", "The table could not be displayed."))

def environment_column_label_map(meta: pd.DataFrame) -> dict:
  """Return exactly one canonical x-axis label per ST8 matrix column."""
  labels = {}
  if meta is None or meta.empty or "matrix_column" not in meta.columns:
    return labels
  for _, r in meta.iterrows():
    col = first_present(r, ["matrix_column"])
    if col:
      labels[str(col).strip()] = str(col).strip()
  return labels

def lake_sample_label_map() -> dict:
  """Return exactly one canonical label per AM/TI/TIA/VI sample column."""
  labels = {}
  try:
    meta = taxonomy_samples_metadata()
  except Exception:
    meta = pd.DataFrame()
  if meta is None or meta.empty:
    return labels
  for _, r in meta.iterrows():
    sample = first_present(r, ["sample.id", "Sample"])
    if sample:
      labels[str(sample).strip()] = str(sample).strip()
  return labels

def _is_article_lake_sample_column(col: object) -> bool:
  return bool(re.match(r"^(AM|TIA|TI|VI)\.P\d+\.(D|R)$", str(col).strip()))


def other_metals_lagoon_matrix() -> tuple[pd.DataFrame, list[str], pd.DataFrame]:
  """Map the 20 Outros-metais count columns to AM/TI/TIA/VI lake samples by position.

  The source sheet stores the count columns with generic IMG/M/JGI labels. The
  number and order match the 20 AM/TI/TIA/VI sample columns used in the other
  Supplementary Table 4 lake matrices, so the app exposes the biologically
  interpretable lake-sample names on the x axis and keeps an audit mapping.
  """
  other = load_sheet("table4", "Outros-metais").copy()
  template = load_sheet("table4", "KO-markers-Fe-metabolism").copy()
  lake_cols = [str(c).strip() for c in template.columns if _is_article_lake_sample_column(c)]
  id_cols = [c for c in ["Function Id", "Function Name"] if c in other.columns]
  numeric_cols_raw = [c for c in other.columns if c not in id_cols and pd.to_numeric(other[c], errors="coerce").notna().sum() > 0]
  n = min(len(lake_cols), len(numeric_cols_raw))
  rename = {numeric_cols_raw[i]: lake_cols[i] for i in range(n)}
  out = other.rename(columns=rename)
  for c in lake_cols[:n]:
    if c in out.columns:
      out[c] = pd.to_numeric(out[c], errors="coerce").fillna(0)
  mapping = pd.DataFrame({
    "Original Outros-metais column": numeric_cols_raw[:n],
    "Displayed lake sample on x axis": lake_cols[:n],
  })
  labels = lake_sample_label_map()
  if not mapping.empty:
    mapping["Displayed full label"] = mapping["Displayed lake sample on x axis"].map(lambda x: labels.get(str(x).strip(), str(x)))
  return out, lake_cols[:n], mapping


def st8_axis_label_map() -> dict:
  """Readable labels for Amazonian samples and external ST8 columns."""
  labels = environment_column_label_map(st8_column_metadata())
  labels.update(lake_sample_label_map())
  return labels


def add_descriptive_contrast_context(df: pd.DataFrame, marker_type: str, source_sheet: str) -> pd.DataFrame:
  """Add explicit comparison/method fields for tables and Plotly hovers."""
  if df is None or df.empty:
    return df
  out = df.copy()
  if "ST8_group" not in out.columns:
    out["ST8_group"] = "selected external group"
  if "data_layer" not in out.columns:
    out["data_layer"] = "selected data layer"
  out["comparison"] = "Amazonian lateritic lakes (AM/TI/TIA/VI) vs " + out["ST8_group"].astype(str) + " — " + out["data_layer"].astype(str)
  out["method"] = "Descriptive log2 ratio = log2((mean Amazonian lake count + 1) / (mean selected external group/layer count + 1)); no statistical test is inferred."
  out["source_table"] = "Supplementary Table 8 final"
  out["source_sheet"] = source_sheet
  out["marker_type"] = marker_type
  return out


def st8_contrast_caption(marker_type: str, selected_groups: list[str], selected_layers: list[str]) -> None:
  groups_txt = "; ".join([str(x) for x in selected_groups]) if selected_groups else "all selected ST8 external groups"
  layers_txt = "; ".join([str(x) for x in selected_layers]) if selected_layers else "all selected omics layers"
  st.caption(txt(
    f"Comparação exibida: lagoas lateríticas amazônicas AM/TI/TIA/VI contra {groups_txt}; camadas: {layers_txt}. Método: razão descritiva log2((média nas lagoas amazônicas + 1)/(média no grupo/camada externo selecionado + 1)). Fonte: Supplementary Table 8 final; tipo de marcador: {marker_type}.",
    f"Displayed comparison: Amazonian lateritic lakes AM/TI/TIA/VI versus {groups_txt}; layers: {layers_txt}. Method: descriptive log2 ratio log2((mean in Amazonian lakes + 1)/(mean in the selected external group/layer + 1)). Source: final Supplementary Table 8; marker type: {marker_type}."
  ))


def venn_region_sets(set_map: dict[str, set]) -> dict[str, dict]:
  """Build exclusive and shared regions for two or three displayed sets."""
  names = [str(k) for k, v in set_map.items() if isinstance(v, set) and v][:3]
  if len(names) < 2:
    return {}
  sets = {name: set(set_map[name]) for name in names}
  regions: dict[str, dict] = {}
  union_all = set.union(*sets.values())
  intersection_all = set.intersection(*sets.values())
  regions["common_all"] = {
    "label": " ∩ ".join(names),
    "description": "Common to all displayed sets",
    "members": intersection_all,
    "sets": names,
  }
  for name in names:
    others = [sets[n] for n in names if n != name]
    members = sets[name] - set.union(*others) if others else sets[name]
    regions[f"only::{name}"] = {
      "label": f"{name} only",
      "description": f"Present only in {name}",
      "members": members,
      "sets": [name],
    }
  if len(names) == 3:
    for i in range(3):
      for j in range(i + 1, 3):
        a, b = names[i], names[j]
        third = next(name for name in names if name not in {a, b})
        members = (sets[a] & sets[b]) - sets[third]
        regions[f"pair::{a}::{b}"] = {
          "label": f"{a} ∩ {b}",
          "description": f"Common to {a} and {b}, excluding {third}",
          "members": members,
          "sets": [a, b],
        }
  regions["union"] = {
    "label": "Union",
    "description": "Present in at least one displayed set",
    "members": union_all,
    "sets": names,
  }
  return regions


def simple_venn_figure(set_map: dict[str, set], title: str, selected_region: str | None = None):
  """Create a selectable Venn-like figure with a non-overlapping legend."""
  names = [str(k) for k, v in set_map.items() if isinstance(v, set) and v][:3]
  if len(names) < 2:
    return None
  sets = {name: set(set_map[name]) for name in names}
  regions = venn_region_sets(sets)
  fig = go.Figure()
  if len(names) == 2:
    circle_specs = [(0.40, 0.54, names[0]), (0.60, 0.54, names[1])]
    point_specs = [
      (0.28, 0.54, f"only::{names[0]}"),
      (0.72, 0.54, f"only::{names[1]}"),
      (0.50, 0.54, "common_all"),
    ]
  else:
    circle_specs = [(0.39, 0.62, names[0]), (0.61, 0.62, names[1]), (0.50, 0.40, names[2])]
    point_specs = [
      (0.25, 0.68, f"only::{names[0]}"),
      (0.75, 0.68, f"only::{names[1]}"),
      (0.50, 0.20, f"only::{names[2]}"),
      (0.50, 0.70, f"pair::{names[0]}::{names[1]}"),
      (0.37, 0.44, f"pair::{names[0]}::{names[2]}"),
      (0.63, 0.44, f"pair::{names[1]}::{names[2]}"),
      (0.50, 0.52, "common_all"),
    ]
  colors = ["rgba(0,121,107,.25)", "rgba(249,168,37,.25)", "rgba(21,101,192,.23)"]
  solid_colors = ["#00796B", "#F9A825", "#1565C0"]
  for i, (x, y, name) in enumerate(circle_specs):
    fig.add_shape(type="circle", xref="paper", yref="paper", x0=x-0.27, x1=x+0.27, y0=y-0.27, y1=y+0.27, fillcolor=colors[i], line=dict(color=solid_colors[i], width=2))
    fig.add_trace(go.Scatter(
      x=[None], y=[None], mode="markers", name=name, showlegend=True,
      marker=dict(size=13, color=solid_colors[i], line=dict(color=solid_colors[i], width=1)),
      hoverinfo="skip",
    ))

  xs, ys, labels, hover, region_keys, sizes = [], [], [], [], [], []
  for x, y, region_key in point_specs:
    region = regions.get(region_key)
    if region is None:
      continue
    n = len(region["members"])
    xs.append(x); ys.append(y); region_keys.append(region_key)
    labels.append(f"<b>{n}</b>")
    hover.append(f"{region['label']}<br>{region['description']}<br>n={n}<br>Click to display the taxa")
    sizes.append(48 if region_key == "common_all" else 38)
  selected_points = [region_keys.index(selected_region)] if selected_region in region_keys else []
  fig.add_trace(go.Scatter(
    x=xs, y=ys, mode="markers+text", text=labels, textposition="middle center",
    customdata=np.asarray(region_keys, dtype=object).reshape(-1, 1),
    marker=dict(size=[56 if key == "common_all" else 46 for key in region_keys], color="rgba(255,255,255,0.96)", line=dict(color="#111827", width=2.5)),
    textfont=dict(size=22, family="Arial Black, Arial, sans-serif", color="#000000"),
    hovertext=hover, hovertemplate="%{hovertext}<extra></extra>",
    selected=dict(marker=dict(opacity=1.0, color="#FFCDD2", size=60, line=dict(color="#B71C1C", width=3))),
    unselected=dict(marker=dict(opacity=0.95)),
    selectedpoints=selected_points,
    name="Clickable overlap regions", showlegend=False,
  ))
  fig.add_annotation(x=0.50, y=0.055, xref="paper", yref="paper", text=f"Union n={len(set.union(*sets.values()))} • click a numbered region", showarrow=False, font=dict(size=12))
  fig.update_xaxes(visible=False, range=[0, 1])
  fig.update_yaxes(visible=False, range=[0, 1])
  fig.update_layout(
    title=dict(text=title, y=0.985, x=0.01, xanchor="left", yanchor="top"),
    height=690, margin=dict(l=20, r=20, t=95, b=130),
    paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    clickmode="event+select", dragmode="select", showlegend=True,
    legend=dict(orientation="h", y=-0.11, yanchor="top", x=0.5, xanchor="center", bgcolor="rgba(255,255,255,0.96)", bordercolor="#CFD8DC", borderwidth=1, font=dict(size=11), title_text="Displayed sets"),
  )
  return fig


def _selected_venn_region(event, valid_regions: set[str]) -> str | None:
  try:
    points = event.selection.points
  except Exception:
    try:
      points = event.get("selection", {}).get("points", [])
    except Exception:
      points = []
  for point in points or []:
    custom = point.get("customdata") if isinstance(point, dict) else getattr(point, "customdata", None)
    region = custom[0] if isinstance(custom, (list, tuple)) and custom else custom
    if str(region) in valid_regions:
      return str(region)
  return None


def taxonomy_overlap_panel(tax: pd.DataFrame, meta: pd.DataFrame, selected_groups: list[str], selected_layers: list[str]):
  st.markdown("#### " + txt("Sobreposição entre camadas/datasets", "Overlap between layers/datasets"))
  st.caption(txt(
    "O diagrama e as tabelas usam as taxonomias GTDB da Supplementary Table 8 final. A presença é definida por count_or_abundance > 0. Nos diagramas com dois ou três conjuntos, clique em uma região numerada para listar os táxons daquela interseção exclusiva ou compartilhada.",
    "The diagram and tables use GTDB taxonomy from the final Supplementary Table 8. Presence is defined as count_or_abundance > 0. For diagrams with two or three sets, click a numbered region to list taxa in that exclusive or shared intersection."
  ))
  if tax is None or tax.empty:
    st.info(txt("Resumo taxonômico ST8 ausente.", "ST8 taxonomy summary is missing."))
    return
  c1, c2 = st.columns([0.28, 0.72])
  with c1:
    level = st.radio(txt("Nível para sobreposição", "Overlap level"), ["Phylum", "Order", "Family"], horizontal=False, key="st8_overlap_level")
    group_mode = st.selectbox(txt("Comparar conjuntos por", "Compare sets by"), ["data_layer", "ST8_group"], index=0, key="st8_overlap_group_mode")
  work = tax[tax["taxonomy_level"].eq(level)].copy()
  if selected_groups:
    work = work[work["ST8_group"].isin(selected_groups)]
  if selected_layers:
    work = work[work["data_layer"].isin(selected_layers)]
  work["count_or_abundance"] = pd.to_numeric(work["count_or_abundance"], errors="coerce").fillna(0)
  work = work[work["count_or_abundance"] > 0]
  if work.empty:
    with c2:
      st.info(txt("Sem táxons positivos após os filtros.", "No positive taxa after filters."))
    return
  set_map = {str(k): set(v["taxon"].dropna().astype(str)) for k, v in work.groupby(group_mode)}
  set_map = {k: v for k, v in set_map.items() if v}
  available_sets = sorted(set_map)
  if len(available_sets) > 3:
    with c1:
      venn_sets = st.multiselect(
        txt("Conjuntos exibidos no Venn (2–3)", "Sets displayed in the Venn (2–3)"),
        available_sets,
        default=available_sets[:3],
        max_selections=3,
        key=f"st8_venn_sets_{level}_{group_mode}",
        help=txt("Escolha até três grupos para visualizar interseções clicáveis. Os demais continuam disponíveis na matriz de presença/ausência.", "Choose up to three groups for clickable intersections. Remaining groups continue to be available in the presence/absence matrix."),
      )
    if len(venn_sets) >= 2:
      set_map = {name: set_map[name] for name in venn_sets}
  regions = venn_region_sets(set_map) if 2 <= len(set_map) <= 3 else {}

  selected_region_key = "common_all"
  with c2:
    if regions:
      event_key = f"st8_{level}_{group_mode}_venn_select"
      region_state_key = f"{event_key}_region"
      region_options = [key for key in regions if key != "union"] + ["union"]
      if st.session_state.get(region_state_key) not in region_options:
        st.session_state[region_state_key] = "common_all"
      fig = simple_venn_figure(
        set_map,
        f"{level} overlap by {group_mode}",
        selected_region=st.session_state.get(region_state_key),
      )
      try:
        event = st.plotly_chart(fig, width="stretch", key=event_key, on_select="rerun", selection_mode="points", config={"displaylogo": False})
        clicked = _selected_venn_region(event, set(regions))
        if clicked and clicked != st.session_state.get(region_state_key):
          st.session_state[region_state_key] = clicked
          st.rerun()
      except TypeError:
        st.plotly_chart(fig, width="stretch", key=event_key, config={"displaylogo": False})
      selected_region_key = st.selectbox(
        txt("Região/interseção exibida abaixo", "Region/intersection displayed below"),
        region_options,
        format_func=lambda key: f"{regions[key]['label']} — n={len(regions[key]['members'])}",
        key=region_state_key,
        help=txt("O seletor e o clique no diagrama controlam a mesma região.", "The selector and diagram click control the same region."),
      )
      st.download_button(
        txt("Baixar diagrama Venn em HTML", "Download Venn diagram as HTML"),
        data=fig.to_html(include_plotlyjs=True).encode("utf-8"),
        file_name=f"ST8_{level}_{group_mode}_interactive_venn.html",
        mime="text/html",
        key=f"download_st8_{level}_{group_mode}_venn_html",
      )
    else:
      presence_rows = []
      for name, vals in set_map.items():
        for taxon in vals:
          presence_rows.append({"set": name, "taxon": taxon, "present": 1})
      pres = pd.DataFrame(presence_rows)
      if not pres.empty:
        mat = pres.pivot_table(index="taxon", columns="set", values="present", aggfunc="max", fill_value=0)
        mat["n_sets"] = mat.sum(axis=1)
        mat = mat.sort_values("n_sets", ascending=False).head(80).drop(columns=["n_sets"])
        fig = px.imshow(mat.values, x=mat.columns.tolist(), y=mat.index.tolist(), aspect="auto", color_continuous_scale="Greys", title=f"{level} presence/absence by {group_mode}")
        fig.update_layout(height=max(560, 18 * len(mat) + 180), margin=dict(l=180, r=10, t=80, b=120))
        render_plotly_downloadable(fig, key=f"st8_{level}_{group_mode}_upset_like", basename=f"ST8_{level}_{group_mode}_presence_absence")

  if regions:
    selected_region = regions[selected_region_key]
    selected_taxa = sorted(selected_region["members"])
    st.markdown("##### " + txt("Táxons da região selecionada", "Taxa in the selected region"))
    st.caption(f"{selected_region['label']} — {selected_region['description']} — n={len(selected_taxa)}")
    selected_df = pd.DataFrame({level: selected_taxa})
    selected_df["Region"] = selected_region["label"]
    selected_df["Compared sets"] = "; ".join(selected_region["sets"])
    show_table(selected_df, f"st8_selected_region_{level}_{group_mode}", height=360)
    csv_button(selected_df, f"ST8_{level}_{group_mode}_{selected_region_key.replace(':', '_')}.csv", txt("Baixar táxons da região selecionada", "Download taxa in selected region"))

    summary_rows = []
    for key, region in regions.items():
      summary_rows.append({
        "Region_key": key,
        "Region": region["label"],
        "Description": region["description"],
        "Compared_sets": "; ".join(region["sets"]),
        "n_taxa": len(region["members"]),
      })
    summary_df = pd.DataFrame(summary_rows).sort_values(["n_taxa", "Region"], ascending=[False, True])
    with st.expander(txt("Resumo de todas as regiões e comparações comuns", "Summary of all regions and shared comparisons"), expanded=True):
      show_table(summary_df, f"st8_region_summary_{level}_{group_mode}", height=360)
      csv_button(summary_df, f"ST8_{level}_{group_mode}_all_overlap_regions.csv", txt("Baixar resumo das regiões", "Download region summary"))
      for key, region in regions.items():
        if key == "union":
          continue
        region_df = pd.DataFrame({level: sorted(region["members"])})
        with st.expander(f"{region['label']} — n={len(region_df)}", expanded=False):
          show_table(region_df, f"st8_region_members_{level}_{group_mode}_{key}", height=260)

  common = sorted(set.intersection(*set_map.values())) if len(set_map) >= 2 else sorted(next(iter(set_map.values()))) if set_map else []
  common_df = pd.DataFrame({f"{level} common to all selected {group_mode} sets": common})
  with st.expander(txt("Interseção comum a todos os conjuntos", "Intersection common to every set"), expanded=False):
    show_table(common_df, f"st8_common_{level}_{group_mode}", height=320)
    csv_button(common_df, f"ST8_common_{level}_{group_mode}.csv", txt("Baixar itens comuns", "Download common items"))
  if meta is not None and not meta.empty and group_mode in meta.columns:
    sample_sets = {str(k): set(v.get("sample_id_created_this_study", v.get("sample_id", pd.Series(dtype=str))).dropna().astype(str)) for k, v in meta.groupby(group_mode)}
    sample_sets = {k: v for k, v in sample_sets.items() if k in set_map and v}
    if len(sample_sets) >= 2:
      common_samples = sorted(set.intersection(*sample_sets.values()))
      sample_df = pd.DataFrame({f"Samples common to all selected {group_mode} sets": common_samples})
      with st.expander(txt("Amostras compartilhadas entre datasets/camadas", "Samples shared between datasets/layers"), expanded=False):
        st.caption(txt(
          "A maioria dos registros externos IMG/M representa amostras distintas; por isso a interseção de amostras pode ser zero mesmo quando há táxons compartilhados.",
          "Most external IMG/M records represent distinct samples; therefore sample intersection can be zero even when taxa are shared."
        ))
        show_table(sample_df, f"st8_common_samples_{group_mode}", height=260)
        csv_button(sample_df, f"ST8_common_samples_{group_mode}.csv", txt("Baixar amostras comuns", "Download common samples"))


def download_text_file_button(path: Path, label: str, filename: str | None = None):
  try:
    if path.exists():
      st.download_button(label, data=path.read_text(encoding="utf-8").encode("utf-8"), file_name=filename or path.name, mime="text/plain", key="download_" + re.sub(r"[^A-Za-z0-9_]+", "_", str(path)))
  except Exception:
    pass


def visitor_counter_public_footer(key: str = "public_footer"):
  metrics = visitor_summary_metrics()
  countries = visitor_country_summary()
  total = int(metrics.get("total_visits", 0))
  chips = []
  if not countries.empty:
    for _, row in countries.head(12).iterrows():
      flag = html_lib.escape(str(row.get("Flag", "🌐")))
      visits = int(row.get("Visits", 0))
      chips.append(f'<span class="visitor-chip">{flag} <b>{visits}</b></span>')
  if not chips:
    chips.append('<span class="visitor-chip">🌐 <b>0</b></span>')
  st.markdown(
    f"""
<div class="public-visitor-footer">
  <b>{txt('Visits', 'Visits')}:</b> {total} &nbsp; {' '.join(chips)}
</div>
""",
    unsafe_allow_html=True,
  )


def visitor_counter_compact():
  """Compact public visitor counter displayed in the page header."""
  metrics = visitor_summary_metrics()
  countries = visitor_country_summary()
  total = int(metrics.get("total_visits", 0))
  chips = []
  if not countries.empty:
    for _, row in countries.head(8).iterrows():
      flag = html_lib.escape(str(row.get("Flag", "🌐")))
      country = html_lib.escape(str(row.get("Country", "Unknown")))
      visits = int(row.get("Visits", 0))
      chips.append(f'<span class="visitor-chip">{flag} {country}: <b>{visits}</b></span>')
  if not chips:
    chips.append(f'<span class="visitor-chip">🌐 {txt("Sem visitas registradas", "No visits recorded")}</span>')
  current = st.session_state.get("visitor_current_record", {}) or {}
  current_city = html_lib.escape(str(current.get("city", "Unknown")))
  current_country = html_lib.escape(str(current.get("country_name", "Unknown")))
  current_flag = html_lib.escape(str(current.get("country_flag", "🌐")))
  st.markdown(
    f"""
<div class="visitor-counter-card">
  <b>{txt("Contador de visitas", "Visitor counter")}</b><br>
  {txt("Total", "Total")}: <b>{total}</b> • {txt("Países", "Countries")}: <b>{int(metrics.get("countries", 0))}</b> • {txt("Cidades", "Cities")}: <b>{int(metrics.get("cities", 0))}</b><br>
  <span style="font-size:.80rem;color:#475569;">{txt("Sua sessão", "Your session")}: {current_flag} {current_city}, {current_country}</span><br>
  {''.join(chips)}
</div>
""",
    unsafe_allow_html=True,
  )


def visitor_analytics_tab():
  if not is_admin_authenticated():
    st.warning(txt("Esta área de gestão do contador é restrita ao admin.", "This visitor-management area is restricted to the admin."))
    visitor_counter_public_footer("visitor_public_only")
    return
  st.subheader(txt("Contador de visitas e origem geográfica — admin", "Visitor counter and geographic origin — admin"))
  st.markdown(txt(
    "Esta página registra visitas por sessão e mostra a distribuição por país e cidade. O app tenta detectar país/cidade a partir dos cabeçalhos do servidor ou, quando houver IP público disponível, por consulta geográfica externa com cache local.",
    "This page records one visit per session and shows distribution by country and city. The app tries to detect country/city from server headers or, when a public IP is available, by cached external geolocation lookup."
  ))
  st.caption(txt(
    "Privacidade: o IP bruto não é salvo. O log armazena apenas hash do IP/sessão, país, cidade, fonte da geolocalização, versão do app e data/hora UTC.",
    "Privacy: the raw IP is not stored. The log stores only hashed IP/session identifiers, country, city, geolocation source, app version and UTC timestamp."
  ))

  metrics = visitor_summary_metrics()
  country_df = visitor_country_summary()
  city_df = visitor_city_summary()
  visits_df = load_visitor_visits()

  c1, c2, c3, c4 = st.columns(4)
  c1.metric(txt("Visitas totais", "Total visits"), int(metrics.get("total_visits", 0)))
  c2.metric(txt("Países", "Countries"), int(metrics.get("countries", 0)))
  c3.metric(txt("Cidades", "Cities"), int(metrics.get("cities", 0)))
  c4.metric(txt("Última visita UTC", "Last visit UTC"), str(metrics.get("last_visit_utc", "") or "—")[:19])

  if country_df.empty:
    st.info(txt(
      "Ainda não há visitas registradas. Recarregue o app em uma sessão pública para iniciar o contador.",
      "No visits have been recorded yet. Reload the app in a public session to start the counter."
    ))
  else:
    country_plot = country_df.copy()
    country_plot["Country display"] = country_plot["Flag"].astype(str) + " " + country_plot["Country"].astype(str)
    fig = px.bar(
      country_plot.sort_values("Visits", ascending=True),
      x="Visits",
      y="Country display",
      orientation="h",
      text="Visits",
      title=txt("Visitas por país", "Visits by country"),
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(height=max(380, 55 * len(country_plot)), margin=dict(l=10, r=50, t=70, b=40), yaxis_title="", xaxis_title=txt("Visitas", "Visits"))
    render_plotly_downloadable(fig, key="visitor_country_bar", basename="visitor_country_counts")

    st.markdown("#### " + txt("Contagem por país", "Counts by country"))
    show_table(country_df, "visitor_country_summary", height=min(520, 120 + 36 * len(country_df)))
    csv_button(country_df, "visitor_country_summary.csv", txt("Baixar resumo por país", "Download country summary"))

  st.markdown("#### " + txt("Contagem por cidade", "Counts by city"))
  if city_df.empty:
    st.info(txt("Nenhuma cidade registrada ainda.", "No city has been recorded yet."))
  else:
    show_table(city_df, "visitor_city_summary", height=min(520, 120 + 36 * len(city_df)))
    csv_button(city_df, "visitor_city_summary.csv", txt("Baixar resumo por cidade", "Download city summary"))

  with st.expander(txt("Auditoria recente de visitas", "Recent visit audit"), expanded=False):
    if visits_df.empty:
      st.info(txt("Sem eventos de visita no log.", "No visit events in the log."))
    else:
      recent_cols = [c for c in ["timestamp_utc", "country_flag", "country_name", "country_code", "city", "geo_source", "app_version", "database_version", "raw_ip_stored"] if c in visits_df.columns]
      recent = visits_df[recent_cols].tail(100).sort_values("timestamp_utc", ascending=False) if "timestamp_utc" in visits_df.columns else visits_df[recent_cols].tail(100)
      show_table(recent, "visitor_recent_audit", height=420)
      csv_button(recent, "visitor_recent_audit_public_fields.csv", txt("Baixar auditoria recente", "Download recent audit"))
      st.code(str(VISITOR_LOG_PATH.relative_to(BASE_DIR)), language="text")

  with st.expander(txt("Como garantir país e cidade em produção", "How to ensure country and city in production"), expanded=False):
    st.markdown(txt(
      """
Para captura mais confiável em produção, coloque o app atrás de Cloudflare/Nginx/Render/Vercel ou outro proxy que envie cabeçalhos de origem. O app já reconhece, quando disponíveis: `CF-Connecting-IP`, `CF-IPCountry`, `X-Forwarded-For`, `X-Real-IP`, `X-Vercel-IP-Country`, `X-Vercel-IP-City`, `X-Geo-Country`, `X-Geo-City`, `X-Country-Code` e `X-City`.

Se apenas o IP público do visitante estiver disponível, o app tenta resolver país/cidade usando serviço público de geolocalização com timeout curto e cache no diretório gravável do usuário (`~/.local/state/cangametag_atlas_v7/visitor/visitor_geo_cache.json` por padrão). Em ambiente local ou quando o provedor não expõe IP/cabeçalhos, país e cidade podem aparecer como `Unknown`.
""",
      """
For more reliable production capture, place the app behind Cloudflare/Nginx/Render/Vercel or another proxy that sends origin headers. The app already recognizes, when available: `CF-Connecting-IP`, `CF-IPCountry`, `X-Forwarded-For`, `X-Real-IP`, `X-Vercel-IP-Country`, `X-Vercel-IP-City`, `X-Geo-Country`, `X-Geo-City`, `X-Country-Code` and `X-City`.

If only the visitor public IP is available, the app tries to resolve country/city using a public geolocation service with short timeout and cache in the user-writable runtime directory (`~/.local/state/cangametag_atlas_v7/visitor/visitor_geo_cache.json` by default). In local environments or when the hosting provider does not expose IP/geo headers, country and city may appear as `Unknown`.
"""
    ))

  if st.session_state.get("admin_authenticated", False):
    with st.expander(txt("Administração do contador", "Counter administration"), expanded=False):
      st.warning(txt(
        "Use apenas se quiser apagar o histórico local de visitas desta instalação.",
        "Use only if you want to delete the local visitor history for this installation."
      ))
      if st.button(txt("Limpar histórico de visitas", "Clear visitor history"), key="clear_visitor_history", width="stretch"):
        removed = clear_visitor_data()
        st.session_state.pop("visitor_visit_recorded", None)
        st.session_state.pop("visitor_current_record", None)
        st.success(txt(f"Histórico limpo. Arquivos removidos: {removed}.", f"History cleared. Files removed: {removed}."))
        st.rerun()


def _clean_column_label(value: object, position: int) -> str:
  label = str(value).strip() if value is not None and not pd.isna(value) else ""
  if not label or label.lower() == "nan":
    label = f"column_{position + 1}"
  return label


def _deduplicate_column_labels(values) -> list[str]:
  labels: list[str] = []
  seen: dict[str, int] = {}
  for position, value in enumerate(values):
    base = _clean_column_label(value, position)
    count = seen.get(base, 0)
    seen[base] = count + 1
    labels.append(base if count == 0 else f"{base}_{count + 1}")
  return labels


def _mag_sort_column(df: pd.DataFrame) -> str | None:
  if df is None or df.empty:
    return None
  preferred = {
    "mag", "mag id", "mag_id", "mag identifier", "bin", "bin id",
    "bin_id", "bin name", "genome", "genome id", "genome_id",
  }
  for column in df.columns:
    if str(column).strip().lower() in preferred:
      return str(column)
  best_column = None
  best_count = 0
  for column in df.columns:
    numbers = df[column].map(mag_number)
    count = int(numbers.notna().sum())
    if count > best_count:
      best_column = str(column)
      best_count = count
  return best_column if best_count > 0 else None


def sort_mags_table(df: pd.DataFrame) -> pd.DataFrame:
  """Return a clean natural MAG order: MAG1, MAG2, ..., MAG10."""
  if df is None or df.empty:
    return df
  out = df.copy()
  mag_column = _mag_sort_column(out)
  if mag_column is None:
    return out.reset_index(drop=True)
  numbers = out[mag_column].map(mag_number)
  valid = numbers.notna()
  out.loc[valid, mag_column] = numbers.loc[valid].map(lambda value: f"MAG{int(value)}")
  out["__MAG_sort_number"] = numbers
  out["__MAG_sort_text"] = out[mag_column].astype(str)
  out = out.sort_values(
    ["__MAG_sort_number", "__MAG_sort_text"],
    kind="stable",
    na_position="last",
  ).drop(columns=["__MAG_sort_number", "__MAG_sort_text"])
  return out.reset_index(drop=True)


def _classification_header_score(row: pd.Series) -> tuple[int, int]:
  values = [str(value).strip() for value in row.tolist() if value is not None and not pd.isna(value) and str(value).strip()]
  tokens = " | ".join(values).lower()
  keywords = (
    "mag", "bin", "classification", "lineage", "taxonomy", "taxon",
    "ena", "accession", "domain", "phylum", "class", "order",
    "family", "genus", "species", "kaiju", "confidence", "rrna",
  )
  score = sum(1 for keyword in keywords if keyword in tokens)
  return score, len(values)


def prepare_mag_classification_table(df: pd.DataFrame) -> pd.DataFrame:
  """Repair embedded headers/title rows and sort MAGs numerically."""
  if df is None or df.empty:
    return pd.DataFrame()
  out = df.copy().dropna(axis=0, how="all").dropna(axis=1, how="all")
  if out.empty:
    return out

  scored = [(_classification_header_score(row), idx) for idx, row in out.iterrows()]
  candidates = [item for item in scored if item[0][0] >= 2 and item[0][1] >= 2]
  if candidates:
    (_, _), header_idx = max(candidates, key=lambda item: (item[0][0], item[0][1], item[1]))
    headers = _deduplicate_column_labels(out.loc[header_idx].tolist())
    before = out.loc[out.index < header_idx].copy()
    after = out.loc[out.index > header_idx].copy()
    out = pd.concat([before, after], ignore_index=True)
    out.columns = headers
  else:
    out.columns = _deduplicate_column_labels(out.columns)

  def is_title_or_repeated_header(row: pd.Series) -> bool:
    values = [str(value).strip() for value in row.tolist() if value is not None and not pd.isna(value) and str(value).strip()]
    if not values:
      return True
    combined = " | ".join(values).lower()
    if len(values) == 1 and any(term in combined for term in (
      "taxonomic classification", "classification and ena", "kaiju classification",
      "rrna machinery", "gtdb-tk", "bin.classification",
    )):
      return True
    row_score, nonempty = _classification_header_score(row)
    return nonempty >= 2 and row_score >= 3 and all(
      str(value).strip() in set(out.columns) for value in values
    )

  out = out.loc[~out.apply(is_title_or_repeated_header, axis=1)].copy()
  out = out.dropna(axis=0, how="all").dropna(axis=1, how="all")
  return sort_mags_table(out)


def load_mag_classification_sheet(sheet_name: str) -> pd.DataFrame:
  """Read MAG classification sheets without assuming the header is the first row."""
  relative = TABLE_FILES.get("table7", "data/Supplementary_table_7-MAGS-Quality-Genome_Lineage-Classification.xlsx")
  workbook = BASE_DIR / relative
  if not workbook.exists():
    return prepare_mag_classification_table(load_sheet("table7", sheet_name))
  try:
    raw = pd.read_excel(workbook, sheet_name=sheet_name, header=None)
    return prepare_mag_classification_table(raw)
  except Exception:
    return prepare_mag_classification_table(load_sheet("table7", sheet_name))


def is_all_mags(value: object) -> bool:
  return str(value).lower().startswith(("all", "todos"))


def filter_table_by_mag(df: pd.DataFrame, selected_mag: object) -> pd.DataFrame:
  if df is None or df.empty or is_all_mags(selected_mag):
    return df
  n = mag_number(selected_mag)
  if n is None:
    return pd.DataFrame(columns=df.columns)
  pattern = fr"(?:MAG[\._\-\s]*{n}\b|MAG{n}\b|bin[\._\-\s]*{n}\b)"
  mask = df.astype(str).apply(lambda col: col.str.contains(pattern, case=False, regex=True, na=False)).any(axis=1)
  return df[mask].copy()


def taxonomy_matrix(level_name: str, groups: List[str] | None = None, top_n: int = 50) -> tuple[pd.DataFrame, pd.DataFrame]:
  df = taxonomy_table(level_name)
  if groups:
    df = df[df["group"].isin(groups)]
  if df.empty:
    return pd.DataFrame(), pd.DataFrame()
  top_taxa = df.groupby("taxon", as_index=False)["abundance"].sum().sort_values("abundance", ascending=False).head(top_n)["taxon"]
  work = df[df["taxon"].isin(top_taxa)].copy()
  matrix = work.pivot_table(index="group", columns="taxon", values="abundance", aggfunc="sum", fill_value=0)
  meta_cols = [c for c in ["group", "environment_feature", "lake", "season", "collection_date", "lat", "lon"] if c in work.columns]
  meta = work[meta_cols].drop_duplicates("group").set_index("group") if meta_cols else pd.DataFrame(index=matrix.index)
  return matrix, meta


def _canonical_beta_transform(matrix: pd.DataFrame) -> pd.DataFrame:
  """Compatibility wrapper around the single article implementation."""
  return canonical_beta_transform_matrix(matrix)


def pcoa_from_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
  """Compatibility wrapper around the single article PCoA implementation."""
  result = canonical_pcoa_bray_curtis_matrix(matrix)
  scores = result.get("scores", pd.DataFrame()).copy()
  if scores.empty:
    return scores
  variance = result["variance"].set_index("axis")
  scores = scores.reset_index().rename(columns={"index": "group"})
  scores["PCoA1_explained_%"] = round(float(variance.loc["PCoA1", "explained_variance_percent"]), 2)
  scores["PCoA2_explained_%"] = round(float(variance.loc["PCoA2", "explained_variance_percent"]), 2)
  scores["negative_eigenvalue_count_before_correction"] = int(result["negative_eigenvalue_count"])
  scores["negative_eigenvalue_absolute_sum_before_correction"] = float(result["negative_eigenvalue_absolute_sum"])
  scores["distance_correction"] = str(result["correction"])
  scores["lingoes_constant"] = float(result["lingoes_constant"])
  return scores


def nmds_from_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
  """Compatibility wrapper around the single article NMDS implementation."""
  result = canonical_nmds_bray_curtis_matrix(matrix, random_state=42, n_init=20, max_iter=1000)
  scores = result.get("scores", pd.DataFrame()).copy()
  if scores.empty:
    return scores
  scores = scores.reset_index().rename(columns={"index": "group"})
  scores["stress_1"] = float(result["stress"])
  scores["iterations"] = int(result["n_iter"])
  scores["converged"] = bool(result["converged"])
  scores["n_init"] = 20
  scores["max_iter"] = 1000
  scores["seed"] = 42
  return scores


def diversity_from_matrix(matrix: pd.DataFrame) -> pd.DataFrame:
  if matrix.empty:
    return pd.DataFrame()
  rows = []
  for group, vals in matrix.iterrows():
    v = pd.to_numeric(vals, errors="coerce").fillna(0).astype(float)
    total = v.sum()
    p = v[v > 0] / total if total > 0 else pd.Series(dtype=float)
    rows.append({
      "group": group,
      "Observed taxa": int((v > 0).sum()),
      "Shannon": float(-(p * np.log(p)).sum()) if len(p) else 0.0,
      "Simpson 1-D": float(1 - (p ** 2).sum()) if len(p) else 0.0,
      "Total abundance": float(total),
    })
  return pd.DataFrame(rows)


def cds_taxonomy_group_matrix(level: str, groups: List[str] | None = None, top_n: int = 60) -> pd.DataFrame:
  """Build a CDS-derived taxon matrix for sample-level or lake-season units.

  The raw CDS OTU/taxonomy files are the source of truth. IMG/JGI columns are
  mapped to the visible study sample labels (AM.P1.D, TI.P2.R, etc.). When the
  requested ordination uses lake-season groups (AM-D, TI-R, ...), the same
  sample-level matrix is aggregated deterministically to those groups.
  """
  otu_path = BASE_DIR / "data" / "resultado.cds.otu.tab"
  tax_path = BASE_DIR / "data" / "resultado.cds.tax.tab"
  if not (otu_path.exists() and tax_path.exists()):
    return pd.DataFrame()
  try:
    otu = pd.read_csv(otu_path, sep="\t", index_col=0)
    tax = pd.read_csv(tax_path, sep="\t", index_col=0)
  except Exception:
    return pd.DataFrame()
  tax.columns = [str(c).strip() for c in tax.columns]
  if level not in tax.columns:
    return pd.DataFrame()

  otu.columns = [METAGENOME_SAMPLE_MAP.get(str(c).split("_")[0], str(c)) for c in otu.columns]
  otu = otu.apply(pd.to_numeric, errors="coerce").fillna(0)
  otu = otu.T.groupby(level=0).sum().T

  shared = otu.index.intersection(tax.index)
  labels = tax.loc[shared, level].fillna("Unclassified").astype(str).str.strip()
  valid = ~labels.str.lower().isin({"", "na", "nan", "unknown", "unclassified", "none"})
  shared = shared[valid.to_numpy()]
  labels = labels.loc[shared]
  work = otu.loc[shared].copy()
  work[level] = labels
  sample_matrix = work.groupby(level).sum(numeric_only=True).T

  requested = [str(g) for g in (groups or [])]
  if requested and any(re.fullmatch(r"[A-Z]+-[DR]", g) for g in requested):
    def _lake_season(sample: str) -> str:
      bits = str(sample).split(".")
      if len(bits) >= 3 and bits[-1] in {"D", "R"}:
        return f"{bits[0]}-{bits[-1]}"
      return str(sample)
    sample_matrix = sample_matrix.groupby(sample_matrix.index.map(_lake_season)).sum()

  if requested:
    ordered = [g for g in requested if g in sample_matrix.index]
    sample_matrix = sample_matrix.reindex(ordered).dropna(how="all")
  if sample_matrix.empty:
    return sample_matrix
  keep = sample_matrix.sum(axis=0).sort_values(ascending=False).head(int(top_n)).index
  return sample_matrix.loc[:, keep].fillna(0)


def ordination_taxon_vectors(matrix: pd.DataFrame, ord_df: pd.DataFrame, x: str, y: str, top_n: int = 15) -> pd.DataFrame:
  if matrix.empty or ord_df.empty or "group" not in ord_df.columns:
    return pd.DataFrame()
  common = [g for g in ord_df["group"].astype(str) if g in matrix.index]
  if len(common) < 4:
    return pd.DataFrame()
  coords = ord_df.set_index("group").loc[common, [x, y]].apply(pd.to_numeric, errors="coerce")
  mat = matrix.loc[common].apply(pd.to_numeric, errors="coerce").fillna(0)
  rows = []
  for taxon in mat.columns:
    vals = mat[taxon].to_numpy(float)
    if np.allclose(np.std(vals), 0):
      continue
    vx = np.corrcoef(vals, coords[x].to_numpy(float))[0, 1]
    vy = np.corrcoef(vals, coords[y].to_numpy(float))[0, 1]
    if not np.isfinite(vx) or not np.isfinite(vy):
      continue
    rows.append({"Taxon": str(taxon), x: float(vx), y: float(vy), "vector_length": float(np.hypot(vx, vy))})
  if not rows:
    return pd.DataFrame()
  return pd.DataFrame(rows).sort_values(["vector_length", "Taxon"], ascending=[False, True]).head(int(top_n)).reset_index(drop=True)


def add_taxon_biplot_vectors(fig: go.Figure, vectors: pd.DataFrame, x: str, y: str, ord_df: pd.DataFrame) -> go.Figure:
  """Add taxon vectors with repelled labels and visible connector lines."""
  if vectors.empty:
    return fig
  scale = max(0.15, float(np.nanmax(np.abs(ord_df[[x, y]].to_numpy(float)))) * 0.82)
  plot = vectors.copy()
  plot["endpoint_x"] = pd.to_numeric(plot[x], errors="coerce").fillna(0) * scale
  plot["endpoint_y"] = pd.to_numeric(plot[y], errors="coerce").fillna(0) * scale
  plot = repel_label_positions(plot, "endpoint_x", "endpoint_y", min_distance=0.20, radial_offset=0.24)
  for _, row in plot.iterrows():
    endpoint_x = float(row["endpoint_x"])
    endpoint_y = float(row["endpoint_y"])
    label_x = float(row["label_x"])
    label_y = float(row["label_y"])
    label = textwrap.shorten(str(row["Taxon"]), width=36, placeholder="…")
    fig.add_shape(
      type="line", x0=0, y0=0, x1=endpoint_x, y1=endpoint_y,
      line=dict(color="rgba(178,24,43,0.62)", width=1.25, dash="dot"),
    )
    fig.add_annotation(
      x=endpoint_x, y=endpoint_y, ax=label_x, ay=label_y,
      xref="x", yref="y", axref="x", ayref="y",
      showarrow=True, arrowhead=2, arrowsize=0.9, arrowwidth=1.0,
      arrowcolor="rgba(178,24,43,0.72)", text=label,
      font=dict(size=11, color="#B2182B"), bgcolor="rgba(255,255,255,0.92)",
      bordercolor="rgba(178,24,43,0.35)", borderwidth=1, borderpad=2,
    )
  return fig


def add_repelled_vector_annotations(
  fig: go.Figure,
  frame: pd.DataFrame,
  *,
  x_col: str,
  y_col: str,
  label_col: str,
  color: str = "#444444",
  dash: str = "solid",
  label_width: int = 38,
  min_distance: float = 0.20,
  radial_offset: float = 0.24,
) -> go.Figure:
  """Draw vectors and repelled labels connected to their endpoints."""
  if frame is None or frame.empty:
    return fig
  plot = frame.copy()
  plot[x_col] = pd.to_numeric(plot[x_col], errors="coerce")
  plot[y_col] = pd.to_numeric(plot[y_col], errors="coerce")
  plot = plot.dropna(subset=[x_col, y_col]).reset_index(drop=True)
  if plot.empty:
    return fig
  plot = repel_label_positions(
    plot, x_col, y_col, min_distance=min_distance, radial_offset=radial_offset
  )
  for _, row in plot.iterrows():
    x = float(row[x_col]); y = float(row[y_col])
    lx = float(row["label_x"]); ly = float(row["label_y"])
    label = textwrap.shorten(str(row[label_col]), width=label_width, placeholder="…")
    fig.add_shape(
      type="line", x0=0, y0=0, x1=x, y1=y,
      line=dict(color=color, width=1.4, dash=dash),
    )
    fig.add_annotation(
      x=x, y=y, ax=lx, ay=ly,
      xref="x", yref="y", axref="x", ayref="y",
      text=label, showarrow=True, arrowhead=2, arrowsize=0.9,
      arrowwidth=1.0, arrowcolor=color,
      font=dict(size=11, color=color),
      bgcolor="rgba(255,255,255,0.94)", bordercolor=color,
      borderwidth=0.7, borderpad=2,
    )
  return fig


def taxonomy_diversity_panel(level_name: str, groups: List[str] | None = None, top_n: int = 60):
  st.markdown("#### " + txt("Diversidade alfa e beta no estilo do artigo", "Article-style alpha and beta diversity"))
  st.caption(txt(
    "Os painéis usam exclusivamente as contagens/abundâncias da Supplementary Table 1 e dos arquivos CDS do estudo. PCoA e NMDS podem exibir um biplot opcional de táxons em Phylum, Order, Genus ou Species, com n selecionável de 2 a 20. Nenhuma amostra ou valor é simulado.",
    "Panels exclusively use counts/abundances from Supplementary Table 1 and the study CDS files. PCoA and NMDS can display an optional taxon biplot at Phylum, Order, Genus or Species rank, with selectable n from 2 to 20. No sample or value is simulated."
  ))
  matrix, meta = taxonomy_matrix(level_name, groups=groups, top_n=top_n)
  if matrix.empty:
    st.info(txt("Sem matriz suficiente para diversidade.", "Not enough matrix data for diversity."))
    return
  alpha = diversity_from_matrix(matrix)
  if not meta.empty:
    alpha = alpha.merge(meta.reset_index(), on="group", how="left")
  c1, c2 = st.columns([0.38, 0.62])
  with c1:
    metric = st.selectbox(txt("Métrica alfa", "Alpha metric"), ["Observed taxa", "Shannon", "Simpson 1-D", "Total abundance"], index=1, key=f"alpha_metric_{level_name}")
    view_kind = st.radio(txt("Visualização alfa", "Alpha visualization"), ["Barplot", "Boxplot por tipo de amostra"], horizontal=True, key=f"alpha_view_{level_name}")
    color_col = "season" if "season" in alpha.columns else "group"
    alpha_stats = pd.DataFrame()
    if view_kind.startswith("Boxplot"):
      available_factors = [c for c in ["lake", "season", "environment_feature", "group"] if c in alpha.columns and alpha[c].dropna().astype(str).nunique() >= 2]
      comparison_factor = st.selectbox(
        txt("Fator comparado no boxplot", "Boxplot comparison factor"),
        available_factors or ["group"],
        key=f"alpha_box_factor_{level_name}_{metric}",
      )
      secondary_color = next((c for c in ["season", "lake"] if c in alpha.columns and c != comparison_factor), None)
      fig = px.box(
        alpha, x=comparison_factor, y=metric, color=secondary_color,
        points="all", hover_data=alpha.columns,
        title=f"Alpha diversity — {metric} by {comparison_factor}",
      )
      alpha_stats = _numeric_group_stats(alpha, metric, comparison_factor, category="Alpha diversity")
    else:
      fig = px.bar(alpha, x="group", y=metric, color=color_col, hover_data=alpha.columns, title=f"Alpha diversity — {metric}")
    fig.update_layout(height=620 if view_kind.startswith("Boxplot") else 560, xaxis_tickangle=-35, margin=dict(l=80, r=30, t=90 if view_kind.startswith("Boxplot") else 80, b=180))
    bold_axis_layout(fig, x_size=15, y_size=15, title_size=18)
    alpha_descriptive = _boxplot_descriptive_stats(alpha, metric, [comparison_factor]) if view_kind.startswith("Boxplot") else pd.DataFrame()
    alpha_output = alpha_stats.copy()
    if not alpha_descriptive.empty:
      alpha_descriptive.insert(0, "table_type", "descriptive_boxplot_statistics")
      if not alpha_output.empty:
        alpha_output.insert(0, "table_type", "inferential_tests")
      alpha_output = pd.concat([alpha_descriptive, alpha_output], ignore_index=True, sort=False)
    render_plotly_downloadable(
      fig, key=f"alpha_diversity_{level_name}_{metric}_{view_kind}", basename=f"alpha_diversity_{level_name}_{metric}_{view_kind}",
      audit_input_table=alpha.copy(), audit_processed_table=alpha.copy(), audit_output_table=alpha_output,
      audit_method=f"Alpha-diversity {metric} values calculated from the exact study matrix; boxplots use individual biological samples grouped by {comparison_factor if view_kind.startswith('Boxplot') else 'sample'}. Parametric and non-parametric tests are reported for boxplots.",
      audit_input_source="Supplementary Table 1 and packaged CDS taxonomy files.",
      audit_script="app.py:taxonomy_matrix,diversity_from_matrix,_numeric_group_stats,taxonomy_diversity_panel",
    )
    if view_kind.startswith("Boxplot"):
      render_boxplot_statistical_summary(
        alpha_stats,
        f"{metric} — {comparison_factor}",
        category_col="category",
        max_pairs=6,
      )
      st.caption(txt(
        "Método: a diversidade alfa é calculada diretamente da Supplementary Table 1 e dos arquivos CDS reais do estudo. Script: app.py, funções diversity_from_matrix(), _numeric_group_stats(), render_boxplot_statistical_summary() e taxonomy_diversity_panel(). A significância dos testes paramétricos e não paramétricos é mostrada acima e a tabela completa abaixo.",
        "Method: alpha diversity is calculated directly from Supplementary Table 1 and the study's real CDS files. Script: app.py, functions diversity_from_matrix(), _numeric_group_stats(), render_boxplot_statistical_summary() and taxonomy_diversity_panel(). Parametric and non-parametric significance is shown above and the full table below."
      ))
      show_table(alpha_stats, f"alpha_stats_{level_name}_{metric}", height=280)
      csv_button(alpha_stats, f"alpha_diversity_statistics_{level_name}_{metric}.csv".replace(" ", "_").replace("—", "-"), txt("Baixar testes estatísticos", "Download statistical tests"))
    show_plot_source_table(alpha, f"alpha_diversity_{level_name}_{metric}", txt("Tabela usada para o gráfico alfa", "Table used for alpha plot"))
    csv_button(alpha, f"alpha_diversity_{level_name}.csv".replace(" ", "_").replace("—", "-"), txt("Baixar diversidade alfa", "Download alpha diversity"))
  with c2:
    ord_kind = st.radio(txt("Ordenação beta", "Beta ordination"), ["PCoA", "NMDS"], horizontal=True, key=f"beta_kind_{level_name}")
    bc1, bc2, bc3 = st.columns([0.34, 0.34, 0.32])
    with bc1:
      show_biplot = st.checkbox(txt("Mostrar biplot de táxons", "Show taxon biplot"), value=False, key=f"beta_biplot_show_{level_name}_{ord_kind}")
    with bc2:
      biplot_rank = st.selectbox(txt("Nível do biplot", "Biplot rank"), ["Phylum", "Order", "Genus", "Species"], index=0, key=f"beta_biplot_rank_{level_name}_{ord_kind}", disabled=not show_biplot)
    with bc3:
      biplot_n = st.select_slider(txt("Número de táxons (n)", "Number of taxa (n)"), options=list(range(2, 21, 2)), value=6, key=f"beta_biplot_n_{level_name}_{ord_kind}", disabled=not show_biplot)
    ord_df = pcoa_from_matrix(matrix) if ord_kind == "PCoA" else nmds_from_matrix(matrix)
    if ord_df.empty:
      st.info(txt("PCoA/NMDS requer mais unidades e features com variação.", "PCoA/NMDS requires more units and variable features."))
    else:
      if not meta.empty:
        ord_df = ord_df.merge(meta.reset_index(), on="group", how="left")
      x, y = ("PCoA1", "PCoA2") if ord_kind == "PCoA" else ("NMDS1", "NMDS2")
      color_col = "season" if "season" in ord_df.columns else "group"
      symbol_col = "lake" if "lake" in ord_df.columns else None
      fig = px.scatter(ord_df, x=x, y=y, color=color_col, symbol=symbol_col, text="group", hover_data=ord_df.columns, title=f"{ord_kind} — Bray-Curtis ({level_name})")
      fig.update_traces(textposition="top center", marker=dict(size=13, line=dict(width=1)), cliponaxis=False)
      vector_df = pd.DataFrame()
      if show_biplot:
        rank_matrix = cds_taxonomy_group_matrix(biplot_rank, groups=ord_df["group"].astype(str).tolist(), top_n=max(80, int(biplot_n) * 5))
        vector_df = ordination_taxon_vectors(rank_matrix, ord_df, x, y, top_n=int(biplot_n))
        fig = add_taxon_biplot_vectors(fig, vector_df, x, y, ord_df)
      fig.update_layout(
        height=720 if show_biplot else 620,
        margin=dict(l=100, r=180 if show_biplot else 80, t=115, b=175),
        title=dict(text=f"{ord_kind} — Bray-Curtis ({level_name})", x=0.02, y=0.98),
        legend=dict(title_text="", orientation="h", yanchor="top", y=-0.18, xanchor="center", x=0.5),
      )
      bold_axis_layout(fig, x_size=15, y_size=15, title_size=18)
      render_plotly_downloadable(fig, key=f"beta_{ord_kind}_{level_name}_{biplot_rank}_{biplot_n}_{show_biplot}", basename=f"beta_{ord_kind}_{level_name}_{biplot_rank}_n{biplot_n}")
      st.caption(txt(
        f"Método: distância Bray–Curtis. Biplot={'ativado' if show_biplot else 'desativado'}; nível={biplot_rank}; n={biplot_n}. Os vetores são correlações entre abundância dos táxons e os eixos, com conectores e posicionamento repelido para evitar sobreposição. Script: app.py, cds_taxonomy_group_matrix(), ordination_taxon_vectors() e add_taxon_biplot_vectors().",
        f"Method: Bray–Curtis distance. Biplot={'enabled' if show_biplot else 'disabled'}; rank={biplot_rank}; n={biplot_n}. Vectors are correlations between taxon abundance and ordination axes, with connectors and repelled labels to avoid overlap. Script: app.py, cds_taxonomy_group_matrix(), ordination_taxon_vectors() and add_taxon_biplot_vectors()."
      ))
      if not vector_df.empty:
        show_table(vector_df, f"beta_vectors_{ord_kind}_{level_name}_{biplot_rank}", height=300)
        csv_button(vector_df, f"{ord_kind}_{biplot_rank}_n{biplot_n}_taxon_vectors.csv", txt("Baixar vetores do biplot", "Download biplot vectors"))
      show_plot_source_table(ord_df, f"beta_{ord_kind}_{level_name}", txt("Tabela usada para a ordenação beta", "Table used for beta ordination"))
      csv_button(ord_df, f"{ord_kind}_bray_curtis_{level_name}.csv".replace(" ", "_").replace("—", "-"), txt("Baixar ordenação beta", "Download beta ordination"))



def page_header():
  logo_png = ASSETS_DIR / "itv_logo.png"
  logo_svg = ASSETS_DIR / "itv_logo.svg"
  logo = logo_png if logo_png.exists() else logo_svg

  st.markdown(
    f"""
<div class="itv-topbar">
  <span class="pill">Instituto Tecnológico Vale</span>
  <span class="pill">{txt('Genômica ambiental', 'Environmental genomics')}</span>
  <span class="pill">Carajás lateritic lakes</span>
  <span class="pill">{txt('Banco científico aberto', 'Open scientific database')}</span>
  <span class="pill">App version {APP_VERSION}</span>
</div>
""",
    unsafe_allow_html=True,
  )

  left, right = st.columns([0.76, 0.24], vertical_alignment="center")
  with left:
    st.markdown(
      f"""
<div class="hero">
  <div class="itv-kicker">{txt('Ciência aplicada para um futuro sustentável', 'Applied science for a sustainable future')}</div>
  <h1>{APP_TITLE}</h1>
  <p>{txt('Banco interativo do artigo para taxonomia, biomarcadores KO, ciclos biogeoquímicos, metabolismo de ferro, MAGs, abundância diferencial e contexto ambiental das lagoas lateríticas de Carajás.', 'Interactive article database for taxonomy, KO biomarkers, biogeochemical cycles, iron metabolism, MAGs, differential abundance and environmental context of Carajás lateritic lakes.')}</p>
  <div class="authors"><b>{txt('Autores', 'Authors')}:</b> {DEFAULT_ARTICLE_AUTHORS}</div>
  <div class="authors"><b>{txt('Afiliação', 'Affiliation')}:</b> {DEFAULT_ARTICLE_AFFILIATION}</div>
  <div class="authors"><b>{txt('Correspondência', 'Correspondence')}:</b> {DEFAULT_ARTICLE_CORRESPONDENCE}</div>
</div>
""",
      unsafe_allow_html=True,
    )
  with right:
    st.markdown('<div class="brand-card">', unsafe_allow_html=True)
    if logo.exists():
      st.image(str(logo), width="stretch")
    else:
      st.info("Logo não encontrado. Coloque `assets/itv_logo.png` ou `assets/itv_logo.svg`.")
    st.markdown(
      '<div class="brand-caption">Instituto Tecnológico Vale • Belém, PA, Brazil</div></div>',
      unsafe_allow_html=True,
    )
    if is_admin_authenticated():
      visitor_counter_compact()


def overview_tab():
  st.markdown('<div class="section-title">Article Atlas</div>', unsafe_allow_html=True)
  st.markdown(
    f'<div style="display:inline-block;padding:0.42rem 0.8rem;margin:0.15rem 0 0.9rem 0;border-radius:999px;background:#E6F4F1;border:1px solid #0F766E;color:#064E3B;font-weight:800;">App version {APP_VERSION}</div>',
    unsafe_allow_html=True,
  )

  title = article_field("title", DEFAULT_ARTICLE_TITLE)
  authors = normalize_authors_string(article_field("authors", DEFAULT_ARTICLE_AUTHORS))
  affiliation = article_field("affiliation", DEFAULT_ARTICLE_AFFILIATION)
  correspondence = article_field("correspondence", DEFAULT_ARTICLE_CORRESPONDENCE)
  abstract = article_field("abstract", DEFAULT_ARTICLE_ABSTRACT)

  if st.session_state.get("admin_authenticated", False):
    with st.expander(txt("Editar título, autores e resumo exibidos no site", "Edit title, authors and abstract displayed on the site"), expanded=False):
      title = st.text_input(txt("Título do artigo/site", "Article/site title"), value=title, key="article_title")
      authors = st.text_area(txt("Autores", "Authors"), value=authors, height=110, key="article_authors")
      affiliation = st.text_input(txt("Afiliação", "Affiliation"), value=affiliation, key="article_affiliation")
      correspondence = st.text_area(txt("Correspondência", "Correspondence"), value=correspondence, height=80, key="article_correspondence")
      abstract = st.text_area(txt("Resumo do artigo", "Article abstract"), value=abstract, height=300, key="article_abstract")
      st.caption(txt(
        "Estas edições ficam na sessão do Streamlit. Para alterar o padrão público, edite os campos DEFAULT_ARTICLE_* em app.py.",
        "These edits remain in the Streamlit session. To change the public default, edit the DEFAULT_ARTICLE_* fields in app.py."
      ))

  st.markdown(
    f"""
    <div class="itv-card">
      <p style="font-size:1.02rem;color:#1f2937;"><b>{txt("Autores", "Authors")}:</b> {html_lib.escape(str(authors))}</p>
      <p style="font-size:1.0rem;color:#1f2937;"><b>{txt("Afiliação", "Affiliation")}:</b> {html_lib.escape(str(affiliation))}</p>
      <p style="font-size:1.0rem;color:#1f2937;"><b>{txt("Correspondência", "Correspondence")}:</b> {html_lib.escape(str(correspondence))}</p>
      <h3 style="margin-bottom:0.35rem;color:#0f3f3c;">{txt("Resumo", "Abstract")}</h3>
      <p style="font-size:1.0rem;line-height:1.62;color:#27383a;text-align:justify;">{html_lib.escape(str(abstract))}</p>
    </div>
    """,
    unsafe_allow_html=True,
  )

  st.markdown("### " + txt("Workflow do atlas", "Atlas workflow"))
  st.caption(txt(
    "O workflow fica imediatamente abaixo do resumo para orientar a leitura do banco e conectar cada módulo às análises e figuras geradas.",
    "The workflow is shown immediately below the abstract to guide database navigation and connect each module to the analyses and generated figures."
  ))
  workflow_path = BASE_DIR / "outputs" / "app_supplementary_figures" / "SupplementaryFigure29_complete_computational_workflow.png"
  if workflow_path.exists():
    st.image(str(workflow_path), width="stretch", caption=txt("Workflow computacional completo do atlas.", "Complete computational workflow of the atlas."))
  else:
    st.warning(txt("Figura do workflow não encontrada em outputs/app_supplementary_figures/.", "Workflow figure not found in outputs/app_supplementary_figures/."))

  st.markdown("#### " + txt("Logos dos módulos e o que cada módulo faz", "Module logos and what each module does"))
  module_cards = [
    ("🧭", "Article Atlas / Overview", "Resumo do estudo, workflow, rastreabilidade e inventários principais.", "Workflow, cartões do artigo e tabelas de inventário."),
    ("🧬", "Taxonomic profiles", "Perfis taxonômicos das lagoas, diversidade, NMDS, heatmaps e barplots por amostra e lagoa–estação.", "Supplementary Table 1; Figures 2-6; Supplementary Figures 1-4, 14, 19-31, 39 and 43-66."),
    ("🧫", "MAGs and genomes", "Qualidade dos MAGs, taxonomia, anotações, FASTA/GBK e BGCs antiSMASH.", "Supplementary Tables 7, 9 and 11; Figure 7; Supplementary Figures 5, 17-18."),
    ("🧪", "KO Biogeochemical Cycles Biomarkers and differential abundance", "Biomarcadores KO, vias C/N/S/fotossíntese, abundância diferencial e contrastes direcionais.", "Supplementary Tables 4-5 and 8; Figure 8; Supplementary Figures 6-12, 32-36 and 68-69."),
    ("🗺️", "KEGG/KEMET modules", "Completude de módulos KEGG em MAGs e metagenomas com raw values, z-score e tabelas baixáveis.", "Supplementary Tables 3 and 9; Supplementary Figures 38-39; outputs/kegg_modules/*.csv."),
    ("⛓️", "Iron-rich environment comparison", "Comparação entre lagoas amazônicas e ambientes ricos em ferro usando ST8, taxonomia, KOs e metadados IMG/JGI.", "Supplementary Table 8; ST8 heatmaps, metadata tables and comparison figures."),
    ("📚", "Code, methods and references", "Scripts, documentação, métodos, referências e manifestos figura–script.", "Script manifest, documentation index, methods and reference tables."),
  ]
  cards_html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(245px,1fr));gap:0.8rem;margin:0.4rem 0 1rem 0;">'
  for icon, title_card, desc, figs in module_cards:
    cards_html += f'<div style="border:1px solid #D1D5DB;border-radius:18px;padding:0.9rem 1rem;background:#FFFFFF;box-shadow:0 2px 8px rgba(15,63,60,0.06);"><div style="font-size:1.6rem;line-height:1;">{icon}</div><div style="font-weight:800;color:#0f3f3c;margin-top:0.35rem;">{html_lib.escape(title_card)}</div><div style="font-size:0.92rem;color:#334155;margin-top:0.35rem;">{html_lib.escape(desc)}</div><div style="font-size:0.84rem;color:#475569;margin-top:0.5rem;"><b>Figures/data:</b> {html_lib.escape(figs)}</div></div>'
  cards_html += '</div>'
  st.markdown(cards_html, unsafe_allow_html=True)

  workflow_modules = pd.DataFrame([
    {"Module": "Article Atlas / Overview", "Analyses performed": "Study summary, sampling context, citation tracking, core database counts and package traceability.", "Figures and outputs generated": "Article summary card, workflow schematic, citation panels and inventory tables."},
    {"Module": "Taxonomic profiles", "Analyses performed": "Kaiju-derived domain, phylum, family, genus and species profiles; lake/season/omics comparisons; richness, diversity and NMDS visualization.", "Figures and outputs generated": "Figures 2-6; Supplementary Figures 1-4, 14, 19-31, 39 and 43-66."},
    {"Module": "MAGs and genomes", "Analyses performed": "MAG quality, completeness/contamination, GTDB-Tk, BV-BRC, Kaiju/rRNA annotation, FASTA/GBK indexing and antiSMASH BGC parsing.", "Figures and outputs generated": "Figure 7; Supplementary Figures 5, 17-18; antiSMASH/MAG tables."},
    {"Module": "KO Biogeochemical Cycles Biomarkers and differential abundance", "Analyses performed": "Curated KO biomarkers for carbon, methane, nitrogen, sulfur, oxygenic photosynthesis and iron metabolism; dry/rainy differential and directional contrasts.", "Figures and outputs generated": "Figure 8; Supplementary Figures 6-12, 32-36 and 68-69."},
    {"Module": "KEGG/KEMET modules", "Analyses performed": "KEMET report parsing, complete/incomplete/absent KEGG module calls and KO component summaries for MAGs and metagenomes.", "Figures and outputs generated": "Supplementary Figures 38-39; KEGG module heatmaps; raw and z-score matrices; downloadable status/completeness tables; scripts: src/kegg_modules.py, scripts/build_kemet_outputs.py, scripts/refresh_kegg_module_heatmaps.py."},
    {"Module": "Iron-rich environment comparison", "Analyses performed": "Supplementary Table 8 and IMG/M metadata integration, descriptive Amazonia-vs-external log2-ratio contrasts and z-score heatmaps.", "Figures and outputs generated": "Supplementary Figures 33-37; ST8 heatmaps, metadata panels and comparison tables."},
    {"Module": "Code and reproducibility", "Analyses performed": "Script, source-data, environment, figure-generation and package-manifest indexing for reproducible reuse.", "Figures and outputs generated": "Workflow figure, figure-script manifest, methods tables and reproducibility inventory."},
  ])
  st.markdown("#### " + txt("Explicação dos módulos abaixo do workflow", "Module explanations below the workflow"))
  st.caption(txt(
    "A tabela abaixo explicita, para cada módulo do app, quais análises são executadas e quais figuras ou saídas são geradas.",
    "The table below states, for each app module, which analyses are performed and which figures or outputs are generated."
  ))
  show_table(workflow_modules, "workflow_module_explanations", height=420)
  csv_button(workflow_modules, "workflow_module_explanations.csv", txt("Baixar explicação dos módulos", "Download module explanations"))

  st.markdown(
    txt(
      "Este banco online organiza os resultados centrais do artigo: MAGs, anotações genômicas, FASTA/GBK, perfis taxonômicos, biomarcadores KO, metabolismo de ferro/metais, abundância diferencial e comparação com ambientes ricos em ferro do IMG/M.",
      "This online database organizes the core article results: MAGs, genome annotations, FASTA/GBK files, taxonomic profiles, KO biomarkers, iron/metal metabolism, differential abundance and IMG/M iron-rich environment comparisons."
    )
  )

  markers = marker_table()
  meta = taxonomy_samples_metadata()
  iron_meta = iron_rich_environment_metadata()
  salazar_unique = int(
    markers.loc[
      markers["Study"].astype(str).str.contains("Salazar", case=False, na=False),
      "KO",
    ].astype(str).str.extract(r"(K\d{5})", expand=False).dropna().nunique()
  ) if (not markers.empty and {"Study", "KO"}.issubset(markers.columns)) else 0
  iron_unique = int(
    markers.loc[
      markers["Study"].astype(str).str.contains("New marker", case=False, na=False),
      "KO",
    ].astype(str).str.extract(r"(K\d{5})", expand=False).dropna().nunique()
  ) if (not markers.empty and {"Study", "KO"}.issubset(markers.columns)) else 0

  m1, m2, m3, m4, m5, m6 = st.columns(6)
  m1.metric(txt("Amostras do artigo", "Article samples"), meta["sample.id"].nunique() if "sample.id" in meta.columns else len(meta))
  m2.metric(txt("KOs únicos", "Unique KOs"), markers["KO"].astype(str).str.extract(r"(K\d{5})", expand=False).nunique() if not markers.empty and "KO" in markers.columns else 0)
  m3.metric(txt("KOs derivados de Salazar", "Salazar-derived KOs"), salazar_unique)
  m4.metric(txt("KOs associados ao ferro", "Iron-associated KOs"), iron_unique)
  m5.metric(txt("Ambientes IMG/M", "IMG/M environments"), iron_meta["sample_id"].nunique() if not iron_meta.empty and "sample_id" in iron_meta.columns else len(iron_meta))
  m6.metric(txt("MAGs", "MAGs"), len(load_sheet("table7", "bins-identificados")))

  c1, c2 = st.columns([0.52, 0.48])
  with c1:
    st.markdown("#### " + txt("Atualização dos biomarcadores e rastreabilidade", "Biomarker update and traceability"))
    st.markdown(txt(
      f"**Salazar et al. (2019)** forneceram a estrutura de referência para genes marcadores de ciclos biogeoquímicos usada neste atlas. O conjunto empacotado contém **{salazar_unique} KOs biogeoquímicos únicos derivados dessa referência**. A publicação atual **atualiza e amplia** esse quadro, consolidando um painel de **195 biomarcadores biogeoquímicos**, dos quais **171 foram detectados** nas amostras do estudo, e acrescentando um painel dedicado de **132 biomarcadores associados ao ferro**. Na versão empacotada do atlas, **{iron_unique} KOs únicos** estão representados explicitamente na matriz focada em ferro/metais. Dessa forma, o estudo não apenas reutiliza a referência de Salazar: ele a expande para sedimentos tropicais ferruginosos e mantém a proveniência de cada marcador.",
      f"**Salazar et al. (2019)** provided the reference framework for biogeochemical-cycle marker genes used in this atlas. The packaged dataset contains **{salazar_unique} unique biogeochemical KOs derived from that reference**. The present publication **updates and expands** the framework by consolidating a panel of **195 biogeochemical biomarkers**, of which **171 were detected** in the study samples, and by adding a dedicated panel of **132 iron-associated biomarkers**. In the packaged atlas release, **{iron_unique} unique KOs** are represented explicitly in the iron/metals-focused matrix. The study therefore does not merely reuse the Salazar reference; it extends it to tropical ferruginous sediments while preserving marker-level provenance."
    ))
    st.caption(txt(
      f"Referências rastreadas: {SALAZAR_CITATION} Publicação atual: {ARTICLE_CITATION}",
      f"Traced references: {SALAZAR_CITATION} Current publication: {ARTICLE_CITATION}"
    ))
    st.markdown(txt(
      "**IMG/M source:** os metadados dos ambientes ricos em ferro vêm da aba `Iron-rich-environment` da Supplementary Table 8, derivada do portal Integrated Microbial Genomes with Microbiome Samples mantido pelo JGI.",
      "**IMG/M source:** metadata for iron-rich environments come from the `Iron-rich-environment` sheet in Supplementary Table 8, derived from the Integrated Microbial Genomes with Microbiome Samples portal maintained by JGI."
    ))
    if available_gbk_count() == 0:
      st.warning(txt(
        "Os FASTA foram incluídos, mas nenhum GBK/GBFF foi encontrado.",
        "FASTA files are included, but no GBK/GBFF files were found."
      ))
  with c2:
    st.markdown("#### " + txt("Amostras, sazonalidade e novidade do estudo", "Study samples, seasonality and novelty"))
    total_samples = int(meta["sample.id"].nunique()) if "sample.id" in meta.columns else len(meta)
    n_lakes = int(meta["lake"].dropna().astype(str).nunique()) if "lake" in meta.columns else 0
    n_dry = int((meta["season"].astype(str).str.lower() == "dry").sum()) if "season" in meta.columns else 0
    n_rainy = int((meta["season"].astype(str).str.lower() == "rainy").sum()) if "season" in meta.columns else 0
    lake_names = ", ".join(sorted(meta["lake"].dropna().astype(str).unique())) if "lake" in meta.columns else ""
    st.markdown(txt(
      f"O estudo inclui **{total_samples} amostras de sedimento** provenientes de **{n_lakes} lagoas lateríticas amazônicas** — **{lake_names}** — com coletas nos períodos **seco e chuvoso**. A novidade do atlas é integrar, para essas mesmas amostras, metadados de coleta e estação, perfis taxonômicos, biomarcadores KO dos ciclos biogeoquímicos, biomarcadores associados ao ferro, módulos KEGG/KEMET, MAGs e comparações com outros ambientes ricos em ferro. A tabela detalhada abaixo mantém explicitamente a **estação do ano de cada amostra**.",
      f"The study includes **{total_samples} sediment samples** from **{n_lakes} Amazonian lateritic lakes** — **{lake_names}** — collected during **dry and rainy seasons**. The novelty of the atlas is the integration, for these same samples, of collection and seasonal metadata, taxonomic profiles, biogeochemical-cycle KO biomarkers, iron-associated biomarkers, KEGG/KEMET modules, MAGs and comparisons with other iron-rich environments. The detailed table below explicitly retains the **season assigned to every sample**."
    ))
    if not meta.empty and {"sample.id", "lake", "season"}.issubset(meta.columns):
      sample_summary = (
        meta[["sample.id", "lake", "season"]]
        .drop_duplicates()
        .assign(
          dry=lambda frame: (frame["season"].astype(str).str.lower() == "dry").astype(int),
          rainy=lambda frame: (frame["season"].astype(str).str.lower() == "rainy").astype(int),
        )
        .groupby("lake", as_index=False)
        .agg(samples=("sample.id", "nunique"), dry_samples=("dry", "sum"), rainy_samples=("rainy", "sum"))
      )
      show_table(sample_summary, "metadata_lake_season_summary", height=190)
    st.caption(txt(
      f"Distribuição sazonal: **{n_dry} amostras do período seco** e **{n_rainy} amostras do período chuvoso**.",
      f"Seasonal distribution: **{n_dry} dry-season samples** and **{n_rainy} rainy-season samples**."
    ))
    cols = [c for c in ["sample.id", "collection_date", "lake", "season", "lat", "lon", "environment_feature"] if c in meta.columns]
    show_table(meta[cols], "metadata_preview", height=320)
    csv_button(meta, "article_sample_dates_coordinates.csv", txt("Baixar datas/coordenadas", "Download dates/coordinates"))

  if st.session_state.get("admin_authenticated", False):
    with st.expander(txt("Technical spreadsheet inventory — admin only", "Technical spreadsheet inventory — admin only"), expanded=False):
      st.caption(txt(
        "As planilhas suplementares ficam ocultas para usuários públicos. O admin pode habilitar a visualização técnica para auditoria.",
        "Supplementary spreadsheets remain hidden to public users. The admin can enable technical viewing for audit."
      ))
      inv = sheet_inventory()
      show_table(inv, "inventory", height=360)
      csv_button(inv, "database_sheet_inventory.csv", txt("Baixar inventário técnico", "Download technical inventory"))

      show_raw = st.checkbox(txt("Habilitar visualização técnica das planilhas suplementares", "Enable technical supplementary-spreadsheet viewer"), value=False, key="show_raw_supplementary_admin")
      if show_raw:
        table_labels = []
        for key, name in TABLE_FILES.items():
          clean_table_name = re.sub(r"\s*\(\d+\)(?=\.[A-Za-z0-9]+$)", "", str(name))
          table_labels.append(f"{key}: {clean_table_name}")
        selected_table_label = st.selectbox("Supplementary table", table_labels, key="admin_raw_table")
        selected_table_key = selected_table_label.split(":", 1)[0]
        sheets = excel_sheet_names(selected_table_key)
        selected_sheet = st.selectbox("Sheet", sheets, key="admin_raw_sheet")
        raw_df = load_sheet(selected_table_key, selected_sheet)
        st.caption(f"{selected_table_label} / {selected_sheet} — {raw_df.shape[0]:,} rows × {raw_df.shape[1]:,} columns")
        show_table(raw_df, f"admin_raw_{selected_table_key}_{selected_sheet}", height=520)
        csv_button(raw_df, f"{selected_table_key}_{selected_sheet}.csv".replace("/", "_"), txt("Baixar aba selecionada", "Download selected sheet"))



def taxonomy_tab_legacy_redundant_removed():
  st.subheader(txt("Perfis taxonômicos da Supplementary Table 1", "Taxonomic profiles from Supplementary Table 1"))
  st.markdown(txt(
    "Os heatmaps e barplots abaixo usam as tabelas taxonômicas exatas do estudo. Por padrão, o heatmap mostra as **20 amostras individuais** e **todos os táxons** do nível escolhido; o filtro Top N é opcional. Os barplots podem alternar entre amostras individuais e grupos agregados lagoa–estação. No heatmap agregado, as réplicas são somadas dentro de cada lagoa/estação; o barplot continua em porcentagem. Cada perfil percentual é renormalizado dentro de sua própria amostra/grupo, portanto a soma nunca ultrapassa 100%.",
    "The heatmaps and barplots below use the study's exact taxonomic tables. By default, the heatmap shows the **20 individual samples** and **all taxa** at the selected rank; the Top-N filter is optional. Barplots can switch between individual samples and aggregated lake–season groups. In the aggregated heatmap, replicate counts are summed within each lake/season; the barplot remains percentage-based. Each percentage profile is renormalized within its own sample/group, so totals never exceed 100%."
  ))
  meta = taxonomy_samples_metadata()
  with st.expander(txt("Amostras, datas, coordenadas e environment_feature", "Samples, dates, coordinates and environment_feature"), expanded=True):
    cols = [c for c in ["sample.id", "Sample", "collection.date", "collection_date", "latitude", "longitude", "lat", "lon", "environment_feature", "lake", "season", "depth"] if c in meta.columns]
    show_table(meta[cols], "taxonomy_metadata", height=340)
    if {"lat", "lon"}.issubset(meta.columns):
      show_high_quality_sample_map(meta, key="taxonomy_article_sample_map")

  level = st.selectbox(txt("Nível taxonômico", "Taxonomic level"), list(TAXONOMY_LEVELS.keys()), index=2, key="taxonomy_legacy_removed_level")
  hmode = st.radio(
    txt("Unidades no heatmap", "Heatmap units"),
    ["Individual samples", "Aggregated lake-season groups"],
    index=0, horizontal=True, key=f"taxonomy_heatmap_mode_{level}",
    format_func=lambda x: txt("Todas as amostras individuais", "All individual samples") if x.startswith("Individual") else txt("Grupos agregados lagoa–estação (soma de contagens)", "Aggregated lake–season groups (summed counts)"),
  )
  heat_df = taxonomy_profile_table(level, view_mode=hmode)
  if heat_df.empty:
    st.info(txt("A seleção atual não possui linhas após os filtros. O app vai usar a tabela completa da Supplementary Table 1 para manter a visualização ativa.", "The current selection has no rows after filtering. The app will use the complete Supplementary Table 1 data to keep the visualization active."))
    heat_df = taxonomy_profile_table(level, view_mode="Individual samples")
    if heat_df.empty:
      st.info(txt("A tabela taxonômica completa será exibida abaixo para auditoria e download.", "The complete taxonomic table is displayed below for audit and download."))
      fallback = load_sheet("table1", TAXONOMY_LEVELS[level]["sheet"])
      show_table(fallback, f"taxonomy_fallback_{level}", height=520)
      csv_button(fallback, f"taxonomy_fallback_{safe_filename(level)}.csv", txt("Baixar tabela taxonômica", "Download taxonomic table"))
      return
  groups = heat_df["group"].dropna().astype(str).drop_duplicates().tolist()
  c1, c2, c3 = st.columns([0.42, 0.28, 0.30])
  with c1:
    selected_groups = st.multiselect(txt("Amostras / environment_feature", "Samples / environment_feature"), groups, default=groups, key=f"taxonomy_groups_{level}_{hmode}")
  with c2:
    total_taxa = int(heat_df["taxon"].nunique())
    show_all_taxa = st.checkbox(txt(f"Mostrar todos os {total_taxa} táxons", f"Show all {total_taxa} taxa"), value=True, key=f"taxonomy_all_taxa_{level}_{hmode}")
    top_n = None if show_all_taxa else int(st.number_input(txt("Top táxons", "Top taxa"), min_value=1, max_value=max(total_taxa, 1), value=min(50, max(total_taxa, 1)), step=1, key=f"taxonomy_topn_{level}_{hmode}"))
  with c3:
    zscore = st.checkbox(txt("Z-score por táxon no heatmap", "Row z-score in heatmap"), value=False, key=f"taxonomy_z_{level}_{hmode}")

  st.markdown("#### Heatmap")
  fig_h = taxonomy_heatmap(level, top_n=top_n, groups=selected_groups, zscore_rows=zscore, view_mode=hmode)
  if fig_h:
    render_plotly_downloadable(fig_h, key=f"taxonomy_heatmap_{level}_{hmode}_{top_n}_{zscore}", basename=f"taxonomy_heatmap_{level}_{hmode}_{top_n}_{zscore}")
  st.caption(txt(
    "Escala: amostras individuais usam abundância relativa (0–100%); grupos agregados usam a soma exata das contagens das réplicas por lagoa/estação. Quando o z-score é ativado, a cor representa o desvio dentro de cada táxon e o valor bruto permanece no hover.",
    "Scale: individual samples use relative abundance (0–100%); aggregated groups use exact summed replicate counts by lake/season. When z-score is enabled, colour represents within-taxon deviation and the raw value remains in hover text."
  ))

  st.markdown("#### " + txt("Gráfico de barras empilhadas", "Stacked bar profile"))
  bmode = st.radio(
    txt("Unidades no barplot", "Barplot units"),
    ["Individual samples", "Aggregated lake-season groups"],
    index=1, horizontal=True, key=f"taxonomy_bar_mode_{level}",
    format_func=lambda x: txt("Todas as amostras individuais", "All individual samples") if x.startswith("Individual") else txt("Grupos agregados lagoa–estação (soma de contagens)", "Aggregated lake–season groups (summed counts)"),
  )
  bar_df = taxonomy_profile_table(level, view_mode=bmode)
  bar_groups = bar_df["group"].dropna().astype(str).drop_duplicates().tolist()
  bc1, bc2 = st.columns([0.62, 0.38])
  with bc1:
    selected_bar_groups = st.multiselect(txt("Amostras/grupos do barplot", "Barplot samples/groups"), bar_groups, default=bar_groups, key=f"taxonomy_bar_groups_{level}_{bmode}")
  with bc2:
    bar_total_taxa = int(bar_df["taxon"].nunique())
    bar_all = st.checkbox(txt(f"Mostrar todos os {bar_total_taxa} táxons no barplot", f"Show all {bar_total_taxa} taxa in barplot"), value=False, key=f"taxonomy_bar_all_{level}_{bmode}")
    bar_top_n = None if bar_all else int(st.number_input(txt("Top táxons no barplot", "Top taxa in barplot"), min_value=1, max_value=max(bar_total_taxa, 1), value=min(20, max(bar_total_taxa, 1)), step=1, key=f"taxonomy_bar_topn_{level}_{bmode}"))
  bar_factor = st.radio(
    txt("Fator exibido no barplot", "Factor displayed in the barplot"),
    ["lake", "season"], horizontal=True, key=f"taxonomy_bar_display_factor_{level}_{bmode}",
    format_func=lambda x: txt("Lagoa", "Lake") if x == "lake" else txt("Estação", "Season"),
    help=txt("Apenas um gráfico é exibido por vez. A seleção altera tanto as barras quanto o teste estatístico.", "Only one chart is displayed at a time. The selection changes both the bars and the statistical test."),
  )
  fig_b = taxonomy_stacked_bar(level, top_n=bar_top_n, groups=selected_bar_groups, view_mode=bmode, display_factor=bar_factor)
  if fig_b:
    render_plotly_downloadable(fig_b, key=f"taxonomy_stacked_bar_{level}_{bmode}_{bar_top_n}_{bar_factor}", basename=f"taxonomy_stacked_bar_{level}_{bmode}_{bar_top_n}_{bar_factor}")
  tax_stats, tested_taxa, displayed_taxa = taxonomy_barplot_statistics(
    level, selected_groups=selected_bar_groups, view_mode=bmode,
    top_n=bar_top_n, grouping_factor=bar_factor,
  )
  tax_stat_summary = compact_significance_summary(tax_stats, max_items=8)
  st.info(txt(
    f"Teste do barplot: ANOVA de uma via e Kruskal–Wallis globais; Welch t-test e Mann–Whitney U pareados; FDR de Benjamini–Hochberg. Táxons testados: {tested_taxa}/{displayed_taxa}. Resultado: {tax_stat_summary}",
    f"Barplot tests: global one-way ANOVA and Kruskal–Wallis; pairwise Welch t-test and Mann–Whitney U; Benjamini–Hochberg FDR. Taxa tested: {tested_taxa}/{displayed_taxa}. Result: {tax_stat_summary}"
  ))
  if not tax_stats.empty:
    show_table(tax_stats, f"taxonomy_barplot_statistics_{level}_{bmode}_{bar_factor}", height=360)
    csv_button(tax_stats, f"taxonomy_barplot_statistics_{safe_filename(level)}_{bmode}_{bar_factor}.csv", txt("Baixar testes estatísticos do barplot", "Download barplot statistical tests"))
  st.caption(txt(
    "Método do barplot taxonômico: abundâncias relativas reais derivadas da Supplementary Table 1 / CDS do estudo, sem simulação. Script: app.py, taxonomy_stacked_bar(), taxonomy_profile_table() e taxonomy_barplot_statistics(). Os testes paramétricos e não paramétricos aparecem acima desta tabela.",
    "Taxonomic barplot method: real relative abundances derived from Supplementary Table 1 / the study CDS files, with no simulation. Script: app.py, taxonomy_stacked_bar(), taxonomy_profile_table() and taxonomy_barplot_statistics(). Parametric and non-parametric tests are reported above this table."
  ))

  # Diversity/ordination remains based on the aggregated Supplementary Table 1
  # representation so its grouping factor is explicit and reproducible.
  agg_df = taxonomy_profile_table(level, view_mode="aggregated")
  agg_groups = agg_df["group"].dropna().astype(str).drop_duplicates().tolist()
  taxonomy_diversity_panel(level, groups=agg_groups, top_n=60)
  st.divider()
  taxonomic_rda_panel()

  st.markdown("#### " + txt("Tabela exata usada na visualização", "Exact table used in the visualization"))
  table = heat_df[heat_df["group"].isin(selected_groups)].copy() if selected_groups else heat_df.copy()
  q = st.text_input(txt("Buscar táxon", "Search taxon"), "")
  table = filter_by_text(table, ["taxon", "group", "environment_feature", "lake", "season"], q)
  sums = table.groupby("group", as_index=False)["abundance"].sum().rename(columns={"abundance": "displayed_percentage_sum"})
  if not sums.empty and float(sums["displayed_percentage_sum"].max()) > 100.000001:
    st.error(txt("Erro de normalização detectado: uma amostra ultrapassou 100%.", "Normalization error detected: a sample exceeded 100%."))
  show_table(table, f"taxonomy_{level}_{hmode}", height=520)
  csv_button(table, f"taxonomy_{level}_{hmode}.csv".replace(" ", "_").replace("—", "-"), txt("Baixar tabela taxonômica", "Download taxonomic table"))


def _article_lake_sample_columns(cols) -> list[str]:
  return [str(c).strip() for c in cols if re.match(r"^(AM|TIA|TI|VI)\.P\d+\.(D|R)$", str(c).strip())]


def _lake_code_from_sample(sample: str) -> str:
  s = str(sample).strip()
  if s.startswith("AM."):
    return "AM"
  if s.startswith("TIA."):
    return "TIA"
  if s.startswith("TI."):
    return "TI"
  if s.startswith("VI."):
    return "VI"
  return "Other"


def _resolve_rda_taxonomy_level(level_name: str) -> str:
  """Map short RDA labels to the exact Supplementary Table 1 taxonomy table names."""
  mapping = {
    "Phylum": "Phylum — Bacteria",
    "Order": "Order",
    "Genus": "Genus — Bacteria",
    "Species": "Species — Bacteria",
  }
  return mapping.get(str(level_name).strip(), str(level_name).strip())


def _amazon_lake_group_order(values: list[str]) -> list[str]:
  order = ["AM-D", "AM-R", "TI-D", "TI-R", "TIA-D", "TIA-R", "VI-D", "VI-R"]
  wanted = [v for v in order if v in values]
  rest = [v for v in values if v not in wanted]
  return wanted + sorted(rest)


def taxonomic_rda_panel():
  """Interactive views produced from the exact article ordination functions."""
  st.markdown("### " + txt("Ordenações canônicas do artigo", "Canonical article ordinations"))
  st.caption(txt(
    "O aplicativo e o gerador do artigo chamam o mesmo módulo científico (`src/publication_ordination.py`). NMDS, RDA, transformações, parâmetros, permutações, seleção de gêneros e estatísticas não possuem uma implementação alternativa na interface.",
    "The application and article generator call the same scientific module (`src/publication_ordination.py`). NMDS, RDA, transformations, parameters, permutations, genus selection and statistics have no alternative implementation in the interface."
  ))
  domain = st.selectbox(txt("Domínio", "Domain"), ["Bacteria", "Archaea"], key="canonical_ordination_domain")
  show_taxa = st.checkbox(txt("Mostrar vetores dos gêneros representativos", "Show representative-genus vectors"), value=True, key="canonical_ordination_taxa")
  try:
    rda_bundle = publication_rda_data(BASE_DIR, domain)
    nmds_bundle = publication_nmds_data(BASE_DIR, domain)
    tab_rda, tab_nmds = st.tabs(["RDA", "NMDS"])
    with tab_rda:
      fig, sites, env, taxa = publication_rda_figure(BASE_DIR, domain, show_taxa)
      render_plotly_downloadable(fig, key=f"canonical_rda_{domain}", basename=f"canonical_{domain}_RDA")
      model_stats = rda_bundle["model_statistics"]
      st.caption(txt(
        "Método: mesma implementação científica usada no artigo (src/publication_ordination.py e src/publication_rda.py). Dados de entrada: abundâncias relativas reais dos gêneros bacterianos/arqueanos e variáveis ambientais reais do estudo. Abaixo são reportados R², R² ajustado, pseudo-F, P global, P por eixo e VIF; nenhum valor é simulado.",
        "Method: same scientific implementation used in the article (src/publication_ordination.py and src/publication_rda.py). Input data: real relative abundances of bacterial/archaeal genera and real environmental variables from the study. R², adjusted R², pseudo-F, global P, axis-level P and VIF are reported below; no value is simulated."
      ))
      table_tabs = st.tabs([
        txt("Escores das posições", "Site scores"),
        txt("Vetores ambientais", "Environmental vectors"),
        txt("Vetores dos gêneros", "Genus vectors"),
        txt("Estatísticas do modelo", "Model statistics"),
        "VIF",
      ])
      with table_tabs[0]:
        show_table(sites, f"canonical_rda_sites_{domain}", height=330)
        csv_button(sites, f"{domain}_canonical_RDA_site_scores.csv", txt("Baixar escores RDA", "Download RDA scores"))
      with table_tabs[1]:
        show_table(env, f"canonical_rda_env_{domain}", height=300)
        csv_button(env, f"{domain}_canonical_RDA_environment_vectors.csv", txt("Baixar vetores ambientais", "Download environmental vectors"))
      with table_tabs[2]:
        show_table(taxa, f"canonical_rda_taxa_{domain}", height=300)
        csv_button(taxa, f"{domain}_canonical_RDA_representative_genus_vectors.csv", txt("Baixar vetores dos gêneros", "Download genus vectors"))
      with table_tabs[3]:
        show_table(model_stats, f"canonical_rda_model_stats_{domain}", height=260)
        csv_button(model_stats, f"{domain}_canonical_RDA_model_statistics.csv", txt("Baixar estatísticas da RDA", "Download RDA statistics"))
      with table_tabs[4]:
        show_table(rda_bundle["vif"], f"canonical_rda_vif_{domain}", height=260)
        csv_button(rda_bundle["vif"], f"{domain}_canonical_RDA_VIF.csv", txt("Baixar VIF", "Download VIF"))
    with tab_nmds:
      nfig, nscores = publication_nmds_figure(BASE_DIR, domain)
      render_plotly_downloadable(nfig, key=f"canonical_nmds_{domain}", basename=f"canonical_{domain}_NMDS")
      st.caption(txt(
        "As 20 amostras são calculadas com proporções relativas transformadas pela raiz quadrada, Bray–Curtis, NMDS não métrico bidimensional, 20 inicializações, máximo de 1.000 iterações e semente 42. O Stress-1 normalizado aparece no título.",
        "All 20 samples are calculated from square-root-transformed relative proportions, Bray–Curtis, two-dimensional non-metric MDS, 20 starts, a 1,000-iteration maximum and seed 42. Normalized Stress-1 is shown in the title."
      ))
      n_tabs = st.tabs([
        txt("Escores", "Scores"), txt("Parâmetros", "Parameters"),
        txt("PERMANOVA e dispersão", "PERMANOVA and dispersion"), txt("Auditoria das amostras", "Sample audit"),
      ])
      with n_tabs[0]:
        show_table(nscores, f"canonical_nmds_scores_{domain}", height=420)
        csv_button(nscores, f"{domain}_canonical_NMDS_scores.csv", txt("Baixar escores NMDS", "Download NMDS scores"))
      with n_tabs[1]:
        show_table(nmds_bundle["parameters"], f"canonical_nmds_parameters_{domain}", height=220)
        csv_button(nmds_bundle["parameters"], f"{domain}_canonical_NMDS_parameters.csv", txt("Baixar parâmetros NMDS", "Download NMDS parameters"))
      with n_tabs[2]:
        show_table(nmds_bundle["statistics"], f"canonical_nmds_statistics_{domain}", height=300)
        csv_button(nmds_bundle["statistics"], f"{domain}_canonical_NMDS_PERMANOVA_dispersion.csv", txt("Baixar testes NMDS", "Download NMDS tests"))
      with n_tabs[3]:
        show_table(nmds_bundle["sample_audit"], f"canonical_nmds_audit_{domain}", height=360)
  except Exception as exc:
    LOGGER.exception("Canonical ordination panel failed: %s", exc)
    st.exception(exc)

def _season_from_sample(sample: str) -> str:
  s = str(sample).strip()
  return "Dry" if s.endswith(".D") else "Rainy" if s.endswith(".R") else "Unknown"


def _long_marker_counts_for_boxplot(df: pd.DataFrame, id_cols: list[str], category_col: str, normalize_per_sample: bool = True) -> pd.DataFrame:
  """Return one independent observation per biological sample × category.

  Missing values remain missing throughout conversion, normalisation and
  aggregation. Marker rows are aggregated with ``min_count=1`` so an
  all-missing sample/category unit is never converted to zero.
  """
  work = df.copy()
  work.columns = [str(c).strip() for c in work.columns]
  id_cols = [c for c in id_cols if c in work.columns]
  if category_col not in work.columns:
    return pd.DataFrame()
  cols = _article_lake_sample_columns(work.columns)
  if not cols:
    return pd.DataFrame()
  for c in cols:
    numeric = pd.to_numeric(work[c], errors="coerce")
    work[c] = numeric.where(numeric.isna(), numeric.clip(lower=0))
  if normalize_per_sample:
    totals = work[cols].sum(axis=0, min_count=1).replace(0, np.nan)
    work[cols] = work[cols].divide(totals, axis=1) * 10000.0
  work[category_col] = work[category_col].fillna("Unclassified").astype(str).str.strip()
  invalid_categories = {"", "undefined", "nan", "none", "null", "na", "n/a"}
  work.loc[work[category_col].str.casefold().isin(invalid_categories), category_col] = "Unclassified"
  raw = work[id_cols + cols].melt(
    id_vars=id_cols, value_vars=cols, var_name="sample", value_name="marker_normalized_count"
  )
  raw["marker_normalized_count"] = pd.to_numeric(raw["marker_normalized_count"], errors="coerce")
  marker_id_candidates = [c for c in id_cols if c != category_col]
  marker_id = marker_id_candidates[0] if marker_id_candidates else None
  rows: list[dict] = []
  for (category, sample), group in raw.groupby([category_col, "sample"], sort=False, dropna=False):
    values = pd.to_numeric(group["marker_normalized_count"], errors="coerce")
    observed = values.notna()
    record = {
      category_col: category,
      "sample": sample,
      "normalized_count": float(values.sum(min_count=1)) if observed.any() else np.nan,
      "marker_rows_total": int(len(group)),
      "marker_rows_nonmissing": int(observed.sum()),
      "missing_marker_rows": int((~observed).sum()),
    }
    if marker_id:
      record["distinct_markers"] = int(group.loc[observed, marker_id].astype(str).nunique())
    else:
      record["distinct_markers"] = int(observed.sum())
    rows.append(record)
  long = pd.DataFrame(rows)
  if long.empty:
    return long
  long["log1p_normalized_count"] = np.log1p(long["normalized_count"])
  long["lake"] = long["sample"].map(_lake_code_from_sample)
  long["season"] = long["sample"].map(_season_from_sample)
  long["observation_present"] = long["normalized_count"].notna()
  long["observation_unit"] = "one biological sample per category after within-sample marker aggregation"
  duplicate_units = long.duplicated([category_col, "sample"], keep=False)
  if duplicate_units.any():
    raise RuntimeError("Duplicate sample × category units remain after marker aggregation")
  return long


def _boxplot_descriptive_stats(
  frame: pd.DataFrame,
  value_col: str,
  group_cols: list[str],
) -> pd.DataFrame:
  """Calculate the exact quartiles, Tukey whiskers and outliers used by boxplots."""
  if frame is None or frame.empty or value_col not in frame.columns:
    return pd.DataFrame()
  rows: list[dict] = []
  for key, group in frame.groupby(group_cols, sort=False, dropna=False):
    keys = key if isinstance(key, tuple) else (key,)
    values_all = pd.to_numeric(group[value_col], errors="coerce")
    values = values_all.dropna().to_numpy(float)
    record = {col: val for col, val in zip(group_cols, keys)}
    record.update({
      "value_column": value_col,
      "n_total_rows": int(len(values_all)),
      "n_observations": int(len(values)),
      "n_missing": int(values_all.isna().sum()),
    })
    if len(values) == 0:
      record.update({name: np.nan for name in (
        "minimum", "q1", "median", "q3", "maximum", "iqr",
        "lower_fence", "upper_fence", "lower_whisker", "upper_whisker",
      )})
      record["outlier_count"] = 0
      record["outliers"] = ""
      record["display_recommendation"] = "no observed values"
    else:
      q1, median, q3 = np.quantile(values, [0.25, 0.5, 0.75], method="linear")
      iqr = q3 - q1
      lower_fence = q1 - 1.5 * iqr
      upper_fence = q3 + 1.5 * iqr
      inside = values[(values >= lower_fence) & (values <= upper_fence)]
      outliers = values[(values < lower_fence) | (values > upper_fence)]
      record.update({
        "minimum": float(np.min(values)), "q1": float(q1), "median": float(median),
        "q3": float(q3), "maximum": float(np.max(values)), "iqr": float(iqr),
        "lower_fence": float(lower_fence), "upper_fence": float(upper_fence),
        "lower_whisker": float(np.min(inside)) if len(inside) else np.nan,
        "upper_whisker": float(np.max(inside)) if len(inside) else np.nan,
        "outlier_count": int(len(outliers)),
        "outliers": "; ".join(f"{value:.12g}" for value in sorted(outliers.tolist())),
        "display_recommendation": "points only / interpret cautiously" if len(values) < 4 else "boxplot with individual points",
      })
    rows.append(record)
  return pd.DataFrame(rows)


def _numeric_group_stats(df: pd.DataFrame, value_col: str, group_col: str, category: str = "All") -> pd.DataFrame:
  """Parametric/non-parametric global and pairwise tests for one boxplot."""
  if df is None or df.empty or value_col not in df.columns or group_col not in df.columns:
    return pd.DataFrame()
  work = df[[group_col, value_col]].copy()
  work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
  work[group_col] = work[group_col].astype(str)
  work = work.dropna(subset=[value_col])
  groups = [g for g in sorted(work[group_col].unique()) if len(work.loc[work[group_col].eq(g), value_col]) > 0]
  values = [work.loc[work[group_col].eq(g), value_col].to_numpy(float) for g in groups]
  if len(groups) < 2:
    return pd.DataFrame([{
      "category": category, "grouping_factor": group_col, "value": value_col,
      "status": "insufficient_groups", "n_groups": len(groups),
    }])
  try:
    anova_p = float(stats.f_oneway(*values).pvalue)
  except Exception:
    anova_p = np.nan
  try:
    kruskal_p = float(stats.kruskal(*values).pvalue)
  except Exception:
    kruskal_p = np.nan
  rows = []
  for i in range(len(groups)):
    for j in range(i + 1, len(groups)):
      a, b = groups[i], groups[j]
      va, vb = values[i], values[j]
      try:
        t_p = float(stats.ttest_ind(va, vb, equal_var=False, nan_policy="omit").pvalue)
      except Exception:
        t_p = np.nan
      try:
        mw_p = float(stats.mannwhitneyu(va, vb, alternative="two-sided").pvalue)
      except Exception:
        mw_p = np.nan
      rows.append({
        "category": category, "grouping_factor": group_col, "value": value_col,
        "global_parametric_test": "one-way ANOVA", "anova_pvalue": anova_p,
        "global_nonparametric_test": "Kruskal-Wallis", "kruskal_pvalue": kruskal_p,
        "pairwise_parametric_test": "Welch t-test", "pairwise_nonparametric_test": "Mann-Whitney U",
        "group1": a, "group2": b, "n_group1": len(va), "n_group2": len(vb),
        "t_test_pvalue": t_p, "mannwhitney_pvalue": mw_p,
      })
  out = pd.DataFrame(rows)
  valid = out["mannwhitney_pvalue"].notna()
  out["qvalue"] = np.nan
  if valid.any():
    pvals = out.loc[valid, "mannwhitney_pvalue"].to_numpy(float)
    order = np.argsort(pvals)
    ranked = pvals[order]
    m = len(ranked)
    bh = np.minimum.accumulate((ranked * m / np.arange(1, m + 1))[::-1])[::-1]
    restored = np.empty_like(bh)
    restored[order] = np.clip(bh, 0, 1)
    out.loc[valid, "qvalue"] = restored
  out["significant_q_lt_0_05"] = out["qvalue"].lt(0.05).fillna(False)
  out["multiple_testing"] = "Benjamini-Hochberg FDR on pairwise Mann-Whitney U p-values"
  return out




def render_boxplot_statistical_summary(
  stats_df: pd.DataFrame,
  context_label: str,
  *,
  category_col: str = "category",
  group1_col: str = "group1",
  group2_col: str = "group2",
  q_col: str = "qvalue",
  max_pairs: int = 6,
) -> None:
  """Render a compact statistical interpretation strictly below a boxplot.

  The summary reports the global tests used and aggregates FDR-significant
  pairwise results by group pair. It is deliberately rendered after the Plotly
  component, so it cannot overlap the graph title, legend, axes or data.
  """
  if stats_df is None or stats_df.empty:
    st.markdown(txt(
      f"**Resumo dos resultados — {context_label}:** não houve comparações válidas suficientes para inferência estatística.",
      f"**Results summary — {context_label}:** there were not enough valid comparisons for statistical inference.",
    ))
    st.caption(txt(
      "Testes previstos: ANOVA de uma via e Kruskal–Wallis globais; Welch t-test e Mann–Whitney U pareados; correção FDR de Benjamini–Hochberg.",
      "Planned tests: global one-way ANOVA and Kruskal–Wallis; pairwise Welch t-test and Mann–Whitney U; Benjamini–Hochberg FDR correction.",
    ))
    return

  work = stats_df.copy()
  if q_col in work.columns:
    work[q_col] = pd.to_numeric(work[q_col], errors="coerce")
  if "anova_pvalue" in work.columns:
    work["anova_pvalue"] = pd.to_numeric(work["anova_pvalue"], errors="coerce")
  if "kruskal_pvalue" in work.columns:
    work["kruskal_pvalue"] = pd.to_numeric(work["kruskal_pvalue"], errors="coerce")

  if category_col in work.columns:
    total_categories = int(work[category_col].astype(str).nunique())
    anova_sig = int(work.loc[work.get("anova_pvalue", pd.Series(np.nan, index=work.index)).lt(0.05), category_col].astype(str).nunique())
    kw_sig = int(work.loc[work.get("kruskal_pvalue", pd.Series(np.nan, index=work.index)).lt(0.05), category_col].astype(str).nunique())
  else:
    total_categories = 1
    anova_sig = int(pd.to_numeric(work.get("anova_pvalue", pd.Series(dtype=float)), errors="coerce").lt(0.05).any())
    kw_sig = int(pd.to_numeric(work.get("kruskal_pvalue", pd.Series(dtype=float)), errors="coerce").lt(0.05).any())

  significant = work[work[q_col].lt(0.05)].copy() if q_col in work.columns else pd.DataFrame()
  pair_labels_pt: list[str] = []
  pair_labels_en: list[str] = []
  if not significant.empty and group1_col in significant.columns and group2_col in significant.columns:
    significant["_pair"] = significant[group1_col].astype(str) + " × " + significant[group2_col].astype(str)
    pair_rows = []
    for pair, group in significant.groupby("_pair", sort=False):
      min_q = float(group[q_col].min())
      n_categories = int(group[category_col].astype(str).nunique()) if category_col in group.columns else int(len(group))
      examples = []
      if category_col in group.columns:
        examples = group.sort_values(q_col)[category_col].astype(str).drop_duplicates().head(2).tolist()
      pair_rows.append((pair, n_categories, min_q, examples))
    pair_rows = sorted(pair_rows, key=lambda x: (x[2], -x[1]))
    for pair, n_categories, min_q, examples in pair_rows[:max_pairs]:
      example_text = f" — {', '.join(examples)}" if examples else ""
      pair_labels_pt.append(f"{pair}: {n_categories} categoria(s), q mínimo={min_q:.3g}{example_text}")
      pair_labels_en.append(f"{pair}: {n_categories} category/categories, minimum q={min_q:.3g}{example_text}")
    remaining = max(0, len(pair_rows) - max_pairs)
    if remaining:
      pair_labels_pt.append(f"+{remaining} par(es) significativo(s)")
      pair_labels_en.append(f"+{remaining} additional significant pair(s)")

  if pair_labels_pt:
    result_pt = "Diferenças pareadas significativas após FDR: " + "; ".join(pair_labels_pt) + "."
    result_en = "FDR-significant pairwise differences: " + "; ".join(pair_labels_en) + "."
  else:
    result_pt = "Nenhuma comparação pareada permaneceu significativa após FDR de Benjamini–Hochberg (q < 0,05)."
    result_en = "No pairwise comparison remained significant after Benjamini–Hochberg FDR (q < 0.05)."

  st.markdown(txt(
    f"**Resumo dos resultados — {context_label}:** entre {total_categories} categoria(s) analisada(s), {anova_sig} apresentaram ANOVA global p < 0,05 e {kw_sig} apresentaram Kruskal–Wallis p < 0,05. {result_pt}",
    f"**Results summary — {context_label}:** among {total_categories} analysed category/categories, {anova_sig} had global ANOVA p < 0.05 and {kw_sig} had Kruskal–Wallis p < 0.05. {result_en}",
  ))
  st.caption(txt(
    "Testes usados: ANOVA de uma via e Kruskal–Wallis para o efeito global; Welch t-test e Mann–Whitney U nas comparações pareadas; significância definida por q < 0,05 após FDR de Benjamini–Hochberg aplicada aos p-valores do Mann–Whitney U.",
    "Tests used: one-way ANOVA and Kruskal–Wallis for the global effect; pairwise Welch t-test and Mann–Whitney U; significance defined as q < 0.05 after Benjamini–Hochberg FDR applied to Mann–Whitney U p-values.",
  ))


def render_environment_boxplot_statistical_summary(
  stats_df: pd.DataFrame,
  id_col: str,
  n_lake_samples: int,
  n_external_samples: int,
  context_label: str,
  *,
  max_markers: int = 8,
) -> None:
  """Summarise the fixed Amazonian-lakes versus external-environments boxplot."""
  if stats_df is None or stats_df.empty:
    st.markdown(txt(
      f"**Resumo dos resultados — {context_label}:** não houve replicação suficiente para comparar os dois conjuntos.",
      f"**Results summary — {context_label}:** there was insufficient replication to compare the two datasets.",
    ))
    return
  work = stats_df.copy()
  q_col = "mannwhitney_qvalue_BH"
  work[q_col] = pd.to_numeric(work.get(q_col), errors="coerce")
  significant = work[work[q_col].lt(0.05)].sort_values(q_col)
  lake_higher = int(significant["direction"].astype(str).eq("Higher in Amazonian lakes").sum()) if "direction" in significant.columns else 0
  external_higher = int(significant["direction"].astype(str).eq("Higher in external environments").sum()) if "direction" in significant.columns else 0
  marker_labels = []
  for _, row in significant.head(max_markers).iterrows():
    marker_labels.append(f"{row.get(id_col, '')} (q={float(row[q_col]):.3g})")
  marker_text = ", ".join(marker_labels)
  if len(significant) > max_markers:
    marker_text += f"; +{len(significant) - max_markers}"

  if significant.empty:
    result_pt = "Nenhum marcador apresentou diferença significativa entre as lagoas amazônicas e os ambientes externos após FDR (q < 0,05)."
    result_en = "No marker differed significantly between Amazonian lakes and external environments after FDR (q < 0.05)."
  else:
    result_pt = f"{len(significant)}/{len(work)} marcadores foram significativos: {lake_higher} com valores maiores nas lagoas amazônicas e {external_higher} com valores maiores nos ambientes externos. Marcadores mais significativos: {marker_text}."
    result_en = f"{len(significant)}/{len(work)} markers were significant: {lake_higher} were higher in Amazonian lakes and {external_higher} were higher in external environments. Most significant markers: {marker_text}."

  st.markdown(txt(
    f"**Resumo dos resultados — {context_label}:** comparação de {n_lake_samples} amostras das lagoas com {n_external_samples} colunas externas. {result_pt}",
    f"**Results summary — {context_label}:** comparison of {n_lake_samples} lake samples with {n_external_samples} external columns. {result_en}",
  ))
  st.caption(txt(
    "Testes usados: Mann–Whitney U bilateral em log1p das contagens exatas, com FDR de Benjamini–Hochberg entre todos os marcadores; Welch t-test bilateral reportado como análise paramétrica complementar. A significância foi definida por q < 0,05.",
    "Tests used: two-sided Mann–Whitney U on log1p exact counts, with Benjamini–Hochberg FDR across all markers; two-sided Welch t-test reported as a complementary parametric analysis. Significance was defined as q < 0.05.",
  ))

def taxonomy_barplot_statistics(
  level_name: str,
  *,
  selected_groups: list[str] | None,
  view_mode: str,
  top_n: int | None,
  grouping_factor: str,
) -> tuple[pd.DataFrame, int, int]:
  """Inferential tests for taxa displayed in the taxonomy stacked barplot.

  Tests always use the 20 individual study samples, even when the displayed
  bars are lake-season aggregates. This preserves biological replication.
  """
  work = taxonomy_profile_table(level_name, view_mode="Individual samples").copy()
  if work.empty or grouping_factor not in work.columns:
    return pd.DataFrame(), 0, 0
  if selected_groups:
    if str(view_mode).lower().startswith("individual"):
      work = work[work["group"].astype(str).isin([str(x) for x in selected_groups])].copy()
    else:
      work = work[work["environment_feature"].astype(str).isin([str(x) for x in selected_groups])].copy()
  ranked = work.groupby("taxon")["abundance"].mean().sort_values(ascending=False)
  displayed_total = len(ranked) if top_n is None or int(top_n) <= 0 or int(top_n) >= len(ranked) else int(top_n)
  # Testing tens of thousands of species interactively is not useful and can
  # freeze the browser. When all taxa are drawn, test the 200 most abundant and
  # state the cap explicitly in the result table/caption.
  tested_n = min(displayed_total, 200)
  keep = ranked.head(tested_n).index.tolist()
  rows = []
  for taxon in keep:
    sub = work[work["taxon"].astype(str).eq(str(taxon))].copy()
    result = _numeric_group_stats(sub, "abundance", grouping_factor, category=str(taxon))
    if not result.empty:
      rows.append(result)
  return (pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()), tested_n, displayed_total

def _boxplot_pairwise_stats(long: pd.DataFrame, category_col: str, group_col: str = "lake") -> pd.DataFrame:
  if long is None or long.empty or category_col not in long.columns or group_col not in long.columns:
    return pd.DataFrame()
  work = long.copy()
  # Defensive aggregation: at most one value per category × group × sample.
  if "sample" in work.columns:
    work = work.groupby([category_col, group_col, "sample"], as_index=False)["log1p_normalized_count"].sum()
  rows = []
  for category, subset in work.groupby(category_col):
    groups = sorted(subset[group_col].dropna().astype(str).unique().tolist())
    values = [subset.loc[subset[group_col].astype(str).eq(group), "log1p_normalized_count"].dropna().to_numpy(float) for group in groups]
    if len(groups) < 2 or any(len(value) < 2 for value in values):
      continue
    try:
      anova_p = float(stats.f_oneway(*values).pvalue)
    except Exception:
      anova_p = np.nan
    try:
      kruskal_p = float(stats.kruskal(*values).pvalue)
    except Exception:
      kruskal_p = np.nan
    for i in range(len(groups)):
      for j in range(i + 1, len(groups)):
        try:
          t_p = float(stats.ttest_ind(values[i], values[j], equal_var=False, nan_policy="omit").pvalue)
        except Exception:
          t_p = np.nan
        try:
          mw_p = float(stats.mannwhitneyu(values[i], values[j], alternative="two-sided").pvalue)
        except Exception:
          mw_p = np.nan
        rows.append({
          "category": str(category),
          "observation_unit": "biological sample after within-category marker aggregation",
          "grouping_factor": group_col,
          "global_parametric_test": "one-way ANOVA",
          "anova_pvalue": anova_p,
          "global_nonparametric_test": "Kruskal-Wallis",
          "kruskal_pvalue": kruskal_p,
          "pairwise_parametric_test": "Welch t-test",
          "pairwise_nonparametric_test": "Mann-Whitney U",
          "group1": groups[i], "group2": groups[j],
          "n_group1": len(values[i]), "n_group2": len(values[j]),
          "t_test_pvalue": t_p, "mannwhitney_pvalue": mw_p,
        })
  result = pd.DataFrame(rows)
  if result.empty:
    return result
  result["qvalue"] = _bh_fdr(result["mannwhitney_pvalue"])
  result["significant_q_lt_0_05"] = result["qvalue"].lt(0.05).fillna(False)
  result["multiple_testing"] = "Benjamini-Hochberg FDR across all displayed category/group pairwise Mann-Whitney tests"
  return result


def publication_boxplot_panel(df: pd.DataFrame, id_cols: list[str], category_col: str, title: str, key_prefix: str, normalize_per_sample: bool = True, season_split: bool = False):
  """Publication boxplot with exact sample×category aggregation and audited inputs."""
  title = str(title or "").strip()
  if not title or title.casefold() in {"undefined", "none", "nan", "null"}:
    title = txt("Boxplot de biomarcadores KO por categoria e lagoa", "KO biomarker boxplot by category and lake")
  st.markdown("#### " + title)
  long = _long_marker_counts_for_boxplot(df, id_cols, category_col, normalize_per_sample=normalize_per_sample)
  if long.empty:
    st.info(txt("Não há colunas de amostras AM/TI/TIA/VI para o boxplot.", "No AM/TI/TIA/VI sample columns are available for the boxplot."))
    return
  ranked_categories = long.groupby(category_col)["normalized_count"].sum().sort_values(ascending=False)
  all_categories = ranked_categories.index.astype(str).tolist()
  show_all_categories = st.checkbox(
    txt(f"Mostrar todas as {len(all_categories)} categorias no boxplot", f"Show all {len(all_categories)} categories in the boxplot"),
    value=False, key=f"{key_prefix}_show_all_categories",
  )
  if show_all_categories:
    selected_categories = all_categories
  else:
    category_top_n = int(st.number_input(
      txt("Top categorias no boxplot", "Top categories in boxplot"),
      min_value=1, max_value=max(1, len(all_categories)), value=min(8, max(1, len(all_categories))), step=1,
      key=f"{key_prefix}_category_top_n",
    ))
    selected_categories = all_categories[:category_top_n]
  plot = long[long[category_col].astype(str).isin(selected_categories)].copy()

  stats_source = plot.copy()
  stats_category = category_col
  if season_split:
    stats_category = "category_and_season"
    stats_source[stats_category] = stats_source[category_col].astype(str) + " | " + stats_source["season"].astype(str)
  stats_df = _boxplot_pairwise_stats(stats_source, stats_category)
  descriptive_group_cols = [category_col, "lake"] + (["season"] if season_split else [])
  descriptive_stats = _boxplot_descriptive_stats(plot, "log1p_normalized_count", descriptive_group_cols)
  significant_categories = set()
  if not stats_df.empty and "significant_q_lt_0_05" in stats_df.columns:
    significant_rows = stats_df[stats_df["significant_q_lt_0_05"]].copy()
    if season_split:
      significant_categories = {str(v).split(" | ", 1)[0] for v in significant_rows.get("category", pd.Series(dtype=str)).astype(str)}
    else:
      significant_categories = set(significant_rows.get("category", pd.Series(dtype=str)).astype(str))
  display_category_col = "_boxplot_category_label"
  plot[display_category_col] = plot[category_col].astype(str).map(lambda v: v + " *" if v in significant_categories else v)
  show_raw_points = st.checkbox(
    txt("Mostrar pontos individuais", "Show individual sample points"), value=True,
    key=f"{key_prefix}_show_raw_points",
  )
  category_label_order = [str(v) + (" *" if str(v) in significant_categories else "") for v in selected_categories]
  common_hover = ["sample", "normalized_count", "distinct_markers", "marker_rows_nonmissing", "missing_marker_rows", category_col, "season", "observation_unit"]
  if season_split:
    fig_box = px.box(
      plot, x=display_category_col, y="log1p_normalized_count", color="lake",
      points="all" if show_raw_points else False, facet_col="season", facet_col_spacing=0.07,
      category_orders={display_category_col: category_label_order, "season": ["Dry", "Rainy"]},
      hover_data=common_hover, title=title,
      labels={"log1p_normalized_count": "log1p normalized count", display_category_col: "marker category"},
      color_discrete_sequence=px.colors.qualitative.Safe,
    )
    season_titles = {"season=Dry": txt("Estação seca", "Dry season"), "season=Rainy": txt("Estação chuvosa", "Rainy season")}
    fig_box.for_each_annotation(lambda annotation: annotation.update(text=season_titles.get(str(annotation.text), str(annotation.text)), y=1.01))
    figure_width = min(3400, max(1800, int(190 * max(1, len(selected_categories)) * 1.55)))
    figure_height = 900
    margins = dict(l=95, r=60, t=125, b=230)
    legend_y = -0.20
    fig_box.update_xaxes(tickangle=-35)
  else:
    fig_box = px.box(
      plot, x="log1p_normalized_count", y=display_category_col, color="lake",
      points="all" if show_raw_points else False, orientation="h",
      category_orders={display_category_col: list(reversed(category_label_order))},
      hover_data=common_hover, title=title,
      labels={"log1p_normalized_count": "log1p normalized count", display_category_col: "marker category"},
      color_discrete_sequence=px.colors.qualitative.Safe,
    )
    figure_width = 1650
    figure_height = max(760, 82 * max(1, len(selected_categories)) + 250)
    margins = dict(l=520, r=70, t=110, b=150)
    legend_y = -0.14
  fig_box.update_traces(jitter=0.25, marker=dict(size=6, opacity=0.62))
  fig_box.update_layout(
    height=figure_height, width=figure_width, boxgap=0.28, boxgroupgap=0.12,
    margin=margins, title=dict(text=title, x=0.01, xanchor="left", y=0.985, yanchor="top"),
    legend=dict(orientation="h", y=legend_y, yanchor="top", x=0, xanchor="left", bgcolor="rgba(255,255,255,0.96)"),
    legend_title_text=txt("Lagoa", "Lake"),
    meta={
      "preserve_legend_position": True, "no_synthetic_values": True, "require_nonempty_title": True,
      "observation_unit": "one biological sample per category after within-sample marker aggregation",
      "source_script": "app.py:_long_marker_counts_for_boxplot/_boxplot_pairwise_stats/publication_boxplot_panel",
    },
  )
  bold_axis_layout(fig_box, x_size=14, y_size=14, title_size=18)
  source_sample_cols = _article_lake_sample_columns(df.columns)
  source_exact = df[[c for c in id_cols + source_sample_cols if c in df.columns]].copy()
  audit_descriptive = descriptive_stats.copy()
  audit_descriptive.insert(0, "table_type", "descriptive_boxplot_statistics")
  audit_inferential = stats_df.copy()
  if not audit_inferential.empty:
    audit_inferential.insert(0, "table_type", "inferential_tests")
  audit_output = pd.concat([audit_descriptive, audit_inferential], ignore_index=True, sort=False)
  render_plotly_downloadable(
    fig_box, key=f"{key_prefix}_boxplot", basename=f"{key_prefix}_boxplot_with_statistics",
    audit_input_table=source_exact, audit_processed_table=plot, audit_output_table=audit_output,
    audit_method="Counts are converted to per-10,000 within the selected marker matrix when normalization is enabled; marker rows are summed to one value per biological sample × category. Global ANOVA and Kruskal–Wallis plus pairwise Welch t-test and Mann–Whitney U are reported with Benjamini–Hochberg FDR.",
    audit_input_source="Exact packaged supplementary-table rows and the 20 AM/TI/TIA/VI study sample columns.",
    audit_script="app.py:_long_marker_counts_for_boxplot,_boxplot_pairwise_stats,publication_boxplot_panel",
    audit_instructions="Open the corresponding KO or Iron & metals module; source, processed and statistical tables are available in this collapsed panel.",
  )
  render_boxplot_statistical_summary(stats_df, title, category_col="category", max_pairs=6)
  st.caption(txt(
    "Unidade de observação: uma amostra biológica por categoria após somar todos os marcadores da categoria dentro da amostra. As tabelas-fonte, processada e estatística completas estão no painel retrátil imediatamente abaixo da figura.",
    "Observation unit: one biological sample per category after summing all category markers within the sample. Complete source, processed and statistical tables are in the collapsed panel immediately below the figure."
  ))


def _bh_fdr(pvalues: pd.Series) -> pd.Series:
  """Benjamini–Hochberg adjustment preserving the original index."""
  out = pd.Series(np.nan, index=pvalues.index, dtype=float)
  valid = pd.to_numeric(pvalues, errors="coerce").dropna()
  if valid.empty:
    return out
  vals = valid.to_numpy(float)
  order = np.argsort(vals)
  ranked = vals[order]
  m = len(ranked)
  adjusted = np.minimum.accumulate((ranked * m / np.arange(1, m + 1))[::-1])[::-1]
  restored = np.empty_like(adjusted)
  restored[order] = np.clip(adjusted, 0, 1)
  out.loc[valid.index] = restored
  return out


def st8_environment_marker_statistics(
  df: pd.DataFrame,
  numeric_cols: list[str],
  id_col: str,
  category_col: str,
  description_col: str,
  external_cols: list[str],
) -> pd.DataFrame:
  """Compare each marker in the 20 Amazonian samples against selected ST8 environments."""
  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  external_cols = [c for c in external_cols if c in df.columns and c not in lake_cols]
  rows = []
  if not lake_cols or not external_cols:
    return pd.DataFrame()
  for _, row in df.iterrows():
    lake_raw = pd.to_numeric(row[lake_cols], errors="coerce").dropna().to_numpy(float)
    ext_raw = pd.to_numeric(row[external_cols], errors="coerce").dropna().to_numpy(float)
    if len(lake_raw) < 2 or len(ext_raw) < 2:
      continue
    lake_log = np.log1p(lake_raw)
    ext_log = np.log1p(ext_raw)
    try:
      welch_p = float(stats.ttest_ind(lake_log, ext_log, equal_var=False, nan_policy="omit").pvalue)
    except Exception:
      welch_p = np.nan
    try:
      mw_p = float(stats.mannwhitneyu(lake_log, ext_log, alternative="two-sided").pvalue)
    except Exception:
      mw_p = np.nan
    lake_mean = float(np.mean(lake_raw))
    ext_mean = float(np.mean(ext_raw))
    l2r = float(np.log2((lake_mean + 1.0) / (ext_mean + 1.0)))
    rows.append({
      id_col: row.get(id_col, ""),
      category_col: row.get(category_col, "Unclassified"),
      description_col: row.get(description_col, ""),
      "amazonian_mean_count": lake_mean,
      "external_mean_count": ext_mean,
      "log2_ratio_amazonia_vs_external": l2r,
      "direction": "Higher in Amazonian lakes" if l2r > 0 else "Higher in external environments" if l2r < 0 else "Equal means",
      "n_amazonian_samples": len(lake_raw),
      "n_external_samples": len(ext_raw),
      "amazonian_detection_fraction": float(np.mean(lake_raw > 0)),
      "external_detection_fraction": float(np.mean(ext_raw > 0)),
      "welch_ttest_pvalue_log1p": welch_p,
      "mannwhitney_pvalue_log1p": mw_p,
    })
  out = pd.DataFrame(rows)
  if out.empty:
    return out
  out["mannwhitney_qvalue_BH"] = _bh_fdr(out["mannwhitney_pvalue_log1p"])
  out["significant_q_lt_0_05"] = out["mannwhitney_qvalue_BH"].lt(0.05).fillna(False)
  out["method"] = "Per-KO Mann–Whitney U and Welch t-test on log1p counts; Benjamini–Hochberg FDR across displayed markers"
  return out.sort_values(["mannwhitney_qvalue_BH", "log2_ratio_amazonia_vs_external"], ascending=[True, False], na_position="last").reset_index(drop=True)


def st8_environment_boxplot_panel(
  df: pd.DataFrame,
  numeric_cols: list[str],
  id_col: str,
  category_col: str,
  description_col: str,
  key_prefix: str,
  title: str,
  fixed_external_cols: list[str] | None = None,
  section_label: str = "",
):
  """Lake-versus-environment boxplots using every selected sample and every displayed marker."""
  heading = (str(section_label).strip() + " " + str(title).strip()).strip()
  st.markdown("#### " + heading)
  meta = st8_column_metadata()
  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  if len(lake_cols) != 20:
    st.error(txt(
      f"O boxplot foi bloqueado: esperado 20 amostras AM/TI/TIA/VI, mas {len(lake_cols)} foram identificadas.",
      f"The boxplot was blocked: 20 AM/TI/TIA/VI samples were expected, but {len(lake_cols)} were identified.",
    ))
    return

  if fixed_external_cols is not None:
    external_cols = [c for c in dict.fromkeys(fixed_external_cols) if c in df.columns and c in numeric_cols and c not in lake_cols]
    st.caption(txt(
      f"Escopo fixo do painel 2B: todas as 20 amostras das lagoas + todas as {len(external_cols)} colunas externas da ST8. Nenhuma amostra é removida por filtros.",
      f"Fixed 2B scope: all 20 lake samples + all {len(external_cols)} external ST8 columns. No sample is removed by filters.",
    ))
  elif meta.empty:
    external_cols = [c for c in numeric_cols if c not in lake_cols]
  else:
    groups = sorted(meta.get("ST8_group", pd.Series(dtype=str)).replace("", np.nan).dropna().astype(str).unique().tolist())
    layers = sorted(meta.get("data_layer", pd.Series(dtype=str)).replace("", np.nan).dropna().astype(str).unique().tolist())
    c1, c2 = st.columns(2)
    with c1:
      selected_groups = st.multiselect(txt("Ambientes/grupos externos", "External environments/groups"), groups, default=groups, key=f"{key_prefix}_stats_groups")
    with c2:
      selected_layers = st.multiselect(txt("Camadas ômicas externas", "External omics layers"), layers, default=layers, key=f"{key_prefix}_stats_layers")
    scoped = _st8_cols_for_scope(numeric_cols, meta, selected_groups, selected_layers, [])
    external_cols = [c for c in scoped if c not in lake_cols]
  if not external_cols:
    st.info(txt("Selecione pelo menos um grupo/camada externa.", "Select at least one external group/layer."))
    return

  stats_df = st8_environment_marker_statistics(df, numeric_cols, id_col, category_col, description_col, external_cols)
  if stats_df.empty:
    st.info(txt("Não há replicação suficiente para os testes por KO.", "There is not enough replication for per-KO tests."))
    return
  show_all_markers = st.checkbox(
    txt(f"Mostrar todos os {len(stats_df)} marcadores no boxplot", f"Show all {len(stats_df)} markers in the boxplot"),
    value=True,
    key=f"{key_prefix}_stats_show_all_markers",
  )
  plot_stats = stats_df.copy()
  if not show_all_markers:
    c1, c2, c3 = st.columns([0.30, 0.34, 0.36])
    with c1:
      direction = st.selectbox(txt("Direção", "Direction"), ["Both", "Higher in Amazonian lakes", "Higher in external environments"], key=f"{key_prefix}_stats_direction")
    with c2:
      significant_only = st.checkbox(txt("Somente q < 0,05", "Only q < 0.05"), value=False, key=f"{key_prefix}_stats_sigonly")
    with c3:
      max_markers = max(1, len(stats_df))
      topn = int(st.number_input(txt("Número de KOs no boxplot", "Number of KOs in boxplot"), min_value=1, max_value=max_markers, value=min(20, max_markers), step=1, key=f"{key_prefix}_stats_topn"))
    if direction != "Both":
      plot_stats = plot_stats[plot_stats["direction"].eq(direction)]
    if significant_only:
      plot_stats = plot_stats[plot_stats["significant_q_lt_0_05"]]
    plot_stats["abs_log2_ratio"] = plot_stats["log2_ratio_amazonia_vs_external"].abs()
    plot_stats = plot_stats.sort_values(["significant_q_lt_0_05", "abs_log2_ratio"], ascending=[False, False]).head(topn)
  else:
    source_order = {str(v): i for i, v in enumerate(df[id_col].astype(str).tolist())}
    plot_stats["_source_order"] = plot_stats[id_col].astype(str).map(source_order).fillna(len(source_order))
    plot_stats = plot_stats.sort_values("_source_order", kind="mergesort")

  if plot_stats.empty:
    st.info(txt("Nenhum KO atende aos filtros.", "No KO matches the filters."))
  else:
    selected_ids = plot_stats[id_col].astype(str).tolist()
    work = df[df[id_col].astype(str).isin(selected_ids)].copy()
    id_meta = [id_col, category_col, description_col]
    long_lake = work[id_meta + lake_cols].melt(id_meta, var_name="sample", value_name="count")
    long_lake["comparison_group"] = "Amazonian lakes"
    long_ext = work[id_meta + external_cols].melt(id_meta, var_name="sample", value_name="count")
    long_ext["comparison_group"] = "External iron-rich environments"
    long = pd.concat([long_lake, long_ext], ignore_index=True)
    long["count"] = pd.to_numeric(long["count"], errors="coerce")
    long["log1p_count"] = np.log1p(long["count"])
    stat_merge_cols = [
      id_col, "mannwhitney_pvalue_log1p", "mannwhitney_qvalue_BH", "welch_ttest_pvalue_log1p",
      "log2_ratio_amazonia_vs_external", "direction", "significant_q_lt_0_05",
    ]
    long = long.merge(stats_df[stat_merge_cols], on=id_col, how="left", validate="many_to_one")
    long["marker_label"] = (
      long[category_col].fillna("Unclassified").astype(str)
      + " (" + long[id_col].astype(str) + ")"
      + np.where(long["significant_q_lt_0_05"].fillna(False), " *", "")
    )
    order = []
    for marker_id in selected_ids:
      row = plot_stats.loc[plot_stats[id_col].astype(str).eq(marker_id)].iloc[0]
      label = f"{row.get(category_col, 'Unclassified')} ({marker_id})"
      if bool(row.get("significant_q_lt_0_05", False)):
        label += " *"
      order.append(label)
    long["marker_label"] = pd.Categorical(long["marker_label"], categories=order[::-1], ordered=True)
    fig = px.box(
      long,
      x="log1p_count",
      y="marker_label",
      color="comparison_group",
      points="all",
      orientation="h",
      hover_data={
        "sample": True,
        "count": ":.3f",
        category_col: True,
        description_col: True,
        "mannwhitney_pvalue_log1p": ":.3g",
        "mannwhitney_qvalue_BH": ":.3g",
        "welch_ttest_pvalue_log1p": ":.3g",
        "log2_ratio_amazonia_vs_external": ":.3f",
        "direction": True,
        "significant_q_lt_0_05": True,
      },
      title=heading,
      labels={"log1p_count": "log1p exact count", "marker_label": "Pathway/category (KO)", "comparison_group": "Dataset"},
      color_discrete_sequence=["#00796B", "#C62828"],
    )
    fig.update_traces(jitter=0.28, marker=dict(size=5, opacity=0.58))
    figure_height = max(680, min(3600, 20 * len(order) + 220))
    fig.update_layout(
      height=max(820, figure_height),
      width=1800,
      margin=dict(l=400, r=60, t=110, b=140),
      title=dict(text=heading, x=0.01, xanchor="left", y=0.985, yanchor="top"),
      legend=dict(orientation="h", y=-0.16, yanchor="top", x=0, xanchor="left", bgcolor="rgba(255,255,255,0.96)"),
      legend_title_text=txt("Conjunto de dados", "Dataset"),
      meta={
        "article_scroll_viewport": True,
        "article_viewport_height": 850,
        "compact_external_title": True,
        "preserve_legend_position": True,
        "require_nonempty_title": True,
        "no_synthetic_values": True,
      },
    )
    environment_descriptive = _boxplot_descriptive_stats(
      long, "log1p_count", [id_col, "comparison_group"]
    )
    environment_descriptive.insert(0, "table_type", "descriptive_boxplot_statistics")
    environment_inferential = stats_df.copy()
    if not environment_inferential.empty:
      environment_inferential.insert(0, "table_type", "inferential_tests")
    environment_output = pd.concat([environment_descriptive, environment_inferential], ignore_index=True, sort=False)
    render_plotly_downloadable(
      fig, key=f"{key_prefix}_environment_boxplot", basename=f"{key_prefix}_Amazonian_lakes_vs_external_boxplot_all_samples",
      audit_input_table=work[id_meta + lake_cols + external_cols].copy(),
      audit_processed_table=long.copy(), audit_output_table=environment_output,
      audit_method="One real ST8 sample/column per point. Boxplot quartiles and Tukey whiskers are calculated on log1p exact counts; per-KO Mann–Whitney U with Benjamini–Hochberg FDR and complementary Welch t-test are reported.",
      audit_input_source="Supplementary Table 8 exact lake and selected external-environment columns; missing values remain missing.",
      audit_script="app.py:st8_environment_marker_statistics,st8_environment_boxplot_panel,_boxplot_descriptive_stats",
      audit_instructions="Open this panel to inspect the exact source matrix, plotted long table, quartiles/whiskers/outliers and inferential tests.",
    )
    render_environment_boxplot_statistical_summary(
      stats_df,
      id_col,
      len(lake_cols),
      len(external_cols),
      heading,
      max_markers=8,
    )
    st.caption(txt(
      "Método: boxplot horizontal com uma observação por amostra/coluna real da ST8; as comparações usam Mann–Whitney U bilateral com FDR de Benjamini–Hochberg e Welch t-test complementar em log1p das contagens exatas. Script: app.py, funções st8_environment_marker_statistics(), render_environment_boxplot_statistical_summary() e st8_environment_boxplot_panel(). O resumo estatístico fica apenas abaixo da figura.",
      "Method: horizontal boxplot with one observation per real ST8 sample/column; comparisons use two-sided Mann–Whitney U with Benjamini–Hochberg FDR and a complementary Welch t-test on log1p exact counts. Script: app.py, functions st8_environment_marker_statistics(), render_environment_boxplot_statistical_summary() and st8_environment_boxplot_panel(). The statistical summary appears only below the figure."
    ))
    csv_button(long, f"{key_prefix}_boxplot_all_marker_sample_values.csv", txt("Baixar todos os valores usados no boxplot", "Download all values used in the boxplot"))
  st.caption(txt(
    f"Legenda estatística: cada ponto representa uma amostra/coluna real da ST8; * indica Mann–Whitney q < 0,05 após FDR de Benjamini–Hochberg entre {len(stats_df)} marcadores. Welch t-test é reportado como análise paramétrica complementar. Foram usados 20 valores amazônicos e {len(external_cols)} valores externos por marcador, sem preencher dados ausentes artificialmente.",
    f"Statistical legend: each point is a real ST8 sample/column; * denotes Mann–Whitney q < 0.05 after Benjamini–Hochberg FDR across {len(stats_df)} markers. Welch t-test is reported as a complementary parametric analysis. Each marker uses 20 Amazonian values and {len(external_cols)} external values, with no artificial filling of missing data.",
  ))
  show_table(stats_df, f"{key_prefix}_environment_statistics", height=520)
  csv_button(stats_df, f"{key_prefix}_Amazonian_lakes_vs_external_statistics.csv", txt("Baixar testes por KO", "Download per-KO tests"))


def markers_tab():
  st.subheader(txt("Atlas de biomarcadores KO dos ciclos biogeoquímicos", "KO Biogeochemical Cycles Biomarkers"))
  catalogue = marker_table()
  prior_n = int(catalogue.loc[catalogue["Study"].astype(str).str.contains("Salazar", case=False, na=False), "KO"].astype(str).nunique())
  new_n = int(catalogue.loc[catalogue["Study"].astype(str).str.contains("New marker", case=False, na=False), "KO"].astype(str).nunique())
  total_n = int(catalogue["KO"].astype(str).nunique())
  st.markdown(txt(
    f"Esta seção parte dos biomarcadores introduzidos por **Salazar et al. (2019)** e mostra a expansão realizada neste estudo. O catálogo contém **{total_n} KOs únicos**: {prior_n} associados ao conjunto de referência e {new_n} classificados como novos marcadores/expansões neste projeto. A origem, a via e a justificativa de cada KO permanecem explícitas.",
    f"This section starts from the biomarkers introduced by **Salazar et al. (2019)** and presents the expansion developed in this study. The catalogue contains **{total_n} unique KOs**: {prior_n} associated with the reference set and {new_n} classified as new markers/extensions in this project. The source, pathway and rationale of every KO remain explicit."
  ))
  c1, c2, c3 = st.columns(3)
  with c1:
    studies = sorted([x for x in catalogue["Study"].dropna().astype(str).unique() if x])
    study = st.multiselect(txt("Fonte do marcador", "Marker source"), studies, default=studies, key="marker_source_filter")
  with c2:
    metas = sorted([x for x in catalogue["General metabolism"].dropna().astype(str).unique() if x])
    metabolism = st.multiselect(txt("Metabolismo geral", "General metabolism"), metas, default=metas, key="marker_general_metabolism_filter")
  with c3:
    q = st.text_input(txt("Buscar KO, descrição ou pathway", "Search KO, description or pathway"), "")
  f = catalogue[catalogue["Study"].isin(study) & catalogue["General metabolism"].isin(metabolism)].copy()
  f = filter_by_text(f, ["KO", "KO description", "Marker for:", "KEGG MODULE"], q)
  show_table(f, "marker_table")
  csv_button(f, "KO-marker-biogeochemical-cyc_filtered.csv", txt("Baixar marcadores filtrados", "Download filtered markers"))

  st.divider()
  st.subheader(txt("1. Lagoas amazônicas — todos os biomarcadores KO da Supplementary Table 8", "1. Amazonian lakes — all KO biomarkers from Supplementary Table 8"))
  counts, numeric_cols = counts_table("table8", ST8_ALL_KO_SHEET, ["KO", "Metabolism", "KO description"])
  if len(counts) != 189:
    st.error(txt(
      f"A aba ST8 — all KO biomarkers deveria conter 189 marcadores, mas {len(counts)} foram carregados. Verifique a Supplementary Table 8 instalada.",
      f"The ST8 — all KO biomarkers sheet should contain 189 markers, but {len(counts)} were loaded. Check the installed Supplementary Table 8.",
    ))
  else:
    st.success(txt("Supplementary Table 8 validada: 189/189 marcadores KO carregados.", "Supplementary Table 8 validated: 189/189 KO markers loaded."))
  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  all_metab = sorted(counts["Metabolism"].dropna().astype(str).unique())
  complete_ko_panel = st.checkbox(
    txt(f"Mostrar o painel completo com todos os {len(counts)} KOs", f"Show the complete panel with all {len(counts)} KOs"),
    value=True, key="st8_lake_bio_complete_189",
  )
  selected_metab = st.multiselect(
    txt("Filtrar vias/categorias", "Filter pathways/categories"), all_metab, default=all_metab,
    key="st8_lake_bio_metabolism", disabled=complete_ko_panel,
  )
  counts_f = counts.copy() if complete_ko_panel else counts[counts["Metabolism"].astype(str).isin(selected_metab)].copy()
  show_ko_pathway_detail = st.checkbox(
    txt("Mostrar a via após o identificador KO nos heatmaps", "Show pathway after the KO identifier in heatmaps"),
    value=True,
    key="st8_show_ko_pathway_detail_189",
    help=txt(
      "Quando ativado, cada linha é exibida como KO | via/categoria. Quando desativado, apenas o identificador KO é mostrado; a via permanece no hover e nas tabelas.",
      "When enabled, each row is displayed as KO | pathway/category. When disabled, only the KO identifier is shown; the pathway remains in hover text and tables.",
    ),
  )
  ko_id = counts_f["KO"].fillna("").astype(str).str.strip()
  ko_pathway = counts_f["Metabolism"].fillna("Unclassified").astype(str).str.strip()
  counts_f["KO_pathway_label"] = np.where(
    show_ko_pathway_detail & ko_pathway.ne(""),
    ko_id + " | " + ko_pathway,
    ko_id,
  )
  top_n = heatmap_row_limit_control(counts_f, "bio_st8_lakes_heatmap", noun_pt="KOs", noun_en="KOs", default_top=len(counts_f))
  fig_raw = heatmap_figure(
    counts_f, lake_cols, "KO_pathway_label",
    f"Supplementary Table 8 — Amazonian lake KO biomarkers: raw counts ({len(counts_f)} markers)",
    top_n=top_n, zscore_rows=False, x_label_map=lake_sample_label_map(),
  )
  if fig_raw:
    render_plotly_downloadable(fig_raw, key="biogeochemical_st8_lakes_heatmap_raw", basename="ST8_all_KO_biomarkers_Amazonian_lakes_raw_counts")
  fig_z = heatmap_figure(
    counts_f, lake_cols, "KO_pathway_label",
    f"Supplementary Table 8 — Amazonian lake KO biomarkers: row z-score ({len(counts_f)} markers)",
    top_n=top_n, zscore_rows=True, x_label_map=lake_sample_label_map(),
  )
  if fig_z:
    render_plotly_downloadable(fig_z, key="biogeochemical_st8_lakes_heatmap_zscore", basename="ST8_all_KO_biomarkers_Amazonian_lakes_row_zscore")
  st.caption(txt(
    f"Legenda: raw count e z-score usam exatamente os mesmos {top_n} KOs e as mesmas {len(lake_cols)} amostras. Todos os {len(counts_f)} KOs são mostrados por padrão; o filtro Top N é opcional.",
    f"Legend: raw-count and z-score panels use exactly the same {top_n} KOs and the same {len(lake_cols)} samples. All {len(counts_f)} KOs are displayed by default; the Top-N filter is optional."
  ))
  with st.expander(txt("Tabela completa das lagoas", "Complete lake table"), expanded=False):
    lake_table = counts_f[[c for c in ["KO", "Metabolism", "KO description"] + lake_cols if c in counts_f.columns]]
    complete_table_note(lake_table, "KOs", "KOs")
    show_table(lake_table, "bio_st8_lakes_counts", height=620)
    csv_button(lake_table, "ST8_all_KO_biomarkers_Amazonian_lakes.csv", txt("Baixar contagens das lagoas", "Download lake counts"))
  publication_boxplot_panel(
    counts_f, ["KO", "Metabolism", "KO description"], "Metabolism",
    txt("Boxplots dos biomarcadores KO por via, lagoa e amostra", "KO biomarker boxplots by pathway, lake and sample"),
    "st8_biogeochemical_ko_lakes", normalize_per_sample=True, season_split=False,
  )

  st.divider()
  st.subheader(txt("2. Lagoas amazônicas versus demais ambientes da Supplementary Table 8", "2. Amazonian lakes versus other Supplementary Table 8 environments"))
  st.caption(txt(
    "Os heatmaps abaixo mantêm todos os KOs por padrão e preservam a categoria/via na linha. A comparação estatística por KO usa as 20 amostras das lagoas contra as colunas externas selecionadas; devido à heterogeneidade entre estudos e camadas, os resultados devem ser interpretados como comparação exploratória.",
    "The heatmaps below retain all KOs by default and preserve pathway/category in each row. Per-KO statistics compare the 20 lake samples with the selected external columns; because studies and layers are heterogeneous, results should be interpreted as exploratory comparisons."
  ))
  render_st8_heatmap_scope_controls(
    counts_f, numeric_cols, "KO_pathway_label", "All biogeochemical-cycle KO biomarkers", "bio_st8_environment",
    x_label_map=st8_axis_label_map(),
    boxplot_spec={
      "id_col": "KO", "category_col": "Metabolism", "description_col": "KO description",
      "title": txt("Biomarcadores KO: todas as lagoas versus todos os ambientes externos", "KO biomarkers: all lakes versus all external environments"),
    },
  )
  st8_marker_abundance_panel()


def heatmap_then_table(df: pd.DataFrame, label_col: str, title: str, file_name: str, key_prefix: str):
  id_cols = infer_metadata_cols(df)
  if label_col not in id_cols:
    id_cols = [label_col] + id_cols
  numeric_cols = [c for c in df.columns if c not in set(id_cols) and pd.to_numeric(df[c], errors="coerce").notna().sum() > 0]
  c1, c2 = st.columns([0.28, 0.72])
  with c1:
    top_n = heatmap_row_limit_control(df, f"{key_prefix}_heatmap", default_top=40)
    zscore = st.checkbox("Z-score por linha", value=False, key=f"{key_prefix}_z")
  fig = heatmap_figure(df, numeric_cols, label_col, title, top_n=top_n, zscore_rows=zscore)
  if fig:
    render_plotly_downloadable(fig, key=f"{key_prefix}_heatmap", basename=f"{key_prefix}_heatmap")
  st.markdown("#### Tabela exata")
  complete_table_note(df)
  show_table(df, f"{key_prefix}_table", height=620)
  csv_button(df, file_name, f"Baixar {file_name}")



def iron_tab():
  st.subheader(txt("Ferro e metais", "Iron & metals"))
  st.markdown(txt(
    "A análise é apresentada em duas etapas: primeiro, todos os marcadores de ferro nas 20 amostras das lagoas; depois, as lagoas em comparação com os demais ambientes da Supplementary Table 8. A categoria biológica de cada KO permanece no rótulo e no hover.",
    "The analysis is presented in two stages: first, all iron markers across the 20 lake samples; then, the lakes compared with the other Supplementary Table 8 environments. The biological category of each KO remains in the label and hover text."
  ))
  counts, numeric_cols = counts_table("table8", ST8_IRON_ALL_SHEET, ["Function Id", "Biologic Role", "Function Name"])
  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  roles = sorted(counts["Biologic Role"].dropna().astype(str).unique())
  selected_roles = st.multiselect(txt("Categorias de metabolismo de ferro", "Iron-metabolism categories"), roles, default=roles, key="iron_metabolism_category_filter")
  counts_f = counts[counts["Biologic Role"].astype(str).isin(selected_roles)].copy() if selected_roles else counts.copy()
  counts_f = add_marker_pathway_label(counts_f, "Function Id", "Biologic Role")

  st.markdown("### " + txt("1. Lagoas amazônicas", "1. Amazonian lakes"))
  top_n = heatmap_row_limit_control(counts_f, "iron_st8_lakes_heatmap", noun_pt="KOs de ferro", noun_en="iron KOs", default_top=len(counts_f))
  fig_raw = heatmap_figure(
    counts_f, lake_cols, "marker_pathway_label",
    f"Supplementary Table 8 iron-metabolism KO markers in Amazonian lake samples — raw counts ({len(counts_f)} markers)",
    top_n=top_n, zscore_rows=False, x_label_map=lake_sample_label_map(),
  )
  if fig_raw:
    render_plotly_downloadable(fig_raw, key="iron_st8_lakes_heatmap_raw", basename="ST8_iron_KO_markers_Amazonian_lakes_raw_counts")
  fig_z = heatmap_figure(
    counts_f, lake_cols, "marker_pathway_label",
    f"Supplementary Table 8 iron-metabolism KO markers in Amazonian lake samples — row z-score ({len(counts_f)} markers)",
    top_n=top_n, zscore_rows=True, x_label_map=lake_sample_label_map(),
  )
  if fig_z:
    render_plotly_downloadable(fig_z, key="iron_st8_lakes_heatmap_zscore", basename="ST8_iron_KO_markers_Amazonian_lakes_row_zscore")
  st.caption(txt(
    f"Legenda: raw count e z-score usam exatamente os mesmos {top_n} marcadores de ferro e as mesmas {len(lake_cols)} amostras das lagoas. Todos os {len(counts_f)} marcadores são mostrados por padrão.",
    f"Legend: raw-count and z-score panels use exactly the same {top_n} iron markers and the same {len(lake_cols)} lake samples. All {len(counts_f)} markers are displayed by default."
  ))
  with st.expander(txt("Tabela completa das lagoas", "Complete lake table"), expanded=False):
    lake_table = counts_f[[c for c in ["Function Id", "Biologic Role", "Function Name"] + lake_cols if c in counts_f.columns]]
    complete_table_note(lake_table, "KOs de ferro", "iron KOs")
    show_table(lake_table, "iron_st8_lakes_counts", height=620)
    csv_button(lake_table, "ST8_iron_KO_markers_Amazonian_lakes.csv", txt("Baixar contagens das lagoas", "Download lake counts"))
  publication_boxplot_panel(
    counts_f, ["Function Id", "Biologic Role", "Function Name"], "Biologic Role",
    txt("Boxplots dos marcadores KO de ferro por categoria, lagoa e estação", "Iron KO marker boxplots by category, lake and season"),
    "st8_iron_ko_lakes", normalize_per_sample=True, season_split=True,
  )

  st.markdown("### " + txt("2. Lagoas versus demais ambientes", "2. Lakes versus other environments"))
  render_st8_heatmap_scope_controls(
    counts_f, numeric_cols, "marker_pathway_label", "Iron-metabolism KO markers", "iron_st8_environment",
    x_label_map=st8_axis_label_map(),
    boxplot_spec={
      "id_col": "Function Id", "category_col": "Biologic Role", "description_col": "Function Name",
      "title": txt("Marcadores KO de ferro: todas as lagoas versus todos os ambientes externos", "Iron KO markers: all lakes versus all external environments"),
    },
  )

  st.markdown("#### " + txt("Estatística da Table 4, FeGenie e outros metais", "Table 4 statistics, FeGenie and other metals"))
  t1, t2, t3 = st.tabs(["Stat-test-KO-Ferro-categ", "Top-Mag-FeGenie", "Outros-metais"])
  with t1:
    stat_fe = load_sheet("table4", "Stat-test-KO-Ferro-categ")
    pathway_file = BASE_DIR / "data" / "final_publication_derived" / "Table4_iron_statistics_KO_with_pathway.csv"
    if pathway_file.exists():
      stat_fe_pathway = pd.read_csv(pathway_file).fillna("")
      st.caption(txt(
        "Os KOs são exibidos com a via/categoria de ferro ao lado do identificador. Os valores estatísticos permanecem exatamente os da Table 4 original.",
        "KOs are displayed with the iron pathway/category beside the identifier. Statistical values remain exactly those from the original Table 4."
      ))
      significance_legend()
      show_table(stat_fe_pathway, "stat_fe_pathway", height=560)
      csv_button(stat_fe_pathway, "Table4_iron_statistics_KO_with_pathway.csv", txt("Baixar testes de ferro com vias", "Download iron tests with pathways"))
    else:
      significance_legend()
      show_table(stat_fe, "stat_fe", height=520)
      csv_button(stat_fe, "Stat-test-KO-Ferro-categ_named_columns.csv", txt("Baixar testes de ferro", "Download iron tests"))
  with t2:
    top_mag = load_sheet("table9", "Top-Mag-FeGenie")
    label = top_mag.columns[0]
    heatmap_then_table(top_mag, label, "Top MAGs by FeGenie iron-metabolism categories", "Top-Mag-FeGenie.csv", "top_mag_fegenie")
    fegenie_detail_file = BASE_DIR / "data" / "final_publication_derived" / "FeGenie_gene_summary_with_pathway.csv"
    if fegenie_detail_file.exists():
      with st.expander(txt("Genes FeGenie com via/categoria", "FeGenie genes with pathway/category"), expanded=False):
        fegenie_detail = pd.read_csv(fegenie_detail_file).fillna("")
        show_table(fegenie_detail, "fegenie_genes_with_pathway", height=520)
        csv_button(fegenie_detail, "FeGenie_gene_summary_with_pathway.csv", txt("Baixar genes FeGenie com vias", "Download FeGenie genes with pathways"))
    fegenie_cat = load_sheet("table3", "Fe-Genie")
    fegenie_cat.columns = [str(c).strip() for c in fegenie_cat.columns]
    if "Categories" in fegenie_cat.columns:
      fegenie_cat = fegenie_cat.rename(columns={"Categories": "Category"})
      publication_boxplot_panel(fegenie_cat, ["Category"], "Category", txt("Boxplots FeGenie por categoria, lagoa e estação", "FeGenie boxplots by category, lake and season"), "supplementary_figure_16_fegenie", normalize_per_sample=False, season_split=True)
  with t3:
    other, other_numeric_cols, other_mapping = other_metals_lagoon_matrix()
    other = with_kegg_links(other, "Function Id")
    other = add_marker_pathway_label(other, "Function Id", "Biologic Role")
    label_col_other = "marker_pathway_label" if "marker_pathway_label" in other.columns else "Function Id"
    other_top = heatmap_row_limit_control(other, "other_metals_all", noun_pt="marcadores", noun_en="markers", default_top=80)
    fig_other = heatmap_figure(other, other_numeric_cols, label_col_other, "Other metal-related KO counts in Amazonian lake samples", top_n=other_top, zscore_rows=False, x_label_map=lake_sample_label_map())
    if fig_other:
      render_plotly_downloadable(fig_other, key="other_metals_lake_samples_heatmap", basename="other_metals_lake_samples_heatmap")
    fig_other_z = heatmap_figure(other, other_numeric_cols, label_col_other, "Other metal-related KO counts in Amazonian lake samples — row z-score", top_n=other_top, zscore_rows=True, x_label_map=lake_sample_label_map())
    if fig_other_z:
      render_plotly_downloadable(fig_other_z, key="other_metals_lake_samples_zscore_heatmap", basename="other_metals_lake_samples_zscore_heatmap")
    metal_file = BASE_DIR / "data" / "final_publication_derived" / "Other_metals_KO_by_metal.csv"
    metal_summary_file = BASE_DIR / "data" / "final_publication_derived" / "Other_metals_KO_summary_by_metal.csv"
    if metal_file.exists():
      metal_kos = pd.read_csv(metal_file).fillna("")
      metal_options = sorted(metal_kos["Metal"].astype(str).unique().tolist())
      selected_metals = st.multiselect(txt("Metais exibidos na lista de KOs", "Metals displayed in the KO list"), metal_options, default=metal_options, key="other_metals_ko_groups")
      metal_view = metal_kos[metal_kos["Metal"].isin(selected_metals)].copy() if selected_metals else metal_kos.copy()
      st.markdown("#### " + txt("KOs organizados por metal", "KOs organized by metal"))
      st.caption(txt(
        "A classificação utiliza exclusivamente o identificador KO, o gene e a descrição funcional da planilha Outros-metais. KOs multimetálicos são repetidos nas categorias pertinentes; a presença do KO indica potencial genético e não uma taxa medida de transformação do metal.",
        "Classification uses only the KO identifier, gene and functional description from the Other-metals sheet. Multi-metal KOs are repeated in the relevant categories; KO presence indicates genetic potential, not a measured metal-transformation rate."
      ))
      if metal_summary_file.exists():
        metal_summary = pd.read_csv(metal_summary_file).fillna("")
        show_table(metal_summary, "other_metals_summary", height=300)
        csv_button(metal_summary, "Other_metals_KO_summary_by_metal.csv", txt("Baixar resumo por metal", "Download summary by metal"))
      show_table(metal_view, "other_metals_ko_by_metal", height=620)
      csv_button(metal_kos, "Other_metals_KO_by_metal.csv", txt("Baixar lista completa de KOs por metal", "Download complete KO-by-metal list"))
    with st.expander(txt("Tabela exata e mapeamento do eixo x", "Exact table and x-axis mapping"), expanded=False):
      show_table(other, "other_metals_lake_samples_table", height=500)
      csv_button(other, "Outros-metais_lake_sample_axis.csv", txt("Baixar Outros-metais", "Download Outros-metais"))
      if not other_mapping.empty:
        show_table(other_mapping, "other_metals_x_axis_mapping", height=300)


def annotate_comparison_direction(df: pd.DataFrame, comparison_col: str | None = None, lfc_col: str | None = None) -> pd.DataFrame:
  out = df.copy()
  if comparison_col is None:
    comparison_col = next((c for c in ["Comparasion", "Comparison", "comparison", "source_sheet"] if c in out.columns), None)
  if lfc_col is None:
    lfc_col = next((c for c in ["log2FoldChange", "LFC", "lfc"] if c in out.columns), None)
  if not comparison_col:
    return out
  def split_comp(x):
    t = str(x).strip().replace(" ", "")
    t = t.replace("-vs", "vs").replace("-VS", "vs")
    for sep in ["vs", "VS", "_", "-"]:
      if sep in t:
        parts = [p for p in t.split(sep) if p]
        if len(parts) >= 2:
          return parts[0], parts[1]
    return "", ""
  lefts, rights = [], []
  for v in out[comparison_col].astype(str):
    left, right = split_comp(v)
    lefts.append(left)
    rights.append(right)
  out["LFC_positive_side"] = lefts
  out["LFC_negative_side"] = rights
  out["Positive side meaning"] = out["LFC_positive_side"].map(lambda x: " / ".join([v for v in parse_group_code(x) if v]) or x)
  out["Negative side meaning"] = out["LFC_negative_side"].map(lambda x: " / ".join([v for v in parse_group_code(x) if v]) or x)
  if lfc_col and lfc_col in out.columns:
    lfc = pd.to_numeric(out[lfc_col], errors="coerce")
    out["Enriched side"] = np.where(lfc >= 0, out["LFC_positive_side"], out["LFC_negative_side"])
    out["Enriched side meaning"] = np.where(lfc >= 0, out["Positive side meaning"], out["Negative side meaning"])
    out["LFC interpretation"] = np.where(
      lfc >= 0,
      "+LFC = enriched in " + out["LFC_positive_side"].astype(str) + " relative to " + out["LFC_negative_side"].astype(str),
      "-LFC = enriched in " + out["LFC_negative_side"].astype(str) + " relative to " + out["LFC_positive_side"].astype(str),
    )
  return out


def comparison_guide_table(df: pd.DataFrame, comparison_col: str = "Comparasion") -> pd.DataFrame:
  if comparison_col not in df.columns:
    return pd.DataFrame()
  cols = [comparison_col, "LFC_positive_side", "Positive side meaning", "LFC_negative_side", "Negative side meaning"]
  guide = df[[c for c in cols if c in df.columns]].drop_duplicates().copy()
  guide = guide.rename(columns={
    comparison_col: "Comparison",
    "LFC_positive_side": "+LFC side",
    "Positive side meaning": "+LFC side meaning",
    "LFC_negative_side": "-LFC side",
    "Negative side meaning": "-LFC side meaning",
  })
  if not guide.empty:
    guide["How to read"] = "+LFC = enriched in " + guide["+LFC side"].astype(str) + "; -LFC = enriched in " + guide["-LFC side"].astype(str)
  return guide.sort_values("Comparison").reset_index(drop=True)


def render_canonical_publication_figure(stem: str, title_pt: str, title_en: str, caption_pt: str, caption_en: str, key_prefix: str) -> None:
  """Display the exact canonical article figure and expose all packaged formats."""
  figure_dir = BASE_DIR / "outputs" / "final_publication_figures"
  png_path = figure_dir / f"{stem}.png"
  if not png_path.exists():
    st.warning(txt(f"Figura canônica não encontrada: {png_path}", f"Canonical figure not found: {png_path}"))
    return
  st.markdown("### " + txt(title_pt, title_en))
  st.image(str(png_path), width="stretch")
  st.caption(txt(caption_pt, caption_en))
  formats = [("PNG", ".png", "image/png"), ("SVG", ".svg", "image/svg+xml"), ("PDF", ".pdf", "application/pdf"), ("TIFF", ".tiff", "image/tiff")]
  cols = st.columns(4)
  for col, (label, ext, mime) in zip(cols, formats):
    fp = figure_dir / f"{stem}{ext}"
    with col:
      if fp.exists():
        st.download_button(
          txt(f"Baixar {label}", f"Download {label}"),
          data=fp.read_bytes(),
          file_name=fp.name,
          mime=mime,
          key=f"{key_prefix}_{label.lower()}",
          width="stretch",
        )


def figure7_lfc_panel():
  st.markdown("### " + txt("Exploração interativa — taxa diferencialmente abundantes", "Interactive exploration — differentially abundant taxa"))
  st.caption(txt(
    "A figura usa a aba Top-6-LFC-Enrich-Arch-Bact da Supplementary Table 2. O usuário escolhe quais comparações deseja visualizar. Valores positivos favorecem o lado esquerdo da comparação; valores negativos favorecem o lado direito.",
    "This figure uses the Top-6-LFC-Enrich-Arch-Bact sheet from Supplementary Table 2. The user chooses which comparisons to visualize. Positive values favor the left side of the comparison; negative values favor the right side."
  ))
  try:
    df = load_sheet("table2", "Top-6-LFC-Enrich-Arch-Bact")
  except Exception as exc:
    st.warning(f"Interactive differential-taxa source table not available: {exc}")
    return
  # The optional Supplementary Table 2 workbook is not distributed in every
  # app bundle. Never interpret another workbook's first sheet as differential
  # taxa data: keep the canonical article figure available and disable only this
  # optional explorer when its exact source schema is absent.
  if df.empty or "Comparasion" not in df.columns or "LFC" not in df.columns:
    st.info(txt(
      "A figura canônica permanece disponível, mas a exploração interativa requer a aba `Top-6-LFC-Enrich-Arch-Bact` da Supplementary Table 2, que não está incluída neste pacote.",
      "The canonical figure remains available, but the interactive explorer requires the `Top-6-LFC-Enrich-Arch-Bact` sheet from Supplementary Table 2, which is not included in this package.",
    ))
    return
  df = annotate_comparison_direction(df, comparison_col="Comparasion", lfc_col="LFC")
  guide = comparison_guide_table(df, "Comparasion")
  with st.expander(txt("O que significa cada comparação", "What each comparison means"), expanded=True):
    st.markdown(txt(
      "Exemplo: se a comparação for `AMD_vs_AMR`, `+LFC` indica enriquecimento em AM-D e `-LFC` indica enriquecimento em AM-R. A interpretação completa aparece na tabela abaixo.",
      "Example: if the comparison is `AMD_vs_AMR`, `+LFC` indicates enrichment in AM-D and `-LFC` indicates enrichment in AM-R. The full interpretation is shown below."
    ))
    show_table(guide, "figure7_comparison_guide", height=260)
  tax_col = "Species/Genus/Phylum" if "Species/Genus/Phylum" in df.columns else next((c for c in df.columns if "Species" in str(c)), df.columns[0])
  c1, c2 = st.columns([0.30, 0.70])
  with c1:
    comps = sorted(df["Comparasion"].dropna().astype(str).unique()) if "Comparasion" in df.columns else []
    selected = st.multiselect(txt("Comparações", "Comparisons"), comps, default=[], key="fig7_comps", placeholder=txt("Selecione uma ou mais comparações", "Select one or more comparisons")) if comps else []
    top_n = st.slider(txt("Top linhas", "Top rows"), 5, min(80, max(5, len(df))), min(40, max(5, len(df))), step=5, key="fig7_top")
  if not selected:
    with c2:
      st.info(txt("Selecione pelo menos uma comparação para explorar esta visualização interativa. Nenhuma comparação fica marcada por padrão.", "Select at least one comparison to explore this interactive view. No comparison is selected by default."))
    return
  work = df[df["Comparasion"].astype(str).isin(selected)].copy()
  work["abs_LFC"] = pd.to_numeric(work["LFC"], errors="coerce").abs() if "LFC" in work.columns else np.nan
  work = work.sort_values("abs_LFC", ascending=False).head(top_n)
  with c2:
    if "LFC" in work.columns and not work.empty:
      fig = px.bar(
        work.sort_values("LFC"),
        x="LFC",
        y=tax_col,
        color="Enriched side",
        orientation="h",
        hover_data=[c for c in ["OTU", "Comparasion", "Positive side meaning", "Negative side meaning", "LFC interpretation", "NCBI Taxonomy rank "] if c in work.columns],
        title=txt("LFC das principais taxa enriquecidas — exploração interativa", "LFC of top enriched taxa — interactive exploration"),
        color_discrete_sequence=["#00796B", "#F9A825", "#1565C0", "#6A1B9A", "#C62828", "#2E7D32"],
      )
      work["bar_label"] = work.get("Comparasion", "").astype(str) + " | enriched: " + work.get("Enriched side meaning", "").astype(str)
      fig.update_traces(text=work.sort_values("LFC")["bar_label"], textposition="outside", cliponaxis=False)
      fig.add_vline(x=0, line_width=1, line_dash="dash", line_color="#263238")
      fig.update_layout(height=max(560, 24 * len(work) + 220), margin=dict(l=10, r=10, t=80, b=30), legend=dict(orientation="h", y=1.04, x=0))
      render_plotly_downloadable(fig, key="figure7_lfc_selected_comparisons", basename="figure7_lfc_selected_comparisons")
  show_table(work, "figure7_lfc_table", height=480)
  csv_button(work, "interactive_LFC_differential_taxa.csv", txt("Baixar dados da exploração interativa", "Download interactive-explorer data"))



def render_top_differential_season(sheet_name: str, season_title: str, key_prefix: str):
  """Render a curated dry/rainy KO differential-abundance chart and its source table."""
  try:
    df = load_sheet("table5", sheet_name)
  except Exception as exc:
    st.error(txt(f"Não foi possível carregar {sheet_name}: {exc}", f"Could not load {sheet_name}: {exc}"))
    return pd.DataFrame()
  if df.empty:
    st.warning(txt(f"A aba {sheet_name} está vazia.", f"Sheet {sheet_name} is empty."))
    return df

  # Workbooks may contain duplicate 'Tools' headers, which pandas renames as
  # Tools.1/Tools.2. Keep every evidence column and normalize essential names.
  normalized = {str(c).strip().lower().replace(" ", ""): c for c in df.columns}
  otu_col = next((normalized[k] for k in normalized if k in {"otu", "ko", "keggorthology"}), None)
  metab_col = next((normalized[k] for k in normalized if k in {"metabolism", "metabolicpathway", "pathway"}), None)
  lfc_col = next((normalized[k] for k in normalized if k in {"log2foldchange", "log2fc", "lfc"}), None)
  comp_col = next((normalized[k] for k in normalized if k in {"comparasion", "comparison", "contrast"}), None)
  if otu_col and otu_col != "OTU":
    df = df.rename(columns={otu_col: "OTU"})
  if metab_col and metab_col != "Metabolism":
    df = df.rename(columns={metab_col: "Metabolism"})
  if lfc_col and lfc_col != "log2FoldChange":
    df = df.rename(columns={lfc_col: "log2FoldChange"})
  if comp_col and comp_col != "Comparasion":
    df = df.rename(columns={comp_col: "Comparasion"})
  if "OTU" not in df.columns:
    df["OTU"] = df.index.astype(str)
  if "Metabolism" not in df.columns:
    df["Metabolism"] = ""
  if "Comparasion" not in df.columns:
    df["Comparasion"] = sheet_name
  if "log2FoldChange" not in df.columns:
    st.warning(txt(f"A aba {sheet_name} não contém log2FoldChange.", f"Sheet {sheet_name} does not contain log2FoldChange."))
    show_table(df, f"{key_prefix}_table")
    return df

  df = annotate_comparison_direction(df, comparison_col="Comparasion", lfc_col="log2FoldChange")
  plot_df = df.copy()
  plot_df["log2FoldChange"] = pd.to_numeric(plot_df["log2FoldChange"], errors="coerce")
  plot_df = plot_df.dropna(subset=["log2FoldChange"])
  if plot_df.empty:
    st.warning(txt("Não há valores numéricos de log2FoldChange para desenhar.", "There are no numeric log2FoldChange values to plot."))
    show_table(df, f"{key_prefix}_table")
    return df

  max_available = int(min(100, len(plot_df)))
  min_n = 5 if max_available >= 5 else 1
  default_n = min(60, max_available)
  top_n = st.slider(
    txt("Número de KOs/táxons diferenciais mostrados", "Number of differential KOs/taxa displayed"),
    min_n, max_available, default_n, step=1, key=f"{key_prefix}_top_n",
  )
  plot_df["abs_log2FoldChange"] = plot_df["log2FoldChange"].abs()
  plot_df = plot_df.sort_values("abs_log2FoldChange", ascending=False).head(int(top_n)).sort_values("log2FoldChange")
  plot_df["otu_label"] = plot_df["OTU"].astype(str) + " | " + plot_df["Metabolism"].fillna("").astype(str)
  if "Enriched side meaning" not in plot_df.columns:
    plot_df["Enriched side meaning"] = np.where(plot_df["log2FoldChange"] >= 0, "first group", "second group")
  if "Negative side meaning" not in plot_df.columns:
    plot_df["Negative side meaning"] = "second group"
  if "Positive side meaning" not in plot_df.columns:
    plot_df["Positive side meaning"] = "first group"
  plot_df["Enriched relative to"] = np.where(
    plot_df["log2FoldChange"] >= 0,
    plot_df["Enriched side meaning"].astype(str) + " relative to " + plot_df["Negative side meaning"].astype(str),
    plot_df["Enriched side meaning"].astype(str) + " relative to " + plot_df["Positive side meaning"].astype(str),
  )

  evidence_cols = [c for c in plot_df.columns if str(c).strip().lower().startswith("tools")]
  hover_cols = [c for c in ["OTU", "Metabolism", "Comparasion", "Enriched side", "Enriched side meaning", "Enriched relative to", "LFC interpretation"] if c in plot_df.columns] + evidence_cols
  customdata = plot_df[hover_cols].fillna("").astype(str).to_numpy() if hover_cols else None
  color_col = "Enriched side" if "Enriched side" in plot_df.columns else None
  color_map = {
    "Positive logFC / enriched in first group": "#1565C0",
    "Negative logFC / enriched in second group": "#C62828",
    "Higher in first group": "#1565C0",
    "Higher in second group": "#C62828",
  }
  fig = px.bar(
    plot_df, x="log2FoldChange", y="otu_label", color=color_col,
    orientation="h", title=season_title, color_discrete_map=color_map,
  )
  if customdata is not None:
    hover_parts = [f"<br><b>{str(col)}:</b> %{{customdata[{i}]}}" for i, col in enumerate(hover_cols)]
    fig.update_traces(customdata=customdata, hovertemplate="".join(hover_parts) + "<br><b>log2 fold change:</b> %{x:.4f}<extra></extra>")
  fig.add_vline(x=0, line_dash="dash", line_width=1, line_color="#263238")
  fig.update_layout(
    height=max(680, 27 * len(plot_df) + 220),
    yaxis={"categoryorder": "array", "categoryarray": plot_df["otu_label"].tolist()},
    legend=dict(orientation="h", y=1.05, x=0),
    margin=dict(l=310, r=50, t=100, b=80),
    hoverlabel=dict(align="left", font_size=13, namelength=-1),
  )
  bold_axis_layout(fig, x_size=14, y_size=12, title_size=18)
  # Render before the table so the plot can never be hidden behind table-only output.
  render_plotly_downloadable(fig, key=f"{key_prefix}_log2fc_{top_n}", basename=f"{key_prefix}_log2fc")
  st.caption(txt(
    "A figura é construída diretamente da aba selecionada; a tabela completa permanece disponível abaixo e para download.",
    "The figure is built directly from the selected sheet; the complete table remains available below and for download."
  ))
  show_table(df, f"{key_prefix}_table")
  csv_button(df, f"{sheet_name}.csv", txt("Baixar tabela completa", "Download complete table"))
  return df



def _table5_column(df: pd.DataFrame, exact: list[str] | None = None, contains: list[str] | None = None) -> str | None:
  exact = [x.casefold() for x in (exact or [])]
  contains = [x.casefold() for x in (contains or [])]
  for column in df.columns:
    normalized = str(column).strip().casefold()
    if normalized in exact:
      return column
  for column in df.columns:
    normalized = str(column).strip().casefold()
    if any(token in normalized for token in contains):
      return column
  return None


def _table5_looks_like_feature_values(series: pd.Series) -> bool:
  """Detect KO/taxon identifiers stored under a shifted statistical header."""
  values = series.dropna().astype(str).str.strip()
  if values.empty:
    return False
  sample = values.head(40)
  ko_ratio = sample.str.contains(r"\bK\d{5}\b", regex=True, na=False).mean()
  text_ratio = pd.to_numeric(sample, errors="coerce").isna().mean()
  return bool(ko_ratio >= 0.35 or text_ratio >= 0.85)


def _normalize_table5_headers(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
  """Repair Table 5 sheets whose first header was omitted during Excel export.

  Several DESeq2/ALDEx2 sheets contain KO identifiers in the first data column,
  while that column is labelled with the next statistical field and the final
  column is ``Unnamed``. In those sheets every header is shifted one position
  to the left. This function restores the missing Feature header and shifts the
  remaining headers back without modifying any values.
  """
  out = df.copy()
  if out.empty or len(out.columns) < 2:
    return out, False
  columns = [str(c).strip() for c in out.columns]
  first = columns[0].casefold()
  feature_aliases = {"otu", "otus", "ko", "kegg orthology", "feature", "taxon", "unnamed: 0"}
  last_is_unnamed = columns[-1].casefold().startswith("unnamed:")
  shifted = first not in feature_aliases and last_is_unnamed and _table5_looks_like_feature_values(out.iloc[:, 0])
  if not shifted:
    return out, False
  restored = ["Feature"] + columns[:-1]
  # Make duplicate labels deterministic for pandas/Plotly.
  seen: dict[str, int] = {}
  unique = []
  for name in restored:
    count = seen.get(name, 0)
    unique.append(name if count == 0 else f"{name}.{count}")
    seen[name] = count + 1
  out.columns = unique
  return out, True


def _table5_sheet_method(sheet_name: str, df: pd.DataFrame) -> str:
  lower = sheet_name.casefold()
  normalized_columns = {str(c).strip().casefold() for c in df.columns}
  if "aldex" in lower or "effect" in normalized_columns or "diff.btw" in normalized_columns:
    return "ALDEx2"
  if "deseq" in lower or "log2foldchange" in normalized_columns:
    return "DESeq2"
  return "Curated summary"


def _table5_comparison_label(sheet_name: str) -> str:
  raw = str(sheet_name).strip()
  if re.search(r"Top-differential-abundance[-_]?Dry$", raw, flags=re.I):
    return "Dry-season curated comparison"
  if re.search(r"Top-differential-abundance[-_]?(?:Rainy?|Rain)$", raw, flags=re.I):
    return "Rainy-season curated comparison"
  base = re.sub(r"[-_](?:DE?SEq2?|Aldex2)$", "", raw, flags=re.I)
  if re.search(r"vs", base, flags=re.I):
    parts = re.split(r"vs", base, maxsplit=1, flags=re.I)
  else:
    parts = [part for part in re.split(r"[-_]", base) if part]
  if len(parts) >= 2:
    return f"{parts[0]} vs {parts[1]}"
  return raw


def render_table5_comparison_sheet(sheet_name: str) -> pd.DataFrame:
  """Render any DESeq2, ALDEx2 or curated Table 5 sheet consistently."""
  try:
    df = load_sheet("table5", sheet_name).copy()
  except Exception as exc:
    st.error(txt(f"Não foi possível carregar {sheet_name}: {exc}", f"Could not load {sheet_name}: {exc}"))
    return pd.DataFrame()
  if df.empty:
    st.warning(txt("A aba selecionada está vazia.", "The selected sheet is empty."))
    return df

  df, headers_repaired = _normalize_table5_headers(df)
  method = _table5_sheet_method(sheet_name, df)
  comparison = _table5_comparison_label(sheet_name)
  feature_col = _table5_column(df, exact=["OTU", "OTUS", "KO", "Kegg Orthology", "Feature"], contains=["unnamed: 0", "feature", "taxon"])
  metabolism_col = _table5_column(df, exact=["Metabolism"], contains=["metabolism", "pathway"])
  if feature_col is None:
    feature_col = df.columns[0]
  if feature_col != "Feature":
    df = df.rename(columns={feature_col: "Feature"})
  if metabolism_col and metabolism_col != "Metabolism":
    df = df.rename(columns={metabolism_col: "Metabolism"})
  if "Metabolism" not in df.columns:
    df["Metabolism"] = ""
  df["source_sheet"] = sheet_name
  df["method"] = method
  df["comparison"] = comparison

  if method == "DESeq2":
    effect_col = _table5_column(df, exact=["log2FoldChange"], contains=["log2foldchange", "log2fc"])
    effect_label = "log2 fold change"
    p_cols = [c for c in ["pvalue", "padj"] if c in df.columns]
  elif method == "ALDEx2":
    effect_col = _table5_column(df, exact=["effect"], contains=["diff.btw"])
    effect_label = "ALDEx2 effect"
    p_cols = [c for c in ["we.ep", "we.eBH", "wi.ep", "wi.eBH", "overlap"] if c in df.columns]
  else:
    effect_col = _table5_column(df, exact=["log2FoldChange", "LFC", "effect"], contains=["log2foldchange", "diff.btw"])
    effect_label = str(effect_col or "effect")
    p_cols = []

  st.markdown(f"##### `{sheet_name}`")
  m1, m2, m3 = st.columns(3)
  m1.metric(txt("Método", "Method"), method)
  m2.metric(txt("Comparação", "Comparison"), comparison)
  m3.metric(txt("Linhas", "Rows"), len(df))
  if headers_repaired:
    st.info(txt(
      "Os cabeçalhos desta aba estavam deslocados uma coluna no arquivo Excel. O app restaurou Feature/Metabolism e os campos estatísticos sem alterar os valores.",
      "This sheet had one-column-shifted headers in the Excel file. The app restored Feature/Metabolism and the statistical fields without changing values."
    ))

  if effect_col and effect_col in df.columns:
    numeric_effect = pd.to_numeric(df[effect_col], errors="coerce")
    plot_df = df.loc[numeric_effect.notna()].copy()
    plot_df["effect_value"] = numeric_effect.loc[numeric_effect.notna()].astype(float)
    if not plot_df.empty:
      max_available = min(100, len(plot_df))
      min_n = 1 if max_available < 5 else 5
      default_n = min(60, max_available)
      top_n = st.slider(
        txt("Número de linhas no gráfico", "Number of rows in the plot"),
        min_n, max_available, default_n, step=1,
        key=f"table5_generic_top_{re.sub(r'[^A-Za-z0-9]+', '_', sheet_name)}",
      )
      plot_df["abs_effect"] = plot_df["effect_value"].abs()
      plot_df = plot_df.nlargest(int(top_n), "abs_effect").sort_values("effect_value")
      plot_df["feature_label"] = plot_df["Feature"].astype(str)
      nonempty_metabolism = plot_df["Metabolism"].fillna("").astype(str).str.strip()
      plot_df.loc[nonempty_metabolism.ne(""), "feature_label"] += " | " + nonempty_metabolism[nonempty_metabolism.ne("")]
      plot_df["Effect direction"] = np.where(plot_df["effect_value"] >= 0, "Positive", "Negative")
      hover_cols = ["Feature", "Metabolism", "comparison", "method", effect_col] + p_cols
      hover_cols = [c for c in dict.fromkeys(hover_cols) if c in plot_df.columns]
      fig = px.bar(
        plot_df,
        x="effect_value", y="feature_label", color="Effect direction", orientation="h",
        color_discrete_map={"Positive": "#1565C0", "Negative": "#C62828"},
        hover_data=hover_cols,
        title=f"{sheet_name} — {effect_label}",
      )
      fig.add_vline(x=0, line_dash="dash", line_width=1, line_color="#263238")
      fig.update_layout(
        height=max(620, 25 * len(plot_df) + 210),
        margin=dict(l=310, r=40, t=90, b=80),
        legend=dict(orientation="h", y=1.04, x=0),
        yaxis={"categoryorder": "array", "categoryarray": plot_df["feature_label"].tolist()},
      )
      render_plotly_downloadable(
        fig,
        key=f"table5_generic_plot_{re.sub(r'[^A-Za-z0-9]+', '_', sheet_name)}",
        basename=f"Table5_{re.sub(r'[^A-Za-z0-9]+', '_', sheet_name)}",
      )
      if method == "ALDEx2":
        st.caption(txt(
          "Para ALDEx2, o gráfico usa a coluna effect quando disponível. A tabela completa mantém diff.btw, dispersão, intervalos de efeito, overlap e valores esperados de teste. O sinal não é reinterpretado além da orientação registrada na própria aba.",
          "For ALDEx2, the plot uses the effect column when available. The complete table retains diff.btw, dispersion, effect intervals, overlap and expected test values. The sign is not reinterpreted beyond the orientation recorded in the sheet."
        ))
    else:
      st.info(txt("Não há valores de efeito numéricos nesta aba; a tabela continua disponível abaixo.", "There are no numeric effect values in this sheet; the table remains available below."))
  else:
    st.info(txt("Esta aba não possui uma coluna de efeito reconhecível; a tabela completa é exibida.", "This sheet has no recognized effect-size column; the complete table is displayed."))

  show_table(df, f"table5_{re.sub(r'[^A-Za-z0-9]+', '_', sheet_name)}", height=540)
  csv_button(df, f"{sheet_name}.csv".replace("/", "_"), txt("Baixar aba selecionada", "Download selected sheet"))
  return df




def corrected_marker_significance_figures_panel():
  """Show canonical bidirectional Amazonian-versus-external contrast figures."""
  fig_dir = BASE_DIR / "outputs" / "app_supplementary_figures"
  derived = BASE_DIR / "data" / "final_publication_derived"
  st.markdown("#### " + txt("Figuras canônicas: contrastes direcionais entre as lagoas e ambientes externos", "Canonical figures: directional contrasts between lakes and external environments"))
  st.info(txt(
    "As Figuras Suplementares 68 e 69 comparam as 20 amostras das lagoas amazônicas com 67 registros externos ricos em ferro. Antes da comparação, as contagens são transformadas em abundância relativa dentro do respectivo painel de marcadores. O painel A mostra os KOs com maior média relativa nas lagoas; o painel B mostra os KOs com maior média relativa nos ambientes externos. O ranking usa o valor absoluto do log2 da razão entre as médias, após filtros mínimos de prevalência e abundância. Como os registros externos pertencem a estudos e camadas ômicas diferentes, os contrastes são descritivos e não são apresentados como testes de significância.",
    "Supplementary Figures 68 and 69 compare the 20 Amazonian-lake samples with 67 external iron-rich records. Counts are converted to relative abundance within the corresponding marker panel before comparison. Panel A shows KOs with a higher mean relative abundance in the lakes; panel B shows KOs with a higher mean in external environments. Ranking uses the absolute log2 ratio of group means after minimum prevalence and abundance filters. Because external records come from different studies and omics layers, these contrasts are descriptive and are not presented as significance tests."
  ))
  panels = [
    ("SupplementaryFigure68_biogeochemical_KO_directional_contrast.png", "Figure8_bidirectional_all_KO_complete_contrast_table.csv", "Supplementary Figure 68 - biogeochemical KO directional contrasts"),
    ("SupplementaryFigure69_iron_KO_directional_contrast.png", "Figure9_bidirectional_iron_KO_complete_contrast_table.csv", "Supplementary Figure 69 - iron-associated KO directional contrasts"),
  ]
  for image_name, csv_name, label in panels:
    image = fig_dir / image_name
    table = derived / csv_name
    if image.exists():
      st.markdown(f"**{label}**")
      st.image(str(image), width="stretch")
      st.caption(txt(
        "Método: abundância relativa dentro do painel de marcadores para cada amostra; média das 20 amostras amazônicas e média dos 67 registros externos; contraste = log2((média amazônica + pseudocontagem)/(média externa + pseudocontagem)). Marcadores exibidos foram detectados em pelo menos 20% do grupo favorecido e apresentaram média mínima de 0,005% nesse grupo. O arquivo completo mantém todos os marcadores, médias, prevalências e o contraste exato.",
        "Method: within-marker-panel relative abundance for each sample; mean across 20 Amazonian samples and mean across 67 external records; contrast = log2((Amazonian mean + pseudocount)/(external mean + pseudocount)). Displayed markers were detected in at least 20% of the favoured group and had a minimum mean of 0.005% in that group. The complete file retains every marker, group means, prevalence and exact contrast."
      ))
      if table.exists():
        st.download_button(txt("Baixar tabela completa do contraste", "Download complete contrast table"), table.read_bytes(), file_name=table.name, mime="text/csv", key=f"download_{csv_name}")


def differential_tab():
  st.subheader(txt("Abundância diferencial e testes estatísticos", "Differential abundance and statistical tests"))
  st.info(txt(
    "Esta página contém explorações interativas, tabelas de testes dentro das lagoas e as Figuras Suplementares 68 e 69 de contraste descritivo bidirecional entre as lagoas e ambientes externos. Os resultados DESeq2 dentro das lagoas permanecem disponíveis nas tabelas e na Figura 7; os contrastes entre estudos não são tratados como testes inferenciais.",
    "This page contains interactive exploration, within-lake statistical tables and Supplementary Figures 68 and 69 showing bidirectional descriptive contrasts between the lakes and external environments. Within-lake DESeq2 results remain available in the tables and Figure 6; cross-study contrasts are not treated as inferential tests."
  ))
  significance_legend()
  figure7_lfc_panel()
  st.divider()
  st.markdown("#### " + txt("Comparações sazonais da Supplementary Table 5", "Seasonal comparisons from Supplementary Table 5"))
  season_choice = st.radio(txt("Estação exibida", "Displayed season"), ["Dry", "Rainy"], horizontal=True, key="table5_season_selector", format_func=lambda value: txt("Seca", "Dry") if value == "Dry" else txt("Chuvosa", "Rainy"))
  seasonal_slot = st.empty()
  with seasonal_slot.container():
    if season_choice == "Dry":
      render_top_differential_season("Top-differential-abundance_Dry", txt("Top differential abundance — dry season", "Top differential abundance — dry season"), "diff_season_active")
    else:
      render_top_differential_season("Top-differential-abundance-Rain", txt("Top differential abundance — rainy season", "Top differential abundance — rainy season"), "diff_season_active")
  st.markdown("#### " + txt("Testes por categoria metabólica", "Metabolic-category tests"))
  t3, t4 = st.tabs(["T-test KO metabolism category", "Kruskal KO metabolism category"])
  with t3:
    df = load_sheet("table4", "T-test-KO-metabolism-category")
    show_table(df, "ttest_ko")
    csv_button(df, "T-test-KO-metabolism-category.csv", "Baixar T-test")
  with t4:
    df = load_sheet("table4", "Kruskal-t-KO-metabolism-categ")
    show_table(df, "kruskal_ko")
    csv_button(df, "Kruskal-t-KO-metabolism-categ.csv", "Baixar Kruskal")
  st.markdown("#### " + txt("Abrir qualquer comparação DESeq2/ALDEx2 da Supplementary Table 5", "Open any DESeq2/ALDEx2 comparison from Supplementary Table 5"))
  st.caption(txt("Todas as abas exibem a tabela completa. DESeq2 usa log2FoldChange; ALDEx2 usa effect ou diff.btw.", "Every sheet displays the complete table. DESeq2 uses log2FoldChange; ALDEx2 uses effect or diff.btw."))
  all_sheets = excel_sheet_names("table5")
  sheet = st.selectbox(txt("Escolha uma aba da Table 5", "Choose a Table 5 sheet"), all_sheets, key="table5_any_sheet")
  render_table5_comparison_sheet(sheet)
  st.divider()
  corrected_marker_significance_figures_panel()


def bvbrc_public_panel(selected_mag: str, public_link: dict):
  """Display official BV-BRC links and explain the app-native internal viewer."""
  cmag = canonical_mag_id(selected_mag)
  genome_id = str(public_link.get("BV-BRC Genome ID", "")).strip() if public_link else ""
  workspace_url = str(public_link.get("Workspace MAG URL", "")).strip() if public_link else ""
  if not workspace_url:
    workspace_url = bvbrc_workspace_mag_url(cmag)
  st.markdown("#### " + txt("Visualização pública BV-BRC integrada", "Integrated public BV-BRC view"))
  st.caption(txt(
    "Use o Annotation ID/BV-BRC Genome ID para abrir as abas oficiais do BV-BRC. A visualização interna de features/organização genômica é feita abaixo com API pública ou arquivos locais, sem depender de iframe.",
    "Use the Annotation ID/BV-BRC Genome ID to open official BV-BRC tabs. The internal feature/genome-organization view below uses the public API or local files and does not depend on iframes."
  ))
  if not genome_id:
    organism_folder_url = str(public_link.get("Workspace organism folder URL", "")).strip() if public_link else ""
    st.warning(txt(
      "Ainda não há Annotation ID público para este MAG em data/bvbrc_public_links.csv. Sem esse ID, o app não inventa feature table nem organização genômica; ele mostra apenas os caminhos públicos esperados e aguarda o ID ou arquivos locais exportados.",
      "There is not yet a public Annotation ID for this MAG in data/bvbrc_public_links.csv. Without this ID, the app does not invent a feature table or genome organization; it only shows the expected public paths and waits for the ID or local exported files."
    ))
    st.link_button("Open expected BV-BRC workspace MAG folder", workspace_url)
    if organism_folder_url:
      st.link_button("Open expected BV-BRC organism folder", organism_folder_url)
    st.code("\n".join([u for u in [workspace_url, organism_folder_url] if u]), language="text")
    return

  tab_links = bvbrc_genome_tab_links(genome_id)
  overview_url = tab_links.get("Overview", bvbrc_genome_url_from_id(genome_id))
  browser_url = str(public_link.get("Genome Browser URL", "")).strip() or tab_links.get("Genome Browser locus", "")
  st.success(txt(f"BV-BRC Annotation ID detected: {genome_id}", f"BV-BRC Annotation ID detected: {genome_id}"))
  top_cols = st.columns([0.20, 0.20, 0.20, 0.20, 0.20])
  with top_cols[0]: st.link_button("Overview", overview_url)
  with top_cols[1]: st.link_button("Genome Browser", browser_url or tab_links.get("Genome Browser", overview_url))
  with top_cols[2]: st.link_button("Sequences", tab_links.get("Sequences", overview_url))
  with top_cols[3]: st.link_button("Features", tab_links.get("Features", overview_url))
  with top_cols[4]: st.link_button("Proteins", tab_links.get("Proteins", overview_url))

  with st.expander(txt("Todas as abas oficiais BV-BRC", "All official BV-BRC tabs"), expanded=True):
    link_rows = []
    for label, url in tab_links.items():
      if label == "Genome Browser locus" and browser_url:
        url = browser_url
      link_rows.append({"BV-BRC tab": label, "URL": url})
    links_df = pd.DataFrame(link_rows)
    show_table(links_df, f"bvbrc_tab_links_{cmag}", height=360)
    csv_button(links_df, f"{cmag.replace('.', '_')}_bvbrc_tab_links.csv", "Download BV-BRC tab links")

  view_options = ["Overview", "Genome Browser", "Sequences", "Features", "Proteins", "Protein Structures", "Specialty Genes", "Domains and Motifs", "Protein Families", "Pathways", "Subsystems"]
  selected_view = st.selectbox(txt("Selecionar aba BV-BRC para visualizar", "Select BV-BRC tab to preview"), view_options, index=0, key=f"bvbrc_embed_view_{cmag}")
  embed_url = browser_url if selected_view == "Genome Browser" and browser_url else tab_links.get(selected_view, overview_url)
  st.link_button(txt("Abrir esta aba no BV-BRC", "Open this BV-BRC tab"), embed_url)
  st.info(txt(
    "O BV-BRC frequentemente bloqueia incorporação por iframe. Por isso, esta versão usa links oficiais para as abas BV-BRC e, nas abas Summary/Feature table/Genome organization abaixo, monta uma visualização interna a partir da API pública ou dos arquivos locais exportados.",
    "BV-BRC often blocks iframe embedding. This version therefore uses official links for BV-BRC tabs and, in the Summary/Feature table/Genome organization tabs below, builds an internal view from the public API or from local exported files."
  ))

def bvbrc_public_downloads_and_tables(selected_mag: str, public_link: dict):
  if not public_link:
    return pd.DataFrame(), pd.DataFrame()
  genome_id = str(public_link.get("BV-BRC Genome ID", "")).strip()
  if not genome_id:
    return pd.DataFrame(), pd.DataFrame()
  cmag = canonical_mag_id(selected_mag)
  st.markdown("##### " + txt("Dados públicos BV-BRC deste MAG", "Public BV-BRC data for this MAG"))
  genome_api = str(public_link.get("Genome Summary API URL", "")).strip() or bvbrc_api_url("genome", genome_id)
  feature_api = str(public_link.get("Feature Table API URL", "")).strip() or bvbrc_api_url("features", genome_id)
  api_links = pd.DataFrame([
    {"Data type": "Genome summary", "URL": genome_api},
    {"Data type": "Feature table", "URL": feature_api},
  ])
  show_table(api_links, f"bvbrc_api_links_{cmag}", height=150)
  summary_df = pd.DataFrame()
  features_df = pd.DataFrame()
  auto = st.checkbox(txt("Carregar automaticamente resumo e features públicas", "Automatically load public summary and features"), value=False, key=f"auto_bvbrc_{cmag}")
  load_now = st.button(txt("Carregar dados públicos do BV-BRC", "Load public BV-BRC data"), key=f"load_public_bvbrc_{cmag}")
  if auto or load_now:
    with st.spinner(txt("Consultando BV-BRC...", "Querying BV-BRC...")):
      ok1, summary_df, msg1 = fetch_bvbrc_json(genome_api)
      ok2, features_df, msg2 = fetch_bvbrc_json(feature_api)
    if ok1:
      st.session_state[public_bvbrc_summary_key(cmag)] = summary_df
      st.success(msg1)
      show_table(summary_df, f"public_bvbrc_summary_{cmag}", height=240)
      csv_button(summary_df, f"{cmag}_BV_BRC_public_genome_summary.csv".replace(".", "_"), "Download public genome summary")
    else:
      st.warning(msg1)
    if ok2:
      features_df = normalize_public_feature_table(features_df)
      st.session_state[public_bvbrc_features_key(cmag)] = features_df
      st.success(msg2)
      summary_cols = st.columns(4)
      if "type" in features_df.columns:
        summary_cols[0].metric("Feature types", features_df["type"].nunique())
      summary_cols[1].metric("Features", f"{len(features_df):,}")
      if "contig_id" in features_df.columns:
        summary_cols[2].metric("Contigs", features_df["contig_id"].nunique())
      if "function" in features_df.columns:
        summary_cols[3].metric("Annotated functions", features_df["function"].replace("", pd.NA).dropna().nunique())
      show_table(features_df, f"public_bvbrc_features_{cmag}", height=560)
      csv_button(features_df, f"{cmag}_BV_BRC_public_features.csv".replace(".", "_"), "Download public BV-BRC features")
    else:
      st.warning(msg2)
  return summary_df, features_df


def public_bvbrc_summary_key(cmag: str) -> str:
  return f"bvbrc_public_summary_{cmag}"


def public_bvbrc_features_key(cmag: str) -> str:
  return f"bvbrc_public_features_{cmag}"


def _safe_df(value) -> pd.DataFrame:
  """Normalize None/invalid objects to an empty DataFrame before .empty checks."""
  return value if isinstance(value, pd.DataFrame) else pd.DataFrame()


def session_df(key: str) -> pd.DataFrame:
  return _safe_df(st.session_state.get(key))


def load_public_bvbrc_data(selected_mag: str, public_link: dict, force: bool = False, show_messages: bool = True) -> tuple[pd.DataFrame, pd.DataFrame]:
  """Load BV-BRC genome summary and feature table into session state.

  BV-BRC does not reliably allow iframe embedding. This helper powers the
  internal app view by reading the public JSON/TSV API when a Genome ID exists.
  """
  cmag = canonical_mag_id(selected_mag)
  genome_id = str(public_link.get("BV-BRC Genome ID", "")).strip() if public_link else ""
  summary_key = public_bvbrc_summary_key(cmag)
  features_key = public_bvbrc_features_key(cmag)
  cached_summary = session_df(summary_key)
  cached_features = session_df(features_key)
  if not genome_id:
    if show_messages:
      st.warning(txt(
        "Não há BV-BRC Genome ID/Annotation ID para montar uma visualização interna por API. Adicione o ID em data/bvbrc_public_links.csv ou inclua arquivos locais exportados pelo BV-BRC em Annotation/MAGx/.",
        "There is no BV-BRC Genome ID/Annotation ID to build an internal API view. Add the ID to data/bvbrc_public_links.csv or include local files exported from BV-BRC under Annotation/MAGx/."
      ))
    return cached_summary, cached_features
  if not force and (not cached_summary.empty or not cached_features.empty):
    return cached_summary, cached_features

  genome_api = str(public_link.get("Genome Summary API URL", "")).strip() or bvbrc_api_url("genome", genome_id)
  feature_api = str(public_link.get("Feature Table API URL", "")).strip() or bvbrc_api_url("features", genome_id)
  with st.spinner(txt("Carregando dados públicos do BV-BRC para a visualização interna...", "Loading public BV-BRC data for the internal view...")):
    ok1, summary_df, msg1 = fetch_bvbrc_json(genome_api)
    ok2, features_df, msg2 = fetch_bvbrc_json(feature_api)
  if ok1:
    st.session_state[summary_key] = summary_df
    cached_summary = summary_df
    if show_messages:
      st.success(msg1)
  elif show_messages:
    st.warning(msg1)
  if ok2:
    features_df = normalize_public_feature_table(features_df)
    st.session_state[features_key] = features_df
    cached_features = features_df
    if show_messages:
      st.success(msg2)
  elif show_messages:
    st.warning(msg2)
  return cached_summary, cached_features


def public_contigs_from_feature_table(features: pd.DataFrame) -> pd.DataFrame:
  features = _safe_df(features)
  """Derive a contig table from a BV-BRC public feature table.

  The public feature endpoint usually has feature coordinates but not always a
  separate contig-length table. For internal plotting, the visible length is the
  maximum observed stop coordinate per contig; this is stated in the UI.
  """
  if features.empty or "contig_id" not in features.columns:
    return pd.DataFrame()
  work = features.copy()
  for col in ["start", "stop"]:
    if col in work.columns:
      work[col] = pd.to_numeric(work[col], errors="coerce")
  if not {"start", "stop"}.issubset(work.columns):
    return pd.DataFrame()
  work["coord_max"] = work[["start", "stop"]].max(axis=1)
  contigs = work.dropna(subset=["contig_id", "coord_max"]).groupby("contig_id", as_index=False).agg(
    length_bp=("coord_max", "max"),
    feature_count=("feature_id", "count") if "feature_id" in work.columns else ("coord_max", "count"),
  )
  if contigs.empty:
    return contigs
  contigs["length_bp"] = pd.to_numeric(contigs["length_bp"], errors="coerce").fillna(0).astype(int)
  return contigs.sort_values(["length_bp", "feature_count"], ascending=[False, False]).reset_index(drop=True)


def add_marker_pathway_label(df: pd.DataFrame, marker_col: str, pathway_col: str, out_col: str = "marker_pathway_label") -> pd.DataFrame:
  """Create compact labels that always show marker + metabolic pathway/role."""
  work = df.copy()
  marker = work[marker_col].astype(str) if marker_col in work.columns else pd.Series([""] * len(work), index=work.index)
  pathway = work[pathway_col].astype(str) if pathway_col in work.columns else pd.Series([""] * len(work), index=work.index)
  pathway = pathway.replace({"nan": "", "None": ""})
  work[out_col] = np.where(pathway.str.strip().ne(""), marker + " | " + pathway, marker)
  return work


def parse_mag_skip_list(text: str) -> list[int]:
  values: list[int] = []
  for part in str(text or "").replace(";", ",").split(","):
    part = part.strip()
    if not part:
      continue
    try:
      values.append(int(part))
    except Exception:
      continue
  return sorted(set(values))


def clear_annotation_caches() -> None:
  try:
    from src import mag_annotations as _mag_annotations
    for name in ["feature_table_cached", "contig_table_cached", "genome_report_metrics_cached"]:
      cache_clear = getattr(getattr(_mag_annotations, name, None), "cache_clear", None)
      if cache_clear:
        cache_clear()
  except Exception:
    pass
  try:
    st.cache_data.clear()
  except Exception:
    pass


def bvbrc_cli_sync_panel(mag_options: list[str]):
  if not is_admin_authenticated():
    render_admin_only_download_notice("Sincronização BV-BRC CLI")
    st.caption(txt(
      "As anotações já baixadas em `Annotation/MAGx/` permanecem disponíveis para visualização. O app nunca executa `p3-cp` para usuários públicos.",
      "Annotations already downloaded into `Annotation/MAGx/` remain available for viewing. The app never runs `p3-cp` for public users.",
    ))
    return
  st.markdown("#### " + txt("Sincronização automática BV-BRC CLI — admin", "Automatic BV-BRC CLI synchronization — admin"))
  with st.expander(txt("Baixar automaticamente resultados BV-BRC para Annotation/MAGx", "Automatically download BV-BRC results to Annotation/MAGx"), expanded=False):
    st.markdown(txt(
      "Este painel usa `p3-ls` e `p3-cp` do BV-BRC CLI para baixar os resultados do Workspace diretamente para `Annotation/MAG2`, `Annotation/MAG3`, etc. Por padrão, o app **primeiro verifica a pasta local e NÃO baixa novamente** se já encontrar arquivos válidos para o MAG. O app **não armazena sua senha**; faça o login uma vez no terminal com `p3-login mattoslmp` e depois use os botões abaixo.",
      "This panel uses BV-BRC CLI `p3-ls` and `p3-cp` to download Workspace results directly into `Annotation/MAG2`, `Annotation/MAG3`, etc. By default, the app **checks the local folder first and does NOT download again** when valid MAG files already exist. The app **does not store your password**; log in once in the terminal with `p3-login mattoslmp`, then use the buttons below."
    ))
    st.code("p3-login mattoslmp", language="bash")

    status_df = bvbrc_cli_status()
    show_table(status_df, "bvbrc_cli_status", height=190)

    i1, i2 = st.columns([0.52, 0.48])
    with i1:
      if st.button(txt("Mostrar comandos de instalação do BV-BRC CLI", "Show BV-BRC CLI installation commands"), key="show_bvbrc_install_commands"):
        st.code(bvbrc_install_commands_ubuntu(), language="bash")
        st.caption(txt("Também incluí o script `scripts/install_bvbrc_cli_ubuntu.sh` no pacote atualizado.", "I also included `scripts/install_bvbrc_cli_ubuntu.sh` in the updated package."))
    with i2:
      st.info(txt(
        "Em servidores de produção, instale o CLI no sistema/ambiente antes de iniciar o Streamlit. Evite executar `sudo` dentro do app.",
        "On production servers, install the CLI in the system/environment before starting Streamlit. Avoid running `sudo` inside the app."
      ))

    workspace_base = st.text_input(
      txt("Diretório remoto BV-BRC metagenomas", "Remote BV-BRC metagenomes directory"),
      value=st.session_state.get("bvbrc_workspace_base", BVBRC_DEFAULT_WORKSPACE_BASE),
      key="bvbrc_workspace_base",
      help="Exemplo correto: /mattoslmp@patricbrc.org/Lakes-Canga/metagenomas",
    )
    local_annotation_dir = st.text_input(
      txt("Diretório local usado pelo app", "Local directory used by the app"),
      value=st.session_state.get("bvbrc_local_annotation_dir", "Annotation"),
      key="bvbrc_local_annotation_dir",
    )
    st.session_state["bvbrc_auto_sync_selected"] = st.checkbox(
      txt("Ao selecionar um MAG sem pasta local, tentar baixar automaticamente", "When selecting a MAG without a local folder, try to download it automatically"),
      value=bool(st.session_state.get("bvbrc_auto_sync_selected", False)),
      key="bvbrc_auto_sync_selected_checkbox",
    )
    overwrite = st.checkbox(
      txt("Forçar atualização: baixar novamente mesmo se Annotation/MAGx já tiver arquivos locais", "Force update: download again even when Annotation/MAGx already has local files"),
      value=bool(st.session_state.get("bvbrc_overwrite_existing", False)),
      key="bvbrc_overwrite_existing",
      help=txt("Deixe desmarcado em produção. Assim o app só usa p3-cp quando o MAG ainda não tem arquivos válidos locais.", "Keep unchecked in production. This makes the app use p3-cp only when the MAG does not yet have valid local files."),
    )
    if not overwrite:
      st.success(txt(
        "Modo seguro ativo: MAGs já presentes em Annotation/MAGx serão apenas reutilizados; nenhum download será executado para eles.",
        "Safe mode active: MAGs already present in Annotation/MAGx will be reused; no download will run for them."
      ))
    else:
      st.warning(txt(
        "Forçar atualização está ativo: o app pode remover e baixar novamente a pasta local do MAG selecionado.",
        "Force update is active: the app may remove and re-download the local folder for the selected MAG."
      ))

    l1, l2, l3 = st.columns(3)
    with l1:
      if st.button(txt("Listar diretório remoto", "List remote directory"), key="list_bvbrc_remote"):
        with st.spinner(txt("Listando metagenomas no BV-BRC...", "Listing metagenomes in BV-BRC...")):
          res = bvbrc_list_remote_path(workspace_base, timeout=180)
        if res.ok:
          st.success(txt("Diretório remoto acessível.", "Remote directory is accessible."))
          st.code(res.stdout[:5000] or "(empty)", language="text")
        else:
          st.error(txt("Não foi possível listar o diretório remoto.", "Could not list the remote directory."))
          st.code((res.stderr or res.stdout or "No details")[:5000], language="text")
    with l2:
      inv = bvbrc_inventory_local_annotations(local_annotation_dir)
      st.metric(txt("MAGs locais baixados", "Local downloaded MAGs"), len(inv))
    with l3:
      if st.button(txt("Atualizar inventário local", "Refresh local inventory"), key="refresh_bvbrc_local_inventory"):
        clear_annotation_caches()
        st.rerun()

    inv = bvbrc_inventory_local_annotations(local_annotation_dir)
    if not inv.empty:
      show_table(inv, "bvbrc_local_annotation_inventory", height=220)
      csv_button(inv, "bvbrc_local_annotation_inventory.csv", txt("Baixar inventário local", "Download local inventory"))

    mag_labels = [m for m in mag_options if mag_number(m) not in {None, 49}]
    if not mag_labels:
      mag_labels = [f"MAG.{n}" for n in range(2, 51) if n != 49]
    selected_download_mag = st.selectbox(
      txt("MAG para baixar agora", "MAG to download now"),
      mag_labels,
      key="bvbrc_single_mag_to_download",
    )
    b1, b2 = st.columns([0.36, 0.64])
    selected_status = bvbrc_local_annotation_status(selected_download_mag, local_annotation_dir)
    st.caption(txt(
      f"Status local do {canonical_mag_id(selected_download_mag)}: {selected_status.get('reason')} | arquivos exibíveis: {selected_status.get('displayable_files', 0)} | pasta: {selected_status.get('local_path', '')}",
      f"Local status for {canonical_mag_id(selected_download_mag)}: {selected_status.get('reason')} | displayable files: {selected_status.get('displayable_files', 0)} | folder: {selected_status.get('local_path', '')}"
    ))
    with b1:
      if st.button(txt("Verificar e baixar MAG selecionado somente se faltar", "Check and download selected MAG only if missing"), key="download_selected_bvbrc_mag", width="stretch"):
        with st.spinner(txt(f"Verificando arquivos locais e sincronizando {canonical_mag_id(selected_download_mag)} somente se necessário...", f"Checking local files and synchronizing {canonical_mag_id(selected_download_mag)} only if needed...")):
          result = bvbrc_sync_mag_annotation(
            selected_download_mag,
            workspace_base=workspace_base,
            local_annotation_dir=local_annotation_dir,
            overwrite=overwrite,
            timeout=3600,
          )
        if result.ok:
          clear_annotation_caches()
          if result.status == "already_local_no_download":
            st.info(txt(f"{result.mag}: arquivos locais já encontrados. Nenhum download foi feito.", f"{result.mag}: local files already found. No download was executed."))
          else:
            st.success(txt(f"{result.mag} sincronizado: {result.status}", f"{result.mag} synchronized: {result.status}"))
        else:
          st.error(txt(f"Falha ao baixar {result.mag}: {result.status}", f"Failed to download {result.mag}: {result.status}"))
        st.code((result.stderr or result.stdout or result.command)[:5000], language="text")
    with b2:
      st.caption(txt(
        "Os arquivos serão salvos em `Annotation/MAGx/`. Se essa pasta já tiver arquivos locais válidos, o app reutiliza esses arquivos e não chama `p3-cp`, exceto se você marcar Forçar atualização. Se o BV-BRC criar uma subpasta com o nome do organismo, o leitor procura recursivamente e exibe os mesmos tipos de arquivos usados em MAG1.",
        "Files are saved under `Annotation/MAGx/`. If this folder already has valid local files, the app reuses those files and does not call `p3-cp`, unless Force update is checked. If BV-BRC creates an organism-name subfolder, the reader searches recursively and displays the same file types used for MAG1."
      ))

    st.markdown("##### " + txt("Download em lote MAG2–MAG50", "Batch download MAG2–MAG50"))
    r1, r2, r3 = st.columns(3)
    with r1:
      start_mag = st.number_input("MAG inicial", min_value=1, max_value=999, value=2, step=1, key="bvbrc_batch_start_mag")
    with r2:
      end_mag = st.number_input("MAG final", min_value=1, max_value=999, value=50, step=1, key="bvbrc_batch_end_mag")
    with r3:
      skip_text = st.text_input(txt("Pular MAGs", "Skip MAGs"), value="49", key="bvbrc_batch_skip_mags")
    if st.button(txt("Verificar e baixar somente MAGs faltantes no intervalo", "Check and download only missing MAGs in range"), key="download_all_bvbrc_mags", type="primary"):
      skip_set = set(parse_mag_skip_list(skip_text))
      nums = [n for n in range(int(start_mag), int(end_mag) + 1) if n not in skip_set]
      progress = st.progress(0)
      rows = []
      log_box = st.empty()
      for idx, n in enumerate(nums, start=1):
        local_status = bvbrc_local_annotation_status(f"MAG{n}", local_annotation_dir)
        if bool(local_status.get("ready_for_app")) and not overwrite:
          log_box.info(txt(f"MAG{n} já existe localmente ({idx}/{len(nums)}). Pulando download...", f"MAG{n} already exists locally ({idx}/{len(nums)}). Skipping download..."))
        else:
          log_box.info(txt(f"MAG{n} ausente/incompleto localmente ({idx}/{len(nums)}). Baixando com p3-cp...", f"MAG{n} missing/incomplete locally ({idx}/{len(nums)}). Downloading with p3-cp..."))
        result = bvbrc_sync_mag_annotation(
          f"MAG{n}",
          workspace_base=workspace_base,
          local_annotation_dir=local_annotation_dir,
          overwrite=overwrite,
          timeout=3600,
        )
        rows.append(result.as_row())
        progress.progress(idx / max(len(nums), 1))
      clear_annotation_caches()
      sync_df = pd.DataFrame(rows)
      st.session_state["bvbrc_last_sync_df"] = sync_df
      skipped_count = int((sync_df.get("status", pd.Series(dtype=str)).astype(str) == "already_local_no_download").sum()) if not sync_df.empty else 0
      downloaded_count = int((sync_df.get("status", pd.Series(dtype=str)).astype(str) == "downloaded").sum()) if not sync_df.empty else 0
      st.success(txt(
        f"Verificação em lote concluída: {downloaded_count} MAG(s) baixados e {skipped_count} reutilizados localmente sem download.",
        f"Batch check finished: {downloaded_count} MAG(s) downloaded and {skipped_count} reused locally without download."
      ))

    sync_df = st.session_state.get("bvbrc_last_sync_df", pd.DataFrame())
    if isinstance(sync_df, pd.DataFrame) and not sync_df.empty:
      show_table(sync_df, "bvbrc_last_sync_summary", height=280)
      csv_button(sync_df, "bvbrc_last_sync_summary.csv", txt("Baixar resumo da sincronização", "Download sync summary"))
      failed = sync_df[~sync_df["ok"].astype(bool)] if "ok" in sync_df.columns else pd.DataFrame()
      if not failed.empty:
        st.warning(txt(f"{len(failed)} MAG(s) falharam. Veja stderr/status na tabela.", f"{len(failed)} MAG(s) failed. See stderr/status in the table."))

def mags_tab():
  st.subheader(txt("MAGs, genome annotations and article classifications", "MAGs, genome annotations and article classifications"))
  st.markdown(
    txt(
      "Esta é a seção principal da base: ela conecta os MAGs/bins do artigo às classificações taxonômicas, métricas de qualidade, FASTA, GenBank/GBK e resultados de anotação BV-BRC/PATRIC. Prefira usar os Genome IDs públicos do BV-BRC em `data/bvbrc_public_links.csv`; pastas locais `Annotation/MAG1`, `Annotation/MAG2`, ... continuam funcionando como fallback.",
      "This is the main database section: it connects article MAGs/bins to taxonomic classifications, quality metrics, FASTA, GenBank/GBK and BV-BRC/PATRIC annotation outputs. Prefer public BV-BRC Genome IDs in `data/bvbrc_public_links.csv`; local `Annotation/MAG1`, `Annotation/MAG2`, ... folders remain supported as a fallback."
    )
  )

  bins = sort_mags_table(load_sheet("table7", "bins-identificados"))
  annotation_index = list_annotation_folders()
  q = st.text_input(txt("Buscar MAG, classificação ou anotação", "Search MAG, classification or annotation"), "", key="mags_q")
  bins_f = filter_by_text(bins, ["MAG", "classification"], q)

  if not bins_f.empty and "MAG" in bins_f.columns:
    bins_f = bins_f.copy()
    bins_f["annotation_folder"] = bins_f["MAG"].map(lambda x: str(annotation_folder(x).relative_to(ANNOTATION_DIR.parent)) if annotation_folder(x) else "")
    bins_f["FASTA_available"] = bins_f["MAG"].map(lambda x: "yes" if fasta_path_for_mag(x, annotation_folder(x)) else "no")
    bins_f["GBK_available"] = bins_f["MAG"].map(lambda x: "yes" if genbank_path_for_mag(x, annotation_folder(x)) else "no")
    bins_f = sort_mags_table(bins_f)

  cA, cB, cC, cD = st.columns(4)
  cA.metric(txt("MAGs no artigo", "MAGs in article"), len(bins))
  cB.metric(txt("Pastas BV-BRC", "BV-BRC folders"), len(annotation_index))
  cC.metric("FASTA", available_fasta_count())
  cD.metric("GBK/GenBank", available_gbk_count() + len([p for p in ANNOTATION_DIR.rglob('*.gb')]) if ANNOTATION_DIR.exists() else available_gbk_count())

  st.markdown("#### " + txt("Completude, qualidade e acessos ENA dos MAGs", "MAG completeness, quality and ENA accessions"))
  mag_quality_table = BASE_DIR / "outputs" / "kegg_modules" / "MAG_genome_quality_completeness_table.csv"
  mag_quality_html = BASE_DIR / "outputs" / "kegg_modules" / "MAG_genome_quality_completeness_interactive.html"
  if mag_quality_table.exists():
    try:
      magq = pd.read_csv(mag_quality_table)
      show_table(magq, "mag_quality_completeness_table", height=320)
      csv_button(magq, "MAG_genome_quality_completeness_and_ENA_accessions.csv", txt("Baixar tabela de qualidade e acessos ENA dos MAGs", "Download MAG quality and ENA accession table"))
    except Exception as exc:
      st.warning(txt(f"Tabela de completude dos MAGs não pôde ser lida: {exc}", f"MAG completeness table could not be read: {exc}"))
  if mag_quality_html.exists():
    with st.expander(txt("Gráfico interativo de completude/contaminação dos MAGs", "Interactive MAG completeness/contamination chart"), expanded=True):
      components.html(mag_quality_html.read_text(encoding="utf-8", errors="ignore"), height=880, scrolling=True)
      st.download_button(
        txt("Baixar HTML interativo de completude dos MAGs", "Download MAG completeness interactive HTML"),
        data=mag_quality_html.read_bytes(),
        file_name=mag_quality_html.name,
        mime="text/html",
        key="download_mag_completeness_interactive_html",
        width="stretch",
      )

  st.markdown("#### " + txt("MAGs identificados no artigo", "Article MAGs"))
  show_table(bins_f, "bins_identificados", height=420)
  csv_button(bins_f, "bins-identificados.csv", txt("Baixar bins-identificados", "Download identified bins"))

  st.markdown("#### " + txt("Seleção do MAG/bin para classificação, download e anotação", "MAG/bin selection for classification, download and annotation"))
  mag_options = sort_mags_table(bins)["MAG"].astype(str).tolist() if "MAG" in bins.columns else []
  bvbrc_cli_sync_panel(mag_options)
  all_label = txt("Todos os MAGs", "All MAGs")
  selected_mag = st.selectbox(txt("Selecione o MAG", "Select MAG"), [all_label] + mag_options, key="selected_mag_annotation")

  if is_all_mags(selected_mag):
    st.info(txt("Selecione um MAG específico para ativar downloads FASTA/GBK e o visualizador BV-BRC/PATRIC.", "Select one specific MAG to enable FASTA/GBK downloads and the BV-BRC/PATRIC viewer."))
  else:
    folder = annotation_folder(selected_mag)
    selected_local_status = bvbrc_local_annotation_status(selected_mag, st.session_state.get("bvbrc_local_annotation_dir", "Annotation"))
    if bool(selected_local_status.get("ready_for_app")):
      # Local assets exist, so never auto-download unless the user explicitly forces a manual update in the sync panel.
      pass
    elif is_admin_authenticated() and not folder and bool(st.session_state.get("bvbrc_auto_sync_selected", False)):
      n_auto = mag_number(selected_mag)
      attempt_key = f"bvbrc_auto_sync_attempted_MAG{n_auto}"
      if n_auto is not None and n_auto != 49 and not st.session_state.get(attempt_key, False):
        st.session_state[attempt_key] = True
        with st.spinner(txt(f"Arquivos locais ausentes para MAG{n_auto}. Baixando automaticamente do BV-BRC com p3-cp...", f"Local files missing for MAG{n_auto}. Automatically downloading from BV-BRC with p3-cp...")):
          auto_result = bvbrc_sync_mag_annotation(
            f"MAG{n_auto}",
            workspace_base=st.session_state.get("bvbrc_workspace_base", BVBRC_DEFAULT_WORKSPACE_BASE),
            local_annotation_dir=st.session_state.get("bvbrc_local_annotation_dir", "Annotation"),
            overwrite=bool(st.session_state.get("bvbrc_overwrite_existing", False)),
            timeout=3600,
          )
        if auto_result.ok:
          clear_annotation_caches()
          folder = annotation_folder(selected_mag)
          st.success(txt(f"{auto_result.mag} baixado automaticamente para {auto_result.local_path}", f"{auto_result.mag} automatically downloaded to {auto_result.local_path}"))
        else:
          st.warning(txt(f"Não foi possível baixar automaticamente {auto_result.mag}: {auto_result.status}", f"Could not automatically download {auto_result.mag}: {auto_result.status}"))
          st.code((auto_result.stderr or auto_result.stdout or auto_result.command)[:3000], language="text")
    public_link = public_link_for_mag(selected_mag)
    fasta = fasta_path_for_mag(selected_mag, folder)
    gbk = genbank_path_for_mag(selected_mag, folder)
    d1, d2, d3 = st.columns(3)
    with d1:
      if fasta:
        st.download_button(txt("Baixar FASTA/contigs", "Download FASTA/contigs"), data=read_text_file(fasta), file_name=fasta.name if fasta.suffix else f"{canonical_mag_id(selected_mag).replace('.', '')}_contigs.fasta", mime="text/plain", key=f"download_fasta_contigs_{safe_filename(selected_mag)}")
      else:
        st.warning(txt("FASTA não encontrado para este MAG.", "FASTA not found for this MAG."))
    with d2:
      if gbk:
        st.download_button(txt("Baixar GenBank/GBK", "Download GenBank/GBK"), data=read_text_file(gbk), file_name=gbk.name, mime="text/plain", key=f"download_genbank_gbk_{safe_filename(selected_mag)}")
      else:
        st.info(txt("GBK/GenBank ainda não incluído para este MAG.", "GBK/GenBank not yet included for this MAG."))
    with d3:
      if folder:
        st.success(txt("Anotação encontrada", "Annotation found") + f": `{folder.relative_to(ANNOTATION_DIR.parent)}`")
      elif public_link:
        st.success(txt("Link público BV-BRC encontrado", "Public BV-BRC link found"))
      else:
        st.info(txt("Sem pasta de anotação BV-BRC/PATRIC para este MAG. Exemplo esperado: `Annotation/MAG1/`.", "No BV-BRC/PATRIC annotation folder for this MAG. Expected example: `Annotation/MAG1/`."))

  st.divider()
  st.markdown("#### " + txt("Classificação taxonômica e acessos ENA dos MAGs", "MAG taxonomic classification and ENA accessions"))
  st.caption(txt(
    "As tabelas abaixo preservam os dados do artigo e apresentam os MAGs em ordem numérica natural: MAG1, MAG2, MAG3, ...",
    "The tables below preserve the article data and display MAGs in natural numeric order: MAG1, MAG2, MAG3, ...",
  ))
  class_specs = [
    ("bin.classification", txt("Classificação taxonômica dos bins e acessos ENA", "Bin taxonomic classification and ENA accessions")),
    ("Gtdbtk.bac120-r89", txt("Classificação GTDB-Tk — Bacteria", "GTDB-Tk classification — Bacteria")),
    ("Gtdbtk.ar122", txt("Classificação GTDB-Tk — Archaea", "GTDB-Tk classification — Archaea")),
    ("(5) rRNA machinery-bins>=70 CI", txt("Classificação Kaiju e maquinaria de rRNA (bins ≥70 CI)", "Kaiju classification and rRNA machinery (bins ≥70 CI)")),
  ]
  class_tabs = st.tabs([title for _, title in class_specs])
  for tab, (sheet_name, table_title) in zip(class_tabs, class_specs):
    with tab:
      st.markdown(f"##### {table_title}")
      df = load_mag_classification_sheet(sheet_name)
      focused = sort_mags_table(filter_table_by_mag(df, selected_mag))
      if focused.empty and not is_all_mags(selected_mag):
        st.warning(txt(f"Nenhum registro encontrado para {canonical_mag_id(selected_mag)} nesta aba.", f"No records found for {canonical_mag_id(selected_mag)} in this sheet."))
      else:
        caption = txt("Mostrando todos os MAGs em ordem numérica", "Showing all MAGs in numeric order") if is_all_mags(selected_mag) else txt(f"Mostrando apenas registros vinculados a {canonical_mag_id(selected_mag)}", f"Showing only records linked to {canonical_mag_id(selected_mag)}")
        st.caption(caption)
        show_table(focused, f"class_{sheet_name}_{selected_mag}", height=520)
        csv_button(focused, f"{sheet_name}_{canonical_mag_id(selected_mag) if not is_all_mags(selected_mag) else 'all_MAGs'}.csv".replace("/", "_"), txt("Baixar tabela filtrada", "Download filtered table"))

  st.divider()
  st.markdown("#### " + txt("Resultados antiSMASH por MAG", "antiSMASH results by MAG"))
  inventory = antismash_inventory()
  with st.expander(txt("Inventário antiSMASH e validação dos nomes", "antiSMASH inventory and filename validation"), expanded=False):
    show_table(inventory, "antismash_inventory", height=440)
    csv_button(inventory, "antiSMASH_MAG_inventory.csv", txt("Baixar inventário antiSMASH", "Download antiSMASH inventory"))
    st.caption(txt(
      "Os MAGs 2, 5, 20, 32, 44, 47 e 49 são marcados explicitamente como sem clusters BGC identificados no conjunto antiSMASH final. Duplicatas enviadas para o mesmo MAG/bin foram resolvidas mantendo o arquivo selecionado no manifesto, e os nomes originais permanecem rastreáveis.",
      "MAGs 2, 5, 20, 32, 44, 47 and 49 are explicitly marked as having no BGC clusters identified in the final antiSMASH set. Duplicate uploads for the same MAG/bin were resolved by retaining the selected archive in the manifest, while original names remain traceable."
    ))
  runs = discover_antismash_runs()
  if not runs:
    st.info(txt(
      "Nenhum index.html do antiSMASH foi encontrado. Extraia cada ZIP em uma pasta própria dentro de data/kegg_modules/mags/gbk_antismash/.",
      "No antiSMASH index.html was found. Extract each ZIP into its own folder under data/kegg_modules/mags/gbk_antismash/."
    ))
  else:
    labels = [str(run["run_name"]) for run in runs]
    default_idx = 0
    if not is_all_mags(selected_mag):
      selected_mag_canonical = canonical_mag_id(selected_mag)
      if selected_mag_canonical:
        for idx, run in enumerate(runs):
          if str(run.get("mag_id")) == selected_mag_canonical:
            default_idx = idx
            break
    selected_run_label = st.selectbox(txt("Execução antiSMASH", "antiSMASH run"), labels, index=default_idx, key="antismash_interactive_run")
    run = runs[labels.index(selected_run_label)]
    st.caption(txt(
      f"Identificador canônico: {run.get('mag_id')}; diretório detectado: {run.get('original_run_name')}.",
      f"Canonical identifier: {run.get('mag_id')}; detected directory: {run.get('original_run_name')}."
    ))
    c1, c2, c3 = st.columns(3)
    with c1:
      st.download_button(
        txt("Baixar execução antiSMASH completa", "Download complete antiSMASH run"),
        data=antismash_run_zip_bytes(run["run_dir"]),
        file_name=f"{run.get('mag_id')}_{run.get('original_run_name')}_antismash.zip".replace(" ", "_"),
        mime="application/zip",
        key=f"download_antismash_run_{selected_run_label}",
        width="stretch",
      )
    with c2:
      if run.get("gbk_path"):
        gbk_path = Path(run["gbk_path"])
        st.download_button("Download antiSMASH GBK", data=gbk_path.read_bytes(), file_name=gbk_path.name, mime="text/plain", key=f"download_antismash_gbk_{selected_run_label}", width="stretch")
    with c3:
      if run.get("fasta_path"):
        fasta_path = Path(run["fasta_path"])
        st.download_button(txt("Baixar FASTA do MAG", "Download MAG FASTA"), data=fasta_path.read_bytes(), file_name=fasta_path.name, mime="text/plain", key=f"download_antismash_fasta_{selected_run_label}", width="stretch")
    show_antismash = st.checkbox(txt("Renderizar relatório antiSMASH dentro do app", "Render antiSMASH report inside the app"), value=True, key=f"show_antismash_html_{selected_run_label}")
    if show_antismash:
      html_report = self_contained_antismash_html(Path(run["run_dir"]))
      if html_report:
        components.html(html_report, height=1000, scrolling=True)
      else:
        st.warning(txt("Não foi possível montar o relatório HTML autocontido.", "The self-contained HTML report could not be assembled."))
    st.caption(txt(
      "Input: diretório completo descompactado do antiSMASH, contendo index.html, regions.js, CSS/JS, GBKs e, quando disponível, input FASTA. Script: src/antismash_viewer.py. Método: identificação canônica MAG.<número>, descoberta recursiva do index.html e incorporação dos assets locais em HTML autocontido. Output: relatório interativo, inventário de disponibilidade, GBK/FASTA e ZIP integral da execução.",
      "Input: complete extracted antiSMASH directory containing index.html, regions.js, CSS/JS, GBKs and, when available, input FASTA. Script: src/antismash_viewer.py. Method: canonical MAG.<number> mapping, recursive index.html discovery and embedding of local assets into self-contained HTML. Output: interactive report, availability inventory, GBK/FASTA and complete run ZIP."
    ))


  if is_all_mags(selected_mag):
    return

  folder = annotation_folder(selected_mag)
  public_link = public_link_for_mag(selected_mag)
  if not folder and not public_link:
    st.divider()
    st.markdown("#### " + txt("Como adicionar anotações BV-BRC/PATRIC", "How to add BV-BRC/PATRIC annotations"))
    st.code(
      "Annotation/\n"
      "  MAG1/\n"
      "    GenomeReport.html\n"
      "    Dehalococcoidia bacterium 2012759.features.txt\n"
      "    Dehalococcoidia bacterium 2012759.xls ou .xlsx\n"
      "    Dehalococcoidia bacterium 2012759.gb\n"
      "    contigs\n"
      "    feature_protein.fasta\n"
      "    feature_dna.fasta\n"
      "\n"
      "Ou registre um link público em data/bvbrc_public_links.csv com MAG, BV-BRC Genome ID e Genome Browser URL.\n",
      language="text",
    )
    return

  st.divider()
  st.markdown("#### BV-BRC/PATRIC annotation viewer")
  if public_link:
    bvbrc_public_panel(selected_mag, public_link)
  a1, a2, a3, a4 = st.tabs([txt("Resumo", "Summary"), "Genome report", "Feature table", txt("Organização genômica", "Genome organization")])

  with a1:
    summary = _safe_df(annotation_summary_table(selected_mag) if folder else None)
    tax = taxonomy_summary(folder) if folder else {}
    features = _safe_df(feature_table(folder) if folder else None)
    contigs = _safe_df(contig_table(folder) if folder else None)
    s1, s2, s3, s4 = st.columns(4)
    s1.metric(txt("Features anotadas", "Annotated features"), len(features))
    s2.metric("Contigs", len(contigs))
    s3.metric(txt("Tamanho total (bp)", "Total size (bp)"), f"{int(contigs['length_bp'].sum()):,}" if not contigs.empty else "NA")
    s4.metric(txt("Categorias funcionais", "Functional categories"), features["functional_category"].nunique() if "functional_category" in features.columns and not features.empty else 0)
    if not summary.empty:
      show_table(summary, "annotation_summary", height=170)
    if tax:
      st.markdown("**" + txt("Taxonomia BV-BRC/PATRIC da anotação", "BV-BRC/PATRIC annotation taxonomy") + ":**")
      for k, v in tax.items():
        st.markdown(f"- **{k}:** {v}")
    public_features_for_summary = pd.DataFrame()
    if public_link:
      _, public_features_for_summary = bvbrc_public_downloads_and_tables(selected_mag, public_link)
      public_features_for_summary = _safe_df(public_features_for_summary)
      if features.empty and not public_features_for_summary.empty:
        features = public_features_for_summary
    stats = feature_stats(features)
    if not stats.empty:
      fig = px.bar(stats[stats["metric"].astype(str).str.startswith("Category:")], x="metric", y="value", title=txt("Resumo funcional da anotação BV-BRC/PATRIC", "BV-BRC/PATRIC functional annotation summary"))
      fig.update_layout(height=420, xaxis_tickangle=-35)
      render_plotly_downloadable(fig, key=f"annotation_functional_summary_{canonical_mag_id(selected_mag)}", basename=f"annotation_functional_summary_{canonical_mag_id(selected_mag)}")
      show_table(stats, "feature_stats", height=300)

  with a2:
    report_df = _safe_df(genome_report_metrics(folder) if folder else None)
    if public_link:
      genome_id = public_link.get("BV-BRC Genome ID", "")
      genome_url = bvbrc_genome_url_from_id(genome_id) if genome_id else public_link.get("Genome Browser URL", "")
      if genome_url:
        st.link_button("Open public BV-BRC genome report", genome_url)
    if not report_df.empty:
      show_table(report_df, "genome_report_metrics", height=460)
      csv_button(report_df, f"{canonical_mag_id(selected_mag)}_GenomeReport_metrics.csv".replace(".", "_"), txt("Baixar métricas do GenomeReport", "Download GenomeReport metrics"))
    report_file = folder / "GenomeReport.html" if folder else None
    if report_file is not None and report_file.exists():
      st.download_button(txt("Baixar GenomeReport.html original", "Download original GenomeReport.html"), data=read_text_file(report_file), file_name=report_file.name, mime="text/html", key=f"download_genome_report_{safe_filename(selected_mag)}")

  with a3:
    if public_link:
      genome_id = public_link.get("BV-BRC Genome ID", "")
      feature_api = public_link.get("Feature Table API URL", "") or (bvbrc_api_url("features", genome_id) if genome_id else "")
      if feature_api:
        st.link_button("Open official BV-BRC feature API", feature_api)
    features = _safe_df(feature_table(folder) if folder else None)
    feature_source = txt("arquivos locais exportados do BV-BRC", "local BV-BRC exported files")
    if features.empty and public_link:
      cmag = canonical_mag_id(selected_mag)
      cached_features = session_df(public_bvbrc_features_key(cmag))
      if cached_features.empty:
        st.info(txt(
          "A tabela local de features não foi encontrada. O app pode montar uma tabela interna usando a API pública do BV-BRC quando o Genome ID/Annotation ID está disponível.",
          "No local feature table was found. The app can build an internal feature table from the BV-BRC public API when a Genome ID/Annotation ID is available."
        ))
        if st.button(txt("Carregar feature table pública dentro do app", "Load public feature table inside the app"), key=f"load_public_features_tab_{canonical_mag_id(selected_mag)}"):
          _, cached_features = load_public_bvbrc_data(selected_mag, public_link, force=True, show_messages=True)
      if not cached_features.empty:
        features = cached_features
        feature_source = "BV-BRC public API"

    if features.empty:
      st.warning(txt(
        "Feature table não disponível dentro do app. Para ativar esta aba, adicione o BV-BRC Genome ID/Annotation ID em data/bvbrc_public_links.csv ou inclua arquivos .features.txt, .xls ou .xlsx exportados pelo BV-BRC em Annotation/MAGx/.",
        "Feature table is not available inside the app. To activate this tab, add the BV-BRC Genome ID/Annotation ID to data/bvbrc_public_links.csv or include .features.txt, .xls or .xlsx files exported from BV-BRC under Annotation/MAGx/."
      ))
    else:
      st.success(txt(f"Feature table interna carregada a partir de: {feature_source}.", f"Internal feature table loaded from: {feature_source}."))
      f1, f2, f3 = st.columns([0.24, 0.28, 0.48])
      with f1:
        types = sorted(features["type"].dropna().astype(str).unique()) if "type" in features.columns else []
        selected_types = st.multiselect("Feature type", types, default=types[:8], key="feat_types") if types else []
      with f2:
        cats = sorted(features["functional_category"].dropna().astype(str).unique()) if "functional_category" in features.columns else []
        selected_cats = st.multiselect("Functional category", cats, default=cats, key="feat_cats") if cats else []
      with f3:
        qf = st.text_input(txt("Buscar função, feature_id, PLfam, PGfam, FIGfam", "Search function, feature_id, PLfam, PGfam, FIGfam"), "", key="feature_search")
      work = features.copy()
      if selected_types and "type" in work.columns:
        work = work[work["type"].astype(str).isin(selected_types)]
      if selected_cats and "functional_category" in work.columns:
        work = work[work["functional_category"].astype(str).isin(selected_cats)]
      if qf:
        search_cols = [c for c in ["feature_id", "patric_id", "function", "aliases", "plfam", "pgfam", "figfam", "evidence_codes", "product"] if c in work.columns]
        work = filter_by_text(work, search_cols, qf)
      show_table(work, "bvbrc_features", height=560)
      csv_button(work, f"{canonical_mag_id(selected_mag)}_BV_BRC_features.csv".replace(".", "_"), txt("Baixar tabela de features filtrada", "Download filtered feature table"))

  with a4:
    if public_link:
      genome_id = public_link.get("BV-BRC Genome ID", "")
      browser_url = public_link.get("Genome Browser URL", "") or (bvbrc_feature_browser_url(genome_id) if genome_id else "")
      if browser_url:
        st.markdown("##### BV-BRC public Genome Browser")
        st.link_button("Open complete BV-BRC Genome Browser", browser_url)
        st.caption(txt(
          "O navegador oficial completo abre no BV-BRC. Dentro do app, a organização genômica é desenhada abaixo usando a tabela pública de features ou os arquivos locais exportados, evitando iframe bloqueado.",
          "The complete official browser opens on BV-BRC. Inside the app, genome organization is drawn below from the public feature table or exported local files, avoiding blocked iframes."
        ))
    features = _safe_df(feature_table(folder) if folder else None)
    contigs = _safe_df(contig_table(folder) if folder else None)
    org_source = txt("arquivos locais exportados do BV-BRC", "local BV-BRC exported files")
    if features.empty and public_link:
      cmag = canonical_mag_id(selected_mag)
      cached_features = session_df(public_bvbrc_features_key(cmag))
      if cached_features.empty:
        st.info(txt(
          "A organização genômica interna precisa da feature table. Carregue a tabela pública do BV-BRC quando houver Genome ID/Annotation ID.",
          "The internal genome-organization plot needs the feature table. Load the public BV-BRC feature table when a Genome ID/Annotation ID is available."
        ))
        if st.button(txt("Carregar features públicas e desenhar organização genômica", "Load public features and draw genome organization"), key=f"load_public_features_org_{canonical_mag_id(selected_mag)}"):
          _, cached_features = load_public_bvbrc_data(selected_mag, public_link, force=True, show_messages=True)
      if not cached_features.empty:
        features = cached_features
        contigs = public_contigs_from_feature_table(features)
        org_source = "BV-BRC public API"
    elif not features.empty and contigs.empty:
      contigs = public_contigs_from_feature_table(features)

    if contigs.empty or features.empty:
      st.warning(txt(
        "Organização genômica não disponível dentro do app porque faltam contigs ou coordenadas de features. Adicione o Genome ID/Annotation ID público ou exporte os arquivos de anotação BV-BRC para Annotation/MAGx/.",
        "Genome organization is not available inside the app because contigs or feature coordinates are missing. Add the public Genome ID/Annotation ID or export BV-BRC annotation files to Annotation/MAGx/."
      ))
    else:
      st.success(txt(f"Organização genômica interna construída a partir de: {org_source}.", f"Internal genome organization built from: {org_source}."))
      if org_source == "BV-BRC public API":
        st.caption(txt(
          "Para dados públicos carregados pela API, o comprimento exibido do contig é o maior coordenada stop observada na feature table pública quando a API não fornece uma tabela separada de contigs.",
          "For public API data, displayed contig length is the largest observed feature stop coordinate when the API does not provide a separate contig-length table."
        ))
      c1, c2 = st.columns([0.42, 0.58])
      with c1:
        top_contigs = contigs.head(120).copy()
        top_contigs["label"] = top_contigs.apply(lambda r: f"{r['contig_id']} | {int(r['length_bp']):,} bp", axis=1)
        selected_contig_label = st.selectbox("Contig", top_contigs["label"].tolist(), key="selected_contig")
        selected_contig = selected_contig_label.split(" | ")[0]
        max_features = st.slider(txt("Máximo de features no desenho", "Maximum features in plot"), 25, 500, 250, step=25, key=f"max_features_genome_plot_{safe_filename(selected_mag)}")
        show_table(contigs.head(50), "contig_lengths", height=330)
      with c2:
        fig = genome_organization_figure(features, contigs, selected_contig, max_features=max_features)
        if fig:
          render_plotly_downloadable(fig, key=f"genome_organization_{canonical_mag_id(selected_mag)}_{selected_contig}", basename=f"genome_organization_{canonical_mag_id(selected_mag)}_{selected_contig}")
        else:
          st.info(txt("Nenhuma feature com coordenadas foi encontrada neste contig.", "No feature with coordinates was found in this contig."))

  st.divider()
  st.markdown("#### " + txt("Tabelas completas de anotação genômica do artigo", "Complete article genome-annotation tables"))
  st.caption(txt(
    "Escolha `ver todos` para mostrar a tabela completa ou selecione um MAG para visualizar apenas as linhas vinculadas ao MAG/bin selecionado.",
    "Choose `view all` to show the complete table or select one MAG to display only rows linked to the selected MAG/bin."
  ))
  table_mag_options = sort_mags_table(bins)["MAG"].astype(str).tolist() if "MAG" in bins.columns else []
  view_all_label = txt("Ver todos", "View all")
  selected_annotation_mag = st.selectbox(
    txt("Filtro das tabelas BGC/FeGenie", "BGC/FeGenie table filter"),
    [view_all_label] + table_mag_options,
    key="complete_annotation_table_mag_filter",
  )
  t1, t2 = st.tabs(["BGC antiSMASH", "FeGenie geneSummary"])
  with t1:
    antismash_index_path = BASE_DIR / "data" / "antiSMASH_MAG_index_manifest.csv"
    antismash_regions_path = BASE_DIR / "data" / "antiSMASH_BGC_region_table_complete_with_no_cluster_MAGs.csv"
    antismash_products_path = BASE_DIR / "data" / "antiSMASH_product_summary.csv"
    if antismash_index_path.exists() and antismash_regions_path.exists():
      index_all = pd.read_csv(antismash_index_path)
      regions_all = pd.read_csv(antismash_regions_path)
      products_all = pd.read_csv(antismash_products_path) if antismash_products_path.exists() else pd.DataFrame()
      index_df = index_all if selected_annotation_mag == view_all_label else filter_table_by_mag(index_all, selected_annotation_mag)
      region_df = regions_all if selected_annotation_mag == view_all_label else filter_table_by_mag(regions_all, selected_annotation_mag)
      bgc_tabs = st.tabs(["MAG index", "BGC regions", "Product summary"])
      with bgc_tabs[0]:
        st.caption(txt(
          f"Manifesto antiSMASH: {len(index_df):,} de {len(index_all):,} MAGs/bins. Os MAGs sem arquivo fornecido foram mantidos como 'sem clusters BGC identificados'.",
          f"antiSMASH manifest: {len(index_df):,} of {len(index_all):,} MAGs/bins. MAGs without a provided archive were retained as 'no BGC clusters identified'."
        ))
        show_table(index_df, "antismash_index_manifest_filtered", height=520)
        csv_button(index_df, f"antiSMASH_MAG_index_manifest_{selected_annotation_mag}.csv".replace(" ", "_").replace("/", "_"), "Download antiSMASH MAG index")
      with bgc_tabs[1]:
        st.caption(txt(
          f"Tabela de regiões BGC antiSMASH: {len(region_df):,} de {len(regions_all):,} linhas.",
          f"antiSMASH BGC-region table: {len(region_df):,} of {len(regions_all):,} rows."
        ))
        show_table(region_df, "antismash_bgc_regions_filtered", height=620)
        csv_button(region_df, f"antiSMASH_BGC_regions_{selected_annotation_mag}.csv".replace(" ", "_").replace("/", "_"), "Download antiSMASH BGC-region table")
      with bgc_tabs[2]:
        st.caption(txt("Resumo dos produtos BGC detectados pelo antiSMASH.", "Summary of antiSMASH-detected BGC products."))
        show_table(products_all, "antismash_product_summary", height=420)
        if not products_all.empty:
          csv_button(products_all, "antiSMASH_product_summary.csv", "Download antiSMASH product summary")
    else:
      df_all = load_sheet("table9", "BGC-Antismash")
      df = df_all if selected_annotation_mag == view_all_label else filter_table_by_mag(df_all, selected_annotation_mag)
      st.caption(txt(
        f"Mostrando {len(df):,} de {len(df_all):,} linhas.",
        f"Showing {len(df):,} of {len(df_all):,} rows."
      ))
      show_table(df, "bgc_filtered", height=520)
      csv_button(df, f"antiSMASH_Annotation_table_{selected_annotation_mag}.csv".replace(" ", "_").replace("/", "_"), "Download antiSMASH annotation table")
  with t2:
    df_all = load_sheet("table9", "FeGenie-geneSummary")
    df = df_all if selected_annotation_mag == view_all_label else filter_table_by_mag(df_all, selected_annotation_mag)
    st.caption(txt(
      f"Mostrando {len(df):,} de {len(df_all):,} linhas.",
      f"Showing {len(df):,} of {len(df_all):,} rows."
    ))
    show_table(df, "fegenie_gene_filtered", height=520)
    csv_button(df, f"FeGenie-geneSummary_{selected_annotation_mag}.csv".replace(" ", "_").replace("/", "_"), "Download FeGenie geneSummary")



def parse_group_code(code: str):
  code = str(code).strip().upper().replace(" ", "")
  mapping = {
    "TIAD": ("TIA", "Dry"), "TIAR": ("TIA", "Rainy"),
    "AMD": ("AM", "Dry"), "AMR": ("AM", "Rainy"),
    "TID": ("TI", "Dry"), "TIR": ("TI", "Rainy"),
    "VID": ("VI", "Dry"), "VIR": ("VI", "Rainy"),
  }
  return mapping.get(code, (None, None))


def carajas_ko_lake_season_summary(df: pd.DataFrame) -> pd.DataFrame:
  sample_cols = []
  for c in df.columns:
    cc = str(c).strip()
    if re.match(r"^(AM|TIA|TI|VI)\.P\d+\.(D|R)$", cc):
      sample_cols.append(c)
  rows = []
  for c in sample_cols:
    cc = str(c).strip()
    m = re.match(r"^(AM|TIA|TI|VI)\.P\d+\.(D|R)$", cc)
    if not m:
      continue
    lake = m.group(1)
    season = "Dry" if m.group(2) == "D" else "Rainy"
    values = pd.to_numeric(df[c], errors="coerce").fillna(0)
    for idx, value in values.items():
      rows.append({
        "lake": lake,
        "season": season,
        "sample_column": cc,
        "KO": df.loc[idx, "KO"] if "KO" in df.columns else "",
        "Metabolism": df.loc[idx, "Metabolism"] if "Metabolism" in df.columns else "",
        "KO description": df.loc[idx, "KO description"] if "KO description" in df.columns else "",
        "count": float(value),
      })
  long = pd.DataFrame(rows)
  if long.empty:
    return long
  summary = long.groupby(["lake", "season", "KO", "Metabolism", "KO description"], as_index=False).agg(
    mean_count=("count", "mean"),
    total_count=("count", "sum"),
    n_samples=("sample_column", "nunique"),
    max_count=("count", "max"),
  )
  return summary.sort_values(["lake", "season", "mean_count"], ascending=[True, True, False]).reset_index(drop=True)


def differential_significance_evidence() -> pd.DataFrame:
  rows = []
  try:
    sheets = excel_sheet_names("table5")
  except Exception:
    return pd.DataFrame()
  for sh in sheets:
    if "deseq" not in sh.lower():
      continue
    prefix = sh.split("-")[0]
    parts = prefix.split("_")
    if len(parts) < 2:
      continue
    left, right = parts[0], parts[1]
    left_lake, left_season = parse_group_code(left)
    right_lake, right_season = parse_group_code(right)
    if not left_lake or not right_lake:
      continue
    try:
      df = load_sheet("table5", sh)
    except Exception:
      continue
    ko_col = None
    for c in df.columns:
      vals = df[c].astype(str).str.extract(r"(K\d{5}:?\s*\w*)", expand=False)
      if vals.notna().sum() >= max(1, min(5, len(df)//8)):
        ko_col = c
        break
    if ko_col is None:
      continue
    p_col = next((c for c in df.columns if str(c).lower() == "pvalue"), None)
    padj_col = next((c for c in df.columns if str(c).lower() == "padj"), None)
    lfc_col = next((c for c in df.columns if "log2foldchange" in str(c).lower()), None)
    metab_col = next((c for c in df.columns if "metabolism" in str(c).lower() and c != ko_col), None)
    for _, r in df.iterrows():
      ko = str(r.get(ko_col, ""))
      if not re.search(r"K\d{5}", ko):
        continue
      lfc = pd.to_numeric(pd.Series([r.get(lfc_col, None)]), errors="coerce").iloc[0] if lfc_col else None
      if pd.isna(lfc):
        enriched_lake, enriched_season, enriched_group = None, None, ""
      elif float(lfc) >= 0:
        enriched_lake, enriched_season, enriched_group = left_lake, left_season, left
      else:
        enriched_lake, enriched_season, enriched_group = right_lake, right_season, right
      pvalue = pd.to_numeric(pd.Series([r.get(p_col, None)]), errors="coerce").iloc[0] if p_col else np.nan
      padj = pd.to_numeric(pd.Series([r.get(padj_col, None)]), errors="coerce").iloc[0] if padj_col else np.nan
      rows.append({
        "source_sheet": sh,
        "comparison": f"{left} vs {right}",
        "enriched_group": enriched_group,
        "lake": enriched_lake,
        "season": enriched_season,
        "KO": ko,
        "Metabolism": r.get(metab_col, "") if metab_col else "",
        "log2FoldChange": float(lfc) if not pd.isna(lfc) else np.nan,
        "pvalue": float(pvalue) if not pd.isna(pvalue) else np.nan,
        "padj": float(padj) if not pd.isna(padj) else np.nan,
        "significance_by_pvalue": p_to_stars(pvalue),
        "method": "DESeq2",
      })
  out = pd.DataFrame(rows)
  if out.empty:
    return out
  return out.sort_values(["pvalue", "padj"], na_position="last").reset_index(drop=True)


def top_differential_evidence_from_curated_tables() -> pd.DataFrame:
  rows = []
  for sh, season_label in [("Top-differential-abundance_Dry", "Dry"), ("Top-differential-abundance-Rain", "Rainy")]:
    try:
      df = load_sheet("table5", sh)
    except Exception:
      continue
    for _, r in df.iterrows():
      comp = str(r.get("Comparasion", ""))
      if "vs" not in comp:
        continue
      left, right = comp.split("vs", 1)
      left_lake, left_season = parse_group_code(left)
      right_lake, right_season = parse_group_code(right)
      lfc = pd.to_numeric(pd.Series([r.get("log2FoldChange", None)]), errors="coerce").iloc[0]
      if pd.isna(lfc):
        enriched_lake, enriched_season, enriched_group = None, None, ""
      elif float(lfc) >= 0:
        enriched_lake, enriched_season, enriched_group = left_lake, left_season, left
      else:
        enriched_lake, enriched_season, enriched_group = right_lake, right_season, right
      rows.append({
        "season_table": season_label,
        "comparison": comp,
        "enriched_group": enriched_group,
        "lake": enriched_lake,
        "season": enriched_season,
        "KO": r.get("OTU", ""),
        "Metabolism": r.get("Metabolism", ""),
        "log2FoldChange": float(lfc) if not pd.isna(lfc) else np.nan,
        "Tools": r.get("Tools", ""),
        "Additional tool/evidence": r.get("Tools.1", r.get("Tools.2", "")),
      })
  return pd.DataFrame(rows)


def ko_abundance_significance_panel(df: pd.DataFrame):
  st.markdown("### " + txt("KOs mais abundantes e evidência diferencial por lagoa/estação", "Most abundant KOs and differential evidence by lake/season"))
  st.caption(txt(
    "A abundância é calculada diretamente das contagens da aba Res-KO-Biomarkers-C-N-S-all environmental data. A significância é lida das tabelas diferenciais DESeq2 quando existe p-value; a tabela curada Top-differential-abundance é mostrada como evidência diferencial adicional.",
    "Abundance is calculated directly from counts in Res-KO-Biomarkers-C-N-S-all environmental data. Significance is read from DESeq2 differential tables when p-values are available; the curated Top-differential-abundance table is shown as additional differential evidence."
  ))
  abundance = carajas_ko_lake_season_summary(df)
  evidence = differential_significance_evidence()
  curated = top_differential_evidence_from_curated_tables()
  c1, c2, c3 = st.columns([0.26, 0.26, 0.48])
  with c1:
    lake_options = sorted(abundance["lake"].dropna().unique()) if not abundance.empty else []
    selected_lakes = st.multiselect(txt("Lagoas", "Lakes"), lake_options, default=lake_options, key="ko_lake_sel")
  with c2:
    season_options = ["Dry", "Rainy"]
    season_display = {"Dry": txt("Seca", "Dry"), "Rainy": txt("Chuva", "Rainy")}
    selected_seasons = st.multiselect(
      txt("Estações", "Seasons"),
      season_options,
      default=season_options,
      format_func=lambda value: season_display.get(value, value),
      key="ko_season_sel",
    )
  with c3:
    top_n = st.slider(txt("Top KOs por lagoa/estação", "Top KOs per lake/season"), 5, 50, 15, step=5, key="ko_top_abund")
  if not abundance.empty:
    abund_f = abundance[abundance["lake"].isin(selected_lakes) & abundance["season"].isin(selected_seasons)].copy()
    top_abund = abund_f.groupby(["lake", "season"], group_keys=False).head(top_n)
    st.markdown("#### " + txt("Mais abundantes pelas contagens", "Most abundant by counts"))
    show_table(top_abund, "top_abundant_lake_season", height=430)
    csv_button(top_abund, "top_abundant_KOs_by_lake_season.csv", txt("Baixar KOs mais abundantes", "Download most abundant KOs"))
  if not evidence.empty:
    ev = evidence[evidence["lake"].isin(selected_lakes) & evidence["season"].isin(selected_seasons)].copy()
    ev = ev.sort_values(["pvalue", "padj"], na_position="last")
    st.markdown("#### " + txt("Mais significativos segundo tabelas DESeq2", "Most significant according to DESeq2 tables"))
    significance_legend()
    show_table(ev.head(300), "significant_evidence", height=430)
    csv_button(ev, "DESeq2_significant_KO_evidence_by_lake_season.csv", txt("Baixar evidência significativa", "Download significant evidence"))
  if not curated.empty:
    cur = curated[curated["lake"].isin(selected_lakes) & curated["season"].isin(selected_seasons)].copy()
    cur["abs_log2FoldChange"] = pd.to_numeric(cur["log2FoldChange"], errors="coerce").abs()
    cur = cur.sort_values("abs_log2FoldChange", ascending=False)
    st.markdown("#### " + txt("Evidência diferencial curada: seca e chuva", "Curated differential evidence: dry and rainy seasons"))
    st.info(txt(
      "Estas linhas vêm das abas Top-differential-abundance_Dry e Top-differential-abundance-Rain; elas indicam direção e magnitude, mas não trazem p-value próprio nessa tabela resumida.",
      "These rows come from Top-differential-abundance_Dry and Top-differential-abundance-Rain; they indicate direction and magnitude, but the summarized table itself does not include p-values."
    ))
    show_table(cur.head(300), "curated_differential_evidence", height=430)
    csv_button(cur, "curated_differential_evidence_dry_rain.csv", txt("Baixar evidência diferencial curada", "Download curated differential evidence"))


def _load_csv_from_data(name: str) -> pd.DataFrame:
  try:
    path = BASE_DIR / "data" / name
    if path.exists():
      return pd.read_csv(path).fillna("")
  except Exception:
    pass
  return pd.DataFrame()


def st8_marker_abundance_panel():
  """Show marker abundance and descriptive significance by ST8 group and omics layer."""
  st.markdown("#### " + txt("Marcadores KO/metabolismo mais abundantes e contrastantes", "Most abundant and contrasting KO/metabolism markers"))
  st.caption(txt(
    "Esta análise usa somente as tabelas derivadas da Supplementary Table 8 final. Ela separa metagenômica, metatranscriptômica e assemblies combinados, e ajuda a identificar marcadores abundantes nas lagoas amazônicas, nos transcriptomas e nos demais ambientes ricos em ferro.",
    "This analysis uses only the tables derived from the final Supplementary Table 8. It separates metagenomics, metatranscriptomics and combined assemblies, and helps identify markers abundant in Amazonian lakes, transcriptomes and other iron-rich environments."
  ))
  ko_summary = _load_csv_from_data("st8_ko_group_summary.csv")
  iron_summary = _load_csv_from_data("st8_iron_ko_group_summary.csv")
  ko_contrast = _load_csv_from_data("st8_ko_amazonia_vs_groups.csv")
  iron_contrast = _load_csv_from_data("st8_iron_amazonia_vs_groups.csv")
  if ko_summary.empty and iron_summary.empty:
    st.info(txt("As tabelas de resumo ST8 não foram encontradas.", "ST8 summary tables were not found."))
    return
  marker_type = st.radio(
    txt("Tipo de marcador", "Marker type"),
    ["All KO biomarkers", "Iron metabolism KO markers"],
    horizontal=True,
    key="st8_marker_abundance_type",
  )
  if marker_type == "All KO biomarkers":
    summary = ko_summary.copy(); contrast = ko_contrast.copy(); id_col = "KO"; cat_col = "Metabolism"; desc_col = "KO description"
  else:
    summary = iron_summary.copy(); contrast = iron_contrast.copy(); id_col = "Function Id"; cat_col = "Biologic Role"; desc_col = "Function Name"
  if summary.empty:
    st.info(txt("Resumo ausente para o tipo de marcador selecionado.", "Summary missing for the selected marker type."))
    return
  groups = sorted(summary["ST8_group"].dropna().astype(str).unique().tolist())
  layers = sorted(summary["data_layer"].dropna().astype(str).unique().tolist())
  c1, c2, c3 = st.columns([0.42, 0.28, 0.30])
  with c1:
    sel_groups = st.multiselect(txt("Grupos ricos em ferro", "Iron-rich groups"), groups, default=groups, key=f"st8_marker_groups_{marker_type}")
  with c2:
    sel_layers = st.multiselect(txt("Camada ômica", "Omics layer"), layers, default=layers, key=f"st8_marker_layers_{marker_type}")
  with c3:
    rank_by = st.selectbox(txt("Ordenar por", "Rank by"), ["mean_count", "total_count", "detection_fraction"], index=0, key=f"st8_marker_rank_{marker_type}")
    topn = st.slider(txt("Top marcadores", "Top markers"), 10, 80, 30, step=10, key=f"st8_marker_topn_{marker_type}")
  filt = summary[summary["ST8_group"].astype(str).isin(sel_groups) & summary["data_layer"].astype(str).isin(sel_layers)].copy()
  if filt.empty:
    st.warning(txt("Nenhum marcador após os filtros.", "No markers after filtering."))
    return
  filt[rank_by] = pd.to_numeric(filt[rank_by], errors="coerce")
  filt["marker_label"] = filt[id_col].astype(str) + " | " + filt[cat_col].astype(str)
  top = filt.sort_values(rank_by, ascending=False).head(topn).copy()
  fig = px.bar(
    top.sort_values(rank_by),
    x=rank_by,
    y="marker_label",
    color="data_layer",
    facet_col="ST8_group" if len(sel_groups) <= 3 else None,
    orientation="h",
    hover_data=[c for c in [desc_col, "ST8_group", "data_layer", "total_count", "mean_count", "detection_fraction", "n_samples"] if c in top.columns],
    title=txt("Marcadores mais abundantes por grupo e camada ômica", "Most abundant markers by group and omics layer"),
  )
  fig.update_layout(height=max(720, 26 * len(top) + 180), margin=dict(l=260, r=20, t=90, b=40), yaxis_tickfont=dict(size=10))
  render_plotly_downloadable(fig, key=f"st8_marker_abundance_{marker_type}_{rank_by}", basename=f"ST8_marker_abundance_{marker_type.replace(' ', '_')}_{rank_by}")

  # Inferential result associated with this barplot. The visual ranking is
  # descriptive, while the test compares the 20 Amazonian samples against the
  # currently selected external groups/layers using exact ST8 counts.
  if marker_type == "All KO biomarkers":
    stat_matrix, stat_cols = counts_table("table8", ST8_ALL_KO_SHEET, ["KO", "Metabolism", "KO description"])
    stat_id, stat_cat, stat_desc = "KO", "Metabolism", "KO description"
  else:
    stat_matrix, stat_cols = counts_table("table8", ST8_IRON_ALL_SHEET, ["Function Id", "Biologic Role", "Function Name"])
    stat_id, stat_cat, stat_desc = "Function Id", "Biologic Role", "Function Name"
  scoped_cols = _st8_cols_for_scope(stat_cols, st8_column_metadata(), sel_groups, sel_layers, [])
  external_cols = [c for c in scoped_cols if not _is_article_lake_sample_column(c)]
  marker_stats = st8_environment_marker_statistics(stat_matrix, stat_cols, stat_id, stat_cat, stat_desc, external_cols)
  n_sig = int(marker_stats.get("significant_q_lt_0_05", pd.Series(dtype=bool)).fillna(False).sum()) if not marker_stats.empty else 0
  sig_names = marker_stats.loc[marker_stats.get("significant_q_lt_0_05", False).astype(bool), stat_id].astype(str).head(8).tolist() if not marker_stats.empty and "significant_q_lt_0_05" in marker_stats.columns else []
  sig_text = ", ".join(sig_names) if sig_names else txt("nenhum marcador significativo", "no significant marker")
  st.info(txt(
    f"Teste associado ao barplot: Mann–Whitney U e Welch t-test em log1p(contagens), lagoas AM/TI/TIA/VI versus os grupos/camadas externos selecionados; FDR de Benjamini–Hochberg. Resultado: {n_sig}/{len(marker_stats)} marcadores com q<0,05. Primeiros: {sig_text}.",
    f"Barplot-associated test: Mann–Whitney U and Welch t-test on log1p counts, AM/TI/TIA/VI lakes versus selected external groups/layers; Benjamini–Hochberg FDR. Result: {n_sig}/{len(marker_stats)} markers with q<0.05. First: {sig_text}."
  ))
  if not marker_stats.empty:
    with st.expander(txt("Resultados estatísticos do barplot", "Barplot statistical results"), expanded=False):
      show_table(marker_stats, f"st8_marker_abundance_stats_{marker_type}", height=420)
      csv_button(marker_stats, f"ST8_{marker_type.replace(' ', '_')}_barplot_statistics.csv", txt("Baixar testes do barplot", "Download barplot tests"))
  show_table(top, f"st8_marker_abundance_table_{marker_type}", height=440)
  csv_button(filt, f"ST8_{marker_type.replace(' ', '_')}_marker_abundance_filtered.csv", txt("Baixar marcadores filtrados", "Download filtered markers"))

  if not contrast.empty:
    st.markdown("##### " + txt("Marcadores mais contrastantes: lagoas amazônicas vs grupos selecionados", "Most contrasting markers: Amazonian lakes vs selected groups"))
    cont = contrast[contrast["ST8_group"].astype(str).isin(sel_groups) & contrast["data_layer"].astype(str).isin(sel_layers)].copy()
    cont = add_descriptive_contrast_context(cont, marker_type, "KO_Amazonia_vs_groups" if marker_type == "All KO biomarkers" else "Iron_Amazonia_vs_groups")
    st8_contrast_caption(marker_type, sel_groups, sel_layers)
    if not cont.empty:
      marker_col = "KO" if "KO" in cont.columns else "Function Id"
      cont["abs_log2_ratio"] = pd.to_numeric(cont["log2_ratio_amazonia_vs_external"], errors="coerce").abs()
      cont["marker_label"] = cont[marker_col].astype(str) + " | " + cont["category"].astype(str)
      # show strongest Amazonian-enriched and external-enriched separately, so transcriptomic markers are easy to inspect.
      c_amz, c_ext = st.columns(2)
      amz = cont.sort_values("log2_ratio_amazonia_vs_external", ascending=False).head(min(topn, 40))
      ext = cont.sort_values("log2_ratio_amazonia_vs_external", ascending=True).head(min(topn, 40))
      with c_amz:
        st.markdown("**" + txt("Maior média nas lagoas amazônicas AM/TI/TIA/VI", "Higher mean in Amazonian lakes AM/TI/TIA/VI") + "**")
        show_table(amz[[c for c in [marker_col, "category", "description", "comparison", "method", "ST8_group", "data_layer", "amazonian_mean_count", "external_group_mean_count", "log2_ratio_amazonia_vs_external", "n_external_samples", "detection_fraction_external", "source_sheet"] if c in amz.columns]], f"st8_amazonia_enriched_{marker_type}", height=380)
      with c_ext:
        st.markdown("**" + txt("Maior média nos grupos/camadas externos selecionados", "Higher mean in selected external groups/layers") + "**")
        show_table(ext[[c for c in [marker_col, "category", "description", "comparison", "method", "ST8_group", "data_layer", "amazonian_mean_count", "external_group_mean_count", "log2_ratio_amazonia_vs_external", "n_external_samples", "detection_fraction_external", "source_sheet"] if c in ext.columns]], f"st8_external_enriched_{marker_type}", height=380)
      plot = pd.concat([amz.head(12), ext.head(12)], axis=0).drop_duplicates().sort_values("log2_ratio_amazonia_vs_external")
      if not plot.empty:
        fig2 = px.bar(plot, x="log2_ratio_amazonia_vs_external", y="marker_label", color="data_layer", orientation="h", hover_data=["comparison", "method", "source_sheet", "ST8_group", "data_layer", "amazonian_mean_count", "external_group_mean_count", "n_external_samples", "detection_fraction_external"], title=txt("Marcadores com maiores contrastes descritivos", "Markers with strongest descriptive contrasts"))
        fig2.add_vline(x=0, line_dash="dash", line_color="#263238")
        fig2.update_layout(height=max(560, 21 * len(plot) + 170), width=1540, bargap=0.10, margin=dict(l=250, r=30, t=112, b=55), title=dict(y=0.985, x=0.01, xanchor="left", yanchor="top"), legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0, xanchor="left"), yaxis_tickfont=dict(size=7))
        render_plotly_downloadable(fig2, key=f"st8_marker_contrast_split_{marker_type}", basename=f"ST8_marker_contrast_split_{marker_type.replace(' ', '_')}")
        st.caption(txt(
          "Legenda: valores positivos indicam maior média nas lagoas AM/TI/TIA/VI; valores negativos indicam maior média no grupo/camada externo selecionado. A comparação, método e planilha-fonte aparecem no hover.",
          "Legend: positive values indicate higher mean in AM/TI/TIA/VI lakes; negative values indicate higher mean in the selected external group/layer. Comparison, method and source sheet are shown in hover text."
        ))
      csv_button(cont, f"ST8_{marker_type.replace(' ', '_')}_Amazonia_vs_filtered_groups.csv", txt("Baixar contrastes filtrados", "Download filtered contrasts"))


def st8_column_metadata() -> pd.DataFrame:
  """Return all 67 ST8 records with harmonised sample-type metadata."""
  try:
    meta = iron_rich_environment_metadata().copy()
  except Exception:
    return pd.DataFrame()
  if meta.empty:
    return meta
  for col in ["ST8_matrix_column", "matrix_column_all_KO", "matrix_column_iron_KO", "matrix_column_selected"]:
    if col not in meta.columns:
      meta[col] = meta.get("matrix_column", meta.get("sample_id", pd.Series("", index=meta.index))).astype(str)
  if "Study Name" not in meta.columns:
    meta["Study Name"] = meta.get("study_name", pd.Series("", index=meta.index)).astype(str)
  if "study_name" not in meta.columns:
    meta["study_name"] = meta["Study Name"].astype(str)
  if "sample_type" not in meta.columns:
    meta["sample_type"] = "Other / not explicitly reported"
  meta["is_sediment_sample"] = meta["sample_type"].astype(str).eq("Sediment")
  return meta.fillna("")


def _st8_cols_for_scope(numeric_cols: list[str], meta: pd.DataFrame, selected_groups: list[str], selected_layers: list[str], selected_studies: list[str]) -> list[str]:
  amazon_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  if meta is None or meta.empty:
    return list(dict.fromkeys(numeric_cols))
  work = meta.copy()
  if selected_groups and "ST8_group" in work.columns:
    work = work[work["ST8_group"].astype(str).isin(selected_groups)]
  if selected_layers and "data_layer" in work.columns:
    work = work[work["data_layer"].astype(str).isin(selected_layers)]
  if selected_studies:
    study_col = "Study Name" if "Study Name" in work.columns else "study_name"
    if study_col in work.columns:
      work = work[work[study_col].astype(str).isin(selected_studies)]
  mapped: list[str] = []
  for colname in ["ST8_matrix_column", "matrix_column_all_KO", "matrix_column_iron_KO", "matrix_column_selected", "matrix_column"]:
    if colname in work.columns:
      mapped.extend(work[colname].dropna().astype(str).tolist())
  mapped = [c for c in dict.fromkeys(mapped) if c in numeric_cols]
  return amazon_cols + [c for c in mapped if c not in amazon_cols]


def _st8_sediment_subset_from_full(frame: pd.DataFrame, numeric_cols: list[str]) -> tuple[pd.DataFrame, list[str]]:
  """Build a true sediment-only external subset from the complete ST8 matrix."""
  if frame is None or frame.empty:
    return pd.DataFrame(), []
  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  meta = st8_column_metadata()
  sediment_records = meta[meta.get("sample_type", pd.Series("", index=meta.index)).astype(str).eq("Sediment")].copy()
  external_cols: list[str] = []
  for colname in ["ST8_matrix_column", "matrix_column_all_KO", "matrix_column_iron_KO", "matrix_column_selected", "matrix_column"]:
    if colname in sediment_records.columns:
      external_cols.extend(sediment_records[colname].dropna().astype(str).tolist())
  external_cols = [c for c in dict.fromkeys(external_cols) if c in numeric_cols and c not in lake_cols]
  selected = lake_cols + external_cols
  id_cols = [c for c in frame.columns if c not in numeric_cols]
  return frame[id_cols + selected].copy(), selected


def st8_metadata_availability_heatmap(meta: pd.DataFrame, zscore_rows: bool = False):
  if meta is None or meta.empty:
    return None, pd.DataFrame()
  preferred = [
    "taxon_oid", "sample_id", "GOLD Analysis Project ID", "GOLD Sequencing Project ID", "GOLD Study ID",
    "Study Name", "Genome Name / Sample Name", "Geographic Location", "Habitat", "ST8_group", "ST8_short_group",
    "data_layer", "data_layer_abbrev", "collection_date", "latitude", "longitude", "NCBI BioProject Accession",
  ]
  fields = [c for c in preferred if c in meta.columns]
  if not fields:
    fields = [c for c in meta.columns[:min(20, len(meta.columns))]]
  labels = []
  for idx, row in meta.iterrows():
    label = first_present(row, ["sample_id_created_this_study", "sample_id", "Genome Name / Sample Name", "taxon_oid"], default=f"record_{idx+1}")
    labels.append(str(label)[:55])
  raw_matrix = pd.DataFrame(index=labels)
  for field in fields:
    values = meta[field].map(lambda x: 0 if pd.isna(x) or str(x).strip().lower() in {"", "nan", "none", "nat", "<na>"} else 1)
    raw_matrix[field] = values.to_numpy()
  matrix = raw_matrix.astype(float)
  if zscore_rows:
    means = matrix.mean(axis=1)
    stds = matrix.std(axis=1).replace(0, np.nan)
    matrix = matrix.sub(means, axis=0).div(stds, axis=0).fillna(0)
  n_rows = max(len(matrix), 1)
  n_cols = max(len(fields), 1)
  cell_px = max(16.0, min(28.0, 4600.0 / n_rows, 4600.0 / n_cols))
  width = int(590 + cell_px * n_cols)
  height = int(310 + cell_px * n_rows)
  fig = go.Figure(go.Heatmap(
    z=matrix.to_numpy(), x=fields, y=matrix.index.tolist(),
    customdata=raw_matrix.to_numpy(),
    zmin=-3 if zscore_rows else 0, zmax=3 if zscore_rows else 1,
    zmid=0 if zscore_rows else None,
    colorscale="RdBu_r" if zscore_rows else [[0, "#E5E7EB"], [0.499, "#E5E7EB"], [0.5, "#0F766E"], [1, "#0F766E"]],
    colorbar={"title": "Row z-score" if zscore_rows else "Metadata availability", "tickvals": [-3, 0, 3] if zscore_rows else [0, 1], "ticktext": ["Lower", "Row mean", "Higher"] if zscore_rows else ["Missing", "Available"]},
    hovertemplate=("<b>%{y}</b><br>%{x}<br>Row z-score: %{z:.3f}<br>Raw availability: %{customdata}<extra></extra>" if zscore_rows else "<b>%{y}</b><br>%{x}: %{z}<extra></extra>"),
    xgap=0.5, ygap=0.5,
  ))
  fig.update_layout(
    title="ST8 — IMG/M metadata availability" + (" — row z-score" if zscore_rows else " — raw 0/1 matrix"),
    width=width, height=height,
    margin={"l": 360, "r": 155, "t": 95, "b": 220},
    font={"color": "#000000", "family": "Arial, Helvetica, sans-serif"},
    meta={"preserve_cell_geometry": True, "cell_px": cell_px},
  )
  fig.update_xaxes(tickangle=-55, tickfont={"color": "#000000", "size": 13}, automargin=True)
  fig.update_yaxes(tickfont={"color": "#000000", "size": 12}, automargin=True)
  export = matrix.reset_index().rename(columns={"index": "record"})
  return fig, export


def _st8_heatmap_export_table(df: pd.DataFrame, numeric_cols: list[str], top_n: int, zscore_rows: bool = False) -> pd.DataFrame:
  numeric_cols = [c for c in numeric_cols if c in df.columns]
  matrix = df[numeric_cols].apply(lambda col: pd.to_numeric(col.astype(str).str.replace(",", ".", regex=False), errors="coerce")).fillna(0)
  ranked = matrix.abs().sum(axis=1).sort_values(ascending=False, kind="mergesort").index
  idx = matrix.index if top_n is None or int(top_n) <= 0 or int(top_n) >= len(matrix) else ranked[:int(top_n)]
  metadata_cols = [c for c in df.columns if c not in numeric_cols]
  out = df.loc[idx, metadata_cols].reset_index(drop=True).copy()
  values = matrix.loc[idx].copy()
  if zscore_rows:
    values = values.sub(values.mean(axis=1), axis=0).div(values.std(axis=1).replace(0, np.nan), axis=0).fillna(0)
  return pd.concat([out, values.reset_index(drop=True)], axis=1)


def _st8_column_metadata_lookup(meta: pd.DataFrame, numeric_cols: list[str]) -> dict[str, dict]:
  """Map every ST8 matrix column to its curated study/group/layer metadata."""
  if meta is None or meta.empty:
    return {}
  allowed = {str(c) for c in numeric_cols}
  matrix_fields = [
    c for c in ["ST8_matrix_column", "matrix_column_all_KO", "matrix_column_iron_KO", "matrix_column_selected"]
    if c in meta.columns
  ]
  lookup: dict[str, dict] = {}
  for _, row in meta.iterrows():
    record = {
      "Study Name": str(row.get("Study Name", "")).strip(),
      "ST8_group": str(row.get("ST8_group", "")).strip(),
      "data_layer": str(row.get("data_layer", "")).strip(),
      "Genome Name / Sample Name": str(row.get("Genome Name / Sample Name", "")).strip(),
      "sample_id_created_this_study": str(row.get("sample_id_created_this_study", "")).strip(),
    }
    for field in matrix_fields:
      matrix_col = str(row.get(field, "")).strip()
      if matrix_col and matrix_col in allowed and matrix_col not in lookup:
        lookup[matrix_col] = record
  return lookup


def st8_characteristic_markers_by_study(
  df: pd.DataFrame,
  selected_cols: list[str],
  meta: pd.DataFrame,
  top_n_per_study: int = 8,
) -> pd.DataFrame:
  """Rank markers enriched in each selected study versus the remaining selected columns.

  This is a descriptive ranking calculated directly from the exact ST8 counts.
  It does not impute values and does not claim inferential significance.
  """
  if df is None or df.empty or not selected_cols:
    return pd.DataFrame()
  selected_cols = [c for c in dict.fromkeys(selected_cols) if c in df.columns]
  if len(selected_cols) < 2:
    return pd.DataFrame()
  matrix = df[selected_cols].apply(lambda col: pd.to_numeric(col, errors="coerce")).fillna(0.0)
  lake_cols = [c for c in selected_cols if _is_article_lake_sample_column(c)]
  external_cols = [c for c in selected_cols if c not in lake_cols]
  lookup = _st8_column_metadata_lookup(meta, selected_cols)

  if "KO" in df.columns:
    id_col, category_col, description_col = "KO", "Metabolism", "KO description"
  else:
    id_col, category_col, description_col = "Function Id", "Biologic Role", "Function Name"

  scopes: list[dict] = []
  if lake_cols:
    scopes.append({
      "scope": "Amazonian lakes (AM/TI/TIA/VI)",
      "study": "Amazonian lakes (AM/TI/TIA/VI)",
      "group": "Amazonian lateritic lakes",
      "layer": "Metagenomic lake samples",
      "columns": lake_cols,
    })

  study_columns: dict[str, list[str]] = {}
  study_groups: dict[str, set[str]] = {}
  study_layers: dict[str, set[str]] = {}
  for col in external_cols:
    info = lookup.get(str(col), {})
    study = str(info.get("Study Name", "")).strip() or str(info.get("ST8_group", "")).strip() or str(col)
    study_columns.setdefault(study, []).append(col)
    group = str(info.get("ST8_group", "")).strip()
    layer = str(info.get("data_layer", "")).strip()
    if group:
      study_groups.setdefault(study, set()).add(group)
    if layer:
      study_layers.setdefault(study, set()).add(layer)
  for study, cols in study_columns.items():
    scopes.append({
      "scope": study,
      "study": study,
      "group": "; ".join(sorted(study_groups.get(study, set()))) or "External ST8 environment",
      "layer": "; ".join(sorted(study_layers.get(study, set()))) or "Not specified",
      "columns": cols,
    })

  rows: list[pd.DataFrame] = []
  for scope in scopes:
    focal_cols = [c for c in scope["columns"] if c in selected_cols]
    background_cols = [c for c in selected_cols if c not in focal_cols]
    if not focal_cols or not background_cols:
      continue
    focal_mean = matrix[focal_cols].mean(axis=1)
    background_mean = matrix[background_cols].mean(axis=1)
    focal_detection = matrix[focal_cols].gt(0).mean(axis=1)
    background_detection = matrix[background_cols].gt(0).mean(axis=1)
    log2_ratio = np.log2((focal_mean + 1.0) / (background_mean + 1.0))
    score = log2_ratio * np.log10(focal_mean + 10.0) * (0.5 + focal_detection)
    work = pd.DataFrame({
      id_col: df[id_col].astype(str),
      category_col: df.get(category_col, pd.Series("", index=df.index)).astype(str),
      description_col: df.get(description_col, pd.Series("", index=df.index)).astype(str),
      "Focal study / scope": scope["scope"],
      "Study Name": scope["study"],
      "ST8 group": scope["group"],
      "Omics layer": scope["layer"],
      "n focal columns": len(focal_cols),
      "n background columns": len(background_cols),
      "focal mean count": focal_mean,
      "background mean count": background_mean,
      "log2 ratio focal vs remaining selected": log2_ratio,
      "focal detection fraction": focal_detection,
      "background detection fraction": background_detection,
      "characteristic score": score,
      "relative status": np.where(log2_ratio > 0, "Higher in focal study", "Not higher than remaining selected columns"),
    })
    work = work.sort_values(
      ["log2 ratio focal vs remaining selected", "characteristic score", "focal mean count"],
      ascending=[False, False, False],
      kind="mergesort",
    ).head(max(1, int(top_n_per_study)))
    work.insert(0, "rank within study", range(1, len(work) + 1))
    work["marker label"] = work[id_col].astype(str) + " | " + work[category_col].astype(str)
    work["method"] = "Descriptive ranking from exact ST8 counts: log2((focal study mean + 1)/(mean of all remaining selected columns + 1)); no inferential significance claimed."
    rows.append(work)
  if not rows:
    return pd.DataFrame()
  return pd.concat(rows, ignore_index=True)


def render_st8_characteristic_marker_panel(
  df: pd.DataFrame,
  selected_cols: list[str],
  meta: pd.DataFrame,
  base_key: str,
):
  """Highlight characteristic markers for every study in the selected ST8 combination."""
  st.markdown("###### " + txt(
    "2C2. Marcadores mais característicos de cada estudo selecionado",
    "2C2. Most characteristic markers for each selected study",
  ))
  top_n = st.slider(
    txt("Marcadores característicos por estudo", "Characteristic markers per study"),
    min_value=3, max_value=20, value=8, step=1,
    key=f"{base_key}_characteristic_topn",
  )
  characteristic = st8_characteristic_markers_by_study(df, selected_cols, meta, top_n_per_study=top_n)
  if characteristic.empty:
    st.info(txt(
      "Não foi possível calcular marcadores característicos com a combinação selecionada.",
      "Characteristic markers could not be calculated for the selected combination.",
    ))
    return
  scopes = characteristic["Focal study / scope"].drop_duplicates().astype(str).tolist()
  c1, c2 = st.columns(2)
  c1.metric(txt("Estudos/escopos destacados", "Highlighted studies/scopes"), len(scopes))
  c2.metric(txt("Linhas de marcadores ranqueadas", "Ranked marker rows"), len(characteristic))
  focus = st.selectbox(
    txt("Estudo/escopo para destacar no gráfico", "Study/scope to highlight in the chart"),
    scopes,
    key=f"{base_key}_characteristic_focus",
  )
  focus_df = characteristic[characteristic["Focal study / scope"].eq(focus)].copy()
  focus_df = focus_df.sort_values("characteristic score", ascending=True)
  if not focus_df.empty:
    hover_cols = [
      c for c in [
        "Study Name", "ST8 group", "Omics layer", "focal mean count", "background mean count",
        "log2 ratio focal vs remaining selected", "focal detection fraction", "background detection fraction",
      ] if c in focus_df.columns
    ]
    fig = px.bar(
      focus_df,
      x="log2 ratio focal vs remaining selected",
      y="marker label",
      orientation="h",
      hover_data=hover_cols,
      title=txt(
        f"Marcadores característicos — {focus}",
        f"Characteristic markers — {focus}",
      ),
    )
    fig.update_layout(
      height=max(620, 46 * len(focus_df) + 260),
      margin=dict(l=330, r=180, t=150, b=80),
      title=dict(y=0.985, x=0.01, xanchor="left", yanchor="top"),
      xaxis_title=txt("log2 razão: estudo focal vs demais colunas selecionadas", "log2 ratio: focal study vs remaining selected columns"),
      yaxis_title=txt("Marcador KO / categoria", "KO marker / category"),
    )
    render_plotly_downloadable(
      fig,
      key=f"{base_key}_characteristic_plot",
      basename=f"{base_key}_characteristic_markers_selected_study",
    )
  st.caption(txt(
    "O destaque é descritivo e usa as contagens exatas da ST8. Para cada estudo, a média de suas colunas selecionadas é comparada à média de todas as demais colunas da combinação, incluindo as 20 amostras das lagoas quando presentes. Valores positivos indicam maior média no estudo focal. Quando um estudo não possui marcador positivo, a tabela ainda mostra seus marcadores relativamente mais altos e sinaliza que eles não superam as demais colunas selecionadas. Estes valores não representam teste de significância.",
    "The highlight is descriptive and uses exact ST8 counts. For each study, the mean of its selected columns is compared with the mean of all remaining columns in the combination, including all 20 lake samples when present. Positive values indicate a higher mean in the focal study. If a study has no positive marker, the table still reports its highest relative markers and flags that they are not higher than the remaining selected columns. These are not significance tests.",
  ))
  with st.expander(txt(
    "Tabela completa dos marcadores característicos por estudo",
    "Complete characteristic-marker table by study",
  ), expanded=False):
    show_table(characteristic, f"{base_key}_characteristic_table", height=520)
    csv_button(
      characteristic,
      f"{base_key}_characteristic_markers_by_study.csv",
      txt("Baixar marcadores característicos por estudo", "Download characteristic markers by study"),
    )


def render_st8_heatmap_scope_controls(df: pd.DataFrame, numeric_cols: list[str], label_col: str, title_prefix: str, base_key: str, x_label_map: dict | None = None, boxplot_spec: dict | None = None):
  """Render non-duplicated ST8 external, combined and selectable-combination scopes."""
  if df is None or df.empty or not numeric_cols:
    return
  x_label_map = x_label_map or {}
  meta = st8_column_metadata()
  numeric_cols = [c for c in dict.fromkeys(numeric_cols) if c in df.columns]
  lake_cols = [c for c in numeric_cols if _is_article_lake_sample_column(c)]
  external_cols = [c for c in numeric_cols if c not in lake_cols]
  combined_cols = lake_cols + external_cols

  if len(lake_cols) != 20:
    st.error(txt(
      f"Falha na composição das lagoas: esperado 20 amostras AM/TI/TIA/VI, mas {len(lake_cols)} foram identificadas.",
      f"Lake-composition failure: expected 20 AM/TI/TIA/VI samples, but {len(lake_cols)} were identified.",
    ))
    return
  if {"KO", "Metabolism", "KO description"}.issubset(df.columns) and len(df) == 189:
    unique_kos = int(df["KO"].astype(str).str.extract(r"(K\d{5})", expand=False).nunique())
    blank_text = int(sum(
      df[c].isna().sum() + df[c].astype(str).str.strip().isin(["", "nan", "None", "<NA>"]).sum()
      for c in ["KO", "Metabolism", "KO description"]
    ))
    blank_matrix = int(df[numeric_cols].isna().sum().sum())
    if unique_kos != 189 or blank_text or blank_matrix:
      st.error(txt(
        f"Falha de integridade da ST8: esperado 189/189 KOs únicos, sem campos vazios; obtido {unique_kos} KOs únicos, {blank_text} campos textuais vazios e {blank_matrix} células numéricas vazias.",
        f"ST8 integrity failure: expected 189/189 unique KOs with no blank fields; obtained {unique_kos} unique KOs, {blank_text} blank text fields and {blank_matrix} blank numeric cells.",
      ))
      return
    st.success(txt(
      "Integridade confirmada: 189/189 KOs, vias e descrições, sem células numéricas vazias.",
      "Integrity confirmed: 189/189 KOs, pathways and descriptions, with no blank numeric cells.",
    ))

  m1, m2, m3 = st.columns(3)
  m1.metric(txt("KOs/marcadores", "KOs/markers"), len(df))
  m2.metric(txt("Amostras das lagoas", "Amazonian lake samples"), f"{len(lake_cols)}/20")
  m3.metric(txt("Ambientes externos", "External environments"), len(external_cols))
  st.info(txt(
    "Os heatmaps exclusivos das lagoas aparecem somente na seção 1 e não são repetidos aqui. Esta seção mostra apenas ambientes externos, a combinação completa e uma combinação selecionável.",
    "Lake-only heatmaps appear only in section 1 and are not repeated here. This section shows only external environments, the complete combination and a selectable combination.",
  ))

  def render_pair(
    scope_name_pt: str,
    scope_name_en: str,
    cols: list[str],
    scope_key: str,
    caption_pt: str,
    caption_en: str,
    require_all_lakes: bool = False,
  ):
    cols = [c for c in dict.fromkeys(cols) if c in numeric_cols and c in df.columns]
    if require_all_lakes:
      cols = lake_cols + [c for c in cols if c not in lake_cols]
    if not cols:
      st.info(txt(f"Sem colunas para {scope_name_pt}.", f"No columns available for {scope_name_en}."))
      return
    pair_lakes = [c for c in cols if c in lake_cols]
    pair_external = [c for c in cols if c in external_cols]
    if require_all_lakes and len(pair_lakes) != 20:
      st.error(txt(
        f"O heatmap combinado foi bloqueado porque continha somente {len(pair_lakes)}/20 amostras das lagoas.",
        f"The combined heatmap was blocked because it contained only {len(pair_lakes)}/20 lake samples.",
      ))
      return
    st.markdown("###### " + txt(scope_name_pt, scope_name_en))
    st.caption(txt(
      f"Composição exibida: {len(pair_lakes)}/20 amostras das lagoas + {len(pair_external)} colunas externas; {len(cols)} colunas no total.",
      f"Displayed composition: {len(pair_lakes)}/20 lake samples + {len(pair_external)} external columns; {len(cols)} columns in total.",
    ))
    if require_all_lakes:
      st.caption(txt(
        "Amostras amazônicas incluídas no eixo X: " + ", ".join(pair_lakes) + ".",
        "Amazonian samples included on the x axis: " + ", ".join(pair_lakes) + ".",
      ))
    top_n = heatmap_row_limit_control(
      df,
      f"{base_key}_{scope_key}",
      noun_pt="KOs/marcadores",
      noun_en="KOs/markers",
      default_top=len(df),
    )
    raw_fig = heatmap_figure(
      df, cols, label_col,
      f"{title_prefix}: {scope_name_en} — raw counts ({top_n}/{len(df)} markers; {len(cols)} columns)",
      top_n=top_n, zscore_rows=False, x_label_map=x_label_map,
    )
    z_fig = heatmap_figure(
      df, cols, label_col,
      f"{title_prefix}: {scope_name_en} — row z-score ({top_n}/{len(df)} markers; {len(cols)} columns)",
      top_n=top_n, zscore_rows=True, x_label_map=x_label_map,
    )
    if raw_fig:
      render_plotly_downloadable(raw_fig, key=f"{base_key}_{scope_key}_raw", basename=f"{base_key}_{scope_key}_raw_counts")
    if z_fig:
      render_plotly_downloadable(z_fig, key=f"{base_key}_{scope_key}_zscore", basename=f"{base_key}_{scope_key}_row_zscore")
    raw_table = _st8_heatmap_export_table(df, cols, top_n, zscore_rows=False)
    z_table = _st8_heatmap_export_table(df, cols, top_n, zscore_rows=True)
    d1, d2 = st.columns(2)
    with d1:
      csv_button(raw_table, f"{base_key}_{scope_key}_raw_counts_table.csv", txt("Baixar tabela raw count usada", "Download raw-count source table"))
    with d2:
      csv_button(z_table, f"{base_key}_{scope_key}_row_zscore_table.csv", txt("Baixar tabela z-score usada", "Download row-z-score source table"))
    st.caption(txt(caption_pt, caption_en))

  render_pair(
    "2A. Somente ambientes externos ricos em ferro",
    "2A. External iron-rich environments only",
    external_cols,
    "external_only",
    f"Legenda: painel externo completo com {len(external_cols)} colunas ambientais, sem repetir as 20 amostras amazônicas já mostradas na seção 1. Raw e z-score usam exatamente as mesmas linhas e colunas.",
    f"Legend: complete external panel with {len(external_cols)} environment columns, without repeating the 20 Amazonian samples already shown in section 1. Raw and z-score use exactly the same rows and columns.",
  )
  render_pair(
    "2B. Lagoas amazônicas + todos os ambientes externos",
    "2B. Amazonian lakes + all external environments",
    combined_cols,
    "combined_all",
    f"Legenda: painel combinado completo com todas as 20 amostras AM/TI/TIA/VI e as {len(external_cols)} colunas externas. Nenhuma amostra das lagoas é omitida.",
    f"Legend: complete combined panel with all 20 AM/TI/TIA/VI samples and all {len(external_cols)} external columns. No lake sample is omitted.",
    require_all_lakes=True,
  )
  if isinstance(boxplot_spec, dict) and boxplot_spec:
    st8_environment_boxplot_panel(
      df,
      numeric_cols,
      str(boxplot_spec.get("id_col", "KO")),
      str(boxplot_spec.get("category_col", label_col)),
      str(boxplot_spec.get("description_col", "")),
      f"{base_key}_combined_all",
      str(boxplot_spec.get("title", title_prefix)),
      fixed_external_cols=external_cols,
      section_label=txt("2B3. Boxplot completo —", "2B3. Complete boxplot —"),
    )

  if meta.empty:
    return
  st.markdown("###### " + txt(
    "2C. Combinação por grupo, estudo e camada ômica",
    "2C. Combination by group, study and omics layer",
  ))
  c1, c2, c3 = st.columns([0.30, 0.25, 0.45])
  groups = sorted(meta.get("ST8_group", pd.Series(dtype=str)).replace("", np.nan).dropna().astype(str).unique().tolist())
  layers = sorted(meta.get("data_layer", pd.Series(dtype=str)).replace("", np.nan).dropna().astype(str).unique().tolist())
  studies = sorted(meta.get("Study Name", pd.Series(dtype=str)).replace("", np.nan).dropna().astype(str).unique().tolist()) if "Study Name" in meta.columns else []
  with c1:
    selected_groups = st.multiselect(
      txt("Grupo ST8", "ST8 group"), groups, default=groups,
      key=f"{base_key}_scope_groups",
    )
  with c2:
    selected_layers = st.multiselect(
      txt("Camada ômica", "Omics layer"), layers, default=layers,
      key=f"{base_key}_scope_layers",
    )
  with c3:
    selected_studies = st.multiselect(
      txt("Estudo", "Study"), studies, default=[],
      key=f"{base_key}_scope_studies",
      help=txt(
        "Opcional. Deixe vazio para incluir todos os estudos compatíveis com os grupos e camadas selecionados.",
        "Optional. Leave empty to include all studies compatible with the selected groups and layers.",
      ),
    )
  scoped_cols = _st8_cols_for_scope(numeric_cols, meta, selected_groups, selected_layers, selected_studies)
  scoped_cols = lake_cols + [c for c in scoped_cols if c not in lake_cols]
  if len(scoped_cols) <= len(lake_cols):
    st.info(txt(
      "A seleção não contém ambientes externos. Selecione pelo menos um grupo, camada ou estudo externo.",
      "The selection contains no external environments. Select at least one external group, layer or study.",
    ))
    return
  full_combination_selected = set(scoped_cols) == set(combined_cols) and len(scoped_cols) == len(combined_cols)
  if full_combination_selected:
    st.info(txt(
      "A combinação atual é idêntica ao painel completo 2B. Para evitar repetir o mesmo heatmap, 2C1 será exibido somente após restringir pelo menos um grupo, estudo ou camada ômica. O painel de marcadores característicos abaixo continua disponível para comparar todos os estudos.",
      "The current combination is identical to the complete 2B panel. To avoid repeating the same heatmap, 2C1 is displayed only after at least one group, study or omics layer is narrowed. The characteristic-marker panel below remains available to compare all studies.",
    ))
  else:
    render_pair(
      "2C1. Todas as lagoas + subconjunto externo selecionado",
      "2C1. All lakes + selected external subset",
      scoped_cols,
      "selected_scope",
      "Legenda: raw count e z-score incluem sempre as 20 amostras das lagoas e somente as colunas externas escolhidas. Os arquivos CSV correspondem diretamente às matrizes exibidas.",
      "Legend: raw-count and z-score always include all 20 lake samples and only the selected external columns. The CSV files correspond directly to the displayed matrices.",
      require_all_lakes=True,
    )
  render_st8_characteristic_marker_panel(df, scoped_cols, meta, base_key)
  with st.expander(txt("Metadados das colunas externas selecionadas", "Selected external-column metadata"), expanded=False):
    show_cols = [c for c in [
      "sample_id_created_this_study", "taxon_oid", "ST8_matrix_column", "ST8_group", "data_layer",
      "Study Name", "Genome Name / Sample Name", "sample_type", "is_sediment_sample", "Geographic Location", "Habitat", "Latitude", "Longitude",
    ] if c in meta.columns]
    if show_cols:
      selected_external = [c for c in scoped_cols if c not in lake_cols]
      meta_matrix_cols = [c for c in [
        "ST8_matrix_column", "matrix_column_all_KO", "matrix_column_iron_KO", "matrix_column_selected",
      ] if c in meta.columns]
      meta_view = meta[meta[meta_matrix_cols].astype(str).isin(selected_external).any(axis=1)] if meta_matrix_cols else meta.iloc[0:0]
      show_table(meta_view[show_cols].astype(str), f"{base_key}_selected_scope_metadata", height=360)

def _load_st8_csv(filename: str) -> tuple[pd.DataFrame, Path | None]:
  """Load an ST8 CSV from the packaged data/tables locations.

  The final ST8 tables are mirrored in both directories so the database layer,
  downloads and publication scripts all resolve the same records. A UTF-8 BOM
  is accepted because the source workbook is exported for Excel compatibility.
  """
  candidates = [BASE_DIR / "data" / filename, BASE_DIR / "tables" / filename]
  errors: list[str] = []
  for candidate in candidates:
    try:
      if not safe_path_exists(candidate):
        continue
      frame = pd.read_csv(candidate, encoding="utf-8-sig", low_memory=False)
      if not frame.empty:
        return frame, candidate
    except Exception as exc:
      errors.append(f"{candidate.name}: {exc}")
  if errors:
    print("ST8 table load failed: " + " | ".join(errors))
  return pd.DataFrame(), None


def st8_final_group_taxonomy_panel():
  """Final ST8 production panel: groups, omics layer split and GTDB taxonomy."""
  st.markdown("### " + txt("ST8 final — grupos, metagenômica/transcriptômica e taxonomia GTDB", "ST8 final — groups, metagenomics/transcriptomics and GTDB taxonomy"))
  render_section_script_inventory(
    "ST8 groups, metagenomics/transcriptomics and GTDB taxonomy",
    ["st8", "gtdb", "taxonomy_summary_by_group", "supplementary_table_8"],
    "st8_final_section",
  )
  meta, meta_path = _load_st8_csv("st8_metadata_curated.csv")
  tax, tax_path = _load_st8_csv("st8_taxonomy_summary_by_group.csv")
  ko_contrast, ko_path = _load_st8_csv("st8_ko_amazonia_vs_groups.csv")
  iron_contrast, iron_path = _load_st8_csv("st8_iron_amazonia_vs_groups.csv")
  study_refs, refs_path = _load_st8_csv("st8_study_references.csv")
  if meta.empty:
    st.error(txt(
      "A tabela de metadados ST8 está ausente ou vazia no pacote. Consulte o log técnico para os caminhos verificados.",
      "The ST8 metadata table is absent or empty in the package. See the technical log for the checked paths.",
    ))
    return
  required_meta = {"ST8_group", "data_layer"}
  missing_meta = sorted(required_meta.difference(meta.columns))
  if missing_meta:
    st.error(txt(
      f"A tabela ST8 não contém as colunas obrigatórias: {', '.join(missing_meta)}.",
      f"The ST8 table does not contain the required columns: {', '.join(missing_meta)}.",
    ))
    return
  with st.expander(txt("Tabelas e metadados ST8 incluídos", "Included ST8 tables and metadata"), expanded=False):
    inventory_rows = []
    for label, frame, source in [
      ("Final ST8 metadata", meta, meta_path),
      ("GTDB taxonomy summary by group", tax, tax_path),
      ("KO Amazonia-versus-group contrasts", ko_contrast, ko_path),
      ("Iron-KO Amazonia-versus-group contrasts", iron_contrast, iron_path),
      ("ST8 study references", study_refs, refs_path),
    ]:
      inventory_rows.append({
        "table": label,
        "relative_path": str(source.relative_to(BASE_DIR)) if source else "not available",
        "rows": int(len(frame)),
        "columns": int(len(frame.columns)) if not frame.empty else 0,
      })
    inventory = pd.DataFrame(inventory_rows)
    show_table(inventory, "st8_packaged_table_inventory", height=260)
    csv_button(inventory, "ST8_packaged_table_inventory.csv", txt("Baixar inventário", "Download inventory"))
    if not study_refs.empty:
      st.markdown("##### " + txt("Referências dos estudos ST8", "ST8 study references"))
      show_table(study_refs, "st8_study_references_full", height=320)
      csv_button(study_refs, "ST8_study_references.csv", txt("Baixar referências ST8", "Download ST8 references"))
  st.caption(txt(
    "A tabela ST8 final foi reorganizada nos grupos solicitados. A interface separa explicitamente metagenômica, metatranscriptômica e assemblies combinados; nenhuma contagem é simulada.",
    "The final ST8 table was reorganized into the requested groups. The interface explicitly separates metagenomics, metatranscriptomics and combined assemblies; no counts are simulated."
  ))
  group_counts = meta.groupby(["ST8_group", "data_layer"], dropna=False).size().reset_index(name="n_records")
  show_table(group_counts, "st8_final_group_counts", height=300)
  fig = px.bar(
    group_counts.sort_values("n_records"),
    x="n_records",
    y="ST8_group",
    color="data_layer",
    barmode="group",
    orientation="h",
    hover_data=["ST8_group", "data_layer", "n_records"],
    title=txt("Registros por grupo e camada ômica", "Records by group and omics layer"),
  )
  fig.update_layout(height=max(620, 36 * group_counts["ST8_group"].nunique() + 260), margin=dict(l=280, r=20, t=82, b=70), legend=dict(orientation="h", y=1.08, x=0))
  render_plotly_downloadable(fig, key="st8_final_group_omics_counts", basename="ST8_final_group_omics_counts")
  st.caption(txt(
    "Legenda: cada barra mostra o número de registros externos IMG/M/JGI por grupo ST8 e camada ômica. Este painel é um inventário de metadados (contagem de registros), não uma variável biológica replicada; portanto, nenhum teste inferencial é estatisticamente apropriado. Fonte: data/st8_metadata_curated.csv derivado da Supplementary Table 8 final.",
    "Legend: each bar shows the number of external IMG/M/JGI records by ST8 group and omics layer. This panel is a metadata inventory (record counts), not a replicated biological variable; therefore no inferential test is statistically appropriate. Source: data/st8_metadata_curated.csv derived from final Supplementary Table 8."
  ))
  selected_groups = st.multiselect(
    txt("Filtrar grupos ST8", "Filter ST8 groups"),
    sorted(meta["ST8_group"].dropna().unique().tolist()),
    default=sorted(meta["ST8_group"].dropna().unique().tolist()),
    key="st8_final_group_filter",
  )
  selected_layers = st.multiselect(
    txt("Filtrar camada", "Filter layer"),
    sorted(meta["data_layer"].dropna().unique().tolist()),
    default=sorted(meta["data_layer"].dropna().unique().tolist()),
    key="st8_final_layer_filter",
  )
  meta_f = meta[meta["ST8_group"].isin(selected_groups) & meta["data_layer"].isin(selected_layers)].copy()
  st.markdown("#### " + txt("Metadados finais usados nos heatmaps", "Final metadata used in heatmaps"))
  cols = [c for c in ["sample_id_created_this_study", "taxon_oid", "ST8_matrix_column", "ST8_group", "data_layer", "Study Name", "Genome Name / Sample Name", "Geographic Location", "Habitat", "Latitude", "Longitude", "NCBI Bioproject Accession", "SRA Run"] if c in meta_f.columns]
  show_table(meta_f[cols], "st8_final_metadata_filtered", height=360)
  csv_button(meta_f[cols], "ST8_final_metadata_filtered.csv", txt("Baixar metadados filtrados", "Download filtered metadata"))

  st8_marker_abundance_panel()

  if not tax.empty:
    st.markdown("#### " + txt("Classificação taxonômica GTDB: Phylum, Order e Family", "GTDB taxonomy: Phylum, Order and Family"))
    tax_f = tax[tax["ST8_group"].isin(selected_groups) & tax["data_layer"].isin(selected_layers)].copy()
    level = st.radio(txt("Nível taxonômico", "Taxonomic level"), ["Phylum", "Order", "Family"], horizontal=True, key="st8_tax_level")
    tax_level = tax_f[tax_f["taxonomy_level"].eq(level)].copy()
    if not tax_level.empty:
      available_layers = sorted(tax_level["data_layer"].dropna().astype(str).unique().tolist())
      selected_tax_layers = st.multiselect(
        txt("Camadas exibidas juntas", "Layers displayed together"), available_layers,
        default=available_layers, key=f"st8_tax_layers_multi_{level}",
        help=txt("Metagenomics, Metatranscriptomics e Combined assembly podem ser exibidas simultaneamente; todas as amostras selecionadas ficam no mesmo barplot.", "Metagenomics, Metatranscriptomics and Combined assembly can be displayed simultaneously; all selected samples appear in the same barplot."),
      )
      unit_mode = st.radio(
        txt("Unidades no barplot", "Barplot units"),
        ["All individual samples", "Aggregated ST8 groups"], horizontal=True,
        key=f"st8_tax_units_{level}",
        format_func=lambda x: txt("Todas as amostras individuais", "All individual samples") if x.startswith("All") else txt("Grupos ST8 por camada", "ST8 groups by layer"),
      )
      chart_mode = st.radio(
        txt("Escala do barplot", "Barplot scale"),
        ["Relative abundance (%)", "Absolute count"], horizontal=True,
        key=f"st8_tax_scale_{level}",
        format_func=lambda x: txt("Abundância relativa (%)", "Relative abundance (%)") if x.startswith("Relative") else txt("Contagem absoluta", "Absolute count"),
      )
      layer_data = tax_level[tax_level["data_layer"].astype(str).isin(selected_tax_layers)].copy() if selected_tax_layers else tax_level.iloc[0:0].copy()
      if layer_data.empty:
        st.info(txt("Selecione pelo menos uma camada.", "Select at least one layer."))
      elif unit_mode.startswith("All"):
        layer_data["sample_layer"] = layer_data["matrix_column"].astype(str) + " [" + layer_data["data_layer"].astype(str) + "]"
        x_col = "sample_layer"
        x_title = txt("Todas as amostras das camadas selecionadas", "All samples from selected layers")
        summary = layer_data.groupby(["sample_layer", "matrix_column", "ST8_group", "data_layer", "taxon"], as_index=False)["count_or_abundance"].sum()
      else:
        layer_data["group_layer"] = layer_data["ST8_group"].astype(str) + " [" + layer_data["data_layer"].astype(str) + "]"
        x_col = "group_layer"
        x_title = txt("Grupos ST8 por camada", "ST8 groups by layer")
        summary = layer_data.groupby(["group_layer", "ST8_group", "data_layer", "taxon"], as_index=False)["count_or_abundance"].sum()
      if not layer_data.empty:
        all_taxa = summary.groupby("taxon", as_index=False)["count_or_abundance"].sum().sort_values("count_or_abundance", ascending=False)["taxon"].astype(str).tolist()
        layer_key = safe_filename("_".join(selected_tax_layers) or "none")
        tc1, tc2 = st.columns([0.42, 0.58])
        with tc1:
          show_all_taxa = st.checkbox(txt(f"Mostrar todos os {len(all_taxa)} táxons", f"Show all {len(all_taxa)} taxa"), value=False, key=f"st8_tax_show_all_{level}_{layer_key}_{unit_mode}")
        with tc2:
          topn = len(all_taxa) if show_all_taxa else int(st.number_input(txt("Top táxons no gráfico", "Top taxa in chart"), min_value=1, max_value=max(1, len(all_taxa)), value=min(20, max(1, len(all_taxa))), step=1, key=f"st8_tax_topn_{level}_{layer_key}_{unit_mode}"))
        top_taxa = all_taxa[:topn]
        plot_df = summary[summary["taxon"].astype(str).isin(top_taxa)].copy()
        totals = summary.groupby(x_col)["count_or_abundance"].sum().replace(0, np.nan)
        if len(top_taxa) < len(all_taxa):
          selected_sums = plot_df.groupby(x_col)["count_or_abundance"].sum()
          base_cols = [x_col, "data_layer"] + (["ST8_group", "matrix_column"] if unit_mode.startswith("All") else ["ST8_group"])
          base = summary[base_cols].drop_duplicates(x_col)
          other = base.copy()
          other["taxon"] = "Other taxa"
          other["count_or_abundance"] = other[x_col].map(lambda x: max(0.0, float(totals.get(x, 0.0)) - float(selected_sums.get(x, 0.0))))
          plot_df = pd.concat([plot_df, other], ignore_index=True, sort=False)
        if chart_mode.startswith("Relative"):
          plot_df["plot_value"] = plot_df["count_or_abundance"] / plot_df[x_col].map(totals) * 100.0
          plot_df["plot_value"] = pd.to_numeric(plot_df["plot_value"], errors="coerce").fillna(0).clip(0, 100)
          y_label = "Relative abundance (%)"
        else:
          plot_df["plot_value"] = pd.to_numeric(plot_df["count_or_abundance"], errors="coerce").fillna(0).clip(lower=0)
          y_label = "Count / abundance"
        order_taxa = top_taxa + (["Other taxa"] if "Other taxa" in plot_df["taxon"].astype(str).values else [])
        color_map = publication_taxonomy_color_map(order_taxa)
        fig_tax = px.bar(
          plot_df, x=x_col, y="plot_value", color="taxon", color_discrete_map=color_map,
          barmode="stack", hover_data=[c for c in ["taxon", "ST8_group", "data_layer", "count_or_abundance", "matrix_column"] if c in plot_df.columns],
          title=f"{level} — {', '.join(selected_tax_layers)} — {'individual samples' if unit_mode.startswith('All') else 'ST8 groups by layer'}",
          labels={"plot_value": y_label, x_col: x_title},
        )
        n_bar_groups = max(1, int(plot_df[x_col].nunique()))
        individual_mode = unit_mode.startswith("All")
        # The grouped ST8 view contains fewer x-axis categories and previously
        # appeared vertically compressed. Give it more height and wider bars;
        # the individual-sample view receives a smaller, proportional increase.
        barplot_height = 940 if individual_mode else 1080
        pixels_per_group = 76 if individual_mode else 132
        barplot_width = max(2050, pixels_per_group * n_bar_groups + 620)
        bottom_margin = 320 if individual_mode else 260
        x_tick_size = 11 if individual_mode else 12
        fig_tax.update_layout(
          template="plotly_white", height=barplot_height,
          width=barplot_width,
          xaxis_tickangle=-55, margin=dict(l=105, r=340, t=125, b=bottom_margin),
          legend=dict(orientation="v", y=1, x=1.01, tracegroupgap=3, font=dict(size=10), title="Taxon", bgcolor="rgba(255,255,255,0.96)"),
          paper_bgcolor="white", plot_bgcolor="white",
          bargap=0.10 if individual_mode else 0.16,
        )
        fig_tax.update_xaxes(automargin=True, tickfont=dict(size=x_tick_size))
        fig_tax.update_yaxes(automargin=True, range=[0, 100] if chart_mode.startswith("Relative") else None, ticksuffix="%" if chart_mode.startswith("Relative") else "")
        render_plotly_downloadable(fig_tax, key=f"st8_final_taxonomy_{level}_{layer_key}_{unit_mode}_{chart_mode}", basename=f"ST8_final_taxonomy_{level}_{layer_key}_{unit_mode}")
        csv_button(plot_df, f"ST8_{level}_{layer_key}_{unit_mode}_barplot_source.csv", txt("Baixar tabela usada no barplot", "Download barplot source table"))

      if not layer_data.empty:
        # Statistical inference uses individual samples from every selected layer,
        # even if the displayed chart is aggregated. This preserves replication.
        test_source = layer_data.copy()
        test_source["log1p_count"] = np.log1p(pd.to_numeric(test_source["count_or_abundance"], errors="coerce").fillna(0))
        tested_taxa = top_taxa[:200]
        stat_parts = []
        for taxon in tested_taxa:
          sub = test_source[test_source["taxon"].astype(str).eq(str(taxon))]
          part = _numeric_group_stats(sub, "log1p_count", "ST8_group", category=str(taxon))
          if not part.empty:
            stat_parts.append(part)
        tax_stats = pd.concat(stat_parts, ignore_index=True) if stat_parts else pd.DataFrame()
        stat_summary = compact_significance_summary(tax_stats, max_items=8)
        st.info(txt(
          f"Teste do barplot ({', '.join(selected_tax_layers)}): Kruskal–Wallis/ANOVA globais e Mann–Whitney U/Welch pareados entre grupos ST8, com FDR de Benjamini–Hochberg. Táxons testados: {len(tested_taxa)}/{len(top_taxa)} exibidos. Resultado: {stat_summary}",
          f"Barplot tests ({', '.join(selected_tax_layers)}): global Kruskal–Wallis/ANOVA and pairwise Mann–Whitney U/Welch across ST8 groups, with Benjamini–Hochberg FDR. Taxa tested: {len(tested_taxa)}/{len(top_taxa)} displayed. Result: {stat_summary}"
        ))
        if not tax_stats.empty:
          show_table(tax_stats, f"st8_taxonomy_statistics_{level}_{layer_key}", height=360)
          csv_button(tax_stats, f"ST8_{level}_{layer_key}_barplot_statistics.csv", txt("Baixar testes estatísticos", "Download statistical tests"))
        st.caption(txt(
          "Legenda: o modo individual mostra, no mesmo gráfico, todas as amostras das camadas selecionadas; o modo agregado separa cada grupo ST8 por camada. Em percentual, cada barra é normalizada e limitada a 100%; em contagem absoluta, a camada permanece explícita no eixo e no hover.",
          "Legend: individual mode shows every sample from the selected layers in one chart; aggregated mode separates each ST8 group by layer. Percentage bars are normalised and bounded to 100%; for absolute counts, the layer remains explicit on the axis and in hover text."
        ))
        show_table(tax_level.sort_values("count_or_abundance", ascending=False), f"st8_taxonomy_table_{level}", height=420)
        csv_button(tax_level, f"ST8_final_{level}_taxonomy.csv", f"Download ST8 final {level} taxonomy")
    taxonomy_overlap_panel(tax_f, meta_f, selected_groups, selected_layers)

  if not ko_contrast.empty or not iron_contrast.empty:
    st.markdown("#### " + txt("Contrastes descritivos: Amazônia vs grupos ricos em ferro", "Descriptive contrasts: Amazonia vs iron-rich groups"))
    contrast_source = st.radio(txt("Tipo de biomarcador", "Biomarker type"), ["All KO biomarkers", "Iron metabolism KO markers"], horizontal=True, key="st8_contrast_source")
    if contrast_source == "All KO biomarkers":
      source = ko_contrast.copy(); id_col="KO"; cat_col="category"
    else:
      source = iron_contrast.copy(); id_col="Function Id"; cat_col="category"
    source = source[source["ST8_group"].isin(selected_groups) & source["data_layer"].isin(selected_layers)].copy()
    source = add_descriptive_contrast_context(source, contrast_source, "KO_Amazonia_vs_groups" if contrast_source == "All KO biomarkers" else "Iron_Amazonia_vs_groups")
    st8_contrast_caption(contrast_source, selected_groups, selected_layers)
    direction = st.radio(txt("Direção do contraste", "Contrast direction"), [txt("Ambos", "Both"), txt("Maior nas lagoas amazônicas", "Higher in Amazonian lakes"), txt("Maior nos grupos externos", "Higher in external groups")], horizontal=True, key=f"st8_contrast_direction_{contrast_source}")
    source["abs_log2_ratio"] = pd.to_numeric(source["log2_ratio_amazonia_vs_external"], errors="coerce").abs()
    if direction.startswith("Maior nas") or direction.startswith("Higher in Amazonian"):
      source = source[pd.to_numeric(source["log2_ratio_amazonia_vs_external"], errors="coerce") > 0]
    elif direction.startswith("Maior nos") or direction.startswith("Higher in external"):
      source = source[pd.to_numeric(source["log2_ratio_amazonia_vs_external"], errors="coerce") < 0]
    view = source.sort_values("abs_log2_ratio", ascending=False).head(80).sort_values("log2_ratio_amazonia_vs_external")
    if not view.empty:
      view["marker_label"] = view[id_col].astype(str) + " | " + view[cat_col].astype(str)
      fig_contrast = px.bar(view, x="log2_ratio_amazonia_vs_external", y="marker_label", color="ST8_group", orientation="h", hover_data=["comparison", "method", "source_sheet", "data_layer", "amazonian_mean_count", "external_group_mean_count", "n_external_samples", "detection_fraction_external"], title=txt("Maiores contrastes descritivos por grupo externo", "Strongest descriptive contrasts by external group"))
      fig_contrast.add_vline(x=0, line_dash="dash", line_color="#263238")
      fig_contrast.update_layout(height=max(620, 14 * len(view) + 180), width=1540, bargap=0.08, margin=dict(l=250, r=25, t=112, b=55), title=dict(y=0.985, x=0.01, xanchor="left", yanchor="top"), legend=dict(orientation="h", y=1.0, yanchor="bottom", x=0, xanchor="left"), yaxis_tickfont=dict(size=7))
      render_plotly_downloadable(fig_contrast, key=f"st8_final_contrast_{contrast_source}", basename=f"ST8_final_contrast_{contrast_source.replace(' ', '_')}")
      st.caption(txt(
        "Legenda: contraste descritivo calculado linha a linha a partir da tabela indicada no hover. O valor positivo favorece as lagoas AM/TI/TIA/VI; o valor negativo favorece o grupo ST8/camada ômica externa exibido na barra.",
        "Legend: descriptive contrast calculated row by row from the table indicated in hover text. A positive value favors AM/TI/TIA/VI lakes; a negative value favors the external ST8 group/omics layer shown in the bar."
      ))
      show_table(view, "st8_final_contrast_table", height=420)
      csv_button(source, f"ST8_final_{contrast_source.replace(' ', '_')}_Amazonia_vs_groups.csv", "Download descriptive contrast table")


def comparison_tab():
  st.subheader(BIOGEOCHEMICAL_DISPLAY_NAME)
  st.markdown(
    txt(
      "Esta seção compara as lagoas lateríticas amazônicas **AM (Amendoim), TI (Três Irmãs), TIA (Três Irmãs Adjacent) e VI (Violão)** com outros ambientes ricos em ferro usando as matrizes de contagem KO da Supplementary Table 8. A visualização online é uma extensão interativa das tabelas usadas para a comparação do artigo; a figura do manuscrito permanece como figura, enquanto as matrizes abaixo são tabelas e heatmaps derivados das planilhas.",
      "This section compares the Amazonian lateritic lakes **AM (Amendoim), TI (Três Irmãs), TIA (Três Irmãs Adjacent) and VI (Violão)** with other iron-rich environments using the KO count matrices from Supplementary Table 8. The online view is an interactive extension of the article comparison tables; the manuscript figure remains the figure, whereas the matrices below are tables and heatmaps derived from the spreadsheets."
    )
  )
  st.info(txt(LAKE_CODE_NOTE_PT, LAKE_CODE_NOTE))
  st8_final_group_taxonomy_panel()
  st.divider()
  df, numeric_cols = counts_table("table8", ST8_ALL_KO_SHEET, ["KO", "Metabolism", "KO description"])
  meta11 = load_external_environment_coordinates(BASE_DIR)
  if meta11.empty:
    meta11 = figure11_environment_metadata()
  with st.expander(txt("Supplementary Table 8 metadata — analysed iron-rich environments", "Supplementary Table 8 metadata — analysed iron-rich environments"), expanded=True):
    st.caption(txt(
      "Coordenadas, local geográfico, habitat, isolamento, país e data vêm das planilhas suplementares. Linhas sem data ou coordenadas permanecem como NA; nada é simulado.",
      "Coordinates, geographic location, habitat, isolation, country and date come from the supplementary spreadsheets. Rows without date or coordinates remain NA; nothing is simulated."
    ))
    if not meta11.empty:
      show_high_quality_sample_map(meta11, key="figure11_iron_rich_environment_map")
      show_table(meta11, "figure11_environment_metadata", height=420)
      csv_button(meta11, "figure11_environment_metadata.csv", txt("Baixar metadados da Supplementary Table 8", "Download Supplementary Table 8 metadata"))
    else:
      st.warning(txt("Não foi possível montar metadados da Figure 10.", "Could not assemble Figure 11 metadata."))
  full_iron_meta = iron_rich_environment_metadata()
  with st.expander(txt("Tabela completa de metadados — Iron-rich-environment", "Complete metadata table — Iron-rich-environment"), expanded=False):
    if full_iron_meta.empty:
      st.info(txt("A aba Iron-rich-environment não retornou dados.", "The Iron-rich-environment sheet returned no data."))
    else:
      show_table(full_iron_meta, "full_iron_rich_environment_metadata", height=560)
      csv_button(full_iron_meta, "Supplementary_Table_8_Iron-rich-environment_metadata.csv", txt("Baixar metadados Iron-rich-environment", "Download Supplementary Table 8 IMG/M metadata for all iron-rich environments"))
  ko_abundance_significance_panel(df)
  st.divider()
  st.markdown("### " + txt("Marcadores KO de destaque", "Highlighted KO markers"))
  st.caption(txt(
    "Destaques calculados a partir das contagens exatas de KO da Supplementary Table 8: biomarcadores de ciclos biogeoquímicos nas lagoas lateríticas amazônicas e outros ambientes ricos em ferro. Um marcador foi considerado contrastante quando apresentou maior magnitude absoluta de log2 ratio entre a média das lagoas amazônicas (AM/TI/TIA/VI) e a média do painel externo; portanto, trata-se de contraste descritivo e não de teste de hipótese. A função vem da coluna KO description e o link abre a entrada KEGG. Script principal: app.py / streamlit_app.py, função amazonia_vs_iron_marker_summary().",
    "Highlights calculated from exact KO counts in Supplementary Table 8: biogeochemical-cycle KO biomarkers across Amazonian lateritic lakes and other iron-rich environments. A marker is treated as contrasting when it has a larger absolute log2 ratio between the mean Amazonian-lake panel and the mean external panel; therefore this is a descriptive contrast and not a hypothesis test. The function comes from the KO description column and the link opens the KEGG entry. Main script: app.py / streamlit_app.py, function amazonia_vs_iron_marker_summary()."
  ))
  marker_summary = amazonia_vs_iron_marker_summary()
  if not marker_summary.empty:
    side = st.radio(txt("Mostrar destaques", "Show highlights"), ["Amazonian lateritic lakes", "Other iron-rich environments", "Both"], horizontal=True, key="amazonia_marker_side")
    view = marker_summary.copy() if side == "Both" else marker_summary[marker_summary["Highlighted side"].eq(side)].copy()
    view = add_marker_pathway_label(view.head(25), "KO", "Metabolism")
    plot_view = view.sort_values("log2 ratio — Amazonia vs other")
    fig_mark = px.bar(
      plot_view,
      x="log2 ratio — Amazonia vs other",
      y="marker_pathway_label",
      color="Highlighted side",
      orientation="h",
      hover_data=["Metabolism", "Function", "Mean count — Amazonian lateritic lakes", "Mean count — other iron-rich environments", "Compared external groups", "Method", "Source table", "Interpretation", "kegg_url"],
      title=txt("KOs com maior contraste descritivo entre grupos — marcador e via metabólica", "KOs with the strongest descriptive contrast between groups — marker and metabolic pathway"),
      labels={"marker_pathway_label": "KO marker | metabolic pathway"},
      color_discrete_sequence=["#00796B", "#F9A825", "#1565C0"],
    )
    fig_mark.add_vline(x=0, line_width=1, line_dash="dash", line_color="#263238")
    fig_mark.update_layout(
      height=max(560, 28 * len(view) + 220),
      margin=dict(l=170, r=10, t=92, b=30),
      legend=dict(orientation="h", y=1.08, x=0),
      font=dict(color="#000000", family="Arial, Helvetica, sans-serif"),
    )
    fig_mark.update_xaxes(showgrid=False, tickfont=dict(color="#000000"), title_font=dict(color="#000000"))
    try:
      y_vals = plot_view["marker_pathway_label"].astype(str).tolist()
      fig_mark.update_yaxes(
        tickmode="array",
        tickvals=y_vals,
        ticktext=y_vals,
        title_text="KEGG KO marker | metabolic pathway",
        tickfont=dict(color="#000000", size=12, family="Arial, Helvetica, sans-serif"),
        title_font=dict(color="#000000"),
      )
      fig_mark.update_xaxes(tickfont=dict(color="#000000"), title_font=dict(color="#000000"))
    except Exception:
      pass
    render_plotly_downloadable(fig_mark, key=f"amazonia_iron_marker_highlights_{side}", basename=f"amazonia_iron_marker_highlights_{side}")
    st.caption(txt(
      "Legenda: a comparação é AM/TI/TIA/VI contra todos os grupos externos ST8 presentes na matriz final. log2 ratio positivo = maior média nas lagoas amazônicas; negativo = maior média no painel externo. Marcadores contrastantes são ranqueados pela magnitude absoluta do log2 ratio. Script: amazonia_vs_iron_marker_summary() em app.py/streamlit_app.py; input principal: Supplementary Table 8 — ST8 — all KO biomarkers. Não é teste estatístico.",
      "Legend: the comparison is AM/TI/TIA/VI versus all external ST8 groups present in the final matrix. Positive log2 ratio = higher mean in Amazonian lakes; negative = higher mean in the external panel. Contrasting markers are ranked by the absolute magnitude of the log2 ratio. Script: amazonia_vs_iron_marker_summary() in app.py/streamlit_app.py; main input: Supplementary Table 8 — ST8 — all KO biomarkers. This is not a statistical test."
    ))
    show_table(view, "highlighted_amazonia_iron_markers", height=430)
    csv_button(marker_summary, "highlighted_KO_markers_Amazonia_vs_iron_rich_environments.csv", txt("Baixar todos os marcadores destacados", "Download all highlighted markers"))
  else:
    st.info(txt("Não foi possível calcular destaques porque faltam colunas numéricas ou metadados de grupo.", "Could not calculate highlights because numeric columns or group metadata are missing."))

  st.divider()
  st.markdown("### " + txt("Resultado — contagens KO dos biomarcadores de ciclos biogeoquímicos", "Results — KO counts for biogeochemical-cycle biomarkers"))
  st.info(txt(
    "Para evitar duplicação, o heatmap principal foi consolidado abaixo em Supplementary Table 8, com duas versões: contagem normal e z-score por KO. A tabela exata continua disponível para download.",
    "To avoid duplication, the main heatmap is consolidated below under Supplementary Table 8, with two versions: raw counts and per-KO z-score. The exact table remains available for download."
  ))

  st.markdown("#### " + txt("Supplementary Table 8 — matrizes, metadados e subsets", "Supplementary Table 8 — matrices, metadata and subsets"))
  st.caption(txt(
    "As cinco abas abaixo usam nomes curtos para evitar sobreposição visual; cada aba lê uma planilha diferente da Supplementary Table 8 e mostra o nome exato da aba usada.",
    "The five tabs below use short names to avoid visual overlap; each tab reads a different Supplementary Table 8 sheet and shows the exact sheet name used."
  ))
  comparison_tabs = st.tabs([
    "ST8 — all KO biomarkers",
    "ST8 — selected sediments",
    "ST8 — iron KO markers",
    "ST8 — iron selected sediments",
    "ST8 — IMG/M metadata",
  ])

  with comparison_tabs[0]:
    full_cns, full_numeric_cols = counts_table("table8", ST8_ALL_KO_SHEET, ["KO", "Metabolism", "KO description"])
    full_cns = with_kegg_links(full_cns, "KO")
    show_comparison_ko_pathway = st.checkbox(
      txt("Mostrar a via após o identificador KO", "Show pathway after the KO identifier"),
      value=True,
      key="comparison_st8_all_ko_show_pathway",
    )
    if show_comparison_ko_pathway:
      full_cns = add_marker_pathway_label(full_cns, "KO", "Metabolism")
    else:
      full_cns["marker_pathway_label"] = full_cns["KO"].fillna("").astype(str).str.strip()
    st.markdown(f"##### Supplementary Table 8 — exact sheet: `{ST8_ALL_KO_SHEET}`")
    st.caption(txt(
      "Matriz completa de biomarcadores KO para C, N, S, CH4, fotossíntese e fosforilação anaeróbia em todas as lagoas/ambientes.",
      "Complete KO-biomarker matrix for C, N, S, CH4, photosynthesis and anaerobic phosphorylation across all lakes/environments."
    ))
    meta_label = figure11_environment_metadata()
    x_label_map = environment_column_label_map(meta_label)
    render_st8_heatmap_scope_controls(full_cns, full_numeric_cols, "marker_pathway_label", "ST8 — all KO biomarkers", "st8_all_ko_biomarkers", x_label_map=x_label_map)
    complete_table_note(full_cns, "KOs", "KOs")
    show_table(full_cns, "st8_all_ko_biomarkers_table", height=680)
    csv_button(full_cns, "ST8_all_KO_biomarkers.csv", "Download ST8 all KO biomarker matrix")
    with st.expander("Column metadata linked to ST8 — all KO biomarkers", expanded=False):
      show_table(meta_label, "st8_all_ko_column_metadata", height=420)
      csv_button(meta_label, "ST8_all_KO_biomarkers_column_metadata.csv", "Download linked column metadata")

  with comparison_tabs[1]:
    selected_full, selected_full_cols = counts_table("table8", ST8_ALL_KO_SHEET, ["KO", "Metabolism", "KO description"])
    selected_cns, selected_numeric_cols = _st8_sediment_subset_from_full(selected_full, selected_full_cols)
    selected_cns = with_kegg_links(selected_cns, "KO")
    selected_cns = add_marker_pathway_label(selected_cns, "KO", "Metabolism")
    st.markdown("##### Supplementary Table 8 — sediment subset derived from the complete ST8 matrix")
    st.caption(txt(
      "Subset reproduzível: todas as 20 amostras sedimentares das lagoas e somente os registros externos classificados como Sediment nos metadados completos da ST8.",
      "Reproducible subset: all 20 sediment samples from the lakes and only external records classified as Sediment in the complete ST8 metadata."
    ))
    meta_selected = figure11_environment_metadata()
    x_label_map_selected = environment_column_label_map(meta_selected)
    render_st8_heatmap_scope_controls(selected_cns, selected_numeric_cols, "marker_pathway_label", "ST8 — selected sediments", "st8_selected_sediments", x_label_map=x_label_map_selected)
    complete_table_note(selected_cns, "KOs", "KOs")
    show_table(selected_cns, "st8_selected_sediments_table", height=680)
    csv_button(selected_cns, "ST8_selected_sediments.csv", "Download ST8 selected sediments KO matrix")

  with comparison_tabs[2]:
    fe_all, fe_all_cols = counts_table("table8", ST8_IRON_ALL_SHEET, ["Function Id", "Biologic Role", "Function Name"])
    fe_all = with_kegg_links(fe_all, "Function Id")
    fe_all = add_marker_pathway_label(fe_all, "Function Id", "Biologic Role")
    st.markdown(f"##### Supplementary Table 8 — exact sheet: `{ST8_IRON_ALL_SHEET}`")
    st.caption(txt(
      "Matriz completa de marcadores KO de metabolismo de ferro para todas as lagoas/ambientes.",
      "Complete iron-metabolism KO-marker matrix across all lakes/environments."
    ))
    fe_x_label_map = environment_column_label_map(figure11_environment_metadata())
    render_st8_heatmap_scope_controls(fe_all, fe_all_cols, "marker_pathway_label", "ST8 — iron metabolism KO markers", "st8_iron_all", x_label_map=fe_x_label_map)
    complete_table_note(fe_all, "KOs de ferro", "iron KOs")
    show_table(fe_all, "st8_iron_all_table", height=680)
    csv_button(fe_all, "ST8_iron_metabolism_KO_marker.csv", "Download ST8 iron-metabolism KO-marker matrix")

  with comparison_tabs[3]:
    fe_selected_full, fe_selected_full_cols = counts_table("table8", ST8_IRON_ALL_SHEET, ["Function Id", "Biologic Role", "Function Name"])
    fe_sel, fe_sel_cols = _st8_sediment_subset_from_full(fe_selected_full, fe_selected_full_cols)
    fe_sel = with_kegg_links(fe_sel, "Function Id")
    fe_sel = add_marker_pathway_label(fe_sel, "Function Id", "Biologic Role")
    st.markdown("##### Supplementary Table 8 — iron-marker sediment subset derived from the complete ST8 matrix")
    st.caption(txt(
      "Subset reproduzível de marcadores de ferro: todas as 20 amostras sedimentares das lagoas e somente registros externos classificados como Sediment.",
      "Reproducible iron-marker subset: all 20 sediment lake samples and only external records classified as Sediment."
    ))
    fe_sel_x_label_map = environment_column_label_map(figure11_environment_metadata())
    render_st8_heatmap_scope_controls(fe_sel, fe_sel_cols, "marker_pathway_label", "ST8 — iron metabolism selected sediments", "st8_iron_selected", x_label_map=fe_sel_x_label_map)
    complete_table_note(fe_sel, "KOs de ferro", "iron KOs")
    show_table(fe_sel, "st8_iron_selected_table", height=680)
    csv_button(fe_sel, "ST8_iron_metabolism_selected.csv", "Download ST8 iron-metabolism selected matrix")

  with comparison_tabs[4]:
    full_meta = iron_rich_environment_metadata()
    st.caption("Metadata for all environments derived from the Supplementary Table 8 Iron-rich-environment sheet. This metadata was exported from IMG/M/JGI-associated records and linked to the KO count matrices by sample/environment name when possible.")
    meta_fig, meta_matrix = st8_metadata_availability_heatmap(full_meta, zscore_rows=False)
    meta_z_fig, meta_z_matrix = st8_metadata_availability_heatmap(full_meta, zscore_rows=True)
    if meta_fig is not None:
      render_plotly_downloadable(meta_fig, key="st8_imgm_metadata_availability_heatmap_raw", basename="ST8_IMG_M_metadata_availability_raw")
      render_plotly_downloadable(meta_z_fig, key="st8_imgm_metadata_availability_heatmap_zscore", basename="ST8_IMG_M_metadata_availability_row_zscore")
      st.caption(txt(
        "Legenda: no painel raw, verde=campo disponível e cinza=ausente. No painel z-score, z=(valor−média da linha)/desvio-padrão da linha; a disponibilidade 0/1 original permanece no hover. As escalas ficam alinhadas à primeira linha e menores que a matriz.",
        "Legend: in the raw panel, green=available and gray=missing. In the z-score panel, z=(value−row mean)/row standard deviation; original 0/1 availability remains in hover text. Colour scales are aligned to the first row and remain shorter than the matrix."
      ))
      cmeta1, cmeta2 = st.columns(2)
      with cmeta1:
        csv_button(meta_matrix, "ST8_IMG_M_metadata_availability_raw_matrix.csv", "Download raw metadata availability matrix")
      with cmeta2:
        csv_button(meta_z_matrix, "ST8_IMG_M_metadata_availability_row_zscore_matrix.csv", "Download metadata row-z-score matrix")
    complete_table_note(full_meta, "registros de metadados", "metadata records")
    show_table(full_meta, "iron_rich_environment_metadata_all_environmental_data_tab", height=680)
    csv_button(full_meta, "Iron-rich-environment-metadata-all-environmental-data.csv", "Download Supplementary Table 8 IMG/M metadata for all iron-rich environments")

  iron_fe_comparison_panel()



def iron_fe_comparison_panel():
  st.divider()
  st.markdown("### " + txt("Metabolismo de ferro — marcadores KO em lagoas lateríticas amazônicas e ambientes ricos em ferro", "Iron metabolism — KO markers in Amazonian lateritic lakes and iron-rich environments"))
  st.caption(txt(
    "Fonte: Supplementary Table 8, matriz de marcadores KO de metabolismo de ferro. A tabela foi baixada do conjunto IMG/M/JGI usado no artigo e as contagens são exibidas exatamente como na planilha, com links para KEGG quando o KO está disponível. Os contrastes mostrados nesta seção são descritivos e foram calculados a partir das médias por grupo amazônico versus painel externo, conforme o script citado na legenda de cada gráfico.",
    "Source: Supplementary Table 8, iron-metabolism KO-marker matrix. The table comes from the IMG/M/JGI dataset used in the article and counts are displayed exactly as in the spreadsheet, with KEGG links when a KO is available. The contrasts shown in this section are descriptive and were calculated from group means for the Amazonian lakes versus the external panel, as stated in each figure legend."
  ))
  fe_df, fe_cols = res_ko_fe_reduzido_table()
  if fe_df.empty or not fe_cols:
    st.warning(txt("A matriz de marcadores KO de metabolismo de ferro não foi encontrada ou não possui colunas numéricas.", "The iron-metabolism KO-marker matrix was not found or has no numeric columns."))
    return

  fe_df = add_marker_pathway_label(fe_df, "Function Id", "Biologic Role")
  fe_summary = iron_fe_marker_summary()
  if not fe_summary.empty:
    c1, c2 = st.columns(2)
    broad = fe_summary.sort_values(["Broad iron-rich score", "Total count — all iron-rich environments"], ascending=[False, False]).head(12)
    amazon = fe_summary.sort_values(["Amazonian-lake score", "log2 ratio — Amazonia vs other"], ascending=[False, False]).head(12)
    with c1:
      st.markdown("#### " + txt("Marcadores mais relevantes em todos os ambientes ricos em ferro", "Most relevant markers across iron-rich environments"))
      show_table(broad[[c for c in ["Function Id", "Biologic Role", "Function Name", "Detection fraction — all environments", "Total count — all iron-rich environments", "Broad iron-rich score", "kegg_url"] if c in broad.columns]], "iron_fe_broad_markers", height=360)
    with c2:
      st.markdown("#### " + txt("Marcadores mais associados às lagoas lateríticas amazônicas", "Markers most associated with Amazonian lateritic lakes"))
      show_table(amazon[[c for c in ["Function Id", "Biologic Role", "Function Name", "Mean count — Amazonian lateritic lakes", "Mean count — other iron-rich environments", "log2 ratio — Amazonia vs other", "Amazonian-lake score", "kegg_url"] if c in amazon.columns]], "iron_fe_amazon_markers", height=360)

    st.info(txt(
      "Como os dois rankings são obtidos: 'Broad across iron-rich environments' combina log10 da abundância total com a fração de ambientes em que o marcador foi detectado, favorecendo marcadores amplos e recorrentes. 'Amazonian lateritic lakes' combina somente o componente positivo de log2((média amazônica + 1)/(média externa + 1)), a abundância média amazônica e a fração de detecção nas 20 amostras amazônicas, favorecendo marcadores relativamente mais representados nas lagoas. Ambos são escores descritivos, não testes de significância.",
      "How the rankings are obtained: 'Broad across iron-rich environments' combines log10 total abundance with the fraction of environments in which the marker was detected, favouring widespread recurrent markers. 'Amazonian lateritic lakes' combines only the positive component of log2((Amazonian mean + 1)/(external mean + 1)), Amazonian mean abundance and detection fraction across the 20 Amazonian samples, favouring markers relatively more represented in the lakes. Both are descriptive scores, not significance tests."
    ))

    view_scope = st.radio(
      txt("Selecionar ranking para gráfico", "Select ranking for chart"),
      ["Broad across iron-rich environments", "Amazonian lateritic lakes"],
      horizontal=True,
      key="iron_fe_marker_scope",
    )
    if view_scope == "Broad across iron-rich environments":
      plot_df = add_marker_pathway_label(broad.sort_values("Broad iron-rich score"), "Function Id", "Biologic Role")
      x = "Broad iron-rich score"
      title = txt("Marcadores de ferro amplamente detectados no painel de ambientes ricos em ferro — marcador e via/atividade", "Iron markers broadly detected across the iron-rich environment panel — marker and pathway/activity")
    else:
      plot_df = add_marker_pathway_label(amazon.sort_values("Amazonian-lake score"), "Function Id", "Biologic Role")
      x = "Amazonian-lake score"
      title = txt("Marcadores de ferro com maior perfil nas lagoas lateríticas amazônicas — marcador e via/atividade", "Iron markers with stronger profile in Amazonian lateritic lakes — marker and pathway/activity")
    fig_sum = px.bar(
      plot_df,
      x=x,
      y="marker_pathway_label",
      color="Biologic Role",
      orientation="h",
      hover_data=["Function Id", "Biologic Role", "Function Name", "kegg_url"],
      labels={"marker_pathway_label": "KO marker | iron pathway/activity"},
      title="",
      color_discrete_sequence=["#00796B", "#F9A825", "#1565C0", "#6A1B9A", "#C62828", "#455A64"],
    )
    fig_sum.update_layout(
      height=max(520, 34 * len(plot_df) + 180),
      margin=dict(l=10, r=10, t=82, b=30),
      legend=dict(orientation="h", y=1.08, x=0),
      font=dict(color="#000000", family="Arial, Helvetica, sans-serif"),
    )
    fig_sum.update_xaxes(showgrid=False, tickfont=dict(color="#000000"), title_font=dict(color="#000000"))
    fig_sum.update_yaxes(showgrid=False, tickfont=dict(color="#000000"), title_font=dict(color="#000000"))
    render_plotly_downloadable(fig_sum, key=f"iron_fe_marker_ranking_{view_scope}", basename=f"iron_fe_marker_ranking_{view_scope}")
    if view_scope == "Broad across iron-rich environments":
      st.caption(txt(
        "Legenda: as barras ranqueiam marcadores de ferro pelo Broad iron-rich score, que combina abundância total e fração de detecção em todo o painel de ambientes ricos em ferro. Input: Supplementary Table 8 — matriz de marcadores KO de ferro. Script: iron_fe_marker_summary() em src/supplementary_database.py; interface: app.py/streamlit_app.py. Output: barplot interativo e tabela CSV completa.",
        "Legend: bars rank iron markers by the Broad iron-rich score, which combines total abundance and detection fraction across the full iron-rich environment panel. Input: Supplementary Table 8 iron KO-marker matrix. Script: iron_fe_marker_summary() in src/supplementary_database.py; interface: app.py/streamlit_app.py. Output: interactive barplot and complete CSV table."
      ))
    else:
      st.caption(txt(
        "Legenda: as barras ranqueiam marcadores de ferro pelo Amazonian-lake score, que combina maior média nas lagoas AM/TI/TIA/VI, log2 ratio positivo em relação ao painel externo e fração de detecção nas amostras amazônicas. Input: Supplementary Table 8 — matriz de marcadores KO de ferro. Script: iron_fe_marker_summary() em src/supplementary_database.py; interface: app.py/streamlit_app.py. Output: barplot interativo e tabela CSV completa.",
        "Legend: bars rank iron markers by the Amazonian-lake score, combining higher mean abundance in AM/TI/TIA/VI, a positive log2 ratio relative to the external panel and detection fraction in Amazonian samples. Input: Supplementary Table 8 iron KO-marker matrix. Script: iron_fe_marker_summary() in src/supplementary_database.py; interface: app.py/streamlit_app.py. Output: interactive barplot and complete CSV table."
      ))
    csv_button(fe_summary, "iron_metabolism_marker_summary_Amazonia_vs_iron_rich_environments.csv", txt("Baixar ranking completo de marcadores de ferro", "Download complete iron-marker ranking"))

  st.info(txt(
    "Os heatmaps de metabolismo de ferro não são repetidos aqui para evitar duplicação. A matriz completa e a matriz selecionada de ferro aparecem nas abas `ST8 — iron KO markers` e `ST8 — iron selected`, cada uma com contagem raw e z-score.",
    "Iron-metabolism heatmaps are not repeated here to avoid duplication. The complete and selected iron matrices are shown in the `ST8 — iron KO markers` and `ST8 — iron selected` tabs, each with raw counts and z-score."
  ))

  ztab = iron_fe_zscore_table(selected=False)
  if not ztab.empty:
    with st.expander(txt("Tabela z-score da matriz completa de ferro", "Z-score table for the complete iron matrix"), expanded=False):
      show_table(ztab, "iron_fe_complete_zscore_table", height=520)
      csv_button(ztab, "ST8_iron_metabolism_KO_marker_zscore.csv", txt("Baixar z-score completo de ferro", "Download complete iron z-score table"))

  ztab_sel = iron_fe_zscore_table(selected=True)
  if not ztab_sel.empty:
    with st.expander(txt("Tabela z-score da matriz selecionada de ferro", "Z-score table for the selected iron matrix"), expanded=False):
      show_table(ztab_sel, "iron_fe_selected_zscore_table", height=520)
      csv_button(ztab_sel, "ST8_iron_metabolism_selected_zscore.csv", txt("Baixar z-score selecionado de ferro", "Download selected iron z-score table"))



def window_from_collection_date(collection_date: pd.Timestamp, mode: str) -> tuple[date, date]:
  d = pd.to_datetime(collection_date).date()
  if mode == "Exact collection day":
    return d, d
  if mode == "±3 days":
    return d - timedelta(days=3), d + timedelta(days=3)
  if mode == "±7 days":
    return d - timedelta(days=7), d + timedelta(days=7)
  if mode == "±15 days":
    return d - timedelta(days=15), d + timedelta(days=15)
  if mode == "±30 days":
    return d - timedelta(days=30), d + timedelta(days=30)
  if mode == "Collection month":
    start = d.replace(day=1)
    end = date(d.year, 12, 31) if d.month == 12 else (d.replace(month=d.month + 1, day=1) - timedelta(days=1))
    return start, end
  if mode == "Collection year":
    return date(d.year, 1, 1), date(d.year, 12, 31)
  return d, d


def add_sample_columns(df: pd.DataFrame, sample_row: pd.Series) -> pd.DataFrame:
  out = df.copy()
  out["sample_id"] = sample_display_id(sample_row)
  out["environment_feature"] = display_text(sample_row, ["environment_feature", "habitat", "specific_ecosystem"], "")
  out["lake"] = display_text(sample_row, ["lake"], "")
  out["season"] = display_text(sample_row, ["season"], "")
  out["collection_date"] = sample_row.get("collection_date")
  if "lat" not in out.columns:
    out["lat"] = sample_row.get("lat")
  if "lon" not in out.columns:
    out["lon"] = sample_row.get("lon")
  return out


def _sample_context_from_df(df: pd.DataFrame) -> dict:
  if df is None or df.empty:
    return {"sample_id": "sample", "environment": "", "coord_text": "coordinates unavailable"}
  row = df.iloc[0]
  sample_id = str(row.get("sample_id", "sample"))
  environment = str(row.get("environment_feature") or row.get("lake") or row.get("season") or "").strip()
  lat = pd.to_numeric(pd.Series([row.get("lat")]), errors="coerce").iloc[0]
  lon = pd.to_numeric(pd.Series([row.get("lon")]), errors="coerce").iloc[0]
  if pd.notna(lat) and pd.notna(lon):
    coord_text = f"lat {lat:.5f}, lon {lon:.5f}"
  else:
    coord_text = "coordinates unavailable"
  return {"sample_id": sample_id, "environment": environment, "coord_text": coord_text}


ENVIRONMENTAL_FRIENDLY_LABELS = {
  "T2M": "Air temperature at 2 m (mean, °C)",
  "T2M_MAX": "Air temperature at 2 m (maximum, °C)",
  "T2M_MIN": "Air temperature at 2 m (minimum, °C)",
  "RH2M": "Relative humidity at 2 m (%)",
  "QV2M": "Specific humidity at 2 m (g/kg equivalent NASA variable)",
  "PRECTOTCORR": "Corrected total precipitation (mm/day)",
  "WS2M": "Wind speed at 2 m (m/s)",
  "ALLSKY_SFC_SW_DWN": "All-sky downward shortwave radiation (kWh/m²/day)",
  "CHIRPS_PRECTOT": "CHIRPS precipitation (mm/day)",
  "NDVI": "Normalized Difference Vegetation Index",
  "NDWI": "Normalized Difference Water Index",
  "NDMI": "Normalized Difference Moisture Index",
  "MNDWI": "Modified Normalized Difference Water Index",
  "EVI": "Enhanced Vegetation Index",
  "SAVI": "Soil-Adjusted Vegetation Index",
  "MSAVI": "Modified Soil-Adjusted Vegetation Index",
  "NBR": "Normalized Burn Ratio",
  "NDRE": "Normalized Difference Red Edge",
  "BSI": "Bare Soil Index",
  "VV": "SAR VV backscatter",
  "VH": "SAR VH backscatter",
  "VH_VV_RATIO": "SAR VH/VV ratio",
  "NDI": "SAR normalized difference index",
  "RVI": "Radar Vegetation Index",
}


def friendly_feature_name(name: object) -> str:
  return ENVIRONMENTAL_FRIENDLY_LABELS.get(str(name), str(name))



def environmental_heatmap_matrix(results: dict) -> pd.DataFrame:
  matrices = []
  nasa = results.get("nasa", pd.DataFrame())
  if isinstance(nasa, pd.DataFrame) and not nasa.empty:
    numeric = [c for c in ["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "QV2M", "PRECTOTCORR", "WS2M", "ALLSKY_SFC_SW_DWN"] if c in nasa.columns]
    if numeric:
      tmp = nasa[["sample_id"] + numeric].copy()
      for c in numeric:
        tmp[c] = pd.to_numeric(tmp[c], errors="coerce")
      wide = tmp.groupby("sample_id", dropna=False)[numeric].mean().reset_index().set_index("sample_id")
      wide.columns = [f"NASA | {friendly_feature_name(c)}" for c in wide.columns]
      matrices.append(wide)
  chirps = results.get("chirps", pd.DataFrame())
  if isinstance(chirps, pd.DataFrame) and not chirps.empty and "CHIRPS_PRECTOT" in chirps.columns:
    tmp = chirps[["sample_id", "CHIRPS_PRECTOT"]].copy()
    tmp["CHIRPS_PRECTOT"] = pd.to_numeric(tmp["CHIRPS_PRECTOT"], errors="coerce")
    wide = tmp.groupby("sample_id", dropna=False)[["CHIRPS_PRECTOT"]].mean().reset_index().set_index("sample_id")
    wide.columns = [f"CHIRPS | {friendly_feature_name(c)}" for c in wide.columns]
    matrices.append(wide)
  s2 = results.get("sentinel2", pd.DataFrame())
  if isinstance(s2, pd.DataFrame) and not s2.empty and {"sample_id", "index", "mean"}.issubset(s2.columns):
    tmp = s2[["sample_id", "index", "mean"]].copy()
    tmp["mean"] = pd.to_numeric(tmp["mean"], errors="coerce")
    wide = tmp.pivot_table(index="sample_id", columns="index", values="mean", aggfunc="mean")
    if not wide.empty:
      wide.columns = [f"Sentinel-2 | {friendly_feature_name(c)}" for c in wide.columns]
      matrices.append(wide)
  s1 = results.get("sentinel1", pd.DataFrame())
  if isinstance(s1, pd.DataFrame) and not s1.empty and {"sample_id", "index", "mean"}.issubset(s1.columns):
    tmp = s1[["sample_id", "index", "mean"]].copy()
    tmp["mean"] = pd.to_numeric(tmp["mean"], errors="coerce")
    wide = tmp.pivot_table(index="sample_id", columns="index", values="mean", aggfunc="mean")
    if not wide.empty:
      wide.columns = [f"Sentinel-1 SAR | {friendly_feature_name(c)}" for c in wide.columns]
      matrices.append(wide)
  soil = results.get("soil", pd.DataFrame())
  if isinstance(soil, pd.DataFrame) and not soil.empty and {"sample_id", "property", "value_mean"}.issubset(soil.columns):
    tmp = soil.copy()
    tmp["value_mean"] = pd.to_numeric(tmp["value_mean"], errors="coerce")
    if "depth" in tmp.columns:
      tmp["feature_name"] = tmp["property"].astype(str) + " @ " + tmp["depth"].astype(str)
    else:
      tmp["feature_name"] = tmp["property"].astype(str)
    wide = tmp.pivot_table(index="sample_id", columns="feature_name", values="value_mean", aggfunc="mean")
    if not wide.empty:
      wide.columns = [f"SoilGrids | {c}" for c in wide.columns]
      matrices.append(wide)
  mapbiomas = results.get("mapbiomas", pd.DataFrame())
  if isinstance(mapbiomas, pd.DataFrame) and not mapbiomas.empty and {"sample_id", "class_name", "fraction"}.issubset(mapbiomas.columns):
    tmp = mapbiomas.copy()
    tmp["fraction"] = pd.to_numeric(tmp["fraction"], errors="coerce")
    wide = tmp.pivot_table(index="sample_id", columns="class_name", values="fraction", aggfunc="mean")
    if not wide.empty:
      wide.columns = [f"MapBiomas | {c}" for c in wide.columns]
      matrices.append(wide)
  if not matrices:
    return pd.DataFrame()
  combined = pd.concat(matrices, axis=1, sort=True)
  combined = combined.dropna(axis=1, how="all")
  return combined.sort_index()



def render_environmental_heatmaps(results: dict):
  matrix = environmental_heatmap_matrix(results)
  if matrix.empty:
    st.info("No environmental matrix is available yet for heatmap generation.")
    return
  st.markdown("#### Heatmap across all environments / coordinates")
  st.caption("Rows are coordinates/samples and columns are climate, Sentinel, soil and land-cover variables. This allows visual comparison of all environments in a single panel.")
  raw = matrix.copy()
  raw_plot = raw.fillna(np.nan)
  fig_raw = go.Figure(data=go.Heatmap(
    z=raw_plot.values,
    x=[str(c) for c in raw_plot.columns],
    y=[str(i) for i in raw_plot.index],
    colorscale="Viridis",
    colorbar=dict(title="raw value"),
    hovertemplate="Sample: %{y}<br>Variable: %{x}<br>Value: %{z}<extra></extra>",
  ))
  raw_geom = adaptive_heatmap_geometry(len(raw_plot.index), len(raw_plot.columns), cell_px=28, min_cell_px=20, max_cell_px=34, left_margin=330, bottom_margin=260)
  fig_raw.update_layout(
    title="Environmental heatmap — raw values for all analyses and all environments",
    width=raw_geom["width"], height=raw_geom["height"],
    margin=dict(l=raw_geom["left_margin"], r=raw_geom["right_margin"], t=raw_geom["top_margin"], b=raw_geom["bottom_margin"]),
    xaxis_title="Environmental variables / analyses",
    yaxis_title="Coordinates / samples",
    meta={"preserve_cell_geometry": True, "cell_px": raw_geom["cell_px"]},
  )
  fig_raw.update_traces(xgap=0.7, ygap=0.7)
  fig_raw.update_xaxes(tickangle=-55, automargin=True); fig_raw.update_yaxes(automargin=True)
  render_plotly_downloadable(fig_raw, key="environmental_heatmap_raw", basename="environmental_heatmap_raw")
  z = raw.apply(lambda col: (col - col.mean()) / (col.std(ddof=0) if pd.notna(col.std(ddof=0)) and col.std(ddof=0) not in (0, 0.0) else 1), axis=0)
  z = z.replace([np.inf, -np.inf], np.nan).fillna(0)
  fig_z = go.Figure(data=go.Heatmap(
    z=z.values,
    x=[str(c) for c in z.columns],
    y=[str(i) for i in z.index],
    colorscale="RdBu",
    zmid=0,
    colorbar=dict(title="z-score"),
    hovertemplate="Sample: %{y}<br>Variable: %{x}<br>Z-score: %{z:.3f}<extra></extra>",
  ))
  z_geom = adaptive_heatmap_geometry(len(z.index), len(z.columns), cell_px=28, min_cell_px=20, max_cell_px=34, left_margin=330, bottom_margin=260)
  fig_z.update_layout(
    title="Environmental heatmap — z-score normalized values for all analyses and all environments",
    width=z_geom["width"], height=z_geom["height"],
    margin=dict(l=z_geom["left_margin"], r=z_geom["right_margin"], t=z_geom["top_margin"], b=z_geom["bottom_margin"]),
    xaxis_title="Environmental variables / analyses",
    yaxis_title="Coordinates / samples",
    meta={"preserve_cell_geometry": True, "cell_px": z_geom["cell_px"]},
  )
  fig_z.update_traces(xgap=0.7, ygap=0.7)
  fig_z.update_xaxes(tickangle=-55, automargin=True); fig_z.update_yaxes(automargin=True)
  bold_axis_layout(fig_z, x_size=13, y_size=14, title_size=17)
  render_plotly_downloadable(fig_z, key="environmental_heatmap_zscore", basename="environmental_heatmap_zscore")
  # Unsupervised clustering overview using PCA on the z-score matrix.
  try:
    from sklearn.decomposition import PCA
    coords = PCA(n_components=2, random_state=42).fit_transform(z.values)
    clust = pd.DataFrame({"sample_id": z.index.astype(str), "PC1": coords[:,0], "PC2": coords[:,1]})
    fig_pca = px.scatter(clust, x="PC1", y="PC2", text="sample_id", hover_data=clust.columns, title="Unsupervised environmental PCA — all selected climate/environmental variables")
    fig_pca.update_traces(textposition="top center", marker=dict(size=14, line=dict(width=1, color="white")))
    fig_pca.update_layout(height=560, margin=dict(l=90, r=40, t=90, b=120))
    bold_axis_layout(fig_pca, x_size=14, y_size=14, title_size=17)
    render_plotly_downloadable(fig_pca, key="environmental_unsupervised_pca", basename="environmental_unsupervised_pca")
    show_plot_source_table(clust, "environmental_unsupervised_pca", txt("Coordenadas da análise não supervisionada", "Unsupervised-analysis coordinates"))
  except Exception as exc:
    st.info(f"Environmental PCA could not be computed: {exc}")
  show_table(raw.reset_index().rename(columns={"sample_id": "sample_id"}), "environmental_heatmap_matrix_raw", height=320)



def render_per_coordinate_timeseries(df: pd.DataFrame, dataset_label: str, x_col: str, group_col: str, value_col: str = "mean"):
  if df is None or df.empty or any(c not in df.columns for c in ["sample_id", x_col, group_col, value_col]):
    return
  st.markdown(f"#### {dataset_label} — one chart for each coordinate")
  st.caption("Each figure below is specific to one coordinate/sample. The title states what the graph represents and which environment/coordinate it refers to.")
  for sample_id, sample_df in df.groupby("sample_id", sort=False):
    sample_df = sample_df.copy()
    sample_df[value_col] = pd.to_numeric(sample_df[value_col], errors="coerce")
    sample_df = sample_df.dropna(subset=[value_col])
    if sample_df.empty:
      continue
    ctx = _sample_context_from_df(sample_df)
    sample_df["friendly_group"] = sample_df[group_col].astype(str).map(friendly_feature_name)
    fig = px.line(
      sample_df,
      x=x_col,
      y=value_col,
      color="friendly_group",
      markers=True,
      title=f"{dataset_label} for coordinate/sample {ctx['sample_id']} — {ctx['coord_text']} | environment: {ctx['environment'] or 'not informed'}",
    )
    fig.update_layout(height=500, xaxis_title="Date / interval", yaxis_title="Value")
    render_plotly_downloadable(fig, key=f"{dataset_label}_{sample_id}_per_coordinate".replace(" ", "_"), basename=f"{dataset_label}_{sample_id}_per_coordinate".replace(" ", "_"))



def render_per_coordinate_nasa(df: pd.DataFrame):
  if df is None or df.empty:
    return
  candidate_vars = [c for c in ["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "QV2M", "PRECTOTCORR", "WS2M", "ALLSKY_SFC_SW_DWN"] if c in df.columns]
  if not candidate_vars or "date" not in df.columns or "sample_id" not in df.columns:
    return
  st.markdown("#### NASA POWER — one chart for each coordinate")
  st.caption("For every coordinate/sample, this chart shows daily climate variables from NASA POWER during the selected date window. Use the selector to show one sample, several samples, or all samples.")
  sample_options = sorted(df["sample_id"].dropna().astype(str).unique().tolist())
  selected_samples = st.multiselect(txt("Selecionar amostras/coordenadas NASA POWER", "Select NASA POWER samples/coordinates"), sample_options, default=sample_options, key="nasa_power_per_coordinate_samples")
  df = df[df["sample_id"].astype(str).isin(selected_samples)].copy() if selected_samples else df.iloc[0:0].copy()
  for sample_id, sample_df in df.groupby("sample_id", sort=False):
    ctx = _sample_context_from_df(sample_df)
    long = sample_df[["date"] + candidate_vars].copy().melt(id_vars="date", var_name="variable", value_name="value")
    long["value"] = pd.to_numeric(long["value"], errors="coerce")
    long = long.dropna(subset=["value"])
    if long.empty:
      continue
    long["variable_label"] = long["variable"].map(friendly_feature_name)
    fig = px.line(
      long,
      x="date",
      y="value",
      color="variable_label",
      markers=True,
      title=f"NASA POWER daily climate for coordinate/sample {ctx['sample_id']} — {ctx['coord_text']} | environment: {ctx['environment'] or 'not informed'}",
    )
    fig.update_layout(height=520, xaxis_title="Date", yaxis_title="Observed value")
    render_plotly_downloadable(fig, key=f"nasa_power_{sample_id}_per_coordinate", basename=f"nasa_power_{sample_id}_per_coordinate")



def render_per_coordinate_chirps(df: pd.DataFrame):
  if df is None or df.empty or not {"sample_id", "date", "CHIRPS_PRECTOT"}.issubset(df.columns):
    return
  st.markdown("#### CHIRPS precipitation — one chart for each coordinate")
  st.caption("For every coordinate/sample, this chart shows daily precipitation from CHIRPS for the selected period.")
  for sample_id, sample_df in df.groupby("sample_id", sort=False):
    sample_df = sample_df.copy()
    sample_df["CHIRPS_PRECTOT"] = pd.to_numeric(sample_df["CHIRPS_PRECTOT"], errors="coerce")
    sample_df = sample_df.dropna(subset=["CHIRPS_PRECTOT"])
    if sample_df.empty:
      continue
    ctx = _sample_context_from_df(sample_df)
    fig = px.bar(
      sample_df,
      x="date",
      y="CHIRPS_PRECTOT",
      title=f"CHIRPS daily precipitation for coordinate/sample {ctx['sample_id']} — {ctx['coord_text']} | environment: {ctx['environment'] or 'not informed'}",
    )
    fig.update_layout(height=460, xaxis_title="Date", yaxis_title="Precipitation (mm/day)")
    render_plotly_downloadable(fig, key=f"chirps_{sample_id}_per_coordinate", basename=f"chirps_{sample_id}_per_coordinate")



def render_per_coordinate_soil(df: pd.DataFrame):
  if df is None or df.empty or not {"sample_id", "property", "value_mean"}.issubset(df.columns):
    return
  st.markdown("#### SoilGrids — one chart for each coordinate")
  st.caption("For every coordinate/sample, this chart shows the predicted soil properties for each available depth layer.")
  for sample_id, sample_df in df.groupby("sample_id", sort=False):
    sample_df = sample_df.copy()
    sample_df["value_mean"] = pd.to_numeric(sample_df["value_mean"], errors="coerce")
    sample_df = sample_df.dropna(subset=["value_mean"])
    if sample_df.empty:
      continue
    ctx = _sample_context_from_df(sample_df)
    if "depth" in sample_df.columns:
      sample_df["property_depth"] = sample_df["property"].astype(str) + " @ " + sample_df["depth"].astype(str)
      x_col = "property_depth"
    else:
      x_col = "property"
    fig = px.bar(
      sample_df,
      x=x_col,
      y="value_mean",
      color="property",
      title=f"SoilGrids properties for coordinate/sample {ctx['sample_id']} — {ctx['coord_text']} | environment: {ctx['environment'] or 'not informed'}",
    )
    fig.update_layout(height=520, xaxis_title="Soil property and depth", yaxis_title="Predicted mean value", xaxis_tickangle=-45)
    render_plotly_downloadable(fig, key=f"soilgrids_{sample_id}_per_coordinate", basename=f"soilgrids_{sample_id}_per_coordinate")



def render_per_coordinate_mapbiomas(df: pd.DataFrame):
  if df is None or df.empty or not {"sample_id", "class_name", "fraction"}.issubset(df.columns):
    return
  st.markdown("#### MapBiomas land cover — one chart for each coordinate")
  st.caption("For every coordinate/sample, this chart shows the fraction of each MapBiomas land-use/land-cover class in the selected buffer/geometry.")
  for sample_id, sample_df in df.groupby("sample_id", sort=False):
    sample_df = sample_df.copy()
    sample_df["fraction"] = pd.to_numeric(sample_df["fraction"], errors="coerce")
    sample_df = sample_df.dropna(subset=["fraction"])
    if sample_df.empty:
      continue
    ctx = _sample_context_from_df(sample_df)
    fig = px.bar(
      sample_df.sort_values("fraction", ascending=False),
      x="class_name",
      y="fraction",
      title=f"MapBiomas land-cover fractions for coordinate/sample {ctx['sample_id']} — {ctx['coord_text']} | environment: {ctx['environment'] or 'not informed'}",
    )
    fig.update_layout(height=500, xaxis_title="Land-cover class", yaxis_title="Fraction", xaxis_tickangle=-45)
    render_plotly_downloadable(fig, key=f"mapbiomas_{sample_id}_per_coordinate", basename=f"mapbiomas_{sample_id}_per_coordinate")


def line_plot(df: pd.DataFrame, date_col: str, value_cols: List[str], title: str):
  existing = [c for c in value_cols if c in df.columns]
  if not existing or df.empty:
    return
  work = df.copy()
  if "sample_id" in work.columns:
    samples = sorted(work["sample_id"].dropna().astype(str).unique().tolist())
    selected_samples = st.multiselect(
      txt("Selecionar amostras/coordenadas para este gráfico", "Select samples/coordinates for this chart"),
      samples,
      default=samples,
      key=f"select_samples_{safe_filename(title)}",
    )
    if selected_samples:
      work = work[work["sample_id"].astype(str).isin(selected_samples)].copy()
  id_vars = [date_col] + (["sample_id"] if "sample_id" in work.columns else [])
  long = work[id_vars + existing].melt(id_vars=id_vars, var_name="variable", value_name="value")
  long["value"] = pd.to_numeric(long["value"], errors="coerce")
  long = long.dropna(subset=["value"])
  if long.empty:
    return
  color_col = "variable"
  line_group = "sample_id" if "sample_id" in long.columns else None
  fig = px.line(long, x=date_col, y="value", color=color_col, line_dash=line_group, markers=True, hover_data=long.columns, title=title)
  fig.update_layout(height=620, margin=dict(l=90, r=40, t=90, b=140))
  bold_axis_layout(fig, x_size=14, y_size=14, title_size=17)
  render_plotly_downloadable(fig, key=f"line_plot_{re.sub(r'[^A-Za-z0-9_]+', '_', title)[:80]}", basename=f"line_plot_{re.sub(r'[^A-Za-z0-9_]+', '_', title)[:80]}")
  show_plot_source_table(work, f"line_plot_{re.sub(r'[^A-Za-z0-9_]+', '_', title)[:80]}", txt("Tabela usada neste gráfico", "Table used in this chart"))



def nasa_power_glossary_table() -> pd.DataFrame:
  rows = []
  for code in NASA_POWER_DEFAULT_PARAMS:
    info = NASA_POWER_PARAMETER_DICTIONARY.get(code, {})
    rows.append({
      "code": code,
      "nome_em_portugues": info.get("pt_name", code),
      "english_name": info.get("name", code),
      "unit": info.get("unit", ""),
      "como_interpretar": info.get("meaning", ""),
    })
  return pd.DataFrame(rows)


def show_nasa_power_glossary():
  with st.expander("📘 Dicionário NASA POWER — o que significam T2M, RH2M, QV2M etc.", expanded=False):
    st.markdown(txt(
      "`RH2M` significa **umidade relativa do ar a 2 metros da superfície**. O valor é dado em `%`: quanto maior, mais úmido está o ar próximo ao solo/água. Este dicionário evita que códigos técnicos da NASA apareçam sem explicação.",
      "`RH2M` means **relative humidity at 2 metres above the surface**. It is expressed in `%`: higher values mean more humid near-surface air. This dictionary prevents NASA technical codes from appearing without explanation."
    ))
    show_table(nasa_power_glossary_table(), "nasa_power_parameter_dictionary", height=330)


def add_biplot_vectors_to_figure(fig, vectors: pd.DataFrame, x_axis: str, y_axis: str, trace_name: str = "biplot vectors"):
  if fig is None or vectors is None or vectors.empty:
    return fig
  try:
    x_values = []
    y_values = []
    for tr in fig.data:
      if hasattr(tr, "x") and hasattr(tr, "y") and tr.x is not None and tr.y is not None:
        x_values.extend([float(v) for v in tr.x if pd.notna(v)])
        y_values.extend([float(v) for v in tr.y if pd.notna(v)])
    x_span = (max(x_values) - min(x_values)) if len(x_values) >= 2 else 2.0
    y_span = (max(y_values) - min(y_values)) if len(y_values) >= 2 else 2.0
    scale = 0.34 * max(x_span, y_span, 1e-9)
  except Exception:
    scale = 1.0
  palette = px.colors.qualitative.Dark24
  categories = list(vectors.get("feature_category", pd.Series([trace_name])).astype(str).unique())
  color_map = {cat: palette[i % len(palette)] for i, cat in enumerate(categories)}
  for _, row in vectors.iterrows():
    vx = float(row.get("vector_x", 0) or 0) * scale
    vy = float(row.get("vector_y", 0) or 0) * scale
    label = str(row.get("feature_label", row.get("feature", "feature")))
    cat = str(row.get("feature_category", trace_name))
    color = color_map.get(cat, "black")
    fig.add_trace(go.Scatter(
      x=[0, vx],
      y=[0, vy],
      mode="lines+markers+text",
      text=["", label],
      textposition="top center",
      marker=dict(size=[1, 8], color=color),
      line=dict(width=2, color=color),
      name=cat,
      hovertemplate=f"{html_lib.escape(label)}<br>{x_axis}: {row.get('vector_x', np.nan):.3f}<br>{y_axis}: {row.get('vector_y', np.nan):.3f}<extra>{html_lib.escape(cat)}</extra>",
      showlegend=True,
      cliponaxis=False,
    ))
  fig.update_layout(legend=dict(title_text="", orientation="h", yanchor="top", y=-0.28, xanchor="center", x=0.5))
  return fig


def test_environmental_api_connections() -> pd.DataFrame:
  """Run lightweight connectivity tests for public/environmental sources.

  The test reports authentication, elapsed response time and rows returned. It
  never creates simulated environmental values.
  """
  rows = []
  lat, lon = -6.3, -50.1
  test_start = "2020-03-01"
  test_end = "2020-03-02"

  def add(source, group, ok, message="", rows_returned=0, requires_credentials="No", auth_status="not required", start_ts=None):
    elapsed = time.time() - start_ts if start_ts else np.nan
    rows.append({
      "source": source,
      "group": group,
      "connection_status": "connected" if ok else "not connected",
      "requires_credentials": requires_credentials,
      "auth_status": auth_status,
      "response_seconds": round(float(elapsed), 2) if pd.notna(elapsed) else np.nan,
      "rows_returned_in_test": int(rows_returned or 0),
      "message": str(message)[:700],
      "last_tested_at": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
      "data_policy": "Connectivity/status test only; no simulated data generated.",
    })

  started = time.time()
  try:
    df = fetch_nasa_power_daily(lat, lon, test_start, test_end, parameters=["T2M", "RH2M"], use_cache=True)
    add("NASA POWER", "Climate", not df.empty, f"Daily climate endpoint responded; rows={len(df)}", len(df), start_ts=started)
  except Exception as exc:
    add("NASA POWER", "Climate", False, exc, start_ts=started)

  started = time.time()
  chirps_status = test_chirps_climateserv_connection(lat, lon, test_start, buffer_m=1000, timeout_s=90)
  add(
    "CHIRPS / ClimateSERV",
    "Climate",
    bool(chirps_status.get("ok")),
    f"{chirps_status.get('message', '')} Endpoint: {chirps_status.get('endpoint_submit', '')}",
    chirps_status.get("rows_returned", 0),
    start_ts=started,
  )

  started = time.time()
  token_ok = False
  try:
    token = _copernicus_token()
    token_ok = bool(token)
    msg = "Copernicus/Sentinel Hub OAuth token acquired for the current Streamlit session."
    add("Copernicus OAuth token", "Sentinel-1/Sentinel-2", token_ok, msg, 1 if token_ok else 0, "Yes", "authenticated" if token_ok else "missing token", started)
  except Exception as exc:
    add("Copernicus OAuth token", "Sentinel-1/Sentinel-2", False, exc, 0, "Yes", "missing or invalid credentials", started)
  # Sentinel-1 and Sentinel-2 use the same token. The full downloads are tested when the user requests layers.
  add("Sentinel-2 L2A Statistical API", "Sentinel-2", token_ok, "Ready to query if token is connected; actual spectral-index download is run on selected dates/coordinates.", 0, "Yes", "authenticated" if token_ok else "waiting for Copernicus credentials")
  add("Sentinel-1 GRD Statistical API", "Sentinel-1 SAR", token_ok, "Ready to query if token is connected; actual SAR download is run on selected dates/coordinates.", 0, "Yes", "authenticated" if token_ok else "waiting for Copernicus credentials")

  started = time.time()
  try:
    df = fetch_soilgrids_point(lat, lon, properties=["clay"], depths=["0-5cm"], use_cache=True)
    add("SoilGrids / ISRIC", "SoilGrids", not df.empty, f"SoilGrids endpoint responded; rows={len(df)}", len(df), start_ts=started)
  except Exception as exc:
    add("SoilGrids / ISRIC", "SoilGrids", False, exc, start_ts=started)

  started = time.time()
  try:
    auth = earthdata_auth_status()
    add(
      "NASA Earthdata auth",
      "NASA Earthdata / CMR",
      bool(auth.get("configured")),
      f"Method: {auth.get('method')}. Token present: {auth.get('token_present')}; netrc configured: {auth.get('netrc_has_urs')}. No secret value is displayed.",
      1 if auth.get("configured") else 0,
      "Yes",
      "configured" if auth.get("configured") else "missing EARTHDATA_TOKEN or ~/.netrc",
      started,
    )
  except Exception as exc:
    add("NASA Earthdata auth", "NASA Earthdata / CMR", False, exc, 0, "Yes", "not configured", started)

  started = time.time()
  try:
    collections = search_earthdata_collections("imerg_daily", max_collections=3, use_cache=True)
    ok = not collections.empty and collections.get("query_status", pd.Series(dtype=str)).astype(str).eq("ok").any()
    add("NASA CMR / GES DISC IMERG", "NASA Earthdata / CMR", ok, f"CMR collection search returned {len(collections)} rows.", len(collections), "Optional for metadata; required for protected downloads", "ready" if ok else "not found", started)
  except Exception as exc:
    add("NASA CMR / GES DISC IMERG", "NASA Earthdata / CMR", False, exc, 0, "Optional for metadata; required for protected downloads", "query failed", started)

  started = time.time()
  try:
    df = fetch_mapbiomas_gee_landcover(lat, lon, year=2020, buffer_m=1000, use_cache=True)
    add("MapBiomas / Google Earth Engine", "MapBiomas", not df.empty, f"MapBiomas/GEE responded; rows={len(df)}", len(df), "Google Earth Engine", "authenticated", started)
  except Exception as exc:
    add("MapBiomas / Google Earth Engine", "MapBiomas", False, exc, 0, "Google Earth Engine", "not authenticated or asset unavailable", started)

  return pd.DataFrame(rows)


def environmental_connection_center(results: dict | None = None):
  results = results or {}
  with st.expander("🔌 Status das conexões ambientais, credenciais e tempo de resposta", expanded=False):
    st.markdown(txt(
      "Use este painel antes de baixar camadas ambientais. Ele mostra se NASA POWER, CHIRPS, Copernicus/Sentinel, SoilGrids e MapBiomas estão acessíveis, se precisam de credencial, o tempo de resposta do teste e o histórico do último download.",
      "Use this panel before downloading environmental layers. It shows whether NASA POWER, CHIRPS, Copernicus/Sentinel, SoilGrids and MapBiomas are reachable, whether credentials are required, test response time and the latest download history."
    ))
    if is_admin_authenticated():
      apply_persisted_admin_credentials_to_session(overwrite=False)
      c1, c2 = st.columns(2)
      with c1:
        st.markdown("##### Copernicus / Sentinel Hub")
        client_id = st.text_input("COPERNICUS_CLIENT_ID", value=st.session_state.get("COPERNICUS_CLIENT_ID", runtime_setting("COPERNICUS_CLIENT_ID", "")), key="env_page_cop_client_id")
      with c2:
        client_secret = st.text_input("COPERNICUS_CLIENT_SECRET", value=st.session_state.get("COPERNICUS_CLIENT_SECRET", runtime_setting("COPERNICUS_CLIENT_SECRET", "")), type="password", key="env_page_cop_client_secret")
      b1, b2, b3 = st.columns([0.34, 0.33, 0.33])
      with b1:
        if st.button("Usar login Copernicus nesta sessão", key="env_page_save_cop", type="primary", width="stretch"):
          st.session_state["COPERNICUS_CLIENT_ID"] = str(client_id).strip()
          st.session_state["COPERNICUS_CLIENT_SECRET"] = str(client_secret).strip()
          st.success("Credenciais Copernicus carregadas somente na sessão admin atual.")
      with b2:
        if st.button("Limpar login Copernicus", key="env_page_clear_cop", width="stretch"):
          st.session_state.pop("COPERNICUS_CLIENT_ID", None)
          st.session_state.pop("COPERNICUS_CLIENT_SECRET", None)
          st.info("Credenciais Copernicus removidas da sessão.")
      with b3:
        if st.button("Testar conexões agora", key="env_page_test_sources", width="stretch"):
          with st.spinner("Testando conexões e medindo tempo de resposta..."):
            st.session_state["environmental_api_connection_status"] = test_environmental_api_connections()
    else:
      st.info(txt("Campos de Copernicus/NASA e testes administrativos ficam ocultos para usuários públicos. Entre no painel admin para configurar credenciais.", "Copernicus/NASA fields and administrative tests are hidden from public users. Log in as admin to configure credentials."))
    status_df = st.session_state.get("environmental_api_connection_status")
    if isinstance(status_df, pd.DataFrame) and not status_df.empty:
      show_table(status_df, "environmental_connection_center_status", height=300)
      csv_button(status_df, "environmental_source_connection_status.csv", "Baixar status das conexões")
      if status_df["connection_status"].eq("not connected").any():
        st.warning("Uma ou mais fontes não conectaram. Isso pode ser credencial ausente, internet, limite temporário de API ou timeout da fonte pública. O app não preenche valores simulados.")
      else:
        st.success("Todas as fontes testadas estão conectadas ou prontas para consulta.")
    else:
      st.info("Nenhum teste executado ainda nesta sessão.")

    source_audit = results.get("source_audit", pd.DataFrame()) if isinstance(results, dict) else pd.DataFrame()
    if isinstance(source_audit, pd.DataFrame) and not source_audit.empty:
      st.markdown("##### Último download executado")
      cols = [c for c in ["sample_id", "source", "status", "rows_returned", "elapsed_seconds", "start_date", "end_date", "message"] if c in source_audit.columns]
      show_table(source_audit[cols], "environmental_connection_center_last_download", height=260)


def admin_copernicus_panel():
  st.markdown('<div class="section-title">Administração e credenciais — somente admin</div>', unsafe_allow_html=True)
  admin_expanded = is_admin_authenticated()
  with st.expander("🔐 Painel admin: acesso público, downloads e credenciais", expanded=admin_expanded):
    st.caption(txt(
      "O atlas abre publicamente por padrão. Este painel é apenas para admin: gerenciar contas opcionais, mostrar/ocultar módulos, configurar credenciais e executar/atualizar downloads persistentes.",
      "The atlas opens publicly by default. This panel is admin-only: manage optional accounts, show/hide modules, configure credentials and run/update persistent downloads."
    ))
    auth = is_admin_authenticated()
    auth_required = admin_auth_enabled()
    if auth and auth_required:
      logged_user = st.session_state.get("admin_username", DEFAULT_ADMIN_USER)
      st.success(txt(f"Admin logado com sucesso: {logged_user}", f"Admin logged in successfully: {logged_user}"))
    elif auth:
      st.info(txt(
        "A proteção por senha do painel administrativo está desativada pela configuração local. O atlas público continua aberto.",
        "Administrator password protection is disabled by the local setting. The public atlas remains open.",
      ))
    else:
      st.info(txt("Admin ainda não logado.", "Admin is not logged in yet."))

    if not auth:
      c1, c2, c3 = st.columns([0.38, 0.36, 0.26])
      with c1:
        u = st.text_input("Admin user", value=DEFAULT_ADMIN_USER, key="admin_user_login")
      with c2:
        p = st.text_input("Admin password", value="", type="password", key="admin_password_login")
      with c3:
        st.write("")
        st.write("")
        if st.button(txt("Logar", "Log in"), key="admin_login_btn", type="primary", width="stretch"):
          user = authenticate_user(u, p)
          if user is not None and str(user.get("role", "viewer")) in {"admin", "editor"}:
            st.session_state["admin_authenticated"] = True
            st.session_state["admin_username"] = user.get("username", u)
            st.session_state["admin_role"] = user.get("role", "admin")
            apply_persisted_admin_credentials_to_session(overwrite=True)
            st.success(txt("Login realizado com sucesso.", "Login successful."))
            st.rerun()
          elif user is not None:
            st.error(txt("Esta conta é viewer e não possui acesso ao painel admin.", "This is a viewer account and does not have admin-panel access."))
          else:
            st.error(txt("Usuário ou senha inválidos.", "Invalid user or password."))
      st.caption(txt(
        "Nenhuma credencial é incorporada ao pacote. Para configurar o primeiro administrador, defina CANGAMETAG_ADMIN_PASSWORD (mínimo de oito caracteres) antes de iniciar o aplicativo; CANGAMETAG_ADMIN_USER é opcional.",
        "No credential is embedded in the package. To configure the first administrator, set CANGAMETAG_ADMIN_PASSWORD (at least eight characters) before launching the application; CANGAMETAG_ADMIN_USER is optional."
      ))
      return

    current_user = st.session_state.get("admin_username", DEFAULT_ADMIN_USER)
    apply_persisted_admin_credentials_to_session(overwrite=False)

    with st.expander(txt("Proteção do painel administrativo", "Administrator-panel protection"), expanded=False):
      security_settings = load_app_settings()
      protect_admin = st.checkbox(
        txt("Exigir senha para abrir o painel admin", "Require a password to open the admin panel"),
        value=bool(security_settings.get("admin_auth_enabled", True)),
        key="admin_auth_enabled_interface",
        help=txt(
          "A proteção só pode ser ativada quando existe uma conta local ou uma senha fornecida por variável de ambiente. Isso não fecha o atlas público.",
          "Protection can be enabled only when a local account exists or a password is supplied through an environment variable. This does not close the public atlas.",
        ),
      )
      if st.button(txt("Salvar proteção administrativa", "Save administrator protection"), key="save_admin_auth_mode", width="stretch"):
        security_settings["admin_auth_enabled"] = bool(protect_admin)
        security_settings["admin_auth_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
        if protect_admin and not load_admin_users():
          bootstrap = default_admin_user_record()
          if bootstrap:
            save_admin_users([bootstrap], silent=True)
          else:
            st.error(txt(
              "Defina CANGAMETAG_ADMIN_PASSWORD antes de ativar a proteção administrativa.",
              "Set CANGAMETAG_ADMIN_PASSWORD before enabling administrator protection.",
            ))
            return
        if save_app_settings(security_settings):
          st.success(txt("Proteção administrativa atualizada.", "Administrator protection updated."))
          st.rerun()
      st.caption(txt(
        "A senha é configurada e alterada somente pela interface e fica armazenada como hash no diretório privado de configuração do usuário.",
        "The password is configured and changed only in the interface and is stored as a hash in the user's private configuration directory.",
      ))

    site_gate_admin_panel()
    admin_contact_settings_panel()

    with st.expander(txt("Usuários editores e senha", "Editor users and password"), expanded=False):
      st.markdown(
        txt(
          "Contas viewer servem apenas para o login opcional do atlas. Contas editor e admin podem entrar no painel administrativo. As senhas são salvas localmente como hash no diretório privado de configuração do usuário.",
          "Viewer accounts are only for optional atlas login. Editor and admin accounts can access the administration panel. Passwords are saved locally as hashes in the user's private configuration directory."
        )
      )
      users = load_admin_users()
      users_public = pd.DataFrame([{
        "username": u.get("username", ""),
        "role": u.get("role", "editor"),
        "can_edit": bool(u.get("can_edit", True)),
        "created_by": u.get("created_by", ""),
        "updated_at": u.get("updated_at", ""),
      } for u in users])
      show_table(users_public, "admin_users_public", height=220)

      st.markdown("##### " + txt("Configurar ou alterar senha opcional", "Configure or change optional password"))
      p1, p2, p3 = st.columns([0.34, 0.34, 0.32])
      with p1:
        current_password = st.text_input(txt("Senha atual (deixe vazia na primeira configuração)", "Current password (leave blank for first-time setup)"), type="password", key="change_current_password")
      with p2:
        new_password = st.text_input(txt("Nova senha", "New password"), type="password", key="change_new_password")
      with p3:
        st.write("")
        st.write("")
        if st.button(txt("Atualizar senha", "Update password"), key="change_password_btn", type="primary", width="stretch"):
          ok, msg = change_admin_password(current_user, current_password, new_password)
          (st.success if ok else st.error)(msg)

      st.markdown("##### " + txt("Cadastrar ou atualizar usuário", "Add or update user"))
      a1, a2, a3, a4 = st.columns([0.30, 0.30, 0.20, 0.20])
      with a1:
        new_user = st.text_input(txt("Novo usuário", "New username"), key="new_admin_username")
      with a2:
        new_user_password = st.text_input(txt("Senha do usuário", "User password"), type="password", key="new_admin_password")
      with a3:
        new_role = st.selectbox("Role", ["viewer", "editor", "admin"], index=1, key="new_admin_role")
      with a4:
        st.write("")
        st.write("")
        if st.button(txt("Salvar usuário", "Save user"), key="save_new_admin_user", type="primary", width="stretch"):
          ok, msg = upsert_admin_user(new_user, new_user_password, role=new_role, created_by=current_user)
          (st.success if ok else st.error)(msg)
          if ok:
            st.rerun()

      removable = [u.get("username", "") for u in load_admin_users() if normalize_username(u.get("username", "")) != normalize_username(current_user)]
      if removable:
        r1, r2 = st.columns([0.65, 0.35])
        with r1:
          remove_user = st.selectbox(txt("Remover usuário", "Remove user"), removable, key="remove_admin_user_select")
        with r2:
          st.write("")
          st.write("")
          if st.button(txt("Remover", "Remove"), key="remove_admin_user_btn"):
            ok, msg = delete_admin_user(remove_user)
            (st.success if ok else st.error)(msg)
            if ok:
              st.rerun()

    persisted_creds = load_admin_private_credentials()
    client_id_default = st.session_state.get("COPERNICUS_CLIENT_ID", persisted_creds.get("COPERNICUS_CLIENT_ID", runtime_setting("COPERNICUS_CLIENT_ID", "")))
    client_secret_default = st.session_state.get("COPERNICUS_CLIENT_SECRET", persisted_creds.get("COPERNICUS_CLIENT_SECRET", runtime_setting("COPERNICUS_CLIENT_SECRET", "")))
    show_secret = st.checkbox(txt("Mostrar secret enquanto edito", "Show secret while editing"), value=False, key="show_cop_secret")
    c1, c2 = st.columns(2)
    with c1:
      client_id = st.text_input("COPERNICUS_CLIENT_ID / Sentinel Hub OAuth client id", value=client_id_default, key="cop_client_id")
    with c2:
      client_secret = st.text_input(
        "COPERNICUS_CLIENT_SECRET / Sentinel Hub OAuth client secret",
        value=client_secret_default,
        type="default" if show_secret else "password",
        key="cop_client_secret",
      )

    c3, c4, c5, c6 = st.columns([0.25, 0.25, 0.22, 0.28])
    with c3:
      if st.button(txt("Usar nesta sessão", "Use in this session"), key="save_cop_session", type="primary"):
        st.session_state["COPERNICUS_CLIENT_ID"] = client_id.strip()
        st.session_state["COPERNICUS_CLIENT_SECRET"] = client_secret.strip()
        st.success(txt("Credenciais Copernicus/Sentinel carregadas na sessão admin atual.", "Copernicus/Sentinel credentials loaded in the current admin session."))
    with c4:
      if st.button(txt("Salvar persistente", "Save persistently"), key="save_cop_persist", type="secondary"):
        existing = load_admin_private_credentials()
        existing["COPERNICUS_CLIENT_ID"] = client_id.strip()
        existing["COPERNICUS_CLIENT_SECRET"] = client_secret.strip()
        st.session_state["COPERNICUS_CLIENT_ID"] = client_id.strip()
        st.session_state["COPERNICUS_CLIENT_SECRET"] = client_secret.strip()
        if save_admin_private_credentials(existing):
          st.success(txt("Credenciais Copernicus salvas localmente para futuros logins admin.", "Copernicus credentials saved locally for future admin logins."))
    with c5:
      if st.button(txt("Limpar sessão", "Clear session"), key="clear_cop_session"):
        st.session_state.pop("COPERNICUS_CLIENT_ID", None)
        st.session_state.pop("COPERNICUS_CLIENT_SECRET", None)
        st.info(txt("Credenciais Copernicus removidas da sessão, sem apagar o arquivo persistente.", "Copernicus credentials removed from session, without deleting the persistent file."))
    with c6:
      if st.button(txt("Sair do admin", "Log out admin"), key="admin_logout_btn"):
        st.session_state["admin_authenticated"] = False
        for _k in [
          "admin_username", "admin_role",
          "COPERNICUS_CLIENT_ID", "COPERNICUS_CLIENT_SECRET",
          "EARTHDATA_TOKEN", "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD",
          "bvbrc_auto_sync_selected", "bvbrc_overwrite_existing",
        ]:
          st.session_state.pop(_k, None)
        st.info(txt("Admin desconectado. Credenciais foram removidas apenas da sessão atual; credenciais persistentes continuam salvas se o admin tiver escolhido salvar.", "Admin logged out. Credentials were removed only from the current session; persistent credentials remain saved if the admin chose to save them."))
        st.rerun()

    with st.expander("🔐 NASA Earthdata — token/.netrc para dados complementares do artigo", expanded=False):
      st.caption("Use este painel apenas no admin. O admin pode manter as credenciais somente na sessão ou salvá-las de forma persistente no servidor local em data/admin_private_credentials.json, que está no .gitignore.")
      auth_status = earthdata_auth_status()
      st.info(f"Status atual: configurado={auth_status.get('configured')} | método={auth_status.get('method')} | netrc={auth_status.get('netrc_has_urs')} | token presente={auth_status.get('token_present')}. Nenhum segredo é exibido.")
      e1, e2, e3 = st.columns([0.42, 0.29, 0.29])
      with e1:
        ed_token = st.text_input("EARTHDATA_TOKEN / Bearer token", value=st.session_state.get("EARTHDATA_TOKEN", persisted_creds.get("EARTHDATA_TOKEN", "")), type="password", key="admin_earthdata_token_input", placeholder="Cole o token se quiser usar Earthdata")
      with e2:
        ed_user = st.text_input("EARTHDATA_USERNAME opcional", value=st.session_state.get("EARTHDATA_USERNAME", persisted_creds.get("EARTHDATA_USERNAME", "")), key="admin_earthdata_user_input")
      with e3:
        ed_password = st.text_input("EARTHDATA_PASSWORD opcional", value=st.session_state.get("EARTHDATA_PASSWORD", persisted_creds.get("EARTHDATA_PASSWORD", "")), type="password", key="admin_earthdata_password_input")
      eb1, eb2, eb3 = st.columns(3)
      with eb1:
        if st.button("Usar Earthdata nesta sessão", key="save_earthdata_session", type="primary", width="stretch"):
          if ed_token.strip():
            st.session_state["EARTHDATA_TOKEN"] = ed_token.strip()
          if ed_user.strip() and ed_password.strip():
            st.session_state["EARTHDATA_USERNAME"] = ed_user.strip()
            st.session_state["EARTHDATA_PASSWORD"] = ed_password.strip()
          st.success("Credenciais Earthdata carregadas na sessão admin atual.")
      with eb2:
        if st.button("Salvar Earthdata persistente", key="save_earthdata_persist", width="stretch"):
          existing = load_admin_private_credentials()
          if ed_token.strip():
            existing["EARTHDATA_TOKEN"] = ed_token.strip()
            st.session_state["EARTHDATA_TOKEN"] = ed_token.strip()
          if ed_user.strip() and ed_password.strip():
            existing["EARTHDATA_USERNAME"] = ed_user.strip()
            existing["EARTHDATA_PASSWORD"] = ed_password.strip()
            st.session_state["EARTHDATA_USERNAME"] = ed_user.strip()
            st.session_state["EARTHDATA_PASSWORD"] = ed_password.strip()
          if save_admin_private_credentials(existing):
            st.success("Credenciais Earthdata salvas localmente para futuros logins admin.")
      with eb3:
        if st.button("Limpar Earthdata da sessão", key="clear_earthdata_session", width="stretch"):
          for k in ["EARTHDATA_TOKEN", "EARTHDATA_USERNAME", "EARTHDATA_PASSWORD"]:
            st.session_state.pop(k, None)
          st.info("Credenciais Earthdata removidas da sessão.")

    with st.expander(txt("Gerenciar credenciais persistentes locais", "Manage local persistent credentials"), expanded=False):
      saved_keys = sorted(load_admin_private_credentials().keys())
      if saved_keys:
        st.info(txt(f"Credenciais persistentes salvas para: {', '.join(saved_keys)}. Valores secretos não são exibidos.", f"Persistent credentials saved for: {', '.join(saved_keys)}. Secret values are not displayed."))
      else:
        st.info(txt("Nenhuma credencial persistente salva ainda.", "No persistent credentials saved yet."))
      if st.button(txt("Apagar credenciais persistentes do servidor", "Delete persistent credentials from server"), key="delete_persistent_admin_credentials"):
        if clear_persisted_admin_credentials():
          st.success(txt("Credenciais persistentes removidas.", "Persistent credentials removed."))
          st.rerun()

    st.markdown("#### " + txt("Testar conexões das APIs ambientais", "Test environmental API connections"))
    st.caption(txt(
      "Use este botão antes de baixar camadas ambientais. O teste verifica conexão/autenticação e registra falhas sem criar dados artificiais.",
      "Use this button before downloading environmental layers. The test verifies connection/authentication and records failures without creating artificial data."
    ))
    if st.button(txt("Conectar e testar APIs", "Connect and test APIs"), key="test_environmental_apis", type="secondary", width="stretch"):
      with st.spinner(txt("Testando NASA POWER, CHIRPS, SoilGrids, Copernicus/Sentinel e MapBiomas...", "Testing NASA POWER, CHIRPS, SoilGrids, Copernicus/Sentinel and MapBiomas...")):
        api_status = test_environmental_api_connections()
      st.session_state["environmental_api_connection_status"] = api_status
    if "environmental_api_connection_status" in st.session_state:
      status_df = st.session_state["environmental_api_connection_status"]
      show_table(status_df, "environmental_api_connection_status", height=260)
      if not status_df.empty and status_df["connection_status"].eq("failed").any():
        st.warning(txt("Uma ou mais fontes falharam. Verifique credenciais, internet, limites de API ou disponibilidade temporária da fonte.", "One or more sources failed. Check credentials, internet, API limits or temporary source availability."))
      else:
        st.success(txt("Todas as fontes testadas responderam.", "All tested sources responded."))


def prepare_metadata_download(meta: pd.DataFrame):
  st.markdown("#### " + txt("Metadados de coleta", "Collection metadata"))
  preview = apply_amazonian_lake_coordinate_overrides(meta.copy())
  preview.insert(0, "sample_display_id", [sample_display_id(r) for _, r in preview.iterrows()])
  cols = [c for c in [
    "sample_display_id", "sample_label", "dataset_group", "sample.id", "sample_id", "matrix_column",
    "linked_st8_all_ko_column", "linked_res_ko_biomarkers_cns_column", "st8_link_status",
    "collection_date", "collection_date_precision", "lat", "lon", "coordinate_status", "environmental_download_ready",
    "environment_feature", "habitat", "lake", "season", "sample_description",
    "taxon_oid", "img_genome_id", "img_taxonomy_phylum", "dominant_phylum", "dominant_phylum_percent",
    "top5_phyla", "phylum_taxonomy_status", "phylum_taxonomy_column"
  ] if c in preview.columns]
  show_table(preview[cols], "env_meta_preview", height=360)
  if "dataset_group" in preview.columns:
    linked_mask = preview.get("st8_link_status", pd.Series([""] * len(preview))).astype(str).str.contains("linked", case=False, na=False)
    phylum_mask = preview.get("phylum_taxonomy_status", pd.Series([""] * len(preview))).astype(str).eq("linked")
    st.caption(txt(
      f"ST8 linked metadata: {int(linked_mask.sum())}/{len(preview)} rows linked to KO matrices; Phylum-taxonomy linked: {int(phylum_mask.sum())}/{len(preview)} rows.",
      f"ST8 linked metadata: {int(linked_mask.sum())}/{len(preview)} rows linked to KO matrices; Phylum-taxonomy linked: {int(phylum_mask.sum())}/{len(preview)} rows."
    ))
  if st.button("Preparar e baixar metadados com progresso", key="prepare_meta_download"):
    progress = st.progress(0, text="Preparando metadados...")
    start = time.time()
    for i in range(1, 6):
      time.sleep(0.08)
      progress.progress(i / 5, text=f"Preparando CSV dos metadados... {i}/5")
    elapsed = time.time() - start
    st.success(f"Metadados preparados em {elapsed:.2f} segundos.")
    st.download_button(
      "Baixar metadados de coleta em CSV",
      data=preview[cols].to_csv(index=False).encode("utf-8"),
      file_name="supplementary_table1_collection_dates_coordinates.csv",
      mime="text/csv",
      key="download_meta_with_progress",
    )
  if {"lat", "lon"}.issubset(meta.columns):
    show_high_quality_sample_map(meta, key="environmental_article_dates_map")


def fetch_sentinel_coverage_layers(selected: pd.DataFrame, window_mode: str, buffer_m: int, max_cloud: int,
                                   use_cache: bool, layers: dict) -> dict:
  """Check Sentinel-1/2/6 coverage for selected samples without downloading full environmental workflow."""
  enabled = [k for k in ["sentinel2", "sentinel1", "sentinel6"] if layers.get(k)]
  enabled_count = max(1, len(enabled) * len(selected))
  step = 0
  start_time = time.time()
  progress = st.progress(0, text="Verificando cobertura Sentinel...")
  status = st.empty()
  rows = {"sentinel2": [], "sentinel1": [], "sentinel6": []}
  audit: List[dict] = []
  errors: List[str] = []

  def tick(label: str):
    nonlocal step
    elapsed = time.time() - start_time
    pct = min((step + 1) / enabled_count, 0.999)
    progress.progress(pct, text=f"{label} | {step + 1}/{enabled_count} | elapsed {elapsed:.1f}s")
    status.markdown(
      f"""
      <div class='download-status-card'>
        <b>Verificando cobertura Sentinel:</b> {html_lib.escape(str(label))}<br>
        <b>Progresso:</b> {step + 1}/{enabled_count} ({pct*100:.1f}%)
      </div>
      """,
      unsafe_allow_html=True,
    )

  for _, sample in selected.iterrows():
    sample_id = str(sample.get("sample.id", sample.get("sample_id", sample.get("Sample", "")))).strip()
    lat = float(sample["lat"])
    lon = float(sample["lon"])
    collection = pd.to_datetime(sample["collection_date"])
    start_date, end_date = window_from_collection_date(collection, window_mode)

    if layers.get("sentinel2"):
      tick(f"Sentinel-2 coverage — {sample_id}")
      started = time.time()
      try:
        df = fetch_sentinel2_catalog_coverage(lat, lon, start_date, end_date, buffer_m=buffer_m, max_cloud_coverage=max_cloud, use_cache=use_cache)
        rows["sentinel2"].append(add_sample_columns(df, sample))
        covered = int((df.get("coverage_status", pd.Series(dtype=str)).astype(str) == "covered").sum()) if not df.empty else 0
        audit.append({"sample_id": sample_id, "source": "Sentinel-2 Catalog coverage", "status": "covered" if covered else "no_items_found", "items": covered, "start_date": start_date, "end_date": end_date, "elapsed_seconds": round(time.time() - started, 2)})
      except Exception as exc:
        errors.append(f"Sentinel-2 coverage {sample_id}: {exc}")
        audit.append({"sample_id": sample_id, "source": "Sentinel-2 Catalog coverage", "status": "error", "items": 0, "message": str(exc), "start_date": start_date, "end_date": end_date, "elapsed_seconds": round(time.time() - started, 2)})
      step += 1

    if layers.get("sentinel1"):
      tick(f"Sentinel-1 coverage — {sample_id}")
      started = time.time()
      try:
        df = fetch_sentinel1_catalog_coverage(lat, lon, start_date, end_date, buffer_m=buffer_m, use_cache=use_cache)
        rows["sentinel1"].append(add_sample_columns(df, sample))
        covered = int((df.get("coverage_status", pd.Series(dtype=str)).astype(str) == "covered").sum()) if not df.empty else 0
        audit.append({"sample_id": sample_id, "source": "Sentinel-1 Catalog coverage", "status": "covered" if covered else "no_items_found", "items": covered, "start_date": start_date, "end_date": end_date, "elapsed_seconds": round(time.time() - started, 2)})
      except Exception as exc:
        errors.append(f"Sentinel-1 coverage {sample_id}: {exc}")
        audit.append({"sample_id": sample_id, "source": "Sentinel-1 Catalog coverage", "status": "error", "items": 0, "message": str(exc), "start_date": start_date, "end_date": end_date, "elapsed_seconds": round(time.time() - started, 2)})
      step += 1

    if layers.get("sentinel6"):
      tick(f"Sentinel-6 coverage — {sample_id}")
      started = time.time()
      try:
        df = fetch_sentinel6_altimetry_granules(lat, lon, start_date, end_date, buffer_m=buffer_m, use_cache=use_cache)
        rows["sentinel6"].append(add_sample_columns(df, sample))
        covered = int((df.get("coverage_status", pd.Series(dtype=str)).astype(str) == "covered").sum()) if not df.empty else 0
        audit.append({"sample_id": sample_id, "source": "Sentinel-6 NASA CMR coverage", "status": "covered" if covered else "no_granules_found", "items": covered, "start_date": start_date, "end_date": end_date, "elapsed_seconds": round(time.time() - started, 2)})
      except Exception as exc:
        errors.append(f"Sentinel-6 coverage {sample_id}: {exc}")
        audit.append({"sample_id": sample_id, "source": "Sentinel-6 NASA CMR coverage", "status": "error", "items": 0, "message": str(exc), "start_date": start_date, "end_date": end_date, "elapsed_seconds": round(time.time() - started, 2)})
      step += 1

  elapsed = time.time() - start_time
  progress.progress(1.0, text=f"Cobertura Sentinel verificada em {elapsed:.1f}s.")
  status.success(f"Cobertura Sentinel verificada em {elapsed:.1f}s.")
  out = {
    "sentinel2": pd.concat(rows["sentinel2"], ignore_index=True) if rows["sentinel2"] else pd.DataFrame(),
    "sentinel1": pd.concat(rows["sentinel1"], ignore_index=True) if rows["sentinel1"] else pd.DataFrame(),
    "sentinel6": pd.concat(rows["sentinel6"], ignore_index=True) if rows["sentinel6"] else pd.DataFrame(),
    "audit": pd.DataFrame(audit),
    "errors": errors,
    "metadata": {
      "status": "completed",
      "window_mode": window_mode,
      "buffer_m": int(buffer_m),
      "max_cloud": int(max_cloud),
      "use_cache": bool(use_cache),
      "layers": {k: bool(layers.get(k)) for k in ["sentinel2", "sentinel1", "sentinel6"]},
      "elapsed_seconds": round(elapsed, 2),
      "checked_at": datetime_now_iso(),
      "app_version": APP_VERSION,
      "database_version": DATABASE_VERSION,
    },
  }
  st.session_state["env_sentinel_coverage_results"] = out
  return out


def show_sentinel_coverage_results(coverage: dict) -> None:
  if not coverage:
    return
  st.markdown("### Cobertura Sentinel verificada")
  meta = coverage.get("metadata", {}) if isinstance(coverage.get("metadata", {}), dict) else {}
  st.caption(
    "Mostra se existem cenas/grânulos para a coordenada, buffer e janela de datas selecionados. "
    "Sentinel-1/2 usam o catálogo Copernicus/Sentinel Hub; Sentinel-6 usa NASA CMR/PO.DAAC. "
    "Nenhum valor simulado é criado."
  )
  if meta:
    st.info(f"Janela: {meta.get('window_mode')} | buffer: {meta.get('buffer_m')} m | cache: {meta.get('use_cache')} | verificado em: {meta.get('checked_at')}")
  s2 = coverage.get("sentinel2", pd.DataFrame())
  s1 = coverage.get("sentinel1", pd.DataFrame())
  s6 = coverage.get("sentinel6", pd.DataFrame())
  audit = coverage.get("audit", pd.DataFrame())
  c1, c2, c3, c4 = st.columns(4)
  c1.metric("S2 itens cobertos", int((s2.get("coverage_status", pd.Series(dtype=str)).astype(str) == "covered").sum()) if isinstance(s2, pd.DataFrame) and not s2.empty else 0)
  c2.metric("S1 itens cobertos", int((s1.get("coverage_status", pd.Series(dtype=str)).astype(str) == "covered").sum()) if isinstance(s1, pd.DataFrame) and not s1.empty else 0)
  c3.metric("S6 grânulos", int((s6.get("coverage_status", pd.Series(dtype=str)).astype(str) == "covered").sum()) if isinstance(s6, pd.DataFrame) and not s6.empty else 0)
  c4.metric("Amostras auditadas", audit["sample_id"].nunique() if isinstance(audit, pd.DataFrame) and "sample_id" in audit.columns else 0)
  tabs = st.tabs(["Sentinel-2 coverage", "Sentinel-1 coverage", "Sentinel-6 coverage", "Auditoria"])
  with tabs[0]:
    show_table(s2, "sentinel2_coverage_table", height=360) if isinstance(s2, pd.DataFrame) and not s2.empty else st.info("Sem cobertura Sentinel-2 encontrada ou não consultada.")
    csv_button(s2, "sentinel2_coverage_catalog.csv", "Baixar cobertura Sentinel-2")
  with tabs[1]:
    show_table(s1, "sentinel1_coverage_table", height=360) if isinstance(s1, pd.DataFrame) and not s1.empty else st.info("Sem cobertura Sentinel-1 encontrada ou não consultada.")
    csv_button(s1, "sentinel1_coverage_catalog.csv", "Baixar cobertura Sentinel-1")
  with tabs[2]:
    st.caption("Sentinel-6 retorna metadados e links de grânulos CMR/PO.DAAC. O download de arquivos NetCDF completos pode exigir Earthdata Login, conforme o link retornado.")
    show_table(s6, "sentinel6_coverage_table", height=360) if isinstance(s6, pd.DataFrame) and not s6.empty else st.info("Sem cobertura Sentinel-6 encontrada ou não consultada.")
    csv_button(s6, "sentinel6_cmr_granules.csv", "Baixar cobertura/grânulos Sentinel-6")
  with tabs[3]:
    show_table(audit, "sentinel_coverage_audit", height=300) if isinstance(audit, pd.DataFrame) and not audit.empty else st.info("Sem auditoria de cobertura.")
    csv_button(audit, "sentinel_coverage_audit.csv", "Baixar auditoria de cobertura")
  for err in coverage.get("errors", []) or []:
    st.warning(err)


def chirps_preflight_for_download(selected: pd.DataFrame, window_mode: str, buffer_m: int) -> tuple[bool, pd.DataFrame]:
  """Test CHIRPS/ClimateSERV before starting a selected download."""
  if selected is None or selected.empty:
    return False, pd.DataFrame([{
      "source": "CHIRPS / ClimateSERV",
      "connection_status": "not connected",
      "rows_returned_in_test": 0,
      "message": "No selected coordinate/date to test.",
    }])
  sample = selected.iloc[0]
  sample_id = str(sample.get("sample.id", sample.get("Sample", sample.get("sample_label", "sample")))).strip()
  collection = pd.to_datetime(sample.get("collection_date"), errors="coerce")
  if pd.isna(collection):
    collection = pd.Timestamp("2020-03-01")
  start_date, _ = window_from_collection_date(collection, "Exact collection day")
  status = test_chirps_climateserv_connection(float(sample["lat"]), float(sample["lon"]), start_date, buffer_m=float(buffer_m), timeout_s=120)
  row = {
    "sample_id_tested": sample_id,
    "source": "CHIRPS / ClimateSERV",
    "connection_status": "connected" if status.get("ok") else "not connected",
    "endpoint_submit": status.get("endpoint_submit", ""),
    "job_id": status.get("job_id", ""),
    "rows_returned_in_test": int(status.get("rows_returned", 0) or 0),
    "response_seconds": status.get("elapsed_seconds", np.nan),
    "message": status.get("message", ""),
    "data_policy": "Pre-download API test only; download is cancelled if CHIRPS/ClimateSERV is not connected.",
  }
  return bool(status.get("ok")), pd.DataFrame([row])


def fetch_environmental_layers(selected: pd.DataFrame, window_mode: str, buffer_m: int, max_cloud: int, use_cache: bool, layers: dict):
  core_layer_keys = ["nasa", "chirps", "sentinel2", "sentinel1", "sentinel6", "soil", "mapbiomas"]
  earthdata_products = list(layers.get("earthdata_products") or [])
  earthdata_units = len(earthdata_products) if layers.get("earthdata") and earthdata_products else (1 if layers.get("earthdata") else 0)
  enabled_units = sum(1 for k in core_layer_keys if layers.get(k)) + earthdata_units
  enabled_count = max(1, enabled_units * len(selected))
  step = 0
  start_time = time.time()
  progress = st.progress(0, text="Starting environmental-layer downloads...")
  status = st.empty()
  errors: List[str] = []
  nasa_rows: List[pd.DataFrame] = []
  chirps_rows: List[pd.DataFrame] = []
  s2_rows: List[pd.DataFrame] = []
  s1_rows: List[pd.DataFrame] = []
  soil_rows: List[pd.DataFrame] = []
  mapbiomas_rows: List[pd.DataFrame] = []
  sentinel6_rows: List[pd.DataFrame] = []
  earthdata_rows: List[pd.DataFrame] = []
  source_log: List[dict] = []

  def current_results(status_label: str = "running", note: str = "") -> dict:
    elapsed = time.time() - start_time
    return {
      "nasa": pd.concat(nasa_rows, ignore_index=True) if nasa_rows else pd.DataFrame(),
      "chirps": pd.concat(chirps_rows, ignore_index=True) if chirps_rows else pd.DataFrame(),
      "sentinel2": pd.concat(s2_rows, ignore_index=True) if s2_rows else pd.DataFrame(),
      "sentinel1": pd.concat(s1_rows, ignore_index=True) if s1_rows else pd.DataFrame(),
      "soil": pd.concat(soil_rows, ignore_index=True) if soil_rows else pd.DataFrame(),
      "mapbiomas": pd.concat(mapbiomas_rows, ignore_index=True) if mapbiomas_rows else pd.DataFrame(),
      "sentinel6": pd.concat(sentinel6_rows, ignore_index=True) if sentinel6_rows else pd.DataFrame(),
      "earthdata": pd.concat(earthdata_rows, ignore_index=True) if earthdata_rows else pd.DataFrame(),
      "source_audit": pd.DataFrame(source_log),
      "errors": list(errors),
      "elapsed_seconds": elapsed,
      "metadata": {
        "status": status_label,
        "note": note,
        "window_mode": window_mode,
        "buffer_m": int(buffer_m),
        "max_cloud": int(max_cloud),
        "use_cache": bool(use_cache),
        "layers": {k: bool(v) for k, v in layers.items()},
        "selected_rows": int(len(selected)),
        "app_version": APP_VERSION,
        "database_version": DATABASE_VERSION,
        "database_release_date": DATABASE_RELEASE_DATE,
      },
    }

  def checkpoint(status_label: str = "running", note: str = "") -> None:
    results_now = current_results(status_label=status_label, note=note)
    st.session_state["env_download_results"] = results_now
    save_persistent_env_results(results_now, status=status_label, note=note)

  def record_source(sample_id: str, source: str, status: str, rows: int = 0, message: str = "", start_date_value=None, end_date_value=None, elapsed_seconds=None):
    source_log.append({
      "sample_id": sample_id,
      "source": source,
      "status": status,
      "rows_returned": int(rows or 0),
      "message": str(message or ""),
      "start_date": start_date_value,
      "end_date": end_date_value,
      "elapsed_seconds": round(float(elapsed_seconds), 2) if elapsed_seconds is not None else np.nan,
      "data_policy": "Downloaded from source API/cache; no simulated values generated.",
    })

  def tick(label: str):
    elapsed = time.time() - start_time
    done = max(step + 1, 1)
    remaining = max(enabled_count - step - 1, 0)
    eta = elapsed / done * remaining if done else 0
    pct = min((step + 1) / enabled_count, 0.999)
    progress.progress(pct, text=f"{label} | {step + 1}/{enabled_count} | elapsed {elapsed:.1f}s | ETA {eta:.1f}s")
    status.markdown(
      f"""
      <div class='download-status-card'>
        <b>Downloading / Baixando:</b> {label}<br>
        <b>Progress:</b> {step + 1}/{enabled_count} ({pct*100:.1f}%)<br>
        <b>Elapsed:</b> {elapsed:.1f}s &nbsp; | &nbsp; <b>ETA:</b> {eta:.1f}s
      </div>
      """,
      unsafe_allow_html=True,
    )

  for _, sample in selected.iterrows():
    sample_id = str(sample.get("sample.id", sample.get("Sample", ""))).strip()
    lat = float(sample["lat"])
    lon = float(sample["lon"])
    collection = pd.to_datetime(sample["collection_date"])
    start_date, end_date = window_from_collection_date(collection, window_mode)
    year = int(collection.year)

    if layers.get("nasa"):
      tick(f"NASA POWER — {sample_id}")
      source_started = time.time()
      try:
        df = fetch_nasa_power_daily(lat, lon, start_date, end_date, parameters=NASA_POWER_DEFAULT_PARAMS, use_cache=use_cache)
        nasa_rows.append(add_sample_columns(df, sample))
        record_source(sample_id, "NASA POWER", "ok", len(df), start_date_value=start_date, end_date_value=end_date, elapsed_seconds=time.time() - source_started)
      except Exception as exc:
        errors.append(f"NASA POWER {sample_id}: {exc}")
        record_source(sample_id, "NASA POWER", "error", 0, str(exc), start_date, end_date, elapsed_seconds=time.time() - source_started)
      step += 1
      checkpoint("running", f"Checkpoint after NASA POWER for {sample_id}")

    if layers.get("chirps"):
      tick(f"CHIRPS — {sample_id}")
      source_started = time.time()
      try:
        df = fetch_chirps_daily_climateserv(lat, lon, start_date, end_date, buffer_m=buffer_m, use_cache=use_cache, timeout_s=300)
        chirps_rows.append(add_sample_columns(df, sample))
        record_source(sample_id, "CHIRPS ClimateSERV", "ok", len(df), start_date_value=start_date, end_date_value=end_date, elapsed_seconds=time.time() - source_started)
      except Exception as exc:
        errors.append(f"CHIRPS {sample_id}: {exc}")
        record_source(sample_id, "CHIRPS ClimateSERV", "error", 0, str(exc), start_date, end_date, elapsed_seconds=time.time() - source_started)
      step += 1
      checkpoint("running", f"Checkpoint after CHIRPS for {sample_id}")

    if layers.get("sentinel2"):
      tick(f"Sentinel-2 spectral indices — {sample_id}")
      source_started = time.time()
      try:
        df = fetch_sentinelhub_monthly_indices(lat, lon, start_date, end_date, buffer_m=buffer_m, max_cloud_coverage=max_cloud, use_cache=use_cache)
        s2_rows.append(add_sample_columns(df, sample))
        record_source(sample_id, "Copernicus Sentinel-2 L2A", "ok", len(df), start_date_value=start_date, end_date_value=end_date, elapsed_seconds=time.time() - source_started)
      except Exception as exc:
        errors.append(f"Sentinel-2 {sample_id}: {exc}")
        record_source(sample_id, "Copernicus Sentinel-2 L2A", "error", 0, str(exc), start_date, end_date, elapsed_seconds=time.time() - source_started)
      step += 1
      checkpoint("running", f"Checkpoint after Sentinel-2 for {sample_id}")

    if layers.get("sentinel1"):
      tick(f"Sentinel-1 SAR — {sample_id}")
      source_started = time.time()
      try:
        df = fetch_sentinel1_monthly_backscatter(lat, lon, start_date, end_date, buffer_m=buffer_m, use_cache=use_cache)
        s1_rows.append(add_sample_columns(df, sample))
        record_source(sample_id, "Copernicus Sentinel-1 GRD", "ok", len(df), start_date_value=start_date, end_date_value=end_date, elapsed_seconds=time.time() - source_started)
      except Exception as exc:
        errors.append(f"Sentinel-1 {sample_id}: {exc}")
        record_source(sample_id, "Copernicus Sentinel-1 GRD", "error", 0, str(exc), start_date, end_date, elapsed_seconds=time.time() - source_started)
      step += 1
      checkpoint("running", f"Checkpoint after Sentinel-1 for {sample_id}")

    if layers.get("sentinel6"):
      tick(f"Sentinel-6/Jason-CS altimetry granules — {sample_id}")
      source_started = time.time()
      try:
        df = fetch_sentinel6_altimetry_granules(lat, lon, start_date, end_date, buffer_m=buffer_m, use_cache=use_cache)
        sentinel6_rows.append(add_sample_columns(df, sample))
        covered = int((df.get("coverage_status", pd.Series(dtype=str)).astype(str) == "covered").sum()) if not df.empty else 0
        status_label = "ok" if covered else "no_granules_found"
        msg = "Sentinel-6 CMR/PO.DAAC granule metadata downloaded; full NetCDF assets may require Earthdata Login." if covered else "No Sentinel-6 granules returned for this coordinate/date window."
        record_source(sample_id, "NASA CMR / PO.DAAC Sentinel-6", status_label, len(df), msg, start_date, end_date, elapsed_seconds=time.time() - source_started)
      except Exception as exc:
        errors.append(f"Sentinel-6 {sample_id}: {exc}")
        record_source(sample_id, "NASA CMR / PO.DAAC Sentinel-6", "error", 0, str(exc), start_date, end_date, elapsed_seconds=time.time() - source_started)
      step += 1
      checkpoint("running", f"Checkpoint after Sentinel-6 for {sample_id}")

    if layers.get("earthdata"):
      product_keys = list(layers.get("earthdata_products") or [])
      if not product_keys:
        product_keys = ["imerg_daily", "merra2_slv", "merra2_flx", "merra2_lnd", "modis_ndvi", "modis_lst", "smap_soil_moisture", "podaac_sentinel6"]
      max_granules = int(layers.get("earthdata_max_granules", 20) or 20)
      force_update = bool(layers.get("earthdata_force_update", False))
      for product_key in product_keys:
        label = EARTHDATA_PRODUCT_REGISTRY.get(product_key, {}).get("label", product_key)
        tick(f"NASA Earthdata/CMR — {label} — {sample_id}")
        source_started = time.time()
        try:
          df = earthaccess_download_product(
            product_key,
            lat,
            lon,
            start_date,
            end_date,
            buffer_m=buffer_m,
            max_granules=max_granules,
            use_cache=use_cache,
            force_update=force_update,
          )
          earthdata_rows.append(add_sample_columns(df, sample))
          covered = int((df.get("coverage_status", pd.Series(dtype=str)).astype(str) == "covered").sum()) if not df.empty else 0
          download_statuses = ", ".join(sorted(set(df.get("download_status", pd.Series(dtype=str)).dropna().astype(str).tolist()))) if not df.empty and "download_status" in df.columns else "metadata_only"
          status_label = "ok" if covered else "no_granules_found"
          msg = f"{covered} CMR granules/items; download_status={download_statuses}. Local-first active; no simulated values."
          record_source(sample_id, f"NASA Earthdata/CMR {product_key}", status_label, len(df), msg, start_date, end_date, elapsed_seconds=time.time() - source_started)
        except Exception as exc:
          errors.append(f"NASA Earthdata/CMR {product_key} {sample_id}: {exc}")
          record_source(sample_id, f"NASA Earthdata/CMR {product_key}", "error", 0, str(exc), start_date, end_date, elapsed_seconds=time.time() - source_started)
        step += 1
        checkpoint("running", f"Checkpoint after NASA Earthdata/CMR {product_key} for {sample_id}")

    if layers.get("soil"):
      tick(f"SoilGrids — {sample_id}")
      source_started = time.time()
      try:
        df = fetch_soilgrids_point(lat, lon, use_cache=use_cache)
        soil_rows.append(add_sample_columns(df, sample))
        record_source(sample_id, "SoilGrids/ISRIC", "ok", len(df), start_date_value=start_date, end_date_value=end_date, elapsed_seconds=time.time() - source_started)
      except Exception as exc:
        errors.append(f"SoilGrids {sample_id}: {exc}")
        record_source(sample_id, "SoilGrids/ISRIC", "error", 0, str(exc), start_date, end_date, elapsed_seconds=time.time() - source_started)
      step += 1
      checkpoint("running", f"Checkpoint after SoilGrids for {sample_id}")

    if layers.get("mapbiomas"):
      tick(f"MapBiomas/GEE — {sample_id}")
      source_started = time.time()
      try:
        df = fetch_mapbiomas_gee_landcover(lat, lon, year=year, buffer_m=buffer_m, use_cache=use_cache)
        mapbiomas_rows.append(add_sample_columns(df, sample))
        record_source(sample_id, "MapBiomas / Google Earth Engine", "ok", len(df), start_date_value=start_date, end_date_value=end_date, elapsed_seconds=time.time() - source_started)
      except Exception as exc:
        errors.append(f"MapBiomas {sample_id}: {exc}")
        record_source(sample_id, "MapBiomas / Google Earth Engine", "error", 0, str(exc), start_date, end_date, elapsed_seconds=time.time() - source_started)
      step += 1
      checkpoint("running", f"Checkpoint after MapBiomas for {sample_id}")

  elapsed = time.time() - start_time
  progress.progress(1.0, text=f"Downloads completed in {elapsed:.1f} seconds.")
  status.success(f"Download process completed in {elapsed:.1f} seconds.")
  results = current_results(status_label="completed", note="Completed environmental-layer download workflow")
  results["elapsed_seconds"] = elapsed
  st.session_state["env_download_results"] = results
  save_persistent_env_results(results, status="completed", note="Completed environmental-layer download workflow")
  return results


def show_environmental_results(results: dict):
  nasa = results.get("nasa", pd.DataFrame())
  chirps = results.get("chirps", pd.DataFrame())
  s2 = results.get("sentinel2", pd.DataFrame())
  s1 = results.get("sentinel1", pd.DataFrame())
  soil = results.get("soil", pd.DataFrame())
  mapbiomas = results.get("mapbiomas", pd.DataFrame())
  sentinel6 = results.get("sentinel6", pd.DataFrame())
  earthdata = results.get("earthdata", pd.DataFrame())
  source_audit = results.get("source_audit", pd.DataFrame())
  errors = results.get("errors", [])
  metadata = results.get("metadata", {}) if isinstance(results.get("metadata", {}), dict) else {}

  state_label = metadata.get("status", "available")
  saved_at = metadata.get("saved_at", "")
  if is_admin_authenticated():
    b1, b2, b3 = st.columns([0.28, 0.28, 0.44])
    with b1:
      if st.button(txt("Limpar dados ambientais vigentes", "Clear active environmental data"), key="clear_env_runtime_results", width="stretch"):
        removed = clear_persistent_env_results()
        st.success(txt(f"Dados ambientais vigentes removidos ({removed} arquivos locais).", f"Active environmental data removed ({removed} local files)."))
        st.rerun()
    with b2:
      if st.button(txt("Apagar cache local das APIs", "Delete local API cache"), key="clear_env_api_cache", width="stretch"):
        removed = clear_api_cache_and_runtime_results()
        st.success(txt(f"Cache e dados vigentes removidos ({removed} arquivos locais).", f"Cache and active data removed ({removed} local files)."))
        st.rerun()
    with b3:
      st.caption(txt("Admin: use esses botões somente quando quiser reiniciar completamente os resultados ambientais.", "Admin: use these buttons only when you want to fully reset environmental results."))
  else:
    st.caption(txt(
      "Modo usuário: estes dados são persistentes e só podem ser limpos, atualizados ou baixados novamente pelo admin.",
      "User mode: these data are persistent and can only be cleared, updated or downloaded again by the admin.",
    ))

  if errors:
    with st.expander("Mensagens das fontes públicas / camadas indisponíveis", expanded=True):
      for err in errors:
        st.warning(err)

  m1, m2, m3, m4, m5, m6, m7, m8 = st.columns(8)
  m1.metric("NASA POWER", len(nasa))
  m2.metric("CHIRPS", len(chirps))
  m3.metric("Sentinel-2", len(s2))
  m4.metric("Sentinel-1", len(s1))
  m5.metric("Sentinel-6", len(sentinel6))
  m6.metric("Earthdata CMR", len(earthdata))
  m7.metric("SoilGrids", len(soil))
  m8.metric("MapBiomas", len(mapbiomas))

  t1, t2, t3, t4, t5, t6, t7, t8, t9 = st.tabs(["Climate", "Sentinel-2", "Sentinel-1 SAR", "Sentinel-6", "NASA Earthdata/CMR", "SoilGrids", "MapBiomas", "Source audit", "Downloads"])
  with t1:
    show_nasa_power_glossary()
    if not nasa.empty:
      st.caption("NASA POWER daily climate: RH2M = relative humidity at 2 m (%); PRECTOTCORR = corrected total precipitation; T2M = mean air temperature at 2 m. The overview chart summarizes all coordinates, and the charts below separate each coordinate/sample.")
      line_plot(nasa, "date", ["T2M", "T2M_MAX", "T2M_MIN", "RH2M", "QV2M", "PRECTOTCORR", "WS2M", "ALLSKY_SFC_SW_DWN"], "NASA POWER daily climate — overview of all selected coordinates and dates")
      render_per_coordinate_nasa(nasa)
      show_table(nasa, "nasa_env", height=420)
    if not chirps.empty:
      line_plot(chirps, "date", ["CHIRPS_PRECTOT"], "CHIRPS daily precipitation — overview of all selected coordinates and dates")
      render_per_coordinate_chirps(chirps)
      show_table(chirps, "chirps_env", height=360)
  with t2:
    if not s2.empty:
      fig = px.line(s2, x="interval_from", y="mean", color="index", facet_row="sample_id", markers=True, title="Sentinel-2 spectral indices — overview for all selected coordinates/samples")
      fig.update_layout(height=max(560, 220 * max(1, s2["sample_id"].nunique())), xaxis_title="Time interval", yaxis_title="Mean spectral-index value")
      render_plotly_downloadable(fig, key="sentinel2_indices_downloaded", basename="sentinel2_indices_downloaded")
      render_per_coordinate_timeseries(s2, "Sentinel-2 spectral indices", "interval_from", "index", value_col="mean")
      show_table(s2, "s2_env", height=420)
    else:
      st.info("Sem linhas Sentinel-2. Admin: verifique credenciais Copernicus e a janela de datas; usuários públicos apenas visualizam dados persistentes já baixados.")
  with t3:
    if not s1.empty:
      fig = px.line(s1, x="interval_from", y="mean", color="index", facet_row="sample_id", markers=True, title="Sentinel-1 SAR indices — overview for all selected coordinates/samples")
      fig.update_layout(height=max(560, 220 * max(1, s1["sample_id"].nunique())), xaxis_title="Time interval", yaxis_title="Mean SAR value")
      render_plotly_downloadable(fig, key="sentinel1_sar_downloaded", basename="sentinel1_sar_downloaded")
      render_per_coordinate_timeseries(s1, "Sentinel-1 SAR indices", "interval_from", "index", value_col="mean")
      show_table(s1, "s1_env", height=420)
    else:
      st.info("Sem linhas Sentinel-1. Admin: verifique credenciais Copernicus e a janela de datas; usuários públicos apenas visualizam dados persistentes já baixados.")
  with t4:
    if not sentinel6.empty:
      st.caption("Sentinel-6/Jason-CS: metadados de grânulos de altimetria obtidos via NASA CMR/PO.DAAC para a janela de data e coordenada selecionadas. O app não simula altura da superfície; arquivos NetCDF completos podem exigir Earthdata Login conforme os links retornados.")
      if "coverage_status" in sentinel6.columns:
        fig_df = sentinel6.copy()
        if "time_start" in fig_df.columns:
          fig_df["time_start"] = pd.to_datetime(fig_df["time_start"], errors="coerce")
          plot_df = fig_df[fig_df.get("coverage_status", "").astype(str).eq("covered")].copy()
          if not plot_df.empty:
            fig = px.scatter(plot_df, x="time_start", y="sample_id", color="collection_short_name", hover_data=[c for c in ["producer_granule_id", "data_url_count", "first_data_url"] if c in plot_df.columns], title="Sentinel-6/Jason-CS granule coverage — selected dates and coordinates")
            fig.update_layout(height=max(420, 80 * max(1, plot_df["sample_id"].nunique())), xaxis_title="Granule start time", yaxis_title="Sample/coordinate")
            render_plotly_downloadable(fig, key="sentinel6_granule_coverage", basename="sentinel6_granule_coverage")
      show_table(sentinel6, "sentinel6_env", height=420)
    else:
      st.info("Sem linhas Sentinel-6. Admin: use cobertura/download Sentinel-6 para consultar CMR/PO.DAAC; usuários públicos apenas visualizam dados persistentes já baixados.")
  with t5:
    if not earthdata.empty:
      st.caption("NASA Earthdata/CMR complementa o Copernicus e as APIs públicas usando apenas as coordenadas e datas do artigo. O app consulta CMR, salva metadados e baixa arquivos com earthaccess quando houver autenticação; se já houver arquivo local, não baixa novamente.")
      if "time_start" in earthdata.columns:
        fig_df = earthdata.copy()
        fig_df["time_start"] = pd.to_datetime(fig_df["time_start"], errors="coerce")
        plot_df = fig_df[fig_df.get("coverage_status", "").astype(str).eq("covered")].copy()
        if not plot_df.empty:
          fig = px.scatter(plot_df, x="time_start", y="sample_id", color="product_key", hover_data=[c for c in ["collection_short_name", "producer_granule_id", "download_status", "local_file_count", "first_data_url"] if c in plot_df.columns], title="NASA Earthdata/CMR product coverage — article dates and coordinates")
          fig.update_layout(height=max(420, 80 * max(1, plot_df["sample_id"].nunique())), xaxis_title="Granule/product time", yaxis_title="Sample/coordinate")
          render_plotly_downloadable(fig, key="earthdata_cmr_product_coverage", basename="earthdata_cmr_product_coverage")
      show_table(earthdata, "earthdata_env", height=420)
      csv_button(earthdata, "nasa_earthdata_cmr_article_dates.csv", "Baixar NASA Earthdata/CMR")
    else:
      st.info("Sem linhas NASA Earthdata/CMR. Admin: baixe a camada NASA Earthdata complementar para consultar IMERG/MERRA-2/MODIS/SMAP/PO.DAAC nas datas/coordenadas do artigo.")
  with t6:
    if not soil.empty:
      fig = px.bar(soil, x="depth", y="value_mean", color="property", facet_row="sample_id", barmode="group", title="SoilGrids predicted soil properties — overview for all selected coordinates/samples")
      fig.update_layout(height=max(560, 230 * max(1, soil["sample_id"].nunique())), xaxis_title="Depth", yaxis_title="Predicted mean value")
      render_plotly_downloadable(fig, key="soilgrids_properties_downloaded", basename="soilgrids_properties_downloaded")
      render_per_coordinate_soil(soil)
      show_table(soil, "soil_env", height=420)
  with t7:
    if not mapbiomas.empty:
      fig = px.bar(mapbiomas, x="class_name", y="fraction", color="sample_id", barmode="group", title="MapBiomas land-cover fractions — overview for all selected coordinates/samples")
      fig.update_layout(height=560, xaxis_tickangle=-45, xaxis_title="Land-cover class", yaxis_title="Fraction")
      render_plotly_downloadable(fig, key="mapbiomas_class_fractions_downloaded", basename="mapbiomas_class_fractions_downloaded")
      render_per_coordinate_mapbiomas(mapbiomas)
      show_table(mapbiomas, "mapbiomas_env", height=420)
    else:
      st.info("Sem linhas MapBiomas. Verifique o buffer/credenciais/limites do serviço.")
    render_environmental_heatmaps(results)
  with t8:
    st.markdown("#### Data-source audit")
    st.caption("Each row records the selected coordinate/date window, the source queried, rows returned, and any source error. Missing rows are not filled with simulated values.")
    if isinstance(source_audit, pd.DataFrame) and not source_audit.empty:
      show_table(source_audit, "environmental_source_audit", height=420)
      csv_button(source_audit, "environmental_source_audit.csv", "Download source audit")
    else:
      st.info("No source audit is available yet.")
  with t9:
    for key, label in [("nasa", "NASA POWER"), ("chirps", "CHIRPS"), ("sentinel2", "Sentinel-2"), ("sentinel1", "Sentinel-1"), ("sentinel6", "Sentinel-6 audit"), ("earthdata", "NASA Earthdata/CMR"), ("soil", "SoilGrids"), ("mapbiomas", "MapBiomas")]:
      df = results.get(key, pd.DataFrame())
      csv_button(df, f"{key}_article_collection_dates.csv", f"Baixar {label}")


def integrated_ordination_panel(results: dict):
  st.markdown("### Integração metagenômica + ambiente")
  st.caption(
    "As ordenações usam somente dados carregados: tabelas suplementares + camadas ambientais baixadas/armazenadas em cache. "
    "PCoA e NMDS oferecem biplots taxonômicos opcionais em Phylum, Order, Genus ou Species, com n entre 2 e 20. A RDA mostra vetores ambientais e táxons com rótulos repelidos e conectores. Nenhum valor ambiental é simulado."
  )
  env = environmental_matrix(
    results.get("nasa", pd.DataFrame()),
    results.get("chirps", pd.DataFrame()),
    results.get("sentinel2", pd.DataFrame()),
    results.get("sentinel1", pd.DataFrame()),
    results.get("sentinel6", pd.DataFrame()),
    results.get("earthdata", pd.DataFrame()),
    results.get("soil", pd.DataFrame()),
    results.get("mapbiomas", pd.DataFrame()),
  )

  c1, c2, c3 = st.columns([0.34, 0.33, 0.33])
  with c1:
    taxonomy_level = st.selectbox("Microbiota / nível taxonômico", list(TAXONOMY_LEVELS.keys()), index=0, key="integr_tax_level")
    top_taxa = st.slider("Top taxa", 5, 150, 40, step=5, key="integr_top_taxa")
  with c2:
    top_ko = st.slider("Top KOs/marcadores", 10, 200, 80, step=10, key="integr_top_ko")
    include_tax = st.checkbox("Incluir microbiota", value=True, key="integr_include_tax")
    include_bio = st.checkbox("Incluir KO biomarkers C/N/S/CH4/fotossíntese", value=True, key="integr_include_bio")
    include_bio_path = st.checkbox("Incluir categorias metabólicas", value=True, key="integr_include_bio_path")
  with c3:
    include_fe = st.checkbox("Incluir marcadores de ferro", value=True, key="integr_include_fe")
    include_fe_role = st.checkbox("Incluir categorias de ferro", value=True, key="integr_include_fe_role")
    include_metals = st.checkbox("Incluir outros metais", value=True, key="integr_include_metals")

  omics, group_kind = combined_omics_matrix(
    taxonomy_level=taxonomy_level,
    include_taxonomy=include_tax,
    include_biogeochemical_ko=include_bio,
    include_biogeochemical_pathway=include_bio_path,
    include_iron_ko=include_fe,
    include_iron_role=include_fe_role,
    include_other_metals=include_metals,
    top_taxa=top_taxa,
    top_ko=top_ko,
  )
  integrated = make_integrated_table(env, omics, group_kind)
  id_col = group_kind

  st.write(f"**Escopo da análise:** `{group_kind}`. Quando o nível taxonômico está agregado por `environment_feature`, os dados ambientais e KO são agregados por `environment_feature` sem simulação.")
  if integrated.empty:
    st.warning("A matriz integrada está vazia. Baixe pelo menos uma camada ambiental e selecione contagens/níveis disponíveis.")
    return

  # Interactive filtering by sample/group. This makes it possible to inspect all samples together or subsets such as AM, TI, VI, dry/rainy groups.
  st.markdown("#### Seleção de amostras/grupos para os gráficos")
  f1, f2, f3 = st.columns([0.38, 0.31, 0.31])
  with f1:
    available_units = sorted(integrated[id_col].dropna().astype(str).unique().tolist()) if id_col in integrated.columns else []
    selected_units = st.multiselect(
      "Amostras/grupos incluídos",
      available_units,
      default=available_units,
      key=f"integrated_units_{id_col}",
    )
  with f2:
    available_lakes = sorted(integrated.get("lake", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()) if "lake" in integrated.columns else []
    selected_lakes = st.multiselect("Lagos", available_lakes, default=available_lakes, key="integrated_lake_filter") if available_lakes else []
  with f3:
    available_seasons = sorted(integrated.get("season", pd.Series(dtype=str)).dropna().astype(str).unique().tolist()) if "season" in integrated.columns else []
    selected_seasons = st.multiselect("Estações", available_seasons, default=available_seasons, key="integrated_season_filter") if available_seasons else []
  if selected_units:
    integrated = integrated[integrated[id_col].astype(str).isin(selected_units)].copy()
  if selected_lakes and "lake" in integrated.columns:
    integrated = integrated[integrated["lake"].astype(str).isin(selected_lakes)].copy()
  if selected_seasons and "season" in integrated.columns:
    integrated = integrated[integrated["season"].astype(str).isin(selected_seasons)].copy()
  if integrated.empty:
    st.warning("Nenhuma amostra/grupo ficou disponível após os filtros.")
    return

  feature_scope_options = [
    "Taxa only",
    "Biomarkers/KO/metabolic markers",
    "Environmental variables",
    "All integrated variables",
  ]
  pca_scope = st.selectbox("PCA — variáveis usadas", feature_scope_options, index=3, key="integr_pca_scope")
  st.caption(txt(
    "PCoA e NMDS podem exibir vetores taxonômicos selecionáveis; a RDA exibe vetores ambientais e taxonômicos com conectores e repelimento de rótulos.",
    "PCoA and NMDS can display selectable taxonomic vectors; RDA displays environmental and taxonomic vectors with connectors and label repulsion."
  ))

  i1, i2, i3 = st.columns(3)
  i1.metric("Unidades analisadas", integrated[id_col].nunique() if id_col in integrated.columns and not integrated.empty else 0)
  i2.metric("Features metagenômicas/KO", len([c for c in integrated.columns if c.startswith(("tax__", "ko_", "metab_", "role_"))]))
  i3.metric("Features ambientais", len([c for c in integrated.columns if c.startswith(("nasa_", "chirps_", "sentinel2_", "sentinel1_", "soilgrids_", "mapbiomas_"))]))

  corr = omics_environment_correlations(integrated, id_col=id_col, max_omics_features=80, max_env_features=80)
  tab_names = ["Matriz integrada", "PCA", "PCoA", "NMDS", "RDA", "Downloads"]
  if not corr.empty:
    tab_names.insert(4, "Correlações")
  tabs = st.tabs(tab_names)
  tab_map = dict(zip(tab_names, tabs))

  with tab_map["Matriz integrada"]:
    show_table(integrated, "integrated_table", height=520)

  with tab_map["PCA"]:
    pca_scores, pca_loadings, pca_var = pca_integrated(integrated, id_col=id_col, feature_scope=pca_scope)
    if not pca_scores.empty:
      var1 = float(pca_var.loc[pca_var["axis"].eq("PC1"), "explained_variance_percent"].iloc[0]) if not pca_var.empty and pca_var["axis"].eq("PC1").any() else np.nan
      var2 = float(pca_var.loc[pca_var["axis"].eq("PC2"), "explained_variance_percent"].iloc[0]) if not pca_var.empty and pca_var["axis"].eq("PC2").any() else np.nan
      title = f"PCA — variáveis combinadas ({pca_scope})"
      fig = ordination_figure(pca_scores, "PC1", "PC2", id_col, title)
      fig.update_xaxes(title_text=f"PC1 ({var1:.1f}% da variância)" if pd.notna(var1) else "PC1")
      fig.update_yaxes(title_text=f"PC2 ({var2:.1f}% da variância)" if pd.notna(var2) else "PC2")
      render_plotly_downloadable(fig, key=f"integrated_pca_no_biplot_{id_col}_{taxonomy_level}", basename=f"integrated_pca_no_biplot_{id_col}_{taxonomy_level}")
      st.markdown("#### Variância explicada")
      show_table(pca_var, "pca_explained_variance", height=140)
      st.markdown("#### Contribuição das variáveis para PC1/PC2")
      show_table(pca_loadings.head(120), "pca_variable_contributions", height=420)
    else:
      st.info("PCA requer pelo menos 3 unidades e 2 variáveis numéricas com variação. Ajuste o escopo, os filtros ou baixe mais camadas ambientais.")

  with tab_map["PCoA"]:
    pcoa, var = pcoa_bray_curtis(integrated, id_col=id_col)
    if not pcoa.empty:
      bp1, bp2, bp3 = st.columns([0.35, 0.35, 0.30])
      with bp1:
        pcoa_show_biplot = st.checkbox(txt("Mostrar biplot de táxons", "Show taxon biplot"), value=False, key="integrated_pcoa_show_biplot")
      with bp2:
        pcoa_rank = st.selectbox(txt("Nível taxonômico", "Taxonomic rank"), ["Phylum", "Order", "Genus", "Species"], index=2, key="integrated_pcoa_rank", disabled=not pcoa_show_biplot)
      with bp3:
        pcoa_n = st.select_slider(txt("Número de táxons", "Number of taxa"), options=list(range(2,21,2)), value=6, key="integrated_pcoa_n", disabled=not pcoa_show_biplot)
      pcoa_var1 = float(var.loc[var["axis"].eq("PCoA1"), "explained_variance_percent"].iloc[0]) if not var.empty and var["axis"].eq("PCoA1").any() else np.nan
      pcoa_var2 = float(var.loc[var["axis"].eq("PCoA2"), "explained_variance_percent"].iloc[0]) if not var.empty and var["axis"].eq("PCoA2").any() else np.nan
      pcoa_correction = str(var["correction"].iloc[0]) if not var.empty and "correction" in var.columns else "none"
      fig = ordination_figure(pcoa, "PCoA1", "PCoA2", id_col, f"PCoA — Bray–Curtis, transformação do artigo ({pcoa_correction} correction)")
      fig.update_xaxes(title_text=f"PCoA1 ({pcoa_var1:.2f}% explained)" if pd.notna(pcoa_var1) else "PCoA1")
      fig.update_yaxes(title_text=f"PCoA2 ({pcoa_var2:.2f}% explained)" if pd.notna(pcoa_var2) else "PCoA2")
      if not var.empty and int(var.get("negative_eigenvalue_count_before_correction", pd.Series([0])).iloc[0]) > 0:
        st.warning(txt(
          f"A distância Bray–Curtis produziu {int(var['negative_eigenvalue_count_before_correction'].iloc[0])} autovalores negativos; foi aplicada correção {pcoa_correction}, documentada na tabela abaixo.",
          f"Bray–Curtis produced {int(var['negative_eigenvalue_count_before_correction'].iloc[0])} negative eigenvalues; the documented {pcoa_correction} correction was applied."
        ))
      pcoa_vectors = pd.DataFrame()
      if pcoa_show_biplot:
        tax_matrix = cds_taxonomy_group_matrix(pcoa_rank, groups=pcoa[id_col].astype(str).tolist(), top_n=max(80, int(pcoa_n)*5))
        ord_for_vectors = pcoa[[id_col, "PCoA1", "PCoA2"]].rename(columns={id_col:"group"})
        pcoa_vectors = ordination_taxon_vectors(tax_matrix, ord_for_vectors, "PCoA1", "PCoA2", top_n=int(pcoa_n))
        fig = add_taxon_biplot_vectors(fig, pcoa_vectors, "PCoA1", "PCoA2", ord_for_vectors)
      render_plotly_downloadable(fig, key=f"integrated_pcoa_{id_col}_{pcoa_rank}_{pcoa_n}_{pcoa_show_biplot}", basename=f"integrated_pcoa_{id_col}_{pcoa_rank}_n{pcoa_n}")
      show_table(var, "pcoa_var", height=120)
      if not pcoa_vectors.empty:
        show_table(pcoa_vectors, "integrated_pcoa_taxon_vectors", height=300)
        csv_button(pcoa_vectors, f"integrated_PCoA_{pcoa_rank}_n{pcoa_n}_vectors.csv", txt("Baixar vetores do biplot", "Download biplot vectors"))
      axis_corr = env_axis_correlations(integrated, pcoa, id_col, ["PCoA1", "PCoA2"])
      if not axis_corr.empty:
        st.markdown("#### Variáveis ambientais correlacionadas com os eixos da PCoA")
        show_table(axis_corr.head(100), "pcoa_env_corr", height=360)
    else:
      st.info("PCoA requer pelo menos 3 unidades e 2 features com variação.")

  with tab_map["NMDS"]:
    nmds = nmds_bray_curtis(integrated, id_col=id_col)
    if not nmds.empty:
      bn1, bn2, bn3 = st.columns([0.35, 0.35, 0.30])
      with bn1:
        nmds_show_biplot = st.checkbox(txt("Mostrar biplot de táxons", "Show taxon biplot"), value=False, key="integrated_nmds_show_biplot")
      with bn2:
        nmds_rank = st.selectbox(txt("Nível taxonômico", "Taxonomic rank"), ["Phylum", "Order", "Genus", "Species"], index=2, key="integrated_nmds_rank", disabled=not nmds_show_biplot)
      with bn3:
        nmds_n = st.select_slider(txt("Número de táxons", "Number of taxa"), options=list(range(2,21,2)), value=6, key="integrated_nmds_n", disabled=not nmds_show_biplot)
      nmds_stress = float(nmds["stress_1"].iloc[0])
      fig = ordination_figure(nmds, "NMDS1", "NMDS2", id_col, f"NMDS — Bray–Curtis, transformação do artigo (normalized Stress-1 = {nmds_stress:.3f})")
      nmds_vectors = pd.DataFrame()
      if nmds_show_biplot:
        tax_matrix = cds_taxonomy_group_matrix(nmds_rank, groups=nmds[id_col].astype(str).tolist(), top_n=max(80, int(nmds_n)*5))
        ord_for_vectors = nmds[[id_col, "NMDS1", "NMDS2"]].rename(columns={id_col:"group"})
        nmds_vectors = ordination_taxon_vectors(tax_matrix, ord_for_vectors, "NMDS1", "NMDS2", top_n=int(nmds_n))
        fig = add_taxon_biplot_vectors(fig, nmds_vectors, "NMDS1", "NMDS2", ord_for_vectors)
      render_plotly_downloadable(fig, key=f"integrated_nmds_{id_col}_{nmds_rank}_{nmds_n}_{nmds_show_biplot}", basename=f"integrated_nmds_{id_col}_{nmds_rank}_n{nmds_n}")
      st.metric("Normalized NMDS Stress-1", f"{float(nmds['stress_1'].iloc[0]):.4f}")
      st.caption(txt(
        "Pré-processamento e otimizador: proporções por unidade, raiz quadrada, Bray–Curtis, 20 inicializações, máximo de 1.000 iterações e semente 42 — os mesmos parâmetros NMDS do artigo.",
        "Preprocessing and optimiser: unit-wise proportions, square root, Bray–Curtis, 20 starts, a 1,000-iteration maximum and seed 42 — the same NMDS settings as the article."
      ))
      if not nmds_vectors.empty:
        show_table(nmds_vectors, "integrated_nmds_taxon_vectors", height=300)
        csv_button(nmds_vectors, f"integrated_NMDS_{nmds_rank}_n{nmds_n}_vectors.csv", txt("Baixar vetores do biplot", "Download biplot vectors"))
      axis_corr = env_axis_correlations(integrated, nmds, id_col, ["NMDS1", "NMDS2"])
      if not axis_corr.empty:
        st.markdown("#### Variáveis ambientais correlacionadas com os eixos da NMDS")
        show_table(axis_corr.head(100), "nmds_env_corr", height=360)
    else:
      st.info("NMDS requer pelo menos 4 unidades e 2 features com variação.")

  with tab_map["RDA"]:
    st.markdown("#### " + txt("RDA canônica do artigo", "Canonical article RDA"))
    st.caption(txt("Este painel utiliza exatamente os escores, vetores ambientais, amostras, variáveis e seleção de táxons produzidos pelo processamento compartilhado do artigo. O modo interativo não recalcula a RDA.", "This panel uses exactly the site scores, environmental vectors, samples, variables and taxon selection produced by the shared article processing. The interactive view does not recalculate the RDA."))
    try:
      fig_rda, rda_scores, rda_vectors, rda_taxa = publication_rda_figure(BASE_DIR)
      render_plotly_downloadable(fig_rda,key="canonical_publication_rda",basename="canonical_publication_RDA")
      csv_button(rda_scores,"Figure_Bacteria_genus_RDA_site_scores.csv",txt("Baixar escores RDA", "Download RDA scores"))
      csv_button(rda_vectors,"Figure_Bacteria_genus_RDA_environment_vectors.csv",txt("Baixar vetores ambientais", "Download environmental vectors"))
      csv_button(rda_taxa,"Figure_Bacteria_genus_RDA_representative_genus_vectors.csv",txt("Baixar vetores taxonômicos", "Download taxon vectors"))
    except Exception as exc:
      st.error(txt(f"Não foi possível carregar a RDA canônica: {exc}", f"Could not load the canonical RDA: {exc}"))

  with tab_map["Downloads"]:
    csv_button(env, "environmental_features_by_article_sample.csv", "Baixar matriz ambiental resumida")
    csv_button(omics, "omics_marker_matrix.csv", "Baixar matriz microbiota_KO_metabolismo")
    csv_button(integrated, "integrated_omics_environment_matrix.csv", "Baixar matriz integrada filtrada")

def environmental_integrator_tab():
  load_persistent_env_results()
  st.subheader(txt("Integrador ambiental–metagenômico", "Environmental–Metagenomic Integrator"))
  st.markdown(
    txt(
      "Este módulo integra datas de coleta, coordenadas, camadas ambientais públicas e resultados metagenômicos do artigo. Quando uma fonte não responde, exige credencial ou não possui cobertura, a falha aparece na interface.",
      "This module integrates collection dates, coordinates, public environmental layers and metagenomic article results. When a source does not respond, requires credentials or lacks coverage, the failure is shown in the interface."
    )
  )
  with st.expander(txt("Estado persistente, limpeza de dados e cache", "Persistent state, data clearing and cache"), expanded=False):
    active = load_persistent_env_results()
    if active:
      meta_state = active.get("metadata", {}) if isinstance(active.get("metadata", {}), dict) else {}
      st.success(txt(
        f"Há resultados ambientais vigentes preservados. Status: {meta_state.get('status', 'available')} | salvo em: {meta_state.get('saved_at', 'sessão atual')}.",
        f"Active environmental results are preserved. Status: {meta_state.get('status', 'available')} | saved at: {meta_state.get('saved_at', 'current session')}."
      ))
    else:
      st.info(txt("Nenhum resultado ambiental vigente foi salvo ainda.", "No active environmental result has been saved yet."))
    st.caption(txt(
      "O app mantém resultados e caches em diretórios graváveis do usuário, fora da pasta do projeto. Trocar de módulo não apaga esses dados.",
      "The app keeps active results and API caches in user-writable directories outside the project folder. Changing modules does not delete these data."
    ))
    if is_admin_authenticated():
      cclear1, cclear2 = st.columns(2)
      with cclear1:
        if st.button(txt("Limpar dados vigentes", "Clear active data"), key="clear_env_runtime_results_panel", width="stretch"):
          removed = clear_persistent_env_results()
          st.success(txt(f"Dados vigentes removidos ({removed} arquivos locais).", f"Active data removed ({removed} local files)."))
          st.rerun()
      with cclear2:
        if st.button(txt("Apagar cache das APIs", "Delete API cache"), key="clear_env_api_cache_panel", width="stretch"):
          removed = clear_api_cache_and_runtime_results()
          st.success(txt(f"Cache e dados vigentes removidos ({removed} arquivos locais).", f"Cache and active data removed ({removed} local files)."))
          st.rerun()
    else:
      st.caption(txt(
        "Limpeza de dados/cache é restrita ao admin para preservar os arquivos baixados e evitar perda acidental dos resultados do artigo.",
        "Data/cache clearing is admin-only to preserve downloaded files and avoid accidental loss of article results.",
      ))
  if is_admin_authenticated():
    environmental_connection_center(load_persistent_env_results() or {})
  article_meta = taxonomy_samples_metadata()
  fig11_meta = figure11_environment_metadata()
  scope = st.radio(
    txt("Escopo de coordenadas/datas", "Coordinate/date scope"),
    [
      txt("Somente lagoas lateríticas amazônicas — AM, TI, TIA e VI", "Amazonian lateritic lakes only — AM, TI, TIA and VI"),
      txt("Somente outros ambientes ricos em ferro — IMG/M/JGI", "Other iron-rich environments only — IMG/M/JGI"),
      txt("Amostras do artigo — Supplementary Table 1", "Article samples — Supplementary Table 1"),
      txt("Amostras/ambientes da comparação completa — Supplementary Table 8", "Complete comparison samples/environments — Supplementary Table 8"),
      txt("Ambos", "Both"),
    ],
    horizontal=False,
    key="env_metadata_scope",
  )
  group_series = (
    fig11_meta["dataset_group"].astype(str)
    if "dataset_group" in fig11_meta.columns
    else pd.Series("", index=fig11_meta.index, dtype=str)
  )
  if scope.startswith("Somente lagoas") or scope.startswith("Amazonian lateritic"):
    meta = fig11_meta[group_series.eq("Amazonian lateritic lakes")].copy()
  elif scope.startswith("Somente outros") or scope.startswith("Other iron-rich"):
    meta = fig11_meta[group_series.ne("Amazonian lateritic lakes")].copy()
  elif scope.startswith("Amostras do artigo") or scope.startswith("Article samples"):
    meta = article_meta.copy()
  elif scope.startswith("Amostras/ambientes") or scope.startswith("Complete comparison"):
    meta = fig11_meta.copy()
  else:
    meta = pd.concat([article_meta.assign(dataset_group="Article samples"), fig11_meta], ignore_index=True, sort=False)
  if meta.empty:
    st.error(txt("Não foi possível ler os metadados selecionados.", "Could not read the selected metadata."))
    return
  if "sample.id" not in meta.columns and "sample_id" in meta.columns:
    meta["sample.id"] = meta["sample_id"]
  required_cols = {"sample.id", "collection_date", "lat", "lon"}
  missing = required_cols.difference(meta.columns)
  if missing:
    st.error(f"Metadados incompletos para integração ambiental: {', '.join(sorted(missing))}")
    return
  meta_valid = meta.copy()
  # Normalize heterogeneous metadata defensively. Text placeholders such as
  # "Not reported in packaged metadata" must never be parsed as dates or numbers.
  meta_valid["collection_date"] = pd.to_datetime(meta_valid["collection_date"], errors="coerce")
  meta_valid["lat"] = pd.to_numeric(meta_valid["lat"], errors="coerce")
  meta_valid["lon"] = pd.to_numeric(meta_valid["lon"], errors="coerce")
  meta_valid = meta_valid.dropna(subset=["collection_date", "lat", "lon"]).copy()
  # Keep exact source/date precision visible. Duplicate coordinates/dates are collapsed only when they are identical.
  dedup_cols = [c for c in ["sample.id", "matrix_column", "collection_date", "lat", "lon"] if c in meta_valid.columns]
  meta_valid = meta_valid.drop_duplicates(subset=dedup_cols).reset_index(drop=True)
  def _env_row_label(r):
    sample = sample_display_id(r)
    env = display_text(r, ["environment_feature", "habitat", "specific_ecosystem"], "environment not provided")
    precision = display_text(r, ["collection_date_precision"], "")
    date_value = r.get("collection_date")
    parsed_date = pd.to_datetime(date_value, errors="coerce")
    date_label = "date unavailable" if pd.isna(parsed_date) else str(parsed_date.date())
    return f"{sample} | {env} | {date_label}" + (f" | {precision}" if precision else "")

  meta_valid["sample_label"] = meta_valid.apply(_env_row_label, axis=1)

  prepare_metadata_download(meta_valid)

  if not is_admin_authenticated():
    st.markdown("### " + txt("Dados ambientais persistentes do artigo", "Persistent article environmental data"))
    st.info(txt(
      "Modo usuário: downloads BV-BRC, Sentinel/Copernicus, NASA Earthdata, credenciais, atualização de cobertura e limpeza de cache são exclusivos do admin. Os usuários visualizam apenas dados já baixados e salvos localmente.",
      "User mode: BV-BRC, Sentinel/Copernicus, NASA Earthdata downloads, credentials, coverage refresh and cache clearing are admin-only. Users only view data already downloaded and saved locally.",
    ))
    results = load_persistent_env_results()
    if st.session_state.get("env_download_results_loaded_from_disk"):
      st.success(txt("Resultados ambientais vigentes restaurados do armazenamento local persistente.", "Active environmental results restored from persistent local storage."))
      st.session_state.pop("env_download_results_loaded_from_disk", None)
    if results:
      show_environmental_results(results)
      st.divider()
      integrated_ordination_panel(results)
    else:
      st.warning(txt(
        "Nenhum dado ambiental persistente foi encontrado. Entre como admin, baixe as camadas do artigo uma vez e os resultados ficarão disponíveis para os usuários.",
        "No persistent environmental data were found. Log in as admin, download the article layers once, and the results will become available to users.",
      ))
    return

  st.markdown("### " + txt("Baixar camadas ambientais para as datas selecionadas — admin", "Download environmental layers for selected dates — admin"))
  c1, c2, c3 = st.columns([0.42, 0.29, 0.29])
  with c1:
    use_all_dates = st.checkbox(
      txt("Baixar todas as amostras/datas disponíveis", "Download all available samples/dates"),
      value=True,
      key="env_download_all_samples",
    )
    sample_labels = meta_valid["sample_label"].tolist()
    selected_labels = st.multiselect(
      txt("Selecionar amostras/datas", "Select samples/dates"),
      sample_labels,
      default=[] if use_all_dates else sample_labels,
      disabled=use_all_dates,
      key="env_selected_samples",
    )
    selected = meta_valid.copy() if use_all_dates else meta_valid[meta_valid["sample_label"].isin(selected_labels)].copy()
    st.caption(txt(
      f"Linhas selecionadas para download: {len(selected)} de {len(meta_valid)}.",
      f"Rows selected for download: {len(selected)} of {len(meta_valid)}.",
    ))
  with c2:
    window_mode = st.selectbox(txt("Janela em torno da data de coleta", "Window around collection date"), ["Exact collection day", "±3 days", "±7 days", "±15 days", "±30 days", "Collection month", "Collection year"], index=3, key="env_window")
    buffer_m = st.slider(txt("Buffer em torno das coordenadas (m)", "Buffer around coordinates (m)"), 60, 3000, 500, step=20, key="env_buffer")
    max_cloud = st.slider(txt("Sentinel-2 cobertura máxima de nuvens (%)", "Sentinel-2 maximum cloud cover (%)"), 0, 100, 30, step=5, key="env_cloud")
  with c3:
    use_cache = st.checkbox(txt("Usar cache local quando existir", "Use local cache when available"), value=True, key="env_cache")
    layers = {
      "nasa": st.checkbox("NASA POWER: temperatura, umidade, chuva, vento e radiação", value=True, key="lyr_nasa"),
      "chirps": st.checkbox("CHIRPS: precipitação histórica", value=False, key="lyr_chirps"),
      "sentinel2": st.checkbox("Sentinel-2/Copernicus: NDVI, NDWI, NDMI, EVI, SAVI, MSAVI, NBR, NDRE, BSI", value=False, key="lyr_s2"),
      "sentinel1": st.checkbox("Sentinel-1/Copernicus SAR: VV, VH, VH/VV, diferença normalizada, RVI", value=False, key="lyr_s1"),
      "sentinel6": st.checkbox("Sentinel-6/Jason-CS: metadados de grânulos de altimetria NASA CMR/PO.DAAC", value=False, key="lyr_s6"),
      "earthdata": st.checkbox("NASA Earthdata complementar: IMERG, MERRA-2, MODIS, SMAP e PO.DAAC", value=False, key="lyr_earthdata"),
      "soil": st.checkbox("SoilGrids/ISRIC: propriedades do solo", value=True, key="lyr_soil"),
      "mapbiomas": st.checkbox("MapBiomas via Google Earth Engine", value=False, key="lyr_mapbiomas"),
    }
    earthdata_options = list(EARTHDATA_PRODUCT_REGISTRY.keys())
    default_earthdata = ["imerg_daily", "merra2_slv", "merra2_flx", "merra2_lnd", "modis_ndvi", "modis_lst", "smap_soil_moisture", "podaac_sentinel6"]
    if layers.get("earthdata"):
      layers["earthdata_products"] = st.multiselect(
        "Produtos NASA Earthdata complementares ao artigo",
        earthdata_options,
        default=[p for p in default_earthdata if p in earthdata_options],
        format_func=lambda k: f"{k} — {EARTHDATA_PRODUCT_REGISTRY.get(k, {}).get('label', k)}",
        key="earthdata_product_multiselect",
      )
      layers["earthdata_max_granules"] = st.slider("Máximo de grânulos CMR por produto/amostra", 1, 100, 20, step=1, key="earthdata_max_granules")
      layers["earthdata_force_update"] = st.checkbox("Forçar novo download NASA Earthdata mesmo se já existir cache/arquivo local", value=False, key="earthdata_force_update")
      st.caption("Earthdata é usado somente para enriquecer as datas/coordenadas do artigo. Se já houver arquivo local válido, o app reutiliza o cache e não baixa novamente, salvo com forçar atualização.")
    else:
      layers["earthdata_products"] = []
      layers["earthdata_max_granules"] = 20
      layers["earthdata_force_update"] = False

  st.markdown("#### " + txt("Teste obrigatório antes do download CHIRPS/ClimateSERV", "Required test before CHIRPS/ClimateSERV download"))
  st.caption(txt(
    "Se CHIRPS estiver marcado, o app testa a API ClimateSERV com a primeira coordenada/data selecionada antes de iniciar qualquer download. Se o teste falhar, o download é cancelado e nada é simulado.",
    "If CHIRPS is selected, the app tests the ClimateSERV API with the first selected coordinate/date before starting any download. If the test fails, the download is cancelled and nothing is simulated."
  ))
  test_col1, test_col2 = st.columns([0.36, 0.64])
  with test_col1:
    if st.button("Testar CHIRPS / ClimateSERV agora", key="manual_chirps_preflight", width="stretch"):
      with st.spinner("Testing CHIRPS / ClimateSERV with the first selected coordinate/date..."):
        ok, chirps_preflight_df = chirps_preflight_for_download(selected, window_mode, buffer_m)
      st.session_state["chirps_preflight_before_download"] = chirps_preflight_df
      if ok:
        st.success("CHIRPS / ClimateSERV conectado. O download CHIRPS pode ser executado.")
      else:
        st.error("CHIRPS / ClimateSERV não conectou. O download CHIRPS será bloqueado até a API responder.")
  with test_col2:
    chirps_preflight_df = st.session_state.get("chirps_preflight_before_download")
    if isinstance(chirps_preflight_df, pd.DataFrame) and not chirps_preflight_df.empty:
      show_table(chirps_preflight_df, "chirps_preflight_before_download", height=160)
    else:
      st.info("Nenhum teste CHIRPS executado ainda nesta sessão.")

  button_label = txt("Baixar todas as camadas ambientais selecionadas" if use_all_dates else "Baixar camadas ambientais selecionadas", "Download all selected environmental layers" if use_all_dates else "Download selected environmental layers")
  if st.button(button_label, type="primary", key="run_env_integrator"):
    if selected.empty:
      st.warning(txt("Selecione pelo menos uma amostra/data.", "Select at least one sample/date."))
    else:
      if layers.get("chirps"):
        with st.spinner("Preflight: testing CHIRPS / ClimateSERV before download..."):
          chirps_ok, chirps_preflight_df = chirps_preflight_for_download(selected, window_mode, buffer_m)
        st.session_state["chirps_preflight_before_download"] = chirps_preflight_df
        show_table(chirps_preflight_df, "chirps_preflight_before_download_auto", height=160)
        if not chirps_ok:
          st.error(txt(
            "CHIRPS / ClimateSERV falhou no teste de conexão. O download foi cancelado antes de começar. Desmarque CHIRPS ou tente novamente quando a API estiver disponível.",
            "CHIRPS / ClimateSERV failed the connection test. The download was cancelled before starting. Uncheck CHIRPS or try again when the API is available."
          ))
          return
      fetch_environmental_layers(selected, window_mode, buffer_m, max_cloud, use_cache, layers)

  st.markdown("#### Sentinel-1, Sentinel-2 e Sentinel-6 — cobertura, atualização e download")
  st.caption("Admin: use estes botões para confirmar cobertura e baixar/atualizar dados Sentinel nas datas/coordenadas do artigo. Usuários públicos não veem esses controles e usam apenas os resultados persistentes já baixados.")
  sb1, sb2, sb3 = st.columns(3)
  sentinel_layers = {"sentinel2": bool(layers.get("sentinel2")), "sentinel1": bool(layers.get("sentinel1")), "sentinel6": bool(layers.get("sentinel6"))}
  with sb1:
    if st.button("Mostrar cobertura Sentinel", key="show_sentinel_coverage", width="stretch"):
      if selected.empty:
        st.warning("Selecione pelo menos uma amostra/data.")
      elif not any(sentinel_layers.values()):
        st.warning("Marque Sentinel-1, Sentinel-2 ou Sentinel-6 antes de mostrar a cobertura.")
      else:
        fetch_sentinel_coverage_layers(selected, window_mode, buffer_m, max_cloud, use_cache=True, layers=sentinel_layers)
  with sb2:
    if st.button("Atualizar cobertura Sentinel", key="refresh_sentinel_coverage", width="stretch"):
      if selected.empty:
        st.warning("Selecione pelo menos uma amostra/data.")
      elif not any(sentinel_layers.values()):
        st.warning("Marque Sentinel-1, Sentinel-2 ou Sentinel-6 antes de atualizar a cobertura.")
      else:
        fetch_sentinel_coverage_layers(selected, window_mode, buffer_m, max_cloud, use_cache=False, layers=sentinel_layers)
  with sb3:
    if st.button("Baixar/atualizar dados Sentinel", key="download_only_sentinel_layers", type="primary", width="stretch"):
      if selected.empty:
        st.warning("Selecione pelo menos uma amostra/data.")
      elif not any(sentinel_layers.values()):
        st.warning("Marque Sentinel-1, Sentinel-2 ou Sentinel-6 antes de baixar dados Sentinel.")
      else:
        sentinel_download_layers = {"nasa": False, "chirps": False, "sentinel2": sentinel_layers["sentinel2"], "sentinel1": sentinel_layers["sentinel1"], "sentinel6": sentinel_layers["sentinel6"], "soil": False, "mapbiomas": False}
        fetch_environmental_layers(selected, window_mode, buffer_m, max_cloud, use_cache=False, layers=sentinel_download_layers)

  coverage_results = st.session_state.get("env_sentinel_coverage_results")
  if coverage_results:
    show_sentinel_coverage_results(coverage_results)

  results = load_persistent_env_results()
  if st.session_state.get("env_download_results_loaded_from_disk"):
    st.success(txt("Resultados ambientais vigentes restaurados do armazenamento local persistente.", "Active environmental results restored from persistent local storage."))
    st.session_state.pop("env_download_results_loaded_from_disk", None)
  if not results:
    st.info(txt("Após clicar no botão acima, os resultados baixados aparecerão aqui e serão integrados com microbiota, KO biomarkers, ferro, outros metais e metabolismo.", "After clicking the button above, downloaded results will appear here and will be integrated with microbiota, KO biomarkers, iron, other metals and metabolism."))
    return

  st.divider()
  show_environmental_results(results)
  st.divider()
  integrated_ordination_panel(results)



@st.cache_data(show_spinner=False)
def load_st8_study_references_table() -> pd.DataFrame:
  """Load curated ST8 study-level bibliographic/data-source links."""
  try:
    if ST8_STUDY_REFERENCES_PATH.exists():
      df = pd.read_csv(ST8_STUDY_REFERENCES_PATH)
      return df.fillna("")
  except Exception:
    return pd.DataFrame()
  return pd.DataFrame()


def _safe_refs_series(refs: pd.DataFrame, column: str, default="") -> pd.Series:
  """Return a Series even when a column is absent; avoids scalar .fillna/.astype errors."""
  if isinstance(refs, pd.DataFrame) and column in refs.columns:
    return refs[column]
  return pd.Series([default] * len(refs), index=refs.index if isinstance(refs, pd.DataFrame) else None)


def _valid_metadata_value(value) -> bool:
  text = str(value or "").strip()
  if not text:
    return False
  return text.lower() not in {"na", "n/a", "nan", "none", "null", "<na>", "not available", "not informed"}


def _valid_http_url(value) -> bool:
  text = str(value or "").strip()
  return text.startswith("http://") or text.startswith("https://")


def _reference_link_candidates(row: pd.Series) -> list[tuple[str, str, str]]:
  """Return only official links backed by explicit ST8 metadata fields.

  Search-only links such as PubMed/Google Scholar are intentionally not
  displayed unless the workbook provides a concrete PubMed/DOI/article field.
  This prevents the public app from showing clickable links for references that
  were not actually present in the metadata.
  """
  links: list[tuple[str, str, str]] = []
  doi_url = str(row.get("doi_or_primary_article_url", row.get("doi_or_primary_article", "")) or "").strip()
  doi_meta = str(row.get("DOI", row.get("doi", row.get("PubMed ID", row.get("pubmed_id", "")))) or "").strip()
  if _valid_http_url(doi_url) and _valid_metadata_value(doi_meta):
    links.append(("DOI / article", doi_url, "Confirmed article metadata"))
  bioproject_url = str(row.get("ncbi_bioproject_url", row.get("NCBI_BioProject_url", "")) or "").strip()
  bioproject_meta = str(row.get("ncbi_bioprojects", row.get("NCBI_BioProject_accessions", "")) or "").strip()
  if _valid_http_url(bioproject_url) and _valid_metadata_value(bioproject_meta):
    links.append(("NCBI BioProject", bioproject_url, bioproject_meta))
  gold_url = str(row.get("gold_study_url", row.get("GOLD_study_url", "")) or "").strip()
  gold_meta = str(row.get("gold_study_ids", row.get("GOLD_study_ids", "")) or "").strip()
  first_gold = str(gold_meta).split(";")[0].strip() if _valid_metadata_value(gold_meta) else ""
  if first_gold and not _valid_http_url(gold_url):
    gold_url = f"https://gold.jgi.doe.gov/study?id={quote_plus(first_gold)}"
  if _valid_http_url(gold_url) and _valid_metadata_value(gold_meta):
    links.append(("GOLD study", gold_url, gold_meta))
  # IMG/JGI/taxon_oid metadata is intentionally summarized as text only.
  # No IMG/JGI button is displayed because generic portal links do not identify
  # a concrete article/reference and can confuse manuscript audit.
  pubmed_url = str(row.get("pubmed_article_url", row.get("PubMed_article_url", "")) or "").strip()
  pubmed_meta = str(row.get("PubMed ID", row.get("pubmed_id", "")) or "").strip()
  if _valid_http_url(pubmed_url) and _valid_metadata_value(pubmed_meta):
    links.append(("PubMed", pubmed_url, pubmed_meta))
  return links



def functional_annotations_tab():
  st.subheader(txt("Anotações funcionais IMG/JGI: KO, EC e PFAM", "IMG/JGI functional annotations: KO, EC and PFAM"))
  st.caption(txt(
    "As matrizes são lidas integralmente das Tabelas Suplementares 6 e 8. Os filtros atuam somente sobre colunas de amostras; nenhuma amostra de um estudo selecionado é removida silenciosamente.",
    "Matrices are read in full from Supplementary Tables 6 and 8. Filters act only on sample columns; no sample from a selected study is silently removed."
  ))

  source_options = ["table6", "table8", "combined"]
  source = st.radio(
    txt("Conjunto de anotações", "Annotation dataset"),
    source_options,
    format_func=lambda value: FUNCTIONAL_SOURCE_LABELS.get(value, value),
    horizontal=True,
    key="functional_annotation_source_v7",
  )
  annotation_type = st.selectbox(
    txt("Tipo de anotação", "Annotation type"),
    ["KO", "EC number", "PFAM"],
    key="functional_annotation_type_v7",
  )

  matrix, column_meta, id_col, name_col = build_annotation_dataset(source, annotation_type)
  if matrix.empty or column_meta.empty:
    st.error(txt("A matriz solicitada não está disponível no pacote.", "The requested matrix is not available in the package."))
    return

  metadata_cols = {id_col, name_col, "Metabolism", "Biologic Role", "KEGG MODULE"}
  sample_cols = [c for c in matrix.columns if c not in metadata_cols]
  column_meta = column_meta[column_meta["matrix_column"].astype(str).isin(set(map(str, sample_cols)))].copy()

  expected_samples = {"table6": 20, "table8": 67, "combined": 87}[source]
  expected_features = {
    ("table6", "KO"): 8045,
    ("table6", "EC number"): 2914,
    ("table6", "PFAM"): 8238,
    ("table8", "KO"): 12144,
    ("table8", "EC number"): 3514,
    ("table8", "PFAM"): 100,
  }
  if source == "combined":
    expected_feature_text = txt("união completa das duas planilhas", "complete union of both sheets")
  else:
    expected_feature_text = f"{expected_features[(source, annotation_type)]:,}"

  actual_samples = column_meta["matrix_column"].astype(str).nunique()
  integrity_ok = actual_samples == expected_samples
  if not integrity_ok:
    st.error(txt(
      f"Composição incompleta: esperadas {expected_samples} amostras/ambientes, mas foram ligadas {actual_samples}.",
      f"Incomplete composition: {expected_samples} samples/environments were expected, but {actual_samples} were linked."
    ))
  else:
    st.success(txt(
      f"Composição confirmada: {actual_samples}/{expected_samples} colunas de amostras; {len(matrix):,} funções ({expected_feature_text}).",
      f"Composition confirmed: {actual_samples}/{expected_samples} sample columns; {len(matrix):,} functions ({expected_feature_text})."
    ))

  filter_cols = st.columns(4)
  with filter_cols[0]:
    dataset_values = sorted(column_meta.get("source_dataset", pd.Series(dtype=str)).dropna().astype(str).unique().tolist())
    selected_datasets = st.multiselect(
      txt("Estudo-fonte", "Source dataset"), dataset_values, default=dataset_values,
      key=f"functional_datasets_v7_{source}_{annotation_type}",
    )
  dataset_meta = column_meta[column_meta.get("source_dataset", pd.Series("", index=column_meta.index)).astype(str).isin(selected_datasets)].copy() if selected_datasets else column_meta.iloc[0:0].copy()

  with filter_cols[1]:
    studies = sorted(dataset_meta.get("study_name", pd.Series(dtype=str)).replace("", np.nan).dropna().astype(str).unique().tolist())
    selected_studies = st.multiselect(
      txt("Estudo", "Study"), studies, default=studies,
      key=f"functional_studies_v7_{source}_{annotation_type}_{len(studies)}",
      help=txt("Todas as amostras de cada estudo selecionado são mantidas.", "All samples from every selected study are retained."),
    )
  study_meta = dataset_meta[dataset_meta.get("study_name", pd.Series("", index=dataset_meta.index)).astype(str).isin(selected_studies)].copy() if studies and selected_studies else (dataset_meta.copy() if not studies else dataset_meta.iloc[0:0].copy())

  with filter_cols[2]:
    sample_types = sorted(study_meta.get("sample_type", pd.Series(dtype=str)).replace("", np.nan).dropna().astype(str).unique().tolist())
    selected_types = st.multiselect(
      txt("Tipo de amostra", "Sample type"), sample_types, default=sample_types,
      key=f"functional_sample_types_v7_{source}_{annotation_type}_{len(sample_types)}",
    )
  type_meta = study_meta[study_meta.get("sample_type", pd.Series("", index=study_meta.index)).astype(str).isin(selected_types)].copy() if sample_types and selected_types else (study_meta.copy() if not sample_types else study_meta.iloc[0:0].copy())

  with filter_cols[3]:
    groups = sorted(type_meta.get("environmental_group", pd.Series(dtype=str)).replace("", np.nan).dropna().astype(str).unique().tolist())
    selected_groups = st.multiselect(
      txt("Grupo ambiental", "Environmental group"), groups, default=groups,
      key=f"functional_groups_v7_{source}_{annotation_type}_{len(groups)}",
    )
  filtered_meta = type_meta[type_meta.get("environmental_group", pd.Series("", index=type_meta.index)).astype(str).isin(selected_groups)].copy() if groups and selected_groups else (type_meta.copy() if not groups else type_meta.iloc[0:0].copy())

  selected_cols = [c for c in filtered_meta.get("matrix_column", pd.Series(dtype=str)).astype(str).tolist() if c in matrix.columns]
  selected_cols = list(dict.fromkeys(selected_cols))
  if not selected_cols:
    st.warning(txt("Nenhuma amostra corresponde aos filtros.", "No sample matches the filters."))
    return

  # Study-selection integrity: every matrix column linked to a selected study is retained.
  selected_study_expected = set(type_meta[type_meta.get("environmental_group", pd.Series("", index=type_meta.index)).astype(str).isin(selected_groups)].get("matrix_column", pd.Series(dtype=str)).astype(str)) if groups else set(type_meta.get("matrix_column", pd.Series(dtype=str)).astype(str))
  missing_from_selection = sorted(selected_study_expected.difference(selected_cols))
  if missing_from_selection:
    st.error(txt(
      f"Foram detectadas {len(missing_from_selection)} colunas selecionadas ausentes do heatmap.",
      f"{len(missing_from_selection)} selected columns are missing from the heatmap."
    ))
    return

  query = st.text_input(
    txt("Filtrar funções por identificador, nome ou via", "Filter functions by identifier, name or pathway"),
    key=f"functional_query_v7_{source}_{annotation_type}",
  ).strip()
  filtered_matrix = matrix.copy()
  if query:
    searchable = pd.Series("", index=filtered_matrix.index, dtype="string")
    for col in [id_col, name_col, "Metabolism", "Biologic Role", "KEGG MODULE"]:
      if col in filtered_matrix.columns:
        searchable = searchable.str.cat(filtered_matrix[col].fillna("").astype(str), sep=" | ")
    filtered_matrix = filtered_matrix[searchable.str.contains(query, case=False, regex=False, na=False)].copy()
  if filtered_matrix.empty:
    st.info(txt("Nenhuma função corresponde à busca.", "No function matches the search."))
    return

  controls = st.columns([1.0, 1.0, 1.0, 1.0])
  with controls[0]:
    ranking_metric = st.selectbox(
      txt("Ordenar funções por", "Rank functions by"),
      ["Total count", "Mean count", "Detection fraction", "Variance", "Source table order"],
      key=f"functional_rank_v7_{source}_{annotation_type}",
    )
  with controls[1]:
    show_all_functions = st.checkbox(
      txt("Mostrar todas as funções no heatmap", "Show all functions in heatmap"),
      value=False,
      key=f"functional_all_functions_v7_{source}_{annotation_type}",
      help=txt("Para milhares de funções, o app preserva tamanho de célula e oferece rolagem.", "For thousands of functions, the app preserves cell geometry and provides scrolling."),
    )
  with controls[2]:
    max_rows = max(1, len(filtered_matrix))
    top_n = max_rows if show_all_functions else int(st.number_input(
      txt("Número de funções no heatmap", "Number of functions in heatmap"),
      min_value=1, max_value=max_rows, value=min(150, max_rows), step=10 if max_rows >= 10 else 1,
      key=f"functional_topn_v7_{source}_{annotation_type}_{max_rows}",
    ))
  with controls[3]:
    view_mode = st.radio(
      txt("Escala", "Scale"),
      [txt("Contagem absoluta", "Absolute counts"), txt("Z-score por função", "Row z-score")],
      key=f"functional_scale_v7_{source}_{annotation_type}",
    )
  zscore_rows = view_mode == txt("Z-score por função", "Row z-score")

  m1, m2, m3, m4 = st.columns(4)
  m1.metric(txt("Funções disponíveis", "Available functions"), f"{len(filtered_matrix):,}")
  m2.metric(txt("Funções exibidas", "Displayed functions"), f"{min(top_n, len(filtered_matrix)):,}")
  m3.metric(txt("Amostras/ambientes", "Samples/environments"), f"{len(selected_cols):,}")
  m4.metric(txt("Estudos", "Studies"), f"{filtered_meta.get('study_name', pd.Series(dtype=str)).nunique():,}")

  full_exact = filtered_matrix[[c for c in [id_col, name_col, "Metabolism", "Biologic Role", "KEGG MODULE"] if c in filtered_matrix.columns] + selected_cols].copy()
  metadata_show = [c for c in [
    "source_dataset", "sample_id", "sample.id", "display_label", "sample_type", "environmental_group",
    "ST8_group", "data_layer", "study_name", "matrix_column", "taxon_oid",
    "IMG_JGI_analysis_project_id", "IMG_JGI_taxon_oid", "GOLD Analysis Project ID",
    "NCBI_BioProject_accession", "NCBI_BioSample_accession", "geographic_location", "habitat",
  ] if c in filtered_meta.columns]

  fig, raw_out, z_out = functional_annotation_heatmap(
    filtered_matrix, filtered_meta, id_col, name_col, selected_cols,
    annotation_type, FUNCTIONAL_SOURCE_LABELS.get(source, source),
    top_n=top_n, ranking_metric=ranking_metric, zscore_rows=zscore_rows,
    page_start=0, page_size=None, force_all_y_labels=True,
  )
  raw_out = add_annotation_links(raw_out, id_col, annotation_type)
  z_out = add_annotation_links(z_out, id_col, annotation_type)
  if fig is not None:
    plotted_output = z_out if zscore_rows else raw_out
    heatmap_x = [str(value) for value in list(getattr(fig.data[0], "x", []) or [])]
    if source == "table6" and len(heatmap_x) != 20:
      st.error(txt(
        f"Falha de integridade do eixo X: a Supplementary Table 6 deve mostrar as 20 amostras, mas {len(heatmap_x)} rótulos foram renderizados.",
        f"X-axis integrity failure: Supplementary Table 6 must show all 20 samples, but {len(heatmap_x)} labels were rendered."
      ))
    render_plotly_downloadable(
      fig,
      key=f"functional_heatmap_v7_{source}_{annotation_type}_{zscore_rows}_{len(selected_cols)}_{top_n}",
      basename=f"functional_annotations_{source}_{annotation_type.replace(' ', '_')}_{'row_zscore' if zscore_rows else 'absolute_counts'}",
      audit_input_table=full_exact,
      audit_processed_table=plotted_output,
      audit_output_table=filtered_meta[metadata_show].copy(),
      audit_method="Functions are read directly from Supplementary Table 6 and/or 8, ranked only by the selected visible metric, and displayed as exact absolute counts or row-wise z-scores. The Table 6 view forces all 20 Amazonian lake samples onto the x-axis with fixed cell width and no hidden sample labels.",
      audit_input_source=f"{FUNCTIONAL_SOURCE_LABELS.get(source, source)} — {annotation_type}; exact packaged workbook sheets.",
      audit_script="src/functional_annotations.py:functional_annotation_heatmap; app.py:functional_annotations_tab",
      audit_instructions="Select KO, EC number or PFAM. For Supplementary Table 6, confirm 20/20 sample columns in the metadata and plotted-values tabs.",
    )
    st.caption(txt(
      f"Heatmap: {len(raw_out):,} funções × {len(selected_cols):,} colunas. Todas as amostras dos estudos selecionados estão presentes. As células mantêm proporção nominal e a matriz usa rolagem quando excede a largura da página.",
      f"Heatmap: {len(raw_out):,} functions × {len(selected_cols):,} columns. Every sample from the selected studies is present. Cells retain nominal proportions and the matrix scrolls when it exceeds page width."
    ))

  d1, d2, d3 = st.columns(3)
  with d1:
    csv_button(full_exact, f"functional_annotations_{source}_{annotation_type.replace(' ', '_')}_complete_matrix.csv", txt("Baixar matriz completa", "Download complete matrix"))
  with d2:
    csv_button(raw_out, f"functional_annotations_{source}_{annotation_type.replace(' ', '_')}_displayed_absolute.csv", txt("Baixar linhas exibidas", "Download displayed rows"))
  with d3:
    csv_button(filtered_meta[metadata_show], f"functional_annotations_{source}_{annotation_type.replace(' ', '_')}_sample_metadata.csv", txt("Baixar metadados", "Download metadata"))

  with st.expander(txt("Matriz completa usada após os filtros", "Complete matrix used after filtering"), expanded=False):
    complete_table_note(full_exact, noun_pt="funções", noun_en="functions")
    show_table(full_exact, f"functional_complete_matrix_v7_{source}_{annotation_type}", height=650)
  with st.expander(txt("Metadados de todas as colunas exibidas", "Metadata for every displayed column"), expanded=False):
    show_table(filtered_meta[metadata_show], f"functional_metadata_v7_{source}_{annotation_type}", height=520)


# Canonical article/app display rule for KEGG/KEMET module completeness.
# A row is eligible only when at least one original source cell is Complete.
# Every cell of an eligible row remains visible. The approved three visual
# classes are Complete (green), 1 block missing (blue), and Incomplete (red).
# Original 2 blocks missing values remain preserved in hover/download tables
# and use the red Incomplete visual class; only true missing data are white.
KEGG_MODULE_DISPLAY_STATUSES = ["Complete", "1 block missing", "Incomplete"]
KEGG_MODULE_STATUS_COLORS = {
  "Complete": "#2E7D32",
  "1 block missing": "#1565C0",
  "One block missing": "#1565C0",
  "Incomplete": "#C62828",
  "2 blocks missing": "#C62828",
  "Two blocks missing": "#C62828",
}
KEGG_MODULE_STATUS_ORDER = ["Incomplete", "1 block missing", "Complete"]
KEGG_MODULE_COLORSCALE = [
  [0.000, "#C62828"], [0.332, "#C62828"],
  [0.333, "#1565C0"], [0.665, "#1565C0"],
  [0.666, "#2E7D32"], [1.000, "#2E7D32"],
]

def _clean_kegg_module_axis_label(value):
  text = str(value if value is not None else "").strip()
  if text and text.lower() not in {"nan", "none", "unnamed: 0", "undefined", "null"}:
    return text
  return "Unlabelled KEGG module"

def _wrap_kegg_axis_label(value: object, width: int = 72) -> str:
  text = _clean_kegg_module_axis_label(value).replace(" => ", "→")
  parts = re.findall(r".{1,%d}(?:\s+|$)" % width, text)
  wrapped = "<br>".join(part.strip() for part in parts if part.strip())
  return wrapped or "Unlabelled KEGG module"

def _normalize_kegg_original_status(value: object) -> str:
  if value is None or (isinstance(value, float) and np.isnan(value)):
    return "Missing data"
  status = " ".join(str(value).strip().split()).casefold()
  if not status or status in {"nan", "none", "null", "undefined", "absent", "missing", "no data"}:
    return "Missing data"
  if status == "complete":
    return "Complete"
  if status in {"1 block missing", "one block missing"}:
    return "1 block missing"
  if status in {"2 blocks missing", "two blocks missing"}:
    return "2 blocks missing"
  if status == "incomplete":
    return "Incomplete"
  raise ValueError(f"Unsupported KEGG module status: {value!r}")

def _kegg_visual_status(value: object) -> str:
  status = _normalize_kegg_original_status(value)
  if status == "Complete":
    return "Complete"
  if status == "1 block missing":
    return "1 block missing"
  if status in {"Incomplete", "2 blocks missing"}:
    return "Incomplete"
  return "Missing data"

def _kegg_status_to_numeric_matrix(status_df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
  original = dataframe_map_compat(status_df.copy(), _normalize_kegg_original_status)
  visual = dataframe_map_compat(original, _kegg_visual_status)
  numeric = dataframe_map_compat(visual, lambda v: {"Incomplete": 0.0, "1 block missing": 1.0, "Complete": 2.0}.get(v, np.nan))
  return numeric, visual

def _split_kegg_module_label(label: object) -> tuple[str, str]:
  text = str(label or "").strip()
  m = re.match(r"^(M\d{5})\s*(?:\||:|—|-)?\s*(.*)$", text)
  if m:
    return m.group(1), m.group(2).strip()
  m = re.search(r"(M\d{5})", text)
  if m:
    return m.group(1), text.replace(m.group(1), "").strip(" |:-—")
  return text, ""


def _kegg_official_module_url(module_code: object) -> str:
  code, _ = _split_kegg_module_label(module_code)
  return f"https://www.kegg.jp/module/{code}" if re.match(r"^M\d{5}$", str(code)) else ""


def _rank_kegg_modules_for_display(status: pd.DataFrame) -> list:
  rank_score = {"Complete": 2, "1 block missing": 1, "One block missing": 1, "Incomplete": 0, "2 blocks missing": 0}
  def _row_score(row):
    vals = [rank_score.get(_normalize_kegg_original_status(v), 0) for v in row]
    if not vals:
      return 0
    return float(np.nanmean(vals)) + float(np.nanstd(vals))*0.05 + float(sum(v > 0 for v in vals))/max(len(vals), 1)
  scores = status.apply(_row_score, axis=1)
  return list(scores.sort_values(ascending=False).index)


def _prepare_kegg_status_frame(raw: pd.DataFrame) -> tuple[pd.DataFrame, str]:
  if raw is None or raw.empty:
    return pd.DataFrame(), "KEGG module"

  def _is_status_column(series: pd.Series) -> bool:
    values = []
    for value in series.tolist():
      if value is None or (isinstance(value, float) and np.isnan(value)):
        continue
      text = str(value).strip()
      if not text or text.casefold() in {"nan", "none", "null", "undefined"}:
        continue
      values.append(text)
      if len(values) >= 200:
        break
    if not values:
      return False
    for value in values:
      try:
        _normalize_kegg_original_status(value)
      except Exception:
        return False
    return True

  frame = raw.copy()
  if {"__module_id__", "Module_name"}.issubset(frame.columns):
    module_ids = frame["__module_id__"].astype(str).map(_clean_kegg_module_axis_label)
    module_names = frame["Module_name"].astype(str).map(_clean_kegg_module_axis_label)
    labels = [f"{mid} | {name}" if name and name != "Unlabelled KEGG module" else mid for mid, name in zip(module_ids, module_names)]
    index_name = "__module_id__"
  else:
    first_col = str(frame.columns[0])
    labels = [_clean_kegg_module_axis_label(v) for v in frame.iloc[:, 0].astype(str)]
    index_name = first_col

  status_cols = [col for col in frame.columns if _is_status_column(frame[col])]
  if not status_cols:
    return pd.DataFrame(), "KEGG module"
  frame = frame.loc[:, status_cols].copy()
  frame.index = pd.Index(labels, name=index_name)
  frame = frame[~pd.Index(frame.index).duplicated(keep="first")]
  frame = dataframe_map_compat(frame, _normalize_kegg_original_status)
  return frame, index_name


def _kegg_scope_rows(article_status: pd.DataFrame, full_status: pd.DataFrame, scope: str) -> pd.DataFrame:
  """Select the requested module universe without changing source statuses."""
  if scope == "article":
    return article_status.copy()
  source = full_status.copy()
  if scope == "complete":
    return source.loc[source.eq("Complete").any(axis=1)].copy()
  if scope == "one_missing":
    return source.loc[source.eq("1 block missing").any(axis=1)].copy()
  if scope == "incomplete":
    return source.loc[source.isin(["Incomplete", "2 blocks missing"]).any(axis=1)].copy()
  return source


def _display_kegg_completeness_panel(fig_path: Path, caption: str, status_csv: Path, key_prefix: str, full_status_csv: Path | None = None) -> None:
  """Show the approved static figure and a stateful full-matrix explorer."""
  _display_static_publication_image(fig_path, fig_path.name, caption, key_prefix=key_prefix)
  if not status_csv.exists():
    st.caption(txt("Matriz interativa não encontrada.", "Interactive matrix not found."))
    return
  try:
    article_raw = pd.read_csv(status_csv, keep_default_na=False)
    full_raw = pd.read_csv(full_status_csv, keep_default_na=False) if full_status_csv and full_status_csv.exists() else article_raw.copy()
    article_status, first_col = _prepare_kegg_status_frame(article_raw)
    full_status, _ = _prepare_kegg_status_frame(full_raw)
    if article_status.empty or full_status.empty:
      st.info(txt("Matriz de status KEGG vazia.", "Empty KEGG status matrix."))
      return

    st.markdown("##### " + txt("Explorador interativo da matriz completa", "Interactive complete-matrix explorer"))
    scope_labels = {
      "article": txt("1. Selecionados para o artigo", "1. Selected for the article"),
      "complete": txt("2. Completos — todos", "2. Complete — all"),
      "one_missing": txt("3. Um bloco ausente", "3. One block missing"),
      "incomplete": txt("4. Incompletos", "4. Incomplete"),
      "all": txt("5. Todos os módulos da matriz-fonte", "5. All modules in the source matrix"),
    }
    c1, c2 = st.columns([0.48, 0.52])
    with c1:
      scope = st.radio(
        txt("Conjunto de módulos", "Module set"),
        list(scope_labels), format_func=lambda value: scope_labels[value],
        key=f"{key_prefix}_module_scope_v8",
      )
    scope_status = _kegg_scope_rows(article_status, full_status, scope)
    ranked = _rank_kegg_modules_for_display(scope_status)
    available = len(ranked)
    with c2:
      show_all = st.checkbox(
        txt(f"Mostrar todos os {available} módulos deste conjunto", f"Show all {available} modules in this set"),
        value=False,
        key=f"{key_prefix}_show_all_modules_v8_{scope}",
      )
      module_count = available if show_all else int(st.number_input(
        txt("Número de módulos exibidos", "Number of displayed modules"),
        min_value=1, max_value=max(1, available), value=min(40, max(1, available)),
        step=1, key=f"{key_prefix}_module_count_v8_{scope}_{available}",
      ))

    if scope == "article":
      st.info(txt(
        "Este conjunto reproduz as linhas destacadas na figura estática do artigo. Elas foram priorizadas por relevância para os ciclos biogeoquímicos discutidos e pela presença de evidência de completude na matriz temática; os estados de todas as células dessas linhas permanecem inalterados.",
        "This set reproduces the rows highlighted in the static article figure. They were prioritised for relevance to the discussed biogeochemical cycles and evidence of completeness in the thematic matrix; every cell status in those rows remains unchanged."
      ))
    else:
      st.caption(txt(
        "Os conjuntos 2–5 são calculados diretamente da matriz-fonte completa e não alteram os valores da figura estática.",
        "Sets 2–5 are selected directly from the complete source matrix and do not alter the static-figure values."
      ))

    selected_modules = ranked[:module_count]
    all_samples = list(scope_status.columns)
    c3, c4 = st.columns([0.55, 0.45])
    with c3:
      sample_filter = st.multiselect(
        txt("Amostras/MAGs", "Samples/MAGs"), all_samples, default=all_samples,
        key=f"{key_prefix}_samples_v8_{scope}",
      )
    with c4:
      visible_states = st.multiselect(
        txt("Estados visíveis", "Visible states"),
        ["Complete", "1 block missing", "Incomplete", "2 blocks missing", "Missing data"],
        default=["Complete", "1 block missing", "Incomplete", "2 blocks missing"],
        key=f"{key_prefix}_visible_states_v8_{scope}",
      )
    if not sample_filter:
      sample_filter = all_samples

    view_original = scope_status.loc[selected_modules, sample_filter].copy()
    numeric, view_visual = _kegg_status_to_numeric_matrix(view_original)
    if visible_states:
      visible_mask = view_original.isin(visible_states)
      numeric = numeric.where(visible_mask)
    if view_original.empty:
      st.info(txt("Nenhum módulo corresponde aos filtros.", "No module matches the filters."))
      return

    x_labels = list(view_original.columns)
    y_labels_full = list(view_original.index)
    y_labels = [_wrap_kegg_axis_label(label, width=68) for label in y_labels_full]
    hover = []
    for row_name, row in view_original.iterrows():
      code, desc = _split_kegg_module_label(row_name)
      url = _kegg_official_module_url(code)
      hover.append([
        "<br>".join([
          f"<b>KEGG module:</b> {code}",
          f"<b>Description:</b> {desc or row_name}",
          f"<b>Sample/MAG:</b> {col}",
          f"<b>Original status:</b> {row[col]}",
          f"<b>Visual category:</b> {view_visual.at[row_name, col]}",
          f"<b>Official KEGG:</b> {url}",
        ]) for col in view_original.columns
      ])
    n_rows, n_cols = view_original.shape
    cell_w = 44 if n_cols <= 24 else 40 if n_cols <= 40 else 34
    cell_h = 34 if n_rows <= 180 else 30
    fig = go.Figure(go.Heatmap(
      z=numeric.to_numpy(float), x=x_labels, y=y_labels,
      customdata=np.asarray(hover, dtype=object),
      hovertemplate="%{customdata}<extra></extra>",
      zmin=0, zmax=2, colorscale=KEGG_MODULE_COLORSCALE,
      xgap=0.45, ygap=0.45,
      colorbar=dict(
        title=dict(text="KEGG module status", font=dict(size=14)),
        tickmode="array", tickvals=[0, 1, 2],
        ticktext=["Incomplete", "1 block missing", "Complete"],
        thickness=18, len=0.78, tickfont=dict(size=12),
      ),
    ))
    fig.update_layout(
      width=max(1250, min(16000, 650 + cell_w * n_cols)),
      height=max(720, min(26000, 300 + cell_h * n_rows)),
      margin=dict(l=760, r=180, t=70, b=330),
      font=dict(size=13, color="#111827"),
      meta={
        "preserve_cell_geometry": True,
        "force_all_y_ticks": True,
        "all_y_labels_visible": True,
        "cell_width_px": cell_w,
        "cell_height_px": cell_h,
      },
    )
    fig.update_xaxes(tickangle=-55, tickfont=dict(size=11), automargin=True, title="Sample / MAG")
    fig.update_yaxes(tickfont=dict(size=11), automargin=True, tickmode="array", tickvals=y_labels, ticktext=y_labels, title="KEGG module")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(txt("Módulos na matriz-fonte", "Modules in source matrix"), len(full_status))
    m2.metric(txt("Módulos no conjunto", "Modules in selected set"), available)
    m3.metric(txt("Módulos exibidos", "Displayed modules"), len(view_original))
    m4.metric(txt("Amostras/MAGs", "Samples/MAGs"), len(sample_filter))
    render_plotly_downloadable(
      fig,
      key=f"{key_prefix}_interactive_v8_{scope}_{module_count}_{len(sample_filter)}",
      basename=f"{key_prefix}_{scope}_{module_count}_modules",
    )
    table_out = view_original.reset_index().rename(columns={view_original.index.name or first_col: "KEGG module"})
    show_table(table_out, f"{key_prefix}_status_matrix_v8_{scope}_{module_count}", height=400)
    d1, d2 = st.columns(2)
    with d1:
      csv_button(table_out, f"{key_prefix}_{scope}_{module_count}_displayed_statuses.csv", txt("Baixar matriz exibida", "Download displayed matrix"), context=key_prefix)
    with d2:
      csv_button(full_raw, f"{key_prefix}_complete_source_matrix.csv", txt("Baixar matriz-fonte completa", "Download complete source matrix"), context=f"{key_prefix}_source")
  except Exception as exc:
    st.warning(txt(f"A versão interativa não pôde ser gerada: {exc}", f"Interactive version could not be generated: {exc}"))

def kegg_modules_tab():
  ensure_kegg_module_directories()
  st.subheader(txt("Módulos KEGG — MAGs e metagenomas", "KEGG Modules — MAGs & Metagenomes"))
  st.markdown(txt(
    "Este módulo integra os relatórios `reportKMC_*.tsv` produzidos pelo KEMET/KEGG e, quando disponível para MAGs, a tabela consolidada `Bin-genomas_all_kegg.xlsx`. O app classifica cada módulo como completo, com um ou dois blocos ausentes, incompleto ou ausente; gera matrizes automaticamente; permite baixar FASTAs; e mostra um mapa local dos KOs detectados e ausentes para cada módulo.",
    "This module integrates KEMET/KEGG `reportKMC_*.tsv` reports and, for MAGs when available, the consolidated `Bin-genomas_all_kegg.xlsx` table. The app classifies each module as complete, one or two blocks missing, incomplete or absent; automatically builds matrices; enables FASTA downloads; and displays a local map of detected and missing KOs for each module."
  ))
  st.info(txt(
    "A figura local de componentes do módulo não substitui o diagrama oficial do KEGG. Ela colore os KOs detectados em verde e os KOs ausentes/alternativos em vermelho, mantendo um link para a entrada oficial do módulo no KEGG.",
    "The local module-component figure does not replace the official KEGG diagram. It colors detected KOs green and missing/alternative KOs red while retaining a link to the official KEGG module entry."
  ))

  st.markdown("### Direct visualization of KEGG module completeness")
  st.caption(txt(
    "Esta seção mostra diretamente as figuras finais de completude de módulos KEGG. Os arquivos exibidos são os mesmos sincronizados com o artigo, as figuras suplementares e a seção Final figures & scripts.",
    "This section directly shows the final KEGG module completeness figures. The displayed files are the same files synchronized with the manuscript, supplementary figures and Final figures & scripts section."
  ))

  figure_dir = BASE_DIR / "outputs" / "app_supplementary_figures"
  kegg_data_dir = BASE_DIR / "data" / "final_kegg_st8_update"
  kegg_derived_dir = BASE_DIR / "data" / "final_publication_derived"
  kegg_figures = [
    (
      "SupplementaryFigure37_MAG_KEGG_module_completeness_heatmap_species_MAGnumber_KEMET_style_3state.png",
      txt("Completude dos módulos KEGG nos MAGs.", "KEGG module completeness in MAGs."),
      BASE_DIR / "data" / "module_figure_inputs" / "SupplementaryFigure37_MAG_KEGG_module_completeness_heatmap_species_MAGnumber_KEMET_style_3state_thematic_status.csv",
      kegg_data_dir / "MAG_KEGG_module_completeness_STATUS_species_MAGnumber_3state.csv",
      "kegg_mags",
    ),
    (
      "SupplementaryFigure38_metagenome_KEGG_module_completeness_heatmap.png",
      txt("Completude dos módulos KEGG nos metagenomas das lagoas.", "KEGG module completeness in lagoon metagenomes."),
      kegg_derived_dir / "SupplementaryFigure38_metagenome_KEGG_module_completeness_heatmap_thematic_app_status.csv",
      kegg_data_dir / "KEMET_lagoon_all_metagenomes_module_completeness_STATUS_3state.csv",
      "kegg_lagoon_metagenomes",
    ),
    (
      "SupplementaryFigure40_ST8_external_iron_rich_module_completeness_by_environmental_group.png",
      txt("S40 — versão final por environmental group: todos os mesmos registros e estados da matriz-fonte, com alteração exclusiva da ordem das colunas para manter cada grupo lado a lado.", "S40 — final environmental-group version: all records and statuses from the same source matrix, with only the column order changed to keep each group together."),
      kegg_derived_dir / "SupplementaryFigure40_ST8_external_iron_rich_module_completeness_by_environmental_group_status.csv",
      kegg_data_dir / "ST8_external_iron_rich_module_completeness_STATUS_3state_from_KO.csv",
      "kegg_external_iron_rich_environmental_group",
    ),
    (
      "SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_KEMET_style_3state_heatmap.png",
      txt("S67 — ordem original: completude combinada dos módulos KEGG nas lagoas e nos metagenomas externos ricos em ferro.", "S67 — original order: combined KEGG module completeness in lagoon and external iron-rich metagenomes."),
      kegg_derived_dir / "SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_KEMET_style_3state_heatmap_status.csv",
      kegg_data_dir / "Combined_lagoon_plus_external_iron_rich_module_completeness_STATUS_3state.csv",
      "kegg_combined_lagoon_external_original",
    ),
    (
      "SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_by_environmental_group.png",
      txt("S67 — por environmental group: as mesmas amostras, registros, módulos e estados da versão original, somente com as colunas do mesmo grupo ambiental lado a lado.", "S67 — by environmental group: the same samples, records, modules and statuses as the original version, with only columns from the same environmental group placed side by side."),
      kegg_derived_dir / "SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_by_environmental_group_status.csv",
      kegg_data_dir / "Combined_lagoon_plus_external_iron_rich_module_completeness_STATUS_3state.csv",
      "kegg_combined_lagoon_external_environmental_group",
    ),
  ]
  for fig_name, fig_caption, status_csv, full_status_csv, panel_key in kegg_figures:
    _display_kegg_completeness_panel(figure_dir / fig_name, fig_caption, status_csv, panel_key, full_status_csv=full_status_csv)

  comparison_tsv = BASE_DIR / "validation" / "environmental_group_heatmap_comparison.tsv"
  comparison_md = BASE_DIR / "validation" / "environmental_group_heatmap_comparison.md"
  if comparison_tsv.exists() or comparison_md.exists():
    with st.expander(txt(
      "Validação programática das versões originais e por environmental group",
      "Programmatic validation of original and environmental-group versions",
    ), expanded=False):
      st.markdown(txt(
        "As matrizes por grupo ambiental de S40 e S67 foram restauradas à ordem de referência da mesma tabela-fonte e comparadas célula a célula. A S40 é exibida somente na versão final por environmental group; sua ordem original permanece apenas como referência de auditoria. A S67 mantém as duas versões.",
        "The S40 and S67 environmental-group matrices were restored to the reference order of the same source table and compared cell by cell. S40 is displayed only in its final environmental-group version; its original order remains audit-only. S67 retains both layouts.",
      ))
      if comparison_tsv.exists():
        st.download_button(
          txt("Baixar comparação detalhada TSV", "Download detailed TSV comparison"),
          data=comparison_tsv.read_bytes(),
          file_name=comparison_tsv.name,
          mime="text/tab-separated-values",
          key="download_environmental_group_heatmap_comparison_tsv",
          width="stretch",
        )
      if comparison_md.exists():
        st.download_button(
          txt("Baixar relatório de equivalência MD", "Download equivalence report MD"),
          data=comparison_md.read_bytes(),
          file_name=comparison_md.name,
          mime="text/markdown",
          key="download_environmental_group_heatmap_comparison_md",
          width="stretch",
        )

  record_key_path = BASE_DIR / "tables" / "Supplementary_Table_15_external_record_key.csv"
  if record_key_path.exists():
    try:
      record_key = pd.read_csv(record_key_path).fillna("Not reported")
      with st.expander(txt(
        "Chave dos registros externos mostrados nas Figuras S40 e S67",
        "Record key for external records shown in Figures S40 and S67",
      ), expanded=False):
        show_table(record_key, "external_iron_rich_record_key", height=420)
        csv_button(
          record_key,
          "Supplementary_Table_15_external_record_key.csv",
          txt("Baixar chave dos registros externos", "Download external-record key"),
          context="kegg_external_record_key",
        )
    except Exception as exc:
      st.caption(f"External record key could not be read: {exc}")

  render_section_script_inventory("KEGG module completeness", ["kegg", "kemet", "module completeness", "final_kegg_st8", "reportKMC"], "kegg_module_section")

  manifest_path = BASE_DIR / "data" / "final_figure_script_manifest.csv"
  if manifest_path.exists():
    try:
      manifest = pd.read_csv(manifest_path).fillna("")
      wanted = {Path(item[0]).stem for item in kegg_figures}
      rows = manifest[manifest.astype(str).apply(lambda row: any(stem in " ".join(row.tolist()) for stem in wanted), axis=1)]
      if not rows.empty:
        st.markdown("### " + txt("Scripts e dados de origem destas figuras", "Scripts and source data for these figures"))
        show_table(rows, "kegg_direct_visualization_manifest", height=260)
        csv_button(rows, "kegg_direct_visualization_manifest.csv", txt("Baixar manifesto KEGG", "Download KEGG manifest"))
    except Exception as exc:
      st.caption(f"Figure manifest could not be read: {exc}")

def study_references_tab():
  st.subheader(txt("Referências bibliográficas e links dos estudos ST8", "ST8 study references and links"))
  st.markdown(txt(
    "Esta aba reúne referências, links oficiais de BioProject/GOLD e resumos IMG/JGI dos estudos externos usados na Supplementary Table 8. Como a coluna PubMed ID da planilha ST8 está vazia para esses metagenomas, o app separa claramente referências confirmadas por metadados, links oficiais de dados e referências candidatas que ainda precisam de confirmação manual antes da submissão do artigo.",
    "This tab compiles references, official BioProject/GOLD links and IMG/JGI summaries for the external studies used in Supplementary Table 8. Because the PubMed ID column in the ST8 metadata is empty for these metagenomes, the app clearly separates metadata-confirmed data links, official data-source links and candidate bibliographic references that require manual confirmation before manuscript submission."
  ))
  refs = load_st8_study_references_table()
  if not refs.empty:
    try:
      sample_meta = st8_column_metadata()
      if not sample_meta.empty:
        study_col = "Study Name" if "Study Name" in sample_meta.columns else "study_name"
        sample_type_summary = sample_meta.groupby(study_col, as_index=False).agg(
          sample_types=("sample_type", lambda values: "; ".join(sorted(set(map(str, values))))),
          sample_type_counts=("sample_type", lambda values: "; ".join(f"{name}: {count}" for name, count in pd.Series(list(map(str, values))).value_counts().sort_index().items())),
          n_metadata_records=("matrix_column", "nunique"),
        ).rename(columns={study_col: "study_name"})
        refs = refs.merge(sample_type_summary, on="study_name", how="left")
    except Exception:
      pass
  if refs.empty:
    st.warning(txt(
      "A tabela data/st8_study_references.csv não foi encontrada. Regenere o app com a Supplementary Table 8 atualizada.",
      "The table data/st8_study_references.csv was not found. Regenerate the app with the updated Supplementary Table 8."
    ))
    return

  total_studies = len(refs)
  n_records_series = _safe_refs_series(refs, "n_metagenomes_in_ST8", 0)
  if "n_metagenomes_in_ST8" not in refs.columns and "n_records" in refs.columns:
    n_records_series = _safe_refs_series(refs, "n_records", 0)
  total_metagenomes = int(pd.to_numeric(n_records_series, errors="coerce").fillna(0).sum())
  bioproject_series = _safe_refs_series(refs, "ncbi_bioprojects", "")
  if "ncbi_bioprojects" not in refs.columns and "NCBI_BioProject_accessions" in refs.columns:
    bioproject_series = _safe_refs_series(refs, "NCBI_BioProject_accessions", "")
  doi_series = _safe_refs_series(refs, "doi_or_primary_article_url", "")
  if "doi_or_primary_article_url" not in refs.columns and "bibliographic_reference_or_candidate" in refs.columns:
    doi_series = _safe_refs_series(refs, "bibliographic_reference_or_candidate", "")
  with_bioproject = int(bioproject_series.astype(str).str.strip().ne("").sum())
  with_doi = int(doi_series.astype(str).str.strip().ne("").sum())
  c1, c2, c3, c4 = st.columns(4)
  c1.metric(txt("Estudos ST8", "ST8 studies"), total_studies)
  c2.metric(txt("Metagenomas externos", "External metagenomes"), total_metagenomes)
  c3.metric(txt("Com BioProject", "With BioProject"), with_bioproject)
  c4.metric(txt("Com DOI/artigo candidato", "With DOI/candidate paper"), with_doi)

  search = st.text_input(txt("Filtrar por estudo, habitat, local, BioProject ou referência", "Filter by study, habitat, location, BioProject or reference"), "", key="st8_study_refs_search")
  status_values = sorted([x for x in _safe_refs_series(refs, "bibliographic_status", "").dropna().astype(str).unique() if x])
  selected_status = st.multiselect(txt("Status bibliográfico", "Bibliographic status"), status_values, default=status_values, key="st8_study_refs_status")
  view = refs.copy()
  if selected_status:
    view = view[view["bibliographic_status"].isin(selected_status)]
  if search.strip():
    pattern = search.strip().casefold()
    mask = view.apply(lambda row: pattern in " ".join(row.astype(str).tolist()).casefold(), axis=1)
    view = view[mask]

  st.markdown("### " + txt("Estudos e referências", "Studies and references"))
  st.caption(txt(
    "Os botões abaixo aparecem somente quando existe um metadado concreto associado ao link, como BioProject, GOLD Study ID, DOI ou PubMed ID. IMG/JGI aparece apenas como metadado textual no resumo, sem botão/link. Links de busca genérica não são mostrados como referência do estudo.",
    "The buttons below are shown only when a concrete metadata field supports the link, such as BioProject, GOLD Study ID, DOI or PubMed ID. IMG/JGI is shown only as text metadata in the summary, with no button/link. Generic search links are not shown as study references."
  ))
  for _, row in view.iterrows():
    study = str(row.get("study_name", "Unknown study"))
    n = str(row.get("n_metagenomes_in_ST8", row.get("n_records", "")))
    with st.expander(f"{study} — {n} metagenome(s)", expanded=False):
      st.markdown("**" + txt("Resumo", "Summary") + "**")
      st.write(str(row.get("summary", "")))
      img_summary_bits = []
      if _valid_metadata_value(row.get("taxon_oids", row.get("taxon_oid", ""))):
        img_summary_bits.append("IMG/JGI taxon_oid(s): " + str(row.get("taxon_oids", row.get("taxon_oid", ""))))
      if _valid_metadata_value(row.get("IMG Genome ID", row.get("IMG Genome IDs", ""))):
        img_summary_bits.append("IMG Genome ID(s): " + str(row.get("IMG Genome ID", row.get("IMG Genome IDs", ""))))
      if img_summary_bits:
        st.caption(" | ".join(img_summary_bits))
      st.markdown("**" + txt("Referência bibliográfica / candidata", "Bibliographic / candidate reference") + "**")
      st.write(str(row.get("bibliographic_reference_or_candidate", row.get("study_name", ""))))
      st.markdown("**" + txt("Status", "Status") + "**")
      st.info(str(row.get("bibliographic_status", "")))
      links = _reference_link_candidates(row)
      if links:
        link_cols = st.columns(min(4, len(links)))
        for col, (label, url, meta_value) in zip(link_cols, links):
          col.link_button(label, url, width="stretch")
          col.caption(str(meta_value)[:90])
      else:
        st.caption(txt(
          "Nenhum hiperlink bibliográfico/oficial foi mostrado porque esta linha não contém DOI, PubMed ID, BioProject ou GOLD Study ID suficiente para abrir uma fonte específica. IMG/JGI permanece apenas no resumo textual.",
          "No bibliographic/official hyperlink is shown because this row does not contain enough DOI, PubMed ID, BioProject or GOLD Study ID metadata to open a specific source. IMG/JGI remains only in the text summary."
        ))
      detail_cols = [
        "sample_ids_created_this_study", "matrix_columns_in_ST8_all_KO_biomarkers", "matrix_columns_in_ST8_selected_sediments",
        "matrix_columns_in_ST8_iron_KO_markers", "matrix_columns_in_ST8_iron_selected", "gold_study_ids", "ncbi_bioprojects",
        "sra_runs", "habitats", "sample_types", "sample_type_counts", "locations", "countries", "phyla_from_ST8_metadata", "notes"
      ]
      detail = pd.DataFrame([{"Field": c, "Value": str(row.get(c, ""))} for c in detail_cols if str(row.get(c, "")).strip()])
      show_table(detail, "st8_study_reference_detail_" + re.sub(r"[^A-Za-z0-9_]+", "_", study)[:40], height=360)

  st.markdown("### " + txt("Tabela completa para auditoria", "Complete audit table"))
  preferred = [
    "study_name", "n_metagenomes_in_ST8", "bibliographic_reference_or_candidate", "bibliographic_status",
    "doi_or_primary_article_url", "ncbi_bioprojects", "gold_study_ids", "habitats", "sample_types", "sample_type_counts", "locations",
    "sample_ids_created_this_study", "matrix_columns_in_ST8_all_KO_biomarkers", "matrix_columns_in_ST8_selected_sediments",
    "matrix_columns_in_ST8_iron_KO_markers", "matrix_columns_in_ST8_iron_selected", "summary"
  ]
  preferred = [c for c in preferred if c in refs.columns]
  show_table(view[preferred], "st8_study_references_full_table", height=520)
  csv_button(view, "st8_study_references_with_links.csv", txt("Baixar referências ST8 em CSV", "Download ST8 references as CSV"))

def references_methods_tab():
  st.subheader(txt("Materiais, métodos e referências", "Materials, methods and references"))
  st.markdown(txt(
    "Esta seção documenta as fontes de dados, planilhas, scripts e critérios usados para montar o banco e as figuras. O objetivo é manter o painel auditável e reprodutível.",
    "This section documents the data sources, spreadsheets, scripts and criteria used to assemble the database and figures. The goal is to keep the panel auditable and reproducible."
  ))
  methods_docs = sorted({p for folder in [BASE_DIR, BASE_DIR / "docs", BASE_DIR / "outputs" / "nature_isme_figures"] if folder.exists() for p in folder.rglob("*.md") if p.is_file()})
  if methods_docs:
    methods_index = pd.DataFrame({
      "document": [str(p.relative_to(BASE_DIR)) for p in methods_docs],
      "bytes": [p.stat().st_size for p in methods_docs],
      "sha256": [hashlib.sha256(p.read_bytes()).hexdigest() for p in methods_docs],
    })
    st.markdown("### " + txt("Documentação metodológica completa", "Complete methodological documentation"))
    st.caption(txt(
      "Todos os documentos metodológicos incluídos no pacote são listados abaixo; nenhum arquivo é ocultado ou resumido fora do inventário.",
      "All methodological documents included in the package are listed below; no file is hidden or omitted from the inventory."
    ))
    show_table(methods_index, "complete_methods_document_index", height=320)
    csv_button(methods_index, "complete_methods_document_index.csv", txt("Baixar índice metodológico", "Download methods index"))
    final_methods_doc = BASE_DIR / "docs" / "code" / "FINAL_APP_VERSION_1_VISUAL_AND_STATISTICAL_METHODS.md"
    if final_methods_doc.exists():
      download_text_file_button(final_methods_doc, txt("Baixar métodos visuais e estatísticos completos", "Download complete visual and statistical methods"))

  st.markdown(f"**{txt('Título', 'Title')}:** {article_field('title', DEFAULT_ARTICLE_TITLE)}")
  st.markdown(f"**{txt('Autores', 'Authors')}:** {normalize_authors_string(article_field('authors', DEFAULT_ARTICLE_AUTHORS))}")
  st.markdown(f"**{txt('Afiliação', 'Affiliation')}:** {article_field('affiliation', DEFAULT_ARTICLE_AFFILIATION)}")
  st.markdown(f"**{txt('Correspondência', 'Correspondence')}:** {article_field('correspondence', DEFAULT_ARTICLE_CORRESPONDENCE)}")
  st.markdown("### " + txt("Resumo do artigo", "Article abstract"))
  st.info(article_field("abstract", DEFAULT_ARTICLE_ABSTRACT))
  st.markdown("### " + txt("Tabelas suplementares visíveis e baixáveis", "Visible and downloadable supplementary tables"))
  table_rows = []
  for key, fname in TABLE_FILES.items():
    fpath = BASE_DIR / "tables" / fname
    if fpath.exists():
      table_rows.append({"key": key, "file": fname, "relative_path": str(fpath.relative_to(BASE_DIR)), "size_MB": round(fpath.stat().st_size/1024/1024, 3), "sheets": "; ".join(excel_sheet_names(key))})
  extra_files = sorted([p for p in (BASE_DIR / "tables").glob("*.csv")]) if (BASE_DIR / "tables").exists() else []
  table_index = pd.DataFrame(table_rows)
  show_table(table_index, "complete_supplementary_table_browser_public", height=440)
  csv_button(table_index, "complete_supplementary_table_index.csv", txt("Baixar índice das tabelas", "Download table index"))
  selected_table_key = st.selectbox(txt("Visualizar tabela suplementar", "View supplementary table"), table_index["key"].tolist() if not table_index.empty else [], key="public_supplementary_table_selector")
  if selected_table_key:
    sheet_names = excel_sheet_names(selected_table_key)
    selected_sheet_name = st.selectbox(txt("Aba", "Sheet"), sheet_names, key="public_supplementary_sheet_selector")
    selected_df = load_sheet(selected_table_key, selected_sheet_name)
    st.caption(f"{selected_table_key} / {selected_sheet_name}: {selected_df.shape[0]:,} rows × {selected_df.shape[1]:,} columns")
    show_table(selected_df, f"public_table_{selected_table_key}_{selected_sheet_name}", height=560)
    csv_button(selected_df, f"{selected_table_key}_{selected_sheet_name}.csv".replace("/", "_"), txt("Baixar aba visível", "Download visible sheet"))
    fpath = BASE_DIR / "tables" / TABLE_FILES[selected_table_key]
    if fpath.exists():
      st.download_button(txt("Baixar workbook original", "Download original workbook"), data=fpath.read_bytes(), file_name=fpath.name, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key=f"download_public_workbook_{selected_table_key}", width="stretch")
  if extra_files:
    csv_index = pd.DataFrame({"file": [p.name for p in extra_files], "relative_path": [str(p.relative_to(BASE_DIR)) for p in extra_files], "size_kB": [round(p.stat().st_size/1024, 2) for p in extra_files]})
    with st.expander(txt("Arquivos CSV adicionais", "Additional CSV files"), expanded=False):
      show_table(csv_index, "public_extra_csv_index", height=260)
      for p in extra_files:
        st.download_button(f"Download {p.name}", data=p.read_bytes(), file_name=p.name, mime="text/csv", key=f"download_extra_csv_{p.name}")

  st.markdown("### " + txt("Fontes das tabelas", "Table sources"))
  sources = pd.DataFrame([
    {"Dataset": "Taxonomic profiles", "Spreadsheet": "Supplementary Table 1", "Sheets": "Domain-Kaiju; Domain-Environment-Featues; Phylum-Bact-environment-feature; Family-Bact-environment-feature; Genus-Bact-environment-feature; Species-Bact-environment-featur", "Use": "Taxonomic profiles, sample coordinates, collection dates"},
    {"Dataset": "Differential abundance", "Spreadsheet": "Supplementary Table 2 and 5", "Sheets": "Figure 7 / top differential abundance; T-test and Kruskal sheets", "Use": "Taxon and KO/pathway differential-abundance visualisation"},
    {"Dataset": "KO Biogeochemical Cycles Biomarkers", "Spreadsheet": "Supplementary Table 4", "Sheets": "KO-marker-biogeochemical-cyc; ResBiomarker-Biochemical-cycles", "Use": "Biogeochemical-cycle marker catalogue and article results"},
    {"Dataset": "MAGs and genome annotation", "Spreadsheet": "Supplementary Table 7 and BV-BRC Annotation/MAG folders", "Sheets": "bins-identificados; bin.classification; GTDB-Tk; rRNA machinery >=70 CI", "Use": "MAG browsing, FASTA/GBK download and taxonomy links"},
    {"Dataset": "KEGG modules — MAGs and metagenomes", "Spreadsheet": "data/kegg_modules/tables/Bin-genomas_all_kegg.xlsx and reportKMC_*.tsv", "Sheets": "Consolidated MAG status table or automatic aggregation of KEMET reports", "Use": "Complete/incomplete/absent KEGG module matrices, KO component maps and downloadable FASTA/report inventories"},
    {"Dataset": "antiSMASH BGC organization", "Spreadsheet": "Complete antiSMASH output directories", "Sheets": "index.html, regions.js, CSS/JS, GBK files", "Use": "Embedded antiSMASH report and complete-run ZIP in MAGs & genomes"},
    {"Dataset": "IMG/JGI functional annotations", "Spreadsheet": "Supplementary Tables 6 and 8", "Sheets": "Detailed-Statistics2-by-Genome; KO; EC-numbers; PFAM; metadata; ko; EC-number; pfam", "Use": "Absolute-count and row-z-score heatmaps for KO, EC/enzyme and PFAM annotations, linked to sample ID, taxon_oid and GOLD Analysis Project ID"},
    {"Dataset": "Amazonian Lateritic Lakes vs Other Iron-Rich Environments", "Spreadsheet": "Supplementary Table 8 + data/st8_study_references.csv", "Sheets": "Iron-rich-environment; Phylum-taxonomy; Res-KO-Biomarkers-C-N-S; ST8 — all KO biomarkers; ST8 — selected sediments; ST8- Iron metabolism KO -marker; ST8-Iron metabolism - selected", "Use": "Supplementary Table 8-derived heatmaps, metadata map, linked IMG/M environmental metadata, Phylum-taxonomy summaries, KO contrast summaries, iron-metabolism z-score profiles and study-level reference links"},
  ])
  show_table(sources, "methods_sources_table", height=360)
  st.markdown("### " + txt("Critérios analíticos", "Analytical criteria"))
  st.markdown(txt(
    """
- KO, EC/enzyme and PFAM heatmaps use the exact count matrices from Supplementary Tables 6 and 8.
- Functional-annotation columns are linked to sample ID, taxon_oid and GOLD Analysis Project ID whenever available.
- KO, EC/enzyme and PFAM result tables include annotation-specific hyperlinks to KEGG or InterPro/PFAM.
- Heatmap width and height use the same nominal pixel size per matrix row and column, and the renderer preserves the chart geometry instead of stretching it to the browser width.
- Z-score heatmaps are row-scaled per function: z = (count − row mean) / row standard deviation.
- KEMET reports are parsed from reportKMC_*.tsv; completed-block fractions are converted to module completeness percentages, and the consolidated MAG workbook is used as the priority source when present.
- Final S40 is generated only in environmental-group order; S67 retains original and environmental-group layouts. `scripts/figures/generate_environmental_group_heatmaps.py` uses the same immutable source matrices, while `scripts/validation/compare_environmental_group_heatmaps.py` restores the reference order and verifies every cell, dimension, identifier and status count. Grouped layouts change only column order. Other static KEGG-module figures retain their documented canonical generators; Top-N options are exploratory filters only and never alter the source matrix.
- antiSMASH visualization uses the unmodified index.html and local run assets, embedded in a self-contained HTML component; the complete run remains downloadable.
- Amazonia-vs-other contrasts are descriptive: log2 ratio = log2((mean Amazonian lateritic lakes + 1) / (mean other iron-rich environments + 1)).
- The broad iron-rich score combines total count and detection fraction across the full environment panel.
- The Amazonian-lake score combines positive Amazonia-vs-other log2 ratio, mean Amazonian count and detection fraction in AM/TI/TIA/VI samples.
- Coordinates and collection dates are read from Supplementary Table 1 and Supplementary Table 8. Missing coordinates or dates remain NA.
    """,
    """
- KO, EC/enzyme and PFAM heatmaps use the exact count matrices from Supplementary Tables 6 and 8.
- Functional-annotation columns are linked to sample ID, taxon_oid and GOLD Analysis Project ID whenever available.
- KO, EC/enzyme and PFAM result tables include annotation-specific hyperlinks to KEGG or InterPro/PFAM.
- Heatmap width and height use the same nominal pixel size per matrix row and column, and the renderer preserves the chart geometry instead of stretching it to the browser width.
- Z-score heatmaps are row-scaled per function: z = (count − row mean) / row standard deviation.
- KEMET reports are parsed from reportKMC_*.tsv; completed-block fractions are converted to module completeness percentages, and the consolidated MAG workbook is used as the priority source when present.
- antiSMASH visualization uses the unmodified index.html and local run assets, embedded in a self-contained HTML component; the complete run remains downloadable.
- Amazonia-vs-other contrasts are descriptive: log2 ratio = log2((mean Amazonian lateritic lakes + 1) / (mean other iron-rich environments + 1)).
- The broad iron-rich score combines total count and detection fraction across the full environment panel.
- The Amazonian-lake score combines positive Amazonia-vs-other log2 ratio, mean Amazonian count and detection fraction in AM/TI/TIA/VI samples.
- Coordinates and collection dates are read from Supplementary Table 1 and Supplementary Table 8. Missing coordinates or dates remain NA.
    """
  ))
  st.markdown("### " + txt("Métodos das figuras: tabela, método e código", "Figure methods: table, method and code"))
  figure_audit = pd.DataFrame([
    {"Figure / panel": "Other metals heatmap", "Section": "Iron & metals / Outros-metais", "Source data": "Supplementary Table 4 — Outros-metais", "Method": "Exact marker counts; x axis mapped to AM/TI/TIA/VI lake samples by the lake-matrix order; optional row z-score", "Code location": "streamlit_app.py: other_metals_lagoon_matrix + iron_tab", "Download table in app": "Outros-metais_lake_sample_axis.csv; Outros-metais_x_axis_mapping.csv"},
    {"Figure / panel": "Coordinate-check map", "Section": "Taxonomic profiles and Environmental–Metagenomic Integrator", "Source data": "Supplementary Table 1 + Supplementary Table 8 metadata", "Method": "Latitude/longitude-only coordinate plot; no external tiles; overlapping points get display-only offsets", "Code location": "streamlit_app.py: show_reliable_plotly_map", "Download table in app": "coordinates_reference_links.csv / metadata CSV buttons"},
    {"Figure / panel": "Records by group and omics layer", "Section": "Iron-Rich Environment Metagenomic Atlas", "Source data": "data/st8_metadata_curated.csv", "Method": "Group-by curated Atlas group and data_layer; count records", "Code location": "streamlit_app.py: st8_final_group_taxonomy_panel", "Download table in app": "ST8_final_metadata_filtered.csv"},
    {"Figure / panel": "Atlas taxonomy by group", "Section": "Iron-Rich Environment Metagenomic Atlas", "Source data": "data/st8_taxonomy_summary_by_group.csv", "Method": "GTDB Phylum/Order/Family presence/count summary; one omics layer at a time; percent mode normalizes within group/layer", "Code location": "streamlit_app.py: st8_final_group_taxonomy_panel + taxonomy_overlap_panel", "Download table in app": "ST8_final_Phylum/Order/Family_taxonomy.csv; common-taxa CSV"},
    {"Figure / panel": "Amazonia-vs-external KO contrasts", "Section": "Atlas / highlighted markers", "Source data": "data/st8_ko_amazonia_vs_groups.csv; data/st8_iron_amazonia_vs_groups.csv", "Method": "Descriptive log2 ratio = log2((mean Amazonian lake count + 1)/(mean selected external group/layer count + 1)); no statistical test", "Code location": "scripts/rebuild_supplementary_table8_final.py + streamlit_app.py", "Download table in app": "ST8_*_Amazonia_vs_groups.csv"},
    {"Figure / panel": "Atlas KO heatmaps", "Section": "Supplementary Table 8 matrices", "Source data": "Supplementary Table 8 final sheets", "Method": "Exact counts and row z-score = (count − row mean)/row standard deviation", "Code location": "src/supplementary_database.py: heatmap_figure; streamlit_app.py: render_st8_heatmap_scope_controls", "Download table in app": "ST8_all_KO_biomarkers.csv; ST8_iron_metabolism_KO_marker.csv"},
    {"Figure / panel": "IMG/JGI functional annotation heatmaps", "Section": "IMG/JGI functional annotations", "Source data": "Supplementary Table 6: KO, EC-numbers, PFAM, Detailed-Statistics2-by-Genome; Supplementary Table 8: ko, EC-number, pfam, metadata", "Method": "Exact counts or row z-score; equal nominal pixel size per cell; top functions ranked by total, mean, detection fraction or variance; columns linked by taxon_oid to sample and GOLD metadata; annotation-specific hyperlinks", "Code location": "src/functional_annotations.py; app.py/streamlit_app.py: functional_annotations_tab; scripts/export_functional_annotation_matrices.py", "Download table in app": "functional_annotations_*_absolute_counts.csv; functional_annotations_*_row_zscore.csv; functional_annotations_*_column_metadata.csv"},
    {"Figure / panel": "KEGG module completeness heatmaps", "Section": "KEGG Modules — MAGs & Metagenomes", "Source data": "Bin-genomas_all_kegg.xlsx or reportKMC_*.tsv", "Method": "Module status from KEMET; completed-block fraction converted to 0–1 score; interactive equal-cell heatmap plus publication panel of the 60 highest-priority modules ranked by completeness, prevalence and variation", "Code location": "src/kegg_modules.py; scripts/build_kegg_module_completeness.py; scripts/generate_kegg_module_completeness_heatmaps.py", "Download table in app": "outputs/kegg_modules/*status_matrix.csv; *completeness_score_matrix.csv; *heatmap_article.*; *heatmap_full.png"},
    {"Figure / panel": "KEGG module KO component map", "Section": "KEGG Modules — MAGs & Metagenomes", "Source data": "Detected_KOs and Missing_or_alternative_KOs fields from reportKMC", "Method": "Detected KOs are green; missing/alternative KOs are red; official KEGG module and KO links retained", "Code location": "src/kegg_modules.py: module_component_figure", "Download table in app": "*_KO_components.csv"},
    {"Figure / panel": "antiSMASH interactive BGC report", "Section": "MAGs & genomes", "Source data": "Complete antiSMASH run directory", "Method": "Local CSS/JS/images are embedded for in-app display without changing antiSMASH result content", "Code location": "src/antismash_viewer.py", "Download table in app": "Complete antiSMASH run ZIP; main GBK; MAG FASTA"},
    {"Figure / panel": "KO/pathway linked tables", "Section": "All KO, pathway and iron-metabolism tables", "Source data": "Supplementary Tables 4, 5 and 8 + data/st8_*.csv", "Method": "Adds KEGG KO entry hyperlinks only when a Kxxxxx identifier exists and KEGG pathway/module/search hyperlinks only when a pathway/module/metabolic-role value exists; no simulated annotation", "Code location": "streamlit_app.py: augment_ko_pathway_links; scripts/export_ko_pathway_linked_tables.py", "Download table in app": "All visible KO tables and outputs/linked_ko_pathway_tables/*.csv"},
    {"Figure / panel": "Atlas workflow schematic", "Section": "Materials, methods and supplementary workflow", "Source data": "App modules, supplementary tables and output figure directories", "Method": "Schematic workflow drawn programmatically from the atlas pipeline steps; exported in PNG, SVG and TIFF formats", "Code location": "scripts/generate_atlas_workflow_figure.py", "Download table in app": "outputs/article_highres_figures/SuppFigure22_Iron_Rich_Atlas_workflow.*"},
    {"Figure / panel": "Publication-format figure exports", "Section": "Code & reproducibility", "Source data": "All static publication figures already generated by the atlas scripts", "Method": "Batch export/conversion of publication figures to PNG, SVG and TIFF using the scripted figure-export pipeline", "Code location": "scripts/export_publication_figure_formats.py", "Download table in app": "outputs/publication_figure_exports/*"},
  ])
  show_table(figure_audit, "figure_audit_methods", height=420)
  csv_button(figure_audit, "figure_audit_tables_methods_code.csv", txt("Baixar tabela de métodos das figuras", "Download figure-method table"))
  figure_manifest_path = BASE_DIR / "data" / "figure_script_manifest.csv"
  if figure_manifest_path.exists():
    st.markdown("### " + txt("Como regenerar cada figura do Atlas", "How to regenerate each Atlas figure"))
    figure_manifest = pd.read_csv(figure_manifest_path)
    show_table(figure_manifest, "figure_script_manifest_methods", height=420)
    csv_button(figure_manifest, "figure_script_manifest.csv", txt("Baixar manifesto figura-script", "Download figure-script manifest"))
    download_text_file_button(BASE_DIR / "FIGURE_SCRIPT_REPRODUCIBILITY_MANIFEST.md", "Download FIGURE_SCRIPT_REPRODUCIBILITY_MANIFEST.md")
  execution_manifest_path = BASE_DIR / "data" / "script_execution_environment_manifest.csv"
  if execution_manifest_path.exists():
    st.markdown("### " + txt("Inputs, bibliotecas e ambientes de cada script", "Inputs, libraries and environments for each script"))
    execution_manifest = pd.read_csv(execution_manifest_path)
    show_table(execution_manifest, "script_execution_environment_manifest_methods", height=560)
    csv_button(execution_manifest, "script_execution_environment_manifest.csv", txt("Baixar manifesto de execução", "Download execution manifest"))
    e1, e2, e3 = st.columns(3)
    with e1:
      download_text_file_button(BASE_DIR / "environment.yml", "Download environment.yml")
    with e2:
      download_text_file_button(BASE_DIR / "environment-r.yml", "Download environment-r.yml")
    with e3:
      download_text_file_button(BASE_DIR / "scripts" / "install_r_packages.R", "Download install_r_packages.R")
  with st.expander(txt("Scripts e módulos usados", "Scripts and modules used"), expanded=False):
    script_paths = sorted((BASE_DIR / "scripts").rglob("*.py")) + sorted((BASE_DIR / "scripts").rglob("*.R")) + sorted((BASE_DIR / "scripts").rglob("*.sh"))
    module_paths = sorted((BASE_DIR / "src").glob("*.py"))
    code_files = script_paths + module_paths + [BASE_DIR / "streamlit_app.py", BASE_DIR / "app.py"]
    code_index = pd.DataFrame([{"file": str(p.relative_to(BASE_DIR)), "size_kB": round(p.stat().st_size/1024, 1)} for p in code_files if p.exists()])
    show_table(code_index, "code_file_index", height=420)
    allow_code = admin_code_access_enabled("code_reproducibility")
    if allow_code:
      for code_path in code_files:
        if code_path.exists():
          download_text_file_button(code_path, f"Download {code_path.relative_to(BASE_DIR)}")
    else:
      st.info(txt("Os nomes dos códigos ficam visíveis para reprodutibilidade. O conteúdo e download dos códigos são liberados somente quando o admin habilita nesta seção.", "Code names remain visible for reproducibility. Full code preview/download is available only when the admin enables it in this section."))
    linked_dir = BASE_DIR / "outputs" / "linked_ko_pathway_tables"
    if linked_dir.exists():
      st.markdown("#### " + txt("Tabelas KO/pathway com links KEGG", "KO/pathway tables with KEGG links"))
      for csv_path in sorted(linked_dir.glob("*.csv")):
        download_text_file_button(csv_path, f"Download {csv_path.relative_to(BASE_DIR)}")

  st.markdown("### " + txt("Referências principais", "Key references"))
  refs = pd.DataFrame([
    {"Reference": "Chen et al. (2019)", "Use in database": "IMG/M v.5.0 annotation and metadata source for microbial genomes and microbiomes", "DOI/URL": "https://doi.org/10.1093/nar/gky901"},
    {"Reference": "Salazar et al. (2019)", "Use in database": "Original marker framework for C, N and S biogeochemical-cycle genes", "DOI/URL": "https://doi.org/10.1016/j.cell.2019.10.014"},
    {"Reference": "Garber et al. (2020)", "Use in database": "FeGenie categories and iron metabolism interpretation", "DOI/URL": "https://doi.org/10.3389/fmicb.2020.00037"},
    {"Reference": "Menzel et al. (2016)", "Use in database": "Kaiju taxonomic assignment of CDS-level metagenomic data", "DOI/URL": "https://doi.org/10.1038/ncomms11257"},
    {"Reference": "Parks et al. and Chaumeil et al.", "Use in database": "CheckM and GTDB-Tk MAG quality/classification support", "DOI/URL": "https://doi.org/10.1093/bioinformatics/btac672"},
    {"Reference": "IMG/M — JGI Integrated Microbial Genomes with Microbiome Samples", "Use in database": "Primary portal/source for other iron-rich environment metagenome metadata summarized in Supplementary Table 8", "DOI/URL": "https://img.jgi.doe.gov/"},
    {"Reference": "KEGG", "Use in database": "KO, enzyme and module links and functional interpretation", "DOI/URL": "https://www.kegg.jp/"},
    {"Reference": "Palù et al. (2022) — KEMET", "Use in database": "KEGG module evaluation and microbial genome/metagenome annotation expansion; reportKMC parsing and module-completeness display", "DOI/URL": "https://doi.org/10.1016/j.csbj.2022.03.015"},
    {"Reference": "Blin et al. (2023) — antiSMASH 7.0", "Use in database": "BGC prediction and in-app visualization of complete antiSMASH reports for MAGs", "DOI/URL": "https://doi.org/10.1093/nar/gkad344"},
    {"Reference": "BV-BRC / PATRIC genome annotation service", "Use in database": "Official MAG annotation pages, Genome IDs, feature tables and local Annotation/MAGx folders downloaded by admin with BV-BRC CLI", "DOI/URL": "https://www.bv-brc.org/"},
    {"Reference": "NASA POWER", "Use in database": "Public API source for point-based climate variables used by the environmental integrator", "DOI/URL": "https://power.larc.nasa.gov/"},
    {"Reference": "CHIRPS", "Use in database": "Rainfall time-series context when selected by admin and available for the article dates/coordinates", "DOI/URL": "https://www.chc.ucsb.edu/data/chirps"},
    {"Reference": "SoilGrids / ISRIC", "Use in database": "Soil property context for mapped coordinates; public REST/API values remain cached locally", "DOI/URL": "https://soilgrids.org/"},
  ])
  show_table(refs, "methods_references", height=520)



def contact_recipients_from_settings() -> list[str]:
  settings = load_app_settings()
  raw = str(settings.get("contact_recipients", "leandro.pereira@pq.itv.org; Gisele.Nunes@itv.org"))
  values = [x.strip() for x in re.split(r"[;,\n]+", raw) if x.strip()]
  return values or ["leandro.pereira@pq.itv.org", "Gisele.Nunes@itv.org"]


def save_contact_submission(payload: dict) -> None:
  ensure_runtime_dirs()
  CONTACT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
  with CONTACT_LOG_PATH.open("a", encoding="utf-8") as handle:
    handle.write(json.dumps(payload, ensure_ascii=False, default=_json_default) + "\n")


def try_send_contact_email(payload: dict, recipients: list[str]) -> tuple[bool, str]:
  """Send contact e-mail if SMTP settings are configured; otherwise keep the logged submission."""
  smtp_host = runtime_setting("SMTP_HOST", "")
  smtp_port = int(runtime_setting("SMTP_PORT", "587") or 587)
  smtp_user = runtime_setting("SMTP_USER", "")
  smtp_password = runtime_setting("SMTP_PASSWORD", "")
  smtp_from = runtime_setting("SMTP_FROM", smtp_user or "no-reply@example.org")
  if not smtp_host or not smtp_from:
    return False, "SMTP is not configured; message was saved locally and a mail client link is shown."
  subject_prefix = str(load_app_settings().get("contact_subject_prefix", "Amazonian Lateritic Lakes Metagenomic Atlas collaboration contact"))
  msg = EmailMessage()
  msg["From"] = smtp_from
  msg["To"] = ", ".join(recipients)
  msg["Subject"] = f"{subject_prefix}: {payload.get('name', 'Visitor')}"
  reply_to = str(payload.get("email", "")).strip()
  if reply_to:
    msg["Reply-To"] = reply_to
  msg.set_content(
    "New contact message from the Amazonian Lateritic Lakes Metagenomic Atlas.\n\n"
    f"Name: {payload.get('name', '')}\n"
    f"Email: {payload.get('email', '')}\n"
    f"Affiliation: {payload.get('affiliation', '')}\n"
    f"Interest: {payload.get('interest', '')}\n"
    f"Message:\n{payload.get('message', '')}\n\n"
    f"Timestamp UTC/local app: {payload.get('timestamp', '')}\n"
    f"Program: {PUBLIC_PROGRAM_NAME} v{PUBLIC_PROGRAM_VERSION} ({DATABASE_RELEASE_LABEL})\n"
  )
  try:
    with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
      server.starttls()
      if smtp_user and smtp_password:
        server.login(smtp_user, smtp_password)
      server.send_message(msg)
    return True, "Message sent by SMTP."
  except Exception as exc:
    return False, f"SMTP sending failed: {exc}. Message was saved locally."


def contact_form_panel(location_key: str = "contact", expanded: bool = False) -> None:
  recipients = contact_recipients_from_settings()
  settings = load_app_settings()
  with st.expander(txt("Contato para colaboração científica", "Contact for scientific collaboration"), expanded=expanded):
    st.markdown(txt(
      "Use este formulário para enviar uma mensagem sobre colaboração, dados, grupos de pesquisa ou dúvidas sobre o atlas metagenômico.",
      "Use this form to send a message about collaboration, data, research groups or questions about the metagenomic atlas."
    ))
    with st.form(f"{location_key}_form", clear_on_submit=True):
      c1, c2 = st.columns(2)
      with c1:
        name = st.text_input(txt("Nome", "Name"), key=f"{location_key}_name")
        email = st.text_input("E-mail", key=f"{location_key}_email")
      with c2:
        affiliation = st.text_input(txt("Instituição / grupo", "Institution / group"), key=f"{location_key}_affiliation")
        interest = st.selectbox(txt("Tipo de contato", "Contact type"), ["Collaboration", "Research group", "Data access", "Question", "Other"], key=f"{location_key}_interest")
      message = st.text_area(txt("Mensagem", "Message"), height=130, key=f"{location_key}_message")
      submitted = st.form_submit_button(txt("Enviar contato", "Send contact"), type="primary", width="stretch")
    if submitted:
      if not message.strip():
        st.error(txt("Escreva uma mensagem antes de enviar.", "Please write a message before sending."))
      else:
        payload = {
          "timestamp": datetime_now_iso(),
          "name": name.strip(),
          "email": email.strip(),
          "affiliation": affiliation.strip(),
          "interest": interest,
          "message": message.strip(),
          "recipients": recipients,
          "app_version": APP_VERSION,
          "program_version": PUBLIC_PROGRAM_VERSION,
        }
        save_contact_submission(payload)
        sent, info = try_send_contact_email(payload, recipients)
        if sent:
          st.success(txt("Mensagem enviada com sucesso para os responsáveis pelo projeto.", "Message sent successfully to the project contacts."))
        else:
          st.warning(info)
          mailto_subject = quote_plus(str(settings.get("contact_subject_prefix", "Amazonian Lateritic Lakes Metagenomic Atlas collaboration contact")))
          body = quote_plus(f"Name: {name}\nEmail: {email}\nAffiliation: {affiliation}\nInterest: {interest}\n\n{message}")
          st.link_button(txt("Abrir e-mail para enviar manualmente", "Open e-mail to send manually"), f"mailto:{','.join(recipients)}?subject={mailto_subject}&body={body}")
    st.caption(txt(
      "Destinatários configurados pelo admin: " + "; ".join(recipients),
      "Admin-configured recipients: " + "; ".join(recipients)
    ))


def admin_contact_settings_panel() -> None:
  settings = load_app_settings()
  with st.expander(txt("Contato público — e-mails de destino", "Public contact — destination e-mails"), expanded=False):
    st.caption(txt(
      "Apenas o admin pode alterar os destinatários do formulário de contato. Separe múltiplos e-mails por ponto e vírgula, vírgula ou quebra de linha.",
      "Only the admin can change the destination recipients for the contact form. Separate multiple e-mails by semicolon, comma or line break."
    ))
    recipients_raw = st.text_area(
      txt("E-mails de destino", "Destination e-mails"),
      value=str(settings.get("contact_recipients", "leandro.pereira@pq.itv.org; Gisele.Nunes@itv.org")),
      height=90,
      key="admin_contact_recipients",
    )
    subject_prefix = st.text_input(
      txt("Prefixo do assunto", "Subject prefix"),
      value=str(settings.get("contact_subject_prefix", "Amazonian Lateritic Lakes Metagenomic Atlas collaboration contact")),
      key="admin_contact_subject_prefix",
    )
    if st.button(txt("Salvar e-mails de contato", "Save contact e-mails"), key="save_contact_recipients", type="primary", width="stretch"):
      settings["contact_recipients"] = recipients_raw.strip()
      settings["contact_subject_prefix"] = subject_prefix.strip()
      settings["contact_settings_updated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
      if save_app_settings(settings):
        st.success(txt("Destinatários do formulário atualizados.", "Contact recipients updated."))


def code_reproducibility_tab():
  st.subheader(txt("Código reprodutível do banco e das figuras", "Reproducible code for the database and figures"))
  visitor_counter_public_footer("code_reproducibility_counter")
  st.markdown(txt(
    "Esta seção mostra somente as versões finais/canônicas dos scripts usados pelo aplicativo e pelo artigo. Os scripts corrigidos substituem as versões anteriores na interface e incluem inputs, outputs e instruções.",
    "This section shows only the final/canonical script versions used by the application and article. Corrected scripts replace earlier versions in the interface and include inputs, outputs and instructions."
  ))
  st.markdown("#### " + txt("Fluxos KEGG/KEMET, antiSMASH e anotações funcionais", "KEGG/KEMET, antiSMASH and functional-annotation workflows"))
  new_workflows = pd.DataFrame([
    {"Code": "src/kegg_modules.py", "Input": "data/kegg_modules/mags|metagenomes/reports/reportKMC_*.tsv; optional tables/Bin-genomas_all_kegg.xlsx", "Output": "outputs/kegg_modules/*status_matrix.csv, *completeness_score_matrix.csv, *report_long.csv", "Method": "Parses KEMET module reports, derives block completeness, builds status/score matrices, proportional-cell heatmaps and per-module KO component maps"},
    {"Code": "scripts/build_kegg_module_completeness.py", "Input": "Same KEMET directories", "Output": "Batch-generated CSV matrices and publication heatmaps outside Streamlit", "Method": "Command-line wrapper; run with --dataset mags, metagenomes or all; also invokes the static heatmap generator"},
    {"Code": "scripts/generate_kegg_module_completeness_heatmaps.py", "Input": "Bin-genomas_all_kegg.xlsx and/or reportKMC_*.tsv", "Output": "Article PNG/PDF/SVG heatmaps, complete-matrix PNGs and selected-module CSV tables", "Method": "Ranks modules by combined completeness, prevalence and variation; uses fixed cell geometry and discrete KEMET status colors"},
    {"Code": "scripts/rebuild_validate_kemet_and_other_metals.py", "Input": "20 metagenome reportKMC_*.tsv files; Supplementary Table 4 Outros-metais and iron statistics; FeGenie source tables", "Output": "Validated 448-module KEMET matrices and Figure 39; per-sample completeness; iron/FeGenie pathway tables; KO lists separated by metal", "Method": "Separates KEMET status from block fraction, requires 448 modules/report, maps 20 Ga identifiers to study samples, and classifies non-iron-metal KOs from original gene/function annotations"},
    {"Code": "scripts/validate_kegg_antismash_filenames.py", "Input": "Supported MAG/metagenome report, FASTA and antiSMASH naming examples", "Output": "outputs/kegg_modules/filename_normalization_validation.csv and antismash_inventory.csv", "Method": "Validates canonical MAG.<number> and Ga identifiers for strict/orig/permissive/metawrap/repaired/ptn/pnt/ptns/pnts variants"},
    {"Code": "scripts/prepare_antismash_runs.py", "Input": "data/kegg_modules/mags/antismash_archives/*.zip", "Output": "Extracted runs under data/kegg_modules/mags/gbk_antismash/<archive-stem>/ plus extraction report", "Method": "Safe ZIP extraction with path traversal protection and index.html validation"},
    {"Code": "scripts/Kemet.merge_final.R", "Input": "Directory containing KEMET reportKMC TSV files", "Output": "Merged Res_KEMET.tsv-style table", "Method": "Original project R workflow preserved for traceability"},
    {"Code": "src/antismash_viewer.py", "Input": "Complete antiSMASH run directory containing index.html, CSS, JS, regions.js, images and GBK files", "Output": "Self-contained interactive HTML view and downloadable run ZIP", "Method": "Inlines local antiSMASH assets without changing BGC content"},
    {"Code": "src/functional_annotations.py", "Input": "Supplementary Tables 6 and 8 KO/EC/PFAM matrices", "Output": "Absolute-count and row-z-score heatmaps plus linked tables", "Method": "Equal nominal pixel size per heatmap row/column; KO, EC and PFAM hyperlinks are derived from the selected annotation type"},
  ])
  show_table(new_workflows, "new_reproducible_workflows", height=470)
  csv_button(new_workflows, "KEGG_KEMET_antiSMASH_functional_annotation_workflows.csv", txt("Baixar descrição dos novos fluxos", "Download new-workflow description"))
  if (BASE_DIR / "docs" / "code" / "KEGG_MODULES_AND_ANTISMASH.md").exists():
    download_text_file_button(BASE_DIR / "docs" / "code" / "KEGG_MODULES_AND_ANTISMASH.md", "Download KEGG_MODULES_AND_ANTISMASH.md")
  code_files = []
  code_extensions = {".py", ".r", ".R", ".sh", ".txt", ".csv", ".yml", ".yaml"}
  for folder in [BASE_DIR / "scripts", BASE_DIR / "src"]:
    if folder.exists():
      code_files.extend(sorted([p for p in folder.rglob("*") if p.is_file() and p.suffix in code_extensions and "__pycache__" not in p.parts]))
  essential_docs = [
    BASE_DIR / "FIGURE_REPRODUCTION_COMMANDS.md",
    BASE_DIR / "README.md",
    BASE_DIR / "README_REPRODUCIBILITY.md",
    BASE_DIR / "RUN_APP_AND_REPRODUCE_FIGURES.md",
    BASE_DIR / "STREAMLIT_COMMUNITY_CLOUD.md",
    BASE_DIR / "FIGURE_SCRIPT_REPRODUCIBILITY_MANIFEST.md",
    BASE_DIR / "docs" / "code" / "PLOTLY_STATIC_EXPORTS.md",
  ]
  code_files.extend([path for path in essential_docs if path.exists()])
  for root_name in ["app.py", "requirements.txt", "packages.txt", ".python-version", "run_app_no_root.sh"]:
    root_file = BASE_DIR / root_name
    if root_file.exists():
      code_files.append(root_file)
  code_files = sorted(set(code_files), key=lambda x: str(x.relative_to(BASE_DIR)))
  if not code_files:
    st.info("No scripts folder found.")
    return
  labels = [str(p.relative_to(BASE_DIR)) for p in code_files]
  manifest = pd.DataFrame({
    "script_path": labels,
    "category": ["legacy" if "legacy_scripts" in str(p) else "source module" if "/src/" in str(p).replace("\\", "/") else "method/documentation" if p.suffix.lower() == ".md" else "analysis/generation script" for p in code_files],
    "bytes": [p.stat().st_size for p in code_files],
    "sha256": [hashlib.sha256(p.read_bytes()).hexdigest() for p in code_files],
  })
  st.markdown("#### " + txt("Manifesto completo dos scripts", "Complete script manifest"))
  show_table(manifest, "code_reproducibility_script_manifest", height=260)
  figure_manifest_path = BASE_DIR / "data" / "figure_script_manifest.csv"
  if figure_manifest_path.exists():
    st.markdown("#### " + txt("Manifesto figura-script", "Figure-script manifest"))
    figure_manifest = pd.read_csv(figure_manifest_path)
    show_table(figure_manifest, "code_reproducibility_figure_script_manifest", height=360)
    csv_button(figure_manifest, "figure_script_manifest.csv", txt("Baixar manifesto figura-script", "Download figure-script manifest"))
  if (BASE_DIR / "FIGURE_SCRIPT_REPRODUCIBILITY_MANIFEST.md").exists():
    download_text_file_button(BASE_DIR / "FIGURE_SCRIPT_REPRODUCIBILITY_MANIFEST.md", "Download FIGURE_SCRIPT_REPRODUCIBILITY_MANIFEST.md")

  nature_dir = BASE_DIR / "outputs" / "nature_isme_figures"
  if nature_dir.exists():
    st.markdown("#### " + txt("Pacote final Nature/ISME com figuras, estatísticas e scripts", "Final Nature/ISME package with figures, statistics and scripts"))
    st.info(txt(
      "Este pacote contém as figuras principais e suplementares, a nova tabela suplementar da Figura Suplementar 1, testes paramétricos e não paramétricos, símbolos de significância e os CSVs-fonte usados em cada painel.",
      "This package contains the main and supplementary figures regenerated with higher readability, the new Supplementary Figure 1 table, parametric and non-parametric tests, significance symbols and the source CSV files used in each panel."
    ))
    final_bundle = nature_dir / "nature_isme_figures_statistics_scripts_bundle.zip"
    if final_bundle.exists():
      st.download_button(
        txt("Baixar pacote final de figuras + estatísticas + scripts (.zip)", "Download final figures + statistics + scripts package (.zip)"),
        data=final_bundle.read_bytes(),
        file_name="nature_isme_figures_statistics_scripts_bundle.zip",
        mime="application/zip",
        key="download_nature_isme_final_bundle",
        width="stretch",
      )
    final_table = nature_dir / "Supplementary_Table_S1_general_metrics_and_statistics.xlsx"
    if final_table.exists():
      st.download_button(
        txt("Baixar nova Tabela Suplementar S1 com estatísticas (.xlsx)", "Download new Supplementary Table S1 with statistics (.xlsx)"),
        data=final_table.read_bytes(),
        file_name="Supplementary_Table_S1_general_metrics_and_statistics.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_nature_isme_supp_table",
        width="stretch",
      )
    for extra_path, label in [
      (BASE_DIR / "scripts" / "generate_nature_isme_article_figures_and_stats.py", "generate_nature_isme_article_figures_and_stats.py"),
      (BASE_DIR / "scripts" / "run_all_nature_isme_figure_pipeline.sh", "run_all_nature_isme_figure_pipeline.sh"),
      (nature_dir / "MANUSCRIPT_METHODS_AND_CODES_TEXT_TO_INSERT.md", "MANUSCRIPT_METHODS_AND_CODES_TEXT_TO_INSERT.md"),
      (nature_dir / "nature_isme_figure_script_manifest.csv", "nature_isme_figure_script_manifest.csv"),
      (nature_dir / "nature_isme_st8_figure_script_manifest.csv", "nature_isme_st8_figure_script_manifest.csv"),
      (nature_dir / "nature_isme_biomarker_boxplot_manifest.csv", "nature_isme_biomarker_boxplot_manifest.csv"),
    ]:
      if extra_path.exists():
        download_text_file_button(extra_path, f"Download {label}")

  zip_path = APP_CACHE_DIR / "generated" / "all_reproducible_scripts_and_modules.zip"
  try:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
      written: set[str] = set()
      for file_path in code_files:
        arcname = str(file_path.relative_to(BASE_DIR))
        if arcname in written:
          continue
        zf.write(file_path, arcname=arcname)
        written.add(arcname)
    st.download_button(
      txt("Baixar TODOS os scripts e módulos (.zip)", "Download ALL scripts and modules (.zip)"),
      data=zip_path.read_bytes(),
      file_name="all_reproducible_scripts_and_modules.zip",
      mime="application/zip",
      key="download_all_reproducible_scripts_zip",
      width="stretch",
    )
  except Exception as exc:
    st.warning(f"Could not create reproducible-code ZIP: {exc}")
  st.info(txt(
    "Somente os scripts finais/canônicos usados para gerar as figuras do app e do artigo aparecem aqui, junto ao manifesto figura-input-script e às instruções de execução.",
    "Only the final/canonical scripts used to generate app and article figures are listed here, together with the figure-input-script manifest and execution instructions."
  ))
  selected = st.selectbox(txt("Selecionar arquivo", "Select file"), labels, key="code_file_select")
  path = BASE_DIR / selected
  code = path.read_text(encoding="utf-8", errors="replace")
  suffix = path.suffix.lower()
  language = "python" if suffix == ".py" else ("r" if suffix == ".r" else ("bash" if suffix == ".sh" else "text"))
  st.code(code, language=language)
  st.download_button(txt("Baixar arquivo de código", "Download code file"), data=code.encode("utf-8"), file_name=path.name, mime="text/plain", key=f"download_{selected}")



def publication_figure_sort_key(path: Path) -> tuple:
  """Order canonical figures exactly as in the article and supplement."""
  stem = path.stem
  m = re.match(r"^Figure(\d+)(?:_|$)", stem, re.I)
  if m:
    return (0, int(m.group(1)), stem.lower())
  if stem == "SupplementaryFigure_Rarefaction_curve_CDS_min_depth":
    return (1, 2.1, stem.lower())
  m = re.match(r"^SupplementaryFigure(\d+)(?:_|$)", stem, re.I)
  if m:
    return (1, int(m.group(1)), stem.lower())
  return (2, 10**9, stem.lower())


def publication_figure_canonical_key(path: Path) -> str:
  """Collapse sibling/original figure variants so each biological figure appears once."""
  stem = path.stem
  stem = re.sub(r"(?i)(_original|_vivid)$", "", stem)
  stem = re.sub(r"(?i)(_copy\d*|_duplicate\d*)$", "", stem)
  return stem.lower()


PROHIBITED_PUBLICATION_FIGURE_BASENAMES = {
  "Taxonomy_Phylum_Bacteria_lake_season_heatmap.png",
  "Taxonomy_Phylum_Bacteria_lake_season_heatmap_preview.png",
  "Taxonomy_Domain_individual_samples_heatmap.png",
  "Taxonomy_Domain_individual_samples_heatmap_preview.png",
  "Figure8_MAG_bins_percentage_abundance.png",
  "SAppFig_KEMET_all_lagoon_metagenomes_heatmap.png",
  "SAppFig_KEMET_all_lagoon_metagenomes_heatmap_KEMET_style_3state.png",
  "SAppFig_lagoon_plus_external_iron_rich_module_completeness_KEMET_style_3state_heatmap.png",
  "SAppFig_ST8_external_iron_rich_module_completeness_KEMET_style_3state_heatmap.png",
  "SAppFig_ST8_external_iron_rich_module_status_summary_3state_barplot.png",
}

def _is_prohibited_publication_figure(path: Path) -> bool:
  if path.name in PROHIBITED_PUBLICATION_FIGURE_BASENAMES:
    return True
  # Very tall contact sheets make labels unreadable in Streamlit.  For the
  # audited long heatmaps, display the exact full-resolution manuscript panels
  # instead of the reduced composite/base PNG.
  match = re.match(r"^(SupplementaryFigure(?:32|33|37|38))_", path.stem, re.I)
  if match and not re.search(r"_P\d{3}$", path.stem, re.I):
    if any(path.parent.glob(path.stem + "_P*.png")):
      return True
  return False

def publication_figure_rank(path: Path) -> tuple[int, int, str]:
  """Prefer publication-ready PNGs over original/debug variants."""
  stem = path.stem.lower()
  original_penalty = 10 if "original" in stem else 0
  vivid_penalty = 1 if stem.endswith("_vivid") else 0
  suffix_rank = {".png": 0, ".jpg": 1, ".jpeg": 2, ".tif": 3, ".tiff": 4}.get(path.suffix.lower(), 9)
  return (original_penalty + vivid_penalty, suffix_rank, path.name.lower())


def is_valid_display_image(path: Path) -> tuple[bool, str]:
  """Return a safe image-display decision without letting truncated files break Streamlit."""
  if not path.exists():
    return False, "missing file"
  if path.stat().st_size <= 0:
    return False, "empty file"
  if Image is None:
    return True, "Pillow unavailable; basic file checks passed"
  try:
    from PIL import ImageFile as _ImageFile
    _ImageFile.LOAD_TRUNCATED_IMAGES = True
    with Image.open(path) as img:
      img.load()
      width, height = img.size
    if width < 10 or height < 10:
      return False, f"invalid image geometry: {width}x{height}"
    return True, f"validated image: {width}x{height}px"
  except Exception as exc:
    return False, f"truncated/corrupted image: {exc}"

def final_publication_figures_tab() -> None:
  """Publication figures, inputs, scripts and execution guide."""
  st.header("Publication figures & scripts")
  st.markdown(
    "This section keeps the full database interface active and shows the same final manuscript figures used in the article, "
    "including all main and supplementary panels, inputs, scripts, statistics and execution instructions."
  )
  main_fig_dir = BASE_DIR / "outputs" / "final_publication_figures"
  supplementary_fig_dir = BASE_DIR / "outputs" / "app_supplementary_figures"
  final_stat_dir = BASE_DIR / "outputs" / "final_publication_statistics"
  final_input_dir = BASE_DIR / "data" / "final_publication_inputs"
  final_script_dir = BASE_DIR / "scripts" / "final_publication_figures"
  manifest_path = BASE_DIR / "data" / "final_figure_script_manifest.csv"
  readme_path = BASE_DIR / "COMO_EXECUTAR_APP_COMPLETO_E_FIGURAS_FINAIS.md"
  manifest_df = pd.read_csv(manifest_path).fillna("") if manifest_path.exists() else pd.DataFrame()

  tabs = st.tabs(["Figures", "Inputs / database", "Scripts", "Methods / execution", "Statistics"])

  with tabs[0]:
    st.subheader("Final article and supplementary figures")
    if manifest_path.exists():
      try:
        figure_manifest_checked = pd.read_csv(manifest_path)
        main_count = int(figure_manifest_checked["Figure"].astype(str).str.match(r"^Figure \d+$").sum())
        supp_count = int(figure_manifest_checked["Figure"].astype(str).str.match(r"^Supplementary Figure \d+$").sum())
        manifest_scripts = []
        for script_spec in figure_manifest_checked["Script"].dropna().astype(str):
          manifest_scripts.extend([part.strip() for part in script_spec.split(";") if part.strip()])
        missing_scripts = [s for s in sorted(set(manifest_scripts)) if not (BASE_DIR / s).exists()]
        available_asset_names = {p.name for folder in (main_fig_dir, supplementary_fig_dir) if folder.exists() for p in folder.iterdir() if p.is_file()}
        missing_assets = []
        for _, audit_row in figure_manifest_checked.iterrows():
          for asset_col in ["PNG", "SVG", "PDF"]:
            asset_name = str(audit_row.get(asset_col, "")).strip()
            if asset_name and asset_name not in available_asset_names:
              missing_assets.append(asset_name)
        qa1, qa2, qa3 = st.columns(3)
        qa1.metric("Main figures", main_count)
        qa2.metric("Supplementary figures", supp_count)
        qa3.metric("Manifest records", len(figure_manifest_checked))
        if main_count > 0 and supp_count > 0 and not missing_scripts and not missing_assets:
          st.success(txt("Conferência aprovada: as figuras principais e suplementares listadas no manifesto possuem arquivos PNG/SVG/PDF e scripts correspondentes presentes.", "Integrity check passed: the main and supplementary figures listed in the manifest have corresponding PNG/SVG/PDF files and scripts present."))
        else:
          st.warning(txt(f"Conferência: scripts ausentes={len(missing_scripts)}; arquivos de figura ausentes={len(set(missing_assets))}.", f"Integrity check: missing scripts={len(missing_scripts)}; missing figure files={len(set(missing_assets))}."))
      except Exception as exc:
        st.warning(f"Figure integrity check could not be completed: {exc}")
    missing_figure_dirs = [str(folder) for folder in (main_fig_dir, supplementary_fig_dir) if not folder.exists()]
    if missing_figure_dirs:
      st.warning("Missing canonical figure directories: " + ", ".join(missing_figure_dirs))
    else:
      image_suffixes = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}
      image_priority = {".png": 0, ".jpg": 1, ".jpeg": 2, ".tif": 3, ".tiff": 4}
      image_candidates = sorted(
        [fp for folder in (main_fig_dir, supplementary_fig_dir) for fp in folder.iterdir() if fp.suffix.lower() in image_suffixes and not _is_prohibited_publication_figure(fp)],
        key=lambda fp: (publication_figure_sort_key(fp), image_priority.get(fp.suffix.lower(), 99), fp.name.lower()),
      )
      # Show each biological figure only once, while keeping all sibling formats
      # available through the download buttons below.
      representatives: dict[str, Path] = {}
      invalid_images = []
      # Build the index from file metadata only. Fully decoding every large PNG
      # during navigation made this page take several minutes and could exhaust
      # memory. Each visible page is still validated immediately before display.
      for fp in image_candidates:
        if not fp.exists() or fp.stat().st_size <= 0:
          invalid_images.append({"file": fp.name, "reason": "missing or empty file", "bytes": fp.stat().st_size if fp.exists() else 0})
          continue
        key = publication_figure_canonical_key(fp)
        if key not in representatives or publication_figure_rank(fp) < publication_figure_rank(representatives[key]):
          representatives[key] = fp
      if invalid_images:
        st.warning(txt(f"{len(invalid_images)} imagem(ns) truncada(s), vazia(s) ou inválida(s) foram ignoradas para evitar quebra do app.", f"{len(invalid_images)} truncated, empty or invalid image(s) were skipped so the app does not crash."))
        show_table(pd.DataFrame(invalid_images), "invalid_final_publication_images", height=220)
      fig_files = sorted(representatives.values(), key=publication_figure_sort_key)
      st.caption(
        f"{len(fig_files)} unique figures available in the canonical main and supplementary directories "
        f"({len(image_candidates)} raster files across both collections)."
      )
      figure_scope = st.radio(
        txt("Coleção de figuras", "Figure collection"),
        ["Main figures", "Supplementary figures", "All figures"],
        index=0, horizontal=True, key="final_figure_scope",
        format_func=lambda value: {
          "Main figures": txt("Figuras principais", "Main figures"),
          "Supplementary figures": txt("Figuras suplementares", "Supplementary figures"),
          "All figures": txt("Todas as figuras", "All figures"),
        }[value],
      )
      if figure_scope == "Main figures":
        scoped_figures = [fp for fp in fig_files if re.match(r"^Figure\d+", fp.stem, re.I)]
      elif figure_scope == "Supplementary figures":
        scoped_figures = [fp for fp in fig_files if re.match(r"^SupplementaryFigure\d+", fp.stem, re.I)]
      else:
        scoped_figures = fig_files
      name_filter = st.text_input(txt("Filtrar nome da figura", "Filter figure name"), value="", key="final_fig_filter")
      filtered_figures = [
        fp for fp in scoped_figures
        if not name_filter or name_filter.lower() in fp.name.lower()
      ]
      main_visible_count = sum(bool(re.match(r"^Figure\d+", fp.stem, re.I)) for fp in filtered_figures)
      supp_visible_count = sum(bool(re.match(r"^SupplementaryFigure\d+", fp.stem, re.I)) for fp in filtered_figures)
      st.caption(f"Current selection: {len(filtered_figures)} figures — {main_visible_count} main and {supp_visible_count} supplementary.")
      # Paginate every collection, including "All figures". Rendering dozens
      # of full-resolution panels and preparing every download in one Streamlit
      # rerun caused the previous section to load slowly. No figure is removed;
      # all remain available through the collection selector and page control.
      page_size = st.selectbox("Figures per page", options=[4, 8, 12, 20], index=1, key="final_fig_page_size")
      total_pages = max(1, (len(filtered_figures) + page_size - 1) // page_size)
      page_number = int(st.number_input("Page", min_value=1, max_value=total_pages, value=1, step=1, key="final_fig_page_number"))
      start_index = (page_number - 1) * page_size
      visible_figures = filtered_figures[start_index:start_index + page_size]
      st.caption(f"Showing {start_index + 1 if visible_figures else 0}–{start_index + len(visible_figures)} of {len(filtered_figures)} matching figures (page {page_number} of {total_pages}).")
      last_section = None
      for p in visible_figures:
        section = "Main article figures" if re.match(r"^Figure\d+", p.stem, re.I) else "Supplementary figures" if re.match(r"^SupplementaryFigure\d+", p.stem, re.I) else "Additional application figures"
        if section != last_section:
          st.markdown("### " + section)
          last_section = section
        st.markdown(f"#### `{p.name}`")
        ok, reason = is_valid_display_image(p)
        if ok:
          st.image(str(p), width="stretch")
        else:
          st.warning(txt(f"Imagem não exibida porque falhou na validação: {p.name} — {reason}", f"Image not displayed because validation failed: {p.name} — {reason}"))
          continue
        format_cols = st.columns(4)
        siblings = {ext: p.with_suffix(ext) for ext in [".png", ".svg", ".pdf", ".tiff"]}
        labels = {".png":("PNG","image/png"),".svg":("SVG","image/svg+xml"),".pdf":("PDF","application/pdf"),".tiff":("TIFF","image/tiff")}
        for col,(ext,fp) in zip(format_cols,siblings.items()):
          with col:
            if fp.exists():
              lab,mime=labels[ext]
              button_key = f"dl_final_fig_{p.name}_{fp.name}_{ext}".replace(" ", "_")
              st.download_button(
                f"Download {lab}",
                data=fp.read_bytes(),
                file_name=fp.name,
                mime=mime,
                key=button_key,
                width="stretch",
              )
        derived_dir = BASE_DIR / "data" / "final_publication_derived"
        source_candidates = list(derived_dir.glob(f"{p.stem}*source*.csv")) if derived_dir.exists() else []
        if source_candidates:
          source_df = pd.read_csv(source_candidates[0])
          show_plot_source_table(source_df, f"derived_source_{p.stem}", f"Input/source data: {source_candidates[0].name}")
        manifest_row = pd.DataFrame()
        if not manifest_df.empty and "PNG" in manifest_df.columns:
          manifest_row = manifest_df[manifest_df["PNG"].astype(str) == f"{p.stem}.png"]
        if not manifest_row.empty:
          mr = manifest_row.iloc[0]
          st.caption(txt(
            f"Figura: {mr.get('Figure', p.stem)} | Entrada: {mr.get('Input', '')} | Script: {mr.get('Script', '')} | Método: {mr.get('Method / description', '')}",
            f"Figure: {mr.get('Figure', p.stem)} | Input: {mr.get('Input', '')} | Script: {mr.get('Script', '')} | Method: {mr.get('Method / description', '')}"
          ))
        else:
          st.caption(txt(
            f"Figura: {p.stem}. Consulte data/final_figure_script_manifest.csv para a entrada e o script exatos.",
            f"Figure: {p.stem}. See data/final_figure_script_manifest.csv for the exact input and script."
          ))
        audit_dir = BASE_DIR / "outputs" / "final_publication_audit_tables"
        if audit_dir.exists():
          stem_key = p.stem.replace("_vivid", "").replace("_original", "")
          candidates = list(audit_dir.glob(f"*{stem_key}*.csv"))
          if not candidates:
            candidates = list(audit_dir.glob(f"source_{p.stem}*.csv"))
          if candidates:
            try:
              source_df = pd.read_csv(candidates[0])
              show_plot_source_table(source_df, f"source_{p.stem}", f"Source table: {candidates[0].name}")
            except Exception as exc:
              st.caption(f"Source table could not be previewed: {exc}")

  with tabs[1]:
    st.subheader("Input files and database additions")
    st.markdown("Clean aliases are available in `data/`; original uploaded names are preserved in `data/final_publication_inputs/`.")
    if manifest_path.exists():
      try:
        man = pd.read_csv(manifest_path)
        st.markdown("#### Figure-to-script/input manifest")
        st.dataframe(arrow_safe_dataframe(man), width="stretch", height=420, key="final_figure_manifest_dataframe")
        st.download_button("Download final figure manifest CSV", data=manifest_path.read_bytes(), file_name=manifest_path.name, mime="text/csv", key="download_final_manifest")
      except Exception as exc:
        st.warning(f"Could not read manifest: {exc}")
    if final_input_dir.exists():
      rows=[]
      for p in sorted(final_input_dir.iterdir()):
        if p.is_file():
          rows.append({"file": p.name, "relative_path": str(p.relative_to(BASE_DIR)), "size_MB": round(p.stat().st_size/1024/1024, 3)})
      st.markdown("#### Packaged original input files")
      st.dataframe(arrow_safe_dataframe(pd.DataFrame(rows)), width="stretch", height=420, key="final_input_files_dataframe")
      for fp in sorted(final_input_dir.iterdir()):
        if fp.is_file():
          mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if fp.suffix.lower()==".xlsx" else "text/plain"
          st.download_button(f"Download input: {fp.name}", data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"download_final_input_{fp.name}")
    direct_inputs = [BASE_DIR/"data"/x for x in ["resultado.cds.otu.tab","resultado.cds.tax.tab","fiqui2.xlsx","Supplementary_table_5-Differential-abundance-pathways-KOs.xlsx","Supplementary_table_7-MAGS-Quality-Genome_Lineage-Classification.xlsx","Supplementary_table_8_final_restructured_filled.xlsx"]]
    st.markdown("#### Canonical inputs used by the corrected figures")
    for fp in direct_inputs:
      if fp.exists():
        mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if fp.suffix.lower()==".xlsx" else "text/tab-separated-values"
        st.download_button(f"Download {fp.name}", data=fp.read_bytes(), file_name=fp.name, mime=mime, key=f"download_canonical_input_{fp.name}")

  with tabs[2]:
    st.subheader("Final optimized scripts")
    st.caption(
      txt(
        "A lista é carregada a partir do manifesto. O conteúdo e o download de cada script são abertos sob demanda para evitar a leitura e o hash de todo o repositório em cada atualização da página.",
        "The list is loaded from the manifest. Script contents and downloads are opened on demand so the app does not read and hash the entire repository on every page rerun.",
      )
    )
    manifest_script_paths = []
    if not manifest_df.empty and "Script" in manifest_df.columns:
      for script_spec in manifest_df["Script"].dropna().astype(str):
        manifest_script_paths.extend([part.strip() for part in script_spec.split(";") if part.strip()])
    canonical_script_paths = sorted({path for path in manifest_script_paths if (BASE_DIR / path).is_file()})
    if canonical_script_paths:
      script_index = pd.DataFrame({
        "script": canonical_script_paths,
        "size_kB": [round((BASE_DIR / rel).stat().st_size / 1024, 1) for rel in canonical_script_paths],
      })
      show_table(script_index, "final_manifest_script_index", height=360)
      selected_script = st.selectbox(
        txt("Selecionar script para visualizar ou baixar", "Select a script to view or download"),
        canonical_script_paths,
        key="final_manifest_script_selector",
      )
      selected_path = BASE_DIR / selected_script
      selected_bytes = selected_path.read_bytes()
      st.caption(f"`{selected_script}` — {len(selected_bytes):,} bytes")
      if selected_path.suffix.lower() in {".py", ".r", ".sh", ".md", ".txt", ".csv", ".yml", ".yaml"}:
        with st.expander(txt("Visualizar conteúdo", "View contents"), expanded=False):
          language = "python" if selected_path.suffix.lower() == ".py" else "bash" if selected_path.suffix.lower() == ".sh" else "text"
          st.code(selected_bytes.decode("utf-8", errors="replace")[:100000], language=language)
      st.download_button(
        txt("Baixar script selecionado", "Download selected script"),
        data=selected_bytes,
        file_name=selected_path.name,
        key="download_selected_final_script",
      )
    else:
      st.warning(txt("Nenhum script do manifesto foi localizado.", "No manifest-listed script was found."))

    load_complete_inventory = st.checkbox(
      txt("Carregar inventário técnico completo de scripts", "Load the complete technical script inventory"),
      value=False,
      key="load_complete_final_script_inventory",
      help=txt(
        "Esta opção percorre todos os diretórios de código e calcula SHA-256. Ative apenas quando precisar da auditoria completa.",
        "This option scans all code directories and calculates SHA-256. Enable it only when the full audit is needed.",
      ),
    )
    if load_complete_inventory:
      all_script_dirs = [BASE_DIR / "scripts", BASE_DIR / "src", BASE_DIR / "docs" / "code"]
      all_script_files = sorted(
        {
          fp
          for folder in all_script_dirs if folder.exists()
          for fp in folder.rglob("*")
          if fp.is_file() and fp.suffix.lower() in {".py", ".r", ".sh", ".md", ".txt", ".csv", ".yml", ".yaml"}
        },
        key=lambda fp: str(fp.relative_to(BASE_DIR)),
      )
      st.markdown("### " + txt("Inventário completo de scripts e métodos", "Complete script and method inventory"))
      all_script_index = pd.DataFrame({
        "file": [str(fp.relative_to(BASE_DIR)) for fp in all_script_files],
        "bytes": [fp.stat().st_size for fp in all_script_files],
        "sha256": [hashlib.sha256(fp.read_bytes()).hexdigest() for fp in all_script_files],
      })
      show_table(all_script_index, "final_figures_all_script_index", height=520)
      csv_button(all_script_index, "all_scripts_and_methods_manifest.csv", txt("Baixar manifesto completo", "Download complete manifest"))

  with tabs[3]:
    st.subheader("Methods and execution")
    if readme_path.exists():
      st.markdown(readme_path.read_text(encoding="utf-8", errors="replace"))
    st.markdown("### Quick execution")
    st.code("python -m pip install -r requirements.txt\nstreamlit run app.py", language="bash")
    st.markdown("### " + txt("Preparação dos diretórios antiSMASH", "antiSMASH directory preparation"))
    st.info(txt(
      "Coloque cada diretório antiSMASH já descompactado em `data/kegg_modules/mags/gbk_antismash/`. Os nomes podem conter `strict`, `orig`, `permissive`, `metawrap`, `repaired`, contadores de reparo ou marcadores como `(1)`; durante a leitura, o app normaliza esses nomes para `MAG.<número>`.",
      "Place each extracted antiSMASH directory under `data/kegg_modules/mags/gbk_antismash/`. Names may contain `strict`, `orig`, `permissive`, `metawrap`, `repaired`, repair counters or markers such as `(1)`; during loading, the app normalizes these names to `MAG.<number>`."
    ))
    execution_manifest_path = BASE_DIR / "data" / "script_execution_environment_manifest.csv"
    if execution_manifest_path.exists():
      st.markdown("### " + txt("Tabela de execução por script", "Per-script execution table"))
      execution_manifest = pd.read_csv(execution_manifest_path)
      show_table(execution_manifest, "final_script_execution_environment_manifest", height=520)
      csv_button(execution_manifest, "script_execution_environment_manifest.csv", txt("Baixar inputs, bibliotecas e ambientes", "Download inputs, libraries and environments"))
    st.markdown("### Validate the final figure database")
    st.code("bash scripts/final_publication_figures/run_all_portable.sh", language="bash")
    st.markdown("### Main final data inputs")
    st.markdown("""
- `data/resultado.cds.otu.tab` and `data/resultado.cds.tax.tab`: CDS Kaiju taxonomy for Figures 2–6 and related supplementary panels.
- `data/resultado.kaiju.fastq.otu.tab` and `data/resultado.kaiju.fastq.tax.tab`: assembly/FASTQ Kaiju taxonomy for supplementary ordination panels.
- `data/geral.xlsx`: general metrics used for Supplementary Figure 1, following the original `generate_plotsv4.py` variable list.
- `data/resultado.cds.otu.tab` and `data/Table_S1_general_statistics.csv`: rarefaction input for Supplementary Figure 2 and fixed-depth alpha-diversity input for Supplementary Figure 4 (32,999 CDS).
- `data/Fe.genes.iron.scaffolds2.txt`: FeGenie category counts for heatmap and boxplots.
- `data/Supplementary_table_8_final_restructured_filled.xlsx`: ST8/Atlas KO, iron, GTDB taxonomy and external iron-rich environment tables.
""")

  with tabs[4]:
    st.subheader("Statistical outputs")
    if final_stat_dir.exists():
      files = sorted([p for p in final_stat_dir.iterdir() if p.is_file()])
      for p in files:
        st.markdown(f"#### `{p.name}`")
        if p.suffix.lower() == ".csv":
          try:
            st.dataframe(arrow_safe_dataframe(pd.read_csv(p)), width="stretch", height=360, key=f"final_stat_dataframe_{safe_filename(p.name)}")
          except Exception as exc:
            st.warning(f"Could not preview {p.name}: {exc}")
        st.download_button("Download statistic file", data=p.read_bytes(), file_name=p.name, key=f"download_final_stat_{p.name}")


site_access_gate()
record_visit(st, app_version=APP_VERSION, database_version=DATABASE_VERSION, page="session_entry")
restore_persistent_runtime_state()
page_header()

def no_public_modules_tab() -> None:
  st.info(txt(
    "Nenhum módulo está habilitado para visualização pública neste momento. Um administrador pode reativar módulos individualmente no painel administrativo.",
    "No module is currently enabled for public viewing. An administrator can re-enable modules individually in the administrator panel.",
  ))


base_page_specs = [
  ("article_atlas", "🏠 " + txt("Atlas do artigo", "Article Atlas"), overview_tab),
  ("mags_genomes", "🧩 " + txt("MAGs e genomas", "MAGs & genomes"), mags_tab),
  ("kegg_modules", "🧭 " + txt("Módulos KEGG — MAGs e metagenomas", "KEGG Modules — MAGs & Metagenomes"), kegg_modules_tab),
  ("taxonomy", "🧫 " + txt("Perfis taxonômicos", "Taxonomic profiles"), taxonomy_tab),
  ("ko_biomarkers", "🧬 " + txt("Biomarcadores KO", "KO Biogeochemical Cycles Biomarkers"), markers_tab),
  ("iron_metals", "⛓️ " + txt("Ferro e metais", "Iron & metals"), iron_tab),
  ("differential_abundance", "📈 " + txt("Abundância diferencial", "Differential abundance"), differential_tab),
  ("iron_environment_comparison", "🌎 " + txt("Lagoas amazônicas vs outros ambientes ricos em ferro", "Amazonian Lateritic Lakes vs Other Iron-Rich Environments"), comparison_tab),
  ("img_functional", "🧾 " + txt("Anotações funcionais IMG/JGI", "IMG/JGI functional annotations"), functional_annotations_tab),
  ("st8_references", "📖 " + txt("Referências dos estudos ST8", "ST8 study references"), study_references_tab),
  ("code_reproducibility", "💻 " + txt("Códigos e reprodutibilidade", "Code & reproducibility"), code_reproducibility_tab),
  ("final_figures", "📊 " + txt("Figuras finais e scripts", "Final figures & scripts"), final_publication_figures_tab),
  ("methods_references", "📚 " + txt("Métodos e referências", "Methods & references"), references_methods_tab),
]
article_atlas_label = base_page_specs[0][1]
visibility_settings = load_app_settings()
hidden_module_ids = set(visibility_settings.get("hidden_modules", []) or [])
active_page_specs = base_page_specs if is_admin_authenticated() else [spec for spec in base_page_specs if spec[0] not in hidden_module_ids]
if not active_page_specs:
  active_page_specs = [("public_status", "ℹ️ " + txt("Módulos indisponíveis", "Modules unavailable"), no_public_modules_tab)]
base_page_options = [label for _, label, _ in active_page_specs]
page_handlers = {label: handler for _, label, handler in active_page_specs}
page_options = list(base_page_options)
if is_admin_authenticated():
  admin_visitor_label = "🌐 " + txt("Contador de visitas — admin", "Visitor counter — admin")
  page_options.insert(10, admin_visitor_label)
  page_handlers[admin_visitor_label] = visitor_analytics_tab

ui_state = load_persistent_ui_state()
default_page = ui_state.get("main_page", page_options[0])
default_index = page_options.index(default_page) if default_page in page_options else 0
st.markdown("### " + txt("Navegação principal", "Main navigation"))
selected_page = st.radio(
  txt("Módulo ativo", "Active module"),
  page_options,
  index=default_index,
  horizontal=True,
  key="main_navigation_choice",
  label_visibility="collapsed",
)
save_persistent_ui_state(main_page=selected_page, app_version=APP_VERSION, database_version=DATABASE_VERSION, program_version=PUBLIC_PROGRAM_VERSION)
st.divider()
page_handler = page_handlers.get(selected_page)
if page_handler is not None:
  page_handler()
if selected_page == article_atlas_label:
  contact_form_panel("global_contact", expanded=False)
visitor_counter_public_footer("bottom_public_counter")
