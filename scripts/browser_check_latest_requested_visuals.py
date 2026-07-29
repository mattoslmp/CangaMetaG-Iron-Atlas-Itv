#!/usr/bin/env python3
from __future__ import annotations
import os,sys,types,json
from pathlib import Path
import pandas as pd
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT)); os.chdir(ROOT); os.environ['CANGAMETAG_DISABLE_NETWORK']='1'
from scripts.headless_navigation_test import FakeStreamlit,StopExecution
fake=FakeStreamlit(0); components=types.ModuleType('streamlit.components'); v1=types.ModuleType('streamlit.components.v1'); v1.html=lambda *a,**k:None; components.v1=v1; components.__path__=[];v1.__path__=[];fake.__path__=[];fake.components=components
sys.modules['streamlit']=fake;sys.modules['streamlit.components']=components;sys.modules['streamlit.components.v1']=v1
ns={'__name__':'__main__','__file__':str(ROOT/'app.py')}
try: exec(compile((ROOT/'app.py').read_text(),str(ROOT/'app.py'),'exec'),ns,ns)
except StopExecution: pass
captured=[]
def capture(fig,*a,**k): captured.append((str(k.get('basename') or k.get('key') or (a[0] if a else 'figure')),fig))
ns['render_plotly_downloadable']=capture
counts,_=ns['counts_table']('table8',ns['ST8_ALL_KO_SHEET'],['KO','Metabolism','KO description'])
ns['publication_boxplot_panel'](counts,['KO','Metabolism','KO description'],'Metabolism','KO biomarker boxplots by pathway, lake and sample','browser_ko',True,False)
iron,_=ns['counts_table']('table8',ns['ST8_IRON_ALL_SHEET'],['Function Id','Biologic Role','Function Name'])
ns['publication_boxplot_panel'](iron,['Function Id','Biologic Role','Function Name'],'Biologic Role','Iron KO marker boxplots by category, lake and season','browser_iron',True,True)
from src.functional_annotations import build_annotation_dataset,functional_annotation_heatmap,SOURCE_LABELS
for typ in ['KO','EC number','PFAM']:
  matrix,meta,id_col,name_col=build_annotation_dataset('table6',typ); cols=meta['matrix_column'].astype(str).tolist()
  fig,_,_=functional_annotation_heatmap(matrix,meta,id_col,name_col,cols,typ,SOURCE_LABELS['table6'],top_n=80,ranking_metric='Source table order',zscore_rows=False)
  captured.append((f'functional_{typ}',fig))
art=ROOT/'validation'/'latest_requested_visual_artifacts'; art.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as pw:
  browser=pw.chromium.launch(headless=True, executable_path='/usr/bin/chromium', args=['--no-sandbox'])
  page=browser.new_page(viewport={'width':1800,'height':1100},device_scale_factor=1)
  page.route('**/*',lambda route: route.abort() if route.request.url.startswith(('http://','https://')) else route.continue_())
  for idx,(name,fig) in enumerate(captured):
    safe=''.join(c if c.isalnum() else '_' for c in name)
    html=fig.to_html(full_html=True,include_plotlyjs='inline',config={'responsive':False,'displaylogo':False})
    path=art/f'{idx+1:02d}_{safe}.html'; path.write_text(html,encoding='utf-8')
    page.set_content(html, wait_until='load'); page.wait_for_selector('.plotly-graph-div'); page.wait_for_timeout(500)
    info=page.evaluate('''() => { const gd=document.querySelector('.plotly-graph-div'); const title=gd.querySelector('.gtitle'); const legend=gd.querySelector('.legend'); const tr=title?title.getBoundingClientRect():null; const lr=legend?legend.getBoundingClientRect():null; const overlap=!!(tr&&lr&&!(lr.right<tr.left||lr.left>tr.right||lr.bottom<tr.top||lr.top>tr.bottom)); return {title:(gd.layout.title&&gd.layout.title.text)||'',xTicks:gd.querySelectorAll('.xtick text').length,yTicks:gd.querySelectorAll('.ytick text').length,annotations:(gd.layout.annotations||[]).map(a=>String(a.text||'')),legendTitleOverlap:overlap,width:gd.getBoundingClientRect().width,height:gd.getBoundingClientRect().height}; }''')
    info.update({'name':name,'undefined':('undefined' in (info['title']+' '+ ' '.join(info['annotations'])).lower())})
    if name.startswith('functional_'): info['pass']=info['xTicks']>=20 and not info['undefined'] and info['width']>=1350
    else: info['pass']=not info['undefined'] and not info['legendTitleOverlap'] and bool(info['title'])
    page.screenshot(path=str(art/f'{idx+1:02d}_{safe}.png'),full_page=True)
    results.append(info)
  browser.close()
report=pd.DataFrame(results); report.to_csv(ROOT/'validation'/'LATEST_REQUESTED_VISUAL_BROWSER_VALIDATION.csv',index=False)
print(report.to_string(index=False))
if not report['pass'].all(): raise SystemExit(1)
print(f'PASS {len(report)}/{len(report)}')
