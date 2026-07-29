#!/usr/bin/env python3
"""Generate Main Figure 7 from the MAG quality/classification workbook."""
from pathlib import Path
import argparse,re
import numpy as np,pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from revision_common import export,wrap

GROUP_ORDER=['AM.D','AM.R','TIA.D','TIA.R','TI.D','TI.R','VI.D','VI.R']
GROUP_MAP={'AM-D':'AM.D','AM-R':'AM.R','TIA-D':'TIA.D','TIA-R':'TIA.R','TI-D':'TI.D','TI-R':'TI.R','VI-D':'VI.D','VI-R':'VI.R'}
COLORS=['#0072B2','#E69F00','#009E73','#CC79A7','#D55E00','#56B4E9','#7E57C2','#8D6E63','#2E7D32']

def phylum(lineage, fallback):
 s=str(lineage)
 m=re.search(r'p__([^;]+)',s)
 if m and m.group(1).strip(): return m.group(1).strip()
 return str(fallback).strip() if pd.notna(fallback) else 'Unclassified'

def short_species(s,n=32):
 s=' '.join(str(s).split())
 return wrap(s,n)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--base-dir',type=Path,default=Path(__file__).resolve().parents[2]); ap.add_argument('--article-root',type=Path); a=ap.parse_args()
 base=a.base_dir.resolve(); wb=base/'data/Supplementary_table_7-MAGS-Quality-Genome_Lineage-Classification.xlsx'
 if not wb.exists(): raise FileNotFoundError(wb)
 cls=pd.read_excel(wb,sheet_name='bin.classification',header=3)
 cls=cls[cls['MAG'].notna()].copy()
 cls['MAG_number']=cls['MAG'].astype(str).str.extract(r'(\d+)').astype(float).astype('Int64')
 cls['Phylum']= [phylum(x,y) for x,y in zip(cls['Gtdbtk (1) bac120-ar122: r89 '],cls['Lineage Classificatio: CheckM'])]
 cls['Completeness']=pd.to_numeric(cls['Completeness (Cpn): CheckM'],errors='coerce')
 cls['Contamination']=pd.to_numeric(cls['Contamination (Ctn): CheckM'],errors='coerce')
 cls['Species']=cls['Species definition'].fillna('Unclassified MAG').astype(str).str.strip()
 q=pd.read_excel(wb,sheet_name='Bins-quant',usecols='A:C')
 q.columns=['Sample','Species','Abundance']; q=q[q['Sample'].notna() & q['Species'].notna()].copy()
 q['Group']=q.Sample.astype(str).str.strip().map(GROUP_MAP).fillna(q.Sample.astype(str).str.replace('-','.',regex=False))
 q['Abundance']=pd.to_numeric(q.Abundance.astype(str).str.replace(',','.',regex=False),errors='coerce').fillna(0)
 q=q[q.Group.isin(GROUP_ORDER)]
 agg=q.groupby(['Species','Group'],as_index=False).Abundance.sum()
 totals=agg.groupby('Species').Abundance.sum().nlargest(7)
 top=totals.index.tolist(); agg_top=agg[agg.Species.isin(top)]
 matrix=agg_top.pivot(index='Species',columns='Group',values='Abundance').fillna(0).reindex(index=top,columns=GROUP_ORDER,fill_value=0)
 counts=cls.Phylum.value_counts(); pct=counts/len(cls)*100
 fig=plt.figure(figsize=(16.3,13.4)); gs=fig.add_gridspec(2,2,width_ratios=[1.02,1.55],height_ratios=[1,1],wspace=.48,hspace=.52)
 axA=fig.add_subplot(gs[0,0]); order=counts.sort_values().index; vals=pct[order]
 y=np.arange(len(order)); axA.barh(y,vals,color='#2C7FB8',edgecolor='#222',height=.72)
 axA.set_yticks(y); axA.set_yticklabels([wrap(x,22) for x in order],fontsize=12.5)
 axA.set_xlabel('Identified MAGs/bins (%)',fontsize=14,fontweight='bold'); axA.set_title('A',loc='left',fontsize=22,fontweight='bold')
 for yy,o,v in zip(y,order,vals): axA.text(v+.7,yy,f'{counts[o]} ({v:.1f}%)',va='center',fontsize=12,fontweight='bold')
 axA.set_xlim(0,max(55,vals.max()+10)); axA.spines[['top','right']].set_visible(False); axA.tick_params(axis='x',labelsize=12)
 axB=fig.add_subplot(gs[0,1]);
 for i,sp in enumerate(matrix.index):
  for j,g in enumerate(matrix.columns):
   v=float(matrix.loc[sp,g]);
   if v>0: axB.scatter(j,i,s=80+900*v/max(matrix.to_numpy().max(),1e-9),c=[v],cmap='viridis',vmin=0,vmax=matrix.to_numpy().max(),edgecolor='#222',linewidth=.5)
 axB.set_xticks(range(len(GROUP_ORDER))); axB.set_xticklabels(GROUP_ORDER,rotation=35,ha='right',fontsize=12.5)
 axB.set_yticks(range(len(top))); axB.set_yticklabels([short_species(x,30) for x in top],fontsize=12.2)
 axB.invert_yaxis(); axB.set_xlabel('Lake–season group',fontsize=14,fontweight='bold'); axB.set_ylabel('MAG/bin consensus assignment',fontsize=14,fontweight='bold'); axB.set_title('B',loc='left',fontsize=22,fontweight='bold')
 sm=plt.cm.ScalarMappable(cmap='viridis',norm=plt.Normalize(0,matrix.to_numpy().max())); cb=fig.colorbar(sm,ax=axB,pad=.025); cb.set_label('Relative abundance',fontsize=13,fontweight='bold'); cb.ax.tick_params(labelsize=11)
 axB.spines[['top','right']].set_visible(False)
 axC=fig.add_subplot(gs[1,0]); axC.scatter(cls.Contamination,cls.Completeness,s=75,c='#56B4E9',edgecolor='#111',linewidth=.7,alpha=.9)
 axC.axhline(90,ls='--',color='#555'); axC.axhline(70,ls=':',color='#777'); axC.axvline(5,ls='--',color='#555')
 label=cls[(cls.Completeness>=90)&(cls.Contamination<=5)].nlargest(3,'Completeness')
 for k,(_,r) in enumerate(label.iterrows()):
  axC.annotate(f"MAG.{int(r.MAG_number)}",(r.Contamination,r.Completeness),xytext=(8,10+18*k),textcoords='offset points',fontsize=10.5,fontweight='bold',bbox=dict(boxstyle='round,pad=.12',fc='white',ec='none',alpha=.75))
 axC.set_xlabel('Contamination (%)',fontsize=14,fontweight='bold'); axC.set_ylabel('Completeness (%)',fontsize=14,fontweight='bold'); axC.set_title('C',loc='left',fontsize=22,fontweight='bold'); axC.tick_params(labelsize=12); axC.spines[['top','right']].set_visible(False)
 axD=fig.add_subplot(gs[1,1]); bottom=np.zeros(len(GROUP_ORDER));
 for i,sp in enumerate(reversed(top)):
  vals=matrix.loc[sp].to_numpy(float); axD.bar(range(len(GROUP_ORDER)),vals,bottom=bottom,color=COLORS[i%len(COLORS)],edgecolor='white',linewidth=.4,label=short_species(sp,28)); bottom+=vals
 axD.set_xticks(range(len(GROUP_ORDER))); axD.set_xticklabels(GROUP_ORDER,rotation=35,ha='right',fontsize=12.5)
 axD.set_ylabel('Summed relative abundance',fontsize=14,fontweight='bold'); axD.set_xlabel('Lake–season group',fontsize=14,fontweight='bold'); axD.set_title('D',loc='left',fontsize=22,fontweight='bold'); axD.tick_params(axis='y',labelsize=12); axD.spines[['top','right']].set_visible(False)
 axD.legend(title='MAG/bin consensus assignment',bbox_to_anchor=(0.5,-0.22),loc='upper center',frameon=False,fontsize=11.8,title_fontsize=13,ncol=2)
 fig.subplots_adjust(left=.10,right=.97,bottom=.23,top=.97)
 out=base/'outputs/final_publication_figures/Figure7_MAG_quality_and_abundance'; copies=[base/'outputs/app_supplementary_figures']
 if a.article_root: copies.append(a.article_root/'02_Main_Figures_title_free')
 export(fig,out,copies,tight=False)
 derived=base/'data/final_publication_derived'; derived.mkdir(parents=True,exist_ok=True)
 cls[['MAG','Phylum','Completeness','Contamination','Species']].to_csv(derived/'Figure7_MAG_quality_source.csv',index=False)
 agg_top.to_csv(derived/'Figure7_MAG_abundance_source.csv',index=False)
 print(out)
if __name__=='__main__': main()
