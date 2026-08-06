#!/usr/bin/env bash
set -uo pipefail

CURRENT_STEP="initialization"
FINAL_STATUS="failure"
APP_PID=""

write_status_and_commit() {
  local exit_code=$?
  if [[ -n "${APP_PID}" ]]; then
    kill "${APP_PID}" 2>/dev/null || true
  fi
  if [[ ${exit_code} -eq 0 ]]; then
    FINAL_STATUS="success"
  fi
  mkdir -p .github/validation
  FINAL_STATUS="${FINAL_STATUS}" CURRENT_STEP="${CURRENT_STEP}" python - <<'PY'
import json, os
from datetime import datetime, timezone
payload = {
  "executed_utc": datetime.now(timezone.utc).isoformat(),
  "status": os.environ.get("FINAL_STATUS", "failure"),
  "last_step": os.environ.get("CURRENT_STEP", "unknown"),
  "scientific_contracts": {
    "shared_phyla": 28,
    "core_families": 56,
    "shared_KOs": 126,
    "FeGenie_MAGs": 47,
    "FeGenie_categories": 9,
    "FeGenie_genes": 531,
    "antiSMASH_regions": 146,
    "antiSMASH_contextual_associations": 2,
  },
}
with open('.github/validation/final_article_results_status.json', 'w', encoding='utf-8') as handle:
  json.dump(payload, handle, indent=2)
PY
  git config user.name "github-actions[bot]"
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git add -- .github/validation/final_article_results_status.json
  if [[ "${FINAL_STATUS}" == "success" ]]; then
    rm -f data/final_integration_bundle_20260806.tar.gz.part-*
    git add -u -- data/final_integration_bundle_20260806.tar.gz.part-* || true
    git add -- \
      app.py \
      src/app_final_article_results_transform.py \
      src/final_article_results_runtime.py \
      src/figure_provenance.py \
      src/taxonomy_normalization.py \
      src/taxonomy_palette.py \
      scripts/export_final_article_source_tables.py \
      scripts/generate_core_microbiome_and_shared_functions.py \
      scripts/generate_shared_ko_heatmap.py \
      scripts/generate_mag_abundance_and_fegenie_figures.py \
      scripts/parse_antismash_bgc_metal_evidence.py \
      scripts/generate_ordinations_revision4.py \
      scripts/generate_final_domain_taxonomy_figures.py \
      scripts/generate_taxonomy_supplementary_figures.py \
      scripts/generate_s3_nmds_revision4.py \
      scripts/run_final_ci_validation.sh \
      tests/test_final_article_results_integration.py \
      data/final_taxonomy_palette_display.json \
      data/final_publication_derived/Bacteria_* \
      data/final_publication_derived/Archaea_* \
      data/final_publication_derived/CDS_NMDS_* \
      data/final_publication_derived/final_taxonomy_palette_resolved.json \
      outputs/final_publication_figures/Figure2_taxonomic_phylum_bacteria_horizontal_CDS.* \
      outputs/final_publication_figures/Figure3_taxonomic_phylum_archaea_horizontal_CDS.* \
      outputs/final_publication_figures/Figure4_taxonomic_bacteria_genus_profiles.* \
      outputs/final_publication_figures/Figure5_taxonomic_archaea_genus_profiles.* \
      outputs/final_publication_figures/SupplementaryFigure4_NMDS_CDS_taxonomy.* \
      outputs/app_main_figures/Figure2_taxonomic_phylum_bacteria_horizontal_CDS.* \
      outputs/app_main_figures/Figure3_taxonomic_phylum_archaea_horizontal_CDS.* \
      outputs/app_main_figures/Figure4_taxonomic_bacteria_genus_profiles.* \
      outputs/app_main_figures/Figure5_taxonomic_archaea_genus_profiles.* \
      outputs/app_supplementary_figures/SupplementaryFigure4_NMDS_CDS_taxonomy.* \
      07_Validation_and_Manifests/taxonomy_lt1_final/MAIN_TAXONOMY_STRICT_LT1_VALIDATION.json \
      reproducibility/ordination_reproducibility/output/CDS_true_nonmetric_NMDS_* \
      reproducibility/ordination_reproducibility/tables/CDS_NMDS_* \
      tables/st8_taxonomy_summary_by_group.csv \
      tables/st8_ko_amazonia_vs_groups.csv \
      tables/final_article_source_table_export_manifest.json \
      data/final_publication_derived/SupplementaryFigure38_core_taxa_shared_compartments_* \
      data/final_publication_derived/SupplementaryFigure39_shared_KO_heatmap_lagoons_metatranscriptomes_* \
      data/final_publication_derived/SupplementaryFigure40_FeGenie_iron_gene_categories_per_MAG_source.csv \
      data/antismash/antiSMASH_BGC_region_table.csv \
      data/antismash/antiSMASH_BGC_region_table_metal_evidence.csv \
      data/antismash/antiSMASH_metal_evidence_summary.csv \
      outputs/final_publication_figures/SupplementaryFigure38_core_taxa_shared_compartments_P*.* \
      outputs/final_publication_figures/SupplementaryFigure39_shared_KO_heatmap_lagoons_metatranscriptomes_P*.* \
      outputs/final_publication_figures/SupplementaryFigure40_FeGenie_iron_gene_categories_per_MAG_P*.* \
      outputs/antismash/SupplementaryFigure42_antiSMASH_BGC_iron_metal_evidence_P*.* \
      outputs/antismash/antiSMASH_BGC_region_table_metal_evidence.csv \
      outputs/antismash/antiSMASH_metal_evidence_summary.csv \
      outputs/app_supplementary_figures/SupplementaryFigure38_core_taxa_shared_compartments_P*.* \
      outputs/app_supplementary_figures/SupplementaryFigure39_shared_KO_heatmap_lagoons_metatranscriptomes_P*.* \
      outputs/app_supplementary_figures/SupplementaryFigure40_FeGenie_iron_gene_categories_per_MAG_P*.* \
      outputs/app_supplementary_figures/SupplementaryFigure42_antiSMASH_BGC_iron_metal_evidence_P*.* \
      12_Validation/CORE_MICROBIOME_AND_SHARED_FUNCTIONS_AUDIT.json \
      12_Validation/SHARED_KO_HEATMAP_AUDIT.json \
      12_Validation/antiSMASH_S42_validation.json
  fi
  if ! git diff --cached --quiet; then
    git commit -m "Record final article validation and generated assets [skip ci]"
    git push origin "HEAD:${GITHUB_REF_NAME:-final-corrections-20260806}"
  fi
  exit "${exit_code}"
}
trap write_status_and_commit EXIT

