# Deployment checklist

- [ ] Local app starts and health endpoint responds.
- [ ] `prepare_space_package.py` completes without errors.
- [ ] `SPACE_FILE_MANIFEST_SHA256.csv` reviewed.
- [ ] No `.env`, token, password, private key or `.streamlit/secrets.toml` present.
- [ ] Docker Space selected; `app_port: 7860` present.
- [ ] Docker image builds.
- [ ] App binds to `0.0.0.0:7860`.
- [ ] Required variables/secrets configured in Space settings.
- [ ] S6/S37/S38/S40/S67 outputs inspected.
- [ ] Integral module heatmaps scroll/zoom correctly.
- [ ] Complete source matrices remain downloadable.
- [ ] Space restarted and revalidated.
- [ ] Final commit/revision recorded in the release audit.
