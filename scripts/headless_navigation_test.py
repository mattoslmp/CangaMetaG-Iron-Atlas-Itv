#!/usr/bin/env python3
"""Execute every Streamlit page with an offline no-op UI shim.

This is not a visual browser test. It exercises page code, local data loading,
filter defaults, and chart/table construction without starting a server or
contacting external APIs.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import traceback
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGE_IDS = [
  "article_atlas", "mags_genomes", "kegg_modules", "taxonomy", "ko_biomarkers",
  "iron_metals", "differential_abundance", "iron_environment_comparison",
  "img_functional", "st8_references", "environment_integrator",
  "code_reproducibility", "final_figures", "methods_references",
]


class SessionState(dict):
  def __getattr__(self, name):
    try:
      return self[name]
    except KeyError as exc:
      raise AttributeError(name) from exc

  def __setattr__(self, name, value):
    self[name] = value


class StopExecution(Exception):
  pass


class FakeBlock:
  def __init__(self, st):
    self._st = st

  def __enter__(self):
    return self

  def __exit__(self, exc_type, exc, tb):
    return False

  def __getattr__(self, name):
    return getattr(self._st, name)


class FakeProgress(FakeBlock):
  def progress(self, *args, **kwargs):
    return self

  def empty(self):
    return None


class ColumnConfig:
  class LinkColumn:
    def __init__(self, *args, **kwargs):
      pass

  class TextColumn:
    def __init__(self, *args, **kwargs):
      pass

  class NumberColumn:
    def __init__(self, *args, **kwargs):
      pass

  class CheckboxColumn:
    def __init__(self, *args, **kwargs):
      pass


class FakeStreamlit(types.ModuleType):
  def __init__(self, page_index: int):
    super().__init__("streamlit")
    self.page_index = page_index
    self.session_state = SessionState()
    self.secrets = {}
    self.column_config = ColumnConfig()
    self.sidebar = FakeBlock(self)
    self.__version__ = "1.60.0"

  def cache_data(self, func=None, **kwargs):
    if func is None:
      return lambda target: target
    return func

  cache_resource = cache_data

  def set_page_config(self, *args, **kwargs):
    return None

  def columns(self, spec, *args, **kwargs):
    count = spec if isinstance(spec, int) else len(spec)
    return [FakeBlock(self) for _ in range(count)]

  def tabs(self, labels):
    return [FakeBlock(self) for _ in labels]

  def container(self, *args, **kwargs):
    return FakeBlock(self)

  def expander(self, *args, **kwargs):
    return FakeBlock(self)

  def form(self, *args, **kwargs):
    return FakeBlock(self)

  def spinner(self, *args, **kwargs):
    return FakeBlock(self)

  def empty(self):
    return FakeProgress(self)

  def progress(self, *args, **kwargs):
    return FakeProgress(self)

  def radio(self, label, options, index=0, key=None, **kwargs):
    values = list(options)
    if key == "main_navigation_choice":
      return values[min(self.page_index, len(values) - 1)]
    return values[index] if values else None

  def selectbox(self, label, options, index=0, **kwargs):
    values = list(options)
    return values[index] if values else None

  def multiselect(self, label, options, default=None, **kwargs):
    values = list(options)
    if default is None:
      return []
    return list(default) if not isinstance(default, str) else [default]

  def checkbox(self, label, value=False, **kwargs):
    return bool(value)

  def slider(self, label, min_value=None, max_value=None, value=None, **kwargs):
    return value if value is not None else min_value

  def select_slider(self, label, options=None, value=None, **kwargs):
    if value is not None:
      return value
    values = list(options or [])
    return values[0] if values else None

  def number_input(self, label, min_value=None, max_value=None, value=None, **kwargs):
    return value if value is not None else (min_value if min_value is not None else 0)

  def text_input(self, label, value="", **kwargs):
    return value

  def text_area(self, label, value="", **kwargs):
    return value

  def button(self, *args, **kwargs):
    return False

  def form_submit_button(self, *args, **kwargs):
    return False

  def download_button(self, *args, **kwargs):
    return False

  def link_button(self, *args, **kwargs):
    return False

  def stop(self):
    raise StopExecution()

  def rerun(self):
    return None

  def dataframe(self, *args, **kwargs):
    return None

  def table(self, *args, **kwargs):
    return None

  def plotly_chart(self, *args, **kwargs):
    return None

  def image(self, *args, **kwargs):
    return None

  def metric(self, *args, **kwargs):
    return None

  def __getattr__(self, name):
    if name.startswith("_"):
      raise AttributeError(name)
    return lambda *args, **kwargs: None


def run_one(page_index: int) -> int:
  fake = FakeStreamlit(page_index)
  components = types.ModuleType("streamlit.components")
  components_v1 = types.ModuleType("streamlit.components.v1")
  components_v1.html = lambda *args, **kwargs: None
  components.v1 = components_v1
  components.__path__ = []
  components_v1.__path__ = []
  fake.__path__ = []
  fake.components = components
  sys.modules["streamlit"] = fake
  sys.modules["streamlit.components"] = components
  sys.modules["streamlit.components.v1"] = components_v1
  os.environ.setdefault("CANGAMETAG_DISABLE_NETWORK", "1")
  os.chdir(ROOT)
  sys.path.insert(0, str(ROOT))
  try:
    code = compile((ROOT / "app.py").read_text(encoding="utf-8"), str(ROOT / "app.py"), "exec")
    namespace = {"__name__": "__main__", "__file__": str(ROOT / "app.py")}
    exec(code, namespace, namespace)
  except StopExecution:
    pass
  except Exception:
    traceback.print_exc()
    return 1
  return 0


def main() -> int:
  parser = argparse.ArgumentParser()
  parser.add_argument("--page-index", type=int)
  parser.add_argument("--workers", type=int, default=4)
  parser.add_argument("--timeout", type=int, default=240)
  args = parser.parse_args()
  if args.page_index is not None:
    return run_one(args.page_index)

  from concurrent.futures import ThreadPoolExecutor, as_completed
  import pandas as pd

  def execute(index: int, page_id: str):
    try:
      result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--page-index", str(index)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=args.timeout,
      )
      status = "PASS" if result.returncode == 0 else "FAIL"
      stderr = result.stderr[-4000:]
    except subprocess.TimeoutExpired as exc:
      status = "TIMEOUT"
      stderr = f"Page exceeded {args.timeout} seconds.\n{(exc.stderr or '')[-3500:]}"
    return page_id, status, stderr

  rows = []
  with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
    futures = {
      pool.submit(execute, index, page_id): page_id
      for index, page_id in enumerate(PAGE_IDS)
    }
    for future in as_completed(futures):
      row = future.result()
      rows.append(row)
      print(row[0], row[1], flush=True)

  order = {page_id: index for index, page_id in enumerate(PAGE_IDS)}
  rows.sort(key=lambda row: order[row[0]])
  out = pd.DataFrame(rows, columns=["page", "status", "stderr"])
  target = ROOT / "validation" / "APP_HEADLESS_NAVIGATION_TEST.tsv"
  out.to_csv(target, sep="\t", index=False)
  if (out["status"] != "PASS").any():
    print(out[out["status"] != "PASS"].to_string(index=False))
    return 1
  print("APP_HEADLESS_NAVIGATION_PASS")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
