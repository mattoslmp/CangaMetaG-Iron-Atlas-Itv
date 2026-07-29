#!/usr/bin/env python3
"""Generate readable Supplementary Figures 6 and 7 with separate A/B panel files."""
from pathlib import Path
import argparse
import pandas as pd,numpy as np
import matplotlib.pyplot as plt
from revision_common import export,wrap

def draw_panel(df,title,letter,color,figsize=(13.85,15.0)):
 df=df.sort_values('absolute_log2_contrast').copy(); y=np.arange(len(df))
 fig,ax=plt.subplots(figsize=figsize)
 ax.barh(y,df.absolute_log2_contrast,color=color,edgecolor='#222',height=.72,linewidth=.5)
 labels=[wrap(x,58) for x in df.full_display_label]
 ax.set_yticks(y); ax.set_yticklabels(labels,fontsize=16.0)
 ax.tick_params(axis='y',length=0,pad=9); ax.tick_params(axis='x',labelsize=14)
 ax.set_xlabel('Absolute descriptive log2 contrast',fontsize=17,fontweight='bold')
 title_text=wrap(title,32)
 ax.set_title(f'{letter}  {title_text}',loc='left',fontsize=19,fontweight='bold',pad=10,linespacing=1.05)
 ax.spines[['top','right','left']].set_visible(False); ax.grid(axis='x',alpha=.2)
 for yy,val in zip(y,df.absolute_log2_contrast): ax.text(val+.12,yy,f'{val:.2f}',va='center',fontsize=13.0,fontweight='bold')
 ax.set_xlim(0,float(df.absolute_log2_contrast.max())+2.0)
 fig.subplots_adjust(left=.58,right=.985,bottom=.075,top=.925)
 return fig

def make(base,number,source,name,colorA,colorB,article_root=None):
 df=pd.read_csv(source)
 # Some legacy display_label values contain a Unicode ellipsis. Reconstruct
 # those labels from the complete KO and Metabolism columns rather than
 # abbreviating or guessing any scientific name.
 df['full_display_label']=df['display_label'].astype(str)
 truncated=df['full_display_label'].str.contains('…',regex=False,na=False)
 if {'KO','Metabolism'}.issubset(df.columns):
  df.loc[truncated,'full_display_label']=(
   df.loc[truncated,'KO'].astype(str).str.strip()+' | '+df.loc[truncated,'Metabolism'].astype(str).str.strip()
  )
 elif {'KO identifier','Metabolism'}.issubset(df.columns):
  df.loc[truncated,'full_display_label']=(
   df.loc[truncated,'KO identifier'].astype(str).str.strip()+' | '+df.loc[truncated,'Metabolism'].astype(str).str.strip()
  )
 pa=df[df.panel.str.contains('Amazonian',case=False,na=False)].nlargest(25,'absolute_log2_contrast')
 pb=df[df.panel.str.contains('external',case=False,na=False)].nlargest(25,'absolute_log2_contrast')
 outdir=base/'outputs/final_publication_figures'; copies=[base/'outputs/app_supplementary_figures']
 if article_root: copies.append(article_root/'03_Supplementary_Figures')
 stem=outdir/name
 export(draw_panel(pa,'Higher in Amazonian lateritic lakes','A',colorA),Path(str(stem)+'_P01'),copies,tight=False)
 export(draw_panel(pb,'Higher in external iron-rich records','B',colorB),Path(str(stem)+'_P02'),copies,tight=False)
 # Combined canonical overview; DOCX uses the separate panel files.
 fig,axes=plt.subplots(1,2,figsize=(28,15),gridspec_kw={'wspace':.72})
 for ax,sub,title,letter,color in [(axes[0],pa,'Higher in Amazonian lateritic lakes','A',colorA),(axes[1],pb,'Higher in external iron-rich records','B',colorB)]:
  sub=sub.sort_values('absolute_log2_contrast'); y=np.arange(len(sub)); ax.barh(y,sub.absolute_log2_contrast,color=color,edgecolor='#222',height=.72,linewidth=.4)
  ax.set_yticks(y); ax.set_yticklabels([wrap(x,52) for x in sub.full_display_label],fontsize=13.0); ax.tick_params(axis='y',length=0,pad=7); ax.tick_params(axis='x',labelsize=12)
  ax.set_xlabel('Absolute descriptive log2 contrast',fontsize=17,fontweight='bold'); ax.set_title(f'{letter}  {wrap(title,34)}',loc='left',fontsize=19,fontweight='bold',pad=10,linespacing=1.05); ax.spines[['top','right','left']].set_visible(False); ax.grid(axis='x',alpha=.2)
  ax.set_xlim(0,float(sub.absolute_log2_contrast.max())+1.7)
 fig.subplots_adjust(left=.22,right=.98,bottom=.08,top=.95,wspace=.72)
 export(fig,stem,copies,tight=False)
 print(stem)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--base-dir',type=Path,default=Path(__file__).resolve().parents[2]); ap.add_argument('--article-root',type=Path); ap.add_argument('--only',choices=['6','7'],action='append'); a=ap.parse_args(); base=a.base_dir.resolve(); ar=a.article_root.resolve() if a.article_root else None
 selected=set(a.only or ['6','7'])
 d=base/'data/final_publication_derived'
 if '6' in selected:
  make(base,6,d/'SupplementaryFigure6_bidirectional_all_KO_figure_source.csv','SupplementaryFigure6_ST8_selected_sediments_all_KO_zscore_proportional','#377EB8','#C46C17',ar)
 if '7' in selected:
  make(base,7,d/'SupplementaryFigure7_bidirectional_iron_KO_figure_source.csv','SupplementaryFigure7_ST8_iron_selected_zscore_proportional','#2A9D8F','#D1495B',ar)
if __name__=='__main__': main()
