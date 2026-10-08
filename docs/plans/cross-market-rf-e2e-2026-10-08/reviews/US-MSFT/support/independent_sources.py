import sys,os,json,hashlib,subprocess,zipfile,re,time
from pathlib import Path
from bs4 import BeautifulSoup
HERE=Path(__file__).resolve().parent
EX=HERE.parents[2]/'executions'/'US-MSFT'
ORIG=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/US-MSFT')
ROOT=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-review-20261008-US-MSFT-independent')
CWP=Path('C:/Users/郑曾波/Projects/company-wiki');RF=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast')
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(data):return hashlib.sha256(data).hexdigest()
def save(name,d): (HERE/name).write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
ROOT.mkdir(parents=True,exist_ok=True)
if sys.argv[1]=='producer':
    response=read(EX/'request_fy2025_reuse_response.json');ref=response['company_wiki_trace']['source_ref']
    cmd=[sys.executable,'-B','-m','company_wiki.source_catalog.source_reader_cli','--config',str(CWP/'config/source_catalog.yaml'),'--document-id',ref['document_id'],'--source-id',ref['source_id'],'--content-sha256',ref['content_sha256'],'--purpose','filing_reuse']
    proc=subprocess.run(cmd,cwd=CWP,capture_output=True,timeout=45,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
    (ROOT/'producer_fy2025.html').write_bytes(proc.stdout)
    receipt=json.loads(proc.stderr);assert proc.returncode==0 and sha(proc.stdout)==ref['content_sha256'] and len(proc.stdout)==ref['byte_size']
    save('independent_producer_read.json',dict(command=cmd,returncode=proc.returncode,sha256=sha(proc.stdout),bytes=len(proc.stdout),receipt=receipt,expected_ref=ref))
    req=read(EX/'request_fy2025_reuse.json');(ROOT/'request_fy2025_reuse.json').write_text(json.dumps(req),encoding='utf-8')
    cmd2=[sys.executable,'-B',str(RF/'scripts/source_preparation.py'),'--request-file',str(ROOT/'request_fy2025_reuse.json'),'--company-wiki-catalog-config',str(CWP/'config/source_catalog.yaml'),'--timeout-seconds','45']
    p2=subprocess.run(cmd2,cwd=RF,capture_output=True,timeout=60,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
    assert p2.returncode==0,p2.stderr.decode();r2=json.loads(p2.stdout)
    assert r2['company_wiki_trace']['source_manifest']['retrieved_at'] is None
    assert r2['reuse_receipt']['download_calls']==0 and r2['source_id']==ref['source_id']
    (ROOT/'independent_sourceprep_response.json').write_bytes(p2.stdout)
    save('independent_sourceprep.json',dict(command=cmd2,returncode=p2.returncode,response=r2))
    soup=BeautifulSoup(proc.stdout,'html.parser')
    for x in soup(['script','style','ix:header']):x.decompose()
    text=soup.get_text(' ',strip=True);(ROOT/'producer_fy2025.txt').write_text(text,encoding='utf-8')
    queries=['Revenue Recognition','Revenue related to cloud services provided on a consumption basis','recognized ratably over the contract period','recognized as services are provided','Principal versus Agent','245,122','281,724']
    contexts=[]
    for q in queries:
        matches=[m.start() for m in re.finditer(re.escape(q),text,re.I)]
        contexts.append(dict(query=q,contexts=[text[max(0,i-300):i+2200] for i in matches[-3:]],occurrences=len(matches)))
    save('independent_fy25_contexts.json',contexts)
    print(json.dumps(dict(raw_sha256=sha(proc.stdout),bytes=len(proc.stdout),reuse_downloads=r2['reuse_receipt']['download_calls'],unknown_retrieved_at_preserved=True,contexts=contexts),ensure_ascii=False))
elif sys.argv[1]=='network':
    import requests
    urls={'presentation':'https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/FY27ExternalKPIs.pptx','results':'https://www.microsoft.com/en-us/Investor/earnings/FY-2026-Q4/press-release-webcast','call':'https://www.microsoft.com/en-us/Investor/events/fy-2026/earnings-fy-2026-q4','metrics':'https://www.microsoft.com/en-us/investor/earnings/FY-2026-Q4/metrics','aws':'https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Second-Quarter-Results/default.aspx'}
    receipts=[]
    for ident,url in urls.items():
        started=time.monotonic();r=requests.get(url,stream=True,timeout=(10,20));r.raise_for_status();raw=bytearray()
        for chunk in r.iter_content(65536):
            raw.extend(chunk)
            if len(raw)>5242880 or time.monotonic()-started>60:raise RuntimeError('review capture ceiling')
        raw=bytes(raw);dest=ROOT/(ident+('.pptx' if ident=='presentation' else '.html'));dest.write_bytes(raw)
        original=ORIG/('fy2027_segments_metrics.pptx' if ident=='presentation' else ident+'.html')
        receipts.append(dict(id=ident,url=url,final_url=r.url,sha256=sha(raw),bytes=len(raw),matches_execution=sha(raw)==sha(original.read_bytes()),elapsed=time.monotonic()-started))
        if ident!='presentation':
            soup=BeautifulSoup(raw,'html.parser')
            for x in soup(['script','style']):x.decompose()
            (ROOT/(ident+'.txt')).write_text(soup.get_text(' ',strip=True),encoding='utf-8')
        else:
            with zipfile.ZipFile(dest) as z:
                assert len([n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)])==22
                images=[]
                for n in range(1,23):
                    im=z.read('ppt/media/image'+str(n)+'.png');existing=(ORIG/'ppt_images'/('image'+str(n)+'.png')).read_bytes()
                    assert im==existing;images.append(dict(slide=n,sha256=sha(im),bytes=len(im),matches_visual_original=True))
                save('independent_ppt_image_integrity.json',images)
    save('independent_network_receipts.json',receipts);print(json.dumps(receipts,ensure_ascii=False))
