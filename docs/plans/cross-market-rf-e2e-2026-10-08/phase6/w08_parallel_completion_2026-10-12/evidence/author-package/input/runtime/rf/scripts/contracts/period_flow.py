"""M3-FLOW (root cause R20): typed dated period flows, schema 3.9 opt-in.

A ``time_basis=period_flow`` parameter states that its ``value`` is the amount
recognized over the explicit ``[period_start, period_end]`` window — nothing
else. The pure rules below keep the amount attached to the covered period:

* both dates are required, strict ISO days, and ``period_start < period_end``;
* the window must lie inside the fiscal year named by the ``period`` label as
  resolved from the document's ``fiscal_year_end`` — this is what makes
  cross-calendar-year flows and non-calendar fiscal years expressible without
  any new period vocabulary;
* the covered length must be 3, 6 or 12 calendar months (an exact fiscal-year
  span is twelve month-differences by construction);
* amounts are never annualized implicitly: an H1 flow plus an H2 flow composes
  into the annual flow only through an explicit derived formula (x0+x1), and a
  point-in-time stock keeps the legacy ``point_in_time`` basis untouched.

Unknown start dates stay unknown: the contract requires both endpoints, so an
author who cannot evidence a real start date must not fabricate one — the flow
simply cannot be typed as ``period_flow`` yet.

W05-RF-FLOW (schema 3.10): ``validate_period_flow_fields`` takes an explicit
``schema_version`` (the old call shape keeps the 3.9 meaning). 3.10 admits any
real finite inclusive window with ``period_start <= period_end`` (same-day
flows included) still inside the fiscal-year window, so a post-control
contribution like 2026-05-31..2026-06-30 is expressible without pretending to
be a half year. ``validate_windowed_composition`` keeps derived dated amounts
honest: components must sit inside the composed window, overlapping summation
components cannot double count one economic flow; a full-year claim must
be complete or explain its real perimeter. Rationale never exempts dates or
shared-source overlap, and annual wrappers preserve their dated ancestry.
"""

from __future__ import annotations

import ast

from calendar import monthrange
from dataclasses import dataclass
from datetime import date, timedelta

from contracts.constants import (
    DATED_CONTRIBUTION_SCHEMA_VERSION,
    PERIOD_EVIDENCE_SCHEMA_VERSION,
    PERIOD_FLOW_MONTH_LENGTHS,
    PERIOD_FLOW_TIME_BASIS,
)
from contracts.evidence import (
    ForecastInputError,
    parse_iso_date,
    period_year,
    require,
)

def _fiscal_year_end_date(fiscal_year_end: str, year: int) -> date:
    month, day = int(fiscal_year_end[:2]), int(fiscal_year_end[3:])
    try:
        return date(year, month, day)
    except ValueError as exc:
        if (month, day) == (2, 29):
            # A Feb-29 FYE anchors to Feb-28 in non-leap years so windows
            # stay contiguous; the MM-DD shape itself is validated upstream.
            return date(year, 2, 28)
        raise ForecastInputError(
            f"fiscal_year_end {fiscal_year_end} is not a valid month-day"
        ) from exc


def fiscal_year_window(fiscal_year_end: str, year: int) -> tuple[date, date]:
    """Return the (start, end) dates of fiscal year ``year`` (inclusive)."""
    require(
        isinstance(fiscal_year_end, str) and len(fiscal_year_end) == 5,
        "fiscal_year_end must use MM-DD",
    )
    end = _fiscal_year_end_date(fiscal_year_end, int(year))
    start = _fiscal_year_end_date(fiscal_year_end, int(year) - 1) + timedelta(days=1)
    return start, end


def period_flow_months(start: date, end: date) -> int:
    """Exact 3/6/12 calendar-month span, using inclusive end dates.

    The next period starts at the calendar-month anniversary of ``start``.
    A duration merely close to a quarter or half year has no typed-month
    meaning. The caller handles an exact fiscal-year window separately to
    preserve leap-day year-end conventions.
    """
    require(
        isinstance(start, date) and isinstance(end, date),
        "period_flow months requires date endpoints",
    )
    require(start < end, "period_start must be strictly before period_end")
    # Compare the exclusive boundary as a tuple so a valid window ending
    # on 9999-12-31 does not overflow datetime by adding one day.
    if end.day == monthrange(end.year, end.month)[1]:
        exclusive_year, exclusive_month_index = divmod(end.year * 12 + end.month, 12)
        exclusive_end = (exclusive_year, exclusive_month_index + 1, 1)
    else:
        exclusive_end = (end.year, end.month, end.day + 1)
    for months in sorted(PERIOD_FLOW_MONTH_LENGTHS):
        month_index = start.year * 12 + start.month - 1 + months
        year, zero_based_month = divmod(month_index, 12)
        month = zero_based_month + 1
        boundary = (year, month, min(start.day, monthrange(year, month)[1]))
        if exclusive_end == boundary:
            return months
    raise ForecastInputError(
        "period_flow must cover 3, 6 or 12 whole calendar months; "
        f"got {start.isoformat()}..{end.isoformat()}"
    )


