#!/usr/bin/env python3
"""Offline integrity checks for the public CangaMetaG Streamlit application."""
from __future__ import annotations

import ast
import hashlib
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
  sys.path.insert(0, str(ROOT))

from src.functional_annotations import build_annotation_dataset, functional_annotation_heatmap
from src.publication_rda import publication_nmds_figure, publication_rda_figure
from src.streamlit_compat import arrow_safe_dataframe
from src.supplementary_database import (
  ST8_ALL_KO_SHEET,
  ST8_IRON_ALL_SHEET,
  counts_table,
  iron_rich_environment_metadata,
  taxonomy_profile_table,
)

EXPECTED_ABSTRACT = (
  "Amazonian lateritic lakes developed on ferruginous canga are seasonally variable, metal-rich systems whose "
  "sediment microbiomes remain poorly characterized. We used shotgun metagenomics to investigate microbial "
  "communities in sediments from Amendoim, Violão, Três Irmãs and Três Irmãs Adjacent lakes during dry and rainy "
  "periods. Coding-sequence taxonomic profiles revealed diverse bacterial and archaeal assemblages and a large "
  "unclassified fraction, indicating substantial underexplored diversity. Lake- and season-associated contrasts "
  "involved methanogenic, ammonia-oxidizing and anaerobic sediment lineages. Non-metric multidimensional scaling "
  "showed partial community overlap, whereas an exploratory, non-significant redundancy analysis placed genus-level "
  "variation along loss-on-ignition, aluminium, silica, sulfur and trace-metal gradients. Functional reconstruction "
  "identified genetic potential for carbon fixation, methane metabolism, nitrogen and sulfur cycling, photosynthesis, "
  "anaerobic respiration and iron metabolism. A curated Kyoto Encyclopedia of Genes and Genomes orthology framework "
  "detected 171 of 195 biogeochemical markers and 132 iron-associated markers. Descriptive cross-study contrasts "
  "distinguished Amazonian canga-lake profiles from external iron-rich records, but were not treated as inferential "
  "tests. We recovered 50 non-redundant metagenome-assembled genomes spanning medium- to high-quality bins, including "
  "lineages related to Acidobacteria, Dehalococcoidia, Nitrospirales, Burkholderiales, Bathyarchaeia, Thermoplasmatota "
  "and Methanoperedens. These results establish a genome-resolved iron metagenomic atlas for tropical lateritic-lake "
  "sediments and a basis for testing how seasonal hydrology and ferruginous geochemistry shape microbial "
  "biogeochemical functions."
)


def require(condition: bool, message: str) -> None:
  if not condition:
    raise RuntimeError(message)


def matrix_sample_columns(frame: pd.DataFrame, id_col: str, name_col: str) -> list[str]:
  return [c for c in frame.columns if c not in {id_col, name_col, "Metabolism", "Biologic Role", "KEGG MODULE"}]


def validate_functional_annotations(rows: list[dict]) -> None:
  expected = {
    ("table6", "KO"): (8045, 20),
    ("table6", "EC number"): (2914, 20),
    ("table6", "PFAM"): (8238, 20),
    ("table8", "KO"): (12144, 67),
    ("table8", "EC number"): (3514, 67),
    ("table8", "PFAM"): (100, 67),
    ("combined", "KO"): (20189, 87),
    ("combined", "EC number"): (3905, 87),
    ("combined", "PFAM"): (8258, 87),
  }
  for (source, annotation), (expected_rows, expected_samples) in expected.items():
    matrix, meta, id_col, name_col = build_annotation_dataset(source, annotation)
    sample_cols = matrix_sample_columns(matrix, id_col, name_col)
    require(len(matrix) == expected_rows, f"{source}/{annotation}: {len(matrix)} rows, expected {expected_rows}")
    require(len(sample_cols) == expected_samples, f"{source}/{annotation}: {len(sample_cols)} samples, expected {expected_samples}")
    require(meta["matrix_column"].astype(str).nunique() == expected_samples, f"{source}/{annotation}: metadata mismatch")
    require(set(sample_cols) == set(meta["matrix_column"].astype(str)), f"{source}/{annotation}: matrix/metadata columns differ")
    # Every selected study must resolve to all its matrix columns.
    for study, group in meta.groupby("study_name", dropna=False):
      expected_study_cols = set(group["matrix_column"].astype(str))
      require(expected_study_cols.issubset(sample_cols), f"{source}/{annotation}/{study}: missing study columns")
    fig, raw, _ = functional_annotation_heatmap(
      matrix, meta, id_col, name_col, sample_cols,
      annotation, source, top_n=min(20, len(matrix)),
    )
    require(fig is not None, f"{source}/{annotation}: heatmap not generated")
    require(len(fig.data[0].x) == expected_samples, f"{source}/{annotation}: heatmap omitted samples")
    require(bool(fig.layout.meta.get("preserve_cell_geometry")), f"{source}/{annotation}: cell geometry not preserved")
    rows.append({"check": f"functional_{source}_{annotation}", "status": "PASS", "rows": len(matrix), "samples": len(sample_cols)})


