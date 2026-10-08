from pathlib import Path
import datetime,hashlib,json
ROOT=Path(__file__).resolve().parent
ref=json.loads((ROOT/'half2026_raw_receipt.json').read_text(encoding='utf-8'))['source_ref']
response=ROOT/'category_bndbg_szsh_official_response.json'
d=json.loads(response.read_text(encoding='utf-8'))
rows=[x for x in d['announcements'] if str(x['announcementId'])=='1225482884']
assert len(rows)==1
row=rows[0]; epoch=row['announcementTime']; assert epoch==1787155200000
stamp=datetime.datetime.fromtimestamp(epoch/1000,datetime.timezone(datetime.timedelta(hours=8)))
assert stamp.date().isoformat()=='2026-08-20'
proof=dict(locator='Official CNINFO JSON announcements[announcementId=1225482884].announcementTime; epoch interpreted UTC+08 China civil publication date',value='2026-08-20',observed_sha256=ref['content_sha256'],official_response_path=str(response),official_response_sha256=hashlib.sha256(response.read_bytes()).hexdigest(),announcementTime=epoch,china_timestamp=stamp.isoformat(),original_download_receipt_preserved=True)
payload=dict(source_ref=ref,facts={'published_date':'2026-08-20'},evidence={'published_date':proof})
dest=ROOT/'requests'/'half2026_published_date_facts.json';dest.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(request_path=str(dest),proof=proof),ensure_ascii=False))
