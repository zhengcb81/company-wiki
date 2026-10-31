"""Post-review gold corrections (independent review OPEN-5). See gold.json
post_review_corrections for scope; engines are not re-run."""
import json
from pathlib import Path

p = Path(r'docs/plans/w23-xiaomi-ocr-2026-10-30/gold.json')
g = json.loads(p.read_text(encoding='utf-8'))


def move_footer_number_to_end(text, number):
    marker = "\n" + number + "\n"
    if marker in text:
        return text.replace(marker, "\n", 1).rstrip() + "\n" + number + "\n"
    return text


fixes = {
    'byd_ar_2024_p021': ('22', 'page footer number 22 placed at reading-order end (post-review reposition)'),
    'byd_ar_2024_p022': ('23', 'page footer number 23 placed at reading-order end (post-review reposition)'),
    'amec_h1_2026_p009': ('10 / 210', "page footer '10 / 210' placed at reading-order end (post-review reposition)"),
    'amec_h1_2026_p011': ('12 / 210', "page footer '12 / 210' placed at reading-order end (post-review reposition)"),
    'hrjp_cb_prospectus_p006': ('6', 'page footer number 6 placed at reading-order end (post-review reposition)'),
    'hrjp_cb_prospectus_p037': ('37', 'page footer number 37 placed at reading-order end (post-review reposition)'),
}
for pid, (num, new_note) in fixes.items():
    page = g['pages'][pid]
    page['full_text'] = move_footer_number_to_end(page['full_text'], num)
    page['corrections'] = [new_note if 'page footer' in c else c for c in page['corrections']]

for pid in ('byd_ar_2024_p021', 'byd_ar_2024_p022'):
    t = g['pages'][pid]['full_text']
    if '\uf052' in t:
        g['pages'][pid]['full_text'] = t.replace('\uf052', '☑')
        g['pages'][pid].setdefault('post_review_corrections', []).append(
            'PUA \uf052 glyph from the native layer replaced with U+2611 (visually the checked box)')

for pid in ('bili_call_4q22_en_p001', 'bili_call_4q22_en_p003'):
    t = g['pages'][pid]['full_text']
    if '\x02' in t:
        g['pages'][pid]['full_text'] = t.replace('\x02', '-')
        g['pages'][pid].setdefault('post_review_corrections', []).append(
            'U+0002 control chars from the native soft-hyphen extraction replaced with the visible hyphen (-)')

g['post_review_corrections'] = {
    'date': '2026-10-31',
    'trigger': 'independent review finding (delivery/w23-xiaomi-ocr/review_independent.md OPEN-5)',
    'scope': 'character-level only: 2x U+0002 -> "-", 2x PUA \uf052 -> U+2611, 6 page footer numbers repositioned to reading-order end',
    'engines': 'NOT re-run; raw engine outputs unchanged; evaluation recomputed against the corrected gold from the re-run records',
    'fairness': 'corrections apply equally to every arm, <=2 chars/page, no engine favored',
}
p.write_text(json.dumps(g, ensure_ascii=False, indent=1), encoding='utf-8')

g2 = json.loads(p.read_text(encoding='utf-8'))
bad = [pid for pid, pg in g2['pages'].items() if '\x02' in pg['full_text'] or '\uf052' in pg['full_text']]
print('remaining control/PUA:', bad)
print('footer-at-end:', {pid: g2['pages'][pid]['full_text'].rstrip().endswith(num) for pid, (num, _) in fixes.items()})
