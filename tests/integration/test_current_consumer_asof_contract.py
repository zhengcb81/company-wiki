"""Opt-in current downstream CLIs must share the producer publication cutoff."""
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from support.narrative_transport_fixture import published_fixture
from integration import test_narrative_batch_cli_e2e as cli
from tools.n4c_live_preflight import consumer_bootstrap


protected_inputs = cli.r6_protected_inputs
REPO = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('consumer', ['rf', 'stockwiki'])
@pytest.mark.parametrize('case', ['early_download', 'late_download', 'future_publication'])
def test_current_consumer_uses_publication_date_not_local_download_date(
    tmp_path, protected_inputs, consumer, case,
):
    rf = os.environ.get('CWP_RF_PROJECT_ROOT')
    sw = os.environ.get('CWP_STOCKWIKI_PROJECT_ROOT')
    if not rf or not sw:
        pytest.skip('explicit read-only RF and StockWiki roots required')
    rf_head = subprocess.check_output(
        ['git', '-C', rf, 'rev-parse', 'HEAD'], text=True, timeout=10,
    ).strip()
    protected_inputs([Path(rf)/'assurance/runs'/name for name in
                      ('daily_alert.jsonl', 'weekly_alert.jsonl', 'weekly_manifest.json')])
    with published_fixture(tmp_path, kind='txt', source_spec={'sidecar_overrides': {
        'fiscal_period': 'Q2',
        'filing_date': '2026-09-02' if case == 'future_publication' else '2026-08-01',
        'retrieved_at': '2026-09-02T00:00:00Z' if case == 'late_download' else '2026-08-02T00:00:00Z',
    }}) as fixture:
        env = {**os.environ, 'PYTHONPATH':os.pathsep.join([str(REPO/'src'), sw]),
               'PYTHONUTF8':'1', 'PYTHONDONTWRITEBYTECODE':'1', 'PYTHON_DOTENV_DISABLED':'1'}
        command = [sys.executable, '-B', '-m', 'company_wiki.source_catalog.narrative_transport_cli',
                   '--config', str(fixture.config_path)]

        def invoke(argv, request):
            return subprocess.run(argv, input=json.dumps(request).encode(), capture_output=True,
                                  env=env, cwd=fixture.root, timeout=60)

        discovery = invoke(command+['--operation','reference'], {
            'schema_version':'narrative-reference-request/1', 'source_ref':fixture.source_ref.to_dict()})
        assert discovery.returncode == 0, discovery.stderr
        request = {'schema_version':'narrative-read-request/1',
                   'narrative_ref':json.loads(discovery.stdout),'as_of_date':'2026-09-01',
                   'expected_source':dict(fixture.expected_source)}
        producer = invoke(command+['--operation','read'], request)
        if consumer == 'rf':
            exported = fixture.root/'rf'
            exported.mkdir()
            consumer_bootstrap(Path(rf), rf_head, exported)
            argv = [sys.executable, '-B', str(exported/'narrative_source_preparation.py'),
                    '--company-wiki-catalog-config', str(fixture.config_path)]
        else:
            config = fixture.root/'reader.json'
            config.write_text(json.dumps({'schema_version':'1.0','python_executable':sys.executable,
                'argv_prefix':command,'timeout_s':30,'max_stdout_bytes':1_310_720}), encoding='utf-8')
            request_file = fixture.root/'request.json'
            request_file.write_text(json.dumps(request), encoding='utf-8')
            argv = [sys.executable, '-B', '-m', 'stockwiki.cli', 'source-read-narrative',
                    '--request', str(request_file), '--reader-config', str(config)]
        downstream = invoke(argv, request)
        report_dir = os.environ.get('CWP_ASOF_REPORT_DIR')
        if report_dir:
            output = Path(report_dir)
            assert output.is_dir() and output.resolve().is_relative_to(REPO.resolve()/'tmp')
            report = {'consumer':consumer, 'case':case, 'as_of':request['as_of_date'],
                      'rf_export_head':rf_head,
                      'producer_code':producer.returncode,'consumer_code':downstream.returncode,
                      'producer_receipt':json.loads(producer.stderr),
                      'consumer_diagnostic':json.loads(downstream.stderr) if downstream.stderr else None}
            (output/f'{consumer}-{case}.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        expected = 2 if case == 'future_publication' else 0
        assert producer.returncode == expected, producer.stderr
        if expected == 0:
            body = json.loads(producer.stdout)
            assert body['versions']['parser'].endswith('0.1.1')
            assert body['versions']['selector'].endswith('0.4.2')
            assert json.loads(producer.stderr)['replay_status'] == 'verified'
        assert downstream.returncode == expected, (consumer, case, downstream.stderr)
        if expected == 0:
            view = json.loads(downstream.stdout)
            spans = view['evidence'] if consumer == 'stockwiki' else view['evidence_spans']
            assert spans == json.loads(producer.stdout)['evidence_spans']
        else:
            assert not downstream.stdout
