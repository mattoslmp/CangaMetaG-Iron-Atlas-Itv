from __future__ import annotations

"""Canonical sample identifiers shared by taxonomy and IMG/JGI annotations.

The publication uses compact study identifiers (for example ``AM.P1.D``),
while the packaged source tables use IMG/JGI analysis-project IDs, taxon OIDs,
and legacy sample aliases. This module keeps one explicit, auditable mapping so
all app views display the publication identifier and retain database IDs only in
hover tables and downloads.
"""

from pathlib import Path
import re
import numpy as np
import pandas as pd

from ._helpers import BASE_DIR

_SAMPLE_ROWS = [
  ("AM.P1.D", "AM", "Amendoim", "P1", "Dry", "Ga0540489", "3300052670", "AM1.1"),
  ("AM.P1.R", "AM", "Amendoim", "P1", "Rainy", "Ga0541010", "3300052671", "AM1.2"),
  ("AM.P2.D", "AM", "Amendoim", "P2", "Dry", "Ga0541011", "3300052672", "AM2.1"),
  ("AM.P2.R", "AM", "Amendoim", "P2", "Rainy", "Ga0541012", "3300052673", "AM2.2"),
  ("TIA.P1.D", "TIA", "Três Irmãs Adjacent", "P1", "Dry", "Ga0541013", "3300052674", "TI11.1"),
  ("TIA.P1.R", "TIA", "Três Irmãs Adjacent", "P1", "Rainy", "Ga0541014", "3300052675", "TI11.2"),
  ("TIA.P2.D", "TIA", "Três Irmãs Adjacent", "P2", "Dry", "Ga0541015", "3300052676", "TI12.1"),
  ("TIA.P2.R", "TIA", "Três Irmãs Adjacent", "P2", "Rainy", "Ga0541016", "3300052916", "TI12.2"),
  ("TI.P1.D", "TI", "Três Irmãs", "P1", "Dry", "Ga0541017", "3300052677", "TI21.1"),
  ("TI.P1.R", "TI", "Três Irmãs", "P1", "Rainy", "Ga0541018", "3300052678", "TI21.2"),
  ("TI.P2.D", "TI", "Três Irmãs", "P2", "Dry", "Ga0541019", "3300052679", "TI31.1"),
  ("TI.P2.R", "TI", "Três Irmãs", "P2", "Rainy", "Ga0541020", "3300052680", "TI31.2"),
  ("TI.P3.D", "TI", "Três Irmãs", "P3", "Dry", "Ga0541021", "3300052681", "TI32.1"),
  ("TI.P3.R", "TI", "Três Irmãs", "P3", "Rainy", "Ga0541022", "3300052682", "TI32.2"),
  ("TI.P4.D", "TI", "Três Irmãs", "P4", "Dry", "Ga0541023", "3300052683", "TI33.1"),
  ("TI.P4.R", "TI", "Três Irmãs", "P4", "Rainy", "Ga0541024", "3300052684", "TI33.2"),
  ("VI.P1.D", "VI", "Violão", "P1", "Dry", "Ga0541025", "3300052685", "V1.1"),
  ("VI.P1.R", "VI", "Violão", "P1", "Rainy", "Ga0541026", "3300052686", "V1.2"),
  ("VI.P2.D", "VI", "Violão", "P2", "Dry", "Ga0541027", "3300052687", "V2.1"),
  ("VI.P2.R", "VI", "Violão", "P2", "Rainy", "Ga0541028", "3300052688", "V2.2"),
]

_SITE_COORDINATES = {
  "AM.P1": "6°23'54.1\"S 50°22'17.6\"W",
  "AM.P2": "6°24'03.0\"S 50°22'18.8\"W",
  "VI.P1": "6°24'02.5\"S 50°21'06.7\"W",
  "VI.P2": "6°23'52.3\"S 50°21'14.0\"W",
  "TIA.P1": "6°20'51.7\"S 50°26'52.3\"W",
  "TIA.P2": "6°20'47.7\"S 50°26'48.2\"W",
  "TI.P1": "6°21'09.6\"S 50°27'01.9\"W",
  "TI.P2": "6°21'12.7\"S 50°26'39.5\"W",
  "TI.P3": "6°21'19.4\"S 50°26'44.2\"W",
  "TI.P4": "6°21'23.5\"S 50°26'53.6\"W",
}


