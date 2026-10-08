"""US task helpers: record real actions and keep all research in isolated TEMP."""
from pathlib import Path
import argparse,datetime,json,hashlib,os,subprocess,sys
LANE=Path(__file__).resolve().parent
RF=Path('C:/Users/郑曾波/.agents/skills/revenue-forecast')
CWP=Path('C:/Users/郑曾波/Projects/company-wiki')
OUTPUT=Path('C:/Users/郑曾波/AppData/Local/Temp/cwp-rf-e2e-20261008/US-MSFT')
def event(step,action,tool='python',**kwargs):
    row=dict(timestamp_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),agent_id='/root/rf_us_execution',step=step,action=action,tool=tool,**kwargs)
    with (LANE/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(row,ensure_ascii=False)+'\n')
def write(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def main():
    ap=argparse.ArgumentParser();ap.add_argument('action');ap.add_argument('arg',nargs='?');a=ap.parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    if a.action=='init':
        info=dict(output_root=str(OUTPUT),skill_root=str(RF),agent_id='/root/rf_us_execution',started_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),as_of_date='2026-10-08',registry=str(OUTPUT/'publications.jsonl'))
        write(LANE/'initial_context.json',info)
        for year in [2024,2025,2026]:
            req=dict(schema_version='2.0',company_query='MSFT',market='US',document_kind='annual_report',mode='exact',fiscal_year=year,as_of_date='2026-10-08',filing_intent='reuse_only')
            write(LANE/f'request_fy{year}_reuse.json',req)
        req=dict(schema_version='2.0',company_query='MSFT',market='US',document_kind='annual_report',mode='exact',fiscal_year=2026,as_of_date='2026-10-08',filing_intent='fetch_if_missing',acquisition_limits=dict(max_bytes=41943040,timeout_seconds=180,max_cost_usd='0.00'),companion_transcript=dict(intent='fetch_if_missing',fiscal_year=2026,fiscal_quarter=4,provider='fmp',acquisition_limits=dict(max_bytes=5242880,timeout_seconds=60,max_cost_usd='0.00')))
        write(LANE/'request_fy2026_fetch.json',req)
        hashes={}
        for rel in ['scripts/source_preparation.py','scripts/revenue_core.py','scripts/revenue_forecast.py','scripts/company_wiki_source_reader_v2.py','scripts/company_wiki_source_v2.py']:
            installed=RF/rel;repo=Path('C:/Users/郑曾波/Projects/revenue-forecast')/rel
            hashes[rel]=dict(installed_sha=hashlib.sha256(installed.read_bytes()).hexdigest(),repo_sha=hashlib.sha256(repo.read_bytes()).hexdigest(),same=installed.read_bytes()==repo.read_bytes())
        write(LANE/'runtime_hashes.json',hashes)
        event('1','initialize isolated output and requests',artifacts=[str(LANE/'initial_context.json'),str(LANE/'runtime_hashes.json')],outcome='complete')
        print(json.dumps(info))
    elif a.action=='prepare':
        req=LANE/a.arg
        cmd=[sys.executable,str(RF/'scripts/source_preparation.py'),'--request-file',str(req),'--company-wiki-catalog-config',str(CWP/'config/source_catalog.yaml'),'--timeout-seconds','180']
        if 'fetch' in req.name:cmd+=['--allow-download']
        env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUTF8='1',REVENUE_PUBLICATION_REGISTRY=str(OUTPUT/'publications.jsonl'),CWP_AUDIT_PROCESS_DIR=str(LANE/'processes'))
        env['PYTHONPATH']=str(LANE.parents[1]/'process_trace')+os.pathsep+env.get('PYTHONPATH','')
        et=Path('C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_tool.py')
        if et.exists():env['EARNINGS_TRANSCRIPTS_TOOL']=str(et)
        proc=subprocess.run(cmd,capture_output=True,env=env,timeout=240,cwd=RF)
        dest=LANE/(req.stem+'_response.json')
        dest.write_bytes(proc.stdout);(LANE/(req.stem+'_stderr.txt')).write_bytes(proc.stderr)
        event('3','actual source_preparation subprocess',input_summary=json.loads(req.read_text()),artifacts=[str(dest)],outcome='success' if proc.returncode==0 else 'failed',returncode=proc.returncode,env_names=['REVENUE_PUBLICATION_REGISTRY','EARNINGS_TRANSCRIPTS_TOOL'] if et.exists() else ['REVENUE_PUBLICATION_REGISTRY'])
        sys.stdout.buffer.write(proc.stdout);sys.stderr.buffer.write(proc.stderr);return proc.returncode
    elif a.action=='legacy-requests':
        for file in LANE.glob('request_*json'):
            if '_legacy' in file.stem or '_response' in file.stem:continue
            obj=json.loads(file.read_text());obj['schema_version']='1.2';obj.pop('filing_intent',None);obj.pop('companion_transcript',None)
            write(file.with_name(file.stem+'_legacy.json'),obj)
        event('3','RF documented schema 1.2 SourceRef request after schema 2.0 client incompatibility',outcome='requests_created')
    elif a.action=='raw-read':
        result=json.loads((LANE/'commands/1791442421321083400-ff-fy2025-inspect.stdout.txt').read_text())
        ref=result['filing']['source_ref']
        cmd=[sys.executable,'-B','-m','company_wiki.source_catalog.source_reader_cli','--config',str(CWP/'config/source_catalog.yaml'),'--document-id',ref['document_id'],'--source-id',ref['source_id'],'--content-sha256',ref['content_sha256'],'--purpose','filing_reuse']
        proc=subprocess.run(cmd,capture_output=True,timeout=40,cwd=CWP,env=dict(os.environ,PYTHONUTF8='1',PYTHONDONTWRITEBYTECODE='1'))
        (OUTPUT/'fy2025_verified_raw.html').write_bytes(proc.stdout)
        (LANE/'fy2025_source_read_receipt.json').write_bytes(proc.stderr)
        good=proc.returncode==0 and len(proc.stdout)==ref['byte_size'] and hashlib.sha256(proc.stdout).hexdigest()==ref['content_sha256']
        event('3','CWP producer verified binary raw read for diagnostics/processing',outcome='verified' if good else 'failed',artifacts=[str(LANE/'fy2025_source_read_receipt.json')],source_ref=ref)
        print(json.dumps(dict(returncode=proc.returncode,verified=good,bytes=len(proc.stdout),receipt_path=str(LANE/'fy2025_source_read_receipt.json'))))
        return 0 if good else 1
    elif a.action=='register-web':
        import re
        for f in OUTPUT.glob('web_*.json'):
            body=json.loads(f.read_text());urls=list(dict.fromkeys(re.findall(r'https://[^\\s)]+',body)))
            event('1A','retain actual web tool open/search response',tool='web.run',artifacts=[str(f)],source_urls=urls,outcome='captured_views_not_html',snapshot_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
        print('registered web captures')
    elif a.action=='aux-ir':
        import requests
        from bs4 import BeautifulSoup
        url='https://www.microsoft.com/en-us/investor/default'
        response=requests.get(url,timeout=30);response.raise_for_status()
        if len(response.content)>5242880:raise RuntimeError('ancillary web capture 5MiB ceiling')
        (OUTPUT/'official_ir_home.html').write_bytes(response.content)
        soup=BeautifulSoup(response.content,'html.parser')
        links=[dict(text=x.get_text(' ',strip=True),href=x.get('href')) for x in soup.find_all('a') if '2027' in str(x) or 'Segments' in str(x)]
        write(LANE/'official_presentation_links.json',dict(url=url,sha256=hashlib.sha256(response.content).hexdigest(),links=links))
        event('1A','retrieve opened official IR webpage to resolve ancillary presentation href; not a filing acquisition',tool='requests',source_url=url,artifacts=[str(OUTPUT/'official_ir_home.html'),str(LANE/'official_presentation_links.json')],outcome='complete',max_bytes=5242880)
        print(json.dumps(links))
    elif a.action=='aux-presentation':
        import requests,time
        from zipfile import ZipFile
        from xml.etree import ElementTree
        url='https://cdn-dynmedia-1.microsoft.com/is/content/microsoftcorp/FY27ExternalKPIs.pptx'
        started=__import__('time').monotonic()
        response=requests.get(url,timeout=(10,30),stream=True);response.raise_for_status()
        data=bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data)>5242880 or __import__('time').monotonic()-started>60:raise RuntimeError('ancillary presentation ceiling')
        dest=OUTPUT/'fy2027_segments_metrics.pptx'
        if dest.exists() and not dest.read_bytes().startswith(b'PK'):
            dest.rename(OUTPUT/'fy2027_failed_office_viewer.html')
        dest.write_bytes(data)
        if not bytes(data).startswith(b'PK'):raise RuntimeError('not OOXML presentation')
        with ZipFile(dest) as z:
            slides=[]
            for n in sorted((n for n in z.namelist() if n.startswith('ppt/slides/slide') and n.endswith('.xml')),key=lambda n:int(n.rsplit('slide',1)[1].split('.')[0])):
                node=ElementTree.fromstring(z.read(n));texts=[x.text or '' for x in node.iter() if x.tag.endswith('}t')];slides.append(dict(slide=n,text='\n'.join(texts)))
        write(OUTPUT/'fy2027_segments_metrics_text.json',slides)
        receipt=dict(request_url=url,final_url=response.url,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),elapsed_seconds=__import__('time').monotonic()-started,tool='requests',purpose='official ancillary presentation, not regulatory filing',published_date='2026-09-02',date_evidence='official IR homepage September 2 heading')
        write(LANE/'presentation_capture_receipt.json',receipt)
        event('1A','capture and parse official FY27 segment/metric investor presentation',tool='requests+OOXML',source_url=response.url,artifacts=[str(dest),str(OUTPUT/'fy2027_segments_metrics_text.json')],outcome='complete',byte_size=len(data))
        print(json.dumps(receipt))
    elif a.action=='parse-html':
        from bs4 import BeautifulSoup
        data=(OUTPUT/'fy2025_verified_raw.html').read_bytes()
        soup=BeautifulSoup(data,'html.parser')
        for node in soup(['script','style','ix:header']):node.decompose()
        text=soup.get_text('\n',strip=True)
        (OUTPUT/'fy2025_consumer_temporary_text.txt').write_text(text,encoding='utf-8')
        receipt=dict(parser='beautifulsoup4 html.parser',raw_sha256=hashlib.sha256(data).hexdigest(),output_bytes=len(text.encode()),cwp_canonical_narrative_processed=False,cwp_reason='production selective parser accepts PDF and transcript; this original is HTML',temporary_only=True)
        write(LANE/'html_temporary_parse_receipt.json',receipt)
        event('3','deterministic temporary HTML parsing of CWP verified raw; no canonical narrative artifact',outcome='complete_temporary_only',artifacts=[str(OUTPUT/'fy2025_consumer_temporary_text.txt')],**receipt)
        print(json.dumps(receipt))
    elif a.action=='capture-pages':
        import requests
        from bs4 import BeautifulSoup
        pages=[
          ('results','https://www.microsoft.com/en-us/Investor/earnings/FY-2026-Q4/press-release-webcast','2026-07-29'),
          ('call','https://www.microsoft.com/en-us/Investor/events/fy-2026/earnings-fy-2026-q4','2026-07-29'),
          ('metrics','https://www.microsoft.com/en-us/investor/earnings/FY-2026-Q4/metrics','2026-07-29'),
          ('strategy','https://blogs.microsoft.com/blog/2026/09/25/introducing-the-new-copilot-with-home-code-and-autopilot/','2026-09-25'),
          ('data_innovation','https://blogs.microsoft.com/blog/2026/09/28/new-microsoft-data-innovations-unlock-what-only-your-business-knows/','2026-09-28'),
          ('leadership','https://blogs.microsoft.com/blog/2026/10/01/microsoft-365-and-linkedin-leadership-update/','2026-10-01'),
          ('aws','https://ir.aboutamazon.com/news-release/news-release-details/2026/Amazon-com-Announces-Second-Quarter-Results/default.aspx','2026-07-30')]
        records=[]
        for ident,url,date in pages:
            began=datetime.datetime.now(datetime.timezone.utc).isoformat()
            r=requests.get(url,timeout=(8,25))
            if r.status_code != 200:
                event('1A','ancillary HTTP failed; retained successful web.run view is the evidence instead',tool='requests',source_url=url,outcome='http_failed',http_status=r.status_code)
                continue
            if len(r.content)>5242880:raise RuntimeError('ancillary webpage 5MiB cap')
            dest=OUTPUT/(ident+'.html');dest.write_bytes(r.content)
            soup=BeautifulSoup(r.content,'html.parser')
            for node in soup(['script','style']):node.decompose()
            text=soup.get_text('\n',strip=True);(OUTPUT/(ident+'.txt')).write_text(text,encoding='utf-8')
            row=dict(id=ident,url=url,published_date=date,captured_at=began,path=str(dest),sha256=hashlib.sha256(r.content).hexdigest(),byte_size=len(r.content),text_path=str(OUTPUT/(ident+'.txt')))
            records.append(row)
            write(OUTPUT/'ancillary_page_receipts.json',records)
            event('1A','retain ancillary official webpage already opened with web tool',tool='requests',source_url=url,artifacts=[str(dest),row['text_path']],outcome='complete',**{k:v for k,v in row.items() if k not in ['url','path','text_path']})
        write(OUTPUT/'ancillary_page_receipts.json',records)
        print(json.dumps(records))
    elif a.action in ['et-discover','et-probe']:
        req=dict(schema_version='earnings-transcript-request/1',request_id='msft-fy26q4-e2e-discover',ticker='MSFT',exchange='nasdaq',fiscal_year=2026,fiscal_quarter=4,as_of_date='2026-10-08',provider='fmp',download_authorized=True,timeout_seconds=45,max_body_bytes=5242880)
        env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUTF8='1',CWP_AUDIT_PROCESS_DIR=str(LANE/'processes'))
        env['PYTHONPATH']=str(LANE.parents[1]/'process_trace')+os.pathsep+env.get('PYTHONPATH','')
        if not env.get('FMP_API_KEY'):
            keyfile=Path('C:/Users/郑曾波/Projects/filing-fetch/config/FMP_API_KEY.txt')
            if keyfile.exists():env['FMP_API_KEY']=keyfile.read_text(encoding='utf-8-sig').strip()
        tool=Path('C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcript_tool.py')
        cmd=[sys.executable,str(tool),'--request-stdin','--operation','discover' if a.action=='et-discover' else 'fetch']
        proc=subprocess.run(cmd,input=json.dumps(req).encode(),capture_output=True,env=env,timeout=60,cwd=tool.parent)
        dest=LANE/('et_discover_response.json' if a.action=='et-discover' else 'et_standalone_probe_response.json')
        dest.write_bytes(proc.stdout);dest.with_suffix('.stderr.txt').write_bytes(proc.stderr)
        event('3','actual exact-period ET '+('discovery' if a.action=='et-discover' else 'standalone legacy fetch diagnostic, not production FF integration')+' under request scope; no translation or persistence; existing-key entitlement check',tool='earnings-transcripts transcript_tool.py',input_summary=req,artifacts=[str(dest)],outcome='boundary_returned' if proc.returncode==0 else 'failed',key_present=bool(env.get('FMP_API_KEY')),credential_source='inherited process environment or user-specified FF key file; value never logged')
        sys.stdout.buffer.write(proc.stdout);sys.stderr.buffer.write(proc.stderr);return proc.returncode
    elif a.action in ['forecast','snapshot','strong-check']:
        env=dict(os.environ,PYTHONIOENCODING='utf-8',PYTHONUTF8='1',REVENUE_PUBLICATION_REGISTRY=str(OUTPUT/'publications.jsonl'),CWP_AUDIT_PROCESS_DIR=str(LANE/'processes'))
        env['PYTHONPATH']=str(LANE.parents[1]/'process_trace')+os.pathsep+str(RF/'scripts')+os.pathsep+env.get('PYTHONPATH','')
        if a.action=='forecast':cmd=[sys.executable,str(RF/'scripts/revenue_forecast.py'),str(OUTPUT/'input.json'),'--output',str(OUTPUT/'forecast.json'),'--markdown',str(OUTPUT/'forecast.md')]
        elif a.action=='snapshot':cmd=[sys.executable,str(RF/'scripts/revenue_backtest.py'),'create',str(OUTPUT/'input.json'),'--version','2026-10-08-MSFT-v1','--output',str(OUTPUT/'snapshot.json')]
        else:cmd=[sys.executable,str(LANE/'validate_msft.py')]
        proc=subprocess.run(cmd,capture_output=True,env=env,timeout=75,cwd=RF)
        (LANE/(a.action+'_stdout.txt')).write_bytes(proc.stdout);(LANE/(a.action+'_stderr.txt')).write_bytes(proc.stderr)
        event('10' if a.action!='snapshot' else '11','actual RF '+a.action+' using isolated publication registry',tool='revenue-forecast',outcome='success' if proc.returncode==0 else 'failed',returncode=proc.returncode,registry=str(OUTPUT/'publications.jsonl'),artifacts=[str(LANE/(a.action+'_stdout.txt')),str(LANE/(a.action+'_stderr.txt'))])
        sys.stdout.buffer.write(proc.stdout);sys.stderr.buffer.write(proc.stderr);return proc.returncode
    elif a.action=='event':event('audit',a.arg,outcome='recorded')
    return 0
if __name__=='__main__':sys.exit(main())
