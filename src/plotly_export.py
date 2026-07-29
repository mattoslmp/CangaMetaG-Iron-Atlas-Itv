from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import unquote_to_bytes
import base64

import plotly.graph_objects as go
from plotly.offline import get_plotlyjs

_BROWSER_NAMES = (
  "google-chrome",
  "google-chrome-stable",
  "chromium",
  "chromium-browser",
  "chrome",
)
_INVALID_TEXT = {"undefined", "none", "null", "nan", "na", "n/a"}


def discover_browser() -> str | None:
  """Find a Chrome/Chromium executable without requiring interactive setup."""
  for env_name in ("PLOTLY_CHROME_PATH", "BROWSER_PATH", "CHROME_PATH", "CHROMIUM_PATH"):
    candidate = os.environ.get(env_name, "").strip()
    if candidate and Path(candidate).is_file():
      return candidate
  for name in _BROWSER_NAMES:
    candidate = shutil.which(name)
    if candidate:
      return candidate
  common = (
    "/usr/bin/google-chrome",
    "/usr/bin/google-chrome-stable",
    "/usr/bin/chromium",
    "/usr/bin/chromium-browser",
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
  )
  for candidate in common:
    if Path(candidate).is_file():
      return candidate
  return None


def configure_browser_environment() -> str | None:
  """Expose the discovered browser to Kaleido and the browser fallback."""
  browser = discover_browser()
  if browser:
    os.environ.setdefault("BROWSER_PATH", browser)
    os.environ.setdefault("CHROME_PATH", browser)
    os.environ.setdefault("PLOTLY_CHROME_PATH", browser)
  return browser


def _iter_visible_text(fig: go.Figure) -> list[tuple[str, str]]:
  texts: list[tuple[str, str]] = []
  layout = fig.layout
  title = str(getattr(getattr(layout, "title", None), "text", "") or "").strip()
  if title:
    texts.append(("title", title))
  for axis_name in ("xaxis", "yaxis", "xaxis2", "yaxis2", "xaxis3", "yaxis3"):
    axis = getattr(layout, axis_name, None)
    axis_title = str(getattr(getattr(axis, "title", None), "text", "") or "").strip()
    if axis_title:
      texts.append((f"{axis_name} title", axis_title))
  legend_title = str(getattr(getattr(getattr(layout, "legend", None), "title", None), "text", "") or "").strip()
  if legend_title:
    texts.append(("legend title", legend_title))
  for index, trace in enumerate(fig.data):
    name = str(getattr(trace, "name", "") or "").strip()
    if name:
      texts.append((f"trace {index + 1} name", name))
  for index, annotation in enumerate(list(getattr(layout, "annotations", []) or [])):
    text = str(getattr(annotation, "text", "") or "").strip()
    if text:
      texts.append((f"annotation {index + 1}", text))
  return texts


def validate_visible_text(fig: go.Figure, *, require_title: bool = False) -> None:
  """Reject user-visible development placeholders before rendering/export."""
  title = str(getattr(getattr(fig.layout, "title", None), "text", "") or "").strip()
  if require_title and not title:
    raise ValueError("The figure title is empty.")
  bad: list[str] = []
  for location, text in _iter_visible_text(fig):
    normalised = text.strip().casefold()
    tokens = {token.strip(" :;,.()[]{}") for token in normalised.replace("=", " ").split()}
    if normalised in _INVALID_TEXT or tokens.intersection(_INVALID_TEXT):
      bad.append(f"{location}: {text!r}")
  if bad:
    raise ValueError("Invalid placeholder text detected: " + "; ".join(bad))


def _html_document(fig: go.Figure, width: int, height: int) -> str:
  figure_json = fig.to_json()
  plotly_js = get_plotlyjs().replace("</script>", "<\\/script>")
  return f"""<!doctype html>
<html><head><meta charset='utf-8'><script>{plotly_js}</script>
<style>html,body{{margin:0;padding:0;background:white;overflow:hidden}}#plot{{width:{width}px;height:{height}px}}</style></head>
<body><div id='plot'></div><script>
const f={figure_json};
f.layout=f.layout||{{}}; f.layout.width={width}; f.layout.height={height}; f.layout.autosize=false;
Plotly.newPlot('plot', f.data, f.layout, {{staticPlot:true,responsive:false,displayModeBar:false}})
.then(()=>{{window.__PLOT_READY__=true;}}).catch(e=>{{window.__PLOT_ERROR__=String(e);}});
</script></body></html>"""


