from pathlib import Path
path = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root/scripts/contracts/period_flow.py')
body = path.read_text(encoding='utf-8')
old = '        require(dimension in _DIMENSION_POWERS, f"{identifier}: typed flow needs a supported dimension")\n'
new = ('        if not isinstance(dimension, str) or dimension not in _DIMENSION_POWERS:\n'
       '            raise ForecastInputError(f"{identifier}: typed flow needs a supported dimension")\n')
assert old in body
path.write_text(body.replace(old, new), encoding='utf-8')
print('Typed dimension now narrows with an actual contract error; no cast/default/waiver')
