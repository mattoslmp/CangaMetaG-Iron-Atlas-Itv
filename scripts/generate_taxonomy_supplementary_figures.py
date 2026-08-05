#!/usr/bin/env python3
from __future__ import annotations
"""Generate all domain-separated supplementary taxonomy Figures S43–S66.

Every barplot and heatmap uses the same strict per-sample <1% display matrix.
No Top-N rule is used. Missing/NA-like classifications are displayed as an
independent Unclassified category. Figures are rendered by this script only.
"""
import argparse, base64, hashlib, json, os, shutil, sys, textwrap
from datetime import datetime, timezone
from pathlib import Path
os.environ.setdefault('SOURCE_DATE_EPOCH','1785888000')
os.environ.setdefault('MPLCONFIGDIR','/tmp/cangametag_matplotlib_20260805')
import matplotlib
matplotlib.use('Agg')
matplotlib.rcParams['svg.hashsalt']='cangametag-targeted-20260805'
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from matplotlib.patches import Patch
import numpy as np, pandas as pd
from PIL import Image
BASE=Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path: sys.path.insert(0,str(BASE))
from src.taxonomy_normalization import aggregate_counts, aggregate_relative_abundance, collapse_below_threshold, normalize_taxonomy_table, validate_strict_threshold, OTHER_TAXA_LT5, THRESHOLD_PERCENT, UNCLASSIFIED
from src.taxonomy_palette import build_palette, load_palette, save_palette
from src.figure_provenance import taxonomy_caption, provenance_caption, register_caption
SAMPLE_MAP={"Ga0540489":"AM.P1.D","Ga0541010":"AM.P1.R","Ga0541011":"AM.P2.D","Ga0541012":"AM.P2.R","Ga0541013":"TIA.P1.D","Ga0541014":"TIA.P1.R","Ga0541015":"TIA.P2.D","Ga0541016":"TIA.P2.R","Ga0541017":"TI.P1.D","Ga0541018":"TI.P1.R","Ga0541019":"TI.P2.D","Ga0541020":"TI.P2.R","Ga0541021":"TI.P3.D","Ga0541022":"TI.P3.R","Ga0541023":"TI.P4.D","Ga0541024":"TI.P4.R","Ga0541025":"VI.P1.D","Ga0541026":"VI.P1.R","Ga0541027":"VI.P2.D","Ga0541028":"VI.P2.R"}
SAMPLE_ORDER=["AM.P1.D","AM.P1.R","AM.P2.D","AM.P2.R","TIA.P1.D","TIA.P1.R","TIA.P2.D","TIA.P2.R","TI.P1.D","TI.P1.R","TI.P2.D","TI.P2.R","TI.P3.D","TI.P3.R","TI.P4.D","TI.P4.R","VI.P1.D","VI.P1.R","VI.P2.D","VI.P2.R"]
DOMAINS=['Bacteria','Archaea']; RANKS=['Phylum','Class','Order','Family','Genus','Species']; BARPLOT_RANKS={'Phylum','Family','Genus','Species'}; START=43

def sha(path):
 h=hashlib.sha256();
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
def norm(v):
 t=str(v if v is not None else '').strip(); return 'Unclassified' if t.casefold() in {'','na','n/a','nan','none','unknown','undefined','null','unassigned'} else t
def wrap(v,w=28): return '\n'.join(textwrap.wrap(norm(v),width=w,break_long_words=False,break_on_hyphens=False))
def fig_num(domain,rank,kind):
 n=START
 for r in RANKS:
  for d in DOMAINS:
   if d==domain and r==rank: return n if kind=='bar' else n+1
   n+=2
 raise KeyError
def save(fig,stem,out,dpi=300):
 png=out/f'{stem}.png'; pdf=out/f'{stem}.pdf'; svg=out/f'{stem}.svg'; tiff=out/f'{stem}.tiff'
 fig.savefig(png,dpi=dpi,facecolor='white',bbox_inches='tight'); fig.savefig(pdf,facecolor='white',bbox_inches='tight'); fig.savefig(svg,facecolor='white',bbox_inches='tight'); plt.close(fig)
 with Image.open(png) as im:
  rgb=im.convert('RGB'); rgb.save(tiff,format='TIFF',compression='tiff_lzw',dpi=(dpi,dpi))
 return {p.name:sha(p) for p in (png,pdf,svg,tiff)}
