"""Actual owned-lake finalization must survive accounting failure without POST."""
from pathlib import Path
import json
from decimal import Decimal

import pytest

from tools.document_understanding_benchmark import phase_c_runner as runner


@pytest.mark.parametrize('posted_event', [False, True])
@pytest.mark.parametrize('hold_storage_fails', [False, True])
def test_accounting_exception_cannot_skip_actual_owned_lake_cleanup(tmp_path, monkeypatch, posted_event, hold_storage_fails):
    monkeypatch.setattr(runner.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(runner, "seed_identity", lambda *args, **kwargs: {})
    real_cli = runner._cli
    owned = []

    def no_model_cli(root, output, label, command, env, **kwargs):
        if label == "import":
            return real_cli(root, output, label, command, env, **kwargs)
        owned.append(Path(root))
        database = Path(command[command.index("--automation-db") + 1])
        database.parent.mkdir(parents=True, exist_ok=True)
        database.touch()
        if posted_event:
            # Simulate an already-sent operation; the test never makes HTTP.
            (output / 'events.jsonl').write_text(json.dumps({'event': 'http_post_attempt'})+'\n', encoding='utf-8')
        return 2, {"status": "failed"}, "", ""

    monkeypatch.setattr(runner, "_cli", no_model_cli)

    def accounting_failed(*args, **kwargs):
        raise OSError("injected native usage persistence failure")

    monkeypatch.setattr(runner, "append_native", accounting_failed)
    if hold_storage_fails:
        write_json = runner.write_json

        def fail_only_hold(path, value):
            if path.name.endswith('.accounting-hold.json'):
                raise OSError('injected hold storage failure')
            return write_json(path, value)

        monkeypatch.setattr(runner, 'write_json', fail_only_hold)
    metadata = runner.loopback_preparation()
    provider = next(row for row in metadata["providers"] if row["provider"] == "deepseek")
    output = tmp_path / "receipts"
    output.mkdir()
    result = runner.run_pair({"sample_id": "loopback-fixture"}, provider, metadata, mode="loopback", output=output,
        fixture_endpoint="http://127.0.0.1:1/chat/completions", selected_versions="0.9.0")
    assert owned and all(not path.exists() for path in owned)
    assert not list(tmp_path.glob("cwplC-*"))
    assert result["status"] == "FAIL" and result["temporary_lake_removed"] is True
    assert result["finalization_error"] == "OSError"
    assert result["model_post_attempts"] == int(posted_event)
    assert (output / "receipt.json").is_file()
    assert result['native_usage_reconciliation_required'] is True
    if hold_storage_fails:
        assert result['native_usage_hold_saved'] is False
        assert result['accounting_hold_error'] == 'OSError'
        return
    held = json.loads((output / (result['native_usage_run_id'] + '.accounting-hold.json')).read_text(encoding='utf-8'))
    assert held['usage_status'] == 'unknown'
    assert held['charged_tokens'] == metadata['candidate_per_paid_request_limits']['max_tokens']
    assert held['charged_micro_usd'] == int(Decimal(metadata['candidate_per_paid_request_limits']['max_cost_usd']) * 1_000_000)
    assert result['native_usage_hold_saved'] is True


def test_mother_uses_full_run_hold_without_double_counting_partial_native_rows(tmp_path):
    metadata = tmp_path / 'metadata.json'
    ledger = tmp_path / 'usage.jsonl'
    metadata.write_text(json.dumps({'mother_budget': {'prior_charged_tokens': 10,
        'prior_charged_micro_usd': 20, 'retained_fx_hold_micro_usd': 0,
        'old_unknown_hold_count_already_in_baseline': 0}}), encoding='utf-8')
    actual = {'kind': 'native_model_charge', 'mode': 'live', 'database': 'owned/AUTO.sqlite',
        'run_id': 'run-1', 'attempt_id': 'actual-attempt', 'usage_status': 'known',
        'charged_tokens': 40, 'charged_micro_usd': 50}
    hold = {**actual, 'attempt_id': 'run-1:accounting-unknown', 'accounting_hold_for_run': 'run-1',
        'usage_status': 'unknown', 'charged_tokens': 100, 'charged_micro_usd': 200}
    ledger.write_text('\n'.join(json.dumps(r) for r in [actual, hold, hold])+'\n',encoding='utf-8')
    held = runner.mother_totals(metadata, ledger)
    assert (held['charged_tokens'], held['charged_micro_usd']) == (110, 220)
    assert held['new_unknown_count'] == 1
    with ledger.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps({**hold, 'usage_status': 'known', 'charged_tokens': 0,
                                'charged_micro_usd': 0})+'\n')
    settled = runner.mother_totals(metadata, ledger)
    assert (settled['charged_tokens'], settled['charged_micro_usd']) == (50, 70)
    assert settled['new_unknown_count'] == 0


