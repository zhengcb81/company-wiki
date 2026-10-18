"""Small independent offline checks, run only in ROOT-owned archived snapshots."""
import hashlib
import json
import os
from pathlib import Path
import time
import pytest
from test_du11_transcript_reuse_support import OwnedWiki, MOTLEY_SIDECAR, KNOWN_TRANSCRIPT_BODY, AS_OF, ENTITY
from test_du11_transcript_reuse_contract import FakeCWP, query_found, reader_entry, build, companion_request, filing, LOCAL_RAW
from transcript_tool_transport import EarningsTranscriptsTransport
from ff_process_transport import ChildFailed
from transcript_companion import resolve_companion_transcript


@pytest.mark.parametrize('delta,expected', [
    ({'published': '2027-01-01'}, 'publication_after_as_of'),
    ({'published': 'not-a-date'}, 'publication_date_invalid'),
    ({'published': None}, 'publication_date_unknown'),
    ({'security_id': '0MSFT'}, 'transcript_lookup_identity_mismatch'),
])
def test_original_independent_false_reuse_is_closed(tmp_path, monkeypatch, delta, expected):
    tool = tmp_path/'offline.py'
    tool.write_text('# never executed\n', encoding='utf8')
    fake = FakeCWP(queries=[query_found(LOCAL_RAW)], reader=[reader_entry(LOCAL_RAW, **delta)])
    result = resolve_companion_transcript(request=companion_request(), filing_handle=filing(),
                                          transport=build(monkeypatch, fake, tool))
    assert result['status'] != 'reused'
    assert result['reason'] == expected
    assert result.get('as_of_cutoff_verified') is not True
    assert fake.kinds() == ['query', 'reader']
    assert fake.count('et') == fake.count('import') == 0


def test_current_real_hk_reader_to_ff_reuse_and_legacy_receipt(tmp_path):
    wiki = OwnedWiki(Path(os.environ['DU11_CWP_TAR']), label='du11-final-hk').build(with_security_master=False)
    final_record = {}
    try:
        facts = dict(MOTLEY_SIDECAR, market='HK', security_id='9896', ticker='09896')
        raw = wiki.seed_transcript('hk_2026_q3_call.txt', KNOWN_TRANSCRIPT_BODY, facts)
        wiki.run_scan()
        wiki.checkpoint()
        handle = filing()
        handle['company_identity'].update(canonical_name=ENTITY, market='HK', security_id='09896', ticker='09896', exchange='HKEX')
        held = EarningsTranscriptsTransport(wiki_root=wiki.root, transcript_tool=wiki.et_tool(),
            fmp_api_key_file=wiki.key_file(), deadline=time.monotonic()+120)
        resolved = resolve_companion_transcript(request=companion_request(), filing_handle=handle, transport=held)
        assert resolved['status'] == 'reused', (resolved.get('status'), resolved.get('reason'))
        assert resolved['provider'] == 'motley_fool'
        assert resolved['provider_calls'] == 0
        assert resolved['as_of_cutoff_verified'] is True
        assert held.company_wiki_calls == 2
        assert not wiki.call_log().exists()
        ref = resolved['source_ref']
        assert ref['content_sha256'] == hashlib.sha256(KNOWN_TRANSCRIPT_BODY).hexdigest()
        code, body, legacy = wiki.read_version(ref)
        assert code == 0
        assert body == KNOWN_TRANSCRIPT_BODY
        assert 'canonical_identity' not in legacy
        assert legacy['manifest']['security_id'] == '9896'
        current = held._verified_open(ref)
        assert current['canonical_identity'] == {'schema_version':'source-canonical-identity/1', 'market':'HK', 'security_id':'09896'}
        assert current['manifest']['security_id'] == '9896'
        before_stat = raw.stat()
        raw.write_bytes(b'changed bytes after indexed source')
        try:
            with pytest.raises((ValueError, ChildFailed)):
                held._verified_open(ref)
        finally:
            raw.write_bytes(KNOWN_TRANSCRIPT_BODY)
            os.utime(raw, ns=(before_stat.st_atime_ns, before_stat.st_mtime_ns))
        assert raw.read_bytes() == KNOWN_TRANSCRIPT_BODY
        restored = wiki.assert_restored()
        final_record = {'actual_ff_query_reader_reuse': True, 'provider_calls':0,
            'content_sha256':ref['content_sha256'], 'raw_unchanged': True,
            'observed_security_id':'9896','canonical_security_id':'09896',
            'legacy_flag_absent_compatible': True, 'raw_tamper_rejected': True,
            'restored': all(restored[k] == [] for k in ('restore_entry_changed','frozen_source_changed','changed_since_checkpoint','unexpected_added','removed_since_checkpoint'))}
    finally:
        wiki.cleanup()
        final_record['owned_wiki_removed'] = not wiki.root.exists()
        Path(os.environ['DU11_ACTUAL_RECEIPT']).write_text(json.dumps(final_record), encoding='utf8')

