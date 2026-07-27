#!/usr/bin/env bash
set -euo pipefail

EXPECTED_REPO="mattoslmp/CangaMetaG-IronMetagenomicAtlas"
EXPECTED_REMOTE="git@github.com:${EXPECTED_REPO}.git"
SOURCE_ROOT="${SOURCE_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
BRANCH="${BRANCH:-release/private-streamlit-review}"
WORKDIR="${WORKDIR:-$(mktemp -d -t cangametag-private-release-XXXXXX)}"
KEEP_WORKDIR="${KEEP_WORKDIR:-0}"

cleanup() {
  if [[ "$KEEP_WORKDIR" != "1" ]]; then rm -rf "$WORKDIR"; else echo "Preserved workdir: $WORKDIR"; fi
}
trap cleanup EXIT

for command in git git-lfs gh python3; do
  command -v "$command" >/dev/null || { echo "ERROR: required command not found: $command" >&2; exit 1; }
done

gh auth status
git lfs install
visibility="$(gh repo view "$EXPECTED_REPO" --json visibility --jq '.visibility')"
default_branch="$(gh repo view "$EXPECTED_REPO" --json defaultBranchRef --jq '.defaultBranchRef.name')"
[[ "$visibility" == "PRIVATE" ]] || { echo "ERROR: repository is not private" >&2; exit 1; }
[[ "$default_branch" == "main" ]] || { echo "ERROR: unexpected default branch: $default_branch" >&2; exit 1; }
python3 "$SOURCE_ROOT/scripts/audit_private_release.py" --root "$SOURCE_ROOT"

git clone "$EXPECTED_REMOTE" "$WORKDIR/repository"
cd "$WORKDIR/repository"
git remote -v
git fetch origin --prune
if git show-ref --verify --quiet "refs/remotes/origin/$BRANCH"; then
  git switch -c "$BRANCH" --track "origin/$BRANCH"
else
  git switch -c "$BRANCH" "origin/main"
fi
base="$(git merge-base HEAD origin/main)"
[[ -n "$base" ]] || { echo "ERROR: no merge base with origin/main" >&2; exit 1; }

manifest="$SOURCE_ROOT/deployment/runtime_files_manifest.tsv"
[[ -f "$manifest" ]] || { echo "ERROR: runtime manifest missing" >&2; exit 1; }
mkdir -p "$WORKDIR/backup"
git ls-tree -r --long HEAD > "$WORKDIR/backup/remote_tree_before.tsv"
sha256sum "$WORKDIR/backup/remote_tree_before.tsv" > "$WORKDIR/backup/remote_tree_before.tsv.sha256"

python3 - "$SOURCE_ROOT" "$manifest" "$WORKDIR/repository" <<'__COPY_MANIFEST_PY__'
from pathlib import Path
import csv, shutil, sys
source = Path(sys.argv[1]).resolve(); manifest = Path(sys.argv[2]).resolve(); dest = Path(sys.argv[3]).resolve()
included=[]
with manifest.open(newline='', encoding='utf-8') as handle:
    for row in csv.DictReader(handle, delimiter='\t'):
        if row['storage_method'] not in {'regular_git','git_lfs'}: continue
        rel=Path(row['path']); src=source/rel
        if not src.is_file(): raise SystemExit(f'Missing required file: {rel}')
        target=dest/rel; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src,target); included.append(str(rel))
print(f'Copied {len(included)} manifest-listed files without deleting remote files.')
__COPY_MANIFEST_PY__

# The manifest files describe the publication set and are copied explicitly
# because a manifest cannot contain a stable SHA-256 record for itself.
mkdir -p deployment
cp -f "$SOURCE_ROOT/deployment/runtime_files_manifest.tsv" deployment/
cp -f "$SOURCE_ROOT/deployment/excluded_files_manifest.tsv" deployment/
cp -f "$SOURCE_ROOT/deployment/git_lfs_manifest.tsv" deployment/
cp -f "$SOURCE_ROOT/deployment/publication_tree_summary.tsv" deployment/

while IFS=$'\t' read -r path size sha file_type purpose referenced_by storage startup runtime; do
  [[ "$path" == "path" ]] && continue
  [[ "$storage" == "git_lfs" ]] && git lfs track "$path"
done < "$SOURCE_ROOT/deployment/runtime_files_manifest.tsv"
python3 "$SOURCE_ROOT/scripts/audit_private_release.py" --root "$WORKDIR/repository"
git status --short
git lfs status

commit_group() { local message="$1"; shift; git add -- "$@" 2>/dev/null || true; if ! git diff --cached --quiet; then git commit -m "$message"; fi; }
commit_group "Add validated Streamlit application and dependencies" app.py src requirements.txt .python-version run_app.py run_app_no_root.sh run_app_windows.bat
commit_group "Harden portability and private-review security" .gitignore .gitattributes .streamlit scripts/audit_private_release.py scripts/publish_repository.sh
commit_group "Add runtime data, figures, tables and storage manifests" data outputs tables database reproducibility deployment/runtime_files_manifest.tsv deployment/excluded_files_manifest.tsv deployment/git_lfs_manifest.tsv
commit_group "Add institutional research provenance" README.md
commit_group "Document future private Streamlit deployment" STREAMLIT_DEPLOYMENT.md deployment/PRIVATE_COLLABORATOR_REVIEW.md deployment/FUTURE_DATABIOMICS_INTEGRATION.md
commit_group "Add validation reports and reproducibility documentation" scripts validation deployment/deployment_validation_report.md docs Final_Figures_and_Scripts Checksums *.md *.txt *.json *.csv

if git status --porcelain | grep -q .; then echo "ERROR: uncommitted publication changes remain:" >&2; git status --short >&2; exit 1; fi
python -m compileall -q app.py src scripts
python -m pip check
python scripts/check_app_runtime.py
python scripts/validate_app_content.py
python scripts/headless_navigation_test.py
git lfs fsck
git push -u origin "$BRANCH"
existing_pr="$(gh pr list --repo "$EXPECTED_REPO" --head "$BRANCH" --base main --state open --json number --jq '.[0].number // empty')"
if [[ -n "$existing_pr" ]]; then
  echo "Existing private pull request: #$existing_pr"
  gh pr view "$existing_pr" --repo "$EXPECTED_REPO" --json number,title,state,isDraft,url
else
  gh pr create --repo "$EXPECTED_REPO" --base main --head "$BRANCH" --draft --title "Prepare private Streamlit review release" --body-file deployment/PRIVATE_RELEASE_PR_BODY.md
fi
