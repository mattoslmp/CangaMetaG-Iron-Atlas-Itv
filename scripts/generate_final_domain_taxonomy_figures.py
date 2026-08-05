#!/usr/bin/env python3
from __future__ import annotations

"""Taxonomy plotting module for canonical main Figures 2–5.

Only taxonomic labels and per-sample display aggregation are updated. NMDS and
RDA coordinates, vectors, statistics, sample order, colours, dimensions and
panel geometry are loaded from the canonical article reproducibility bundle.
No generative image editing is used.
"""
from pathlib import Path
import hashlib, json, math, os, shutil, sys
import numpy as np
import pandas as pd
os.environ.setdefault("SOURCE_DATE_EPOCH", "1785888000")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/cangametag_matplotlib_20260805")
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["svg.hashsalt"] = "cangametag-targeted-20260805"
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

BASE=Path(__file__).resolve().parents[1]
if str(BASE) not in sys.path: sys.path.insert(0,str(BASE))
from src.taxonomy_normalization import (
  aggregate_relative_abundance, collapse_below_threshold,
  normalize_taxonomy_table, validate_strict_threshold, build_threshold_audit,
  UNCLASSIFIED, THRESHOLD_PERCENT,
)
from src.taxonomy_palette import build_palette, load_palette, save_palette
from src.figure_provenance import taxonomy_caption, ordination_caption, register_caption
# Reuse the deterministic label-placement helpers already validated on S17, so
# vector labels and sample labels never overlap in the ordination panels.
sys.path.insert(0, str(BASE / 'scripts'))
sys.path.insert(0, str(BASE / 'scripts' / 'figures'))
from generate_ordinations_revision4 import (
  _bounded_environment_labels, _bounded_taxon_labels, _repelled_point_labels,
)
DATA=BASE/'data'; OUT=BASE/'outputs'/'final_publication_figures'; DER=DATA/'final_publication_derived'
ARTICLE_MAIN=BASE/'article'/'02_Main_Figures'; APP_MAIN=BASE/'outputs'/'app_main_figures'
AUDIT=BASE/'validation'/'targeted_figures_20260805'/'taxonomy_lt1_final'
for p in (OUT,DER,ARTICLE_MAIN,APP_MAIN,AUDIT): p.mkdir(parents=True,exist_ok=True)
SAMPLE_MAP={"Ga0540489":"AM.P1.D","Ga0541010":"AM.P1.R","Ga0541011":"AM.P2.D","Ga0541012":"AM.P2.R","Ga0541013":"TIA.P1.D","Ga0541014":"TIA.P1.R","Ga0541015":"TIA.P2.D","Ga0541016":"TIA.P2.R","Ga0541017":"TI.P1.D","Ga0541018":"TI.P1.R","Ga0541019":"TI.P2.D","Ga0541020":"TI.P2.R","Ga0541021":"TI.P3.D","Ga0541022":"TI.P3.R","Ga0541023":"TI.P4.D","Ga0541024":"TI.P4.R","Ga0541025":"VI.P1.D","Ga0541026":"VI.P1.R","Ga0541027":"VI.P2.D","Ga0541028":"VI.P2.R"}
SAMPLE_ORDER=["AM.P1.D","AM.P1.R","AM.P2.D","AM.P2.R","TIA.P1.D","TIA.P1.R","TIA.P2.D","TIA.P2.R","TI.P1.D","TI.P1.R","TI.P2.D","TI.P2.R","TI.P3.D","TI.P3.R","TI.P4.D","TI.P4.R","VI.P1.D","VI.P1.R","VI.P2.D","VI.P2.R"]
LAKE_COLORS={"AM":"#0072B2","TIA":"#E69F00","TI":"#009E73","VI":"#CC79A7"}; SEASON_MARKERS={"Dry":"o","Rainy":"s"}
ORD=BASE/'reproducibility'/'ordination_reproducibility'

def sha256(path):
  h=hashlib.sha256()
  with path.open('rb') as f:
    for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
  return h.hexdigest()

def load_inputs():
  otu=pd.read_csv(DATA/'resultado.cds.otu.tab',sep='\t',index_col=0)
  tax_path=DATA/'resultado.cds.tax.display_current.tab'
  tax=pd.read_csv(tax_path if tax_path.exists() else DATA/'resultado.cds.tax.tab',sep='\t',index_col=0)
  otu.index=otu.index.astype(str).str.strip(); tax.index=tax.index.astype(str).str.strip()
  otu.columns=[SAMPLE_MAP.get(str(c).split('_')[0].strip('.'),str(c).split('_')[0].strip('.')) for c in otu.columns]
  otu=otu.reindex(columns=SAMPLE_ORDER).apply(pd.to_numeric,errors='coerce').fillna(0)
  tax.columns=[str(c).strip() for c in tax.columns]
  tax=normalize_taxonomy_table(tax, DATA/'mapeamento_taxonomico.csv')
  return otu,tax

