"""Zero-paid public-consumer replay of immutable real summary bytes."""
from datetime import UTC, datetime
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile

ROOT = Path.cwd()
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')]
from tools.document_understanding_benchmark import phase_c_runner as runner
from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source
from company_wiki.automation.narrative_contracts import NarrativeBundle

WORK = ROOT / '.planning/summary-quality-20261030'
LIVE = WORK / 'real-fidelity-v1'
OUT = WORK / 'real-fidelity-consumer-v1'
assert not OUT.exists()
OUT.mkdir()
meta_path = WORK / 'prepared-cn-ir-fidelity-v1.json'
meta = json.loads(meta_path.read_text('utf-8'))
protected = runner.verify_preparation(meta, mode='live')
ledger = ROOT / '.planning/shared-reading-production/live/usage.jsonl'
ledger_before = runner.fingerprint(ledger)
payload = gzip.decompress(next(LIVE.glob('*.bundle.json.gz')).read_bytes())
bundle = json.loads(payload)
NarrativeBundle.from_dict(bundle)
request = json.loads(next(LIVE.glob('*.read-request.json')).read_text('utf-8'))
original_ref = json.loads(json.dumps(request['narrative_ref']))
sample = meta['samples'][0]
descriptor = runner.source_descriptor(sample)
helper = ROOT / 'docs/plans/du11-source-closure-2026-10-18/review/market-family-upgrade-20261024/cn-h1-real-summary-recovery-20261024/run_consumer_e2e.py'
spec = importlib.util.spec_from_file_location('prior_official_consumer_replay', helper)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

with tempfile.TemporaryDirectory(prefix='cwp-fidelity-consumer-') as temporary:
    root = Path(temporary)
    runner.seed_identity(root, 'live', descriptor, source_catalog_config=ROOT/'config/source_catalog.yaml')
    mounted = prepare_registered_source(
        source_config=ROOT/'config/source_catalog.yaml', owned_root=root,
        original=Path(sample['original']), expected_sha256=sample['fingerprint']['sha256'],
        descriptor=descriptor, as_of_date=request['as_of_date'])
    assert mounted['source_ref'] == original_ref['source_ref']
    replay = module.rehydrate_bundle(Path(mounted['catalog_config']), payload, bundle,
                                    original_artifact_version_id=original_ref['artifact_version_id'])
    request['narrative_ref']['artifact_version_id'] = replay['visible_artifact_version_id']
    assert request['narrative_ref']['artifact_sha256'] == hashlib.sha256(payload).hexdigest()
    observer = root/'observer.json'
    runner.write_json(observer, {'events': str(OUT/'events.jsonl'), 'forbid_post': True})
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1',
           'PYTHONPATH': os.pathsep.join([str(runner.BOOTSTRAP), str(ROOT), str(ROOT/'src'), str(ROOT/'scripts')]),
           'CWP_PHASE_C_OBSERVER': str(observer), 'CWP_PHASE_C_NO_NETWORK': '1'}
    results = runner.consumers(root, OUT, env, Path(mounted['catalog_config']),
                               descriptor, request, bundle, projects=ROOT.parent)
    runner.write_json(OUT/'results.json', results)
    runner.write_json(OUT/'replayed-ref.json', {'original': original_ref, 'owned_replay': request['narrative_ref'],
                    'official_store': replay, 'bundle_bytes_unchanged': True,
                    'not_a_new_model_or_cache_generation': True})
assert runner.verify_preparation(meta, mode='live') == protected
assert runner.fingerprint(ledger) == ledger_before
receipt = {'status': 'PASS_READONLY_CONSUMERS_NOT_FORECAST_ADOPTION', 'model_posts': 0, 'downloads': 0,
           'raw_copies': mounted['raw_copies'], 'original_and_config_unchanged': True,
           'mother_ledger_unchanged': True, 'owned_lake_removed': not root.exists(),
           'artifact_body_sha256': hashlib.sha256(payload).hexdigest(),
           'unknown_period_and_url_preserved': True,
           'summary_assessment_preserved': True, 'semantic_status': 'not_evaluated',
           'observed_at': datetime.now(UTC).isoformat()}
runner.write_json(OUT/'receipt.json', receipt)
print(json.dumps(receipt, ensure_ascii=False))
