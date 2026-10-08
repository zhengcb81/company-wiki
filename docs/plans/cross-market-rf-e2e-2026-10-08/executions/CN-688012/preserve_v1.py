from pathlib import Path
import hashlib,json,os,shutil
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
dest=OUT/'v1';dest.mkdir(exist_ok=True)
records=[]
for name in ['input.json','forecast.json','forecast.md','snapshot.json']:
 p=OUT/name;q=dest/name
 assert not q.exists(),'v1 preservation is write-once'
 shutil.copyfile(p,q)
 assert p.read_bytes()==q.read_bytes()
 records.append(dict(path=str(q),sha256=hashlib.sha256(q.read_bytes()).hexdigest()))
print(json.dumps(dict(preserved=records,original_snapshot_unchanged=str(OUT/'snapshot.json')),ensure_ascii=False))