def test_real_append_reconciles_same_fallback_key_after_native_rows_are_durable(tmp_path, monkeypatch):
    from dataclasses import dataclass
    import sqlite3
    from types import SimpleNamespace
    from company_wiki.automation import narrative_run_store

    database = tmp_path / 'AUTO.sqlite'
    with sqlite3.connect(database) as db:
        db.execute('CREATE TABLE attempts(attempt_id,job_id,outcome,error_code,error_detail,result_json)')
        db.execute('CREATE TABLE narrative_run_jobs(job_id,run_id)')
    output = tmp_path / 'out'
    output.mkdir()
    ledger = tmp_path / 'usage.jsonl'
    monkeypatch.setattr(runner, 'USAGE', ledger)
    runner._preserve_accounting_hold(database, 'run-1', output, 'live',
                                    {'max_tokens': 100, 'max_cost_usd': '0.000200'})

    @dataclass
    class KnownReservation:
        attempt_id: str = 'actual-attempt'
        run_id: str = 'run-1'
        usage_status: str = 'known'
        charged_tokens: int = 40
        charged_micro_usd: int = 50

    monkeypatch.setattr(narrative_run_store, 'NarrativeRunStore',
                        lambda path: SimpleNamespace(reservations_for_run=lambda run: [KnownReservation()]))
    runner.append_native(database, 'run-1', output, 'live')
    runner.append_native(database, 'run-1', output, 'live')
    rows = runner.read_rows(ledger)
    holds = [row for row in rows if row.get('accounting_hold_for_run')]
    assert len(rows) == 3  # original hold, exact native charge, same-key release; no replay duplicates
    assert holds[0]['attempt_id'] == holds[1]['attempt_id']
    assert holds[0]['usage_status'] == 'unknown' and holds[1]['usage_status'] == 'known'
    assert holds[1]['charged_tokens'] == holds[1]['charged_micro_usd'] == 0
    assert (output / 'run-1.native-usage.json').is_file()


def test_live_mother_hold_survives_diagnostic_sidecar_write_failure(tmp_path, monkeypatch):
    ledger = tmp_path / 'usage.jsonl'
    monkeypatch.setattr(runner, 'USAGE', ledger)
    output = tmp_path / 'output'
    output.mkdir()
    monkeypatch.setattr(runner, 'write_json', lambda *args, **kwargs: (_ for _ in ()).throw(OSError('sidecar denied')))
    saved = runner._preserve_accounting_hold(tmp_path / 'gone/AUTO.sqlite', 'run-1', output, 'live',
                                            {'max_tokens': 100, 'max_cost_usd': '0.000200'})
    assert saved['ledger_saved'] is True and saved['sidecar_saved'] is False
    row, = runner.read_rows(ledger)
    assert row['usage_status'] == 'unknown'
    assert (row['charged_tokens'], row['charged_micro_usd']) == (100, 200)


