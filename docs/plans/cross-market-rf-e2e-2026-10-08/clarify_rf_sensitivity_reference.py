from pathlib import Path

path = Path('C:/Users/郑曾波/Projects/revenue-forecast/references/input-schema.md')
text = path.read_text(encoding='utf-8')
anchor = '- `percent`, `percentage_point`, `basis_point`, or `absolute` with positive `shock_value`;'
assert text.count(anchor) == 1
addition = '''

Sensitivity units are numeric contract units, not the free-text test name:

- `percent`: multiplicative fractional change. `shock_value=0.05` means +/-5% of the parameter: `v +/- abs(v) * 0.05`. It does not mean 5 percentage points.
- `percentage_point`: additive change to a ratio stored as a fraction. For growth `v=0.38`, +/-5 percentage points requires `shock_value=0.05`, giving requested values `0.33` and `0.43`. `shock_value=5.0` means +/-500 percentage points, even if the name says "5pp".
- `basis_point`: one basis point is 0.0001; `shock_value=50` requests an additive ratio change of 0.005.
- `absolute`: use the parameter's declared unit and scale.

Check the requested and effective up/down parameter values against the intended unit before accepting the result. Bounds/clamping do not correct a unit error. Recomputing the same malformed input only verifies arithmetic consistency; it cannot prove the free-text name or economic intent is correct.
'''
assert 'Sensitivity units are numeric contract units' not in text
text = text.replace(anchor, anchor + addition)
path.write_text(text, encoding='utf-8')
