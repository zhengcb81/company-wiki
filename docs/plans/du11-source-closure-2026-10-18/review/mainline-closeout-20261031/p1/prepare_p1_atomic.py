"""Frozen DEVELOPMENT gold adapter; never changes a production reader/oracle.

Original C3 checkpoints remain authoritative human-reviewed composite meanings.
Each explicit subproposition is still checked within ONE real source closure;
the parent only passes when ALL its subpropositions pass. Background anchors
remain in the original source appendix, rather than becoming accidental ANDs.
No grouping is learned from model output and no API is called here.
"""
from pathlib import Path
import copy
import datetime
import hashlib
import json
import sys

ROOT = Path.cwd()
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT / 'scripts')]
from tools.document_understanding_benchmark import phase_c_runner as runner
from tools.document_understanding_benchmark.records import validate_gold

W = ROOT / '.planning/mainline-closeout-20261031'
D = W / 'p1-preparation-v5'


def paras(page, first, last):
    return [f'p{page}-paragraph{i}' for i in range(first, last + 1)]


# An explicit reviewed fixture, not production company-dependent logic.
PARTS = {
    'HUALI-02': [(paras(1, 14, 24), 'Brand-specific destocking affected H2/Q4 2022 and Q1 2023 shipments; only some brands expected Q2 improvement.')],
    'HUALI-04': [
        (paras(1, 33, 38) + paras(2, 0, 0), 'Some urgent additional orders can be delivered in 2-3 weeks; this is not every order.'),
        (paras(1, 33, 33) + paras(2, 1, 2), 'No urgent-order price increase; urgent orders increase revenue scale and can benefit scale efficiency.'),
    ],
    'HUALI-06': [
        (paras(2, 9, 12), 'New/existing customer order discussions drive flexible capacity planning and planned active expansion.'),
        (paras(2, 9, 9) + paras(2, 13, 17), 'Buying land and building is one expansion method; only AFTER land formalities, construction to acceptance requires 1-2 years, not an order lead time or completed plant.'),
    ],
    'HUALI-07': [(paras(2, 18, 18) + paras(2, 20, 27), 'Indonesia phases I and II total expected capacity 50-60 million pairs/year; phase I expected to begin in 2023; both phased, conditioned on orders, construction, local approval. Prior controller/staff experience is not company completed output.')],
    'HUALI-08': [
        (paras(2, 28, 34), 'HK trade subsidiaries use USD financial statements and settlements; mainland company/entities use RMB with some foreign-currency assets/liabilities.'),
        (paras(2, 28, 28) + paras(2, 35, 41), 'Overseas subsidiaries use local currencies; FX changes affect foreign assets/liabilities. 2022 gain RMB82 million versus Q1 2023 approximate LOSS RMB35 million, small proportion of current profit.'),
    ],
    'BRK-05': [
        (paras(6, 1, 1), 'PacifiCorp wind capacity was 33 MW at 2006 purchase and now 794 MW, not employees or incremental annual MW.'),
        (paras(6, 2, 2), 'MidAmerican spent $1.8 billion on wind in 2008 at TWO operations, not PacifiCorp alone.'),
    ],
    'BRK-08': [
        (paras(7, 5, 5), 'GEICO AUTO insurance market share 7.7%, up from 7.2% in 2007; not premium growth or all Berkshire insurance.'),
        (paras(7, 6, 6), 'GEICO new business and better existing-business renewals moved it to number three among auto insurers.'),
    ],
    # p7/8 supplies GEICO and Jan/Feb2009 for the we/our/last-year paragraph.
    # It must be in the SAME actual closure, not merely elsewhere in the input.
    'BRK-09': [(paras(7, 8, 9), 'GEICO motorcycle policies grew 23.4% in 2008; share about 6% to over 7%; RV/ATV grew from SMALL BASE and commercial autos RECENTLY began; p7/8 binds the owner and 2009 narration, not consolidated revenue growth or a new standalone Berkshire segment.')],
}


