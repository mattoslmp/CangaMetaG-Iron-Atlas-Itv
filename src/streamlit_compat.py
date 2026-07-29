from __future__ import annotations

"""Compatibility helpers for current Streamlit and PyArrow releases."""

import json
import numpy as np
import pandas as pd


def arrow_safe_dataframe(data) -> pd.DataFrame:
  """Return a display-only DataFrame that PyArrow can serialize reliably.

  Excel supplementary sheets may contain explanatory strings and numeric
  values in the same column. Numeric columns remain numeric; mixed object,
  category, and string columns are converted to nullable text. Nested values
  are JSON-encoded. The underlying source workbooks are never modified.
  """
  if isinstance(data, pd.DataFrame):
    df = data.copy()
  else:
    df = pd.DataFrame(data)
  seen: dict[str, int] = {}
  names: list[str] = []
  for raw in df.columns:
    name = str(raw)
    count = seen.get(name, 0)
    seen[name] = count + 1
    names.append(name if count == 0 else f"{name}__{count + 1}")
  df.columns = names

  def as_text(value):
    if value is None:
      return None
    try:
      if pd.isna(value):
        return None
    except Exception:
      pass
    if isinstance(value, bytes):
      return value.decode("utf-8", errors="replace")
    if isinstance(value, (dict, list, tuple, set)):
      try:
        return json.dumps(value, ensure_ascii=False, default=str)
      except Exception:
        return str(value)
    if isinstance(value, np.generic):
      value = value.item()
    return str(value)

  for col in df.columns:
    series = df[col]
    if pd.api.types.is_datetime64_any_dtype(series):
      df[col] = pd.to_datetime(series, errors="coerce")
    elif pd.api.types.is_bool_dtype(series):
      df[col] = series.astype("boolean")
    elif pd.api.types.is_numeric_dtype(series):
      df[col] = pd.to_numeric(series, errors="coerce")
    else:
      df[col] = series.map(as_text).astype("string")
  return df.reset_index(drop=True)
