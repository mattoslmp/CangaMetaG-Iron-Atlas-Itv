from __future__ import annotations

import os
from pathlib import Path


def _runtime_root() -> Path:
  configured = os.environ.get('CANGAMETAG_RUNTIME_DIR', '').strip()
  if configured:
    return Path(configured).expanduser().resolve()
  if os.name == 'nt':
    base = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
  else:
    base = Path(os.environ.get('XDG_STATE_HOME', Path.home() / '.local' / 'state'))
  return base / 'CangaMetaG'


APP_STATE_DIR = _runtime_root() / 'state'
APP_CACHE_DIR = _runtime_root() / 'cache'
APP_CONFIG_DIR = _runtime_root() / 'config'
APP_DATA_DIR = _runtime_root() / 'data'


def ensure_runtime_layout(extra_paths=None) -> dict[str, str]:
  paths = [APP_STATE_DIR, APP_CACHE_DIR, APP_CONFIG_DIR, APP_DATA_DIR]
  paths.extend(list(extra_paths or []))
  for path in paths:
    Path(path).mkdir(parents=True, exist_ok=True)
  return runtime_summary()


def runtime_summary() -> dict[str, str]:
  return {
    'state': str(APP_STATE_DIR),
    'cache': str(APP_CACHE_DIR),
    'config': str(APP_CONFIG_DIR),
    'data': str(APP_DATA_DIR),
  }
