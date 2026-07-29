# Computational reproducibility and figure generation

## Scope

This package contains the complete scripts, packaged inputs, derived tables and exact commands for all main and supplementary figures. Revision 4 regenerates only Supplementary Figure 3, Figures 4 and 5, and Supplementary Figures S17, S37, S38, S40, S41 and S47. S3 was added to the targeted set because the prior implementation used metric MDS while labeling the output as NMDS. All other validated figures are preserved byte-for-byte; see `validation/FIGURE_PRESERVATION_AUDIT_REVISION4.csv`.

## Environment

- Linux or another operating system supporting Python 3.11+
- Python dependencies: `requirements.txt`
- Conda environment: `environment.yml`

```bash
conda env create -f environment.yml
conda activate gangametag-iron-atlas
```

or:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Targeted reproducible run

From the application root:

```bash
python generate_all_figures.py \
  --base-dir . \
  --article-root ../ARTICLE_FINAL_ISME_SUBMISSION_TAXONOMY_ST8_V7_REVISION4_ORDINATION_CORRECTED \
  --mode targeted
```

Validation without overwriting any figure:

```bash
python generate_all_figures.py \
  --base-dir . \
  --article-root ../ARTICLE_FINAL_ISME_SUBMISSION_TAXONOMY_ST8_V7_REVISION4_ORDINATION_CORRECTED \
  --mode validate
```

## Exact targeted commands

```bash
python scripts/figures/generate_s3_nmds_revision4.py --base-dir . --article-root ../ARTICLE_FINAL_ISME_SUBMISSION_TAXONOMY_ST8_V7_REVISION4_ORDINATION_CORRECTED
python scripts/figures/generate_ordinations_revision4.py --base-dir . --article-root ../ARTICLE_FINAL_ISME_SUBMISSION_TAXONOMY_ST8_V7_REVISION4_ORDINATION_CORRECTED
python scripts/figures/generate_module_figures_revision4.py --base-dir . --article-root ../ARTICLE_FINAL_ISME_SUBMISSION_TAXONOMY_ST8_V7_REVISION4_ORDINATION_CORRECTED
python scripts/figures/generate_s47_revision4.py --base-dir . --article-root ../ARTICLE_FINAL_ISME_SUBMISSION_TAXONOMY_ST8_V7_REVISION4_ORDINATION_CORRECTED
```

## RDA and NMDS

The full audit is in `reproducibility/ordination_audit/README.md`. Supplementary Figure 3 uses the complete CDS abundance matrix; Figures 4C and 5C use domain-specific genus matrices. Every NMDS retains all 20 metagenomes and uses square-root-transformed relative proportions, Bray–Curtis dissimilarity, true non-metric MDS, two dimensions, 20 starts, 1,000 maximum iterations, seed 42 and normalized Stress-1. RDA uses ten sampling positions because physicochemical measurements are position-level. Dry and rainy metagenomes are pooled by position before Hellinger transformation; no raw metagenome is silently excluded. Predictors are LOI, SiO2, Al2O3, total sulfur, Cu and Pb.

The Streamlit application consumes the exact exported site scores and vectors through `src/publication_rda.py`; it does not refit the article model.

## Module heatmaps

S37 and S38 are paginated only across rows, so every page contains all 47 MAGs or all 20 Amazonian metagenomes, respectively. S40 may be split across both dimensions because it contains 67 external records. All tick positions use the integer centres of the `imshow` cells. Only modules classified as Complete in at least one displayed record are retained.

## Manifest and audit

- `FIGURE_SCRIPT_INPUT_OUTPUT_MANIFEST_REVISION4.csv`: figure/panel, true plotting script, inputs, command and SHA-256.
- `validation/FIGURE_SCRIPT_AVAILABILITY_REVISION4.csv`: script-presence audit.
- `validation/FIGURE_PRESERVATION_AUDIT_REVISION4.csv`: byte-level proof that non-target figures were preserved.
- `reproducibility/ordination_audit/`: inputs, intermediates, scores, tests, figures, logs and validation.

All commands use paths relative to the project root.
