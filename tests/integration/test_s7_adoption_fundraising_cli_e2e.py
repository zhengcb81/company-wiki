"""Opt-in real adoption/project quality node; local model, committed RF only."""

import hashlib
import json
import os

import pytest

from integration import test_n6_business_cli_e2e as business


loopback_model_server = business.loopback_model_server
protected_inputs = business.protected_inputs


@pytest.mark.real_data
@pytest.mark.e2e
def test_real_adoption_fundraising_cli_quality_node(tmp_path_factory, loopback_model_server,
                                                   monkeypatch, protected_inputs):
    if os.environ.get('CWP_S7_RUN_PROJECT_E2E') != '1':
        pytest.skip('only run at the grouped S7 adoption/project quality node')

    def sources(_real):
        register = json.loads((business.REPO / 'benchmarks/narrative_document_types/samples.json')
                              .read_text(encoding='utf-8'))['samples']
        chosen, originals, raw_by_sample = [], [], {}
        for sample in register:
            sid = sample['sample_id']
            if sid not in {'S01', 'S04', 'S09'}:
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

    def inspect_spans(sid, spans):
        if sid != 'S04':
            return
        page = [s for s in spans if s.coordinates.page_number == 34]
        intro = [s for s in page if '投资于以下' in (s.raw_text or '')]
        assert intro, 'actual funding introduction must reach committed RF'
        group = (intro[0].structured_value or {}).get('selection_group_id')
        assert group and group.startswith('urn:company-wiki:fundraising-context:')
        linked = [s for s in page if (s.structured_value or {}).get('selection_group_id') == group]
        assert len(linked) == 4
        text = ''.join(s.raw_text or '' for s in linked)
        assert '高端半导体设备扩产升级项目' in text and '技术研发中心建设升级项目' in text
        assert '补充流动资金' not in text and '合计' not in text

    monkeypatch.setattr(business, '_sources', sources)
    business._exercise(tmp_path_factory, loopback_model_server, monkeypatch,
                       protected_inputs, real=True,
                       probes={'S01': {'G-S01-01', 'G-S01-02', 'G-S01-03', 'G-S01-04', 'G-S01-05'},
                               'S04': {'G-S04-03', 'G-S04-04'}, 'S09': {'G-S09-05'}},
                       negative_probes={'S04': {'G-S04-08'}}, inspect_spans=inspect_spans,
                       queries={'S01': '设备', 'S04': '募集资金', 'S09': 'available capacity'})
