"""One-shot bounded edits to the ROOT RF tree; never touches canonical RF."""
from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root').resolve()


def edit(relative, transform):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT) and path.is_file()
    original = path.read_text(encoding='utf-8')
    changed = transform(original)
    assert changed != original, relative
    path.write_text(changed, encoding='utf-8')


CODE = '''# Rates/prices and explicitly dated stocks do not cover a flow interval.
_NON_FLOW_DIMENSIONS = frozenset({
    "ratio", "revenue_per_unit", "revenue_per_activity", "revenue_per_area",
    "monetary_balance", "backlog", "reserve_volume",
})


def _flow_parameter(parameter: dict) -> bool:
    return (parameter.get("time_basis") in {"annual", PERIOD_FLOW_TIME_BASIS}
            and parameter.get("dimension") not in _NON_FLOW_DIMENSIONS)


def _dated_ancestor(parameter: dict, index: dict[str, dict], seen: set[str]) -> bool:
    """An annual wrapper cannot hide a dated ancestor in a derived DAG."""
    for input_id in parameter.get("input_parameter_ids", []):
        source = index.get(input_id)
        if not isinstance(source, dict) or input_id in seen:
            continue  # input/cycle validation has its own existing owner
        if source.get("time_basis") == PERIOD_FLOW_TIME_BASIS:
            return True
        if source.get("kind") == "derived_fact" and _dated_ancestor(source, index, seen | {input_id}):
            return True
    return False


def _flow_coefficients(parameter_id: str, parameter: dict, index: dict[str, dict]) -> dict[int, float]:
    """Linear temporal provenance, using the native arithmetic evaluator.

    Scalar/rate/price factors scale amounts, not intervals. Zero-weight and
    unused inputs cannot manufacture coverage. Add/subtraction preserve signs
    so a residual bridge is distinguishable from duplicate positive summation.
    """
    from forecast.calc import evaluate_derived_formula

    ids = parameter["input_parameter_ids"]
    inputs = [index[input_id] for input_id in ids]
    values = [float(item["value"]) for item in inputs]
    formula = parameter["formula"]
    # Native syntax/variable/finite/division/exponent validation remains owned
    # by the native arithmetic evaluator; this adds temporal meaning only.
    evaluate_derived_formula(formula, values)
    parsed = ast.parse(formula, mode="eval")

    def scalar(node: ast.AST) -> float:
        return evaluate_derived_formula(ast.unparse(node), values)

    def scale(terms: dict[int, float], factor: float) -> dict[int, float]:
        return {key: value * factor for key, value in terms.items() if value * factor != 0}

    def walk(node: ast.AST) -> tuple[dict[int, float], float]:
        if isinstance(node, ast.Expression):
            return walk(node.body)
        if isinstance(node, ast.Name):
            position = int(node.id[1:])  # validated native x0/x1/... vocabulary
            return ({position: 1.0}, 0.0) if _flow_parameter(inputs[position]) else ({}, values[position])
        if isinstance(node, ast.Constant):
            return {}, scalar(node)
        if isinstance(node, ast.UnaryOp):
            terms, constant = walk(node.operand)
            sign = -1.0 if isinstance(node.op, ast.USub) else 1.0
            return scale(terms, sign), constant * sign
        if isinstance(node, ast.BinOp):
            left, left_scalar = walk(node.left)
            right, right_scalar = walk(node.right)
            if isinstance(node.op, (ast.Add, ast.Sub)):
                sign = -1.0 if isinstance(node.op, ast.Sub) else 1.0
                combined = dict(left)
                for key, value in right.items():
                    combined[key] = combined.get(key, 0.0) + sign * value
                return scale(combined, 1.0), left_scalar + sign * right_scalar
            if isinstance(node.op, ast.Mult):
                require(not (left and right), f"{parameter_id}: dated composition cannot multiply two flow amounts")
                return (scale(left, right_scalar) if left else scale(right, left_scalar), left_scalar * right_scalar)
            if isinstance(node.op, ast.Div):
                require(not right, f"{parameter_id}: dated composition cannot divide by a flow amount")
                return scale(left, 1.0 / right_scalar), left_scalar / right_scalar
            if isinstance(node.op, ast.Pow):
                require(not right and (not left or right_scalar in {0.0, 1.0}),
                        f"{parameter_id}: dated composition must preserve flow units")
                return (left, left_scalar) if left and right_scalar == 1 else ({}, scalar(node))
        return {}, scalar(node)  # unsupported arithmetic was rejected above

    return walk(parsed)[0]


def validate_windowed_composition(
    parameter_id: str,
    parameter: dict,
    parameter_index: dict[str, dict],
    fiscal_year_end: str,
) -> None:
    """One temporal rule for 3.10 dated flows and their annual wrappers.

    A rationale describes a perimeter/gap or residual work split; it never
    licenses moving a known amount to another interval or adding the same
    economic flow twice. Legacy annual-only formulas keep their prior meaning;
    annual derived nodes with dated ancestors use exactly the dated-flow rule.
    """
    if not _flow_parameter(parameter):
        return
    if parameter.get("time_basis") == "annual" and not _dated_ancestor(parameter, parameter_index, {parameter_id}):
        return
    year = period_year(parameter.get("period"), f"{parameter_id}.period")
    fiscal_window = fiscal_year_window(fiscal_year_end, year)
    if parameter.get("time_basis") == "annual":
        result_start, result_end = fiscal_window
    else:
        try:
            result_start = parse_iso_date(parameter.get("period_start"), f"{parameter_id}.period_start")
            result_end = parse_iso_date(parameter.get("period_end"), f"{parameter_id}.period_end")
        except ForecastInputError:
            return  # the owning field validator already recorded the error
    rationale = parameter.get("rationale")
    explained = isinstance(rationale, str) and bool(rationale.strip())
    windows: list[tuple[date, date, str, float, str]] = []
    for position, coefficient in _flow_coefficients(parameter_id, parameter, parameter_index).items():
        input_id = parameter["input_parameter_ids"][position]
        source = parameter_index[input_id]
        if source.get("time_basis") == "annual":
            start, end = fiscal_year_window(fiscal_year_end, period_year(source.get("period"), f"{input_id}.period"))
        else:
            start = parse_iso_date(source.get("period_start"), f"{input_id}.period_start")
            end = parse_iso_date(source.get("period_end"), f"{input_id}.period_end")
        require(result_start <= start and end <= result_end,
                f"{parameter_id}: dated composition input {input_id} window {start}..{end} "
                f"lies outside the composed window {result_start}..{result_end}")
        semantic = " ".join(str(source.get("definition", "")).casefold().split())
        windows.append((start, end, input_id, coefficient, semantic))
    for position, (start, end, input_id, coefficient, semantic) in enumerate(windows):
        for other_start, other_end, other_id, other_coefficient, other_semantic in windows[position + 1:]:
            if end < other_start or other_end < start:
                continue
            require(not (semantic == other_semantic and coefficient * other_coefficient > 0),
                    f"{parameter_id}: dated composition double counts the same economic flow "
                    f"in overlapping inputs {input_id} and {other_id}")
            require(explained, f"{parameter_id}: overlapping dated composition needs a scope/residual rationale")
    if (result_start, result_end) != fiscal_window:
        return
    covered = sorted((start, end) for start, end, *_ in windows)
    cursor = result_start
    for start, end in covered:
        require(start <= cursor or explained,
                f"{parameter_id}: full-year dated composition has unexplained gaps; missing flows cannot be zero-filled")
        cursor = max(cursor, end + timedelta(days=1))
    require(cursor > result_end or explained,
            f"{parameter_id}: full-year dated composition needs complete flow coverage or an explicit perimeter rationale")
'''