def validate_period_flow_fields(
    parameter_id: str,
    parameter: dict,
    fiscal_year_end: str,
    schema_version: str = PERIOD_EVIDENCE_SCHEMA_VERSION,
) -> dict[str, date]:
    """Fail closed unless the parameter carries a legal dated flow.

    Returns the parsed endpoints ``{"period_start": date, "period_end": date}``
    for callers that need typed dates (rendering, downstream checks).

    *schema_version* is explicit for new callers; the default keeps the pure
    helper's historical 3.9 meaning (strict order, 3/6/12 whole months). Only
    3.10 admits arbitrary real inclusive windows (``period_start <=
    period_end``), and only inside the labeled fiscal year — a cross-FY amount
    must be split by its source or an explicit estimate, never date-clipped
    while keeping the whole amount.
    """
    if schema_version not in (PERIOD_EVIDENCE_SCHEMA_VERSION, DATED_CONTRIBUTION_SCHEMA_VERSION):
        raise ForecastInputError(
            f"{parameter_id}: period_flow is not defined for schema {schema_version}"
        )
    require(
        "period_start" in parameter and "period_end" in parameter,
        f"{parameter_id}: time_basis {PERIOD_FLOW_TIME_BASIS} requires "
        "period_start and period_end",
    )
    start = parse_iso_date(parameter["period_start"], f"{parameter_id}.period_start")
    end = parse_iso_date(parameter["period_end"], f"{parameter_id}.period_end")
    if schema_version == DATED_CONTRIBUTION_SCHEMA_VERSION:
        require(
            start <= end,
            f"{parameter_id}: period_start must not be after period_end",
        )
    else:
        require(
            start < end,
            f"{parameter_id}: period_start must be strictly before period_end",
        )
    year = period_year(parameter.get("period"), f"{parameter_id}.period")
    window_start, window_end = fiscal_year_window(fiscal_year_end, year)
    require(
        window_start <= start and end <= window_end,
        f"{parameter_id}: period_flow dates must lie within the FY{year} window "
        f"({window_start.isoformat()}..{window_end.isoformat()}) implied by "
        f"fiscal_year_end {fiscal_year_end}",
    )
    # A fiscal year is explicitly a twelve-month reporting window even
    # when its leap-day boundary does not match a naive date anniversary.
    # All shorter 3.9 flows must match exact calendar-month boundaries.
    # Schema 3.10 admits any real window length; the amount still belongs
    # only to the written window (no implicit x2/x12/day annualization).
    if (start, end) != (window_start, window_end):
        if schema_version == DATED_CONTRIBUTION_SCHEMA_VERSION:
            return {"period_start": start, "period_end": end}
        try:
            period_flow_months(start, end)
        except ForecastInputError as exc:
            raise ForecastInputError(f"{parameter_id}: {exc}") from exc
    return {"period_start": start, "period_end": end}


# Rates/prices and explicitly dated stocks do not cover a flow interval.
_NON_FLOW_DIMENSIONS = frozenset({
    "ratio", "revenue_per_unit", "revenue_per_activity", "revenue_per_area",
    "monetary_balance", "backlog", "reserve_volume",
})


def _flow_parameter(parameter: dict) -> bool:
    return (parameter.get("time_basis") in {"annual", PERIOD_FLOW_TIME_BASIS}
            and parameter.get("dimension") not in _NON_FLOW_DIMENSIONS)


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
class _PeriodExpression:
    """Affine period power with shared price-role symbols, not independent sets.

    Like raw temporal prices of one existing dimension share one role within
    the actual formula DAG: transaction price (0) or operating-period ARPU (1).
    Original aliases retain that symbol; multiplication/division add/subtract
    it. Thus a same/like price ratio is scalar before any annual interpretation
    is selected. Source unit/currency/scale still have their existing owner.
    """
    constant: float
    choices: dict[str, float]


@dataclass(frozen=True)
class _FormulaType:
    powers: dict[str, float]
    period: _PeriodExpression
    value: float
    literal_zero: bool = False


