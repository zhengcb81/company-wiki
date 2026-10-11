"""Write only the authorized ET responsibility tests before implementation."""
import hashlib
import json
from pathlib import Path

TREE = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w06/et-cutoff-root')
EVIDENCE = Path(__file__).resolve().parent / 'et'
before = json.loads((EVIDENCE / 'before.json').read_text(encoding='utf-8'))
by_path = {entry['path'].replace('\\', '/'): entry for entry in before['files']}
api_path = TREE / 'tests/test_transcript_api.py'
cli_path = TREE / 'tests/test_retrieval_cli_e2e.py'
for path in (api_path, cli_path):
    relative = path.relative_to(TREE).as_posix()
    if hashlib.sha256(path.read_bytes()).hexdigest() != by_path[relative]['sha256']:
        raise RuntimeError(f'Unexpected test drift: {relative}')

api = api_path.read_text(encoding='utf-8')
api = api.replace('    assert result["status"] == "not_found"\n    assert len(session.calls) == 1\n', '    assert result["status"] == "not_found"\n    assert result["error_code"] == "publication_after_as_of"\n    assert len(session.calls) == 1\n', 1)
old = '    assert result["status"] == "not_found"\n\n\ndef test_fmp_rejects_redirects():'
new = '    assert result["status"] == "not_found"\n    assert result["error_code"] == "call_after_as_of"\n\n\ndef test_fmp_rejects_redirects():'
if old not in api:
    raise RuntimeError('FMP RED assertion anchor missing')
api = api.replace(old, new, 1)
api += '''

# W06: exclusion is an observed acquisition outcome, not provider unavailability.
def _fmp_cutoff_result(payload, *, as_of="2026-07-21", include_payload=False):
    session = FakeSession({
        FMP_URL: FakeResponse(FMP_URL, payload, content_type="application/json")
    })
    result = fetch_transcript(
        make_request(
            ticker="MSFT", exchange="nasdaq", fiscal_quarter=3,
            provider="fmp", as_of_date=as_of,
        ),
        session_factory=lambda: session, fmp_api_key="fake-cutoff-key",
        include_source_payload=include_payload,
    )
    assert len(session.calls) == 1
    return result


def test_w06_fmp_cutoff_cause_survives_both_result_versions():
    for include_payload in (False, True):
        result = _fmp_cutoff_result(fmp_payload(), include_payload=include_payload)
        assert result["schema_version"] == (
            "earnings-transcript-result/2" if include_payload
            else "earnings-transcript-result/1"
        )
        assert result["status"] == "not_found"
        assert result["fiscal_period"] == "2026-Q3"
        assert result["candidate_count"] == 0
        assert result["error_code"] == "call_after_as_of"
        assert not set(result) & {
            "reason", "content_utf8", "provider_payload_base64",
            "as_of_cutoff_verified", "publication_date",
        }


def test_w06_fmp_empty_response_is_missing_without_cutoff_inference():
    for include_payload in (False, True):
        result = _fmp_cutoff_result(b"[]", include_payload=include_payload)
        assert result["status"] == "not_found"
        assert result["candidate_count"] == 0
        assert "error_code" not in result


def test_w06_fmp_cutoff_day_is_allowed_but_publication_stays_unknown():
    result = _fmp_cutoff_result(fmp_payload(), as_of="2026-07-22")
    assert result["status"] == "fetched"
    assert "error_code" not in result
    assert result["call_date"] == "2026-07-22"
    assert result["publication_date"] is None
    assert result["as_of_cutoff_verified"] is False


def test_w06_fmp_wrong_scope_cannot_be_reclassified_as_cutoff():
    for payload in (
        fmp_payload(symbol="OTHER"), fmp_payload(period="Q2"),
        fmp_payload(year=2025), fmp_payload(date="2026-7-22"),
    ):
        result = _fmp_cutoff_result(payload)
        assert result["status"] == "provenance_rejected"
        assert result.get("error_code") != "call_after_as_of"


def test_w06_fmp_multiple_candidates_keep_existing_ambiguity():
    current = json.loads(fmp_payload(date="2026-07-20"))[0]
    future = json.loads(fmp_payload(date="2026-07-22"))[0]
    for rows in ([current, future], [future, dict(future)]):
        result = _fmp_cutoff_result(json.dumps(rows).encode("utf-8"))
        assert result["status"] == "ambiguous"
        assert result["candidate_count"] == 2
        assert "error_code" not in result


def test_w06_motley_fetch_and_discover_preserve_target_publication_cutoff():
    for operation in (fetch_transcript, discover_transcripts):
        session = FakeSession({QUOTE_URL: FakeResponse(QUOTE_URL, quote_html(Q2_URL))})
        result = operation(
            make_request(as_of_date="2026-08-31"),
            session_factory=lambda: session,
            provider_settings=ProviderSettings(motley_fool_enabled=True),
        )
        assert result["status"] == "not_found"
        assert result["candidate_count"] == 0
        assert result["error_code"] == "publication_after_as_of"
        assert len(session.calls) == 1
        assert "content_utf8" not in result


def test_w06_motley_other_period_future_record_is_plain_missing():
    for operation in (fetch_transcript, discover_transcripts):
        session = FakeSession({QUOTE_URL: FakeResponse(QUOTE_URL, quote_html(Q1_URL))})
        result = operation(
            make_request(as_of_date="2026-04-30"),
            session_factory=lambda: session,
            provider_settings=ProviderSettings(motley_fool_enabled=True),
        )
        assert result["status"] == "not_found"
        assert result["candidate_count"] == 0
        assert "error_code" not in result
        assert len(session.calls) == 1


def test_w06_motley_cutoff_day_and_mixed_dates_select_eligible_candidate():
    future = Q2_URL.replace("/09/01/", "/09/02/")
    for operation in (fetch_transcript, discover_transcripts):
        session = FakeSession({
            QUOTE_URL: FakeResponse(QUOTE_URL, quote_html(Q2_URL, future)),
            Q2_URL: FakeResponse(Q2_URL, transcript_html()),
        })
        result = operation(
            make_request(as_of_date="2026-09-01"),
            session_factory=lambda: session,
            provider_settings=ProviderSettings(motley_fool_enabled=True),
        )
        assert result["status"] == (
            "fetched" if operation is fetch_transcript else "discovered"
        )
        assert "error_code" not in result
        assert len(session.calls) == (2 if operation is fetch_transcript else 1)
        if operation is discover_transcripts:
            assert result["candidate_count"] == 1
            assert result["candidates"][0]["source_url"] == Q2_URL
'''
api_path.write_text(api, encoding='utf-8', newline='\n')

