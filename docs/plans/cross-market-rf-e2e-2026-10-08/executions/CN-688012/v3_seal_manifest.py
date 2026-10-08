"""Seal after the logged child returns, avoiding self-changing log hashes."""
from pathlib import Path
import datetime,hashlib,json
ROOT=Path(__file__).resolve().parent
OUT=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/CN-688012/v3')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
for p in read(ROOT/'v3_protected_v2.json')['protected']:assert sha(Path(p['path']))==p['sha256'] and Path(p['path']).stat().st_size==p['bytes']
receipt=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),action='final stable SHA inventory after run_logged finish; no child commands follow seal',reason='Bookkeeping is intentionally outside run_logged: logging seal itself would change index/stdout hashes after their inventory.',old_v2_byte_protection=True)
(ROOT/'manifest_seal_v3_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
manifest=read(ROOT/'manifest_v3_unsealed.json')
paths=set(p for p in OUT.rglob('*') if p.is_file())
paths.update(ROOT.glob('v3_*.py'));paths.update(ROOT.glob('*_v3.json'));paths.update(ROOT.glob('*_v3.md'))
paths.update([ROOT/'v3_input_repair_receipt.json',ROOT/'v3_protected_v2.json',ROOT/'commands/index.jsonl',ROOT/'events.jsonl'])
paths.update(p for p in (ROOT/'commands').glob('*v3-*') if p.is_file())
roles={'input.json':'formal_input','forecast.json':'formal_forecast','forecast.md':'formal_markdown','snapshot.json':'immutable_snapshot','publications.jsonl':'isolated_publication_registry'}
manifest['artifacts']=[dict(absolute_path=str(p),sha256=sha(p),bytes=p.stat().st_size,role=roles.get(p.name,'original_pdf' if p.suffix=='.pdf' else 'engineering_or_source_evidence')) for p in sorted(paths,key=str) if p.name not in ['manifest_v3.json','manifest_v3_unsealed.json']]
manifest['main_artifacts']={name:{'absolute_path':str(OUT/name),'sha256':sha(OUT/name),'bytes':(OUT/name).stat().st_size} for name in ['input.json','forecast.json','forecast.md','snapshot.json']}
manifest['seal_receipt_path']=str(ROOT/'manifest_seal_v3_receipt.json')
manifest['sealed_at']=receipt['timestamp_utc']
target=ROOT/'manifest_v3.json';target.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
for a in manifest['artifacts']:assert sha(Path(a['absolute_path']))==a['sha256']
print(json.dumps({'manifest_path':str(target),'manifest_sha256':sha(target),'artifacts':len(manifest['artifacts']),'main_artifacts':manifest['main_artifacts'],'old_v2_unchanged':True,'status':'PARTIAL; pending independent closure review'},ensure_ascii=False))