def validate_derived_flow_ancestry(parameter_id: str, parameter: dict, parameter_index: dict[str, dict]) -> None:
    """3.10 actual formula dimension/period ancestry, not an annual label.

    Units and period meaning follow every actual operator to the original
    leaves. Shared symbols and all intermediate equations must admit ONE
    consistent interpretation. A stock is not an amount over a period.
    Financial native models retain explicit stock/rate business roles.
    """
    from itertools import product as assignments
    from forecast.calc import evaluate_derived_formula

    memo: dict[str, _FormulaType] = {}
    constraints: list[_PeriodExpression] = []

    def product(left: dict[str, float], right: dict[str, float], sign: float) -> dict[str, float]:
        result = dict(left)
        for key, value in right.items():
            result[key] = result.get(key, 0.0) + sign * value
        return {key: value for key, value in result.items() if value != 0}

    def combine(left: _PeriodExpression, right: _PeriodExpression, sign: float) -> _PeriodExpression:
        return _PeriodExpression(left.constant + sign * right.constant,
                                 product(left.choices, right.choices, sign))

    def equate(left: _PeriodExpression, right: _PeriodExpression) -> None:
        constraints.append(combine(left, right, -1.0))

    scalar_period = _PeriodExpression(0.0, {})
    flow_period = _PeriodExpression(1.0, {})

    def describe(identifier: str, item: dict, stack: frozenset[str]) -> _FormulaType:
        require(identifier not in stack, f"{parameter_id}: typed flow derived cycle at {identifier}")
        if identifier in memo:
            return memo[identifier]
        dimension = item.get("dimension")
        if not isinstance(dimension, str) or dimension not in _DIMENSION_POWERS:
            raise ForecastInputError(f"{identifier}: typed flow needs a supported dimension")
        expected = _DIMENSION_POWERS[dimension]
        temporal = item.get("time_basis") in {"annual", PERIOD_FLOW_TIME_BASIS}
        if item.get("kind") != "derived_fact":
            period = scalar_period
            if temporal and dimension in _PERIOD_PRICE_DIMENSIONS:
                # At most the three existing price dimensions are ambiguous.
                # A fiscal-year label or another source ID does not change the
                # dimensional meaning of like operating-period prices. Different
                # genuine roles use actual flow-derived prices/native models.
                period = _PeriodExpression(0.0, {dimension: 1.0})
            elif temporal and _flow_parameter(item):
                period = flow_period
            result = _FormulaType(dict(expected), period, float(item["value"]))
            memo[identifier] = result
            return result
        input_ids = item["input_parameter_ids"]
        values = [float(parameter_index[source_id]["value"]) for source_id in input_ids]
        formula = item["formula"]
        evaluate_derived_formula(formula, values)  # native syntax/finite/zero-divide owner

        def numeric(node: ast.AST) -> float:
            return evaluate_derived_formula(ast.unparse(node), values)

        def walk(node: ast.AST) -> _FormulaType:
            if isinstance(node, ast.Expression):
                return walk(node.body)
            if isinstance(node, ast.Name):
                source_id = input_ids[int(node.id[1:])]
                return describe(source_id, parameter_index[source_id], stack | {identifier})
            if isinstance(node, ast.Constant):
                value = numeric(node)
                return _FormulaType({}, scalar_period, value, value == 0)
            if isinstance(node, ast.UnaryOp):
                inner = walk(node.operand)
                return _FormulaType(inner.powers, inner.period, numeric(node), inner.literal_zero)
            if isinstance(node, ast.BinOp):
                left, right = walk(node.left), walk(node.right)
                value = numeric(node)
                if isinstance(node.op, (ast.Add, ast.Sub)):
                    require(left.powers == right.powers or left.literal_zero or right.literal_zero,
                            f"{identifier}: typed flow addition/subtraction has incompatible dimensions; register a typed assumption instead of an untyped amount")
                    powers = right.powers if left.literal_zero else left.powers
                    period = right.period if left.literal_zero else left.period
                    if not left.literal_zero and not right.literal_zero:
                        equate(left.period, right.period)
                    return _FormulaType(powers, period, value, left.literal_zero and right.literal_zero)
                if isinstance(node.op, ast.Mult):
                    return _FormulaType(product(left.powers, right.powers, 1.0),
                                        combine(left.period, right.period, 1.0), value)
                if isinstance(node.op, ast.Div):
                    return _FormulaType(product(left.powers, right.powers, -1.0),
                                        combine(left.period, right.period, -1.0), value)
                if isinstance(node.op, ast.Pow):
                    require(not right.powers, f"{identifier}: typed flow exponent must be dimensionless")
                    equate(right.period, scalar_period)
                    powers = {key: power * right.value for key, power in left.powers.items() if power * right.value != 0}
                    period = _PeriodExpression(left.period.constant * right.value,
                                               {key: power * right.value for key, power in left.period.choices.items()
                                                if power * right.value != 0})
                    return _FormulaType(powers, period, value)
            return _FormulaType({}, scalar_period, numeric(node))  # invalid native AST rejected above

        actual = walk(ast.parse(formula, mode="eval"))
        require(actual.powers == expected,
                f"{identifier}: typed flow formula dimension does not match declared {dimension}; relabeling cannot change original units")
        if temporal and dimension == "revenue":
            # Keep the original expression after constraining it: resetting an
            # alias to a fresh annual label would lose price-role correlation.
            equate(actual.period, flow_period)
        memo[identifier] = actual
        return actual

    result = describe(parameter_id, parameter, frozenset())
    equate(result.period, flow_period)
    symbols = sorted({key for equation in constraints for key in equation.choices})
    # Only three native price dimensions exist, hence <=8 assignments. We do
    # not enumerate per-source Cartesian choices or require a solver package.
    consistent = any(all(abs(equation.constant + sum(coefficient * selection[symbol]
        for symbol, coefficient in equation.choices.items())) <= 1e-9 for equation in constraints)
        for values in assignments((0.0, 1.0), repeat=len(symbols))
        for selection in [dict(zip(symbols, values))])
    require(consistent, f"{parameter_id}: typed flow requires consistent flow-bearing ancestry for the actual annual consumer; stocks, scalar or cancelled price ratios cannot establish a period amount")


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


