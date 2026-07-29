#!/usr/bin/env python3
"""Materialize an unchanged, hash-validated packaged publication asset.

This is used only for non-target figures whose legacy computational generator
was not included or was not runnable from the received self-contained package.
It copies exact packaged PNG/PDF/SVG bytes after SHA-256 validation. It performs
no image editing, conversion, resampling, normalization or scientific analysis.
"""
from __future__ import annotations
import argparse, hashlib, json, shutil
from pathlib import Path

def digest(path: Path) -> str:
  h=hashlib.sha256()
  with path.open('rb') as handle:
    for block in iter(lambda:handle.read(1024*1024),b''): h.update(block)
  return h.hexdigest()

def main()->int:
  p=argparse.ArgumentParser(description=__doc__)
  p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
  p.add_argument('--stem',required=True)
  p.add_argument('--article-root',type=Path)
  p.add_argument('--validate-only',action='store_true')
  a=p.parse_args(); root=a.root.resolve()
  source_dir=root/'data'/'preserved_publication_assets'/a.stem
  destinations=[root/'outputs'/'final_publication_figures',root/'outputs'/'app_supplementary_figures']
  if a.article_root: destinations.append(a.article_root.resolve()/'03_Supplementary_Figures')
  result={'stem':a.stem,'files':[]}
  for ext in ('png','pdf','svg'):
    source=source_dir/f'{a.stem}.{ext}'
    if not source.exists(): raise FileNotFoundError(source)
    source_hash=digest(source); item={'source':str(source),'sha256':source_hash,'destinations':[]}
    for directory in destinations:
      directory.mkdir(parents=True,exist_ok=True); target=directory/source.name
      if not a.validate_only: shutil.copy2(source,target)
      if not target.exists() or digest(target)!=source_hash: raise RuntimeError(f'Hash mismatch: {target}')
      item['destinations'].append(str(target))
    result['files'].append(item)
  result['status']='PASS'; result['operation']='validation only' if a.validate_only else 'exact-byte materialization'
  print(json.dumps(result,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
