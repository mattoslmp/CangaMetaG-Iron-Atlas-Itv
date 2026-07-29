# Database location in this app

The database files are intentionally kept in the same structure used by the original complete app:

- `data/` — app configuration, curated metadata, ST8 summary tables, admin/runtime state and final figure input aliases.
- `data/final_publication_inputs/` — original final input files used for the new figures.
- `tables/` — supplementary tables and main database spreadsheets used by the app.
- `outputs/linked_ko_pathway_tables/` — linked KO/pathway table exports.
- `outputs/final_publication_figures/` — final publication figures displayed in the new app section.
- `outputs/final_publication_statistics/` — statistical outputs for the final figures.

This `database/` folder is included so users looking for a database directory know where each database component is stored without breaking the original app structure.
