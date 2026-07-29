# KEMET metagenome inputs and reconstruction

The app package includes KEMET metagenome data. The expected directory is:

`data/kegg_modules/metagenomes/reports/`

This directory currently contains 20 `reportKMC_*.tsv` files, one for each metagenome:

- `Ga0540489` / `AM.P1.D`
- `Ga0541010` / `AM.P1.R`
- `Ga0541011` / `AM.P2.D`
- `Ga0541012` / `AM.P2.R`
- `Ga0541013` / `TIA.P1.D`
- `Ga0541014` / `TIA.P1.R`
- `Ga0541015` / `TIA.P2.D`
- `Ga0541016` / `TIA.P2.R`
- `Ga0541017` / `TI.P1.D`
- `Ga0541018` / `TI.P1.R`
- `Ga0541019` / `TI.P2.D`
- `Ga0541020` / `TI.P2.R`
- `Ga0541021` / `TI.P3.D`
- `Ga0541022` / `TI.P3.R`
- `Ga0541023` / `TI.P4.D`
- `Ga0541024` / `TI.P4.R`
- `Ga0541025` / `VI.P1.D`
- `Ga0541026` / `VI.P1.R`
- `Ga0541027` / `VI.P2.D`
- `Ga0541028` / `VI.P2.R`

If these files are absent in a future deployment, place all metagenome `reportKMC_*.tsv` files in:

`APP_FINAL/data/kegg_modules/metagenomes/reports/`

Then rebuild the matrices from the app root with:

```bash
python scripts/build_kemet_outputs.py
```

The KEGG Modules page reads the rebuilt files in:

`outputs/kegg_modules/`

The displayed heatmaps use:

- `outputs/kegg_modules/metagenomes_KEGG_module_completeness_score_matrix.csv`
- `outputs/kegg_modules/metagenomes_KEGG_module_status_matrix.csv`
- `outputs/kegg_modules/metagenomes_KEMET_sample_coverage.csv`
