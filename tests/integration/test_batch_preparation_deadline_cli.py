"""Actual CLI time-budget admission, existing charges, and recoverable ownership."""
import json

import pytest

from company_wiki.automation.narrative_run_store import NarrativeRunStore
from integration import test_narrative_batch_cli_e2e as cli
from support.narrative_batch_fixtures import assert_originals_and_foreign_jobs_untouched, isolated_batch_directory


loopback_model_server = cli.loopback_model_server
protected_inputs = cli.r6_protected_inputs


@pytest.mark.parametrize('already_completed', [False, True])
def test_expired_real_cli_admission_preserves_sources_charges_and_releases_owner(
    tmp_path_factory, loopback_model_server, protected_inputs, already_completed,
):
    protected_inputs([])
    with isolated_batch_directory(tmp_path_factory) as root:
        state = cli._prepare(root, loopback_model_server.endpoint)
        try:
            originals = cli._originals(state)
            complete = None
            if already_completed:
                process, complete = cli._invoke(state)
                assert process.returncode == 0 and complete['status'] == 'completed'
                assert complete['budget']['tokens'] > 0
            before = tuple(state.store.list_jobs())
            calls = len(loopback_model_server.requests)
            launcher = root/'expire.py'
            launcher.write_text('''
from pathlib import Path
import time
from company_wiki.automation import narrative_batch as batch
from company_wiki.automation.narrative_batch_cli import main
original = batch.SourceVersionReader.open_version
trace = Path(__file__).with_name("opened.txt")
def open_then_expire(self, ref, **kwargs):
    with trace.open("a", encoding="utf-8") as out:
        out.write(ref.document_id + "\\n")
    result = original(self, ref, **kwargs)
    past = time.monotonic() + 120
    batch.time.monotonic = lambda: past
    return result
batch.SourceVersionReader.open_version = open_then_expire
if __name__ == "__main__":
    raise SystemExit(main())
''', encoding='utf-8')
            process, expired = cli._invoke(state, launcher=launcher)
            assert process.returncode == 2 and expired['status'] == 'failed'
            assert expired['error'] == 'BATCH_PREPARATION_DEADLINE_EXCEEDED'
            assert len((root/'opened.txt').read_text(encoding='utf-8').splitlines()) == 1
            assert tuple(state.store.list_jobs()) == before
            assert len(loopback_model_server.requests) == calls and not loopback_model_server.errors
            if already_completed:
                assert expired['budget'] == complete['budget']
            else:
                assert expired['budget'] == {'tokens':0, 'estimated_micro_usd':0,
                                             'unknown_reservations':0, 'unsettled_reservations':0}
                assert NarrativeRunStore(state.store.db_path).get_run('cli-e2e') is None
            # A normal retry proves that the same mutex/store were released;
            # an already-completed run must keep its exact finals and charges.
            process2, recovered = cli._invoke(state)
            assert process2.returncode == 0 and recovered['status'] == 'completed'
            if already_completed:
                assert recovered['documents'] == complete['documents']
                assert recovered['budget'] == complete['budget']
                assert len(loopback_model_server.requests) == calls
            assert_originals_and_foreign_jobs_untouched(state, originals,
                output=process.stdout + process.stderr + process2.stdout + process2.stderr)
            assert not json.loads(state.request_path.read_text(encoding='utf-8')).get('deadline')
        finally:
            state.catalog.close()