def add_caption(fig,text,stem,**kw):
  # The provenance footer is registered as editable text and inserted under the
  # figure by the document/app build; it is never rasterised into the image.
  register_caption(stem,text)

def save_all(fig,stem,dpi=600):
  paths=[]
  for ext in ('png','pdf','svg'):
    p=OUT/f'{stem}.{ext}'; fig.savefig(p,dpi=dpi if ext=='png' else None,bbox_inches='tight',pad_inches=0.06,facecolor='white'); paths.append(p)
  plt.close(fig)
  for p in paths:
    for dst_dir in (ARTICLE_MAIN,APP_MAIN): shutil.copy2(p,dst_dir/p.name)
  return {p.name:sha256(p) for p in paths}

def percentage_label(value):
  """Format a bar percentage without hiding small Unclassified fractions."""
  value=float(value)
  return f'{value:.2f}%' if 0 < value < 1 else f'{value:.1f}%'

def annotate_unclassified(ax,rel,samples,fontsize=11.5):
  """Print the exact per-sample Unclassified percentage on every non-zero bar."""
  if UNCLASSIFIED not in rel.index:
    return
  taxa=list(rel.index); position=taxa.index(UNCLASSIFIED)
  starts=rel.loc[taxa[:position],samples].sum(axis=0) if position else pd.Series(0.0,index=samples)
  values=rel.loc[UNCLASSIFIED,samples]
  for y,sample in enumerate(samples):
    value=float(values.at[sample])
    if value <= 0:
      continue
    label=ax.text(float(starts.at[sample])+value/2.0,y,percentage_label(value),
      ha='center',va='center',fontsize=fontsize,fontweight='bold',color='white',
      clip_on=False,zorder=12)
    label.set_path_effects([path_effects.Stroke(linewidth=2.2,foreground='#111111'),path_effects.Normal()])

def phylum_figure(rel,domain,stem,palette):
  # A landscape source matches the manuscript text block: both seasons occupy
  # the full available width while retaining enough room for the complete key.
  taxa=list(rel.index); fig,axes=plt.subplots(1,2,figsize=(15.0,9.5),sharex=True)
  for ax,suffix,panel,label in zip(axes,['D','R'],['A','B'],['Dry season','Rainy season']):
    samples=[s for s in SAMPLE_ORDER if s.endswith('.'+suffix)]
    y=np.arange(len(samples)); left=np.zeros(len(samples))
    for taxon in taxa:
      vals=rel.loc[taxon,samples].to_numpy(float); ax.barh(y,vals,left=left,color=palette[taxon],edgecolor='white',linewidth=.25); left+=vals
    annotate_unclassified(ax,rel,samples,fontsize=11.5)
    ax.set_yticks(y,samples,fontsize=17); ax.invert_yaxis(); ax.set_xlim(0,100); ax.tick_params(axis='x',labelsize=16)
    ax.set_title(f'{panel}  {label}',loc='left',fontsize=22,fontweight='bold',pad=9); ax.spines[['top','right']].set_visible(False); ax.grid(False)
    ax.set_xlabel('Relative abundance (%)',fontsize=19,fontweight='bold',labelpad=9)
    ax.set_ylabel('CDS-classified sediment sample',fontsize=18,fontweight='bold')
  legend_cols=min(6,max(3,math.ceil(len(taxa)/3)))
  fig.legend(handles=[Patch(facecolor=palette[t],edgecolor='none',label=t) for t in taxa],title='Phylum',loc='lower center',bbox_to_anchor=(.5,.012),ncol=legend_cols,frameon=False,fontsize=14.5,title_fontsize=16)
  fig.suptitle(f'{domain} phylum-level taxonomic profiles',fontsize=25,fontweight='bold',y=.985); fig.subplots_adjust(left=.085,right=.985,bottom=.245,top=.91,wspace=.22)
  add_caption(fig,taxonomy_caption('scripts/generate_targeted_figures_20260805.py',stem),stem)
  return save_all(fig,stem)

