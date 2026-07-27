# Private Streamlit release validation report

## Repository and release state

```text
Repository: mattoslmp/CangaMetaG-IronMetagenomicAtlas
Visibility: private
Default branch: main
Preparation branch: release/private-streamlit-review
Streamlit deployment: not activated
Public application URL: unavailable
Databiomics page: unchanged
```

## Publication tree

- Source package preserved separately; no local original was overwritten.
- Publication tree: `988,240,776` bytes before the final manifest refresh.
- Included runtime/supporting files: `3,145` before the final manifest refresh.
- Explicitly excluded files: `12`.
- Newly required Git LFS files: `0`; no included individual file is 50 MiB or larger after the documented exclusions.
- Manuscripts, editorial supplements, the 251 MB TIFF, raw ZIP archives, credentials, virtual environments, caches and logs are excluded.

## Scientific and application checks

| Check | Result | Notes |
|---|---|---|
| Private-release secret/size audit | PASS | No committed secret file pattern and no ordinary file >=100 MiB |
| Python compilation | PASS | `app.py`, `src/`, and `scripts/` |
| Runtime import/workflow check | PASS | 22 Python files, 19 `src` imports, 157 symbols, representative scientific workflows |
| Functional annotation matrices | PASS | Table 6, Table 8 and combined KO/EC/PFAM sample counts validated |
| ST8 external and sediment subsets | PASS | 67 external records; 14 external sediment records; 87 combined columns |
| Taxonomy identifiers and ordination hover metadata | PASS | 20 publication sample IDs retained; IMG/JGI identifiers kept as metadata |
| KEGG/KEMET module controls | PASS | 448 modules for 47 MAGs and 20 metagenomes; dynamic row-count control validated |
| Streamlit width/Arrow compatibility source checks | PASS | Deprecated `use_container_width` absent from `app.py`; mixed columns normalized |
| Headless navigation | PASS | 14/14 pages |
| Bash syntax for private publication script | PASS | `bash -n scripts/publish_repository.sh` |

## Environment details

- Validated deployment target: Python 3.12 (`.python-version`).
- Offline validation interpreter: Python 3.13.5.
- Highest observed memory among offline validation commands: approximately 397 MiB.
- The shared build environment does not contain Streamlit; the runtime checker therefore reported a warning rather than launching a real server.
- A clean dependency installation could not be completed in this environment because its restricted package mirror did not provide `streamlit==1.60.0`. The version remains pinned in `requirements.txt` for validation on the authenticated deployment machine.
- `python -m pip check` in the shared environment reported an unrelated pre-existing `moviepy`/`Pillow` conflict. `moviepy` is not a project dependency and will not be installed by the project requirements.

## Security and portability

- No absolute `/mnt`, `/home`, Windows user-profile, or macOS user path was found in executable application code.
- `.streamlit/secrets.toml`, `.env`, private keys and credential files are excluded.
- `.streamlit/secrets.example.toml` contains fictional placeholders only.
- Runtime user state is stored outside the repository through `src/runtime_paths.py`.
- The publication workflow never uses `git push --force`, `git reset --hard`, or `git clean -fdx`.
- The safe publication script copies only manifest-listed files and does not use `rsync --delete`.

## Files and manifests

- `deployment/runtime_files_manifest.tsv`
- `deployment/excluded_files_manifest.tsv`
- `deployment/git_lfs_manifest.tsv`
- `deployment/publication_tree_summary.tsv`
- `deployment/PRIVATE_COLLABORATOR_REVIEW.md`
- `deployment/FUTURE_DATABIOMICS_INTEGRATION.md`
- `STREAMLIT_DEPLOYMENT.md`
- `.streamlit/secrets.example.toml`
- `scripts/audit_private_release.py`
- `scripts/publish_repository.sh`

## Merge gate

Do not merge the preparation branch until the complete manifest-listed tree has been pushed from an authenticated machine, `git lfs fsck` (if applicable) passes, the private pull-request diff is reviewed, and the application is launched in a clean Python 3.12 environment.
