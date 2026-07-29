from __future__ import annotations

import importlib.util


def streamlit_dependency_guard(st) -> None:
  """Validate optional runtime packages without aborting a usable installation.

  The function intentionally avoids importing project modules. It reports only
  genuinely missing optional packages and allows Streamlit to continue.
  """
  optional = {
    'openpyxl': 'Excel previews',
    'Bio': 'FASTA/GenBank parsing',
    'statsmodels': 'some statistical summaries',
  }
  missing = [label for module, label in optional.items() if importlib.util.find_spec(module) is None]
  if missing:
    try:
      st.warning('Optional components unavailable: ' + ', '.join(missing))
    except Exception:
      pass