def frozen_ordination(domain):
  out=ORD/'output'; tables=ORD/'tables'
  nmds=pd.read_csv(out/f'{domain}_NMDS_scores.csv'); sites=pd.read_csv(out/f'{domain}_RDA_site_scores.csv'); env=pd.read_csv(out/f'{domain}_RDA_environment_vectors.csv'); taxa=pd.read_csv(out/f'{domain}_RDA_representative_genus_vectors.csv')
  nstats=json.loads((out/f'{domain}_NMDS_statistics.json').read_text(encoding='utf-8'))
  rstats=pd.read_csv(tables/f'{domain}_RDA_model_statistics.csv').iloc[0]
  return nmds,sites,env,taxa,nstats,rstats

def draw_stacked(ax,rel,samples,palette,panel,title):
  y=np.arange(len(samples)); left=np.zeros(len(samples))
  for taxon in rel.index:
    vals=rel.loc[taxon,samples].to_numpy(float); ax.barh(y,vals,left=left,color=palette[taxon],edgecolor='white',linewidth=.20); left+=vals
  annotate_unclassified(ax,rel,samples,fontsize=10.5)
  ax.set_yticks(y,samples,fontsize=17); ax.invert_yaxis(); ax.set_xlim(0,100); ax.tick_params(axis='x',labelsize=16); ax.set_xlabel('Relative abundance (%)',fontsize=19,fontweight='bold'); ax.set_title(f'{panel}  {title}',loc='left',fontsize=21,fontweight='bold'); ax.spines[['top','right']].set_visible(False); ax.grid(False)

def draw_inner_taxon_labels(ax,taxa,scale,palette,xlim,ylim):
  """Draw frozen RDA genus vectors with labels separated from sample columns."""
  xmin,xmax=xlim; ymin,ymax=ylim; xr=xmax-xmin; yr=ymax-ymin
  entries=[]
  for name,row in taxa.iterrows():
    x=float(row.RDA1*scale); y=float(row.RDA2*scale); color=palette.get(str(name),'#111111')
    ax.annotate('',xy=(x,y),xytext=(0,0),arrowprops=dict(arrowstyle='-|>',color=color,lw=1.7,linestyle='--'),zorder=3)
    entries.append((str(name),x,y,color))
  for side in (-1,1):
    side_entries=sorted([e for e in entries if (e[1]<0)==(side<0)],key=lambda e:e[2],reverse=True)
    if not side_entries: continue
    lower=ymin+yr*.16; upper=ymax-yr*.16
    if len(side_entries)==1:
      placed=[lower+(upper-lower)*(.22 if side>0 else .50)]
    else:
      placed=list(np.linspace(upper,lower,len(side_entries)))
      if side>0:
        placed=[float(np.clip(v+(yr*.105 if i%2 else 0),lower,upper)) for i,v in enumerate(placed)]
    lx=(xmin+xmax)/2 if side>0 and len(side_entries)==1 else (xmin+xr*.32 if side<0 else xmax-xr*.32)
    for (name,x,y,color),ly in zip(side_entries,placed):
      ax.annotate(name,xy=(x,y),xytext=(lx,ly),textcoords='data',
        ha='center',va='center',fontsize=11.2,fontweight='bold',color=color,
        arrowprops=dict(arrowstyle='-',color=color,lw=.75,alpha=.8),
        bbox=dict(boxstyle='round,pad=0.12',fc='white',ec='none',alpha=.88),annotation_clip=True,zorder=9)

