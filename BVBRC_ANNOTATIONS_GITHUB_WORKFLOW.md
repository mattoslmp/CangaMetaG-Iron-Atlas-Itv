# Persistent BV-BRC annotations for Streamlit

The Streamlit Community Cloud filesystem is temporary. Files downloaded by the
running app into `Annotation/MAGx` are available only in that container and are
not committed back to GitHub. A reboot or redeployment may remove them.

For a reproducible public deployment, download the annotations in a local clone,
review them, and then push `Annotation/` to GitHub. This repository tracks
`Annotation/**` with Git LFS.

> **Data visibility:** if this repository is public, every committed annotation
> becomes public. Upload only data that are authorized for public distribution.

## 1. Update the local clone

```bash
cd /mnt/d/CangaMetaG-Iron-Atlas-Itv
git switch main
git pull --ff-only origin main
```

## 2. Install Git LFS and the BV-BRC CLI on Ubuntu/WSL

```bash
sudo apt-get update
sudo apt-get install -y git-lfs ca-certificates curl

git lfs install

curl -L -o /tmp/bvbrc-cli-1.040.deb \
  https://github.com/BV-BRC/BV-BRC-CLI/releases/download/1.040/bvbrc-cli-1.040.deb
sudo apt-get install -y /tmp/bvbrc-cli-1.040.deb
```

Confirm the commands:

```bash
command -v p3-login
command -v p3-ls
command -v p3-cp
```

## 3. Authenticate locally

```bash
p3-login mattoslmp
```

Enter the BV-BRC password only in the terminal. Never place it in Git,
`secrets.toml`, source code, screenshots, or command history.

Check access to the workspace:

```bash
p3-ls /mattoslmp@patricbrc.org/Lakes-Canga/metagenomas
```

## 4. Download MAG2 through MAG50

```bash
python scripts/prefetch_bvbrc_annotations.py \
  --start 2 \
  --end 50 \
  --workspace /mattoslmp@patricbrc.org/Lakes-Canga/metagenomas
```

The script writes:

- `Annotation/MAG2` through `Annotation/MAG50`;
- `Annotation/bvbrc_download_manifest.csv`;
- `Annotation/bvbrc_file_size_manifest.csv`.

It reuses complete local folders unless `--overwrite` is supplied.

## 5. Inspect completeness and size

```bash
du -sh Annotation
find Annotation -type f -size +50M -printf '%s %p\n' | sort -nr
find Annotation -type f -size +100M -printf '%s %p\n' | sort -nr

python - <<'PY'
from pathlib import Path
for number in range(2, 51):
  folder = Path('Annotation') / f'MAG{number}'
  files = sum(1 for path in folder.rglob('*') if path.is_file()) if folder.exists() else 0
  print(f'{folder.name}: {files} files')
PY
```

GitHub blocks ordinary Git files larger than 100 MiB. The included
`.gitattributes` routes all files under `Annotation/` through Git LFS.

## 6. Commit and push

```bash
git lfs track
git add .gitattributes Annotation BVBRC_ANNOTATIONS_GITHUB_WORKFLOW.md \
  scripts/prefetch_bvbrc_annotations.py

git status --short
git lfs status

git commit -m "Add persistent BV-BRC MAG annotations"
git push origin main
```

Verify that LFS objects were uploaded:

```bash
git lfs ls-files
```

## 7. Redeploy Streamlit

After the push, Streamlit Community Cloud will clone the repository and Git LFS
objects. The app checks `Annotation/MAGx` first and does not download a MAG again
when valid local files are already packaged with the deployment.

Use **Manage app → Reboot app** after the GitHub push if the deployment does not
restart automatically.

## When not to place the files in GitHub

If `Annotation/` is several gigabytes, changes frequently, or contains data that
must remain private, use private object storage or a private release/archive
instead of normal repository history. Keep only a manifest and download logic in
Git in that case.
