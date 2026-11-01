"""Resume exact captured paid artifacts; no model/PDF parsing or old DB restore."""
from pathlib import Path
from datetime import datetime, UTC
import gzip
import hashlib
import json
import os
import socket
import sys
import tempfile

ROOT = Path.cwd()
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')]
from tools.document_understanding_benchmark import phase_c_runner as runner
from tools.document_understanding_benchmark.phase_c_readonly_source import prepare_registered_source
from company_wiki.automation.narrative_contracts import NarrativeBundle
from company_wiki.automation.narrative_generation import verify_reading_bundle_generation
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.source_reader import SourceRef
from company_wiki.source_catalog.store import CatalogStore
from company_wiki.source_catalog.narrative_artifact_store import (
    NarrativeArtifactDraft, NarrativeArtifactStore, LocalNarrativeObjectStore,
)

W = ROOT / '.planning/mainline-closeout-20261031'
CAP = W / 'p1-huali-live-v2'
OUT = W / 'p1-huali-consumer-recovery-v2'


def main():
    assert not OUT.exists(), 'preserve earlier attempts'
    OUT.mkdir()
    meta = json.loads((W / 'p1-preparation-v5/metadata.json').read_text(encoding='utf-8'))
    sample = next(s for s in meta['samples'] if s['sample_id'] == 'c3-cn-huali-ir-202305')
    state = json.loads((CAP / 'overall.json').read_text(encoding='utf-8'))['states'][0]
    assert state['exit'] == 0 and state['activation_recovery']['status'] == 'PASS'
    assert state['same_run_zero_POST'] and state['cross_run_zero_POST']
    capsule_path, = (CAP / 'materials').glob('*.prepared.capsule.json.gz')
    capsule = json.loads(gzip.decompress(capsule_path.read_bytes()))
    pin = capsule['payload']
    body = gzip.decompress((CAP / 'materials' / pin['file']).read_bytes())
    assert len(body) == pin['bytes'] and hashlib.sha256(body).hexdigest() == pin['sha256']
    assert gzip.decompress((CAP / (state['run_id'] + '.bundle.json.gz')).read_bytes()) == body
    bundle = NarrativeBundle.from_dict(json.loads(body))
    generation = json.loads(gzip.decompress((CAP / 'materials' / capsule['generation_checkpoint']['file']).read_bytes()))
    assert generation == state['final_generation']
    verify_reading_bundle_generation(bundle, generation)
    guard = OUT / 'no-network'
    guard.mkdir()
    (guard / 'sitecustomize.py').write_text(
        'import socket\n_orig=socket.socket.connect\ndef block(self,addr):\n'
        ' if self.family in (socket.AF_INET,socket.AF_INET6): raise RuntimeError("NO_NETWORK_EXACT_ARTIFACT_REUSE")\n'
        ' return _orig(self,addr)\nsocket.socket.connect=block\n', encoding='utf-8')
    env = {**os.environ, 'PYTHONDONTWRITEBYTECODE': '1', 'CWP_PHASE_C_NO_NETWORK': '1',
           'PYTHONPATH': os.pathsep.join([str(guard), str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')])}
    env.pop('CWP_PHASE_C_OBSERVER', None)
    original_connect = socket.socket.connect

    def blocked(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6):
            raise RuntimeError('NO_NETWORK_EXACT_ARTIFACT_REUSE')
        return original_connect(sock, address)

    socket.socket.connect = blocked
    protected = {p: runner.fingerprint(Path(p)) for p in meta['protected_fingerprints']}
    protected[str(ROOT / '.planning/shared-reading-production/live/usage.jsonl')] = runner.fingerprint(ROOT / '.planning/shared-reading-production/live/usage.jsonl')
    temp = None
    try:
        with tempfile.TemporaryDirectory(prefix='cwp-p1-source-resume-') as td:
            temp = Path(td)
            descriptor = runner.source_descriptor(sample)
            mounted = prepare_registered_source(
                source_config=ROOT / 'config/source_catalog.yaml', owned_root=temp,
                original=Path(sample['original']), expected_sha256=sample['fingerprint']['sha256'],
                descriptor=descriptor, as_of_date=datetime.now(UTC).date().isoformat(),
                source_facts=sample['registered_source_facts'], expected_ref=SourceRef(**sample['source_ref']))
            runner.write_json(OUT / 'registration.json', mounted)
            config = load_catalog_config(Path(mounted['catalog_config']))
            store = CatalogStore(config.database_path)
            # CatalogStore opens/closes each transaction; it owns no persistent
            # connection/close method (unlike the read facade SourceCatalog).
            artifacts = NarrativeArtifactStore(store, LocalNarrativeObjectStore(config.catalog_dir))
            draft = NarrativeArtifactDraft(**capsule['prepared_draft'])
            artifacts.prepare(draft, body)
            active = artifacts.activate(draft.effect_id, verified_after_hash=pin['sha256'], activated_at=datetime.now(UTC).isoformat())
            assert active.content_sha256 == state['artifact_ref']['artifact_sha256']
            request = json.loads((CAP / (state['run_id'] + '.read-request.json')).read_text(encoding='utf-8'))
            old_ref = request['narrative_ref']
            request['narrative_ref'] = {**old_ref, 'artifact_version_id': active.artifact_version_id}
            runner.write_json(OUT / 'read-request.json', request)
            result = runner.consumers(temp, OUT, env, Path(mounted['catalog_config']), descriptor, request, bundle.to_dict(), projects=ROOT.parent)
            runner.write_json(OUT / 'consumers.json', result)
            runner.write_json(OUT / 'receipt.json', {
                'status': 'PASS', 'capture': str(CAP), 'original_run_id': state['run_id'],
                'original_artifact_ref': old_ref, 'restored_ref': request['narrative_ref'],
                'body_sha256': pin['sha256'], 'generation_unchanged': True,
                'activation_same_cross_run': state['activation_recovery'],
                'same_run_zero_POST': True, 'cross_run_zero_POST': True,
                'new_POST': 0, 'new_tokens': 0, 'new_micro_usd': 0,
                'new_selection_parse_runs': 0, 'locator_replay_performed': True,
                'locator_replay_parse_call_count': None, 'downloads': 0,
                'scope': 'exact paid artifact consumer restoration; no old AUTO/usage/history restored; original full-run failure retained',
            })
    finally:
        socket.socket.connect = original_connect
        unchanged = all(runner.fingerprint(Path(p)) == v for p, v in protected.items())
        runner.write_json(OUT / 'cleanup.json', {'temporary_root': str(temp), 'removed': temp is not None and not temp.exists(), 'protected_unchanged': unchanged})
        assert unchanged and temp is not None and not temp.exists()
    print('PASS: exact artifact consumers recovered; 0 POST/0 new selection/0 downloads; locator replay performed')


if __name__ == '__main__':
    main()