def validate_st8(rows: list[dict]) -> None:
  all_ko, all_cols = counts_table("table8", ST8_ALL_KO_SHEET, ["KO", "Metabolism", "KO description"])
  iron, iron_cols = counts_table("table8", ST8_IRON_ALL_SHEET, ["Function Id", "Biologic Role", "Function Name"])
  require(len(all_ko) == 189 and len(iron) == 131, "Unexpected ST8 marker row counts")
  require(all_cols == iron_cols, "ST8 all-KO and iron-KO sample columns differ")
  lake_cols = [c for c in all_cols if re.match(r"^(AM|TIA|TI|VI)\.P\d+\.(D|R)$", str(c))]
  external_cols = [c for c in all_cols if c not in lake_cols]
  require(len(lake_cols) == 20, f"Expected 20 lake samples, found {len(lake_cols)}")
  require(len(external_cols) == 67, f"Expected 67 external records, found {len(external_cols)}")
  meta = iron_rich_environment_metadata()
  require(len(meta) == 67, f"Expected 67 ST8 metadata rows, found {len(meta)}")
  require(meta["matrix_column"].astype(str).nunique() == 67, "ST8 matrix-column metadata is not unique")
  require(set(external_cols) == set(meta["matrix_column"].astype(str)), "ST8 external matrix and metadata columns differ")
  sediment_cols = set(meta.loc[meta["sample_type"].eq("Sediment"), "matrix_column"].astype(str))
  require(len(sediment_cols) == 14, f"Expected 14 external sediment records, found {len(sediment_cols)}")
  require(sediment_cols.issubset(external_cols), "Sediment subset contains non-matrix columns")
  rows.append({"check": "st8_complete_columns", "status": "PASS", "rows": len(all_ko), "samples": len(all_cols)})
  rows.append({"check": "st8_external_records", "status": "PASS", "rows": len(meta), "samples": len(external_cols)})
  rows.append({"check": "st8_sediment_subset", "status": "PASS", "rows": len(sediment_cols), "samples": len(lake_cols) + len(sediment_cols)})


def validate_taxonomy_and_ordination(rows: list[dict]) -> None:
  profile = taxonomy_profile_table("Phylum — Bacteria", "Individual samples")
  require(profile["group"].nunique() == 20, "Taxonomy does not expose all 20 publication samples")
  require(not profile["group"].astype(str).str.startswith("Ga").any(), "IMG project IDs are still used as displayed taxonomy groups")
  require(profile["IMG_JGI_analysis_project_id"].astype(str).str.startswith("Ga").any(), "IMG project IDs were not retained as hover metadata")
  _fig, sites, env, taxa = publication_rda_figure(ROOT)
  require(not sites.empty and not env.empty and not taxa.empty, "RDA data unavailable")
  require("Publication sample IDs" in sites.columns and "IMG_JGI_analysis_project_id" in sites.columns, "RDA hover metadata missing")
  _fig, scores = publication_nmds_figure(ROOT)
  require(not scores.empty and "IMG_JGI_analysis_project_id" in scores.columns, "NMDS hover metadata missing")
  require(scores["Sample"].astype(str).str.match(r"^(AM|TIA|TI|VI)\.P\d+\.(D|R)$").all(), "NMDS labels are not publication sample IDs")
  rows.append({"check": "taxonomy_publication_ids", "status": "PASS", "rows": len(profile), "samples": profile["group"].nunique()})
  rows.append({"check": "ordination_hover_metadata", "status": "PASS", "rows": len(scores), "samples": scores["Sample"].nunique()})


