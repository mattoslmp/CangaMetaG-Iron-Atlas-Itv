# CangaMetaG — Iron-Rich Amazonian Lateritic Lake Metagenomic Atlas

**CangaMetaG** is an interactive scientific atlas for exploring microbial diversity and functional potential in iron-rich Amazonian lateritic lake sediments. The repository contains the Streamlit application, curated datasets, publication figures, supplementary tables, and reproducible scripts associated with the study.

## Abstract

Iron-rich lateritic lakes in the Amazon contain microbial communities adapted to highly mineralized and geochemically distinctive sediments. CangaMetaG integrates metagenomic and metatranscriptomic information to support the exploration of taxonomic diversity, community structure, functional markers, iron-related metabolism, biogeochemical pathways, metagenome-assembled genomes, and biosynthetic gene clusters.

The web application provides interactive access to the study data through tables, filters, heatmaps, taxonomic profiles, diversity analyses, ordinations, functional annotations, KEGG/KEMET module summaries, MAG information, and downloadable publication resources. The repository also preserves the computational scripts needed to reproduce the main and supplementary figures associated with the manuscript.

## Authors

- Leandro de Mattos Pereira
- José Augusto Pires Bittencourt
- Vitor Cirilo Araujo Santos
- Ronnie Alves
- Eder Pires
- Prafulla Kumar Sahoo
- José Tasso Felix Guimarães
- Bruno Garcia Simões
- Renato R. Moreira-Oliveira
- Guilherme Oliveira
- Gisele Lopes Nunes

**Institution:** Instituto Tecnológico Vale, Belém, Pará, Brazil.

**Corresponding authors**

- Gisele Lopes Nunes — `gisele.nunes@itv.org`
- Leandro de Mattos Pereira — `leandro.pereira@pq.itv.org`

## Main scientific components

CangaMetaG brings together the principal analytical components of the study:

- taxonomic profiles of Bacteria and Archaea;
- alpha- and beta-diversity analyses;
- rarefaction, NMDS, PCoA, PCA, and RDA visualizations;
- functional annotation and KEGG Orthology exploration;
- iron-metabolism and biogeochemical marker analyses;
- KEGG/KEMET module-completeness matrices;
- metagenome-assembled genome quality, taxonomy, abundance, and annotation;
- antiSMASH biosynthetic gene-cluster results;
- publication figures, supplementary figures, and source tables;
- interactive filtering and download of scientific results.

## Repository organization

```text
CangaMetaG-Iron-Atlas-Itv/
├── app.py                         # Main Streamlit application
├── src/                           # Reusable application and analysis modules
├── scripts/                       # Figure, table, document, and workflow scripts
├── data/                          # Curated input data and derived scientific matrices
├── tables/                        # Main and supplementary tables
├── outputs/                       # Figures and files displayed or distributed by the app
├── requirements.txt               # Python dependencies
├── packages.txt                   # Linux packages used during cloud deployment
├── environment.yml                # Conda environment specification
├── FIGURE_REPRODUCTION_COMMANDS.md
└── STREAMLIT_COMMUNITY_CLOUD.md
```

### `app.py`

Entry point of the Streamlit application. It assembles the interface and connects the scientific modules, datasets, figures, tables, and download resources.

### `src/`

Contains the reusable Python modules used by the application. These modules are organized by scientific or operational responsibility, including:

- taxonomic data processing and visualization;
- ordination and diversity analyses;
- functional annotation;
- KEGG and KEMET modules;
- MAG annotation and genome organization;
- antiSMASH result visualization;
- integrated omics analyses;
- sample metadata and runtime path management;
- Plotly export and visual-quality utilities.

### `data/`

Contains the scientific input files used by the application and figure-generation workflows. This includes taxonomic matrices, functional tables, sample metadata, MAG information, KEGG/KEMET results, publication source data, and derived matrices.

### `tables/`

Contains editable main and supplementary tables distributed with the project, primarily in CSV and Excel formats.

### `outputs/`

Contains publication-quality figures and the image resources displayed by the application. The repository keeps article figures and application-display assets in separate output locations so that each has a clear purpose.

## Organization of the scripts

The `scripts/` directory is organized by function rather than by execution order.

### General scripts in `scripts/`

These scripts coordinate broader tasks that involve multiple datasets or figure groups. Examples include:

- generation of the Amazonian sampling map;
- taxonomic figure production;
- consolidation of publication figures;
- generation of the computational workflow figure;
- construction of figure-to-script reference tables;
- synchronization of article and application outputs.

### `scripts/figures/`

Contains focused generators for individual main figures or defined groups of supplementary figures. These scripts are the preferred entry points when reproducing a specific figure or a closely related set of panels.

Representative workflows include:

- bacterial and archaeal taxonomic profiles;
- MAG quality and abundance figures;
- KO differential-abundance figures;
- biogeochemical-marker heatmaps;
- KEGG/KEMET module-completeness heatmaps;
- integrated environmental and taxonomic visualizations.

### `scripts/final_publication_figures/`

Contains specialized routines used for final publication analyses and figures, including rarefaction, diversity calculations, and other figure-specific processing steps.

### `scripts/documents/`

Contains scripts used to assemble or update manuscript-related documents and supplementary material from the repository data, tables, and final figures.

### Figure-to-script index

The exact relationship among each figure, its script, command, and input files is documented in:

[`FIGURE_REPRODUCTION_COMMANDS.md`](FIGURE_REPRODUCTION_COMMANDS.md)

## Run the application locally

### 1. Clone the repository

The repository uses Git LFS for large scientific assets.

```bash
git lfs install
git clone https://github.com/mattoslmp/CangaMetaG-Iron-Atlas-Itv.git
cd CangaMetaG-Iron-Atlas-Itv
```

### 2. Create the environment

Using Conda:

```bash
conda env create -f environment.yml
conda activate cangametag-reproducibility
```

Or using a Python virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On Windows PowerShell, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Start CangaMetaG

```bash
streamlit run app.py
```

The local application will normally be available at:

```text
http://localhost:8501
```

## Streamlit Community Cloud

Recommended deployment configuration:

```text
Repository: mattoslmp/CangaMetaG-Iron-Atlas-Itv
Branch: main
Main file path: app.py
Python version: 3.12
```

Detailed deployment instructions are available in:

[`STREAMLIT_COMMUNITY_CLOUD.md`](STREAMLIT_COMMUNITY_CLOUD.md)

Public application address:

[https://cangametag-iron-atlas-itv.streamlit.app](https://cangametag-iron-atlas-itv.streamlit.app)

## Reproducing publication figures

Commands for the main and supplementary figures are indexed in `FIGURE_REPRODUCTION_COMMANDS.md`. Run the commands from the repository root so that all relative data and output paths are resolved consistently.

Example:

```bash
python scripts/generate_amazon_coordinate_figure.py --base-dir .
python scripts/generate_final_domain_taxonomy_figures.py --base-dir .
python scripts/figures/generate_figure7.py --base-dir .
python scripts/figures/generate_figure8.py --base-dir .
```

## Associated manuscript

**Pereira et al.** *Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling.*

This repository contains the interactive atlas and computational resources associated with the manuscript.

## Scientific use

When using CangaMetaG data, figures, scripts, or the interactive atlas, cite the associated manuscript and this repository. Dataset-specific provenance and references are maintained within the application and the supplementary resources.