#!/usr/bin/env python3
"""Generate canonical domain-separated taxonomy supplementary figures.

The scientific matrices, top-taxon rules, sample order, palette, and values are
unchanged. This revision adds targeted execution and page-aware typography so
requested figures remain legible at 100% zoom in the supplementary Word/PDF.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import shutil
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
import numpy as np
import pandas as pd
from PIL import Image

SAMPLE_MAP = {
  "Ga0540489": "AM.P1.D", "Ga0541010": "AM.P1.R", "Ga0541011": "AM.P2.D", "Ga0541012": "AM.P2.R",
  "Ga0541013": "TIA.P1.D", "Ga0541014": "TIA.P1.R", "Ga0541015": "TIA.P2.D", "Ga0541016": "TIA.P2.R",
  "Ga0541017": "TI.P1.D", "Ga0541018": "TI.P1.R", "Ga0541019": "TI.P2.D", "Ga0541020": "TI.P2.R",
  "Ga0541021": "TI.P3.D", "Ga0541022": "TI.P3.R", "Ga0541023": "TI.P4.D", "Ga0541024": "TI.P4.R",
  "Ga0541025": "VI.P1.D", "Ga0541026": "VI.P1.R", "Ga0541027": "VI.P2.D", "Ga0541028": "VI.P2.R",
}
SAMPLE_ORDER = [
  "AM.P1.D", "AM.P1.R", "AM.P2.D", "AM.P2.R", "TIA.P1.D", "TIA.P1.R", "TIA.P2.D", "TIA.P2.R",
  "TI.P1.D", "TI.P1.R", "TI.P2.D", "TI.P2.R", "TI.P3.D", "TI.P3.R", "TI.P4.D", "TI.P4.R",
  "VI.P1.D", "VI.P1.R", "VI.P2.D", "VI.P2.R",
]
DOMAINS = ["Bacteria", "Archaea"]
RANKS = ["Phylum", "Class", "Order", "Family", "Genus", "Species"]
TOP_BAR = 24
TOP_HEATMAP = 30
START_NUMBER = 43
REQUESTED = {47, 49, 51, 53, 55, 57, 58, 61, 63, 65}
PROPORTION_ONLY_BAR_FIGURES = {47, 49, 51, 53, 55, 57, 61, 63, 65}


def sha256(path: Path) -> str:
  h = hashlib.sha256()
  with path.open("rb") as handle:
    for block in iter(lambda: handle.read(1024 * 1024), b""):
      h.update(block)
  return h.hexdigest()


def normalise_label(value: object) -> str:
  text = str(value if value is not None else "").strip()
  if not text or text.casefold() in {"nan", "none", "na", "n/a", "unknown", "undefined", "null"}:
    return "Unclassified"
  return text


def wrap_label(value: object, width: int) -> str:
  return "\n".join(textwrap.wrap(normalise_label(value), width=max(10, width), break_long_words=False, break_on_hyphens=False))


def load_palette(path: Path) -> dict[str, str]:
  return json.loads(path.read_text(encoding="utf-8"))


def load_inputs(data: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
  otu = pd.read_csv(data / "resultado.cds.otu.tab", sep="\t", index_col=0)
  tax = pd.read_csv(data / "resultado.cds.tax.tab", sep="\t", index_col=0)
  otu.index = otu.index.astype(str).str.strip(); tax.index = tax.index.astype(str).str.strip()
  otu.columns = [SAMPLE_MAP.get(str(c).split("_")[0].strip("."), str(c).split("_")[0].strip(".")) for c in otu.columns]
  otu = otu.reindex(columns=[s for s in SAMPLE_ORDER if s in otu.columns]).apply(pd.to_numeric, errors="coerce").fillna(0)
  tax.columns = [str(c).strip() for c in tax.columns]
  for col in tax.columns:
    tax[col] = tax[col].map(normalise_label)
  return otu, tax


def relative_matrix(otu: pd.DataFrame, tax: pd.DataFrame, domain: str, rank: str) -> pd.DataFrame:
  shared = otu.index.intersection(tax.index)
  mask = tax.loc[shared, "Domain"].astype(str).str.strip().str.casefold().eq(domain.casefold())
  ids = shared[mask.to_numpy()]
  labels = tax.loc[ids, rank].map(normalise_label)
  counts = otu.loc[ids].copy(); counts["__taxon__"] = labels.to_numpy()
  agg = counts.groupby("__taxon__", sort=False).sum(numeric_only=True)
  rel = agg.div(agg.sum(axis=0).replace(0, np.nan), axis=1).fillna(0) * 100.0
  return rel.loc[rel.sum(axis=1).sort_values(ascending=False).index]


def top_with_others(rel: pd.DataFrame, top_n: int) -> pd.DataFrame:
  keep = rel.sum(axis=1).nlargest(min(top_n, len(rel))).index
  out = rel.loc[keep].copy()
  remainder = rel.drop(index=keep, errors="ignore").sum(axis=0)
  if float(remainder.sum()) > 0:
    out.loc["Others"] = remainder
  totals = out.sum(axis=0).replace(0, np.nan)
  return out.div(totals, axis=1).fillna(0) * 100.0


def save_formats(fig: plt.Figure, stem: Path, dpi: int = 300) -> dict[str, object]:
  stem.parent.mkdir(parents=True, exist_ok=True)
  png, pdf, svg = stem.with_suffix(".png"), stem.with_suffix(".pdf"), stem.with_suffix(".svg")
  fig.savefig(png, dpi=dpi, facecolor="white")
  with Image.open(png) as opened:
    image = opened.convert("RGB"); dims = list(image.size); image.save(pdf, "PDF", resolution=float(dpi))
  payload = base64.b64encode(png.read_bytes()).decode("ascii")
  svg.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{dims[0]}" height="{dims[1]}" viewBox="0 0 {dims[0]} {dims[1]}"><image href="data:image/png;base64,{payload}" width="{dims[0]}" height="{dims[1]}"/></svg>', encoding="utf-8")
  return {"png": {"path": str(png), "sha256": sha256(png), "dimensions": dims}, "pdf": {"path": str(pdf), "sha256": sha256(pdf)}, "svg": {"path": str(svg), "sha256": sha256(svg)}}


def validate_layout(fig: plt.Figure, ax: plt.Axes, title_artist, legend=None, colourbar=None, legend_relation: str = "below") -> dict[str, object]:
  fig.canvas.draw(); renderer = fig.canvas.get_renderer(); figbox = fig.bbox; axbox = ax.get_window_extent(renderer)
  artists = [title_artist, ax.xaxis.label, ax.yaxis.label, *ax.get_xticklabels(), *ax.get_yticklabels()]
  if legend is not None: artists += list(legend.get_texts())
  if colourbar is not None: artists += [colourbar.ax.yaxis.label, *colourbar.ax.get_yticklabels()]
  outside=[]
  for artist in artists:
    if not artist.get_visible() or not artist.get_text(): continue
    b=artist.get_window_extent(renderer)
    if b.x0 < figbox.x0-2 or b.y0 < figbox.y0-2 or b.x1 > figbox.x1+2 or b.y1 > figbox.y1+2:
      outside.append({"text":artist.get_text().replace("\n"," | ")[:160],"bbox":[b.x0,b.y0,b.x1,b.y1]})
  result={"all_text_inside_figure":not outside,"outside_texts":outside,"axes_bbox":[axbox.x0,axbox.y0,axbox.x1,axbox.y1]}
  if legend is not None:
    lb=legend.get_window_extent(renderer)
    result["legend_inside_figure"]=bool(lb.x0>=figbox.x0 and lb.y0>=figbox.y0 and lb.x1<=figbox.x1 and lb.y1<=figbox.y1)
    if legend_relation == "right":
      result["legend_right_of_plot"]=bool(lb.x0 > axbox.x1)
      relation_ok=result["legend_right_of_plot"]
    else:
      result["legend_below_plot"]=bool(lb.y1<axbox.y0)
      relation_ok=result["legend_below_plot"]
  else:
    relation_ok=True
  if not result["all_text_inside_figure"] or not relation_ok or (legend is not None and not result["legend_inside_figure"]):
    raise RuntimeError(f"Typography/layout validation failed: {result}")
  return result


def draw_barplot(matrix: pd.DataFrame, domain: str, rank: str, palette: dict[str, str], figure_id: int) -> tuple[plt.Figure, dict[str, object]]:
  taxa = list(matrix.index); samples = list(matrix.columns)
  proportion_only = figure_id in PROPORTION_ONLY_BAR_FIGURES
  if proportion_only:
    # Supplementary Figure 59 is the accepted proportion reference. The plot
    # occupies the left portion of a 15.98 x 9.45 inch canvas and the unchanged
    # legend is placed to the right, preventing horizontal stretching.
    figsize=(15.00,10.50); axpos=[0.095,0.080,0.670,0.820]
  else:
    figsize=(15.20,9.45); axpos=[0.075,0.395,0.895,0.475]
  fig=plt.figure(figsize=figsize,facecolor="white"); ax=fig.add_axes(axpos)
  y=np.arange(len(samples)); left=np.zeros(len(samples))
  for taxon in taxa:
    values=matrix.loc[taxon,samples].to_numpy(float)
    ax.barh(y,values,left=left,height=0.80,color=palette[taxon],edgecolor="white",linewidth=0.3)
    left += values
  ax.set_xlim(0,100); ax.set_yticks(y,samples,fontsize=12.5); ax.invert_yaxis()
  ax.set_xlabel("Relative abundance (%)",fontsize=14.5,fontweight="bold",labelpad=9)
  ax.set_ylabel("Sediment metagenome sample",fontsize=14.5,fontweight="bold",labelpad=8)
  ax.tick_params(axis="x",labelsize=12.0); ax.spines[["top","right"]].set_visible(False); ax.grid(False)
  title=fig.text(0.045,0.965,f"{domain} — {rank} — barplot by individual sample",fontsize=17.0,fontweight="bold",ha="left",va="top")
  handles=[Patch(facecolor=palette[t],edgecolor="none",label=wrap_label(t,24 if proportion_only else 30)) for t in taxa]
  if proportion_only:
    legend=fig.legend(handles=handles,title=rank,loc="center left",bbox_to_anchor=(0.780,0.520),ncol=1,frameon=False,fontsize=11.5,title_fontsize=13.0,handlelength=1.2,columnspacing=1.0,labelspacing=0.30,borderaxespad=0.0)
    layout=validate_layout(fig,ax,title,legend=legend,legend_relation="right")
    legend_columns=1
  else:
    ncol=4 if rank in {"Family","Genus","Species"} else (5 if len(handles)>=18 else 3)
    legend=fig.legend(handles=handles,title=rank,loc="lower left",bbox_to_anchor=(0.04,0.012,0.92,0.34),mode="expand",ncol=ncol,frameon=False,fontsize=11.5,title_fontsize=13.0,handlelength=1.2,columnspacing=1.0,labelspacing=0.55,borderaxespad=0.0)
    layout=validate_layout(fig,ax,title,legend=legend,legend_relation="below")
    legend_columns=ncol
  layout.update({"figure_inches":[figsize[0],figsize[1]],"aspect_ratio":round(figsize[0]/figsize[1],3),"title_font_pt":17.0,"axis_title_font_pt":14.5,"tick_font_pt":12.0,"sample_label_font_pt":12.5,"legend_font_pt":11.5,"legend_columns":legend_columns,"panel_count":1,"proportion_only_adjustment":proportion_only,"scientific_values_changed":False})
  return fig,layout


def draw_heatmap(matrix: pd.DataFrame, domain: str, rank: str, figure_id: int) -> tuple[plt.Figure, pd.DataFrame, dict[str, object]]:
  raw=matrix.to_numpy(float); transformed=np.log10(np.clip(raw,a_min=0.0,a_max=None)+1.0); transformed_df=pd.DataFrame(transformed,index=matrix.index,columns=matrix.columns)
  figsize=(13.70,10.10) if figure_id == 48 else (15.20,9.45)
  axpos=[0.205,0.16,0.695,0.74] if figure_id == 48 else [0.235,0.19,0.655,0.68]
  cbarpos=[0.920,0.28,0.020,0.50] if figure_id == 48 else [0.915,0.30,0.018,0.48]
  fig=plt.figure(figsize=figsize,facecolor="white")
  ax=fig.add_axes(axpos)
  vmax=max(0.01,float(np.nanmax(transformed)))
  image=ax.imshow(transformed,aspect="auto",interpolation="nearest",cmap="coolwarm_r",vmin=0,vmax=vmax)
  ax.set_xticks(np.arange(matrix.shape[1]),matrix.columns,rotation=58,ha="right",rotation_mode="anchor",fontsize=12.0)
  ax.set_yticks(np.arange(matrix.shape[0]),[wrap_label(x,28) for x in matrix.index],fontsize=11.5)
  ax.tick_params(axis="y",pad=3);ax.tick_params(axis="x",pad=3)
  ax.set_xlabel("Sediment metagenome sample",fontsize=14.5,fontweight="bold",labelpad=10)
  ax.set_ylabel(rank,fontsize=14.5,fontweight="bold",labelpad=8)
  title_text=wrap_label(f"{domain} — {rank} — relative-abundance heatmap [log10(x + 1)]",52)
  title=fig.text(0.045,0.965,title_text,fontsize=17.0,fontweight="bold",ha="left",va="top",linespacing=1.08)
  cax=fig.add_axes(cbarpos);cb=fig.colorbar(image,cax=cax);cb.set_label("log10(relative abundance\n[%] + 1)",fontsize=12.0,fontweight="bold",labelpad=7);cb.ax.tick_params(labelsize=11.0)
  layout=validate_layout(fig,ax,title,colourbar=cb)
  layout.update({"figure_inches":[figsize[0],figsize[1]],"title_font_pt":17.0,"axis_title_font_pt":14.5,"x_tick_font_pt":12.0,"y_tick_font_pt":11.5,"colourbar_font_pt":11.0,"panel_count":1})
  return fig,transformed_df,layout


def figure_number(domain: str, rank: str, plot_type: str) -> int:
  number=START_NUMBER
  for r in RANKS:
    for d in DOMAINS:
      if d==domain and r==rank:
        return number if plot_type=="bar" else number+1
      number += 2
  raise KeyError((domain,rank,plot_type))


def parse_args() -> argparse.Namespace:
  parser=argparse.ArgumentParser()
  parser.add_argument('--base-dir',type=Path,default=Path(__file__).resolve().parents[1])
  parser.add_argument('--article-root',type=Path)
  parser.add_argument('--only',type=int,action='append')
  parser.add_argument('--png-dpi',type=int,default=300)
  return parser.parse_args()


def main() -> int:
  args=parse_args(); root=args.base_dir.resolve(); article_root=args.article_root.resolve() if args.article_root else None
  selected=set(args.only) if args.only else REQUESTED
  invalid=selected-{n for n in range(43,67)}
  if invalid: raise ValueError(f"Unsupported taxonomy supplementary figure(s): {sorted(invalid)}")
  data=root/'data';out=root/'outputs'/'final_publication_figures';app_out=root/'outputs'/'app_supplementary_figures';derived=data/'final_publication_derived';article_dir=article_root/'03_Supplementary_Figures' if article_root else None
  for folder in [out,app_out,derived]+([article_dir] if article_dir else []): folder.mkdir(parents=True,exist_ok=True)
  otu,tax=load_inputs(data); palette=load_palette(data/'taxonomy_palette.json')
  records=[]
  for rank in RANKS:
    for domain in DOMAINS:
      rel=relative_matrix(otu,tax,domain,rank)
      bar_number=figure_number(domain,rank,'bar');heat_number=bar_number+1
      if bar_number in selected:
        bar=top_with_others(rel,TOP_BAR);stem=f"SupplementaryFigure{bar_number}_Taxonomy_{domain}_{rank}_individual_samples_barplot_100pct"
        print(f"Generating {stem}",flush=True)
        fig,layout=draw_barplot(bar,domain,rank,palette,bar_number);outputs=save_formats(fig,out/stem,args.png_dpi);plt.close(fig)
        for ext in ('png','pdf','svg'):
          shutil.copy2(out/f'{stem}.{ext}',app_out/f'{stem}.{ext}')
          if article_dir: shutil.copy2(out/f'{stem}.{ext}',article_dir/f'{stem}.{ext}')
        bar.to_csv(derived/f'{stem}_source.csv')
        records.append({"figure":f"S{bar_number}","stem":stem,"script":"scripts/generate_taxonomy_supplementary_figures.py","command":f"python scripts/generate_taxonomy_supplementary_figures.py --base-dir . --article-root <article_root> --only {bar_number}","inputs":["data/resultado.cds.otu.tab","data/resultado.cds.tax.tab","data/taxonomy_palette.json"],"outputs":outputs,"layout":layout,"scientific_values_changed":False,"top_rule":f"Top {TOP_BAR} taxa plus Others, unchanged"})
      if heat_number in selected:
        heat=rel.head(min(TOP_HEATMAP,len(rel))).copy();stem=f"SupplementaryFigure{heat_number}_Taxonomy_{domain}_{rank}_individual_samples_heatmap_relative_abundance"
        print(f"Generating {stem}",flush=True)
        fig,transformed,layout=draw_heatmap(heat,domain,rank,heat_number);outputs=save_formats(fig,out/stem,args.png_dpi);plt.close(fig)
        for ext in ('png','pdf','svg'):
          shutil.copy2(out/f'{stem}.{ext}',app_out/f'{stem}.{ext}')
          if article_dir: shutil.copy2(out/f'{stem}.{ext}',article_dir/f'{stem}.{ext}')
        heat.to_csv(derived/f'{stem}_source_relative_abundance_percent.csv');transformed.to_csv(derived/f'{stem}_source_log10_x_plus_1.csv')
        records.append({"figure":f"S{heat_number}","stem":stem,"script":"scripts/generate_taxonomy_supplementary_figures.py","command":f"python scripts/generate_taxonomy_supplementary_figures.py --base-dir . --article-root <article_root> --only {heat_number}","inputs":["data/resultado.cds.otu.tab","data/resultado.cds.tax.tab"],"outputs":outputs,"layout":layout,"scientific_values_changed":False,"top_rule":f"Top {TOP_HEATMAP} taxa, unchanged"})
  validation=root/'validation';validation.mkdir(parents=True,exist_ok=True)
  report={"script":"scripts/generate_taxonomy_supplementary_figures.py","executed_utc":datetime.now(timezone.utc).isoformat(),"selected_figures":sorted(selected),"scientific_processing":"unchanged relative abundance, top-taxon rules, sample order, values and palette","records":records,"python":sys.version,"matplotlib":matplotlib.__version__,"pandas":pd.__version__,"numpy":np.__version__}
  path=validation/'taxonomy_targeted_legibility_v11_execution.json';path.write_text(json.dumps(report,indent=2,ensure_ascii=False),encoding='utf-8');print(path)
  return 0

if __name__=='__main__':
  raise SystemExit(main())