def genus_figure(rel,domain,stem,palette):
  scores,sites,env,taxvec,nstats,rstats=frozen_ordination(domain)
  # Landscape 2 x 2 layout fills the manuscript text width and leaves room for
  # a complete external genus key without compressing the ordination panels.
  fig=plt.figure(figsize=(15.0,9.6)); gs=fig.add_gridspec(2,2,height_ratios=[1.0,1.12],width_ratios=[1,1],hspace=.48,wspace=.28)
  axA=fig.add_subplot(gs[0,0]); axB=fig.add_subplot(gs[0,1]); axC=fig.add_subplot(gs[1,0]); axD=fig.add_subplot(gs[1,1])
  dry=[s for s in SAMPLE_ORDER if s.endswith('.D')]; rainy=[s for s in SAMPLE_ORDER if s.endswith('.R')]
  draw_stacked(axA,rel,dry,palette,'A','Dry-season genus profiles'); draw_stacked(axB,rel,rainy,palette,'B','Rainy-season genus profiles')
  for lake in ['AM','TIA','TI','VI']:
    for season in ['Dry','Rainy']:
      d=scores[(scores.Lake.astype(str)==lake)&(scores.Season.astype(str)==season)]
      axC.scatter(d.NMDS1,d.NMDS2,s=110,color=LAKE_COLORS[lake],marker=SEASON_MARKERS[season],edgecolor='black',linewidth=.6,zorder=3)
  stress=float(nstats['stress_1']); axC.axhline(0,color='#AAA',lw=.6); axC.axvline(0,color='#AAA',lw=.6); axC.set_xlabel('NMDS1',fontweight='bold',fontsize=18); axC.set_ylabel('NMDS2',fontweight='bold',fontsize=18); axC.tick_params(labelsize=15.5); axC.set_title(f'C  Bray-Curtis NMDS (stress = {stress:.3f})',loc='left',fontsize=20,fontweight='bold'); axC.margins(.22)
  _repelled_point_labels(axC,scores,'NMDS1','NMDS2','Sample',fontsize=15.0)
  for lake,d in sites.groupby('Lake'):
    axD.scatter(d.RDA1,d.RDA2,s=105,color=LAKE_COLORS.get(lake,'#777'),edgecolor='black',linewidth=.6,zorder=4)
  extent=max(float(np.max(np.abs(sites[['RDA1','RDA2']].to_numpy()))),1e-6); env_scale=extent*.82; tax_scale=extent*.70
  arrow_x=[0.0]+[float(v)*env_scale for v in env.RDA1]+[float(v)*tax_scale for v in taxvec.RDA1]
  arrow_y=[0.0]+[float(v)*env_scale for v in env.RDA2]+[float(v)*tax_scale for v in taxvec.RDA2]
  xmin=min(float(sites.RDA1.min()),min(arrow_x)); xmax=max(float(sites.RDA1.max()),max(arrow_x))
  ymin=min(float(sites.RDA2.min()),min(arrow_y)); ymax=max(float(sites.RDA2.max()),max(arrow_y))
  xr=max(xmax-xmin,extent); yr=max(ymax-ymin,extent)
  xlim=(xmin-xr*.48,xmax+xr*.48); ylim=(ymin-yr*.33,ymax+yr*.33)
  axD.set_xlim(*xlim); axD.set_ylim(*ylim)
  # The helpers label rows by DataFrame index and draw the arrows themselves, so
  # the frozen tables are re-indexed on their name column before being passed in.
  env_idx=env.set_index('Variable')[['RDA1','RDA2']]
  tax_idx=taxvec.set_index('Genus')[['RDA1','RDA2']]
  _bounded_environment_labels(axD,env_idx,env_scale,xlim,ylim)
  draw_inner_taxon_labels(axD,tax_idx,tax_scale,palette,xlim,ylim)
  _repelled_point_labels(axD,sites,'RDA1','RDA2','Sample',fontsize=15.0)
  r2=float(rstats.R2); p=float(rstats.global_permutation_p); p1=float(rstats.RDA1_constrained_variance_percent); p2=float(rstats.RDA2_constrained_variance_percent); radj=float(rstats.adjusted_R2)
  axD.axhline(0,color='#AAA',lw=.6); axD.axvline(0,color='#AAA',lw=.6); axD.set_xlabel(f'RDA1 ({p1:.1f}% constrained variation)',fontsize=18,fontweight='bold'); axD.set_ylabel(f'RDA2 ({p2:.1f}% constrained variation)',fontsize=18,fontweight='bold'); axD.tick_params(labelsize=15); axD.set_title(f'D  RDA biplot\nR² = {r2:.2f}; adjusted R² = {radj:.3f}; P = {p:.3f}',loc='left',fontsize=18,fontweight='bold')
  axD.legend(handles=[Line2D([0],[0],color='#3F3F46',lw=1.5,label='Environmental variable'),Line2D([0],[0],color='#555',lw=1.5,linestyle='--',label='Representative genus vector')],loc='upper center',bbox_to_anchor=(.5,-.18),frameon=True,framealpha=.88,edgecolor='#CCC',fontsize=11.5,ncol=2)
  tax_handles=[Patch(facecolor=palette[t],edgecolor='none',label=t) for t in rel.index]
  fig.legend(handles=tax_handles,title='Genus',loc='lower center',bbox_to_anchor=(.5,.010),ncol=min(6,max(3,math.ceil(len(tax_handles)/2))),frameon=False,fontsize=14,title_fontsize=16)
  ord_handles=[Line2D([0],[0],marker='o',linestyle='None',markerfacecolor=LAKE_COLORS[l],markeredgecolor='black',label=l,markersize=7) for l in ['AM','TIA','TI','VI']]+[Line2D([0],[0],marker=SEASON_MARKERS[s],linestyle='None',color='black',label=s,markersize=7) for s in ['Dry','Rainy']]
  axC.legend(handles=ord_handles,loc='upper center',bbox_to_anchor=(.5,-.18),frameon=True,framealpha=.88,edgecolor='#CCC',fontsize=11.5,title='Lake / season',title_fontsize=12.5,ncol=3)
  fig.suptitle(f'{domain} genus-level taxonomic profiles and ordination',fontsize=24,fontweight='bold',y=.987); fig.subplots_adjust(left=.075,right=.985,top=.92,bottom=.29)
  add_caption(fig,taxonomy_caption('scripts/generate_targeted_figures_20260805.py',stem,
    'Panels C and D: '+ordination_caption('scripts/generate_targeted_figures_20260805.py',stem).split('Method: ')[1].rstrip('.')+
    '. The RDA constrains 6 predictors on 10 pooled sampling positions (3 residual degrees of freedom), so the adjusted R2 and the permutation P are the interpretable statistics'),stem)
  return save_all(fig,stem), {'NMDS_stress':stress,'RDA_R2':r2,'RDA_p':p,'RDA1_percent':p1,'RDA2_percent':p2}

