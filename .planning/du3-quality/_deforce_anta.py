import json, pathlib, sys
sys.path.insert(0, '.')
from tools.document_understanding_benchmark.contamination import support_set_digest

p = pathlib.Path('tools/document_understanding_benchmark/gold/fresh-hk-anta-fy2025.json')
gold = json.loads(p.read_text(encoding='utf8'))

# Pure P&L lines that a financial API can supply are not forced into the summary
# (card rule); they stay correctness_if_emitted so a direction/unit trap is still
# checked *if* emitted. Operating volume / subject / brand facts stay required.
DEFORCE = {
    'anta-operating-profit-up',
    'anta-gross-margin-decline',
    'anta-shareholders-profit-decline',
}
for fact in gold['facts']:
    if fact['id'] in DEFORCE:
        fact['target_kind'] = 'correctness_if_emitted'
        fact.setdefault('classification_reason',
                        '一般财务/损益数值可由财务API替代，不强制进入摘要；'
                        '若摘要输出仍必须核验方向、单位、期间与出处。')

gold['notes'] = gold['notes'] + (
    ' 分级规则：一般损益/财务数值（经营溢利、毛利率、股東應佔溢利、收入）标 correctness_if_emitted，'
    '不强制摘要但若输出须核验方向/单位/期间；经营量（存貨周轉日數）、主体（Amer Sports）、'
    '品牌组合与风险/口径限定保留 required_business。'
)
gold['support_set_digest'] = support_set_digest(gold)
p.write_text(json.dumps(gold, ensure_ascii=False, indent=2) + '\n', encoding='utf8')
print('de-forced:', sorted(DEFORCE))
print('new digest:', gold['support_set_digest'][:16])
print('required_business facts:', [f['id'] for f in gold['facts'] if f['target_kind'] == 'required_business'])
