# Deploy CangaMetaG to Hugging Face Spaces

Hugging Face deprecated Streamlit as a default built-in Space SDK on 30 April 2025. The reproducible route for this application is therefore a **Docker Space** running Streamlit on port `7860`.

Official references:

- https://huggingface.co/docs/hub/en/spaces-sdks-docker
- https://huggingface.co/docs/hub/en/spaces-changelog
- https://huggingface.co/docs/huggingface_hub/en/guides/upload
- https://huggingface.co/docs/huggingface_hub/en/guides/manage-spaces

## 1. Test locally

From the application root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run app.py --server.address 127.0.0.1 --server.port 8502 --server.headless true
```

Open `http://127.0.0.1:8502` and inspect the KEGG module views, downloads and all pages used by the Space.

## 2. Prepare a Space package

```bash
python deployment/huggingface_spaces/prepare_space_package.py \
  --app-root . \
  --output-dir build/huggingface_space
```

The preparation script copies the executable code and permitted assets, creates a Docker Space `README.md`, creates a `Dockerfile`, excludes secrets/runtime caches and records SHA-256 checksums. Inspect `build/huggingface_space/SPACE_FILE_MANIFEST_SHA256.csv` before upload.

## 3. Create the Space in the web interface

1. Sign in to Hugging Face.
2. Choose **New Space**.
3. Set `HF_SPACE_NAME`, visibility and license.
4. Select **Docker** as the SDK.
5. Upload the prepared directory through the Files interface, or use Git/API as below.
6. In **Settings → Variables and secrets**, add only the values required by your deployment.

For this app, optional administrator variables are:

```text
CANGAMETAG_ADMIN_USER
CANGAMETAG_ADMIN_PASSWORD
```

Never commit their values.

## 4. Upload with Git

```bash
git lfs install
git clone https://huggingface.co/spaces/HF_USERNAME/HF_SPACE_NAME
rsync -a --delete build/huggingface_space/ HF_SPACE_NAME/
cd HF_SPACE_NAME
git add -A
git commit -m "Deploy validated CangaMetaG app"
git push
```

Use Git LFS or Hub/Xet storage for files that should not be stored as ordinary Git blobs. Do not upload the multipart delivery archives unless that is intentional; the Space normally needs the reconstructed executable files.

## 5. Upload with `huggingface_hub`

```bash
python -m pip install --upgrade huggingface_hub hf_xet
export HF_TOKEN='your-write-token-in-the-shell-only'
export HF_USERNAME='your-user-or-organization'
export HF_SPACE_NAME='your-space-name'
python deployment/huggingface_spaces/upload_to_huggingface.py \
  --folder build/huggingface_space
```

The token is read from `HF_TOKEN`; it is never written to the package.

## 6. Large files and multipart archives

The final delivery archives can be reconstructed outside the Space with the scripts in `reconstruction/`. Verify SHA-256 and `unzip -t` before extracting. For Space runtime data, prefer Hub repositories/Xet, Git LFS or mounted storage rather than reconstructing multi-gigabyte archives on every restart.

## 7. Validate after publication

- Build status is green.
- The app responds on port `7860`.
- No secret appears in logs or repository files.
- Static and interactive module heatmaps show only `Complete` and `1 block missing` calls; other calls are blank.
- Integral heatmaps can be scrolled/zoomed.
- Downloads return the complete source matrices.
- Restart the Space once and repeat the checks.

## 8. Troubleshooting

- **Build fails during pip install:** inspect the build log, pin the package named in the error, rebuild.
- **App does not bind:** the Docker command must use `--server.address 0.0.0.0 --server.port 7860`.
- **Out of memory:** reduce simultaneous data loading or select upgraded hardware; do not alter scientific matrices merely to fit the screen.
- **Missing file:** compare against `SPACE_FILE_MANIFEST_SHA256.csv` and rerun the preparation script.
- **Secret missing:** configure it in Space settings; never add `.env` or `.streamlit/secrets.toml` to Git.
- **Update an existing Space:** prepare a fresh deterministic folder, review the manifest/diff, then upload or push a new commit.
