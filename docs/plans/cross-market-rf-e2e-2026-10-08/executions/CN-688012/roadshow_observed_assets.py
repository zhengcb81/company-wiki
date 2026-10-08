from pathlib import Path
import hashlib,json,os,time,urllib.request
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
# Actual pageAssets.list observed script URLs, no generated candidate URLs.
names=['9252.8f9ada5b80359fdc.chunk.js','3539.8c87283a5b464230.chunk.js','4811.7d3ee828b5dd6682.chunk.js','5994.05e109e0d3541aa9.chunk.js']
records=[];total=0
for name in names:
 url='https://roadshow.sseinfo.com/'+name
 with urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=15) as response:
  raw=response.read(2097153)
  assert len(raw)<=2097152
 total+=len(raw);assert total<=8388608
 dest=OUT/name;dest.write_bytes(raw)
 records.append(dict(url=url,path=str(dest),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
 text=raw.decode('utf-8')
 print(name,len(raw))
 for needle in ['/page_question_answer','/answer_question_page','getQuestionList','questionTypeList']:
  at=0
  while (at:=text.find(needle,at))>=0:
   print(text[max(0,at-300):at+400]);at+=len(needle)
(ROOT/'roadshow_observed_assets_receipt.json').write_text(json.dumps(dict(basis='actual cua pageAssets inventory9ef2eae4-17c7-4fde-8ced-f581cde4c627',assets=records,total_bytes=total,execution='read text only; no downloaded script executed'),ensure_ascii=False,indent=2),encoding='utf-8')
