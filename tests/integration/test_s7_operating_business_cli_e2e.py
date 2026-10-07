"""Real affected originals through configured Worker, CWP and committed RF.

An opt-in quality-node test, never a daily CI job. All company metadata is the
existing isolated Acme fixture, while byte/quote/locator checks use real raws.
The three local HTTP responses are deterministic; no vendor or translation.
"""

import hashlib
import json
import os

import pytest

from integration import test_n6_business_cli_e2e as business


loopback_model_server = business.loopback_model_server
protected_inputs = business.protected_inputs


@pytest.mark.real_data
@pytest.mark.e2e
def test_real_operating_fact_cli_quality_node(tmp_path_factory, loopback_model_server,
                                            monkeypatch, protected_inputs):
    if os.environ.get('CWP_S7_RUN_REAL_E2E') != '1':
        pytest.skip('only run at the S7 grouped quality node')

    def sources(_real):
        register = json.loads((business.REPO / 'benchmarks/narrative_document_types/samples.json')
                              .read_text(encoding='utf-8'))['samples']
        chosen, originals, raw_by_sample = [], [], {}
        for sample in register:
            sid = sample['sample_id']
            if sid not in {'S01', 'S02', 'S06'}:
                continue
            assert sample['root_key'] == 'company_raw' and sample['source_format'] == 'pdf'
            path = business.REPO / sample['relative_path']
            raw = path.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == sample['sha256']
            chosen.append((sample['language'], sid + '.pdf', sample['title'],
                           sample['existing_kind'], raw))
            originals.append(path)
            raw_by_sample[sid] = raw
        assert len(chosen) == 3
        return chosen, originals, raw_by_sample

    monkeypatch.setattr(business, '_sources', sources)
    business._exercise(tmp_path_factory, loopback_model_server, monkeypatch,
                       protected_inputs, real=True,
                       probes={'S01': {'G-S01-02', 'G-S01-03', 'G-S01-05'},
                               'S02': {'G-S02-02', 'G-S02-03'},
                               'S06': {'G-S06-02', 'G-S06-04'}},
                       queries={'S01': '购买', 'S02': '客户', 'S06': '进口'})
