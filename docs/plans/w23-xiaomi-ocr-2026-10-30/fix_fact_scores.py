"""Fix fact_scores accounting per independent review OPEN-3."""
import json
from pathlib import Path

p = Path(r'delivery/w23-xiaomi-ocr/fact_scores.json')
d = json.loads(p.read_text(encoding='utf-8'))
d['method'] = d['method'].replace(
    '.w23_cache/r0_outputs', 'delivery/w23-xiaomi-ocr/raw_r0.json (per-page text field)')

d['eval_pages']['ksy_q1_2026_p002']['facts'] = {
    'hit': 6, 'partial': 2, 'miss': 0,
    'notes': ('F0 partial (納斯達克→斯逹克); F2 partial because R0 outputs 392.01百萬美元 — '
              'same superscript-footnote merge as the native layer; gold is 392.0. '
              'All other numeric facts (2,703.7 / 37.2% / 2.1% / 351.4 / 7.2% / 27.6% / 11.4 / 30億 / '
              '1,996.3 / 289.4 / 47.5% / 4.9% / 707.4 / 102.6 / 14.7% / 17.6% / 6.8980) present'),
}
d['eval_pages']['ir_wanrun_20241104_p000']['conditions'] = {
    'hit': 0, 'partial': 0, 'miss': 0,
    'notes': ('gold has no condition entries on this page; the checked-checkbox-state loss is '
              'accounted in facts F0 partial, not double-counted here'),
}
d['eval_pages']['bili_call_4q22_en_p001']['facts'] = {
    'hit': 5, 'partial': 4, 'miss': 1,
    'notes': ('F0 partial (opening line Thank you, Juliet… lost; on behalf of Mr. Chen present); '
              'F4 partial (96 minutes present, up 51% lost as garbage - q d o o); '
              'F5 partial (6.1 billion present, RMB 21.9 billion line lost); '
              'F7 partial (30%→21% present, cut S&M by 28% lost as fragment s); '
              'F8 miss (narrowed by 21%/26% quarter line lost as - - t q p); '
              'F1/F2/F3/F6/F9 hit (gross margin 20%/18% present, order scrambled across the page)'),
}
d['holdout_pages']['bili_call_4q22_en_p003']['facts'] = {
    'hit': 6, 'partial': 3, 'miss': 1,
    'notes': ('F1 partial (up 24% and 26% after RMB8.7 billion lost); '
              'F3 partial (hosts 70% read as 7o% — o-for-0; MPU 40% present but line tail cut); '
              'F9 partial (performance-based 50% read as 5o%); '
              'F6 miss (over 200 million views line lost; Yao-Chinese Folktale title present); '
              'F0/F2/F4/F5/F7/F8 hit (13%/21.9B/30%/21.4M/Three-Body/12%/5.1B/1.5B/verticals)'),
}
p.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding='utf-8')

# verify full accounting
gold = json.loads(Path(r'docs/plans/w23-xiaomi-ocr-2026-10-30/gold.json').read_text(encoding='utf-8'))
ok = True
for split in ('eval_pages', 'holdout_pages'):
    for pid, entry in d[split].items():
        nf = len(gold['pages'][pid].get('facts', []))
        nc = len(gold['pages'][pid].get('conditions', []))
        f = entry['facts']; c = entry['conditions']
        fa = f['hit'] + f['partial'] + f['miss']
        ca = c['hit'] + c.get('partial', 0) + c['miss']
        if fa != nf or ca != nc:
            ok = False
            print('MISMATCH', pid, fa, nf, ca, nc)
print('accounting complete:', ok)
tot = {'hit': 0, 'partial': 0, 'miss': 0}
c_tot = {'hit': 0, 'partial': 0, 'miss': 0}
for split in ('eval_pages', 'holdout_pages'):
    for pid, entry in d[split].items():
        for k in ('hit', 'partial', 'miss'):
            tot[k] += entry['facts'][k]
            c_tot[k] += entry['conditions'].get(k, 0)
print('facts totals:', tot, '| conditions totals:', c_tot)