cli = cli_path.read_text(encoding='utf-8')
cli += '''

def test_w06_cutoff_diagnostic_and_actual_usage_survive_real_worker(monkeypatch, tmp_path):
    forbid_translator(monkeypatch)
    monkeypatch.chdir(tmp_path)
    temp_root = tmp_path / "rt"
    temp_root.mkdir()
    for provider in ("fmp", "motley_fool"):
        calls_file = tmp_path / f"{provider}.jsonl"
        if provider == "fmp":
            request = make_request(
                ticker="MSFT", exchange="nasdaq", fiscal_quarter=3,
                provider="fmp", as_of_date="2026-07-21",
            )
            payload = fmp_payload()
            responses = {
                FMP_URL: FakeResponse(FMP_URL, payload, content_type="application/json")
            }
            expected_code = "call_after_as_of"
        else:
            request = make_request(as_of_date="2026-08-31")
            payload = quote_html(Q2_URL)
            responses = {QUOTE_URL: FakeResponse(QUOTE_URL, payload)}
            expected_code = "publication_after_as_of"
        spec = fake_spec(responses, calls_file=calls_file)
        rc, out, err = run_tool(
            monkeypatch,
            ["--request-stdin", "--include-source-payload", "--report-usage"],
            request, spec=spec, temp_root=temp_root, settings=ENABLED_FOOL,
        )
        result = json.loads(out)
        usage = json.loads(err)
        assert rc == 0
        assert result["schema_version"] == "earnings-transcript-result/2"
        assert result["status"] == "not_found"
        assert result["error_code"] == expected_code
        assert result["candidate_count"] == 0
        assert "provider_payload_base64" not in result
        assert usage["schema_version"] == "earnings-retrieval-usage/1"
        assert usage["request_id"] == request["request_id"]
        assert usage["usage_complete"] is True
        assert usage["usage"]["requests_used"] == 1
        assert usage["usage"]["response_bytes_used"] == len(payload)
        assert len(get_urls(calls_file)) == 1
        assert all(not envelope["translator_loaded"] for envelope in envelopes(calls_file))
        assert list(temp_root.iterdir()) == []
        assert E2E_KEY not in out + err
'''
cli_path.write_text(cli, encoding='utf-8', newline='\n')
with (TREE / '.planning/w06-cutoff-result/progress.md').open('a', encoding='utf-8') as stream:
    stream.write('\nA：责任测试已写；强化原两个断言，新8组单元正负控和真实worker双provider诊断/usage/cleanup。尚未运行RED，未改产品。\n')
print(json.dumps({'test_files_written': 2, 'product_files_written': 0}))
