#!/usr/bin/env python3
from __future__ import annotations
from pathlib import Path
import hashlib, shutil, textwrap
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

DPI=300
plt.rcParams.update({
 'font.family':'DejaVu Sans','font.size':12,'axes.labelsize':14,'axes.labelweight':'bold',
 'xtick.labelsize':12,'ytick.labelsize':12,'legend.fontsize':12,'legend.title_fontsize':13,
 'pdf.fonttype':42,'ps.fonttype':42,'svg.fonttype':'none','savefig.dpi':DPI,
 'axes.linewidth':1.2,'lines.linewidth':1.8
})

def wrap(s,width=42):
 return '\n'.join(textwrap.wrap(' '.join(str(s).split()),width=width,break_long_words=False))

def export(fig, stem:Path, copies:list[Path]|None=None, tight=True):
 stem.parent.mkdir(parents=True,exist_ok=True)
 kwargs={'facecolor':'white'}
 if tight: kwargs['bbox_inches']='tight'
 for ext in ('png','pdf','svg'):
  fig.savefig(stem.with_suffix('.'+ext),dpi=DPI,**kwargs)
 plt.close(fig)
 for outdir in copies or []:
  outdir.mkdir(parents=True,exist_ok=True)
  for ext in ('png','pdf','svg'):
   shutil.copy2(stem.with_suffix('.'+ext),outdir/(stem.name+'.'+ext))
 return [stem.with_suffix('.'+e) for e in ('png','pdf','svg')]

def sha256(path:Path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
 return h.hexdigest()
