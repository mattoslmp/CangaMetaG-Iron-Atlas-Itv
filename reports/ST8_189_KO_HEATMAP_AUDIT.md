# Supplementary Table 8 — 189 KO heatmap audit

## Source verification

Source workbook: `tables/Supplementary_Table_8.xlsx`  
Worksheet: `ST8 — all KO biomarkers`

Verified structure:

- 189 rows and 189 unique KO identifiers;
- 87 numeric sample/record columns;
- 20 Amazonian lake samples;
- 67 external iron-rich records;
- zero blank numeric cells;
- zero negative counts.

## Detection results

| Scope | Detected KOs | Total-zero KOs |
|---|---:|---:|
| 20 Amazonian lake samples | 172 | 17 |
| 67 external records | 183 | 6 |
| all 87 columns | 188 | 1 |

The one marker with total count zero across every column is:

- `K17877: NIT-6` — nitrite reductase (NAD(P)H), assimilatory nitrate reduction.

## Interpretation

The zero rows are present in the original worksheet. They are not caused by a
spreadsheet import error and must not be replaced by synthetic values. However,
an all-zero row carries no observable heatmap signal in the selected scope.

Final policy:

1. Keep all 189 rows in the exact source table and detection audit.
2. Exclude total-zero rows from heatmap rendering by default.
3. Permit explicit inclusion of undetected rows for source inspection.
4. Apply the filter before Top-N ranking and before row z-score calculation.
5. Use the same filtered rows for the raw-count and row-z-score panels.
6. Never impute or invent a count.

## Canonical implementation

- `src/st8_biomarker_heatmap.py`
- `src/app_st8_biomarker_heatmap_transform.py`
- `scripts/final_publication_figures/07_generate_st8_ko_biomarker_heatmaps.py`
- `tests/test_st8_biomarker_heatmap.py`

The app, static generator and future article package must use these files.
