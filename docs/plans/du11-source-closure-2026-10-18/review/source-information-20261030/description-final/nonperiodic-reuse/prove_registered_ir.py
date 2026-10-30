"""Real owner-open to RF input contract; no provider/model, isolated catalog."""
from datetime import UTC, datetime, date
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile

repo = Path.cwd()
sys.path.insert(0, str(repo))
from tools.document_understanding_benchmark import phase_c_runner as runner
from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source

work = repo / '.planning/summary-quality-20261030'
out = work / 'real-registered-ir-v2'
assert not out.exists()
out.mkdir()
meta = json.loads((repo / '.planning/source-description-20261030/prepared-cn-ir-summary-v4.json').read_text('utf-8'))
sample = meta['samples'][0]
descriptor = sample['source_metadata_observation']
protected = runner.verify_preparation(meta, mode='live')
today = datetime.now(UTC).date().isoformat()
with tempfile.TemporaryDirectory(prefix='rf-ir-', dir=work) as name:
    root = Path(name)
    runner.seed_identity(root, 'live', descriptor, source_catalog_config=repo / 'config/source_catalog.yaml')
    mounted = prepare_registered_source(
        source_config=repo / 'config/source_catalog.yaml', owned_root=root,
        original=Path(sample['original']), expected_sha256=sample['fingerprint']['sha256'],
        descriptor=descriptor, as_of_date=today)
    manifest = mounted['manifest']
    # Translate an actual public owner manifest to the existing pathless
    # candidate DTO. This is not a fabricated FF response or a published date.
    candidate = {key: manifest[key] for key in ('document_kind', 'fiscal_year', 'fiscal_period')}
    candidate.update(status='source_candidate', source_ref=mounted['source_ref'],
                     byte_verification='pending_verified_open',
                     resolution_outcome='reused_existing', download_events=mounted['download_events'])
    request = {'candidate': candidate, 'as_of_date': today, 'config': mounted['catalog_config']}
    child = root / 'read.py'
    child.write_text('''import json,sys\nfrom pathlib import Path\nfrom datetime import date\nfrom source_preparation import prepare_registered_source_result\nfrom contracts.document import validate_sources\nr=json.load(sys.stdin)\nv=prepare_registered_source_result(r['candidate'],as_of_date=r['as_of_date'],company_wiki_catalog_config=Path(r['config']),source_reader_receipt_version='2.2')\nvalidate_sources({'sources':[v['source']]},date.fromisoformat(r['as_of_date']),require_capture=True)\nprint(json.dumps(v,ensure_ascii=False))\n''', encoding='utf-8')
    events = out / 'events.jsonl'
    observer = root / 'observer.json'
    runner.write_json(observer, {'events': str(events)})
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(runner.BOOTSTRAP), str(repo.parent / 'revenue-forecast/scripts'), str(repo), str(repo / 'src'), str(repo / 'scripts')]), 'CWP_PHASE_C_OBSERVER': str(observer), 'CWP_PHASE_C_NO_NETWORK': '1'}
    proc = subprocess.run([sys.executable, '-B', '-X', 'utf8', str(child)], input=json.dumps(request), encoding='utf-8', capture_output=True, env=env, cwd=repo.parent/'revenue-forecast', timeout=45)
    (out/'stderr.txt').write_text(proc.stderr, encoding='utf-8')
    if proc.returncode:
        runner.write_json(out/'failure.json', {'exit': proc.returncode, 'stderr': proc.stderr})
        raise RuntimeError(proc.stderr)
    result = json.loads(proc.stdout)
    source = result['source']
    runner.write_json(out/'source-preparation.json', result)
    assert source['url'] is None and source['published_date'] is None
    assert source['company_wiki_trace']['source_manifest']['security_id'] == descriptor['security_id']
    assert all(manifest[key] is None for key in ('fiscal_year', 'fiscal_period', 'published_date', 'source_url'))
    assert source['capture']['snapshot_sha256'] == sample['fingerprint']['sha256']
    assert result['filing_fetch'] is None and source['reuse_receipt']['download_calls'] == 0
    assert runner.verify_preparation(meta, mode='live') == protected
receipt = {'status':'PASS', 'scope':'real registered IR owner byte open + RF source input validation; not narrative/forecast adoption', 'source_sha256':sample['fingerprint']['sha256'], 'unknown_metadata_preserved':True, 'downloads':0, 'model_posts':0, 'network_blocked':True, 'raw_copies':mounted['raw_copies'], 'owned_temporary_lake_removed':not root.exists(), 'protected_unchanged':True}
runner.write_json(out/'receipt.json', receipt)
print(json.dumps(receipt, ensure_ascii=False))
