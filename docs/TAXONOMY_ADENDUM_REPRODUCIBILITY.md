# Taxonomy addendum: reproducibility and validation

## Canonical taxonomy palette

All taxonomic visualisations load one canonical palette from:

- `data/taxonomy_palette.json`
- `data/taxonomy_palette.csv`
- `src/taxonomy_palette.py`

The palette is independent of row/category order. `Chloroflexi` is `#7B2CBF`, whereas `Candidatus Rokubacteria` is `#00A6A6`. Neutral categories (`Others`, `Unclassified`, `Unassigned`, `Unknown`) use reserved neutral colours.

Rebuild the palette:

```bash
python scripts/build_taxonomy_palette.py
```

## Domain-separated taxonomy figures

The final supplementary sequence 43–66 contains the 24 requested domain/rank/visualisation combinations:

- domains: Bacteria and Archaea;
- ranks: Phylum, Class, Order, Family, Genus and Species;
- visualisations: 100% stacked individual-sample barplot and heatmap displayed as log10(relative abundance [%] + 1).

Rebuild:

```bash
python scripts/generate_taxonomy_supplementary_figures.py
```

Inputs:

- `data/resultado.cds.otu.tab`
- `data/resultado.cds.tax.tab`
- sample metadata loaded by the script from the portable package.

Outputs:

- `outputs/final_publication_figures/`
- `outputs/app_supplementary_figures/`
- `data/final_publication_derived/`
- `data/taxonomy_supplementary_figure_manifest.csv`

Barplot values are normalised independently per sample and validated to sum to approximately 100%, with only rounding-level deviations. Heatmaps show the same untransformed relative-abundance percentages; no z-score or logarithmic scale is applied.

## Application controls

The Taxonomy module exposes:

- `Domain`: Bacteria or Archaea;
- `Taxonomic level`: Phylum, Class, Order, Family, Genus or Species;
- `Visualization`: Barplot by individual sample or Relative-abundance heatmap.

The displayed title is generated from the selected values, for example:

```text
Archaea — Family — Relative-abundance heatmap
```

A fallback guard prevents `undefined`, `null`, `None`, `NA` or `NaN` from reaching the frontend.

## Module-completeness heatmaps

Rebuild the corrected module heatmaps:

```bash
python scripts/generate_kegg_module_completeness_heatmaps_green_blue_red.py
```

The figure dimensions are calculated from the matrix shape and label lengths. Y labels are placed next to the first cell column, X labels are centred on their corresponding columns, and artificial inter-cell gaps are not used.

## Validation

```bash
python scripts/validate_taxonomy_adendum.py
streamlit run app.py
```

Machine-readable validation outputs are stored in `reports/`. The UI test evaluates all 24 domain/rank/visualisation combinations with Streamlit's application-testing interface and records exceptions and dynamic-title checks.
## Main genus-profile RDA biplots

`python scripts/generate_final_domain_taxonomy_figures.py` rebuilds Figures 2–5. In Figures 4 and 5, panel D is a constrained RDA biplot containing sample site scores, solid physicochemical vectors and dashed representative-genus vectors. Representative genus vectors are selected from the domain-filtered genus matrix and retain the same colours assigned by `data/taxonomy_palette.json`. The complete and representative vector tables are written to `data/final_publication_derived/`.

## Taxonomy heatmap transformation

`python scripts/generate_taxonomy_supplementary_figures.py` rebuilds Supplementary Figures 43–66. Heatmaps retain relative abundance as the scientific source quantity and display `log10(relative abundance [%] + 1)` solely to reveal low-abundance variation. Each heatmap writes both the raw percentage matrix and the displayed transformed matrix to `data/final_publication_derived/`. The colour scale is `coolwarm_r`, yielding red for lower transformed values and blue for higher transformed values.