def main():
  otu,tax=load_inputs(); full={}; display={}; validations={}; audit_frames=[]
  for domain in ('Bacteria','Archaea'):
    for rank in ('Phylum','Genus'):
      key=f'{domain}_{rank}'; full[key]=aggregate_relative_abundance(otu,tax,domain,rank); display[key]=collapse_below_threshold(full[key]); validations[key]=validate_strict_threshold(full[key],display[key]); audit_frames.append(build_threshold_audit(full[key],display[key],domain,rank)); full[key].to_csv(DER/f'{key}_full_relative_abundance_percent.csv'); display[key].to_csv(DER/f'{key}_strict_lt1_display_source.csv')
  row_audit=pd.concat(audit_frames,ignore_index=True)
  if not row_audit.validation_status.eq('PASS').all(): raise RuntimeError('Taxonomy row-level audit failed')
  grouped=row_audit.loc[row_audit.grouped_into_other].copy()
  unclassified=row_audit.loc[row_audit.is_unclassified,[
    'domain','taxonomic_level','sample_or_group','original_taxon',
    'original_relative_abundance','displayed_percentage','sum_before','sum_after','validation_status']].copy()
  for directory in (AUDIT,DER):
    row_audit.to_csv(directory/'TAXONOMY_STRICT_LT1_ROW_AUDIT_20260805.csv',index=False)
    grouped.to_csv(directory/'OTHER_TAXA_LT1_TRACEABILITY_20260805.csv',index=False)
    unclassified.to_csv(directory/'UNCLASSIFIED_PERCENTAGES_20260805.csv',index=False)
  taxa=[]
  for m in display.values(): taxa.extend(m.index.tolist())
  for domain in ('Bacteria','Archaea'):
    _,_,_,tv,_,_=frozen_ordination(domain); taxa.extend(tv.Genus.astype(str).tolist())
  palette=build_palette(taxa,load_palette(DATA/'taxonomy_palette.json')); save_palette(palette,DATA/'taxonomy_palette.json')
  figures={}
  figures['Figure2']=phylum_figure(display['Bacteria_Phylum'],'Bacteria','Figure2_taxonomic_phylum_bacteria_horizontal_CDS',palette)
  figures['Figure3']=phylum_figure(display['Archaea_Phylum'],'Archaea','Figure3_taxonomic_phylum_archaea_horizontal_CDS',palette)
  figures['Figure4'],s4=genus_figure(display['Bacteria_Genus'],'Bacteria','Figure4_taxonomic_bacteria_genus_profiles',palette)
  figures['Figure5'],s5=genus_figure(display['Archaea_Genus'],'Archaea','Figure5_taxonomic_archaea_genus_profiles',palette)
  report={'script':str(Path(__file__).relative_to(BASE)),'rule':'Per sample, every classified taxon with relative abundance strictly <1.0% is summed into Other taxa (<1%); exactly 1.0% remains explicit; missing/NA-like classifications are Unclassified and remain independent.','ordination':'Canonical frozen coordinates, vectors and statistics loaded without recomputation.','generative_ai_used':False,'validations':validations,'figures':figures,'ordination_statistics':{'Figure4':s4,'Figure5':s5}}
  (AUDIT/'MAIN_TAXONOMY_STRICT_LT1_VALIDATION.json').write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8')
  if not all(v['pass'] for v in validations.values()): raise RuntimeError('Strict <1% validation failed')
  print(json.dumps(report,indent=2,ensure_ascii=False))
if __name__=='__main__': main()
