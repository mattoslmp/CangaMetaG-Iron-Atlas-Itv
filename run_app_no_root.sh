#!/usr/bin/env bash
set -Eeuo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ORIGINAL_HOME="${HOME:?HOME is not defined}"
USER_ID="${UID:-$(id -u)}"
APP_SLUG="cangametag_atlas_v6"

choose_writable_dir() {
  local requested="$1"
  local fallback="$2"
  local emergency="/tmp/${APP_SLUG}-${USER_ID}"
  if mkdir -p "$requested" 2>/dev/null && [[ -w "$requested" ]]; then printf '%s\n' "$requested"; return 0; fi
  if mkdir -p "$fallback" 2>/dev/null && [[ -w "$fallback" ]]; then printf '%s\n' "$fallback"; return 0; fi
  mkdir -p "$emergency"
  chmod 700 "$emergency" 2>/dev/null || true
  printf '%s\n' "$emergency"
}

STATE_REQUESTED="${CANGAMETAG_STATE_DIR:-${XDG_STATE_HOME:-$ORIGINAL_HOME/.local/state}/${APP_SLUG}}"
CACHE_REQUESTED="${CANGAMETAG_CACHE_DIR:-${XDG_CACHE_HOME:-$ORIGINAL_HOME/.cache}/${APP_SLUG}}"
DATA_REQUESTED="${CANGAMETAG_DATA_DIR:-${XDG_DATA_HOME:-$ORIGINAL_HOME/.local/share}/${APP_SLUG}}"
CONFIG_REQUESTED="${CANGAMETAG_CONFIG_DIR:-${XDG_CONFIG_HOME:-$ORIGINAL_HOME/.config}/${APP_SLUG}}"

export CANGAMETAG_STATE_DIR="$(choose_writable_dir "$STATE_REQUESTED" "$ORIGINAL_HOME/.local/state/${APP_SLUG}")"
export CANGAMETAG_CACHE_DIR="$(choose_writable_dir "$CACHE_REQUESTED" "$ORIGINAL_HOME/.cache/${APP_SLUG}")"
export CANGAMETAG_DATA_DIR="$(choose_writable_dir "$DATA_REQUESTED" "$ORIGINAL_HOME/.local/share/${APP_SLUG}")"
export CANGAMETAG_CONFIG_DIR="$(choose_writable_dir "$CONFIG_REQUESTED" "$ORIGINAL_HOME/.config/${APP_SLUG}")"
export CANGAMETAG_DOWNLOAD_DIR="$(choose_writable_dir "${CANGAMETAG_DOWNLOAD_DIR:-$CANGAMETAG_DATA_DIR/downloads}" "$ORIGINAL_HOME/.local/share/${APP_SLUG}/downloads")"

RUNTIME_CANDIDATE="${CANGAMETAG_STREAMLIT_WORK_DIR:-${XDG_RUNTIME_DIR:-/tmp}/${APP_SLUG}_streamlit_${USER_ID}}"
RUNTIME_ROOT="$(choose_writable_dir "$RUNTIME_CANDIDATE" "/tmp/${APP_SLUG}_streamlit_${USER_ID}")"
WORK_DIR="$RUNTIME_ROOT/work"
SHADOW_HOME="$RUNTIME_ROOT/home"
mkdir -p "$WORK_DIR" "$SHADOW_HOME"
chmod 700 "$RUNTIME_ROOT" "$WORK_DIR" "$SHADOW_HOME" 2>/dev/null || true

export CANGAMETAG_PROJECT_DIR="$APP_DIR"
export CANGAMETAG_ORIGINAL_HOME="$ORIGINAL_HOME"
export PYTHONPATH="$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
export HOME="$SHADOW_HOME"
export TMPDIR="$(choose_writable_dir "$RUNTIME_ROOT/tmp" "/tmp/${APP_SLUG}-${USER_ID}/tmp")"
export MPLCONFIGDIR="$(choose_writable_dir "$CANGAMETAG_CACHE_DIR/matplotlib" "/tmp/${APP_SLUG}-${USER_ID}/matplotlib")"
export NUMBA_CACHE_DIR="$(choose_writable_dir "$CANGAMETAG_CACHE_DIR/numba" "/tmp/${APP_SLUG}-${USER_ID}/numba")"
export JOBLIB_TEMP_FOLDER="$(choose_writable_dir "$CANGAMETAG_CACHE_DIR/joblib" "/tmp/${APP_SLUG}-${USER_ID}/joblib")"
if [[ -r "$ORIGINAL_HOME/.netrc" ]]; then export NETRC="$ORIGINAL_HOME/.netrc"; fi

export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
export STREAMLIT_CLIENT_TOOLBAR_MODE=minimal
export STREAMLIT_CLIENT_SHOW_ERROR_DETAILS=false
export STREAMLIT_THEME_PRIMARY_COLOR="#008A83"
export STREAMLIT_THEME_BACKGROUND_COLOR="#FFFFFF"
export STREAMLIT_THEME_SECONDARY_BACKGROUND_COLOR="#F5FAF9"
export STREAMLIT_THEME_TEXT_COLOR="#3F444A"
export STREAMLIT_THEME_FONT="sans serif"
unset STREAMLIT_SECRETS_FILES STREAMLIT_SECRETS_FILE 2>/dev/null || true

BOOTSTRAP="$WORK_DIR/cangametag_streamlit_bootstrap.py"
cat > "$BOOTSTRAP" <<'PYBOOT'
from __future__ import annotations
import os
import runpy
import sys
app_dir = os.environ["CANGAMETAG_PROJECT_DIR"]
if app_dir not in sys.path:
    sys.path.insert(0, app_dir)
runpy.run_path(os.path.join(app_dir, "app.py"), run_name="__main__")
PYBOOT
chmod 600 "$BOOTSTRAP" 2>/dev/null || true

cd "$WORK_DIR"
exec python -m streamlit run "$BOOTSTRAP" \
  --server.port "${CANGAMETAG_PORT:-8502}" \
  --server.address "${CANGAMETAG_ADDRESS:-0.0.0.0}" \
  --server.headless true \
  --browser.gatherUsageStats false \
  --client.toolbarMode minimal \
  --client.showErrorDetails false \
  "$@"