def barplot(m,domain,rank,palette,stem=''):
 fig=plt.figure(figsize=(16,10.2),facecolor='white'); ax=fig.add_axes([.105,.095,.665,.815]); y=np.arange(len(m.columns)); left=np.zeros(len(m.columns))
 for taxon in m.index:
  v=m.loc[taxon].to_numpy(float); ax.barh(y,v,left=left,height=.80,color=palette[taxon],edgecolor='white',linewidth=.3); left+=v
 if UNCLASSIFIED in m.index:
  taxa=list(m.index); position=taxa.index(UNCLASSIFIED)
  starts=m.loc[taxa[:position]].sum(axis=0) if position else pd.Series(0.0,index=m.columns)
  for row,sample in enumerate(m.columns):
   value=float(m.at[UNCLASSIFIED,sample])
   if value <= 0: continue
   rendered=f'{value:.2f}%' if value < 1 else f'{value:.1f}%'
   label=ax.text(float(starts.at[sample])+value/2.0,row,rendered,ha='center',va='center',fontsize=9.5,fontweight='bold',color='white',clip_on=False,zorder=12)
   label.set_path_effects([path_effects.Stroke(linewidth=2.0,foreground='#111111'),path_effects.Normal()])
 ax.set_xlim(0,100); ax.set_yticks(y,m.columns,fontsize=12.5); ax.invert_yaxis(); ax.set_xlabel('Relative abundance (%)',fontsize=14.5,fontweight='bold'); ax.set_ylabel('Sediment metagenome sample',fontsize=14.5,fontweight='bold'); ax.spines[['top','right']].set_visible(False); ax.grid(False)
 fig.text(.045,.965,f'{domain} — {rank} — barplot by individual sample',fontsize=17,fontweight='bold',ha='left',va='top')
 fig.legend(handles=[Patch(facecolor=palette[t],edgecolor='none',label=wrap(t,24)) for t in m.index],title=rank,loc='center left',bbox_to_anchor=(.78,.55),ncol=1,frameon=False,fontsize=11.5,title_fontsize=13,handlelength=1.2,labelspacing=.3)
 register_caption(stem,taxonomy_caption('scripts/generate_taxonomy_supplementary_figures.py',stem))
 return fig
