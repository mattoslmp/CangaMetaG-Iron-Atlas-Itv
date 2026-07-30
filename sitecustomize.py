"""Regenerate the packaged atlas workflow image when the app environment starts.

The source figure remains reproducible in scripts/generate_atlas_workflow_figure.py.
Failures are intentionally ignored during dependency installation, when
matplotlib may not yet be available.
"""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _regenerate_atlas_workflow() -> None:
  root = Path(__file__).resolve().parent
  script = root / "scripts" / "generate_atlas_workflow_figure.py"
  if not script.exists():
    return

  spec = spec_from_file_location("cangametag_workflow_figure", script)
  if spec is None or spec.loader is None:
    return

  module = module_from_spec(spec)
  spec.loader.exec_module(module)
  figure = module.build_figure()
  module.save_figure(figure)

  try:
    import matplotlib.pyplot as plt

    plt.close(figure)
  except Exception:
    pass


try:
  _regenerate_atlas_workflow()
except Exception:
  # During package installation, plotting dependencies may not yet exist.
  # The Streamlit runtime starts a fresh Python process after installation.
  pass
