# Plotly static exports: PNG, SVG and PDF

The application exports Plotly figures through two reproducible backends:

1. **Kaleido** (`kaleido>=1,<2`) using a detected Chrome/Chromium executable.
2. **Chromium + Playwright fallback** when Kaleido is unavailable or fails.

## Required Python packages

```bash
pip install -r requirements.txt
```

The requirements include both `kaleido` and `playwright`.

## Required system browser

Install one of:

```text
google-chrome
google-chrome-stable
chromium
chromium-browser
```

For Debian/Ubuntu environments:

```bash
sudo apt-get update
sudo apt-get install -y chromium fonts-liberation
```

Streamlit Community Cloud reads the included `packages.txt` and installs Chromium automatically.

## Automatic detection

Run:

```bash
python scripts/configure_plotly_export.py --print-shell
```

The application searches common executable names and paths. To override detection:

```bash
export PLOTLY_CHROME_PATH=/absolute/path/to/chromium
```

The same path is propagated to `BROWSER_PATH` and `CHROME_PATH` for Kaleido compatibility.

## Validation

Run:

```bash
python scripts/validate_plotly_exports.py
```

The validator generates one real PNG, SVG and PDF, verifies signatures, non-zero size, labels, title, dimensions and browser/backend availability.
