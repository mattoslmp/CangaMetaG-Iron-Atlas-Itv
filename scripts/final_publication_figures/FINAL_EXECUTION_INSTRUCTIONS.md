# Final figure execution instructions

These commands are the canonical entry points used for the next article package.
Do not run superseded copies of the former figure generators.

## 1. Environment

```bash
python -m venv .venv-final-figures
source .venv-final-figures/bin/activate
python -m pip install --upgrade pip
python -m pip install -r scripts/final_publication_figures/requirements-final-figures.txt
```

## 2. Final taxonomy Figures 2–5

```bash
python scripts/final_publication_figures/02_05_generate_final_taxonomy_figures.py
```

Compatibility command:

```bash
python scripts/generate_final_domain_taxonomy_figures.py
```

Both commands use the same final implementation. They generate:

- `Figure2_taxonomic_phylum_bacteria_horizontal_CDS.{png,pdf,svg,tiff}`
- `Figure3_taxonomic_phylum_archaea_horizontal_CDS.{png,pdf,svg,tiff}`
- `Figure4_taxonomic_bacteria_genus_profiles.{png,pdf,svg,tiff}`
- `Figure5_taxonomic_archaea_genus_profiles.{png,pdf,svg,tiff}`

Figure 2/3 taxonomy labels are generated from the corrected frozen source CSVs.
Figure 4/5 abundance matrices, NMDS coordinates, RDA site scores, vectors and
statistics are read from the same frozen tables used by the application. NMDS,
RDA and genus legends are placed in reserved areas outside the scientific panels.

## 3. Final Supplementary Table 8 KO heatmaps

Amazonian lake scope, default final view:

```bash
python scripts/final_publication_figures/07_generate_st8_ko_biomarker_heatmaps.py
```

All 87 Supplementary Table 8 columns:

```bash
python scripts/final_publication_figures/07_generate_st8_ko_biomarker_heatmaps.py --scope all
```

External records only:

```bash
python scripts/final_publication_figures/07_generate_st8_ko_biomarker_heatmaps.py --scope external
```

The immutable worksheet contains:

- 189 unique KO rows;
- 87 numeric columns;
- 20 Amazonian lake samples;
- 67 external records;
- no blank numeric cells;
- no negative counts.

Detection audit:

- 172 KOs are detected in at least one Amazonian sample;
- 17 KOs have total count zero across the 20 Amazonian samples;
- 188 KOs are detected across all 87 columns;
- `K17877: NIT-6` has total count zero across all 87 columns.

All 189 source rows remain in the exact source table and audit CSV. Heatmap
figures exclude rows with total zero in the selected scope by default. To
include them explicitly for inspection:

```bash
python scripts/final_publication_figures/07_generate_st8_ko_biomarker_heatmaps.py --include-undetected
```

No count is imputed or invented.

## 4. Outputs and audits

Final figures are written under:

- `outputs/final_publication_figures/`
- `outputs/app_supplementary_figures/`

Exact matrices and audits are written under:

- `data/final_publication_derived/`
- `reports/FINAL_DOMAIN_TAXONOMY_GENERATION_REPORT.json`
- `reports/FINAL_ST8_KO_HEATMAP_REPORT.json`

The canonical registry is:

```text
scripts/FINAL_SCRIPT_MANIFEST.json
```

## 5. Focused validation

```bash
pytest -q -p no:cacheprovider \
  tests/test_st8_biomarker_heatmap.py \
  tests/test_visitor_geolocation.py \
  tests/test_final_script_manifest.py \
  tests/test_frozen_article_taxonomy_panels.py \
  tests/test_exact_figure2_3_alignment.py \
  tests/test_app_exact_figure2_3_transform.py
```
