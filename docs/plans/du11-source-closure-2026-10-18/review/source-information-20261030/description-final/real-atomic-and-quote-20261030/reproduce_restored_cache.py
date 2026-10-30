"""Restore only a verified derived artifact; never restore/fabricate AUTO history."""
from contextlib import closing
from datetime import UTC, datetime
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile

ROOT = Path.cwd()
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT/'scripts')]
from tools.document_understanding_benchmark import phase_c_runner as runner
from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source
from company_wiki.source_catalog.source_reader import SourceRef
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.store import CatalogStore
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactStore, LocalNarrativeObjectStore
from company_wiki.source_catalog.official_source_flow import prepare_official_narrative_request

WORK = ROOT/'.planning/summary-quality-20261030'
HERE = WORK/'atomic-real-recovery'
OUT = HERE/'restored-cache-v5'
assert not OUT.exists()
OUT.mkdir()
(OUT/'materials').mkdir()
spec = importlib.util.spec_from_file_location('exact_artifact_restore', HERE/'restore_cache.py')
restore = importlib.util.module_from_spec(spec)
spec.loader.exec_module(restore)
meta_path = WORK/'prepared-cn-ir-atomic-v2.json'
meta = json.loads(meta_path.read_text('utf-8'))
sample, provider = runner.prepared_live_input(meta, meta['samples'][0]['sample_id'])
protected = runner.verify_preparation(meta, mode='live')
ledger = ROOT/'.planning/shared-reading-production/live/usage.jsonl'
ledger_before = runner.fingerprint(ledger)
runner.USAGE = ledger
descriptor = runner.source_descriptor(sample)
events = OUT/'events.jsonl'
results = []

def database_dump(path):
    with closing(sqlite3.connect(path)) as database:
        return tuple(database.iterdump())

