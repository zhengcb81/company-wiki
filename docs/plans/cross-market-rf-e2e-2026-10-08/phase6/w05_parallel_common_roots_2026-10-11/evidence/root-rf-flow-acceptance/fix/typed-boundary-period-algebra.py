from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
path = ROOT / 'scripts/contracts/period_flow.py'
body = path.read_text(encoding='utf-8')
start = body.index('@dataclass(frozen=True)\nclass _FormulaType:')
end = body.index('\n\ndef _dated_ancestor(', start)
body = body[:start] + '''@dataclass(frozen=True)
class _FormulaType:
    powers: dict[str, float]
    # 0: stock/scalar; 1: amount over a period. Ratios preserve the actual
    # algebra (flow/stock = 1, stock/flow = -1), not their outer metadata tag.
    # A raw annual per-unit price can serve a spot-sale price (0) or an annual
    # ARPU (1); actual derived prices keep their recomputed ancestry instead.
    period_powers: frozenset[float]
    value: float
    literal_zero: bool = False


def validate_derived_flow_ancestry(parameter_id: str, parameter: dict, parameter_index: dict[str, dict]) -> None:
    """3.10 actual formula dimension/period ancestry, not an annual label.

    Units and period meaning follow every actual operator to the original
    leaves. A stock is not an amount over a period. Financial native models
    retain explicit stock/rate business roles; no permission is inferred.
    """
    from forecast.calc import evaluate_derived_formula

    memo: dict[str, _FormulaType] = {}

    def product(left: dict[str, float], right: dict[str, float], sign: float) -> dict[str, float]:
        result = dict(left)
        for key, value in right.items():
            result[key] = result.get(key, 0.0) + sign * value
        return {key: value for key, value in result.items() if value != 0}

    def combine(left: frozenset[float], right: frozenset[float], sign: float) -> frozenset[float]:
        return frozenset(a + sign * b for a in left for b in right)

    def describe(identifier: str, item: dict, stack: frozenset[str]) -> _FormulaType:
        require(identifier not in stack, f"{parameter_id}: typed flow derived cycle at {identifier}")
        if identifier in memo:
            return memo[identifier]
        dimension = item.get("dimension")
        require(dimension in _DIMENSION_POWERS, f"{identifier}: typed flow needs a supported dimension")
        expected = _DIMENSION_POWERS[dimension]
        temporal = item.get("time_basis") in {"annual", PERIOD_FLOW_TIME_BASIS}
        if item.get("kind") != "derived_fact":
            periods = frozenset({0.0})
            if temporal and dimension in _PERIOD_PRICE_DIMENSIONS:
                periods = frozenset({0.0, 1.0})
            elif temporal and _flow_parameter(item):
                periods = frozenset({1.0})
            result = _FormulaType(dict(expected), periods, float(item["value"]))
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
                return _FormulaType({}, frozenset({0.0}), value, value == 0)
            if isinstance(node, ast.UnaryOp):
                inner = walk(node.operand)
                return _FormulaType(inner.powers, inner.period_powers, numeric(node), inner.literal_zero)
            if isinstance(node, ast.BinOp):
                left, right = walk(node.left), walk(node.right)
                value = numeric(node)
                if isinstance(node.op, (ast.Add, ast.Sub)):
                    require(left.powers == right.powers or left.literal_zero or right.literal_zero,
                            f"{identifier}: typed flow addition/subtraction has incompatible dimensions; register a typed assumption instead of an untyped amount")
                    powers = right.powers if left.literal_zero else left.powers
                    periods = (right.period_powers if left.literal_zero else left.period_powers
                               if right.literal_zero else left.period_powers & right.period_powers)
                    require(bool(periods), f"{identifier}: typed flow cannot add/subtract stocks and period amounts; use the explicit native stock-flow model")
                    return _FormulaType(powers, periods, value, left.literal_zero and right.literal_zero)
                if isinstance(node.op, ast.Mult):
                    return _FormulaType(product(left.powers, right.powers, 1.0),
                                        combine(left.period_powers, right.period_powers, 1.0), value)
                if isinstance(node.op, ast.Div):
                    return _FormulaType(product(left.powers, right.powers, -1.0),
                                        combine(left.period_powers, right.period_powers, -1.0), value)
                if isinstance(node.op, ast.Pow):
                    require(not right.powers and right.period_powers == frozenset({0.0}),
                            f"{identifier}: typed flow exponent must be dimensionless")
                    powers = {key: power * right.value for key, power in left.powers.items() if power * right.value != 0}
                    return _FormulaType(powers, frozenset(power * right.value for power in left.period_powers), value)
            return _FormulaType({}, frozenset({0.0}), numeric(node))  # invalid native AST rejected above

        actual = walk(ast.parse(formula, mode="eval"))
        require(actual.powers == expected,
                f"{identifier}: typed flow formula dimension does not match declared {dimension}; relabeling cannot change original units")
        periods = actual.period_powers
        # Preserve the actual ratio/price period algebra. Only a recognized
        # revenue result selects the period interpretation required by its
        # existing contract. A monetary balance cannot create that power.
        if temporal and dimension == "revenue":
            require(1.0 in periods, f"{identifier}: typed flow requires flow-bearing ancestry with a period amount; stock/rate/scalar alone cannot establish recognized revenue")
            periods &= frozenset({1.0})
        result = _FormulaType(actual.powers, periods, actual.value)
        memo[identifier] = result
        return result

    result = describe(parameter_id, parameter, frozenset())
    require(1.0 in result.period_powers,
            f"{parameter_id}: typed flow requires flow-bearing ancestry for the actual annual consumer")
''' + body[end:]
path.write_text(body, encoding='utf-8')
print('Actual period algebra now composes and cancels through ratios; native/ARPU stock conversions preserve genuine flow origin')