CURRENT_STEP="restore_bundle"
cat data/final_integration_bundle_20260806.tar.gz.part-* > /tmp/final_integration_bundle_20260806.tar.gz
tar -xzf /tmp/final_integration_bundle_20260806.tar.gz -C .
test -s data/final_taxonomy_palette_display.json
test -s data/antismash/antiSMASH_BGC_region_table.csv
test -s data/final_publication_derived/SupplementaryFigure40_FeGenie_iron_gene_categories_per_MAG_source.csv

CURRENT_STEP="taxonomy_nmds_rda"
FINAL_TAXONOMY_PALETTE_PATH=data/final_taxonomy_palette_display.json \
  python scripts/generate_final_domain_taxonomy_figures.py
python scripts/generate_s3_nmds_revision4.py --base-dir .
mkdir -p outputs/app_supplementary_figures
cp outputs/final_publication_figures/SupplementaryFigure4_NMDS_CDS_taxonomy.* outputs/app_supplementary_figures/

CURRENT_STEP="source_tables"
python scripts/export_final_article_source_tables.py \
  --workbook tables/Supplementary_Table_8.xlsx \
  --output-dir tables

CURRENT_STEP="supplementary_figures_38_42"
python scripts/generate_core_microbiome_and_shared_functions.py --base-dir . --only-core
python scripts/generate_shared_ko_heatmap.py --base-dir .
python scripts/generate_mag_abundance_and_fegenie_figures.py \
  --source-counts data/final_publication_derived/SupplementaryFigure40_FeGenie_iron_gene_categories_per_MAG_source.csv \
  --base-dir . --only-fegenie
python scripts/parse_antismash_bgc_metal_evidence.py \
  --antismash-dir data/kegg_modules/mags/gbk_antismash \
  --canonical-table data/antismash/antiSMASH_BGC_region_table.csv \
  --out-dir outputs/antismash \
  --article-root .
mkdir -p outputs/app_supplementary_figures
cp outputs/final_publication_figures/SupplementaryFigure38_core_taxa_shared_compartments_P*.* outputs/app_supplementary_figures/
cp outputs/final_publication_figures/SupplementaryFigure39_shared_KO_heatmap_lagoons_metatranscriptomes_P*.* outputs/app_supplementary_figures/
cp outputs/final_publication_figures/SupplementaryFigure40_FeGenie_iron_gene_categories_per_MAG_P*.* outputs/app_supplementary_figures/