def _browser_export(fig: go.Figure, fmt: str, width: int, height: int, scale: int) -> bytes:
  browser = configure_browser_environment()
  if not browser:
    raise RuntimeError(
      "Chrome/Chromium was not found. Set PLOTLY_CHROME_PATH or install google-chrome/chromium."
    )
  try:
    from playwright.sync_api import sync_playwright
  except Exception as exc:
    raise RuntimeError(
      "The browser fallback requires the Python package 'playwright'. Install it with: pip install playwright"
    ) from exc

  with tempfile.TemporaryDirectory(prefix="cangametag_plotly_export_") as tmp:
    html_path = Path(tmp) / "figure.html"
    html_text = _html_document(fig, width, height)
    html_path.write_text(html_text, encoding="utf-8")
    with sync_playwright() as manager:
      chromium = manager.chromium.launch(
        executable_path=browser,
        headless=True,
        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
      )
      page = chromium.new_page(
        viewport={"width": max(1, width), "height": max(1, height)},
        device_scale_factor=max(1, min(int(scale), 3)),
      )
      page.set_content(html_text, wait_until="load", timeout=90000)
      page.wait_for_function("window.__PLOT_READY__ === true || window.__PLOT_ERROR__", timeout=90000)
      error = page.evaluate("window.__PLOT_ERROR__ || ''")
      if error:
        raise RuntimeError(f"Plotly browser rendering failed: {error}")
      locator = page.locator("#plot")
      if fmt == "png":
        result = locator.screenshot(type="png")
      elif fmt == "pdf":
        result = page.pdf(
          width=f"{width}px", height=f"{height}px", print_background=True,
          margin={"top": "0", "right": "0", "bottom": "0", "left": "0"},
          prefer_css_page_size=False,
        )
      elif fmt == "svg":
        data_url = page.evaluate("""async ({width, height}) => {
          const node = document.getElementById('plot');
          if (!node) throw new Error('Plotly graph element was not found');
          return await Plotly.toImage(node, {format: 'svg', width, height});
        }""", {"width": width, "height": height})
        header, payload = str(data_url).split(',', 1)
        if ';base64' in header:
          result = base64.b64decode(payload)
        else:
          result = unquote_to_bytes(payload)
      else:
        raise ValueError(f"Unsupported browser export format: {fmt}")
      chromium.close()
  return result


def validate_export_bytes(data: bytes, fmt: str) -> None:
  if not data or len(data) < 100:
    raise RuntimeError(f"The {fmt.upper()} export is empty or too small.")
  fmt = fmt.lower()
  if fmt == "png" and not data.startswith(b"\x89PNG\r\n\x1a\n"):
    raise RuntimeError("Invalid PNG signature.")
  if fmt == "pdf" and not data.startswith(b"%PDF-"):
    raise RuntimeError("Invalid PDF signature.")
  if fmt == "svg":
    head = data[:1000].lower()
    if b"<svg" not in head:
      raise RuntimeError("Invalid SVG content.")


def export_plotly_bytes(
  fig: go.Figure,
  fmt: str,
  *,
  width: int,
  height: int,
  scale: int = 1,
) -> tuple[bytes, str]:
  """Export through Kaleido first and a local Chrome/Chromium fallback second."""
  fmt = str(fmt).lower()
  configure_browser_environment()
  kaleido_error: Exception | None = None
  try:
    data = fig.to_image(format=fmt, width=width, height=height, scale=scale)
    validate_export_bytes(data, fmt)
    return data, "kaleido"
  except Exception as exc:
    kaleido_error = exc
  try:
    data = _browser_export(fig, fmt, width, height, scale)
    validate_export_bytes(data, fmt)
    return data, "chromium-playwright"
  except Exception as fallback_error:
    raise RuntimeError(
      f"Kaleido export failed ({type(kaleido_error).__name__}: {kaleido_error}); "
      f"Chrome/Chromium fallback failed ({type(fallback_error).__name__}: {fallback_error}). "
      "Install dependencies with 'pip install kaleido playwright' and install Chrome/Chromium, "
      "or set PLOTLY_CHROME_PATH to the browser executable."
    ) from fallback_error
