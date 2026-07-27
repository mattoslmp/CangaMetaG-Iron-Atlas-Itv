# Future Streamlit Community Cloud deployment

## Current state

```text
GitHub repository: private
Repository status: private review
Streamlit application: not activated
Databiomics page: not published
Public application URL: unavailable
```

No deployment or public link is created by this document.

## Deployment coordinates

```text
GitHub account: mattoslmp
Repository: mattoslmp/CangaMetaG-IronMetagenomicAtlas
Branch: main
Main file path: app.py
Suggested subdomain: cangametag-iron-atlas
Alternative subdomain: cangametag-iron-metagenomic-atlas
Validated Python target: 3.12
```

## Runtime dependencies

Python dependencies are listed in `requirements.txt`. No Linux package is currently required by the app runtime itself; publication-only tools such as Git, Git LFS, rsync, LibreOffice and ImageMagick are intentionally not listed in `packages.txt`.

## Optional environment variables and Secrets

Configure only the variables needed for enabled optional integrations:

```text
CANGAMETAG_ADMIN_USER
CANGAMETAG_ADMIN_PASSWORD
CANGAMETAG_RUNTIME_DIR
COPERNICUS_CLIENT_ID
COPERNICUS_CLIENT_SECRET
EARTHDATA_TOKEN
EARTHDATA_USERNAME
EARTHDATA_PASSWORD
SMTP_HOST
SMTP_PORT
SMTP_USER
SMTP_PASSWORD
SMTP_FROM
SMTP_TO
```

Use `.streamlit/secrets.example.toml` as a names-only template. Never commit `.streamlit/secrets.toml` or `.env`.

## Private activation steps for a future authorized review

1. Sign in to Streamlit Community Cloud with the GitHub account `mattoslmp`.
2. Authorize access to the private repository only when institutional review permits it.
3. Select `mattoslmp/CangaMetaG-IronMetagenomicAtlas`.
4. Select branch `main`.
5. Set the main file path to `app.py`.
6. Add only the required Secrets in the Streamlit Secrets panel.
7. Deploy first as a private review app and test all pages, filters, downloads, light/dark themes and memory usage.
8. Share private access individually; do not create a public link during private review.

## Future public activation

Public release must wait for the responsible researchers' decision, appropriate institutional authorization, article-release policy and an actual Streamlit URL. Only then should a public Databiomics integration be considered.

## Git LFS

Clone with Git LFS installed if a future release introduces required LFS assets:

```bash
git lfs install
git clone git@github.com:mattoslmp/CangaMetaG-IronMetagenomicAtlas.git
git lfs pull
git lfs fsck
```

The current private-review manifest records no newly included file above the configured LFS threshold.

## Research provenance

This application and its study-specific results were developed by Leandro de Mattos Pereira during his postdoctoral research at Instituto Tecnológico Vale (ITV), under the supervision of Dr. Gisele Lopes Nunes. This statement does not imply commercial endorsement or public-release authorization.
