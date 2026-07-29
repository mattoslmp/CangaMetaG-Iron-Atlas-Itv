#!/usr/bin/env python3
"""Generate a true world map for Supplementary Figure 70 using app metadata."""
from __future__ import annotations
from pathlib import Path
import argparse, shutil, sys, math
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from mpl_toolkits.basemap import Basemap


def export(fig,stem,dests):
  stem.parent.mkdir(parents=True,exist_ok=True)
  for ext in ('png','pdf','svg'):fig.savefig(stem.with_suffix('.'+ext),dpi=300,bbox_inches='tight',facecolor='white')
  plt.close(fig)
  for d in dests:
    d.mkdir(parents=True,exist_ok=True)
    for ext in ('png','pdf','svg'):shutil.copy2(stem.with_suffix('.'+ext),d/f'{stem.name}.{ext}')

def main():
  ap=argparse.ArgumentParser();ap.add_argument('--base-dir',type=Path,default=Path(__file__).resolve().parents[2]);ap.add_argument('--article-root',type=Path,required=True);a=ap.parse_args();base=a.base_dir.resolve();article=a.article_root.resolve();sys.path.insert(0,str(base))
  from src.environment_map_data import load_external_environment_coordinates
  pts=load_external_environment_coordinates(base)
  outcsv=base/'data/final_publication_derived/SupplementaryFigure70_external_iron_rich_environment_coordinates.csv';outcsv.parent.mkdir(parents=True,exist_ok=True);pts.to_csv(outcsv,index=False)
  groups=list(dict.fromkeys(pts.dataset_group.astype(str)));cmap=plt.get_cmap('tab10');colors={g:cmap(i%10) for i,g in enumerate(groups)}
  fig,ax=plt.subplots(figsize=(22,12.5));m=Basemap(projection='robin',lon_0=0,resolution='c',ax=ax)
  m.drawmapboundary(fill_color='#DCEEFF',linewidth=.8);m.fillcontinents(color='#F3E8CF',lake_color='#DCEEFF',zorder=0);m.drawcoastlines(color='#555555',linewidth=.65);m.drawcountries(color='#777777',linewidth=.4)
  m.drawparallels(range(-60,91,30),labels=[1,0,0,0],fontsize=11,color='#B0B8C0',dashes=[2,2],linewidth=.5);m.drawmeridians(range(-180,181,60),labels=[0,0,0,1],fontsize=11,color='#B0B8C0',dashes=[2,2],linewidth=.5)
  offsets={
    'ENV01':(-20,18),'ENV02':(12,-22),'ENV03':(-10,18),'ENV04':(14,-18),
    'ENV05':(-28,18),'ENV06':(12,16),'ENV07':(14,10),'ENV08':(12,-20),
    'ENV09':(-16,20),'ENV10':(16,-20),'ENV11':(18,2),'ENV12':(-18,-30),
    'ENV13':(-24,18),'ENV14':(16,-16),'ENV15':(-20,-18),'ENV16':(12,16),
    'ENV17':(-24,16),'ENV18':(14,-16),'ENV19':(-28,18),'ENV20':(14,2),'ENV21':(-18,-24),
  }
  for g,sub in pts.groupby('dataset_group',sort=False):
    x,y=m(sub.lon.to_numpy(float),sub.lat.to_numpy(float));m.scatter(x,y,s=95,c=[colors[g]],edgecolor='black',linewidth=.7,label=g,zorder=5)
    for xx,yy,(_,r) in zip(x,y,sub.iterrows()):
      off=offsets.get(str(r.Environment_ID),(7,7));ax.annotate(str(r.Environment_ID),(xx,yy),xytext=off,textcoords='offset points',fontsize=11.5,fontweight='bold',ha='left' if off[0]>=0 else 'right',va='bottom' if off[1]>=0 else 'top',bbox=dict(boxstyle='round,pad=.18',fc='white',ec='none',alpha=.88),arrowprops=dict(arrowstyle='-',lw=.6,color='#555555',shrinkA=2,shrinkB=2),zorder=6)
  ax.text(.01,.97,'N',transform=ax.transAxes,fontsize=16,fontweight='bold',ha='left',va='top');ax.annotate('',xy=(.022,.92),xytext=(.022,.84),xycoords='axes fraction',arrowprops=dict(arrowstyle='-|>',lw=2,color='black'))
  ax.legend(title='Curated comparison environment',bbox_to_anchor=(1.01,1.0),loc='upper left',frameon=False,fontsize=11.5,title_fontsize=13)
  # General title is provided in the supplementary caption, not inside the image.
  fig.subplots_adjust(left=.04,right=.76,bottom=.08,top=.97)
  stem=base/'outputs/final_publication_figures/SupplementaryFigure70_external_iron_rich_environment_world_map'
  # remove obsolete target only
  for d in [base/'outputs/final_publication_figures',base/'outputs/app_supplementary_figures',article/'03_Supplementary_Figures']:
    for p in d.glob('SupplementaryFigure70_external_iron_rich_environment_map*'):
      if p.is_file():p.unlink()
  export(fig,stem,[base/'outputs/app_supplementary_figures',article/'03_Supplementary_Figures'])
  print(stem,outcsv,len(pts))
if __name__=='__main__':main()