def _dms_to_decimal(value: str) -> tuple[float, float]:
  match = re.search(
    r"(\d+)°(\d+)'([\d.]+)\"([NS])\s+(\d+)°(\d+)'([\d.]+)\"([EW])",
    str(value),
  )
  if not match:
    return np.nan, np.nan
  lat_d, lat_m, lat_s, lat_h, lon_d, lon_m, lon_s, lon_h = match.groups()
  lat = float(lat_d) + float(lat_m) / 60.0 + float(lat_s) / 3600.0
  lon = float(lon_d) + float(lon_m) / 60.0 + float(lon_s) / 3600.0
  if lat_h == "S":
    lat *= -1
  if lon_h == "W":
    lon *= -1
  return lat, lon


def amazonian_sample_metadata() -> pd.DataFrame:
  rows: list[dict[str, object]] = []
  for sample_id, lake, lake_name, position, season, img_project, taxon_oid, legacy in _SAMPLE_ROWS:
    site = ".".join(sample_id.split(".")[:2])
    coord = _SITE_COORDINATES.get(site, "")
    lat, lon = _dms_to_decimal(coord)
    rows.append({
      "sample.id": sample_id,
      "publication_sample_id": sample_id,
      "lake": lake,
      "lake_name": lake_name,
      "sampling_position": position,
      "site": site,
      "season": season,
      "group": sample_id,
      "lake_season_group": f"{lake}-{'D' if season == 'Dry' else 'R'}",
      "IMG_JGI_analysis_project_id": img_project,
      "IMG_JGI_taxon_oid": taxon_oid,
      "legacy_sample_alias": legacy,
      "taxonomy_matrix_column": f"{img_project}_genes.fna.",
      "table6_matrix_column_pattern": taxon_oid,
      "ENA_study_accession": "ERP137391",
      "environment_feature": "Amazonian lateritic lake sediment",
      "sample_type": "Sediment",
      "geographic_coordinates": coord,
      "lat": lat,
      "lon": lon,
      "collection_date": "Not reported in packaged metadata",
      "source_dataset": "Amazonian lake annotations (Supplementary Table 6)",
    })
  return pd.DataFrame(rows)


def normalize_database_id(value: object) -> str:
  text = str(value or "").strip().strip(".")
  ga = re.search(r"Ga\d{7}", text)
  if ga:
    return ga.group(0)
  oid = re.search(r"(?<!\d)(3\d{9})(?!\d)", text)
  if oid:
    return oid.group(1)
  return text


def publication_sample_id(value: object) -> str:
  text = str(value or "").strip()
  if re.match(r"^(AM|TIA|TI|VI)\.P\d+\.(D|R)$", text):
    return text
  normalized = normalize_database_id(text)
  meta = amazonian_sample_metadata()
  for column in ["IMG_JGI_analysis_project_id", "IMG_JGI_taxon_oid", "legacy_sample_alias", "taxonomy_matrix_column"]:
    matches = meta.loc[meta[column].astype(str).map(normalize_database_id).eq(normalized), "sample.id"]
    if not matches.empty:
      return str(matches.iloc[0])
  return text


def lake_column_metadata(columns: list[object], *, source_dataset: str) -> pd.DataFrame:
  meta = amazonian_sample_metadata().copy()
  rows = []
  for col in columns:
    text = str(col)
    sample_id = publication_sample_id(text)
    hit = meta[meta["sample.id"].eq(sample_id)]
    if hit.empty:
      continue
    record = hit.iloc[0].to_dict()
    record["matrix_column"] = text
    record["source_dataset"] = source_dataset
    rows.append(record)
  return pd.DataFrame(rows)
