# Scripts, figures, tables and methods manifest

This package uses the files in `tables/` as the authoritative source for taxonomy, KO pathways, KEMET/KEGG modules, MAG quality, annotation completeness, antiSMASH outputs and ST8 references.

## Main scripts and where outputs appear

| Script | Objective | Inputs | Outputs | App/article location |
|---|---|---|---|---|
| `src/supplementary_database.py` | Load supplementary workbooks and build taxonomy/KO/MAG/ST8 data tables | `tables/Supplementary_Table_1.xlsx`, Tables 4, 5, 6, 7, 8, 9 | Taxonomic heatmaps/barplots, metadata tables, KO/EC/PFAM tables | Taxonomy, Functional annotations, Methods |
| `src/kegg_modules.py` | Parse and display KEMET/KEGG module completeness | Tables 3 and 9, `data/kegg_modules/**/reportKMC_*.tsv`, MAG taxonomy workbook | Categorical module status, raw completeness matrix, z-score matrix, module-component maps | KEGG Modules — MAGs & Metagenomes; Supplementary Figures 38-39 |
| `scripts/refresh_kegg_module_heatmaps.py` | Regenerate large KEGG module heatmap panels | `outputs/kegg_modules/*display_labels_matrix.csv` | Supplementary Figures 38 and 39 | Final figures and KEGG modules |
| `scripts/generate_bidirectional_environment_contrast_figures.py` | Generate directional KO contrast panels | `tables/Supplementary_table_8_final_restructured_filled.xlsx` | Figures 7-8 and Supplementary Figures 6-7 | Differential abundance and article figures |
| `src/functional_annotations.py` | Render KO/EC/PFAM raw-count and z-score heatmaps | Tables 6 and 8 | Linked annotation heatmaps and tables | Functional annotations |
| `src/antismash_viewer.py` | Display antiSMASH BGC outputs | antiSMASH folders and BGC tables | BGC tables and embedded antiSMASH HTML | MAGs & genomes |

All supplementary workbooks are rendered in the app through the public table browser in Materials, methods and references, and every visible table can be downloaded.
