from pathlib import Path
import datetime,hashlib,json
ROOT=Path(__file__).resolve().parent
OLD=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/CN-688012')
OUT=OLD/'v3'
OUT.mkdir(exist_ok=False)
paths=[OLD/n for n in ['input.json','forecast.json','forecast.md','snapshot_v2.json']]+[ROOT/'manifest.json']
record={'timestamp_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protected':[{'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in paths]}
(ROOT/'v3_protected_v2.json').write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(record,ensure_ascii=False))
