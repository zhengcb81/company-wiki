"""Bounded official post-H1 metadata read, not a replacement download path."""
from pathlib import Path
import datetime,hashlib,json,os,sys
from urllib.parse import parse_qs,urlencode
ROOT=Path(__file__).resolve().parent
OUT=Path(os.environ['TEMP'])/'cwp-rf-e2e-20261008'/'CN-688012'
SID=Path('C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite')
sys.path.insert(0,str(SID))
from src.cninfo_api import CninfoAnnouncementClient
from src.cninfo_identity import OrgIdIdentityResolver
from src.acquisition_budget import ProviderAcquisitionBudget
budget=ProviderAcquisitionBudget(4194304,90,'0.00')
client=CninfoAnnouncementClient()
org=OrgIdIdentityResolver(client=client).resolve_org_id('688012',budget=budget)
body=client._build_request_body(stock_code='688012',org_id=org,document_kind='semi_annual_report',fiscal_year=2026,page_num=1,page_size=100)
params={k:v[0] for k,v in parse_qs(body.decode()).items()}
params.update(category='',seDate='2026-08-20~2026-10-08',pageSize='100')
response=client._post_json(urlencode(params).encode(),budget=budget)
dest=OUT/'recent_cninfo_metadata.json';dest.write_text(json.dumps(response,ensure_ascii=False,indent=2),encoding='utf-8')
records=response.get('announcements') or []
summary=dict(query=params,total=response.get('totalAnnouncement'),returned=len(records),as_of='2026-10-08',capture_time=datetime.datetime.now(datetime.timezone.utc).isoformat(),path=str(dest),sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),usage=budget.usage(),completeness='all returned if returned equals total; metadata only, not full-document verification',announcements=[{k:x.get(k) for k in ['announcementId','announcementTitle','announcementTime','adjunctUrl','secCode']} for x in records])
(ROOT/'recent_announcements_receipt.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False,indent=2))
