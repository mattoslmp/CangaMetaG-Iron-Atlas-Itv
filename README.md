<div align="center">

# Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling

## CangaMetaG — Interactive Iron Metagenomic Atlas of Amazonian Canga Lakes

[![Streamlit](https://img.shields.io/badge/Streamlit-interactive%20atlas-FF4B4B?logo=streamlit&logoColor=white)](https://cangametag-iron-atlas-itv.streamlit.app)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Metagenomics](https://img.shields.io/badge/omics-shotgun%20metagenomics-2A9D8F)
![Genome resolved](https://img.shields.io/badge/analysis-genome--resolved-264653)

**[Open the interactive atlas](https://cangametag-iron-atlas-itv.streamlit.app)** · **[Figure reproduction index](FIGURE_REPRODUCTION_COMMANDS.md)** · **[Deployment guide](STREAMLIT_COMMUNITY_CLOUD.md)**

</div>

---

## Overview

**CangaMetaG** is the interactive scientific application associated with the study of microbial communities inhabiting iron-rich lateritic lake sediments in Serra dos Carajás, southeastern Amazonia, Brazil. The atlas integrates taxonomic, ecological, functional and genome-resolved information from sediment shotgun metagenomes collected in **Amendoim (AM), Violão (VI), Três Irmãs (TI)** and **Três Irmãs Adjacent (TIA)** lakes during dry and rainy periods.

The repository is centred on two complementary products:

1. an interactive **Streamlit application** for exploring and downloading the study results;
2. a structured collection of **reproducible scripts** used to generate the main and supplementary figures, tables and application resources.

> **Scientific interpretation:** detected genes, KEGG Orthology markers and reconstructed modules represent encoded biological potential. Their presence alone does not demonstrate pathway activity or in situ process rates.

---

## Article information

| Field | Information |
|---|---|
| **Article title** | *Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling* |
| **Running title** | *Iron atlas of Amazonian canga lakes* |
| **Article type** | Original Article |
| **Target journal** | *The ISME Journal* |
| **Institution** | Instituto Tecnológico Vale, Belém, Pará, Brazil |
| **Study system** | Ferruginous lateritic-lake sediments from Serra dos Carajás, Amazonia |
| **Primary approach** | Shotgun metagenomics and genome-resolved metagenomics |
| **Repository resource** | Interactive atlas, scripts, figures, tables and curated scientific data |

### Authors

**Leandro de Mattos Pereira**, **José Augusto Pires Bittencourt**, **Vitor Cirilo Araujo Santos**, **Ronnie Alves**, **Eder Pires**, **Prafulla Kumar Sahoo**, **José Tasso Felix Guimarães**, **Bruno Garcia Simões**, **Renato R. Moreira-Oliveira**, **Guilherme Oliveira** and **Gisele Lopes Nunes**.

**Affiliation:** Instituto Tecnológico Vale, Belém, PA, Brazil.

**Correspondence:** Gisele Lopes Nunes — `gisele.nunes@itv.org`

### Keywords

`shotgun metagenomics` · `metagenome-assembled genomes` · `Amazonian lakes` · `lateritic crust` · `canga` · `iron metabolism` · `biogeochemical cycling` · `methane cycling` · `nitrogen cycling`

---

## Abstract

Amazonian lateritic lakes developed on ferruginous canga are seasonally variable, metal-rich systems whose sediment microbiomes remain poorly characterized. We used shotgun metagenomics to investigate microbial communities in sediments from Amendoim, Violão, Três Irmãs and Três Irmãs Adjacent lakes during dry and rainy periods. Coding-sequence taxonomic profiles revealed diverse bacterial and archaeal assemblages and a large unclassified fraction, indicating substantial underexplored diversity. Lake- and season-associated contrasts involved methanogenic, ammonia-oxidizing and anaerobic sediment lineages. Non-metric multidimensional scaling showed partial community overlap, whereas an exploratory, non-significant redundancy analysis placed genus-level variation along iron, aluminium, silica, carbon and trace-metal gradients. Functional reconstruction identified genetic potential for carbon fixation, methane metabolism, nitrogen and sulfur cycling, photosynthesis, anaerobic respiration and iron metabolism. A curated Kyoto Encyclopedia of Genes and Genomes orthology framework detected 171 of 195 biogeochemical markers and 132 iron-associated markers. Descriptive cross-study contrasts distinguished Amazonian canga-lake profiles from external iron-rich records, but were not treated as inferential tests. We retained 50 non-redundant genome bins: 49 medium- to high-quality MAGs reconstructed through the metaSPAdes/MetaWRAP workflow and one additional PATRIC/BV-BRC-derived bin reported separately because of higher estimated contamination and the absence of a GTDB-Tk r89 classification in the supplied outputs. These results establish a genome-resolved iron metagenomic atlas for tropical lateritic-lake sediments and a basis for testing how seasonal hydrology and ferruginous geochemistry shape microbial biogeochemical functions.

---

## What the application provides

CangaMetaG brings the principal results of the study into a single interactive environment.

| Application area | Content available |
|---|---|
| **Study overview** | Article information, sampling context, authorship and scientific interpretation |
| **Taxonomy** | Bacterial and archaeal profiles across multiple taxonomic ranks |
| **Community ecology** | Rarefaction, alpha diversity, Bray–Curtis dissimilarity, NMDS, PCoA, PCA and RDA |
| **Functional potential** | Functional annotation tables, KEGG Orthology markers and pathway summaries |
| **Biogeochemical cycling** | Carbon fixation, methane, nitrogen, sulfur, photosynthesis and anaerobic-respiration markers |
| **Iron metabolism** | FeGenie categories and 132 curated iron-associated KOs |
| **KEGG/KEMET** | Module-completeness matrices for metagenomes, MAGs and comparative iron-rich datasets |
| **Genome-resolved ecology** | Quality, taxonomy, abundance and annotation of 50 non-redundant genome bins |
| **Biosynthetic potential** | antiSMASH biosynthetic gene-cluster regions and product summaries |
| **Publication resources** | Main figures, supplementary figures, tables and downloadable source data |

### Interactive features

- searchable and filterable scientific tables;
- taxonomic stacked bars and heatmaps;
- diversity and ordination plots;
- physicochemical and RDA visualizations;
- KEGG/KEMET module-completeness explorers;
- KO biomarker and iron-metabolism panels;
- MAG quality, taxonomy and annotation views;
- antiSMASH region and BGC summaries;
- direct download of figures, tables and supporting data.

---

## Methods at a glance

The complete experimental and analytical methods are described in the manuscript. The repository README retains only the methodological context needed to understand the application and reproduce its computational outputs.

| Stage | Summary |
|---|---|
| **Sampling and sequencing** | Twenty sediment samples from four Amazonian canga-lake systems were analysed by paired-end shotgun metagenomic sequencing on an Illumina NextSeq 500. |
| **Read processing and assembly** | Reads were quality-filtered with PRINSEQ and inspected with FastQC. Metagenomes were assembled with SPAdes/metaSPAdes, and assembly quality was evaluated with QUAST/MetaQUAST. |
| **Taxonomy and community ecology** | Coding sequences were classified with Kaiju. Taxonomic matrices were analysed with phyloseq, Bray–Curtis dissimilarity, NMDS, PERMANOVA, rarefaction, alpha diversity and exploratory RDA. |
| **Functional analysis** | Functional annotations were obtained from IMG/MER resources and analysed using KEGG Orthology markers, KAAS/KEMET module reconstruction and FeGenie-supported iron-metabolism categories. |
| **Genome-resolved analysis** | MAG reconstruction used metaSPAdes and MetaWRAP. Genome quality and taxonomy integrated CheckM, GTDB-Tk and BV-BRC information. |
| **Biosynthetic analysis** | antiSMASH outputs were parsed to expose BGC regions, predicted products and associated MAG information in the atlas. |

---

## Repository organization

```text
CangaMetaG-Iron-Atlas-Itv/
├── app.py                         # Main Streamlit application
├── src/                           # Reusable application and scientific modules
├── scripts/                       # Figure, table, document and workflow scripts
│   ├── figures/                   # Focused figure generators
│   ├── final_publication_figures/ # Publication-specific analytical routines
│   └── documents/                 # Manuscript and supplementary-document workflows
├── data/                          # Curated inputs and derived scientific matrices
├── tables/                        # Main and supplementary tables
├── outputs/                       # Publication figures and application assets
├── requirements.txt               # Python dependencies
├── packages.txt                   # Linux packages for cloud deployment
├── environment.yml                # Conda environment specification
├── FIGURE_REPRODUCTION_COMMANDS.md
└── STREAMLIT_COMMUNITY_CLOUD.md
```

### Core application files

| Path | Role |
|---|---|
| `app.py` | Main entry point. Builds the Streamlit interface and connects all scientific modules and resources. |
| `src/supplementary_database.py` | Central access layer for study tables, metadata and supplementary resources. |
| `src/publication_ordination.py` | Bray–Curtis, PCoA, NMDS, PERMANOVA and related ordination functions. |
| `src/publication_rda.py` | RDA and associated publication-ready data and figures. |
| `src/integrated_omics.py` | Integration of biological matrices and environmental variables. |
| `src/functional_annotations.py` | Functional annotation datasets, links and heatmaps. |
| `src/kegg_modules.py` | KEGG/KEMET matrices, module completeness and metagenome/MAG metadata. |
| `src/mag_annotations.py` | MAG inventories, quality summaries, taxonomy, features and genome organization. |
| `src/antismash_viewer.py` | Discovery, parsing and display of antiSMASH reports. |
| `src/plotly_export.py` | Export of interactive figures to publication-compatible formats. |
| `src/runtime_paths.py` | Safe application paths for local and cloud execution. |

### Data and output directories

| Directory | Purpose |
|---|---|
| `data/` | Taxonomic matrices, functional annotations, sample metadata, MAG information, KEGG/KEMET results and derived datasets used by the app. |
| `tables/` | Editable main and supplementary tables, principally in CSV and Excel formats. |
| `outputs/final_publication_figures/` | Publication-quality main and supplementary figures. |
| `outputs/app_supplementary_figures/` | Figure assets prepared for display inside the Streamlit application. |

---

## Organization of the scripts

The `scripts/` tree is organized by **scientific function**, rather than as one mandatory sequential pipeline. Most users will run a specific figure generator or consult the complete figure-to-script index.

### 1. General workflow scripts — `scripts/`

These scripts coordinate analyses or outputs that span multiple datasets or figure groups.

| Representative script | Main purpose |
|---|---|
| `scripts/generate_amazon_coordinate_figure.py` | Generates the sampling-location map and coordinate-based study figure. |
| `scripts/generate_final_domain_taxonomy_figures.py` | Produces final bacterial and archaeal domain-level taxonomic figures. |
| `scripts/generate_taxonomy_supplementary_figures.py` | Generates supplementary taxonomic figures across ranks and omics layers. |
| `scripts/generate_core_taxonomy_overlap_figure.py` | Produces taxonomic-overlap figures for selected ranks. |
| `scripts/generate_atlas_workflow_figure.py` | Generates the graphical overview of the CangaMetaG computational workflow. |
| `scripts/consolidate_final_publication.py` | Coordinates groups of final publication figures derived from packaged study data. |
| `scripts/build_complete_figure_script_table.py` | Builds the editable figure-to-script reference table. |
| `scripts/synchronize_article_app_outputs.py` | Synchronizes selected final figures and tables used by the article and application. |

### 2. Focused figure generators — `scripts/figures/`

These scripts reproduce individual main figures or closely related groups of supplementary figures.

| Representative script | Main purpose |
|---|---|
| `scripts/figures/generate_figures4_5_s17_revision3.py` | Bacterial and archaeal genus profiles and the associated environmental figure. |
| `scripts/figures/generate_figure7.py` | MAG quality and abundance visualization. |
| `scripts/figures/generate_figure8.py` | KO differential-abundance visualization. |
| `scripts/figures/generate_s6_s7.py` | Biogeochemical and iron-marker heatmaps. |
| `scripts/figures/generate_s31_taxonomic_levels_revision3.py` | Shared-taxonomy heatmaps across selected taxonomic ranks. |
| `scripts/figures/generate_s31_s32.py` | Biogeochemical-marker source and heatmap outputs. |
| `scripts/figures/generate_s33_biogeochemical_zscore_revision3.py` | Z-score representation of biogeochemical markers. |
| `scripts/figures/generate_environmental_group_heatmaps.py` | KEGG/KEMET module-completeness heatmaps organized by environmental group. |

### 3. Publication-specific routines — `scripts/final_publication_figures/`

This directory contains specialized analytical routines used by the final article figures, including fixed-depth rarefaction, alpha-diversity reconstruction and figure-specific statistical or graphical processing.

A representative entry point is:

```bash
CANGAMETA_ONLY_S4=1 python scripts/final_publication_figures/06_recalculate_rarefaction_alpha_32999.py
```

### 4. Document workflows — `scripts/documents/`

These scripts assemble or update manuscript-related and supplementary documents using the final tables and figures. They are separate from the scientific figure generators so that changes to document layout do not alter analytical outputs.

### Complete figure-to-script mapping

The exact relationship among each main or supplementary figure, its generating script, command and input files is documented in:

**[`FIGURE_REPRODUCTION_COMMANDS.md`](FIGURE_REPRODUCTION_COMMANDS.md)**

---

## Run the application locally

### 1. Clone the repository with Git LFS

```bash
git lfs install
git clone https://github.com/mattoslmp/CangaMetaG-Iron-Atlas-Itv.git
cd CangaMetaG-Iron-Atlas-Itv
git lfs pull
```

### 2. Create the environment

#### Conda

```bash
conda env create -f environment.yml
conda activate cangametag-reproducibility
```

#### Python virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Start CangaMetaG

```bash
streamlit run app.py
```

Local address:

```text
http://localhost:8501
```

---

## Reproduce publication figures

Commands must be run from the repository root so that repository-relative input and output paths remain consistent.

Examples:

```bash
python scripts/generate_amazon_coordinate_figure.py --base-dir .
python scripts/generate_final_domain_taxonomy_figures.py --base-dir .
python scripts/figures/generate_figure7.py --base-dir .
python scripts/figures/generate_figure8.py --base-dir .
```

For all main and supplementary figures, consult:

**[`FIGURE_REPRODUCTION_COMMANDS.md`](FIGURE_REPRODUCTION_COMMANDS.md)**

---

## Streamlit Community Cloud

Recommended deployment settings:

```text
Repository: mattoslmp/CangaMetaG-Iron-Atlas-Itv
Branch: main
Main file path: app.py
Python version: 3.12
```

Application address:

### https://cangametag-iron-atlas-itv.streamlit.app

The repository includes:

- `requirements.txt` for Python packages;
- `packages.txt` for required Linux packages;
- `.streamlit/config.toml` for application configuration;
- repository-relative paths suitable for local and cloud execution.

Detailed deployment instructions are available in [`STREAMLIT_COMMUNITY_CLOUD.md`](STREAMLIT_COMMUNITY_CLOUD.md).

---

## Scientific scope and limitations

- The atlas presents the computational outputs associated with the study and does not replace the full manuscript or supplementary information.
- Gene and KO detection indicates functional potential, not direct biochemical activity.
- RDA relationships are presented as exploratory where the global constrained model is not statistically significant.
- Cross-study comparisons with external iron-rich records are descriptive because datasets differ in habitat, sequencing strategy, omics layer and annotation history.
- The additional PATRIC/BV-BRC-derived genome bin is reported separately from the 49 medium- to high-quality MetaWRAP MAGs because of its higher estimated contamination and unavailable GTDB-Tk r89 classification in the supplied outputs.

---

## Citation

Until the article receives its final bibliographic record, cite the manuscript as:

> Pereira LM, Bittencourt JAP, Santos VCA, Alves R, Pires E, Sahoo PK, Guimarães JTF, Simões BG, Moreira-Oliveira RR, Oliveira G, Nunes GL. **Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling.** Original Article, manuscript prepared for submission.

When using CangaMetaG data, figures, scripts or interactive resources, cite both the associated article and this repository. After publication, replace the provisional citation with the definitive journal citation and DOI.

---

## Selected references

The complete bibliography is provided in the manuscript. References below highlight the environmental and computational resources most directly connected to the application and scripts.

1. Sahoo PK, Souza-Filho PWM, Guimarães JTF, et al. Use of multi-proxy approaches to determine the origin and depositional processes in modern lacustrine sediments: Carajás Plateau, Southeastern Amazon, Brazil. *Applied Geochemistry*. 2015;52:130–146. https://doi.org/10.1016/j.apgeochem.2014.11.010

2. Sahoo PK, Guimarães JTF, Souza-Filho PWM, et al. Influence of seasonal variation on the hydro-biogeochemical characteristics of two upland lakes in the southeastern Amazon, Brazil. *Anais da Academia Brasileira de Ciências*. 2016;88:2211–2227. https://doi.org/10.1590/0001-3765201620160354

3. Bankevich A, Nurk S, Antipov D, et al. SPAdes: a new genome assembly algorithm and its applications to single-cell sequencing. *Journal of Computational Biology*. 2012;19:455–477. https://doi.org/10.1089/cmb.2012.0021

4. Mikheenko A, Saveliev V, Gurevich A. MetaQUAST: evaluation of metagenome assemblies. *Bioinformatics*. 2016;32:1088–1090. https://doi.org/10.1093/bioinformatics/btv697

5. Chen IMA, Chu K, Palaniappan K, et al. IMG/M v.5.0: an integrated data management and comparative analysis system for microbial genomes and microbiomes. *Nucleic Acids Research*. 2019;47:D666–D677. https://doi.org/10.1093/nar/gky901

6. Palù M, Basile A, Zampieri G, et al. KEMET: a Python tool for KEGG Module evaluation and microbial genome annotation expansion. *Computational and Structural Biotechnology Journal*. 2022;20:1481–1486. https://doi.org/10.1016/j.csbj.2022.03.015

7. Garber AI, Nealson KH, Okamoto A, et al. FeGenie: a comprehensive tool for the identification of iron genes and iron gene neighborhoods in genome and metagenome assemblies. *Frontiers in Microbiology*. 2020;11:37. https://doi.org/10.3389/fmicb.2020.00037

8. Menzel P, Ng KL, Krogh A. Fast and sensitive taxonomic classification for metagenomics with Kaiju. *Nature Communications*. 2016;7:11257. https://doi.org/10.1038/ncomms11257

9. McMurdie PJ, Holmes S. phyloseq: an R package for reproducible interactive analysis and graphics of microbiome census data. *PLOS ONE*. 2013;8:e61217. https://doi.org/10.1371/journal.pone.0061217

10. Love MI, Huber W, Anders S. Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2. *Genome Biology*. 2014;15:550. https://doi.org/10.1186/s13059-014-0550-8

11. Uritskiy GV, DiRuggiero J, Taylor J. MetaWRAP—a flexible pipeline for genome-resolved metagenomic data analysis. *Microbiome*. 2018;6:158. https://doi.org/10.1186/s40168-018-0541-1

12. Parks DH, Imelfort M, Skennerton CT, Hugenholtz P, Tyson GW. CheckM: assessing the quality of microbial genomes recovered from isolates, single cells, and metagenomes. *Genome Research*. 2015;25:1043–1055. https://doi.org/10.1101/gr.186072.114

13. Chaumeil P-A, Mussig AJ, Hugenholtz P, Parks DH. GTDB-Tk v2: memory friendly classification with the Genome Taxonomy Database. *Bioinformatics*. 2022;38:5315–5316. https://doi.org/10.1093/bioinformatics/btac672

14. Blin K, Shaw S, Kloosterman AM, et al. antiSMASH 6.0: improving cluster detection and comparison capabilities. *Nucleic Acids Research*. 2021;49:W29–W35. https://doi.org/10.1093/nar/gkab335

---

<div align="center">

**CangaMetaG** · Instituto Tecnológico Vale · Amazonian iron-rich lake metagenomics

</div>
