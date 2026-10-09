"""Independent W06 RED reproduction: normal APIs, A labels + B raw/SEC URL.

Run with normal Python, explicit W06 code checkout, no provider/network keys:
  python -X utf8 -B qualification_shared_re_review_reproduce.py --code-root <CWP worktree>

Returns 1 when a wrong-company source was accepted. Creates/removes only one
owned TEMP catalog, originals and identity fixture. It does not edit a checkout,
production catalog/config/raw, original review receipts or installed skills.
The returned JSON contains complete API inputs and five observed entry results.
"""
from __future__ import annotations
import argparse, hashlib, json, os, pathlib, socket, sys, tempfile

HARNESS = "\nimport copy,hashlib,json,pathlib,shutil,sys,time\nfrom dataclasses import replace\nfrom unittest.mock import patch\nfrom helpers.source_fact_fixture import lake,html,evidence,imported,close\nfrom company_wiki.source_catalog.official_source_flow import import_official_source\nfrom company_wiki.source_catalog.source_reader import SourceRef,SourceVersionReader,SourceReadError\nfrom company_wiki.source_catalog.resolver import SourceRequest,SourceResolver\nfrom company_wiki.source_catalog.local_inventory import LocalReadBudget,LocalPrepareLimits\nfrom company_wiki.source_catalog.local_reconcile import prepare_local_source\nfrom company_wiki.source_catalog import assertion_service,dayu_fiscal_metadata\nfrom company_wiki.source_catalog.acquisition import AcquisitionCoordinator,AdapterRegistry,AcquisitionResult,AcquisitionStatus,DownloadCandidate\nfrom company_wiki.source_catalog.acquisition_service import SourceAcquisitionService\nfrom company_wiki.source_catalog.acquisition_journal import AcquisitionJournal\nfrom company_wiki.source_catalog.canonical_writer import CanonicalSourceWriter\nclass NoSupplier:\n name='offline';version='1'\n def discover(self,*a):raise AssertionError('no supplier allowed')\n def fetch(self,*a):raise AssertionError('no supplier allowed')\nreq=SourceRequest(entity='Acme',market='US',security_id='ACME',document_kind='annual_report',fiscal_year=2026,fiscal_period='FY',form_type='10-K',as_of_date='2026-10-09',mode='exact')\nbaseURL='https://www.sec.gov/Archives/edgar/data/{cik}/00000{cik}26{accession}/original.htm'\ncontrols=[]\ndef make_original(cat,data,url_cik='12345'):\n sha=hashlib.sha256(data).hexdigest()\n src={'entity':'Acme','market':'US','security_id':'ACME','document_kind':'annual_report','title':'independent fixture original','publisher':'Acme','source_url':baseURL.format(cik=url_cik,accession='000007'),'published_date':'2026-07-30','filing_date':'2026-07-30','fiscal_year':2026,'language':'en'}\n message={'schema_version':'official-source-import-request/1','request_id':'independent-source','source':src,'content_sha256':sha,'mime_type':'text/html','max_bytes':4096,'capture_receipt':{'capture_method':'local_document','tool_name':'independent-fixture','tool_call_id':'one','captured_at':'2026-10-09T00:00:00Z','content_sha256':sha,'response_bytes':len(data)}}\n result=import_official_source(cat,original=data,request=message)\n ref=SourceRef(**result['source_ref']); loc=cat.reader.exact_source_locations(ref.document_id,ref.source_id)[0]\n path=cat.config.roots[0].path/loc['relative_path']\n facts={'form_type':'10-K','fiscal_period':'FY','provider':'official','provider_document_id':'p-1'}\n cat.record_source_facts(ref=ref,facts=facts,evidence=evidence(ref,facts))\n return ref,path,message,result\n\ndef entry(cat,ref,name,empty,url_cik='12345'):\n r=SourceVersionReader(cat)\n if name=='open':return r.open_version(ref,purpose='filing_reuse')\n if name=='verify':return r.verify_version(ref,purpose='filing_reuse')\n if name=='resolver':return SourceResolver(cat).resolve(req)\n supplier=NoSupplier()\n coord=AcquisitionCoordinator(catalog=cat,adapters=AdapterRegistry(supplier,supplier,supplier),staging_root=cat.config.catalog_dir/'staging')\n service=SourceAcquisitionService(coordinator=coord,writer=CanonicalSourceWriter(cat),journal=AcquisitionJournal(cat.config.catalog_dir))\n if name=='ensure':return service.ensure(req)\n candidate=DownloadCandidate('c-1','official','p-1','US','Acme','annual',baseURL.format(cik=url_cik,accession='000007'),'annual_report','2026-07-30',2026,form_type='10-K',fiscal_period='FY')\n selection=AcquisitionResult('1.0',AcquisitionStatus.SELECTED,empty,candidate=candidate)\n return coord.stage_selected(replace(req,allow_download=True),selection)\n\ndef describe(result):\n if hasattr(result,'status'):return {'status':getattr(result.status,'value',result.status),'reason':getattr(result,'reason',None),'matches':len(getattr(result,'matches',()))}\n return {'returned_verified_bytes':hasattr(result,'data'),'returned_byte_size':getattr(result,'byte_size',None)}\n\nfor case in ['labels_A_raw_and_URL_B']:\n for name in ['open','verify','resolver','ensure','stage']:\n  folder=OWNED/(case+'-'+name);folder.mkdir();cat=lake(folder)\n  try:\n   empty=SourceResolver(cat).resolve(req)\n   data=html(cik='99999') if case.startswith('wrong_cik') else html(year=2022,end='2022-06-30') if case.startswith('wrong_FY') else html(cik='99999').replace(b'Acme actual original.',b'Other issuer B actual original.')\n   url_cik='99999' if case=='labels_A_raw_and_URL_B' else '12345'\n   ref,path,message,import_result=make_original(cat,data,url_cik)\n   row={'label':case+'-'+name,'entry':name,'source_import_request':message,'fixture_original_utf8':data.decode(),'request':req.__dict__,'import_status':import_result.get('status'),'query_status':SourceVersionReader(cat).query_local(req).status,'known_master_requested_CIK':'12345','actual_CIK':url_cik if case=='labels_A_raw_and_URL_B' else ('99999' if case.startswith('wrong_cik') else '12345')}\n   assertions=cat.reader.fetchone('SELECT COUNT(*) FROM source_metadata_assertions')[0]\n   try:\n    result=entry(cat,ref,name,empty,url_cik)\n    row.update(observed=describe(result),rejected=False,passed=False)\n   except SourceReadError as exc:\n    row.update(observed={'error_type':type(exc).__name__,'status':exc.status,'reason':exc.reason},rejected=True,passed=exc.status=='blocked' and exc.reason in {'primary_issuer_conflict','primary_scope_conflict'})\n   except Exception as exc:\n    row.update(observed={'unexpected_error_type':type(exc).__name__,'error':str(exc)},rejected=False,passed=False)\n   row['fixture_bytes_unchanged']=path.read_bytes()==data\n   row['assertions_unchanged']=cat.reader.fetchone('SELECT COUNT(*) FROM source_metadata_assertions')[0]==assertions\n   row['passed']=row['passed'] and row['fixture_bytes_unchanged'] and row['assertions_unchanged']\n   controls.append(row)\n  finally:close(cat)\n\nRESULT.write_text(json.dumps({'controls':controls,'passes':sum(x['passed'] for x in controls),'count':len(controls)},ensure_ascii=False,indent=2),encoding='utf-8')\n"

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--code-root',type=pathlib.Path,required=True)
    args=parser.parse_args()
    code=args.code_root.resolve(strict=True)
    sys.path[:0]=[str(code/'src'),str(code/'tests')]
    def no_external(event,values):
        if event in {'socket.connect','socket.getaddrinfo'}:
            raise RuntimeError('offline reproduction forbids network')
    sys.addaudithook(no_external)
    names={'SYSTEMROOT','WINDIR','PATH','PATHEXT','COMSPEC','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA','HOMEDRIVE','HOMEPATH'}
    # Run this script using the same documented minimal environment as review.
    # No environment values or credentials are emitted.
    with tempfile.TemporaryDirectory(prefix='w06-identity-five-',dir=str(pathlib.Path(os.environ['LOCALAPPDATA'])/'Temp')) as temp:
        owned=pathlib.Path(temp).resolve()
        controls=owned/'controls';controls.mkdir()
        result_path=owned/'results.json'
        namespace={'OWNED':controls,'RESULT':result_path}
        exec(compile(HARNESS,'<independent-w06-normal-api>','exec'),namespace)
        result=json.loads(result_path.read_text(encoding='utf-8'))
        result['fixture_kind']='synthetic normal source APIs; no query/DB mock'
        result['standard_sec_url']='https://www.sec.gov/Archives/edgar/data/99999/000009999926000007/original.htm'
        result['expected_requested_company_CIK']='12345'
        result['actual_raw_and_URL_CIK']='99999'
        result['owned_temp']=str(owned)
    result['owned_temp_absent']=not owned.exists()
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return int(result['passes']!=result['count'])

if __name__=='__main__':
    raise SystemExit(main())
