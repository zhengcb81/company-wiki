import json,subprocess,sys,os,hashlib
from pathlib import Path
from pypdf import PdfReader
HERE=Path(__file__).resolve().parent;EX=HERE.parents[1]/'executions/HK-00700'
m=json.loads((EX/'manifest.json').read_text(encoding='utf-8'));OUT=Path(m['output_root'])
TMP=OUT.parent/'review-HK-00700-rf_hk_independent_review';TMP.mkdir(exist_ok=True)
poppler=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/Library/bin/pdftoppm.exe'
annual=EX.parents[4]/'companies/腾讯/raw/financial_reports/annual'
targets=[('fy2024',annual/'腾讯：2024年年度报告.pdf',[1,188]),('fy2025',annual/'腾讯：2025年年度报告.pdf',[4,80,165,166,167,196]),('h1',OUT/'interim_2026_official.pdf',[6,10,47]),('corp',OUT/'corporate_overview_20260916.pdf',[12,15])]
records=[]
for name,p,pages in targets:
 reader=PdfReader(p)
 for page in pages:
  text=reader.pages[page-1].extract_text();prefix=TMP/(name+'-page-'+str(page))
  command=[str(poppler),'-f',str(page),'-l',str(page),'-singlefile','-scale-to','1600','-png',str(p),str(prefix)]
  r=subprocess.run(command,capture_output=True);assert r.returncode==0,r.stderr
  records.append(dict(document=name,source=str(p),page=page,reader='pypdf',text=text,render_command=command,render_path=str(prefix)+'.png',returncode=r.returncode))
(HERE/'pypdf_context_and_poppler_render_receipts.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps([{k:q[k] for k in ['document','page','render_path','returncode']} for q in records],ensure_ascii=False))
