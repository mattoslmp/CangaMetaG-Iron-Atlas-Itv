<div align="center">

# Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling

### CangaMetaG — Interactive Iron Metagenomic Atlas of Amazonian Canga Lakes

[![Streamlit](https://img.shields.io/badge/Streamlit-interactive%20atlas-FF4B4B?logo=streamlit&logoColor=white)](https://cangametag-iron-atlas-itv.streamlit.app)
![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![Metagenomics](https://img.shields.io/badge/omics-shotgun%20metagenomics-2A9D8F)
![Study](https://img.shields.io/badge/study-original%20article-264653)

**[Open the interactive atlas](https://cangametag-iron-atlas-itv.streamlit.app)** · **[Figure reproduction index](FIGURE_REPRODUCTION_COMMANDS.md)** · **[Deployment guide](STREAMLIT_COMMUNITY_CLOUD.md)**

</div>

---

## Overview

**CangaMetaG** is the interactive scientific resource associated with the study of microbial communities inhabiting iron-rich lateritic lake sediments in Serra dos Carajás, southeastern Amazonia, Brazil. The atlas integrates taxonomic, functional and genome-resolved information from sediment shotgun metagenomes collected in **Amendoim (AM), Violão (VI), Três Irmãs (TI)** and **Três Irmãs Adjacent (TIA)** lakes during dry and rainy periods.

The repository provides the Streamlit application, curated scientific matrices, main and supplementary figures, downloadable tables, MAG information, KEGG/KEMET module-completeness results, curated KEGG Orthology marker panels, FeGenie-supported iron-metabolism annotations and antiSMASH biosynthetic gene-cluster outputs.

> **Scientific interpretation:** metagenomic genes, markers and reconstructed modules represent encoded biological potential. They do not, by themselves, demonstrate pathway activity or process rates.

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
| **Manuscript status** | Prepared for submission |

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

## Scientific scope of CangaMetaG

The atlas connects several complementary layers of evidence:

| Scientific layer | Content available in the atlas |
|---|---|
| **Sampling context** | Lake, season, sampling position and available physicochemical metadata |
| **Taxonomy** | Bacterial and archaeal profiles from coding-sequence assignments |
| **Community ecology** | Rarefaction, alpha diversity, Bray–Curtis dissimilarity, NMDS, PCoA, PCA and RDA |
| **Functional potential** | Functional annotations, KEGG Orthology markers and pathway summaries |
| **Biogeochemical cycling** | Carbon fixation, methane, nitrogen, sulfur, photosynthesis and anaerobic respiration markers |
| **Iron metabolism** | FeGenie categories and 132 curated iron-associated KOs |
| **KEGG/KEMET** | Module-completeness matrices for metagenomes, MAGs and comparative iron-rich records |
| **Genome-resolved ecology** | Quality, taxonomy, abundance and functional annotation of 50 non-redundant genome bins |
| **Natural-product potential** | antiSMASH biosynthetic gene-cluster regions, products and report links |
| **Scientific resources** | Main figures, supplementary figures, source tables and downloadable data |

---

# Materials and Methods

The sections below summarize the experimental and computational procedures described in the manuscript. Reference numbering follows the manuscript bibliography.

## 1. Study area and sampling design

Violão, Amendoim and Três Irmãs are perennial highland lakes located in the Carajás National Forest, southeastern Amazonia, Brazil, on ferruginous lateritic plateaus at approximately **695–765 m above sea level** [8,9,14,15]. Três Irmãs is the largest system and becomes connected during the rainy season; during the dry season, an adjacent water body was considered separately as Três Irmãs Adjacent Lake.

Sediments were collected during the **rainy season in March** and the **dry season in September**. Sampling positions followed longitudinal profiles informed by bathymetric maps and drainage patterns. Two sites were sampled in AM, VI and TIA, and four sites were sampled in TI because of its larger area.

Surface sediments (**30–40 mL**) were collected with an **Ekman–Birge dredge**, transferred to sterile 50 mL polypropylene tubes and stored at **−20 °C** until DNA extraction. Geographic coordinates and sampling metadata are provided in the associated supplementary resources.

## 2. DNA extraction, library preparation and sequencing

Total DNA was extracted from **20 sediment samples**, using approximately **250 mg of sediment per extraction**, with the PowerSoil DNA Isolation Kit. Duplicate extractions were performed for each sample. DNA integrity and concentration were evaluated by 1% agarose gel electrophoresis and Qubit 3.0 fluorometry.

Shotgun paired-end metagenomic libraries were prepared from approximately **50 ng DNA** using enzymatic random fragmentation and the SureSelectQXT kit. Fragmented DNA was purified with AMPure XP beads, amplified with Illumina-adapter primers, purified, quantified by Qubit and evaluated on an Agilent 2100 Bioanalyzer with the High Sensitivity DNA kit.

Libraries were pooled and sequenced on an **Illumina NextSeq 500** using a NextSeq 500 v2 high-output 300-cycle kit.

## 3. Read processing, assembly and functional annotation

Raw reads were quality-filtered with **PRINSEQ**, retaining reads with an average quality score of at least 20, and were inspected with **FastQC** [18,19]. Trimmed reads were assembled *de novo* with **SPAdes v3.7.0** in metagenomic mode:

```bash
spades.py --meta --only-assembler -k 21,33,55,77,121
```

Assembly quality was evaluated with **MetaQUAST/QUAST v3.0**, including N50, L50 and largest-contig metrics [20,21]. Coding sequences and scaffold-level functional annotations were generated with the **IMG/MER** pipeline [22].

KEGG modules were reconstructed through a local **KAAS-based workflow**, and module completeness was evaluated with an adapted **KEMET** procedure [23–26]. Module states were summarized as:

- **Complete**;
- **one block missing**;
- **two blocks missing**;
- **incomplete**;
- **absent or not detected**, where applicable in the atlas.

Iron-metabolism potential was evaluated with **FeGenie**, covering iron acquisition, storage, oxidation, reduction and iron-gene neighbourhoods in metagenomes and MAGs [27].

## 4. Taxonomic profiling

IMG/MER-predicted coding sequences were taxonomically assigned with **Kaiju v1.9.0** against the `nr_euk` database, which includes proteins from Archaea, Bacteria, viruses, fungi and microbial eukaryotes [28]. Kaiju outputs were converted into OTU and taxonomy matrices with the `kaiju2-data-parser` workflow and processed in R using **dplyr** and **phyloseq** [29,30].

Taxonomic summaries were generated for Bacteria and Archaea at multiple ranks, while preserving the unclassified fraction as an important component of the sediment microbial diversity.

## 5. Alpha diversity, beta diversity and ordination

For alpha diversity and rarefaction, the CDS OTU matrix was rarefied to a fixed depth of **32,999 CDS**, corresponding to the smallest predicted-CDS sample depth and retaining all 20 samples. The same depth was used for rarefaction curves and for **Observed OTUs**, **Chao1 richness** and **Shannon diversity**. Visualizations and statistical summaries were produced with **ggplot2** [31].

Beta diversity was evaluated using **Bray–Curtis dissimilarity** calculated from `log2(x + 1)`-transformed taxonomic data. **Non-metric multidimensional scaling (NMDS)** was used to visualize community structure, and differences among groups were assessed by **PERMANOVA with 999 permutations** using `adonis` in **vegan** [32].

Genus-level community profiles were integrated with physicochemical measurements at ten sampling positions. Community data were **Hellinger-transformed**, environmental predictors were standardized, and six non-collinear variables were retained for redundancy analysis:

- Fe₂O₃;
- SiO₂;
- Al₂O₃;
- total sulfur;
- Cu;
- Pb.

The global constrained RDA model was evaluated with 999 permutations. Because the global model was not significant, environmental vectors and taxon relationships are presented as **exploratory covariation**, not as confirmed causal associations.

## 6. Curated KO biomarkers for biogeochemical cycling and iron metabolism

A marker-based framework was developed to complement KEGG module reconstruction. The analysis began with a published 77-marker set and was expanded to **195 KEGG Orthology biomarkers** representing:

- seven carbon-fixation pathway categories;
- methane metabolism;
- nitrogen cycling;
- sulfur cycling;
- oxygenic and anoxygenic photosynthesis;
- anaerobic ammonium oxidation;
- DMSO-linked anaerobic oxidative phosphorylation;
- alternative nitrogenase forms;
- additional carbon, nitrogen and respiratory functions.

Of the 195 biogeochemical markers, **171 were detected** in the Amazonian sediment annotation dataset. The marker panel was interpreted as a complementary line of evidence and not as a replacement for pathway/module reconstruction.

The iron-marker framework contained **132 iron-associated KOs**, grouped into 12 biological categories:

1. heme synthesis;
2. heme transport;
3. iron acquisition;
4. iron regulation;
5. iron oxidation;
6. iron reduction;
7. iron storage;
8. iron transport;
9. magnetosome formation;
10. siderophore secretion;
11. siderophore synthesis;
12. siderophore transport.

## 7. Differential abundance and directional contrasts

Within-Amazonian KO differential abundance was evaluated using **DESeq2** and **ALDEx2**. KO counts were normalized using the geometric mean of pairwise ratios (**GMPR**), and DESeq2 size factors were estimated before fitting negative-binomial models with Wald tests and parametric dispersion estimation [34–36].

The analysis included **12 unique directional comparisons** and **2,052 all-KO tests**. Two tests for the mercury reductase marker **K00320 (`mer`)** reached `q < 0.05`, whereas the within-Amazonian iron-KO subset did not yield tests significant at `q < 0.05`. Consequently, the highest directional log₂ fold-change markers are presented as descriptive contrasts unless explicitly identified as FDR-significant.

For broader environmental context, the 20 Amazonian metagenomes were compared descriptively with **67 external iron-rich metagenomic and metatranscriptomic records** obtained from IMG/JGI. Counts were transformed into within-sample marker-panel relative abundances, group means were calculated and directional log₂ mean ratios were estimated after adding a small pseudocount.

This cross-study analysis is **descriptive rather than inferential**, because the external records differ in habitat, sequencing strategy, omics layer and annotation history.

## 8. MAG reconstruction, quality assessment and annotation

MAGs were reconstructed using a co-assembly strategy in which reads from all samples were pooled. Co-assembly was performed with **metaSPAdes v3.15.1**, using automatic k-mer selection, co-correction and default parameters. Genome binning used the **MetaWRAP v1.3** binning module integrating:

- metaBAT2;
- CONCOCT;
- MaxBin2.

Bins were consolidated into a refined non-redundant set using `bin-refinement` with Binning_refiner and DAS Tool, with a minimum completeness of 50% and a maximum contamination of 5% for the refined MetaWRAP set. Reassembly used the MetaWRAP `Reassemble_bins` module [37].

The final catalogue retained **50 non-redundant genome bins**:

- **49 medium- to high-quality MAGs** reconstructed through the metaSPAdes/MetaWRAP workflow;
- **one additional PATRIC/BV-BRC-derived bin**, retained as MAG.49 and reported separately because its estimated completeness was 62.62%, contamination was 14.77%, and it lacked a GTDB-Tk r89 classification in the supplied outputs.

MAG quality was assessed with **CheckM v1.2.1** and **BV-BRC** [38,39]. Taxonomic annotation integrated **GTDB-Tk v2.1.1** with GTDB R07-RS207, CheckM, MetaWRAP `Classify_bins`, BV-BRC, Kaiju and rRNA evidence [28,37–40]. Quality interpretation followed MIMAG-related completeness and contamination criteria [39,41], and species-level assignments were treated conservatively in light of ANI-based species boundaries [42].

## 9. Biosynthetic gene-cluster analysis

Biosynthetic gene-cluster potential was evaluated from the supplied **antiSMASH v8.0.4** output directories. Original HTML and JSON reports were parsed to retrieve:

- BGC regions and protoclusters;
- predicted products and biosynthetic categories;
- MIBiG matches, when available;
- MAGs for which no BGC region was detected.

The final parser retained identifiers from MAG.1 to MAG.50 and generated the corresponding region-level summaries used by the application and Supplementary Table 11 [43].

## 10. Interactive platform implementation

The accompanying Streamlit platform was developed to provide interactive access to:

- eight main figures;
- 69 supplementary figures;
- supplementary tables;
- MAG quality, taxonomy and annotation summaries;
- KEGG/KEMET module matrices;
- curated KO-marker panels;
- antiSMASH BGC outputs.

Packaged CSV and XLSX files are loaded through a centralized scientific data layer. Interactive resources include searchable and downloadable tables, taxonomic and functional heatmaps, diversity and ordination panels, RDA visualizations, MAG summaries and antiSMASH region tables.

The KEGG module-completeness views use consistent categorical states and colours:

| State | Colour |
|---|---|
| Complete | `#2A9D8F` |
| One block missing | `#90BE6D` |
| Two blocks missing | `#E9C46A` |
| Incomplete | `#F4A6A6` |
| Absent or not detected | `#F1F5F9` |

---

## Repository organization

```text
CangaMetaG-Iron-Atlas-Itv/
├── app.py                         # Main Streamlit application
├── src/                           # Reusable scientific and application modules
├── scripts/                       # Figure, table, document and workflow scripts
│   ├── figures/                   # Focused main/supplementary figure generators
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

### `app.py`

Primary entry point for the Streamlit application. It assembles the interface and connects taxonomic, functional, ecological, genome-resolved and publication resources.

### `src/`

Reusable modules supporting:

- supplementary-table loading;
- taxonomic visualization;
- diversity and ordination;
- RDA and integrated-omics views;
- functional annotation;
- KEGG/KEMET module completeness;
- MAG annotation and genome organization;
- antiSMASH report visualization;
- sample metadata;
- runtime paths and dependency checks;
- Plotly rendering and export.

### `data/`

Scientific inputs and derived matrices used by the app and figure-generation workflows, including taxonomic counts, functional annotations, sampling metadata, MAG data, KEGG/KEMET matrices, curated KO panels and publication source data.

### `tables/`

Editable main and supplementary tables distributed with the project, principally in CSV and Excel formats.

### `outputs/`

Publication-quality figures and application-display resources. Article outputs and application assets are kept in clearly designated locations.

---

## Organization of the scripts

The `scripts/` tree is organized by **scientific function**, not as a single mandatory sequential pipeline.

### General scripts in `scripts/`

Coordinate workflows that involve multiple data sources or groups of figures, including sampling maps, broad taxonomic outputs, publication consolidation, workflow diagrams and figure-to-script documentation.

### `scripts/figures/`

Contains focused generators for individual main figures or defined groups of supplementary figures, including:

- bacterial and archaeal taxonomic profiles;
- MAG quality and abundance;
- KO differential-abundance summaries;
- biogeochemical and iron-marker heatmaps;
- KEGG/KEMET module-completeness figures;
- integrated environmental and taxonomic visualizations.

### `scripts/final_publication_figures/`

Contains specialized routines used for final publication analyses, such as fixed-depth rarefaction, alpha-diversity reconstruction and figure-specific statistical or graphical processing.

### `scripts/documents/`

Contains workflows that assemble or update manuscript-related documents and supplementary material from final tables and figures.

### Figure-to-script mapping

The exact script, command and input files associated with each main and supplementary figure are indexed in:

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

Using Conda:

```bash
conda env create -f environment.yml
conda activate cangametag-reproducibility
```

Using a Python virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Windows PowerShell activation:

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

## Streamlit Community Cloud

Recommended deployment settings:

```text
Repository: mattoslmp/CangaMetaG-Iron-Atlas-Itv
Branch: main
Main file path: app.py
Python version: 3.12
```

Public application:

### https://cangametag-iron-atlas-itv.streamlit.app

Additional deployment information is available in [`STREAMLIT_COMMUNITY_CLOUD.md`](STREAMLIT_COMMUNITY_CLOUD.md).

---

## Reproducing publication figures

Run figure commands from the repository root so that repository-relative input and output paths remain consistent.

Examples:

```bash
python scripts/generate_amazon_coordinate_figure.py --base-dir .
python scripts/generate_final_domain_taxonomy_figures.py --base-dir .
python scripts/figures/generate_figure7.py --base-dir .
python scripts/figures/generate_figure8.py --base-dir .
```

For the complete command index, consult [`FIGURE_REPRODUCTION_COMMANDS.md`](FIGURE_REPRODUCTION_COMMANDS.md).

---

## Citation

Until the article receives its final bibliographic record, cite the manuscript as:

> Pereira LM, Bittencourt JAP, Santos VCA, Alves R, Pires E, Sahoo PK, Guimarães JTF, Simões BG, Moreira-Oliveira RR, Oliveira G, Nunes GL. **Iron-rich Amazonian lateritic lake sediments harbor diverse microbial communities with biogeochemical potential relevant to carbon and methane cycling.** Original Article, manuscript prepared for submission.

When using data, figures, scripts or interactive resources from CangaMetaG, cite both the associated article and this repository. After journal publication, the definitive journal citation and DOI should replace the provisional citation above.

---

## Selected references from the manuscript

The numbering below follows the manuscript. This section highlights the environmental, analytical and computational references most directly connected to the atlas; the complete bibliography remains part of the article.

1. Golder Associates. *Estudo de Impacto Ambiental, EIA Projeto Ferro Carajás S11D*. Vol. II-A. 2010.

2. Sahoo PK, Souza-Filho PWM, Guimarães JTF, et al. Use of multi-proxy approaches to determine the origin and depositional processes in modern lacustrine sediments: Carajás Plateau, Southeastern Amazon, Brazil. *Applied Geochemistry*. 2015;52:130–146. https://doi.org/10.1016/j.apgeochem.2014.11.010

4. Gagen EJ, Levett A, Paz A, et al. Biogeochemical processes in canga ecosystems: armoring of iron ore against erosion and importance in iron duricrust restoration in Brazil. *Ore Geology Reviews*. 2019;107:582–593. https://doi.org/10.1016/j.oregeorev.2019.03.013

8. Sahoo PK, Guimarães JTF, Souza-Filho PWM, et al. Influence of seasonal variation on the hydro-biogeochemical characteristics of two upland lakes in the southeastern Amazon, Brazil. *Anais da Academia Brasileira de Ciências*. 2016;88:2211–2227. https://doi.org/10.1590/0001-3765201620160354

9. Silva MS, Guimarães JTF, Souza-Filho PWM, et al. Morphology and morphometry of upland lakes over lateritic crust, Serra dos Carajás, southeastern Amazon region. *Anais da Academia Brasileira de Ciências*. 2018;90:1309–1325. https://doi.org/10.1590/0001-3765201820170349

20. Bankevich A, Nurk S, Antipov D, et al. SPAdes: a new genome assembly algorithm and its applications to single-cell sequencing. *Journal of Computational Biology*. 2012;19:455–477. https://doi.org/10.1089/cmb.2012.0021

21. Mikheenko A, Saveliev V, Gurevich A. MetaQUAST: evaluation of metagenome assemblies. *Bioinformatics*. 2016;32:1088–1090. https://doi.org/10.1093/bioinformatics/btv697

22. Chen IMA, Chu K, Palaniappan K, et al. IMG/M v.5.0: an integrated data management and comparative analysis system for microbial genomes and microbiomes. *Nucleic Acids Research*. 2019;47:D666–D677. https://doi.org/10.1093/nar/gky901

23. Palù M, Basile A, Zampieri G, et al. KEMET: a Python tool for KEGG Module evaluation and microbial genome annotation expansion. *Computational and Structural Biotechnology Journal*. 2022;20:1481–1486. https://doi.org/10.1016/j.csbj.2022.03.015

24. Moriya Y, Itoh M, Okuda S, Yoshizawa AC, Kanehisa M. KAAS: an automatic genome annotation and pathway reconstruction server. *Nucleic Acids Research*. 2007;35:W182–W185. https://doi.org/10.1093/nar/gkm321

25. Kanehisa M, Sato Y, Morishima K. BlastKOALA and GhostKOALA: KEGG tools for functional characterization of genome and metagenome sequences. *Journal of Molecular Biology*. 2016;428:726–731. https://doi.org/10.1016/j.jmb.2015.11.006

26. Aramaki T, Blanc-Mathieu R, Endo H, et al. KofamKOALA: KEGG Ortholog assignment based on profile HMM and adaptive score threshold. *Bioinformatics*. 2020;36:2251–2252. https://doi.org/10.1093/bioinformatics/btz859

27. Garber AI, Nealson KH, Okamoto A, et al. FeGenie: a comprehensive tool for the identification of iron genes and iron gene neighborhoods in genome and metagenome assemblies. *Frontiers in Microbiology*. 2020;11:37. https://doi.org/10.3389/fmicb.2020.00037

28. Menzel P, Ng KL, Krogh A. Fast and sensitive taxonomic classification for metagenomics with Kaiju. *Nature Communications*. 2016;7:11257. https://doi.org/10.1038/ncomms11257

30. McMurdie PJ, Holmes S. phyloseq: an R package for reproducible interactive analysis and graphics of microbiome census data. *PLOS ONE*. 2013;8:e61217. https://doi.org/10.1371/journal.pone.0061217

33. Salazar G, Paoli L, Alberti A, et al. Gene expression changes and community turnover differentially shape the global ocean metatranscriptome. *Cell*. 2019;179:1068–1083.e21. https://doi.org/10.1016/j.cell.2019.10.014

35. Love MI, Huber W, Anders S. Moderated estimation of fold change and dispersion for RNA-seq data with DESeq2. *Genome Biology*. 2014;15:550. https://doi.org/10.1186/s13059-014-0550-8

36. Fernandes AD, Macklaim JM, Linn TG, Reid G, Gloor GB. Unifying the analysis of high-throughput sequencing datasets by compositional data analysis. *Microbiome*. 2014;2:15. https://doi.org/10.1186/2049-2618-2-15

37. Uritskiy GV, DiRuggiero J, Taylor J. MetaWRAP—a flexible pipeline for genome-resolved metagenomic data analysis. *Microbiome*. 2018;6:158. https://doi.org/10.1186/s40168-018-0541-1

38. Olson RD, Assaf R, Brettin T, et al. Introducing the Bacterial and Viral Bioinformatics Resource Center (BV-BRC): a resource combining PATRIC, IRD and ViPR. *Nucleic Acids Research*. 2023;51:D678–D689. https://doi.org/10.1093/nar/gkac1003

39. Parks DH, Imelfort M, Skennerton CT, Hugenholtz P, Tyson GW. CheckM: assessing the quality of microbial genomes recovered from isolates, single cells, and metagenomes. *Genome Research*. 2015;25:1043–1055. https://doi.org/10.1101/gr.186072.114

40. Chaumeil P-A, Mussig AJ, Hugenholtz P, Parks DH. GTDB-Tk v2: memory friendly classification with the Genome Taxonomy Database. *Bioinformatics*. 2022;38:5315–5316. https://doi.org/10.1093/bioinformatics/btac672

41. Bowers RM, Kyrpides NC, Stepanauskas R, et al. Minimum information about a single amplified genome and a metagenome-assembled genome of bacteria and archaea. *Nature Biotechnology*. 2017;35:725–731. https://doi.org/10.1038/nbt.3893

42. Jain C, Rodriguez-R LM, Phillippy AM, Konstantinidis KT, Aluru S. High-throughput ANI analysis of 90K prokaryotic genomes reveals clear species boundaries. *Nature Communications*. 2018;9:5114. https://doi.org/10.1038/s41467-018-07641-9

43. Blin K, Shaw S, Kloosterman AM, et al. antiSMASH 6.0: improving cluster detection and comparison capabilities. *Nucleic Acids Research*. 2021;49:W29–W35. https://doi.org/10.1093/nar/gkab335

61. Emerson D, Fleming EJ, McBeth JM. Iron-oxidizing bacteria: an environmental and genomic perspective. *Annual Review of Microbiology*. 2010;64:561–583. https://doi.org/10.1146/annurev.micro.112408.134208

62. Weber KA, Achenbach LA, Coates JD. Microorganisms pumping iron: anaerobic microbial iron oxidation and reduction. *Nature Reviews Microbiology*. 2006;4:752–764. https://doi.org/10.1038/nrmicro1490

63. Melton ED, Swanner ED, Behrens S, Schmidt C, Kappler A. The interplay of microbially mediated and abiotic reactions in the biogeochemical Fe cycle. *Nature Reviews Microbiology*. 2014;12:797–808. https://doi.org/10.1038/nrmicro3347

64. Crowe SA, Jones C, Katsev S, et al. Photoferrotrophs thrive in an Archean ocean analogue. *Proceedings of the National Academy of Sciences USA*. 2008;105:15938–15943. https://doi.org/10.1073/pnas.0805313105

65. Crowe SA, Katsev S, Leslie K, et al. The methane cycle in ferruginous Lake Matano. *Geobiology*. 2011;9:61–78. https://doi.org/10.1111/j.1472-4669.2010.00257.x

66. Vuillemin A, Friese A, Alawi M, et al. Geomicrobiological features of ferruginous sediments from Lake Towuti, Indonesia. *Frontiers in Microbiology*. 2016;7:1007. https://doi.org/10.3389/fmicb.2016.01007

67. Friese A, Bauer K, Glombitza C, et al. Organic matter mineralization in modern and ancient ferruginous sediments. *Nature Communications*. 2021;12:2216. https://doi.org/10.1038/s41467-021-22453-0

68. Druschel GK, Baker BJ, Gihring TM, Banfield JF. Acid mine drainage biogeochemistry at Iron Mountain, California. *Geochemical Transactions*. 2004;5:13–32. https://doi.org/10.1186/1467-4866-5-13

69. Tyson GW, Chapman J, Hugenholtz P, et al. Community structure and metabolism through reconstruction of microbial genomes from the environment. *Nature*. 2004;428:37–43. https://doi.org/10.1038/nature02340

70. Singer E, Heidelberg JF, Dhillon A, Edwards KJ. Metagenomic insights into the dominant Fe(II)-oxidizing Zetaproteobacteria from an iron mat at Lō‘ihi, Hawai‘i. *Frontiers in Microbiology*. 2013;4:52. https://doi.org/10.3389/fmicb.2013.00052

71. McAllister SM, Polson SW, Butterfield DA, et al. Validating the Cyc2 neutrophilic iron oxidation pathway using meta-omics of Zetaproteobacteria iron mats at marine hydrothermal vents. *mSystems*. 2020;5:e00553-19. https://doi.org/10.1128/mSystems.00553-19

72. Bardgett RD, van der Putten WH. Belowground biodiversity and ecosystem functioning. *Nature*. 2014;515:505–511. https://doi.org/10.1038/nature13855

---

## Scientific use and responsibility

CangaMetaG is intended for scientific exploration, reproducible research and transparent access to the processed resources associated with the study. Users should preserve sample identifiers, units, metadata context and the distinction between descriptive and inferential analyses when reusing the data.

The authors retain responsibility for the scientific interpretation of the manuscript. Third-party users remain responsible for validating derived analyses and for citing the original article, datasets and software tools.

---

## Contact

**Gisele Lopes Nunes**  
Instituto Tecnológico Vale  
`gisele.nunes@itv.org`

**Repository and application:** Leandro de Mattos Pereira  
`leandro.pereira@pq.itv.org`
