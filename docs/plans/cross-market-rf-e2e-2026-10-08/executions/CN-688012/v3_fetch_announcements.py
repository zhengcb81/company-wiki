"""Existing SID public transport API; this is auxiliary research, not FF ingestion."""
from pathlib import Path
import datetime,hashlib,json,sys,time
ROOT=Path(__file__).resolve().parent
OLD=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/CN-688012')
OUT=OLD/'v3'
sys.path.insert(0,'C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite')
from src.cninfo_api import CninfoAnnouncementClient
from src.acquisition_budget import ProviderAcquisitionBudget
import fitz
metadata=json.loads((OLD/'recent_cninfo_metadata.json').read_text(encoding='utf-8'))
client=CninfoAnnouncementClient()
ids=['1225582793','1225482911','1225482916','1225482918','1225482917','1225482894','1225482893','1225482882','1225482880']
receipts=[]
for aid in ids:
    raw=next(x for x in metadata['announcements'] if x['announcementId']==aid)
    assert raw['secCode']=='688012'
    announcement=client._parse_announcement(raw,stock_code='688012')
    budget=ProviderAcquisitionBudget(41943040,180,'0.00')
    start=time.monotonic()
    try:
        path=client.fetch_pdf(announcement.transport_url,OUT/'announcements',expected_filename=aid+'.pdf',budget=budget)
        pages=[dict(page=i+1,text=page.get_text()) for i,page in enumerate(fitz.open(path))]
        pagespath=OUT/'announcements'/(aid+'_pages.json')
        pagespath.write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
        r=dict(announcement_id=aid,title=raw['announcementTitle'],published_date=announcement.filing_date,source_url=announcement.transport_url,path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),bytes=path.stat().st_size,pages_path=str(pagespath),pages_sha256=hashlib.sha256(pagespath.read_bytes()).hexdigest(),page_count=len(pages),status='downloaded_and_fully_parsed',provider='existing SID CninfoAnnouncementClient.fetch_pdf',pipeline='auxiliary official research; not FF->CWP acquisition or ingestion',usage=budget.usage(),elapsed_seconds=time.monotonic()-start,timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    except Exception as e:
        r=dict(announcement_id=aid,title=raw['announcementTitle'],source_url=announcement.transport_url,status='not_available',error=repr(e),usage=budget.usage(),elapsed_seconds=time.monotonic()-start)
    receipts.append(r)
    (ROOT/'announcements_v3_receipts.json').write_text(json.dumps(receipts,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    print(json.dumps(r,ensure_ascii=False,default=str),flush=True)
assert all(r['status']=='downloaded_and_fully_parsed' for r in receipts), 'See retained truthful failure receipts'
