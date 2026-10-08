"""Task-local evidence freeze and reference reading; never a production writer."""
from pathlib import Path
import hashlib, json, os, datetime, sys

HERE = Path(__file__).resolve().parent
WIKI = HERE.parents[4]
SKILL = Path.home()/'.agents/skills/revenue-forecast'
OUT = Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008/HK-00700'
OUT.mkdir(parents=True, exist_ok=True)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
paths = [WIKI/'config/source_catalog.yaml', SKILL/'config/company_wiki.json']
paths += list((WIKI/'companies/腾讯').rglob('*.pdf'))
runtime=['scripts/source_preparation.py','scripts/revenue_forecast.py','scripts/revenue_core.py','scripts/revenue_report.py','scripts/revenue_backtest.py','SKILL.md']
paths += [SKILL/p for p in runtime]
before = {'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(), 'output_root':str(OUT),'protected':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths if p.is_file()], 'runtime_comparison':[]}
repo=Path.home()/'Projects/revenue-forecast'
for f in runtime:
    a,b=SKILL/f,repo/f
    before['runtime_comparison'].append({'file':f,'installed_sha':sha(a) if a.exists() else None,'repo_sha':sha(b) if b.exists() else None,'same': a.exists() and b.exists() and sha(a)==sha(b)})
(HERE/'before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
req={'schema_version':'2.0','company_query':'00700','market':'HK','document_kind':'annual_report','mode':'exact','fiscal_year':2025,'as_of_date':'2026-10-08','filing_intent':'reuse_only','language':'zh','companion_transcript':{'intent':'reuse_only','fiscal_year':2025,'fiscal_quarter':4}}
(HERE/'request_annual_2025.json').write_text(json.dumps(req,ensure_ascii=False,indent=2),encoding='utf-8')
for y in [2024]:
    r=dict(req,fiscal_year=y);r.pop('companion_transcript',None)
    (HERE/f'request_annual_{y}.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
r=dict(req,document_kind='semi_annual_report',fiscal_year=2026,fiscal_period='H1',filing_intent='fetch_if_missing', acquisition_limits={'max_bytes':41943040,'timeout_seconds':180,'max_cost_usd':'0.00'}, companion_transcript={'intent':'reuse_only','fiscal_year':2026,'fiscal_quarter':2})
(HERE/'request_interim_2026.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
refs=['research-coverage','buy-side-methodology','industry-lifecycle-routing','growth-driver-tree','management-targets','accounting-boundaries','model-library','input-schema','output-schema','backtesting']
if sys.argv[-1]=='refs':
    for name in refs:
        print('\n# REF',name);print((SKILL/'references'/f'{name}.md').read_text(encoding='utf-8'))
else:
    print(json.dumps({'before':str(HERE/'before.json'),'output_root':str(OUT),'protected_count':len(before['protected']),'runtime_comparison':before['runtime_comparison']},ensure_ascii=False))
