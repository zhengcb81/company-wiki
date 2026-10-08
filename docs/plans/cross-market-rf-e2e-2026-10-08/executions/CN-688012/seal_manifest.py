"""Final stable hash inventory after run_logged has closed its own outputs.

This bookkeeping seal intentionally is not nested in run_logged: doing so
would modify the command index/stdout after hashing those same artifacts.
"""
from pathlib import Path
import datetime,hashlib,json,os
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
manifest=json.loads((ROOT/'manifest.json').read_text(encoding='utf-8'))
now=datetime.datetime.now(datetime.timezone.utc).isoformat()
receipt=dict(timestamp_utc=now,action='seal stable artifact inventory after all logged child commands returned',command='python '+str(Path(__file__).resolve()),reason='Avoid recursive mutation of command-index/stdout hashes by a logger wrapping its own inventory seal',formal_artifacts_unchanged=True)
(ROOT/'manifest_seal_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
artifacts=[]
for base,role in [(ROOT,'engineering_execution_record'),(OUT,'isolated_research_or_test_evidence')]:
 for p in sorted(base.rglob('*')):
  if not p.is_file() or p.name=='manifest.json' or '__pycache__' in p.parts:continue
  artifacts.append(dict(absolute_path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,role='formal_research' if p.parent==OUT and p.name in {'input.json','forecast.json','forecast.md','snapshot_v2.json'} else role))
manifest['artifacts']=artifacts;manifest['ended_at']=now;manifest['seal_receipt']=str(ROOT/'manifest_seal_receipt.json')
finished=[json.loads(x) for x in (ROOT/'commands'/'index.jsonl').read_text(encoding='utf-8').splitlines() if x.strip() and json.loads(x)['event']=='finish']
manifest['calls_and_cost']['logged_commands']=len(finished)
manifest['calls_and_cost']['failed_attempts']=sum(1 for x in finished if x['returncode']!=0)
(ROOT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
for row in artifacts:
 p=Path(row['absolute_path']);assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256']
print(json.dumps(dict(status='sealed',manifest=str(ROOT/'manifest.json'),sha256=hashlib.sha256((ROOT/'manifest.json').read_bytes()).hexdigest(),artifacts=len(artifacts),commands=len(finished),failures=manifest['calls_and_cost']['failed_attempts']),ensure_ascii=False))
