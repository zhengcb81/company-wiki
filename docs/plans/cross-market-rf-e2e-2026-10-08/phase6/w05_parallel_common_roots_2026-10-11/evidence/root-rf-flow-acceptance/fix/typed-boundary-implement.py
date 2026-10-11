from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
path = ROOT / 'scripts/contracts/period_flow.py'
body = path.read_text(encoding='utf-8')
body = body.replace('from calendar import monthrange\n', 'from calendar import monthrange\nfrom dataclasses import dataclass\n')
anchor = '\n\ndef _dated_ancestor('
assert anchor in body
helper = '''

# Dimensional powers are independent of caller/output labels. Currency/scale
# remain owned by the existing parameter contract; these are economic types,
# not a second units/identity registry or a configurable permission gate.
_DIMENSION_POWERS = {
    "revenue": {"money": 1.0}, "monetary_balance": {"money": 1.0},
    "backlog": {"money": 1.0}, "quantity": {"quantity": 1.0},
    "coverage_units": {"quantity": 1.0}, "reserve_volume": {"quantity": 1.0},
    "activity": {"activity": 1.0}, "area": {"area": 1.0}, "ratio": {},
    "revenue_per_unit": {"money": 1.0, "quantity": -1.0},
    "revenue_per_activity": {"money": 1.0, "activity": -1.0},
    "revenue_per_area": {"money": 1.0, "area": -1.0},
}
_PERIOD_PRICE_DIMENSIONS = frozenset({"revenue_per_unit", "revenue_per_activity", "revenue_per_area"})


@dataclass(frozen=True)
class _FormulaType:
    powers: dict[str, float]
    has_flow_period: bool
    value: float
    literal_zero: bool = False


def validate_derived_flow_ancestry(parameter_id: str, parameter: dict, parameter_index: dict[str, dict]) -> None:
    """3.10 actual formula type/time ancestry, independent of outer annual tags.

    Stocks carry monetary/quantity units but no recognized-flow duration. An
    annual per-unit/activity/area price supplies duration when multiplied by
    matching stock/operating quantities. Generic ratio/scalar factors scale an
    existing flow; they cannot turn a money balance into recognized revenue.
    Native financial/stock-flow models retain their existing explicit roles.
    """
    from forecast.calc import evaluate_derived_formula

    memo: dict[str, _FormulaType] = {}

    def product(left: dict[str, float], right: dict[str, float], sign: float) -> dict[str, float]:
        result = dict(left)
        for key, value in right.items():
            result[key] = result.get(key, 0.0) + sign * value
        return {key: value for key, value in result.items() if value != 0}

    def describe(identifier: str, item: dict, stack: frozenset[str]) -> _FormulaType:
        require(identifier not in stack, f"{parameter_id}: typed flow derived cycle at {identifier}")
        if identifier in memo:
            return memo[identifier]
        dimension = item.get("dimension")
        require(dimension in _DIMENSION_POWERS, f"{identifier}: typed flow needs a supported dimension")
        expected = _DIMENSION_POWERS[dimension]
        basis = item.get("time_basis")
        temporal = basis in {"annual", PERIOD_FLOW_TIME_BASIS}
        if item.get("kind") != "derived_fact":
            duration = temporal and (_flow_parameter(item) or dimension in _PERIOD_PRICE_DIMENSIONS)
            result = _FormulaType(dict(expected), duration, float(item["value"]))
            memo[identifier] = result
            return result
        inputs = [describe(source_id, parameter_index[source_id], stack | {identifier})
                  for source_id in item["input_parameter_ids"]]
        values = [source.value for source in inputs]
        formula = item["formula"]
        evaluate_derived_formula(formula, values)  # native syntax/finite/zero-divide owner

        def numeric(node: ast.AST) -> float:
            return evaluate_derived_formula(ast.unparse(node), values)

        def walk(node: ast.AST) -> _FormulaType:
            if isinstance(node, ast.Expression):
                return walk(node.body)
            if isinstance(node, ast.Name):
                return inputs[int(node.id[1:])]
            if isinstance(node, ast.Constant):
                value = numeric(node)
                return _FormulaType({}, False, value, value == 0)
            if isinstance(node, ast.UnaryOp):
                inner = walk(node.operand)
                return _FormulaType(inner.powers, inner.has_flow_period, numeric(node), inner.literal_zero)
            if isinstance(node, ast.BinOp):
                left, right = walk(node.left), walk(node.right)
                value = numeric(node)
                if isinstance(node.op, (ast.Add, ast.Sub)):
                    require(left.powers == right.powers or left.literal_zero or right.literal_zero,
                            f"{identifier}: typed flow addition/subtraction has incompatible dimensions; register a typed assumption instead of an untyped amount")
                    powers = right.powers if left.literal_zero else left.powers
                    return _FormulaType(powers, left.has_flow_period or right.has_flow_period, value,
                                        left.literal_zero and right.literal_zero)
                if isinstance(node.op, ast.Mult):
                    duration = ((left.has_flow_period and right.value != 0)
                                or (right.has_flow_period and left.value != 0))
                    return _FormulaType(product(left.powers, right.powers, 1.0), duration, value)
                if isinstance(node.op, ast.Div):
                    return _FormulaType(product(left.powers, right.powers, -1.0), left.has_flow_period, value)
                if isinstance(node.op, ast.Pow):
                    require(not right.powers and not right.has_flow_period,
                            f"{identifier}: typed flow exponent must be dimensionless")
                    powers = {key: power * right.value for key, power in left.powers.items() if power * right.value != 0}
                    return _FormulaType(powers, left.has_flow_period and right.value != 0, value)
            return _FormulaType({}, False, numeric(node))  # invalid native AST rejected above

        actual = walk(ast.parse(formula, mode="eval"))
        require(actual.powers == expected,
                f"{identifier}: typed flow formula dimension does not match declared {dimension}; relabeling cannot change original units")
        duration = actual.has_flow_period and temporal and (
            dimension not in _NON_FLOW_DIMENSIONS or dimension in _PERIOD_PRICE_DIMENSIONS)
        result = _FormulaType(actual.powers, duration, actual.value)
        # A revenue alias is checked at each recursive node, not only at its
        # final consumer, so an intermediate definition/time-basis cannot cast
        # a monetary stock into a flow and subsequently look authoritative.
        if temporal and dimension == "revenue":
            require(duration, f"{identifier}: typed flow requires a flow-bearing amount or dimensionally matching annual price; stock/rate/scalar alone cannot establish recognized revenue")
        memo[identifier] = result
        return result

    result = describe(parameter_id, parameter, frozenset())
    require(result.has_flow_period,
            f"{parameter_id}: typed flow requires flow-bearing ancestry for the actual annual consumer")
'''
body = body.replace(anchor, helper + anchor)
anchor = '    if parameter.get("time_basis") == "annual" and not _dated_ancestor(parameter, parameter_index, {parameter_id}):\n'
assert anchor in body
body = body.replace(anchor,
'''    if parameter.get("dimension") == "revenue" or parameter.get("time_basis") == PERIOD_FLOW_TIME_BASIS:
        validate_derived_flow_ancestry(parameter_id, parameter, parameter_index)
''' + anchor)
path.write_text(body, encoding='utf-8')

