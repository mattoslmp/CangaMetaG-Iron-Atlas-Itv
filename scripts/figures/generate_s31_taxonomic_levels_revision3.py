#!/usr/bin/env python3
"""Generate separate Supplementary Figure 31 heatmaps by taxonomic level."""
from __future__ import annotations
from pathlib import Path
import argparse, shutil, re
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

LEVEL_SPECS=[('Phylum',14,'A'),('Order',20,'B'),('Family',23,'C')]

def short_group(x):
  layer='MGX' if 'Metagenomics' in x else ('MTX' if 'Metatranscriptomics' in x else '')
  names=[('Richmond Mine','Richmond AMD'),('Akron','Akron AMD'),('Lake Towuti','Lake Towuti'),('Lake Matano','Lake Matano'),('Lake Superior','Lake Superior'),('Burr Oak','Burr Oak control'),('Hydrothermal','Hydrothermal mats')]
  for key,name in names:
    if key in x:return f'{name} | {layer}'
  return str(x)[:32]

def taxon_name(raw,level):
  parts=[p.strip() for p in str(raw).split(':') if p.strip()]
  if str(raw).strip().lower()=='other taxa': return 'Other taxa'
  return parts[-1] if parts else 'Unclassified'

def export(fig,stem,dests):
  stem.parent.mkdir(parents=True,exist_ok=True)
  for ext in ('png','pdf','svg'): fig.savefig(stem.with_suffix('.'+ext),dpi=300,bbox_inches='tight',facecolor='white')
  plt.close(fig)
  for d in dests:
    d.mkdir(parents=True,exist_ok=True)
    for ext in ('png','pdf','svg'): shutil.copy2(stem.with_suffix('.'+ext),d/f'{stem.name}.{ext}')

def make_level(base,article,level,source_number,suffix):
  audit=base/'outputs/final_publication_source_tables';src=next(audit.glob(f'source_SupplementaryFigure{source_number}_*.csv'));df=pd.read_csv(src)
  required={'display_group','taxon','relative_abundance_percent','taxonomy_level'}
  if not required.issubset(df.columns):raise RuntimeError(f'{src} missing {required-set(df.columns)}')
  df=df[df.taxonomy_level.astype(str).str.casefold()==level.casefold()].copy()
  piv=df.pivot_table(index='taxon',columns='display_group',values='relative_abundance_percent',aggfunc='sum',fill_value=0)
  piv=piv.loc[piv.gt(0).sum(axis=1)>=3]
  piv=piv.loc[piv.sum(axis=1).sort_values(ascending=False).index]
  piv.index=[taxon_name(x,level) for x in piv.index];piv.columns=[short_group(x) for x in piv.columns]
  z=piv.sub(piv.mean(axis=1),axis=0).div(piv.std(axis=1,ddof=0).replace(0,1),axis=0)
  # detect accidental duplicates after display-label shortening and aggregate deterministically
  if z.index.duplicated().any():z=z.groupby(level=0,sort=False).mean()
  derived=base/'data/final_publication_derived';derived.mkdir(parents=True,exist_ok=True);z.to_csv(derived/f'SupplementaryFigure31{suffix}_{level.lower()}_common_taxa_row_zscore_source.csv')
  nr,nc=z.shape;fig,ax=plt.subplots(figsize=(max(18,6.0+nc*1.12),max(12,3.0+nr*.48)))
  vals=z.to_numpy(float);vmax=max(abs(np.nanmin(vals)),abs(np.nanmax(vals)),1e-9);im=ax.imshow(vals,aspect='auto',cmap='RdBu_r',vmin=-vmax,vmax=vmax,interpolation='nearest')
  ax.set_xticks(np.arange(nc));ax.set_xticklabels(z.columns,rotation=48,ha='right',va='top',rotation_mode='anchor',fontsize=13)
  ax.set_yticks(np.arange(nr));ax.set_yticklabels(z.index,fontsize=13)
  ax.tick_params(axis='x',length=0,pad=8);ax.tick_params(axis='y',length=0,pad=6)
  ax.set_xlabel('Environmental group / data layer',fontsize=16,fontweight='bold',labelpad=18);ax.set_ylabel(level,fontsize=16,fontweight='bold',labelpad=10)
  ax.text(-.02,1.035,f'S31{suffix}',transform=ax.transAxes,fontsize=20,fontweight='bold',ha='left',va='bottom')
  ax.set_xticks(np.arange(-.5,nc,1),minor=True);ax.set_yticks(np.arange(-.5,nr,1),minor=True);ax.grid(which='minor',color='white',lw=.8);ax.tick_params(which='minor',bottom=False,left=False)
  cb=fig.colorbar(im,ax=ax,pad=.012,fraction=.025);cb.set_label('Row z-score',fontsize=15,fontweight='bold');cb.ax.tick_params(labelsize=13)
  fig.subplots_adjust(left=.24,right=.93,bottom=.30,top=.93)
  stem=base/'outputs/final_publication_figures'/f'SupplementaryFigure31{suffix}_common_taxa_{level.lower()}_heatmap'
  export(fig,stem,[base/'outputs/app_supplementary_figures',article/'03_Supplementary_Figures'])
  return stem,z.shape

def main():
  ap=argparse.ArgumentParser();ap.add_argument('--base-dir',type=Path,default=Path(__file__).resolve().parents[2]);ap.add_argument('--article-root',type=Path,required=True);a=ap.parse_args();base=a.base_dir.resolve();article=a.article_root.resolve()
  # Remove only obsolete S31 combined outputs.
  for d in [base/'outputs/final_publication_figures',base/'outputs/app_supplementary_figures',article/'03_Supplementary_Figures']:
    for p in d.glob('SupplementaryFigure31_common_taxa_heatmap*'):
      if p.is_file():p.unlink()
  for spec in LEVEL_SPECS:
    stem,shape=make_level(base,article,*spec);print(stem.name,shape)
if __name__=='__main__':main()
