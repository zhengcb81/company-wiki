from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')

path = ROOT / 'tools/pre_push_gate.py'
body = path.read_text(encoding='utf-8')
anchor = '    "tests/test_m3_evidence_roles.py",'
assert anchor in body and 'test_w05_root_temporal_lineage.py' not in body
body = body.replace(anchor, anchor + '\n' + '\n'.join(
    '    "tests/' + name + '",' for name in (
        'test_w05_dated_contribution_contract.py',
        'test_w05_dated_contribution_composition.py',
        'test_w05_dated_contribution_output.py',
        'test_w05_root_temporal_lineage.py',
        'test_mixed_aggregate_recognition.py',
    )))
path.write_text(body, encoding='utf-8')

path = ROOT / 'SKILL.md'
body = path.read_text(encoding='utf-8')
old = 'Full-year claims must be exact compositions of non-overlapping windows or carry an explicit rationale (口径解释)'
new = ('Full-year claims must preserve actual input windows and temporal lineage through derived aliases, '
       'including annual wrappers. A rationale (口径解释) may explain a real perimeter gap, independent '
       'business scopes or a residual subtraction; it never permits changing known dates or summing '
       'the same economic flow twice')
assert old in body
path.write_text(body.replace(old, new), encoding='utf-8')

path = ROOT / 'references/input-construction.md'
body = path.read_text(encoding='utf-8')
start = body.index('- Full-year honesty: a derived `period_flow`')
end = body.index('\n- ', start + 3)
old = body[start:end]
new = '''- A derived `period_flow`, or an `annual` derived wrapper with a dated ancestor,
  must preserve its actual nonzero formula inputs and their original temporal
  lineage. Every contributing input window stays inside the result window.
  A full-year bridge needs complete coverage or a rationale for a real perimeter
  gap. A rationale may explain disjoint business scopes or residual subtraction,
  but cannot relocate a 2026 amount into 2027 or add H1 and its own Q2. Renaming
  a derived output does not erase the original input identity/scope. Group total
  and included subsidiary revenue cannot be added; reconstruct a documented
  residual first. Stock/rate inputs alone do not establish a recognized flow.'''
assert 'rationale' in old
path.write_text(body[:start] + new + body[end:], encoding='utf-8')

path = ROOT / 'tests/test_w05_dated_contribution_contract.py'
body = path.read_text(encoding='utf-8')
body = body.replace('Fixture amounts are synthetic except the sealed control-window fact above.',
                    'Generic arithmetic fixtures are synthetic. The native C1 E2E separately preserves\n'
                    'the sealed CNY amount and dates within an entirely CNY synthetic fixture.')
body = body.replace('# Sealed counterexample: purchase date 2026-05-31, purchase-to-end\n'
                    '        # revenue 1,291,902.08 CNY (1.29190208 CNY million).',
                    '# Synthetic numeric/date regression inspired by the sealed control window;\n'
                    '        # the full native C1 E2E preserves the original CNY unit separately.')
path.write_text(body, encoding='utf-8')

path = ROOT / 'tests/test_w05_root_temporal_lineage.py'
body = path.read_text(encoding='utf-8')
assert 'test_point_stock_alone_cannot_be_retyped_as_dated_recognized_revenue' not in body
body += '''\n\ndef test_point_stock_alone_cannot_be_retyped_as_dated_recognized_revenue():
    data = schema_3_10_document()
    add_window_parameter(data, "closing_stock", 20.0, None, None, 2026,
                         time_basis="point_in_time", definition="Closing receivable balance")
    parameter(data, "closing_stock")["dimension"] = "monetary_balance"
    add_window_parameter(data, "fake_flow_from_stock", 20.0, "2026-01-01", "2026-12-31", 2026,
                         kind="derived_fact", claim=False, formula="x0", input_parameter_ids=["closing_stock"],
                         rationale="The balance is relabeled as recognized flow")
    with pytest.raises(ForecastInputError, match="flow-bearing"):
        run_forecast(data)
'''
path.write_text(body, encoding='utf-8')
print('Applied bounded gate/docs/stock RED additions; no commit')