path = ROOT / 'scripts/contracts/annual_consumption.py'
body = path.read_text(encoding='utf-8')
body = body.replace('from contracts.constants import PERIOD_FLOW_SCHEMA_VERSIONS, PERIOD_FLOW_TIME_BASIS',
                    'from contracts.constants import DATED_CONTRIBUTION_SCHEMA_VERSION, PERIOD_FLOW_SCHEMA_VERSIONS, PERIOD_FLOW_TIME_BASIS')
body = body.replace('from contracts.period_flow import fiscal_year_window',
                    'from contracts.period_flow import fiscal_year_window, validate_derived_flow_ancestry')
anchor = '        if basis == "annual":\n            continue\n'
assert anchor in body
body = body.replace(anchor, '''        if basis == "annual":
            if (data.get("schema_version") == DATED_CONTRIBUTION_SCHEMA_VERSION
                    and parameter_id in flow_roles and parameter.get("kind") == "derived_fact"):
                validate_derived_flow_ancestry(parameter_id, parameter, parameter_index)
            continue
''')
body = body.replace('This contract does not annualize amounts, expand derived ancestors, infer dates,',
                    'This contract does not annualize amounts or infer dates. Schema 3.10 checks\nderived actual-flow ancestry before accepting an annual consumer label; it does not')
path.write_text(body, encoding='utf-8')

path = ROOT / 'tests/test_w05_root_temporal_lineage.py'
body = path.read_text(encoding='utf-8')
old = '            "unit": "ratio" if dimension == "ratio" else "USD million",'
new = '            "unit": {"ratio": "ratio", "quantity": "units", "revenue_per_unit": "USD million per unit"}.get(dimension, "USD million"),'
assert old in body
path.write_text(body.replace(old, new), encoding='utf-8')
print('Applied one 3.10 recursive formula dimension/time helper at source composition and actual annual-flow consumer; legacy schemas untouched')
