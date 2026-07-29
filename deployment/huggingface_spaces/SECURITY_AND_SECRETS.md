# Security and secrets

Never commit tokens, passwords, `.env`, private keys, credential JSON, browser cookies, `.streamlit/secrets.toml` or local administrator state.

Use Space Settings for secrets. Safe placeholders are:

```text
HF_TOKEN
HF_USERNAME
HF_SPACE_NAME
CANGAMETAG_ADMIN_USER
CANGAMETAG_ADMIN_PASSWORD
```

The upload utility requires `HF_TOKEN` in the current process environment. It refuses an empty token and does not print the token. The package-preparation utility excludes common secret and cache paths. Review its manifest before every upload.

Public Spaces expose repository files. Use private or protected visibility when source/data licensing or privacy requires it. Store persistent or private datasets in an appropriate private Hub repository or mounted storage and grant only the access required by the Space.
