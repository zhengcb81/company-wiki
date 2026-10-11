from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root').resolve()


def edit(relative, fn):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT) and path.is_file()
    old = path.read_text(encoding='utf-8')
    new = fn(old)
    assert new != old, relative
    path.write_text(new, encoding='utf-8')


edit('scripts/contracts/recognition.py', lambda text: text.replace(
    '    require(isinstance(recognition, dict), f"{name} requires recognition metadata")\n',
    '    require(isinstance(recognition, dict), f"{name} requires recognition metadata")\n    if not isinstance(recognition, dict):\n        return {}  # collect-all recorded the real shape error; never traverse None\n', 1))
edit('docs/handoffs/w05-rf-flow/e2e/read_and_tamper.py', lambda text: text.replace(
    '        forged["currency"] = "CNY"\n        print("tamper: currency -> CNY (rehashed)")',
    '        replacement = "USD" if forged["currency"] == "CNY" else "CNY"\n        forged["currency"] = replacement\n        print(f"tamper: currency -> {replacement} (rehashed)")', 1))

DOC = '''## Composition honesty (`validate_windowed_composition`, 3.10 only)

The same temporal rule checks derived `period_flow` and derived `annual`
wrappers with dated ancestors. Changing the outer time-basis or definition
cannot hide the period of the underlying amount:

* Actual nonzero formula operands must lie inside the composed window. An
  annual operand uses its actual FY window. `rationale` never exempts dates.
* Scalar/rate/price factors change amount, not time coverage. Unused or
  zero-weight operands never fill gaps. Date coverage follows the real formula.
* Positive overlapping additions of the same original flow or same source
  semantic definition are rejected even with explanation. Dated derived aliases
  preserve original leaf identity/definition, so renaming the output or an
  intermediate node does not make H1 plus its Q2 a valid sum.
* Different disclosed business scopes and a negative residual work split can
  overlap in dates; both still need an explicit existing `rationale`. A scope
  explanation is data, not authorization. Different labels do not erase a
  shared original leaf.
* A full-year claim needs exact coverage, or an explicit perimeter explanation
  (e.g. the pre-control interval is outside consolidation). Valid annual bridges
  carry their validated period/scope forward; no repeated review receipt exists.

Source identity/definition remains authored and evidenced by the source/input
layer. This validator cannot infer real subsidiary membership or the truth of
two independently rewritten reported facts from hashes or free text alone.
The company audit still reads those sources. Arbitrary nonlinear products of
two flow amounts are not a temporal sum; express the intended estimate/model
through the existing assumption/forecast fields. No new identity contracts,
permission flags, data lake copies or per-material approvals are introduced.

'''


def update_reference(text):
    start = text.index('## Composition honesty (')
    end = text.index('## Annual consumers, kinds, units', start)
    return text[:start] + DOC + text[end:]


edit('references/dated-contribution.md', update_reference)
edit('scripts/contracts/period_flow.py', lambda text: text.replace(
    'components must be disclosed, and a full-year claim must be a complete\ncomposition or carry an explicit rationale — a gap is never silently zero.',
    'components cannot double count one economic flow; a full-year claim must\nbe complete or explain its real perimeter. Rationale never exempts dates or\nshared-source overlap, and annual wrappers preserve their dated ancestry.', 1))
edit('CHANGELOG.md', lambda text: text.replace('## [4.3.0]', '## [4.3.0]', 1).replace(
    '# Changelog', '# Changelog\n\nROOT W05 reception hardening (unreleased 4.3.0): dated provenance reaches annual wrappers; date containment and original-flow overlap are mathematical checks regardless of rationale. Recognition metadata has one shared contract owner and is validated before dependency traversal; C1 E2E uses CNY throughout. Original delivery failures remain in ROOT evidence.', 1))
print('Public type shape, generic currency tamper and authoring contract updated.')