edit('scripts/contracts/period_flow.py', lambda text: text.replace('from __future__ import annotations\n', 'from __future__ import annotations\n\nimport ast\n', 1).split('def validate_windowed_composition(', 1)[0] + CODE)
edit('scripts/contracts/document.py', lambda text: text.replace('and parameter.get("time_basis") == PERIOD_FLOW_TIME_BASIS\n            ):', 'and parameter.get("time_basis") in {"annual", PERIOD_FLOW_TIME_BASIS}\n            ):', 1))

# Move the existing complete recognition owner without changing its rules.
segments = ROOT / 'scripts/forecast/segments.py'
text = segments.read_text(encoding='utf-8')
start = text.index('def validate_recognition_metadata(')
end = text.index('\n\ndef apply_revenue_recognition(', start)
function = text[start:end]
recognition = ROOT / 'scripts/contracts/recognition.py'
assert not recognition.exists()
recognition.write_text('''"""Shared recognition contract: validate shape before consumers traverse it."""
from __future__ import annotations
from typing import Any
from contracts.constants import PRESENTATIONS, RECOGNITION_MODES, RECOGNITION_TIMING, SCENARIOS
from contracts.evidence import require, validate_claim_ids

''' + function + '\n', encoding='utf-8')
segments.write_text(text[:start] + text[end + 2:], encoding='utf-8')
edit('scripts/forecast/segments.py', lambda text: text.replace('from contracts.document import validate_document, validate_scenario_probabilities', 'from contracts.document import validate_document, validate_scenario_probabilities\nfrom contracts.recognition import validate_recognition_metadata', 1))

def wire_recognition(text):
    text = text.replace('from contracts.period_flow import validate_period_flow_fields, validate_windowed_composition', 'from contracts.period_flow import validate_period_flow_fields, validate_windowed_composition\nfrom contracts.recognition import validate_recognition_metadata', 1)
    # Add once at the contract boundary before growth-driver traversal. In
    # fail-fast and collect-all this is the same owner, not dict.get defaults.
    helper = '''def validate_recognition_contracts(data: dict[str, Any], source_index: dict[str, dict[str, Any]], claim_index: dict[str, dict[str, Any]]) -> None:
    for segment in data["segments"]:
        validate_recognition_metadata(segment, source_index, claim_index)


'''
    where = text.index('def validate_document(')
    text = text[:where] + helper + text[where:]
    target = '        growth_driver_tree = validate_growth_driver_tree('
    assert target in text
    text = text.replace(target, '        validate_recognition_contracts(data, source_index, claim_index)\n' + target, 1)
    target = '        growth_driver_tree = (\n'
    assert target in text
    text = text.replace(target, '        _run_gate(collector, "recognition", validate_recognition_contracts,\n                  data, source_index, claim_index)\n' + target, 1)
    return text

edit('scripts/contracts/document.py', wire_recognition)
print('Applied temporal lineage and shared recognition contract to ROOT tree only.')
