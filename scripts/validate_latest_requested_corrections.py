#!/usr/bin/env python3
from __future__ import annotations
import os, sys, types, re
from pathlib import Path
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT)); os.chdir(ROOT); os.environ.setdefault('CANGAMETAG_DISABLE_NETWORK','1')
from scripts.headless_navigation_test import FakeStreamlit, StopExecution
fake=FakeStreamlit(0)
components=types.ModuleType('streamlit.components'); components_v1=types.ModuleType('streamlit.components.v1')
components_v1.html=lambda *a,**k: None; components.v1=components_v1; components.__path__=[]; components_v1.__path__=[]; fake.__path__=[]; fake.components=components
sys.modules['streamlit']=fake; sys.modules['streamlit.components']=components; sys.modules['streamlit.components.v1']=components_v1
ns={'__name__':'__main__','__file__':str(ROOT/'app.py')}
try:
  exec(compile((ROOT/'app.py').read_text(encoding='utf-8'),str(ROOT/'app.py'),'exec'),ns,ns)
except StopExecution:
  pass

checks=[]
def check(name, condition, detail=''):
  checks.append({'check':name,'status':'PASS' if condition else 'FAIL','detail':detail})
  if not condition: raise AssertionError(f'{name}: {detail}')

text=(ROOT/'app.py').read_text(encoding='utf-8')
for person in ['Leandro de Mattos Pereira','José Augusto Pires Bittencourt','Vitor Cirilo Araujo Santos','Ronnie Alves','Eder Pires','Prafulla Kumar Sahoo','José Tasso Felix Guimarães','Bruno Garcia Simões','Renato R. Moreira-Oliveira','Guilherme Oliveira','Gisele Lopes Nunes']:
  check('author_'+person, person in text)
check('affiliation', 'Instituto Tecnológico Vale, Belém, PA, Brazil' in text)
check('correspondence', 'gisele.nunes@itv.org' in text and 'leandro.pereira@pq.itv.org' in text)
check('abstract', 'A curated Kyoto Encyclopedia of Genes and Genomes orthology framework detected 171 of 195 biogeochemical markers' in text)
check('english_module_name', 'KO Biogeochemical Cycles Biomarkers' in text)
check('no_undefined_title_literal', 'title="undefined"' not in text.lower())
check('audit_expander', 'def render_figure_audit_expander' in text)
check('legacy_not_in_ui_roots', 'for folder in [BASE_DIR / "scripts", BASE_DIR / "src", BASE_DIR / "docs" / "code", BASE_DIR / "legacy_scripts"]' not in text)

from src.functional_annotations import build_annotation_dataset, functional_annotation_heatmap, SOURCE_LABELS
expected_samples=['AM.P1.D','AM.P1.R','AM.P2.D','AM.P2.R','TIA.P1.D','TIA.P1.R','TIA.P2.D','TIA.P2.R','TI.P1.D','TI.P1.R','TI.P2.D','TI.P2.R','TI.P3.D','TI.P3.R','TI.P4.D','TI.P4.R','VI.P1.D','VI.P1.R','VI.P2.D','VI.P2.R']
for typ in ['KO','EC number','PFAM']:
  matrix,meta,id_col,name_col=build_annotation_dataset('table6',typ)
  cols=meta['matrix_column'].astype(str).tolist()
  fig,raw,z=functional_annotation_heatmap(matrix,meta,id_col,name_col,cols,typ,SOURCE_LABELS['table6'],top_n=min(100,len(matrix)),ranking_metric='Source table order',zscore_rows=False)
  x=[str(v) for v in fig.data[0].x]
  check(f'{typ}_20_samples', x==expected_samples, str(x))
  zarr=np.asarray(fig.data[0].z,float)
  expected=raw[cols].to_numpy(float)
  check(f'{typ}_exact_values', np.allclose(zarr,expected,equal_nan=True), f'shape={zarr.shape}')

# Independent boxplot aggregation checks.
counts,numeric_cols=ns['counts_table']('table8',ns['ST8_ALL_KO_SHEET'],['KO','Metabolism','KO description'])
lake_cols=[c for c in numeric_cols if ns['_is_article_lake_sample_column'](c)]
long=ns['_long_marker_counts_for_boxplot'](counts,['KO','Metabolism','KO description'],'Metabolism',normalize_per_sample=True)
check('KO_boxplot_unique_units', not long.duplicated(['Metabolism','sample']).any(), f'rows={len(long)}')
work=counts.copy(); work[lake_cols]=work[lake_cols].apply(pd.to_numeric,errors='coerce').fillna(0).clip(lower=0)
totals=work[lake_cols].sum(axis=0).replace(0,np.nan); work[lake_cols]=work[lake_cols].divide(totals,axis=1).fillna(0)*10000
work['Metabolism']=work['Metabolism'].fillna('Unclassified').astype(str).str.strip()
work.loc[work['Metabolism'].str.casefold().isin({'','undefined','nan','none','null','na','n/a'}),'Metabolism']='Unclassified'
exp=work.groupby('Metabolism',dropna=False)[lake_cols].sum().reset_index().melt(id_vars='Metabolism',var_name='sample',value_name='expected')
merged=long.merge(exp,on=['Metabolism','sample'],how='left')
check('KO_boxplot_exact_aggregation',np.allclose(merged['normalized_count'],merged['expected'],equal_nan=True),f'rows={len(merged)}')

iron,_=ns['counts_table']('table8',ns['ST8_IRON_ALL_SHEET'],['Function Id','Biologic Role','Function Name'])
long_i=ns['_long_marker_counts_for_boxplot'](iron,['Function Id','Biologic Role','Function Name'],'Biologic Role',normalize_per_sample=True)
check('iron_boxplot_unique_units',not long_i.duplicated(['Biologic Role','sample']).any(),f'rows={len(long_i)}')
check('boxplot_titles_present','KO biomarker boxplots by pathway, lake and sample' in text and 'Iron KO marker boxplots by category, lake and season' in text)
check('legend_position_preserved','preserve_legend_position' in text and 'Dry season' in text and 'Rainy season' in text)

out=pd.DataFrame(checks)
validation_dir=ROOT/'validation'; validation_dir.mkdir(exist_ok=True)
out.to_csv(validation_dir/'LATEST_REQUESTED_CORRECTIONS_VALIDATION.csv',index=False)
(validation_dir/'LATEST_REQUESTED_CORRECTIONS_VALIDATION.md').write_text('# Latest requested corrections validation\n\n'+f'Passed: {(out.status=="PASS").sum()}/{len(out)}\n\n'+out.to_markdown(index=False)+'\n',encoding='utf-8')
print(out.to_string(index=False)); print(f'PASS {len(out)}/{len(out)}')