def test_reconcile_after_cleanup_uses_durable_native_journal_without_database(tmp_path, monkeypatch):
    import subprocess
    import sys
    database = tmp_path / 'already-removed/AUTO.sqlite'
    output = tmp_path / 'output'
    output.mkdir()
    ledger = tmp_path / 'usage.jsonl'
    monkeypatch.setattr(runner, 'USAGE', ledger)
    row = {'kind': 'native_model_charge', 'mode': 'live', 'database': str(database),
        'run_id': 'run-1', 'attempt_id': 'actual-attempt', 'usage_status': 'known',
        'charged_tokens': 40, 'charged_micro_usd': 50}
    journal = output / 'run-1.native-usage.json'
    journal.write_text(json.dumps([row]), encoding='utf-8')
    runner._preserve_accounting_hold(database, 'run-1', output, 'live',
                                    {'max_tokens': 100, 'max_cost_usd': '0.000200'})
    original = journal.read_bytes()
    # Real CLI restart; no AUTO DB, HTTP endpoint, original file or model credentials.
    for _ in range(2):
        result = subprocess.run([sys.executable, str(Path(runner.__file__)), '--mode', 'live',
            '--output', str(output), '--usage-ledger', str(ledger), '--reconcile-run-id', 'run-1'],
            capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stdout + result.stderr
    assert not database.parent.exists() and journal.read_bytes() == original
    rows = runner.read_rows(ledger)
    assert len(rows) == 3
    assert rows[-1]['accounting_hold_for_run'] == 'run-1'
    assert rows[-1]['usage_status'] == 'known'
    assert rows[-1]['charged_tokens'] == rows[-1]['charged_micro_usd'] == 0


def test_empty_usage_after_recorded_post_cannot_release_unknown_hold(tmp_path, monkeypatch):
    ledger = tmp_path / 'usage.jsonl'
    output = tmp_path / 'output'
    output.mkdir()
    monkeypatch.setattr(runner, 'USAGE', ledger)
    (output / 'run-1.native-usage.json').write_text('[]', encoding='utf-8')
    runner._preserve_accounting_hold(tmp_path / 'gone/AUTO.sqlite', 'run-1', output, 'live',
                                    {'max_tokens': 100, 'max_cost_usd': '0.000200'})
    (output / 'events.jsonl').write_text(json.dumps({'event': 'http_post_attempt', 'run_id': 'run-1'})+'\n', encoding='utf-8')
    before = ledger.read_bytes()
    with pytest.raises(ValueError, match='empty native usage after recorded POST'):
        runner.reconcile_native_usage(output, 'run-1')
    assert ledger.read_bytes() == before


@pytest.mark.parametrize('change', ['lower_values', 'empty', 'late_unbound'])
def test_replay_rejects_changed_or_unbound_usage_and_keeps_full_hold(tmp_path, monkeypatch, change):
    output = tmp_path / 'out'
    output.mkdir()
    ledger = tmp_path / 'usage.jsonl'
    monkeypatch.setattr(runner, 'USAGE', ledger)
    database = tmp_path / 'gone/AUTO.sqlite'
    row = {'kind': 'native_model_charge', 'mode': 'live', 'database': str(database),
        'run_id': 'run-1', 'attempt_id': 'actual-attempt', 'usage_status': 'known',
        'charged_tokens': 40, 'charged_micro_usd': 50}
    journal = output / 'run-1.native-usage.json'
    if change != 'late_unbound':
        journal.write_text(json.dumps([row]), encoding='utf-8')
    runner._preserve_accounting_hold(database, 'run-1', output, 'live',
                                    {'max_tokens': 100, 'max_cost_usd': '0.000200'})
    changed = [] if change == 'empty' else [{**row, 'charged_tokens': 1, 'charged_micro_usd': 1}]
    journal.write_text(json.dumps(changed), encoding='utf-8')
    before = ledger.read_bytes()
    with pytest.raises(ValueError, match='native usage journal (changed|has no bound)'):
        runner.reconcile_native_usage(output, 'run-1')
    assert ledger.read_bytes() == before