CURRENT_STEP="tests_and_compile"
python -m pytest -q tests/test_final_article_results_integration.py
python -m py_compile \
  app.py \
  src/app_final_article_results_transform.py \
  src/final_article_results_runtime.py \
  src/figure_provenance.py \
  scripts/export_final_article_source_tables.py \
  scripts/generate_core_microbiome_and_shared_functions.py \
  scripts/generate_shared_ko_heatmap.py \
  scripts/generate_mag_abundance_and_fegenie_figures.py \
  scripts/parse_antismash_bgc_metal_evidence.py \
  scripts/generate_ordinations_revision4.py \
  scripts/generate_final_domain_taxonomy_figures.py \
  scripts/generate_taxonomy_supplementary_figures.py \
  scripts/generate_s3_nmds_revision4.py

CURRENT_STEP="scientific_contracts"
python - <<'PY'
from pathlib import Path
import hashlib, json
import pandas as pd
root = Path('.')
report = json.loads(Path('07_Validation_and_Manifests/taxonomy_lt1_final/MAIN_TAXONOMY_STRICT_LT1_VALIDATION.json').read_text())
assert all(item.get('pass') for item in report['validations'].values())
assert 'strictly <1.0%' in report['rule']
for number in (2, 3, 4, 5):
  stem = next((root/'outputs/final_publication_figures').glob(f'Figure{number}_*.png')).stem
  for ext in ('png','pdf','svg'):
    a=root/'outputs/final_publication_figures'/f'{stem}.{ext}'
    b=root/'outputs/app_main_figures'/f'{stem}.{ext}'
    assert b.is_file() and hashlib.sha256(a.read_bytes()).digest()==hashlib.sha256(b.read_bytes()).digest(), b
params=json.loads(Path('data/final_publication_derived/CDS_NMDS_parameters.json').read_text())
assert params.get('included_samples')==20 and params.get('nonmetric')
expected={
 'SupplementaryFigure38_core_taxa_shared_compartments':6,
 'SupplementaryFigure39_shared_KO_heatmap_lagoons_metatranscriptomes':6,
 'SupplementaryFigure40_FeGenie_iron_gene_categories_per_MAG':3,
 'SupplementaryFigure42_antiSMASH_BGC_iron_metal_evidence':3,
}
for stem,pages in expected.items():
  src=root/'outputs/antismash' if stem.startswith('SupplementaryFigure42') else root/'outputs/final_publication_figures'
  for ext in ('png','pdf','svg'):
    files=sorted(src.glob(f'{stem}_P*.{ext}'))
    assert len(files)==pages,(stem,ext,len(files))
    for f in files:
      app=root/'outputs/app_supplementary_figures'/f.name
      assert app.is_file() and hashlib.sha256(f.read_bytes()).digest()==hashlib.sha256(app.read_bytes()).digest(),f
  for svg in src.glob(f'{stem}_P*.svg'):
    text=svg.read_text(errors='replace')
    assert not any(x in text for x in ('Supplementary Figure','Page 1','Page 2','Page 3','Page 4','Page 5','Page 6')),svg
tax=pd.read_csv('data/final_publication_derived/SupplementaryFigure38_core_taxa_shared_compartments_phylum_matrix.csv',index_col=0)
regions=pd.read_csv('data/final_publication_derived/SupplementaryFigure38_core_taxa_shared_compartments_phylum_regions.csv')
family=pd.read_csv('data/final_publication_derived/SupplementaryFigure38_core_taxa_shared_compartments_family_matrix.csv',index_col=0)
ko=pd.read_csv('data/final_publication_derived/SupplementaryFigure39_shared_KO_heatmap_lagoons_metatranscriptomes_source_counts.csv',index_col=0)
fe=pd.read_csv('data/final_publication_derived/SupplementaryFigure40_FeGenie_iron_gene_categories_per_MAG_source.csv',index_col=0)
bgc=pd.read_csv('outputs/antismash/antiSMASH_BGC_region_table_metal_evidence.csv')
assert tax.shape==(63,3)
assert int((regions['region'].astype(str)=='all_three').sum())==28
assert int((family>0).all(axis=1).sum())==56
assert ko.shape==(126,4)
assert fe.shape==(47,9) and int(fe.to_numpy().sum())==531
assert len(bgc)==146 and int((bgc['Evidence type']=='Contextual association').sum())==2
PY

CURRENT_STEP="streamlit_health"
streamlit run app.py --server.headless true --server.address 127.0.0.1 --server.port 8501 > streamlit-final.log 2>&1 &
APP_PID=$!
READY=0
for attempt in $(seq 1 30); do
  if curl --fail --silent http://127.0.0.1:8501/_stcore/health >/dev/null; then READY=1; break; fi
  sleep 2
done
cat streamlit-final.log
[[ ${READY} -eq 1 ]]
! grep -E "Traceback|ModuleNotFoundError|ImportError|RuntimeError:" streamlit-final.log
FINAL_STATUS="success"
CURRENT_STEP="complete"
