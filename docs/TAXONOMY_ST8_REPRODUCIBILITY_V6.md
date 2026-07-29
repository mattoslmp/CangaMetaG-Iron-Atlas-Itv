# Taxonomy and ST8 reproducibility

## Interactive taxonomy

The interactive taxonomy panel reads the complete taxonomic profiles from `tables/Supplementary_Table_1.xlsx` through `src/supplementary_database.py`. The domain, rank, text filter and Top-N selection are applied before the plotting matrix is built. Increasing Top-N therefore adds the next ranked taxa; taxa outside the selected Top-N are summed into `Other taxa`.

The categorical colour source is `data/taxonomy_palette.json`. The same mapping is loaded by the interactive application, the main taxonomy-figure generator and the supplementary taxonomy-figure generator. Colours depend on the taxon label, not on plotting order.

| Purpose | Script/module | Inputs | Outputs / use | Command |
|---|---|---|---|---|
| Interactive taxonomy controls and Plotly barplots | `app.py` | Supplementary Table 1, canonical palette | Interactive barplots, heatmaps, tables and downloads | `bash run_app_no_root.sh` |
| Taxonomy table parsing and legacy barplots | `src/supplementary_database.py` | `tables/Supplementary_Table_1.xlsx` | Long-form taxonomic profiles | Imported by `app.py` |
| Canonical taxon colours | `src/taxonomy_palette.py` | `data/taxonomy_palette.json` | Stable taxon-to-colour mapping | Imported by application and figure scripts |
| Main taxonomy figures 2-5 | `scripts/generate_final_domain_taxonomy_figures.py` | `data/resultado.cds.otu.tab`, `data/resultado.cds.tax.tab`, physicochemical data | Figures 2-5 in PNG/PDF/SVG and source tables | `python scripts/generate_final_domain_taxonomy_figures.py` |
| Supplementary taxonomy barplots and heatmaps | `scripts/generate_taxonomy_supplementary_figures.py` | CDS abundance/taxonomy tables and canonical palette | Supplementary Figures 43-66 in PNG/PDF/SVG | `python scripts/generate_taxonomy_supplementary_figures.py` |

## ST8 metadata and taxonomy

The complete source workbook is `tables/Supplementary_table_8_final_restructured_filled.xlsx`. Compact CSV mirrors in `data/` and `tables/` are generated from named workbook sheets to reduce application startup time. The application checks both packaged locations and exposes the complete workbook for download.

| Purpose | Script/module | Inputs | Outputs / use | Command |
|---|---|---|---|---|
| Export ST8 metadata and summaries | `scripts/rebuild_st8_final_exports.py` | Supplementary Table 8 final workbook | `st8_metadata_curated.csv`, taxonomy/group/contrast/reference CSVs | `python scripts/rebuild_st8_final_exports.py` |
| ST8 application panel | `app.py` | Exported CSVs and source workbook | Metadata tables, filters, GTDB barplots, contrasts and downloads | `bash run_app_no_root.sh` |

All paths are project-relative for packaged resources and user-writable XDG paths for runtime state, cache, configuration, downloads and generated outputs.
