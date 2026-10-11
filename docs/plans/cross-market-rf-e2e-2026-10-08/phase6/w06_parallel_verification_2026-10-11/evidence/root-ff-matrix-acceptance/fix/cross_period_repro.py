"""Bounded synthetic actual-writer reproduction; never accesses production key bytes."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(r'C:/Users/郑曾波/Projects/_harness_worktrees/w06/ff-contract-matrix-root')
CWP = Path(r'C:/Users/郑曾波/Projects/company-wiki')
ET = Path(r'C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts')
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT/'tools/offline_contract_matrix'))
from runtime import Deadline, OwnedAttempt, run_process, guard_events
from run import Context, ProductionGuard, _mk_filing_request
from fixture_builder import US, CN

diagnostic = r'''import json,sys
from pathlib import Path
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.assertion_service import get_verified_assertion,_evidence_payload
wiki=Path(sys.argv[1]); catalog=SourceCatalog(load_catalog_config(wiki/'config/source_catalog.yaml',project_root=wiki))
records=[]
try:
 for row in catalog.reader.fetchall('SELECT d.document_id,d.document_kind,d.published_date,d.metadata_json,s.source_id,s.content_sha256 FROM documents d JOIN sources s ON s.source_id=d.primary_source_id'):
  record=dict(row); record['metadata']=json.loads(record.pop('metadata_json') or '{}')
  a=get_verified_assertion(catalog.reader,row['source_id'],row['content_sha256'],reader='steady')
  record['actual_verified_assertion']=a
  record['actual_evidence_payload']=_evidence_payload(a['evidence_json'],a['assertion_id']) if a else None
  records.append(record)
 print(json.dumps(records,ensure_ascii=False))
finally: catalog.close()
'''

def main():
    d=Deadline(45)
    owned=OwnedAttempt.create(CWP/'.tmp/w06-repro-owned',CWP/'.tmp/w06-repro-evidence')
    guard=ProductionGuard(ROOT,CWP,ET)
    result={'schema_version':'w06-cross-period-repro/1','meaning':'actual writer warm2024, new period request2025/2026; distinct identity/period bytes; no handmade assertion','output':str(owned.output),'warm':[],'cases':[]}
    ctx=Context(ff_root=ROOT,cwp_root=CWP,et_root=ET,scratch=owned.scratch,out_root=owned.output,deadline=d)
    try:
        for identity in (US,CN):
            result['warm'].append(ctx.warm_seed(identity,'annual_report',2024,'FY'))
        # Public CWP ensure itself, followed by public FF request, not a helper-only assertion.
        result['warm2025_attempt']=ctx.warm_seed(US,'annual_report',2025,'FY')
        for identity in (US,CN):
            tag='warm2024_request2026_'+identity.market
            ctx.begin_case()
            ctx.write_state(scenario='success',provider_scenario='serve',calls_file=ctx.env.calls_file(tag),receipt_tag=tag)
            request=_mk_filing_request(identity,document_kind='annual_report',fiscal_year=2026,fiscal_period='FY',intent='fetch_if_missing')
            result['cases'].append({'identity':identity.market,'run':ctx.run_ff(request,case_id=tag)})
        proc=run_process([sys.executable,'-B','-c',diagnostic,str(ctx.env.wiki)],env=ctx.child_env(),cwd=owned.scratch,deadline=d)
        fact_path=ctx.artifacts/'actual-verified-source-facts.json'
        fact_path.write_bytes(proc.stdout)
        (ctx.artifacts/'actual-verified-source-facts.stderr.txt').write_bytes(proc.stderr)
        result['verified_facts']={'path':str(fact_path),'exit_code':proc.returncode,'sha256':hashlib.sha256(proc.stdout).hexdigest(),'records':json.loads(proc.stdout)}
        result['adapter_invocations']=ctx.adapter_records()
        result['guard']=guard_events(owned.scratch)
    finally:
        result['restore']=owned.cleanup()
        result['production_stat_unchanged']=guard.unchanged(guard.snapshot())
        result['remaining_seconds']=max(0,d.end-__import__('time').monotonic())
        (owned.output/'repro.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        (HERE/'cross-period-repro.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'output':str(owned.output),'warm_statuses':[x['response'].get('status') for x in result['warm']],'warm2025':result.get('warm2025_attempt',{}).get('response',{}),'case_statuses':[(x['identity'],x['run']['response'].get('filing')) for x in result['cases']],'restore':result['restore']},ensure_ascii=True))

if __name__=='__main__': main()
