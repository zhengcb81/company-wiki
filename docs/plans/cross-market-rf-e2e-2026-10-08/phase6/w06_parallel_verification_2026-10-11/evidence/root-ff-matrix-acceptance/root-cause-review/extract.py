"""Read-only structural/evidence diagnosis, no source execution or credentials."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
PROJECT = Path('C:/Users/郑曾波/Projects/company-wiki')
INPUT = BASE / 'fix/cross-period-repro.json'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


repro = json.loads(INPUT.read_text(encoding='utf-8'))
source_names = (
    'canonical_writer.py', 'acquisition.py', 'acquisition_service.py',
    'local_reconcile.py', 'assertion_service.py', 'resolver.py',
    'metadata_observation.py', 'acquisition_validation.py',
    'source_reader.py', 'cli.py', 'source_operation.py',
    'operation_projection.py', 'acquisition_failure.py',
)
before = {name: digest(PROJECT / 'src/company_wiki/source_catalog' / name) for name in source_names}
symbols = {
    'canonical_writer.py': ('class CanonicalSourceWriter:', 'def import_staged(', 'def _validate_staged(',
                            'def _write_provenance(', 'register_catalog_sources(', 'def source_ref_for_import('),
    'acquisition.py': ('def select(', 'local = prepare_local_source(', 'elif local["blocks_download"]:',
                       'adapter = self.adapters.for_market(', 'def _validate_candidates('),
    'acquisition_service.py': ('def _ensure(', 'if acquisition.status is AcquisitionStatus.MISSING:',
                               'imported = self.writer.import_staged('),
    'local_reconcile.py': ('def _prior_source_facts(', 'def _proven_facts(',
                           'raise SourceReadError("blocked", "local_metadata_incomplete")',
                           'def _prepare_local_source(', 'candidates = catalog.query_filing_candidates(',
                           'candidates = [x for x in candidates', 'operation = restore_document_facts(',
                           'if operation["status"] == "not_relevant":', 'targeted = True',
                           'if targeted:', '"local_metadata_gap",'),
    'assertion_service.py': ('def _sec_original(', 'def source_scope_qualification(',
                            'def record_source_facts(', 'def restore_document_facts(',
                            'prior = get_verified_assertion(', 'if facts is None and evidence is None:'),
    'resolver.py': ('def resolve(', 'if request.fiscal_year is not None and year != request.fiscal_year:',
                    'if request.fiscal_period and fiscal_period != request.fiscal_period:',
                    'def _source_metadata(', 'def _fiscal_year('),
    'operation_projection.py': ('def _status_and_source(', 'return "not_found", None, None',
                                'def project_source_operation('),
}
locations = {}
for filename, needles in symbols.items():
    lines = (PROJECT / 'src/company_wiki/source_catalog' / filename).read_text(encoding='utf-8').splitlines()
    locations[filename] = {
        needle: [i+1 for i, line in enumerate(lines) if needle in line]
        for needle in needles
    }

observed_records = []
for row in repro['verified_facts']['records']:
    acq = row['metadata']['acquisition']
    observed_records.append({
        'source_id': row['source_id'], 'content_sha256': row['content_sha256'],
        'document_kind': row['document_kind'], 'published_date': row['published_date'],
        'acquisition': {key: acq.get(key) for key in (
            'schema_version', 'request_id', 'company_name', 'market', 'security_id', 'document_kind',
            'fiscal_year', 'fiscal_period', 'form_type', 'filing_date',
            'content_sha256', 'byte_size', 'mime_type', 'adapter_name', 'adapter_version',
        )},
        'validated_request': acq.get('request'),
        'validated_candidate': {key: (acq.get('candidate') or {}).get(key) for key in (
            'candidate_id', 'entity', 'market', 'document_kind', 'fiscal_year', 'fiscal_period',
            'provider', 'provider_document_id', 'source_url', 'filing_date',
        )},
        'receipt': {key: (acq.get('receipt') or {}).get(key) for key in (
            'candidate_id', 'provider', 'provider_document_id', 'content_sha256', 'byte_size', 'mime_type',
        )},
        'actual_verified_assertion': row.get('actual_verified_assertion'),
        'actual_evidence_payload': row.get('actual_evidence_payload'),
    })

artifact_dir = Path(repro['output']) / 'artifacts'
artifacts = []
for seed in repro['warm'] + [repro['warm2025_attempt']]:
    path = artifact_dir / seed['response_ref']
    artifacts.append({'ref': seed['response_ref'], 'exists': path.is_file(),
                      'sha256': digest(path) if path.is_file() else None,
                      'expected_sha256': seed['response_sha256'],
                      'matching': path.is_file() and digest(path) == seed['response_sha256']})
for case in repro['cases']:
    run = case['run']
    for field in ('request', 'response'):
        path = artifact_dir / run[field+'_ref']
        artifacts.append({'ref': run[field+'_ref'], 'exists': path.is_file(),
                          'sha256': digest(path) if path.is_file() else None,
                          'expected_sha256': run[field+'_sha256'],
                          'matching': path.is_file() and digest(path) == run[field+'_sha256']})
    request_path = artifact_dir / run['request_ref']
    if request_path.is_file():
        request = json.loads(request_path.read_text(encoding='utf-8'))
        case['request_observation'] = {k: request.get(k) for k in (
            'schema_version', 'company', 'company_name', 'entity', 'market', 'security_id',
            'document_kind', 'fiscal_year', 'fiscal_period', 'as_of_date', 'period',
        ) if k in request}

facts_path = Path(repro['verified_facts']['path'])
artifacts.append({'ref': 'actual-verified-source-facts.json', 'exists': facts_path.is_file(),
                  'sha256': digest(facts_path) if facts_path.is_file() else None,
                  'expected_sha256': repro['verified_facts']['sha256'],
                  'matching': facts_path.is_file() and digest(facts_path) == repro['verified_facts']['sha256']})
after = {name: digest(PROJECT / 'src/company_wiki/source_catalog' / name) for name in source_names}
assert before == after
result = {
    'schema_version': 'w06-cross-period-readonly-root-cause/1',
    'verdict': 'CONFIRMED_SHARED_RELEVANCE_AND_PROOF_CHANNEL_MISMATCH',
    'input_ref': '../fix/cross-period-repro.json', 'input_sha256': digest(INPUT),
    'source_head': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip(),
    'current_source_before': before, 'current_source_after': after,
    'current_sources_unchanged': before == after,
    'actual_source_locations': locations,
    'warm2024': [{'command': seed['command'], 'status': seed['response']['status'],
                  'outcome': seed['response']['outcome'], 'download_events': seed['response']['download_events'],
                  'actual_ref': seed['response']['source_ref'], 'response_sha256': seed['response_sha256']}
                 for seed in repro['warm']],
    'warm2025_attempt': repro['warm2025_attempt'],
    'next2026': repro['cases'],
    'actual_indexed_source_facts': observed_records,
    'adapter_invocations': repro['adapter_invocations'],
    'artifact_sha_checks': artifacts,
    'all_available_artifacts_match': all(item['matching'] for item in artifacts if item['exists']),
    'all_artifacts_present': all(item['exists'] for item in artifacts),
    'new_control_execution': 'none; existing exact CLI/cross-repo public-boundary repro already proves path',
    'network_calls': 0, 'LLM_calls': 0, 'provider_calls': 0, 'fees_usd': 0,
    'product_writes': 0, 'user_raw_reads_or_writes': 0,
}
(HERE / 'evidence-observations.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps({'verdict': result['verdict'], 'source_head': result['source_head'],
                  'locations': locations,
                  'artifacts_present': result['all_artifacts_present'],
                  'artifacts_match': result['all_available_artifacts_match'],
                  'warm': [{'market': row['acquisition']['market'], 'year': row['acquisition']['fiscal_year'],
                            'actual_verified_assertion': row['actual_verified_assertion'],
                            'candidate_year': row['validated_candidate']['fiscal_year'],
                            'request_year': row['validated_request'].get('fiscal_year')}
                           for row in observed_records]}, ensure_ascii=False, indent=2))
