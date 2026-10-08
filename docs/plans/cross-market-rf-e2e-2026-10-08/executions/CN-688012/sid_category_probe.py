"""Read-only official JSON category comparison, never a replacement acquisition."""
from pathlib import Path
import json, sys
from urllib.parse import parse_qs,urlencode
ROOT=Path(__file__).resolve().parent
SID=Path('C:/Users/郑曾波/Projects/StockInfoDLSimple/v2-clean-rewrite')
sys.path.insert(0,str(SID))
from src.cninfo_api import CninfoAnnouncementClient
from src.cninfo_identity import OrgIdIdentityResolver
from src.acquisition_budget import ProviderAcquisitionBudget
budget=ProviderAcquisitionBudget(41943040,180,'0.00')
client=CninfoAnnouncementClient()
org=OrgIdIdentityResolver(client=client).resolve_org_id('688012',budget=budget)
body=client._build_request_body(stock_code='688012',org_id=org,document_kind='semi_annual_report',fiscal_year=2026,page_num=1,page_size=30)
base={k:v[0] for k,v in parse_qs(body.decode()).items()}
rows=[]
for category in (sys.argv[1:] or ['category_ndbg_szsh','category_bndbg_szsh']):
    params=dict(base,category=category)
    response=client._post_json(urlencode(params).encode(),budget=budget)
    file=ROOT/(category+'_official_response.json'); file.write_text(json.dumps(response,ensure_ascii=False,indent=2),encoding='utf-8')
    rows.append(dict(request=params,response_path=str(file),total=response.get('totalAnnouncement'),announcements=[{k:x.get(k) for k in ['announcementId','announcementTitle','announcementTime','adjunctUrl','secCode']} for x in (response.get('announcements') or [])]))
print(json.dumps(dict(org_id=org,comparisons=rows,acquisition_usage=budget.usage()),ensure_ascii=False,indent=2))
