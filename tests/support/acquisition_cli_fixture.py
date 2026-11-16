"""Local bounded provider and isolated catalog config for CLI integration tests."""

from __future__ import annotations

import json
from pathlib import Path
import sys


RAW_BODY = b"Fixture original annual report. The company provides devices and services.\n"


PROVIDER = r'''
import argparse, hashlib, json, sys, time
from pathlib import Path
p=argparse.ArgumentParser()
p.add_argument('mode');p.add_argument('log');p.add_argument('action');p.add_argument('--staging-dir')
a=p.parse_args()
request=json.loads(sys.stdin.read())
log=Path(a.log)
entries=log.read_text().splitlines() if log.exists() else []
with log.open('a',encoding='utf-8') as f:f.write(a.action+'\n')
identity={'name':'proof-cli','version':'1.0.0'}
def usage(n,c='0.01'):return {'schema_version':'1.0','response_bytes':n,'cost_usd':c}
def fail(n,c='0.01'):
 sys.stderr.write(json.dumps({'schema_version':'1.0','status':'failed','adapter':identity,
  'error':{'code':'upstream_unavailable','retryable':True,'message':'never-copy-secret?api_key=bad','acquisition_usage':usage(n,c)}})+'\n')
 raise SystemExit(1)
def progress(n):
 sys.stderr.write(json.dumps({'schema_version':'1.0','status':'progress','adapter':identity,'acquisition_usage':usage(n,'0.02')})+'\n');sys.stderr.flush()
if a.mode=='discover-fail':fail(17)
if a.action=='discover':
 market=request['market']
 provider,domain,form={'CN':('cninfo','www.cninfo.com.cn','FY'),
   'HK':('hkexnews','www.hkexnews.hk','FY'),'US':('sec','www.sec.gov','10-K')}[market]
 result={'schema_version':'1.0','status':'ok','adapter':identity,'acquisition_usage':usage(17),
   'candidates':[{'candidate_id':'one','provider':provider,'provider_document_id':'accession-one','market':market,
   'entity':request['entity'],'title':'Fixture Annual Report','source_url':f'https://{domain}/fixture.txt',
   'document_kind':'annual_report','form_type':form,'filing_date':'2026-03-20',
   'fiscal_year':request['fiscal_year'],'fiscal_period':'FY','language':'en',
   'security_id':request['security_id']}]}
 if a.mode=='missing-security':del result['candidates'][0]['security_id']
else:
 if a.mode=='retry-fail':fail(9*(entries.count('fetch')+1))
 if a.mode=='timeout-checkpoint':progress(19);time.sleep(30)
 if a.mode=='timeout-unknown':time.sleep(30)
 if a.mode=='output':progress(19);sys.stderr.write('x'*1200000);sys.stderr.flush();time.sleep(30)
 body=b'Fixture original annual report. The company provides devices and services.\n'
 path=Path(a.staging_dir)/'report.txt';path.write_bytes(body)
 result={'schema_version':'1.0','status':'ok','adapter':identity,'acquisition_usage':usage(len(body)),
  'receipt':{'candidate_id':request['candidate_id'],'provider':request['provider'],'provider_document_id':request['provider_document_id'],
   'source_url':request['source_url'],'staged_path':str(path),'content_sha256':hashlib.sha256(body).hexdigest(),
   'byte_size':len(body),'mime_type':'text/plain','retrieved_at':'2026-10-09T12:00:00Z','http_status':200,
   'adapter_name':identity['name'],'adapter_version':identity['version']}}
 if a.mode=='bad-receipt':result['receipt']['content_sha256']='0'*64
sys.stdout.write(json.dumps(result))
'''


def fixture_root(root: Path, mode: str):
    (root / "config").mkdir()
    (root / "companies").mkdir()
    script = root / "provider.py"
    script.write_text(PROVIDER, encoding="utf-8", newline="\n")
    log = root / "provider_calls.txt"
    catalog = root / "config" / "source_catalog.yaml"
    catalog.write_text(json.dumps({"schema_version": "1.0", "catalog_dir": str(root/"catalog"),
        "roots": [{"root_id": "company_raw", "kind": "company_raw", "path": str(root/"companies"), "priority": 10}]}), encoding="utf-8")
    spec = {"name": "proof-cli", "version": "1.0.0", "interface": "json_command_v1", "project_root": str(root),
            "config_root": None, "command": [sys.executable, "-B", str(script), mode, str(log)], "supports_acquisition_budget": True}
    acquisition = root / "config" / "source_acquisition.yaml"
    acquisition.write_text(json.dumps({"schema_version": "1.1", "staging_root": str(root/"staging"),
        "timeout_seconds": 5, "adapters": {m: dict(spec, interface="json_command_v1" if m == "cn" else "dayu_sdk_bounded_v1") for m in ("cn", "hk", "us")}}), encoding="utf-8")
    return catalog, acquisition, log
