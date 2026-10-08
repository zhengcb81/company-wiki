"""Freeze old delivery; render actual FY2025 original before append-only observation repair."""
from pathlib import Path
import json, hashlib, datetime as dt, os
HERE=Path(__file__).resolve().parent
OLD=Path(json.loads((HERE/'before.json').read_text(encoding='utf-8'))['output_root'])
OUT=OLD/'v3'
def item(p): return {'path':str(p.resolve()),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
assert not (HERE/'before_v3.json').exists(), 'Never overwrite the repair baseline'
old_temp=[item(p) for p in OLD.rglob('*') if p.is_file() and 'v3' not in p.relative_to(OLD).parts]
old_engineering=[item(p) for p in HERE.iterdir() if p.is_file() and not p.name.startswith(('v3_','repair_v3','manifest_v3','before_v3','after_v3')) and p.name!='events.jsonl']
original=json.loads((HERE/'before.json').read_text(encoding='utf-8'))
protected=[item(Path(x['path'])) for x in original['protected'] if '/skills/revenue-forecast/scripts/' not in x['path'].replace('\\','/')]
baseline={'timestamp_utc':dt.datetime.now(dt.timezone.utc).isoformat(),'old_output_root':str(OLD),'v3_output_root':str(OUT),'old_temp_artifacts':old_temp,'old_engineering_artifacts':old_engineering,'raw_and_config_baseline':protected,'allowed_append_only':['events.jsonl','commands/index.jsonl','processes/*','CWP source-facts assertion via public producer CLI'],'runtime_owner':'MAIN; no runtime writes by HK executor'}
(HERE/'before_v3.json').write_text(json.dumps(baseline,ensure_ascii=False,indent=2),encoding='utf-8')
OUT.mkdir(exist_ok=False)
import fitz
raw=Path('C:/Users/郑曾波/Projects/company-wiki/companies/腾讯/raw/financial_reports/annual/腾讯：2025年年度报告.pdf')
assert hashlib.sha256(raw.read_bytes()).hexdigest()=='d19f183452e9b8d0c47bcb7543dcbf435b585b2610759b42c0cba7c13f7361c7'
doc=fitz.open(raw)
renders=[]
for n in (1,4):
 p=OUT/f'FY2025_page_{n}_visual.png';doc[n-1].get_pixmap(matrix=fitz.Matrix(1.4,1.4)).save(p);renders.append(item(p))
print(json.dumps({'old_temp_frozen':len(old_temp),'old_engineering_frozen':len(old_engineering),'protected':len(protected),'renders':renders},ensure_ascii=False))