def validate_kegg_interaction(rows: list[dict]) -> None:
  pairs = [
    (
      "MAG",
      ROOT / "data/module_figure_inputs/SupplementaryFigure37_MAG_KEGG_module_completeness_heatmap_species_MAGnumber_KEMET_style_3state_thematic_status.csv",
      ROOT / "data/final_kegg_st8_update/MAG_KEGG_module_completeness_STATUS_species_MAGnumber_3state.csv",
    ),
    (
      "Metagenome",
      ROOT / "data/final_publication_derived/SupplementaryFigure38_metagenome_KEGG_module_completeness_heatmap_thematic_app_status.csv",
      ROOT / "data/final_kegg_st8_update/KEMET_lagoon_all_metagenomes_module_completeness_STATUS_3state.csv",
    ),
  ]
  for label, article_path, full_path in pairs:
    require(article_path.exists(), f"{label}: article status matrix missing")
    require(full_path.exists(), f"{label}: full status matrix missing")
    article = pd.read_csv(article_path, keep_default_na=False)
    full = pd.read_csv(full_path, keep_default_na=False)
    require(len(article) > 0 and len(full) > len(article), f"{label}: interactive matrix is not broader than article subset")
    sample = full.set_index(full.columns[0])
    norm = sample.map(lambda value: "Complete" if str(value).strip().casefold() == "complete" else "1 block missing" if str(value).strip().casefold() in {"1 block missing", "one block missing"} else "2 blocks missing" if str(value).strip().casefold() in {"2 blocks missing", "two blocks missing"} else "Incomplete" if str(value).strip().casefold() == "incomplete" else "Missing data")
    complete = norm.loc[norm.eq("Complete").any(axis=1)]
    require(len(complete.head(5)) == 5 and len(complete.head(10)) == 10, f"{label}: module-count control cannot change row count")
    rows.append({"check": f"kegg_dynamic_{label.lower()}", "status": "PASS", "rows": len(full), "samples": full.shape[1] - 1})


def validate_streamlit_compatibility(rows: list[dict]) -> None:
  app_source = (ROOT / "app.py").read_text(encoding="utf-8")
  require("use_container_width" not in app_source, "Deprecated use_container_width remains in app.py")
  require("width=\"stretch\"" in app_source, "New Streamlit width API is not used")
  require(EXPECTED_ABSTRACT in app_source, "App abstract does not match the article abstract")
  ast.parse(app_source)
  mixed = pd.DataFrame({"Unnamed: 2": [1.5, "Completeness (Cpn): CheckM", 2], "Unnamed: 5": [1, b"two", 3]})
  safe = arrow_safe_dataframe(mixed)
  require(all(str(dtype).startswith("string") for dtype in safe.dtypes), "Mixed Excel columns were not normalized for Arrow")
  require((ROOT / ".streamlit/config.toml").exists(), "Streamlit config is missing")
  require((ROOT / ".python-version").read_text().strip() == "3.12", "Python 3.12 deployment marker is missing")
  require("streamlit==1.60.0" in (ROOT / "requirements.txt").read_text(), "Streamlit is not pinned")
  require(not (ROOT / "environment.yml").exists(), "Root environment.yml would override requirements.txt on Community Cloud")
  rows.append({"check": "streamlit_width_and_arrow", "status": "PASS", "rows": len(safe), "samples": len(safe.columns)})
  rows.append({"check": "streamlit_community_layout", "status": "PASS", "rows": 1, "samples": 1})


def main() -> int:
  rows: list[dict] = []
  validate_functional_annotations(rows)
  validate_st8(rows)
  validate_taxonomy_and_ordination(rows)
  validate_kegg_interaction(rows)
  validate_streamlit_compatibility(rows)
  report = pd.DataFrame(rows)
  out = ROOT / "validation" / "APP_CONTENT_VALIDATION.tsv"
  out.parent.mkdir(parents=True, exist_ok=True)
  report.to_csv(out, sep="\t", index=False)
  digest = hashlib.sha256(out.read_bytes()).hexdigest()
  md = ROOT / "validation" / "APP_CONTENT_VALIDATION.md"
  md.write_text(
    "# Application content validation\n\n"
    + report.to_markdown(index=False)
    + f"\n\nResult: **PASS**\n\nTSV SHA-256: `{digest}`\n",
    encoding="utf-8",
  )
  print(report.to_string(index=False))
  print("APP_CONTENT_VALIDATION_PASS")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
