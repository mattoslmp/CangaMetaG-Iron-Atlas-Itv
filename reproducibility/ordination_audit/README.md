# Ordination audit: RDA and NMDS

This directory is the complete, executable audit trail for the ordinations used in Supplementary Figure 3, Main Figures 4 and 5, Supplementary Figure 17 and the corresponding application panels.

## Scientific design

- **Raw taxonomic samples:** 20 metagenomes (dry and rainy sediment metagenomes at ten sampling positions).
- **NMDS:** all 20 metagenomes are retained. Supplementary Figure 3 uses the complete CDS abundance matrix, whereas Figures 4C and 5C use Bacteria- and Archaea-specific genus matrices. Counts are converted to sample-wise relative proportions, square-root transformed, and Bray–Curtis dissimilarities are calculated. A two-dimensional **non-metric** MDS is fitted with 20 initializations, maximum 1,000 iterations, random seed 42 and normalized Stress-1.
- **RDA:** physicochemistry is available independently for ten sampling positions rather than separately by season. Dry and rainy taxonomic counts are therefore pooled by position before Hellinger transformation. The six standardized predictors are LOI, SiO2, Al2O3, total sulfur (TOT/S), Cu and Pb. Global and axis-specific significance use 999 permutations with seed 42.
- No raw metagenome is silently discarded. Each RDA point represents one named position and accounts for its dry and rainy metagenomes. The mapping is in `tables/RDA_all_samples_audit.csv`.

## Directory structure

- `input/`: packaged abundance, taxonomy and physicochemical inputs.
- `intermediate/`: transformed community matrices, Bray–Curtis matrices, pooled position matrices and standardized environmental predictors.
- `output/`: site scores, taxon/environment scores, NMDS statistics and exact files consumed by figures and app.
- `tables/`: sample accounting, VIF, model statistics, PERMANOVA and multivariate-dispersion tests.
- `figures/`: final PNG, PDF and SVG versions of S3, Figures 4 and 5, and S17.
- `scripts/`: the shared scientific calculation module and the figure generator.
- `logs/`: execution record.
- `validation/`: numeric summary, overlap checks and SHA-256 manifest.

## Environment

Python 3.11+ with NumPy, pandas, SciPy, scikit-learn, matplotlib, openpyxl and plotly. Use the project `requirements.txt` or `environment.yml`.

## Reproduce

From the application root:

```bash
python scripts/figures/generate_s3_nmds_revision4.py \
  --base-dir . \
  --article-root ../ARTICLE_FINAL_ISME_SUBMISSION_TAXONOMY_ST8_V7_REVISION4_ORDINATION_CORRECTED

python scripts/figures/generate_ordinations_revision4.py \
  --base-dir . \
  --article-root ../ARTICLE_FINAL_ISME_SUBMISSION_TAXONOMY_ST8_V7_REVISION4_ORDINATION_CORRECTED
```

The command reads `data/resultado.cds.otu.tab`, `data/resultado.cds.tax.tab` and `data/fiqui2.xlsx`, recreates the audit tables and outputs, and replaces only Figures 4, 5 and S17 in the configured article package.

## Interpretation

The RDA models are exploratory because there are ten independent physicochemical positions, six predictors and three residual degrees of freedom. The global permutation tests and adjusted R² are reported in `validation/ORDINATION_FINAL_NUMERIC_SUMMARY.csv`; no causal or strong confirmatory inference should be made from a non-significant model. The app reads the exported coordinates and does not refit these canonical article models.
