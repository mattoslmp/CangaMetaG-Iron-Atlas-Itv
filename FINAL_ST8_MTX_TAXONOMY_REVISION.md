# Final ST8, metatranscriptome and taxonomy revision

## Scientific source contract

The final implementation uses `tables/Supplementary_Table_8.xlsx`, worksheet `ST8 — all KO biomarkers`, as the source of truth.

- Source KOs: **189**
- Unique KOs: **189**
- Amazonian lake samples: **20**
- KOs detected across the Amazonian samples: **172**
- Zero-total KOs across the Amazonian samples: **17**
- Metatranscriptome samples: **12**
- Zero remains a measured zero.
- No value is filled, invented or imputed.

## Root causes corrected

### Incomplete metatranscriptome heatmaps

Legacy application layers resolved metatranscriptome columns primarily through exact string equality between metadata fields and matrix columns. A scientific matrix column can instead match a normalized metadata field or include the IMG/JGI identifier inside a longer display name. The incomplete list was subsequently reused by raw, normalized and Z-score renderers.

The final resolver in `src/st8_final_contract.py` follows metadata order and applies exact, normalized and unique-identifier matching. It requires exactly 12 distinct source columns.

### KO Biogeochemical Cycles

The KO panel previously reconstructed the metatranscriptome list after preparing the matrix and filters. The final application contract resolves source columns before functional row filters and reuses the same ordered sample list for raw, relative-abundance and row-Z-score views.

### Amazonian lateritic lakes versus other environments

The combined view previously inferred columns through overlapping lake/external classifiers. The final source matrices explicitly preserve 20 Amazonian columns followed by all 12 metadata-ordered metatranscriptomes. Environmental grouping changes display order only; scientific values remain unchanged.

## App integration

- `src/st8_final_contract.py`
- `src/app_final_st8_ko_mtx_revision_transform.py`
- `src/app_mtx_alpha_taxonomy_runtime.py`
- `app.py`

The public interface avoids internal audit wording. Scientific-data panels retain only Source, Processed, Output, Plotted values and Script.

## Corrected and regenerated figure groups

- Supplementary Figures 26–28: Phylum, Order and Family Venn diagrams.
- Supplementary Figures 31A–31C: common-taxa heatmaps.
- Supplementary Figure 40: 45-degree x-axis labels and dynamic geometry.
- Supplementary Figure 67: 45-degree x-axis labels and dynamic geometry.
- ST8 MTX heatmaps: 189 KOs × 12 samples, raw, relative abundance and row Z-score.
- ST8 Amazonian + MTX heatmaps: 189 KOs × 32 samples, raw, relative abundance and row Z-score.

## Final generators

```bash
python scripts/generate_core_taxonomy_overlap_figure.py \
  --base-dir . \
  --article-root ARTICLE_ROOT

python scripts/figures/generate_s31_taxonomic_levels_revision3.py \
  --base-dir . \
  --article-root ARTICLE_ROOT

python scripts/figures/generate_environmental_group_heatmaps_final.py \
  --root .

python scripts/figures/generate_st8_ko_mtx_final_figures.py \
  --root . \
  --article-root ARTICLE_ROOT \
  --workbook tables/Supplementary_Table_8.xlsx
```

## Validation

The repository includes:

- `tests/test_st8_final_contract.py`
- `.github/workflows/validate-final-app-and-st8.yml`

The tests verify the 189/172/17 KO contract, 20 Amazonian samples, 12 MTX samples, matching raw/relative/Z-score dimensions, zero preservation, no imputation, 45-degree heatmap geometry and final transform order.

## Delivery

Repository: `mattoslmp/CangaMetaG-Iron-Atlas-Itv`

Branch: `main`

The publication package contains clean and review manuscripts, final figures, source tables, scripts, validation reports, checksums and reconstruction instructions for the 49-part archive.