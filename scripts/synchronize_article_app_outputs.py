#!/usr/bin/env python3
"""Synchronize grouped-only S40, both S67 layouts and reproducibility files."""
from __future__ import annotations
import argparse, hashlib, shutil
from pathlib import Path
import pandas as pd

STEMS = [
  "SupplementaryFigure40_ST8_external_iron_rich_module_completeness_by_environmental_group",
  "SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_KEMET_style_3state_heatmap",
  "SupplementaryFigure67_lagoon_plus_external_iron_rich_module_completeness_by_environmental_group",
]
SCRIPTS = [
  "scripts/figures/generate_environmental_group_heatmaps.py",
  "scripts/validation/compare_environmental_group_heatmaps.py",
  "scripts/build_complete_figure_script_table.py",
  "scripts/materialize_preserved_publication_asset.py",
  "scripts/synchronize_article_app_outputs.py",
  "scripts/documents/update_supplementary_information.py",
]

def sha256(path: Path) -> str:
  h=hashlib.sha256()
  with path.open('rb') as f:
    for b in iter(lambda:f.read(1024*1024),b''): h.update(b)
  return h.hexdigest()

def copy(src: Path, dst: Path) -> None:
  dst.parent.mkdir(parents=True, exist_ok=True)
  shutil.copy2(src,dst)

def main() -> int:
  p=argparse.ArgumentParser(description=__doc__)
  p.add_argument('--app-root',type=Path,default=Path(__file__).resolve().parents[1])
  p.add_argument('--article-root',type=Path,required=True)
  a=p.parse_args(); app=a.app_root.resolve(); art=a.article_root.resolve()
  rows=[]
  obsolete_stem='SupplementaryFigure40_ST8_external_iron_rich_module_completeness_KEMET_style_3state_heatmap'
  for directory in (app/'outputs'/'app_supplementary_figures', app/'outputs'/'final_publication_figures', art/'03_Supplementary_Figures'):
    directory.mkdir(parents=True,exist_ok=True)
    for candidate in directory.glob(f'{obsolete_stem}*'):
      if candidate.is_file() and candidate.suffix.lower() in {'.png','.pdf','.svg'}: candidate.unlink()
  for stem in STEMS:
    for name in [f'{stem}.png',f'{stem}.pdf',f'{stem}.svg',*[f'{stem}_P{i:03d}.{ext}' for i in (1,2) for ext in ('png','pdf','svg')]]:
      src=app/'outputs'/'final_publication_figures'/name
      if not src.exists(): continue
      app_dst=app/'outputs'/'app_supplementary_figures'/name; copy(src,app_dst)
      rows.append({'kind':'figure_app','source':str(src.relative_to(app)),'destination':str(app_dst.relative_to(app)),'sha256_source':sha256(src),'sha256_destination':sha256(app_dst),'identical':sha256(src)==sha256(app_dst)})
      dst=art/'03_Supplementary_Figures'/name; copy(src,dst)
      rows.append({'kind':'figure_article','source':str(src.relative_to(app)),'destination':str(dst.relative_to(art)),'sha256_source':sha256(src),'sha256_destination':sha256(dst),'identical':sha256(src)==sha256(dst)})
    for suffix in ('status.csv','column_order.csv'):
      src=app/'data'/'final_publication_derived'/f'{stem}_{suffix}'
      if src.exists():
        dst=art/'05_Source_Data_and_Audit'/'final_publication_derived'/src.name; copy(src,dst)
        rows.append({'kind':'derived','source':str(src.relative_to(app)),'destination':str(dst.relative_to(art)),'sha256_source':sha256(src),'sha256_destination':sha256(dst),'identical':sha256(src)==sha256(dst)})
  for name in ('environmental_group_heatmap_comparison.tsv','environmental_group_heatmap_comparison.md','environmental_group_heatmap_comparison.json'):
    src=app/'validation'/name; dst=art/'07_Validation_and_Manifests'/name; copy(src,dst)
    rows.append({'kind':'comparison','source':str(src.relative_to(app)),'destination':str(dst.relative_to(art)),'sha256_source':sha256(src),'sha256_destination':sha256(dst),'identical':sha256(src)==sha256(dst)})
  for rel in SCRIPTS:
    src=app/rel
    if src.exists():
      dst=art/rel; copy(src,dst)
      rows.append({'kind':'script','source':rel,'destination':rel,'sha256_source':sha256(src),'sha256_destination':sha256(dst),'identical':sha256(src)==sha256(dst)})
  for name in ('Supplementary_Table_16_final_scripts.csv','Supplementary_Table_16_final_scripts.xlsx','Supplementary_Table_16_final_scripts.docx'):
    src=app/'tables'/name
    if src.exists():
      dst=art/'04_Supplementary_Tables'/name; copy(src,dst)
      rows.append({'kind':'table','source':str(src.relative_to(app)),'destination':str(dst.relative_to(art)),'sha256_source':sha256(src),'sha256_destination':sha256(dst),'identical':sha256(src)==sha256(dst)})
  frame=pd.DataFrame(rows)
  if frame.empty or not frame['identical'].all(): raise RuntimeError('Article/application synchronization failed')
  for root,path in [(app,app/'validation'/'article_app_target_sync.tsv'),(art,art/'07_Validation_and_Manifests'/'article_app_target_sync.tsv')]:
    path.parent.mkdir(parents=True,exist_ok=True); frame.to_csv(path,sep='\t',index=False)
  print(f'PASS: synchronized {len(frame)} target files with identical SHA-256 values.')
  return 0
if __name__=='__main__': raise SystemExit(main())
