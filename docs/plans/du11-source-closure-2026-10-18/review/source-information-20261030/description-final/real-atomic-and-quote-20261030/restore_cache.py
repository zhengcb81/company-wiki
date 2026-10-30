"""Public artifact-store recovery adapter; importing this module performs no writes.

Caller supplies an existing registered/current NarrativeArtifactStore. This only
restores byte-identical publication plus generation metadata. It cannot recover
original AUTO attempts, leases, paid HTTP envelope/pin, or original artifact UUID.
"""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src'))
from company_wiki.automation.models import canonical_json,canonical_json_hash
from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.narrative_generation import generation_sha256,verify_reading_bundle_generation
from company_wiki.automation.narrative_transport_contracts import EXPECTED_SOURCE_FIELDS
from company_wiki.source_catalog.narrative_artifact_store import NarrativeArtifactDraft

HERE=Path(__file__).resolve().parent
EXPECTED_SHA='216827368a284843c661e6b00c722e659e11e0838b1bae6dcc0aaf5c6d725311'
EXPECTED_GENERATION='d929ea90aa03988cbdda27122f1fbcbf4aaefb28af2be62762d6967280af3fa4'

def recovery_draft(*,created_at):
    body=(HERE/'original-canonical-bundle.json').read_bytes()
    assert len(body)==170748 and hashlib.sha256(body).hexdigest()==EXPECTED_SHA
    bundle=NarrativeBundle.from_dict(json.loads(body))
    final=json.loads((HERE/'original-generation-final.json').read_text('utf-8-sig'))
    base=json.loads((HERE/'original-generation-base.json').read_text('utf-8-sig'))
    assert generation_sha256(final)==EXPECTED_GENERATION
    assert {k:v for k,v in final.items() if k not in {'selection_generation','reading_dependencies'}}==base
    verify_reading_bundle_generation(bundle,final)
    original=json.loads((HERE/'artifact-reconstruction.json').read_text('utf-8-sig'))['original_artifact_ref']
    identity={'schema_version':'narrative-offline-artifact-recovery/1',
              'original_artifact_ref':original,'generation_sha256':EXPECTED_GENERATION}
    key=canonical_json_hash(identity)
    metadata={'bundle_schema':bundle.schema_version,'summary_status':bundle.summary.status,
              'generation_manifest':final,'generation_sha256':EXPECTED_GENERATION,
              'base_generation_sha256':generation_sha256(base),
              'recovery_provenance':{**identity,'mode':'exact_captured_artifact_reconstruction',
                 'new_model_generation':False,'AUTO_history_restored':False,
                 'original_artifact_uuid_restored':False}}
    draft=NarrativeArtifactDraft(effect_id='offline-recovery-'+key,work_key=key,
        document_id=bundle.source_ref.document_id,source_id=bundle.source_ref.source_id,
        source_sha256=bundle.source_ref.content_sha256,producer_name='company_wiki.narrative_bundle',
        producer_version=bundle.versions.bundle_producer,policy_sha256=bundle.expected_read_policy_sha256,
        selection_status=bundle.selection.status,quality_status=bundle.quality_status,
        metadata_json=canonical_json(metadata),created_at=created_at)
    return draft,body

def restore_cache(artifacts,*,created_at,activated_at):
    """Explicit write API; source registration must already exist and be current.

    prepare/activate remain responsible for CAS, current-source checks and byte
    hashing. This function never inserts jobs, accepted states or paid pins.
    Returned artifact version ID is necessarily a new local publication UUID.
    """
    draft,body=recovery_draft(created_at=created_at)
    prepared=artifacts.prepare(draft,body)
    assert prepared.content_sha256==EXPECTED_SHA and prepared.byte_size==170748
    visible=artifacts.activate(draft.effect_id,verified_after_hash=EXPECTED_SHA,activated_at=activated_at)
    return visible

def exact_read_request(version):
    manifest=json.loads((ROOT/'.planning/summary-quality-20261030/real-atomic-v2/registered-source.json').read_text('utf-8-sig'))['manifest']
    return {'schema_version':'narrative-read-request/1','as_of_date':None,
            'expected_source':{key:manifest.get(key) for key in EXPECTED_SOURCE_FIELDS},
            'narrative_ref':{'schema_version':'narrative-ref/1',
              'artifact_version_id':version.artifact_version_id,'artifact_sha256':version.content_sha256,
              'byte_size':version.byte_size,
              'source_ref':json.loads((HERE/'original-canonical-bundle.json').read_bytes())['source_ref']}}

if __name__=='__main__':
    # Metadata preparation only. No catalog, object-store or AUTO writes.
    from datetime import datetime,timezone
    draft,_=recovery_draft(created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'))
    (HERE/'cache-recovery-draft.json').write_text(json.dumps(asdict(draft),ensure_ascii=False,indent=2),encoding='utf-8')
    (HERE/'cache-recovery-metadata.json').write_text(json.dumps(json.loads(draft.metadata_json),ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'status':'METADATA_READY_NOT_PUBLISHED','work_key':draft.work_key,
                      'model_posts':0,'store_writes':0}))
