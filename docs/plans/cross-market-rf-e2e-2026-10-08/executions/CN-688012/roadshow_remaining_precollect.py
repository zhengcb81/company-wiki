from pathlib import Path
import datetime,hashlib,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
first=json.loads((OUT/'roadshow_precollect_questions_page1.json').read_text(encoding='utf-8'))
assert first['success'];dataset=first['datas'][0]
pages=dataset['pages']; assert pages==10 and dataset['total']==29
records=dataset['records'][:];artifacts=[];start=time.monotonic()
for page in range(2,pages+1):
 assert time.monotonic()-start<90,'90 second cumulative limit'
 subprocess.run([sys.executable,str(ROOT/'roadshow_public_questions.py'),'precollect',str(page)],check=True,timeout=min(30,90-(time.monotonic()-start)))
 p=OUT/f'roadshow_precollect_questions_page{page}.json'
 result=json.loads(p.read_text(encoding='utf-8'));assert result['success']
 records+=result['datas'][0]['records']
 artifacts.append(dict(path=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
assert len(records)==dataset['total']==29
cn=[x for x in records if any('中微' in str(v) or '688012' in str(v) for v in x.values())]
receipt=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),total=len(records),pages=pages,cn_mentions=cn,artifacts=artifacts,coverage='all 29 pre-collected responses read; per-company affiliation still checked independently',credentials_used=False,cost_usd=0)
(ROOT/'roadshow_precollect_complete_receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
print('COMPLETE '+json.dumps(receipt,ensure_ascii=False))
