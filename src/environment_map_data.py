#!/usr/bin/env python3
"""Shared external-environment coordinate preparation for the app and article."""
from __future__ import annotations
from pathlib import Path
import pandas as pd


def load_external_environment_coordinates(base_dir: Path | str) -> pd.DataFrame:
  base=Path(base_dir)
  src=base/'data/st8_metadata_curated.csv'
  df=pd.read_csv(src,low_memory=False)
  flag=df.get('include_in_selected_ST8',False)
  if hasattr(flag,'fillna'):
    df=df[flag.fillna(False).astype(bool)].copy()
  df['lat']=pd.to_numeric(df.get('Latitude'),errors='coerce')
  df['lon']=pd.to_numeric(df.get('Longitude'),errors='coerce')
  df=df.dropna(subset=['lat','lon']).copy()
  df['dataset_group']=df.get('ST8_group','').astype(str)
  df['geographic_location']=df.get('Geographic Location','').astype(str)
  df['sample_description']=df.get('Genome Name / Sample Name','').astype(str)
  df['habitat']=df.get('Habitat','').astype(str)
  df['environment_feature']=df.get('Specific Ecosystem','').astype(str)
  df['isolation_country']=df.get('Geographic Location','').astype(str).str.split(':').str[0]
  df['sample_id']=df.get('ST8_matrix_column',df.get('sample_id_created_this_study','')).astype(str)
  keep=['dataset_group','geographic_location','sample_description','habitat','environment_feature','isolation_country','lat','lon','sample_id','data_layer','NCBI Bioproject Accession','NCBI Biosample Accession','SRA ID','Study Name','Ecosystem Type','Specific Ecosystem','ST8_group']
  out=df[[c for c in keep if c in df.columns]].drop_duplicates(subset=['dataset_group','geographic_location','lat','lon']).sort_values(['dataset_group','geographic_location','lat','lon']).reset_index(drop=True)
  out.insert(0,'Environment_ID',[f'ENV{i:02d}' for i in range(1,len(out)+1)])
  return out
