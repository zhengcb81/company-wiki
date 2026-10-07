"""Quality-node IR and unchanged TXT through the existing formal business path."""

import hashlib
import json
import os

import pytest

from integration import test_n6_business_cli_e2e as business


loopback_model_server = business.loopback_model_server
protected_inputs = business.protected_inputs


@pytest.mark.real_data
@pytest.mark.e2e
def test_real_ir_parser_cli_quality_node(tmp_path_factory, loopback_model_server,
                                        monkeypatch, protected_inputs):
    if os.environ.get('CWP_S7_RUN_IR_E2E') != '1':
        pytest.skip('only run at the grouped S7 IR parser quality node')

    def sources(_real):
        register = json.loads((business.REPO / 'benchmarks/narrative_document_types/samples.json')
                              .read_text(encoding='utf-8'))['samples']
        chosen, originals, raw_by_sample = [], [], {}
        for sample in register:
            sid = sample['sample_id']
            if sid not in {'S07', 'S08', 'S09'}:
                continue
            root = (business.REPO if sample['root_key'] == 'company_raw' else
                    business.REPO.parent / 'earnings-transcripts/earnings-transcripts/transcripts')
            path = root / sample['relative_path']
            raw = path.read_bytes()
            assert hashlib.sha256(raw).hexdigest() == sample['sha256']
            chosen.append((sample['language'], sid + path.suffix, sample['title'],
                           sample['existing_kind'], raw))
            originals.append(path)
            raw_by_sample[sid] = raw
        assert len(chosen) == 3
        return chosen, originals, raw_by_sample

    monkeypatch.setattr(business, '_sources', sources)
    business._exercise(tmp_path_factory, loopback_model_server, monkeypatch,
                       protected_inputs, real=True,
                       probes={'S07': {'G-S07-01', 'G-S07-02'},
                               'S08': {'G-S08-01'}, 'S09': {'G-S09-05'}},
                       negative_probes={'S08': {'G-S08-05', 'G-S08-06'}},
                       queries={'S07': '中试线', 'S08': '黄金占比', 'S09': 'available capacity'})