with tempfile.TemporaryDirectory(prefix='cwp-restored-cache-') as temporary:
    root = Path(temporary)
    # Exact source pin: do not qualify metadata into a different material identity.
    mounted = prepare_registered_source(
        source_config=ROOT/'config/source_catalog.yaml', owned_root=root,
        original=Path(sample['original']), expected_sha256=sample['fingerprint']['sha256'],
        descriptor=descriptor, as_of_date=datetime.now(UTC).date().isoformat(), expected_ref=SourceRef(**sample['source_ref']))
    assert mounted['source_ref'] == sample['source_ref']
    config_path = Path(mounted['catalog_config'])
    config = load_catalog_config(config_path)
    artifacts = NarrativeArtifactStore(CatalogStore(config.database_path), LocalNarrativeObjectStore(config.catalog_dir))
    now = datetime.now(UTC).strftime('%Y-%m-%dT%H:%M:%SZ')
    visible = restore.restore_cache(artifacts, created_at=now, activated_at=now)
    public_request = restore.exact_read_request(visible)
    # This is exact-content processing, not issuer/period qualification.
    public_request['expected_source'] = dict.fromkeys(public_request['expected_source'])
    public_request['as_of_date'] = None
    observer = root/'observer.json'
    observer_config = {'schema_version':'phase-c-observer/1','events':str(events),
        'materials':str(OUT/'materials'), 'mode':'live',
        'source_sha256':sample['fingerprint']['sha256'], 'model_options':provider['options'],
        'gold':sample['gold'], 'gold_sha256':runner.fingerprint(Path(sample['gold']))['sha256'], 'metadata':str(meta_path), 'usage_ledger':str(ledger), 'forbid_post':True}
    runner.write_json(observer, observer_config)
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE':'1',
           'PYTHONPATH':os.pathsep.join([str(runner.BOOTSTRAP),str(ROOT),str(ROOT/'src'),str(ROOT/'scripts')]),
           'CWP_PHASE_C_OBSERVER':str(observer),'CWP_PHASE_C_NO_NETWORK':'1'}
    code, body, stderr, raw = runner._cli(root, OUT, 'recovered-public-read',
        [sys.executable,'-B','-X','utf8','-m','company_wiki.source_catalog.narrative_transport_cli',
         '--config',str(config_path),'--operation','read'],env,public_request,
        timeout=45,compact_stdout=True)
    assert code == 0, stderr
    assert body['summary_assessment']['validator']['version']=='source-summary-assessment/1.1.0'
    limits = meta['candidate_per_paid_request_limits']
    template = {'schema_version':'narrative-batch-request/1','profile':'P2','selector_version':'0.9.0',
        'reading_model_projection':'reading-model-input/7',
        **{key:limits[key] for key in ('max_seconds','max_tokens','max_cost_usd','max_final_bytes',
                                       'max_persistent_bytes','max_scratch_bytes')},
        'model':{**provider['options'],**limits['model_transport_only']},
        'pricing':{key:value for key,value in provider['price_proxy'].items() if key in
                   ('version','input_micro_usd_per_million_tokens','output_micro_usd_per_million_tokens')}}
    database = root/'AUTO.sqlite'
    previous_dump = None
    for run_id, label in (('restored-cache-1','first'),('restored-cache-1','same'),('restored-cache-2','cross')):
        template['run_id']=run_id
        request = prepare_official_narrative_request([{'source_ref':mounted['source_ref']}], batch_template=template)
        path = root/(run_id+'.json')
        runner.write_json(path, request.to_dict())
        observer_config['activation_run_id']=run_id
        runner.write_json(observer, observer_config)
        command=[sys.executable,'-B','-X','utf8',str(runner.TOOLS/'phase_c_launcher.py'),
            '--llm-provider',provider['provider'],'--project-root',str(root),
            '--catalog-config',str(config_path),'--automation-db',str(database),
            '--work-dir',str(root/run_id),'--request',str(path)]
        code, receipt, stderr, _ = runner._cli(root, OUT, label, command, env, timeout=90)
        native = runner.append_native(database, run_id, OUT, 'live')
        row={'label':label,'exit':code,'receipt':receipt,'native_usage':native}
        results.append(row)
        runner.write_json(OUT/'results.json', results)
        assert code == 0 and receipt['status']=='completed', (receipt,stderr)
        assert receipt['budget']['tokens']==0 and not native
        assert receipt['documents'][0]['artifact_ref']['content_sha256']==restore.EXPECTED_SHA
        assert receipt['documents'][0]['artifact_ref']['artifact_version_id']==visible.artifact_version_id
        current_dump=database_dump(database)
        if label=='same':
            assert current_dump==previous_dump
        previous_dump=current_dump
    assert not any(row['event']=='http_post_attempt' for row in runner.read_rows(events))
    runner.write_json(OUT/'recovered-reference.json', {'ref':public_request['narrative_ref'],
        'original_uuid_restored':False,'original_AUTO_history_restored':False,
        'original_bundle_bytes_restored':True,'original_generation_manifest_restored':True})
assert runner.verify_preparation(meta,mode='live')==protected
assert runner.fingerprint(ledger)==ledger_before
receipt={'status':'PASS_DERIVED_CACHE_RESTORATION_NOT_ORIGINAL_AUTO_HISTORY',
         'model_posts':0,'charged_tokens':0,'same_run_zero_POST':True,'cross_run_zero_POST':True,
         'source_and_config_unchanged':True,'mother_ledger_unchanged':True,
         'owned_lake_removed':not root.exists(),'raw_copies':mounted['raw_copies'],'source_selection_mode':'exact_source_version_NOT_EVALUATED_no_historical_filing_qualification',
         'artifact_sha256':restore.EXPECTED_SHA,'generation_sha256':restore.EXPECTED_GENERATION,
         'semantic_review':'OPEN','RF_actual_forecast_adoption':'OPEN'}
runner.write_json(OUT/'receipt.json',receipt)
print(json.dumps(receipt,ensure_ascii=False))
