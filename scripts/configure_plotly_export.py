#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.plotly_export import configure_browser_environment, discover_browser


def main() -> int:
  parser = argparse.ArgumentParser(description="Detect and configure Chrome/Chromium for Plotly static exports.")
  parser.add_argument("--print-shell", action="store_true", help="Print export commands for the detected browser.")
  args = parser.parse_args()
  browser = configure_browser_environment()
  if not browser:
    print("Chrome/Chromium was not found.", file=sys.stderr)
    print("Install one of: google-chrome, google-chrome-stable, chromium, chromium-browser", file=sys.stderr)
    print("Then set PLOTLY_CHROME_PATH=/absolute/path/to/browser if automatic detection still fails.", file=sys.stderr)
    return 1
  print(f"Detected browser: {browser}")
  print("Kaleido will use BROWSER_PATH/CHROME_PATH; the application also has a Playwright Chromium fallback.")
  if args.print_shell:
    print(f"export PLOTLY_CHROME_PATH={browser!r}")
    print(f"export BROWSER_PATH={browser!r}")
    print(f"export CHROME_PATH={browser!r}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
