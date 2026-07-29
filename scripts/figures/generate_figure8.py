#!/usr/bin/env python3
"""Generate Main Figure 8 from Supplementary Table 5 with explicit comparisons."""
from pathlib import Path
import argparse,re
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
from revision_common import export,wrap

MAP={'AMD':'Amendoim (dry)','TID':'Três Irmãs (dry)','TIAD':'Três Irmãs Adjacent (dry)','VID':'Violão (dry)',
     'AMR':'Amendoim (rainy)','TIR':'Três Irmãs (rainy)','TIAR':'Três Irmãs Adjacent (rainy)','VIR':'Violão (rainy)'}
ABBR={'AMD':'AM.D','TID':'TI.D','TIAD':'TIA.D','VID':'VI.D','AMR':'AM.R','TIR':'TI.R','TIAR':'TIA.R','VIR':'VI.R'}

def parse_comp(s):
 s=re.sub(r'\s+','',str(s))
 m=re.match(r'([A-Z]+)vs([A-Z]+)',s,re.I)
 if not m:
  m=re.match(r'([A-Z]+)[_\-]([A-Z]+)',s,re.I)
 if not m: return s,s,s
 a,b=m.group(1).upper(),m.group(2).upper()
 return f"{MAP.get(a,a)} vs {MAP.get(b,b)}",f"{ABBR.get(a,a)} vs {ABBR.get(b,b)}",a

def label_otu_with_pathway(otu, pathway, width=44):
 s=' '.join(str(otu).split())
 p=' '.join(str(pathway).split())
 if p and p.lower() != 'nan':
  combined=f"{s} — {p}"
 else:
  combined=s
 return wrap(combined,width=width)

def panel(ax,df,title,letter):
 df=df.copy()
 df['log2FoldChange']=pd.to_numeric(df['log2FoldChange'],errors='coerce')
 df=df.dropna(subset=['log2FoldChange']).assign(abs_lfc=lambda x:x.log2FoldChange.abs()).nlargest(16,'abs_lfc').sort_values('log2FoldChange')
 comps=df['Comparasion'].apply(parse_comp)
 df['comparison_full']=[x[0] for x in comps]; df['comparison_short']=[x[1] for x in comps]
 y=np.arange(len(df))
 colors=np.where(df.log2FoldChange>=0,'#2166AC','#B2182B')
 ax.barh(y,df.log2FoldChange,color=colors,height=.72,edgecolor='#222',linewidth=.5)
 ax.axvline(0,color='black',lw=1.2)
 labs=[f"{label_otu_with_pathway(o,m)}\n{c}" for o,m,c in zip(df.OTU,df.Metabolism,df.comparison_short)]
 ax.set_yticks(y); ax.set_yticklabels(labs,fontsize=9.6,linespacing=1.08)
 ax.tick_params(axis='x',labelsize=12)
 ax.set_xlabel('log2 fold change',fontsize=14,fontweight='bold')
 ax.set_title(f'{letter}  {title}',loc='left',fontsize=18,fontweight='bold',pad=12)
 lim=max(5.4,float(df.abs_lfc.max())+1.2); ax.set_xlim(-lim,lim)
 for yy,val,short in zip(y,df.log2FoldChange,df.comparison_short):
  ha='left' if val>=0 else 'right'; x=val+(0.10 if val>=0 else -0.10)
  ax.text(x,yy,f'{val:+.2f}',ha=ha,va='center',fontsize=10.5,fontweight='bold',clip_on=False)
 ax.spines[['top','right','left']].set_visible(False); ax.tick_params(axis='y',length=0,pad=7)
 ax.grid(axis='x',alpha=.18,lw=.7)
 return df

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--base-dir',type=Path,default=Path(__file__).resolve().parents[2]); ap.add_argument('--article-root',type=Path); a=ap.parse_args()
 base=a.base_dir.resolve(); table=base/'data/publication_sources/Supplementary_Table_5.xlsx'
 if not table.exists(): table=base/'tables/Supplementary_Table_5.xlsx'
 if not table.exists():
  table=base/'data/Supplementary_Table_5.xlsx'
 if not table.exists(): raise FileNotFoundError(table)
 dry=pd.read_excel(table,sheet_name='Top-differential-abundance_Dry')
 rain=pd.read_excel(table,sheet_name='Top-differential-abundance-Rain')
 fig,axes=plt.subplots(1,2,figsize=(18.0,11.6),gridspec_kw={'wspace':.72})
 d1=panel(axes[0],dry,'Dry-season contrasts','A'); d2=panel(axes[1],rain,'Rainy-season contrasts','B')
 fig.subplots_adjust(left=.29,right=.985,bottom=.08,top=.94,wspace=.84)
 out=base/'outputs/final_publication_figures/Figure8_KO_differential_abundance_dry_rainy'
 copies=[base/'outputs/app_supplementary_figures']
 if a.article_root: copies.append(a.article_root/'02_Main_Figures_title_free')
 export(fig,out,copies,tight=False)
 src=base/'data/final_publication_derived/Figure8_KO_differential_abundance_dry_rainy_source.csv'; src.parent.mkdir(parents=True,exist_ok=True)
 out_df=pd.concat([d1.assign(season='Dry'),d2.assign(season='Rainy')],ignore_index=True)
 out_df['display_label']=[label_otu_with_pathway(o,m).replace('\n',' | ') for o,m in zip(out_df['OTU'],out_df['Metabolism'])]
 out_df.to_csv(src,index=False)
 print(out)
if __name__=='__main__': main()
