import sys,json,gzip,hashlib
from pathlib import Path
from types import SimpleNamespace
sys.path[:0]=['.','src','tests']
from company_wiki.source_contract import EvidenceSpan
from company_wiki.automation.narrative_model_scoped import compile_scoped_model_view
from tools.document_understanding_benchmark.records import validate_gold
from tools.document_understanding_benchmark import phase_c_observer as observer

folder=Path(__file__).parent
base=Path('.planning/source-description-20261030')
gold_path=base/'cn-ir-development-gold-v3.json'
metadata_path=base/'prepared-cn-ir-summary-v4.json'
selection_path=base/'real-ci-r1/selection.json.gz'
gold=json.loads(gold_path.read_text(encoding='utf-8'))
normalized=validate_gold(gold)
metadata=json.loads(metadata_path.read_text(encoding='utf-8'))
snapshot=json.loads(gzip.decompress(selection_path.read_bytes()))
assert gold['source_sha256']==snapshot['source_sha256']==metadata['samples'][0]['fingerprint']['sha256']
assert len(gold['facts'])==len(normalized['facts'])==8
assert all(f['target_kind']=='required_business' for f in normalized['facts'])
assert normalized['scope']=='development'
assert snapshot['status']=='partial' and not snapshot['coverage_complete']
# Adapter of the saved, validated span/context fields only. This deliberately
# does not fabricate worker/Catalog state or read the original/credentials.
source=SimpleNamespace(evidence_spans=tuple(EvidenceSpan.from_dict(s) for s in snapshot['evidence_spans']),
    reading_context=snapshot['reading_context'],
    source_ref=SimpleNamespace(source_id=snapshot['source_id'],content_sha256=snapshot['source_sha256']))
view=compile_scoped_model_view(source,max_claims=20)
material=view.to_model_dict()
assert len(view.model_tasks)==len(view.admitted_task_keys)==8
spans={s.span_id:s for s in source.evidence_spans}
for task in view.model_tasks:
    assert task.support_ids and all(spans[sid].raw_text.strip() for sid in task.support_ids)
    assert set(task.member_ids)==set(task.support_ids)|set(task.context_ids)
envelope={'schema_version':'narrative-model-request/5','material':material}
report=observer.gold_observation(gold,source,envelope)
assert report['required_count']==report['supported_count']==8
assert report['sent_tasks']['required_count']==report['sent_tasks']['supported_count']==8
assert not observer.gold_admission_missing(report,attempt_no=1)
assert all(row['supported_task_keys'] for row in report['sent_tasks']['facts'])
tasks={task.key:task for task in view.model_tasks}
for fact,scored in zip(gold['facts'],report['sent_tasks']['facts'],strict=True):
    assert any(support_set and all(any(
        anchor['exact_quote'] in spans[sid].raw_text
        and anchor['page']==spans[sid].coordinates.page_number
        and anchor['locator']==spans[sid].locator
        for sid in tasks[key].support_ids) for anchor in support_set)
        for key in scored['supported_task_keys'] for support_set in fact['any_support_sets'])
protected=metadata['protected_fingerprints']
gold_sha=hashlib.sha256(gold_path.read_bytes()).hexdigest()
assert any(k.replace('\\','/').endswith(gold_path.name) and v['sha256']==gold_sha for k,v in protected.items())
result={'scope':'Actual scoped-compiler material replay from saved selection; not an executed HTTP request or worker/Catalog run.',
 'gold':str(gold_path),'gold_sha256':gold_sha,
 'metadata':str(metadata_path),'metadata_sha256':hashlib.sha256(metadata_path.read_bytes()).hexdigest(),
 'selection':str(selection_path),'selection_gzip_sha256':hashlib.sha256(selection_path.read_bytes()).hexdigest(),
 'source_sha256':snapshot['source_sha256'],'source_status':snapshot['status'],'coverage_complete':snapshot['coverage_complete'],
 'compiler_tasks':len(view.model_tasks),'all_support_nonempty':True,'all_member_unions_valid':True,
 'gold_exact_quotes_in_factual_support_not_just_context':True,
 'material_sha256':hashlib.sha256(json.dumps(material,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest(),
 'observation':report,'metadata_ready_for_post':metadata['ready_for_post'],
 'native_runtime_observation':metadata['runtime'],
 'limits':metadata['candidate_per_paid_request_limits'],
 'provider_calls':0,'sdk_calls':0,'pdf_reads':0,
 'claim_semantics':'not_evaluated; interpretation_checks and exact source qualifications retained for real output review',
 'mother_usage':'Use canonical current ledger before reservation; historical metadata baseline is not an independent current-balance audit.'}
(folder/'actual-material.json').write_text(json.dumps(material,ensure_ascii=False,indent=2),encoding='utf-8')
(folder/'actual-preflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:result[k] for k in ('scope','source_status','coverage_complete','compiler_tasks','all_support_nonempty','all_member_unions_valid','provider_calls')},indent=2))
print(json.dumps(report['sent_tasks'],ensure_ascii=True,indent=2))
