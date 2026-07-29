# Streamlit Community Cloud deployment

This package is configured to use the root `requirements.txt` and Python 3.12.
The former root Conda file was preserved under
`reproducibility/environment_conda.yml` so it does not take precedence over
`requirements.txt` during Community Cloud deployment.

## Repository settings

- Repository root: the directory containing `app.py`
- Main file path: `app.py`
- Python version: 3.12 (`.python-version`)
- Dependency file: `requirements.txt`
- Streamlit settings: `.streamlit/config.toml`

## Local pre-deployment test

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/check_app_runtime.py
python scripts/validate_app_content.py
python -m streamlit run app.py
```

## Data files

Keep the directory structure unchanged. The app resolves data relative to
`app.py`; do not upload only `app.py` without `src/`, `tables/`, `data/`,
`outputs/`, and `reproducibility/`.

For repositories with files above GitHub's normal blob limit, use Git LFS or
publish those immutable data files as a release/dataset and materialize them at
startup with checksums. Do not silently omit any Supplementary Table 6 or 8
matrix column.
