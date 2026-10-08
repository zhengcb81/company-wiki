from pathlib import Path

root = Path('C:/Users/郑曾波/Projects/revenue-forecast')
test = root / 'tests/test_mixed_aggregate_recognition.py'
text = test.read_text(encoding='utf-8')
text = text.replace('{c["claim_id"]: c for c in data["claims"]}', '{}')
test.write_text(text, encoding='utf-8')
old = root / 'tests/test_zr707_mixed_recognition.py'
text = old.read_text(encoding='utf-8')
assert 'assert PRESENTATIONS == {"gross", "net"}' in text
text = text.replace('assert PRESENTATIONS == {"gross", "net"}',
                    'assert PRESENTATIONS == {"gross", "net", "mixed"}')
old.write_text(text, encoding='utf-8')
reference = root / 'references/input-schema.md'
text = reference.read_text(encoding='utf-8')
anchor = '- Point-in-time `modeled_as_recognized`: modeled revenue is recognized directly.'
assert anchor in text
text = text.replace(anchor, anchor + '\n'
    '- Published aggregates may use `timing: mixed` and/or `presentation: mixed` only '
    'with `modeled_as_recognized` and `direct_growth` / `direct_revenue` in all scenarios. '
    '`modeled_presentation` must still match. Require a nonempty `aggregation_boundary` '
    'and recognition-policy claims explaining the component policies and unavailable split. '
    'These annual totals are already recognized: do not supply progress, lag, carry-in, '
    'or a second gross/net conversion. Use the ordinary single-policy fields when '
    'the underlying component is disclosed. Mixed is a disclosure limitation, not '
    'permission to treat activity measures as recognized revenue.')
reference.write_text(text, encoding='utf-8')
