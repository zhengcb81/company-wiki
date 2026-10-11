from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
path = ROOT / 'scripts/contracts/annual_consumption.py'
body = path.read_text(encoding='utf-8')
start = body.index('"""')
end = body.index('"""', start + 3) + 3
body = body[:start] + '''"""Pure eligibility of parameters actually consumed by annual business roles.

This contract never annualizes amounts, infers dates or checks permissions.
Schema 3.10 derived annual-flow roots reuse the actual formula dimension/period
ancestry before accepting an outer annual label. Schema 3.9 retains its direct
window eligibility; old schemas retain legacy behavior. Partial flows remain
legal supporting facts but cannot directly serve a full-year consumer. Explicit
native stock/rate roles stay distinct from recognized amounts.
"""''' + body[end:]
path.write_text(body, encoding='utf-8')
path = ROOT / 'references/dated-contribution.md'
body = path.read_text(encoding='utf-8')
anchor = '\n## Annual consumers, kinds, units\n'
assert anchor in body
addition = '''
## Actual type ancestry, including annual-only aliases (ROOT P1 follow-up)

Schema 3.10 checks the actual formula, not just an output's `annual` label.
`validate_derived_flow_ancestry` is shared by derived revenue composition and
actual annual-flow consumer roots. It recursively preserves original units and
period meaning through aliases, ratios, multiplication and division:

* A money balance, point quantity, scalar or ratio cannot be renamed annual
  recognized revenue. An unused or zero-multiplied income input cannot justify
  adding an untyped literal amount. Stock and period money cannot simply be
  added, even when one amount is zero.
* `flow * (stock / flow)` is still stock; an intermediate `ratio` label does not
  erase the inverse period meaning. Conversely an actual annual turnover
  `flow / stock` may multiply a stock to form a period amount. A derived price
  `annual income / point customers` preserves annual ARPU; `money stock / point
  customers` remains a stock-per-unit value and cannot become annual ARPU.
* Point operating quantity times a raw annual per-unit price/ARPU is allowed when
  units match. Raw annual per-unit/activity/area prices can be transaction prices
  or annual operating rates; the formula's matched quantity and real source/native
  model establish the business interpretation. Derived prices keep their actual
  origin and cannot acquire a period simply by changing metadata.
* Existing native subscription, bank, asset-management and stock-flow models
  retain their explicit driver roles. Generic stock/flow additions should use
  those native bridges. Arbitrary dated stock-pricing expressions are not a dated
  sum of evidenced contribution amounts; model the contribution and its real
  interval explicitly. The date containment/coverage owner is unchanged.

This is mathematical precondition validation, with no new fields, flags, identity
registry, authorization or repeated human review. Schema 3.9 and earlier keep
their established behavior. It cannot establish economic truth of independently
authored source facts, or choose a real business scope from free text alone.
'''
body = body.replace(anchor, '\n' + addition + anchor)
path.write_text(body, encoding='utf-8')
path = ROOT / 'SKILL.md'
body = path.read_text(encoding='utf-8')
anchor = 'Reports show real window dates, amounts and sources;'
assert anchor in body
body = body.replace(anchor, 'Derived annual revenue must also preserve actual unit/period ancestry: stock, scalar or ratio aliases cannot become recognized income; use genuine annual ARPU/turnover or an explicit native stock-flow model. ' + anchor, 1)
path.write_text(body, encoding='utf-8')
path = ROOT / 'references/input-construction.md'
body = path.read_text(encoding='utf-8')
anchor = '  shared original leaf.\n'
if anchor in body:
    body = body.replace(anchor, anchor + '  An annual label also preserves actual unit/period ancestry; it cannot cast a\n  point monetary stock, scalar or ratio into revenue. Use a genuine annual\n  operating price/ARPU, recomputable turnover or the existing explicit native\n  stock-flow model.\n', 1)
else:
    anchor = '  residual first. Stock/rate inputs alone do not establish a recognized flow.\n'
    assert anchor in body
    body = body.replace(anchor, anchor + '  Derived annual aliases follow the same actual unit/period ancestry, including\n  ratios and inverse-period conversions; use genuine annual ARPU/turnover or a\n  native stock-flow model rather than changing metadata.\n', 1)
path.write_text(body, encoding='utf-8')
path = ROOT / 'CHANGELOG.md'
body = path.read_text(encoding='utf-8')
anchor = '\n'
line = 'ROOT P1 follow-up: schema 3.10 now preserves actual formula dimension and period algebra through annual aliases, ratio cancellation, price/ARPU and turnover conversions; shared annual consumers reject stock/rate/scalar laundering while native business roles and schema 3.9 remain unchanged.\n'
body = body.replace(anchor, anchor + line, 1)
path.write_text(body, encoding='utf-8')
print('Updated mathematical contract and author guidance; no new gate/field/install')
