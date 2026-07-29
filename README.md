> **Atualização de 28/07/2026:** RDA e NMDS do artigo e do aplicativo agora usam o mesmo módulo científico (`src/publication_ordination.py`). As 25 correções da auditoria foram implementadas e validadas. Consulte [`CORRECTIONS_2026-07-28.md`](CORRECTIONS_2026-07-28.md).

# CangaMetaG — complete computational reproducibility

## Canonical package and strict preservation scope

`CangaMetaG_App_Final/` is the canonical execution root. `CangaMetaG_Article_Final/` contains synchronized publication outputs, source-data/audit files, scripts, validation reports and Supplementary Table 16.

This delivery changes only the explicitly requested S40/S67 environmental-group workflow, its documentation, its application entries, the editable script table and the Supplementary Information. Every other main and supplementary figure is preserved with its previous filename, numbering, panel order, dimensions, proportions, axes, category/sample order, colours, labels and scientific content. No global style or plotting change is applied. Figures S26–S28 remain in their already approved order and were not regenerated or reordered.

Final layout policy:

- **S40:** only the version organized by `environmental group` is an active publication/application figure. The immutable original-order matrix is retained solely as an audit reference for cell-by-cell equivalence testing and is not distributed as an active S40 graphic.
- **S67:** both the original layout and the version organized by `environmental group` remain available.
- No X/Y axis is exchanged, no matrix is transposed, and no module, sample, record or categorical status is removed, duplicated, recalculated, normalized or transformed.

## Environment

```bash
cd CangaMetaG_App_Final
conda env create -f environment.yml
conda activate cangametag-reproducibility
```

Alternative:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Directory organization

- `scripts/`: canonical final generators plus validation/document workflows.
- `data/module_figure_inputs/`: immutable S40/S67 categorical matrices and environmental-group metadata.
- `data/final_publication_derived/`: final status matrices and explicit active column-order files.
- `outputs/final_publication_figures/`: article-compatible PNG/PDF/SVG outputs.
- `outputs/app_supplementary_figures/`: application-display copies.
- `validation/`: cell-level comparisons, preservation audits, script-table checks and cross-package hashes.
- `tables/`: editable Supplementary Table 16 in CSV, XLSX and DOCX.
- `FIGURE_REPRODUCTION_COMMANDS.md`: exact command/input/output mapping for every final figure record.

## Generate final S40 and S67 outputs

```bash
python scripts/figures/generate_environmental_group_heatmaps.py --root .
```

Active outputs:

- S40 environmental-group final: `outputs/final_publication_figures/SupplementaryFigure40_ST8_external_iron_rich_module_completeness_by_environmental_group*`
- S67 original: `outputs/final_publication_figures/SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_KEMET_style_3state_heatmap*`
- S67 environmental-group alternative: `outputs/final_publication_figures/SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_by_environmental_group*`

The script reconstructs the original-order S40 matrix in memory only for audit. It removes any superseded active original-order S40 PNG/PDF/SVG and derived order/status aliases. The immutable source table remains at:

```text
data/module_figure_inputs/SupplementaryFigure40_ST8_external_iron_rich_module_completeness_KEMET_style_3state_heatmap_thematic_status.csv
```

## Compare the source and grouped matrices

```bash
python scripts/validation/compare_environmental_group_heatmaps.py --root .
```

Outputs:

- `validation/environmental_group_heatmap_comparison.tsv`
- `validation/environmental_group_heatmap_comparison.md`
- `validation/environmental_group_heatmap_comparison.json`

A PASS requires equal dimensions, identical module/sample sets without duplicates, identical completeness-state counts, no transposition, and every cell identical after restoring the original column order. The environmental-group metadata control only the stable column permutation.

## Build the complete script table

```bash
python scripts/build_complete_figure_script_table.py \
  --root . \
  --article-root ../CangaMetaG_Article_Final
```

The canonical delivery table contains **81 final figure records**, **97 figure/panel rows**, **5 workflow rows**, **102 editable data rows** and **26 unique script/workflow paths** across 20 editable fields. Files:

- `tables/Supplementary_Table_16_final_scripts.csv`
- `tables/Supplementary_Table_16_final_scripts.xlsx`
- `tables/Supplementary_Table_16_final_scripts.docx`
- `validation/complete_figure_script_table_validation.tsv`
- `validation/complete_figure_script_table_summary.json`

The XLSX is an editable filtered table. The Word version is an editable A3 landscape table with a repeated header.

## Update Supplementary Information and synchronize packages

```bash
python scripts/documents/update_supplementary_information.py \
  --app-root . \
  --article-root ../CangaMetaG_Article_Final

python scripts/synchronize_article_app_outputs.py \
  --app-root . \
  --article-root ../CangaMetaG_Article_Final
```

The document workflow inserts grouped-only S40 P001/P002, original S67 P001/P002, grouped S67 P001/P002 and the complete editable Table 16. It does not edit publication images manually. The synchronization workflow copies only target/reproducibility outputs and verifies article/application identities.

## Run the application

```bash
streamlit run app.py
```

The KEGG/KEMET module area exposes the final environmental-group S40, both S67 layouts, source/order tables and equivalence reports. It does not expose a superseded original-order S40 graphic.

## Reproduce every figure

See `FIGURE_REPRODUCTION_COMMANDS.md` and `tables/Supplementary_Table_16_final_scripts.*`. The command index includes all **81 final figure records**: 8 main records and 73 supplementary records, including grouped-only S40 and both S67 layouts. Multipage figures are expanded panel by panel in Table 16.

## Preservation verification

Final validation includes:

- byte/hash comparison of all non-target article and application figure files against the corrected incoming ZIPs;
- explicit verification that S26, S27 and S28 files, axes/order and names are unchanged;
- comparison of S40/S67 matrices after identifier-based order restoration;
- script/input/output existence and Python compilation checks;
- application/article target synchronization checks;
- smoke regeneration showing that the final script renders no original-order S40 and reproduces all active PNG pixels exactly.

Reports are under `validation/` in the app and `07_Validation_and_Manifests/` in the article.

## Complete end-to-end commands

Extract the two roots side by side, then run:

```bash
cd CangaMetaG_App_Final
python -m py_compile app.py $(find scripts -type f -name '*.py' -print)
python scripts/figures/generate_environmental_group_heatmaps.py --root .
python scripts/validation/compare_environmental_group_heatmaps.py --root .
python scripts/build_complete_figure_script_table.py --root . --article-root ../CangaMetaG_Article_Final
python scripts/documents/update_supplementary_information.py --app-root . --article-root ../CangaMetaG_Article_Final
python scripts/synchronize_article_app_outputs.py --app-root . --article-root ../CangaMetaG_Article_Final
streamlit run app.py
```

Expected layout:

```text
parent_directory/
├── CangaMetaG_App_Final/
└── CangaMetaG_Article_Final/
```


## Runtime startup fix and validation

This package contains the complete `src` module tree required by `app.py`. Before launching, run:

```bash
python scripts/check_app_runtime.py
python -m streamlit run app.py
```

On Windows, after installing `requirements.txt`, double-click `run_app_windows.bat` or execute it from Command Prompt. The detailed correction report is `APP_RUNTIME_FIX_REPORT.md`.

## Streamlit Community Cloud

Deployment configuration and pre-deployment checks are documented in
[`STREAMLIT_COMMUNITY_CLOUD.md`](STREAMLIT_COMMUNITY_CLOUD.md). The app uses
Python 3.12, the root `requirements.txt`, `.streamlit/config.toml`, and
repository-relative data paths.
