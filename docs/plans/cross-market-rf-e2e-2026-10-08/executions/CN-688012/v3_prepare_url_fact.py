from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parent
proofpath=ROOT.parents[1]/'reviews/CN-688012/official_pdf_current_sha_checks.json'
proof=json.loads(proofpath.read_text(encoding='utf-8'))
url='https://static.cninfo.com.cn/finalpage/2026-08-20/1225482884.PDF'
text=json.dumps(proof)
assert url in text and '182e2062fed950cd32310099cdf47f392c791440ce251f5e3bab7137dbc932fe' in text
prior=json.loads((ROOT/'requests/half2026_published_date_facts.json').read_text(encoding='utf-8'))
request=dict(source_ref=prior['source_ref'],facts={'source_url':url},evidence={'source_url':{'locator':'Independent actual official HTTP 200 application/pdf same-SHA transport GET; current immutable raw verified by reviewer and source-preparation verified-open','value':url,'observed_sha256':prior['source_ref']['content_sha256'],'official_receipt_path':str(proofpath),'official_receipt_sha256':hashlib.sha256(proofpath.read_bytes()).hexdigest(),'original_download_receipt_and_raw_preserved':True}})
(ROOT/'requests/v3_half_source_url_fact.json').write_text(json.dumps(request,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(request,ensure_ascii=False))