def main():
    D.mkdir(exist_ok=True)
    assert not any(D.iterdir()), 'do not overwrite previous preparation'
    old = W / 'p1-preparation-v3'
    meta = json.loads((old / 'metadata.json').read_text(encoding='utf-8'))
    original_root = ROOT / 'docs/plans/du11-source-closure-2026-10-18/review/pdf-c3-20261026/holdout'
    bridge = []
    for sample in meta['samples']:
        original_path = original_root / (sample['sample_id'] + '.gold.json')
        original = json.loads(original_path.read_text(encoding='utf-8'))
        old_gold = json.loads(Path(sample['gold']).read_text(encoding='utf-8'))
        supports = {s['support_id']: s for s in original['support_units']}
        cp_by_id = {cp['checkpoint_id']: cp for cp in original['checkpoints']}
        facts, parents = [], []
        for original_fact in old_gold['facts']:
            cp_id = original_fact['id']
            cp = cp_by_id[cp_id]
            original_ids = {sid for group in cp['required_support_sets'] for sid in group}
            parts = PARTS.get(cp_id)
            ids = []
            if parts is None:
                facts.append(copy.deepcopy(original_fact)); ids.append(cp_id)
            else:
                for index, (support_ids, meaning) in enumerate(parts, 1):
                    assert support_ids and len(support_ids) == len(set(support_ids))
                    assert set(support_ids) <= original_ids, (cp_id, support_ids)
                    fact = copy.deepcopy(original_fact)
                    fact['id'] = cp_id + f'.A{index}'
                    fact['any_support_sets'] = [[{'page': supports[sid]['locator']['page_number'], 'exact_quote': supports[sid]['quote']} for sid in support_ids]]
                    fact['must_preserve'] = [meaning]
                    fact['reason'] = f'Atomic subproposition of original {cp_id}; parent requires ALL atoms, full original meaning/quotes preserved in bridge.'
                    facts.append(fact); ids.append(fact['id'])
            parents.append({'checkpoint_id': cp_id, 'required_fact_ids': ids, 'aggregation': 'ALL', 'original_checkpoint': cp, 'target_kind': original_fact['target_kind']})
        converted = {**old_gold, 'facts': facts, 'notes': 'DEVELOPMENT, exposed source diagnostic. Atomic reviewed adapter; never blind. See gold-bridge.json for unchanged original checkpoints and anchors.'}
        validate_gold(converted)
        gold_path = D / (sample['sample_id'] + '.gold.json')
        runner.write_json(gold_path, converted)
        sample['gold'] = str(gold_path)
        if sample['registered_source_facts']['facts']['security_id'] is None:
            sample['verified_official_descriptor']['security_id'] = None
        meta['protected_fingerprints'][str(gold_path)] = runner.fingerprint(gold_path)
        bridge.append({'sample_id': sample['sample_id'], 'original_gold_path': str(original_path), 'original_gold_sha256': hashlib.sha256(original_path.read_bytes()).hexdigest(), 'original_support_units': original['support_units'], 'original_source_identity': original['source_identity'], 'parents': parents, 'converted_gold_sha256': runner.fingerprint(gold_path)['sha256']})
    meta['preparation_revision'] = 'M8-P1-atomic-reviewed-source-gold-v5'
    meta['observed_at'] = datetime.datetime.now(datetime.UTC).isoformat()
    meta['status'] = 'FROZEN_FREE_PREFLIGHT_AND_INDEPENDENT_REVIEW_BEFORE_POST'
    runner.write_json(D / 'gold-bridge.json', bridge)
    meta['source_gold_bridge'] = str(D / 'gold-bridge.json')
    runner.write_json(D / 'metadata.json', meta)
    runner.verify_preparation(meta, mode='live')
    totals = runner.mother_totals(D / 'metadata.json', ROOT / '.planning/shared-reading-production/live/usage.jsonl')
    runner.write_json(D / 'mother-before.json', totals)
    print(json.dumps({'status': 'FROZEN_0_POST', 'original_checkpoints': sum(len(b['parents']) for b in bridge), 'original_anchors': sum(len(b['original_support_units']) for b in bridge), 'new_facts': [len(json.loads(Path(s['gold']).read_text(encoding='utf-8'))['facts']) for s in meta['samples']], 'mother': totals}))


if __name__ == '__main__':
    main()