def heatmap(counts,domain,rank,stem=''):
 """Heatmap of ln(count + 1) computed directly on the original count matrix.

 The previous version plotted log10(relative abundance [%] + 1). That is wrong
 for this analysis on two counts: the logarithm base was 10 rather than natural,
 and the transformation was applied to per-sample percentages instead of the
 observed counts, so the value shown depended on the library composition of each
 sample rather than on the observed abundance of the feature. The matrix passed
 in here is the raw count matrix; it is never converted to relative abundance or
 to a percentage before the transformation.
 """
 x=counts.to_numpy(float)
 if np.isnan(x).any(): raise ValueError(f'NaN in count matrix for {domain} {rank}')
 if (x<0).any(): raise ValueError(f'Negative counts for {domain} {rank}')
 trans=np.log(x+1.0)                      # natural logarithm, ln(x+1)
 if not np.isfinite(trans).all(): raise ValueError(f'Non-finite ln(x+1) for {domain} {rank}')
 nrow=counts.shape[0]
 # Each row needs a guaranteed vertical slot, otherwise long wrapped species
 # names collide. The label font is reduced for dense ranks and the row pitch is
 # never allowed below the height of a two-line label.
 label_fs=11.0 if nrow<=26 else (9.2 if nrow<=45 else 8.0)
 lines=[len(wrap(v,34).split('\n')) for v in counts.index] or [1]
 row_inches=max(0.30,(max(lines)*label_fs*1.35)/72.0)
 plot_h=row_inches*nrow
 height=max(8.0,plot_h+3.2)
 fig=plt.figure(figsize=(17.0,height),facecolor='white')
 bottom=1.9/height
 ax=fig.add_axes([.275,bottom,.615,plot_h/height])
 im=ax.imshow(trans,aspect='auto',interpolation='nearest',cmap='YlGnBu',
              vmin=0.0,vmax=max(1e-6,float(np.nanmax(trans))))
 ax.set_xticks(np.arange(counts.shape[1]),counts.columns,rotation=58,ha='right',
               rotation_mode='anchor',fontsize=12)
 ax.set_yticks(np.arange(nrow),[wrap(v,34) for v in counts.index],fontsize=label_fs)
 ax.tick_params(axis='y',length=0,pad=4)
 ax.set_xlabel('Sediment metagenome sample',fontsize=14.5,fontweight='bold')
 ax.set_ylabel(rank,fontsize=14.5,fontweight='bold')
 fig.text(.045,1-0.35/height,f'{domain} — {rank} — abundance heatmap [ln(count + 1)]',
          fontsize=17,fontweight='bold',ha='left',va='top')
 cax=fig.add_axes([.905,bottom+plot_h/height*0.28,.016,plot_h/height*0.44]); cb=fig.colorbar(im,cax=cax)
 cb.set_label('ln(count + 1)\n(natural logarithm of the original count)',
              fontsize=11.5,fontweight='bold')
 register_caption(stem,provenance_caption(
   inputs=('data/resultado.cds.otu.tab','data/resultado.cds.tax.display_current.tab',
           'data/mapeamento_taxonomico.csv'),
   script='scripts/generate_taxonomy_supplementary_figures.py',
   method=('counts aggregated per taxon and sample from the original CDS OTU table; the natural '
           'logarithm transformation ln(x + 1) is applied directly to those counts, where x is '
           'the observed count of the taxon in the sample; the data are never converted to '
           'relative abundance or to a percentage before the transformation, no log10 is used, '
           'and the transformation is applied exactly once; a count of 0 maps to ln(1) = 0; no '
           'z-score is applied, so the colour bar shows ln(count + 1) itself'),
   outputs=f'{stem}.png, {stem}.pdf, {stem}.svg, {stem}_source_counts.csv, '
           f'{stem}_matrix_ln_x_plus_1.csv'))
 return fig,pd.DataFrame(trans,index=counts.index,columns=counts.columns)