def _flow_atoms(input_id: str, coefficient: float, index: dict[str, dict], fiscal_year_end: str, stack: frozenset[str]) -> list[tuple[date, date, str, float, str]]:
    """Keep original flow identities through dated derived aliases/bridges.

    Output definition changes never change these atoms. Annual-only legacy
    projections stay terminal: 3.10 adds dated provenance, not a new forecast
    algorithm for old annual assumptions.
    """
    require(input_id not in stack, f"derived parameter cycle detected in dated composition at {input_id}")
    source = index[input_id]
    if source.get("kind") == "derived_fact" and (
        source.get("time_basis") == PERIOD_FLOW_TIME_BASIS
        or _dated_ancestor(source, index, {input_id})
    ):
        result: list[tuple[date, date, str, float, str]] = []
        for position, weight in _flow_coefficients(input_id, source, index).items():
            result.extend(_flow_atoms(source["input_parameter_ids"][position], coefficient * weight,
                                      index, fiscal_year_end, stack | {input_id}))
        return result
    if source.get("time_basis") == "annual":
        start, end = fiscal_year_window(fiscal_year_end, period_year(source.get("period"), f"{input_id}.period"))
    else:
        start = parse_iso_date(source.get("period_start"), f"{input_id}.period_start")
        end = parse_iso_date(source.get("period_end"), f"{input_id}.period_end")
    semantic = " ".join(str(source.get("definition", "")).casefold().split())
    return [(start, end, input_id, coefficient, semantic)]


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
    if parameter.get("dimension") == "revenue" or parameter.get("time_basis") == PERIOD_FLOW_TIME_BASIS:
        validate_derived_flow_ancestry(parameter_id, parameter, parameter_index)
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
    atoms: list[tuple[date, date, str, float, str]] = []
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
        atoms.extend(_flow_atoms(input_id, coefficient, parameter_index, fiscal_year_end, frozenset({parameter_id})))
    require(bool(windows), f"{parameter_id}: dated composition needs a flow-bearing input; stock/rate alone cannot establish recognized revenue")
    for position, (start, end, input_id, coefficient, semantic) in enumerate(atoms):
        for other_start, other_end, other_id, other_coefficient, other_semantic in atoms[position + 1:]:
            if end < other_start or other_end < start:
                continue
            require(not ((input_id == other_id or semantic == other_semantic) and coefficient * other_coefficient > 0),
                    f"{parameter_id}: dated composition double counts the same economic flow "
                    f"in overlapping inputs {input_id} and {other_id}")
            require(explained, f"{parameter_id}: overlapping dated composition needs a scope/residual rationale")
    if (result_start, result_end) != fiscal_window:
        return
    covered = sorted((start, end) for start, end, *_ in windows)
    cursor = result_start.toordinal()
    for start, end in covered:
        require(start.toordinal() <= cursor or explained,
                f"{parameter_id}: full-year dated composition has unexplained gaps; missing flows cannot be zero-filled")
        cursor = max(cursor, end.toordinal() + 1)
    require(cursor > result_end.toordinal() or explained,
            f"{parameter_id}: full-year dated composition needs complete flow coverage or an explicit perimeter rationale")