def main():
 p=argparse.ArgumentParser(); p.add_argument('--base-dir',type=Path,default=BASE); p.add_argument('--article-root',type=Path); p.add_argument('--only',type=int,action='append'); p.add_argument('--png-dpi',type=int,default=600); a=p.parse_args(); root=a.base_dir.resolve(); data=root/'data'; out=root/'outputs'/'final_publication_figures'; app=root/'outputs'/'app_supplementary_figures'; article=(a.article_root.resolve()/'article'/'03_Supplementary_Figures') if a.article_root else root/'article'/'03_Supplementary_Figures'; der=data/'final_publication_derived'; audit=root/'validation'/'targeted_figures_20260805'/'taxonomy_lt1_final'
 for d in (out,app,article,der,audit): d.mkdir(parents=True,exist_ok=True)
 otu=pd.read_csv(data/'resultado.cds.otu.tab',sep='\t',index_col=0); tp=data/'resultado.cds.tax.display_current.tab'; tax=pd.read_csv(tp if tp.exists() else data/'resultado.cds.tax.tab',sep='\t',index_col=0); otu.index=otu.index.astype(str).str.strip(); tax.index=tax.index.astype(str).str.strip(); otu.columns=[SAMPLE_MAP.get(str(c).split('_')[0].strip('.'),str(c).split('_')[0].strip('.')) for c in otu.columns]; otu=otu.reindex(columns=SAMPLE_ORDER).apply(pd.to_numeric,errors='coerce').fillna(0); tax.columns=[str(c).strip() for c in tax.columns]; tax=normalize_taxonomy_table(tax,data/'mapeamento_taxonomico.csv')
 selected=set(a.only or range(44,68)); matrices={}; validation={}; all_taxa=[]; heat_audit=[]
 needed=set()
 for rank in RANKS:
  for domain in DOMAINS:
   bn=fig_num(domain,rank,'bar'); hn=bn+1
   if (bn in selected and rank in BARPLOT_RANKS) or hn in selected: needed.add((domain,rank))
 for domain,rank in sorted(needed):
   full=aggregate_relative_abundance(otu,tax,domain,rank); display=collapse_below_threshold(full); counts=aggregate_counts(otu,tax,domain,rank); key=f'{domain}_{rank}'; matrices[key]=(full,display,counts); validation[key]=validate_strict_threshold(full,display); all_taxa.extend(display.index); full.to_csv(der/f'Taxonomy_{domain}_{rank}_full_relative_abundance_percent.csv'); display.to_csv(der/f'Taxonomy_{domain}_{rank}_strict_lt1_display.csv')
 palette=build_palette(all_taxa,load_palette(data/'taxonomy_palette.json')); save_palette(palette,data/'taxonomy_palette.json'); records=[]
 for rank in RANKS:
  for domain in DOMAINS:
   bn=fig_num(domain,rank,'bar'); hn=bn+1
   if bn not in selected and hn not in selected: continue
   full,m,counts=matrices[f'{domain}_{rank}']
   if bn in selected and rank in BARPLOT_RANKS:
    stem=f'SupplementaryFigure{bn}_Taxonomy_{domain}_{rank}_individual_samples_barplot_100pct'; hashes=save(barplot(m,domain,rank,palette,stem),stem,out,a.png_dpi); m.to_csv(der/f'{stem}_source.csv')
    for ext in ('png','pdf','svg','tiff'): shutil.copy2(out/f'{stem}.{ext}',app/f'{stem}.{ext}'); shutil.copy2(out/f'{stem}.{ext}',article/f'{stem}.{ext}')
    records.append({'figure':f'S{bn}','stem':stem,'kind':'barplot','script':'scripts/generate_taxonomy_supplementary_figures.py','input':['data/resultado.cds.otu.tab','data/resultado.cds.tax.display_current.tab','data/mapeamento_taxonomico.csv'],'processed':f'data/final_publication_derived/{stem}_source.csv','hashes':hashes,'other_taxa_rule':'strict <1.0% per sample; exactly 1.0% explicit; Unclassified independent'})
   if hn in selected:
    stem=f'SupplementaryFigure{hn}_Taxonomy_{domain}_{rank}_individual_samples_heatmap_relative_abundance'; hm=counts.reindex(index=[i for i in m.index if i!=OTHER_TAXA_LT5]).fillna(0.0); fig,tr=heatmap(hm,domain,rank,stem); hashes=save(fig,stem,out,a.png_dpi); hm.to_csv(der/f'{stem}_source_counts.csv'); tr.to_csv(der/f'{stem}_matrix_ln_x_plus_1.csv'); heat_audit.append({'figure':f'S{hn}','stem':stem,'count_matrix':f'data/final_publication_derived/{stem}_source_counts.csv','rows':int(hm.shape[0]),'cols':int(hm.shape[1]),'zeros':int((hm.to_numpy()==0).sum()),'na':int(hm.isna().to_numpy().sum()),'previous_transform':'log10(relative abundance [%] + 1)','final_transform':'ln(count + 1)','relative_abundance_used':False,'log10_used':False,'zscore_applied':False,'max_ln':float(tr.to_numpy().max())})
    for ext in ('png','pdf','svg','tiff'): shutil.copy2(out/f'{stem}.{ext}',app/f'{stem}.{ext}'); shutil.copy2(out/f'{stem}.{ext}',article/f'{stem}.{ext}')
    records.append({'figure':f'S{hn}','stem':stem,'kind':'heatmap','script':'scripts/generate_taxonomy_supplementary_figures.py','input':['data/resultado.cds.otu.tab','data/resultado.cds.tax.display_current.tab','data/mapeamento_taxonomico.csv'],'processed':f'data/final_publication_derived/{stem}_source_counts.csv','hashes':hashes,'transform':'ln(count + 1) on the original counts'})
 report={'executed_utc':datetime.now(timezone.utc).isoformat(),'selected':sorted(selected),'generative_ai_used':False,'normalization':'central src/taxonomy_normalization.py','validations':validation,'records':records,'heatmap_audit':heat_audit}; (audit/'SUPPLEMENTARY_TAXONOMY_S43_S66_STRICT_LT1_VALIDATION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');
 if not all(v['pass'] for v in validation.values()): raise RuntimeError('Strict threshold validation failed')
 print(json.dumps({'pass':True,'figures':len(records)},indent=2))
if __name__=='__main__': main()
