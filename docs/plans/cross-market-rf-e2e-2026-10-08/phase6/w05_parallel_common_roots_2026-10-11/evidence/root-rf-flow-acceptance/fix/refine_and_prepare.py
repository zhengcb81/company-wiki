from pathlib import Path
ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root').resolve()


def edit(relative, fn):
    path = (ROOT / relative).resolve()
    assert path.is_relative_to(ROOT) and path.is_file()
    old = path.read_text(encoding='utf-8')
    new = fn(old)
    assert new != old, relative
    path.write_text(new, encoding='utf-8')


ATOMS = '''def _flow_atoms(input_id: str, coefficient: float, index: dict[str, dict], fiscal_year_end: str, stack: frozenset[str]) -> list[tuple[date, date, str, float, str]]:
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


'''


def refine_period(text):
    text = text.replace('def validate_windowed_composition(', ATOMS + 'def validate_windowed_composition(', 1)
    text = text.replace('    windows: list[tuple[date, date, str, float, str]] = []\n',
                        '    windows: list[tuple[date, date, str, float, str]] = []\n    atoms: list[tuple[date, date, str, float, str]] = []\n', 1)
    text = text.replace('        windows.append((start, end, input_id, coefficient, semantic))\n',
                        '        windows.append((start, end, input_id, coefficient, semantic))\n        atoms.extend(_flow_atoms(input_id, coefficient, parameter_index, fiscal_year_end, frozenset({parameter_id})))\n', 1)
    text = text.replace(' in enumerate(windows):\n        for other_start, other_end, other_id, other_coefficient, other_semantic in windows[position + 1:]:',
                        ' in enumerate(atoms):\n        for other_start, other_end, other_id, other_coefficient, other_semantic in atoms[position + 1:]:', 1)
    text = text.replace('semantic == other_semantic and coefficient * other_coefficient > 0',
                        '(input_id == other_id or semantic == other_semantic) and coefficient * other_coefficient > 0', 1)
    text = text.replace('    cursor = result_start\n', '    cursor = result_start.toordinal()\n', 1)
    text = text.replace('        require(start <= cursor or explained,', '        require(start.toordinal() <= cursor or explained,', 1)
    text = text.replace('        cursor = max(cursor, end + timedelta(days=1))', '        cursor = max(cursor, end.toordinal() + 1)', 1)
    text = text.replace('    require(cursor > result_end or explained,', '    require(cursor > result_end.toordinal() or explained,', 1)
    return text


edit('scripts/contracts/period_flow.py', refine_period)
edit('scripts/forecast/segments.py', lambda text: text.replace('    PRESENTATIONS,\n', '').replace('    RECOGNITION_MODES,\n', '').replace('    RECOGNITION_TIMING,\n', '').replace('    validate_claim_ids,\n', ''))

# Correct the test fixture's advertised same-perimeter overlap. Preserve the
# original worker assertion in its original commit and ROOT intake report.
def correct_overlap_test(text):
    text = text.replace('def test_overlapping_components_allowed_with_explicit_rationale(self)',
                        'def test_same_perimeter_overlap_rejected_even_with_explicit_rationale(self)', 1)
    start = text.index('    def test_same_perimeter_overlap_rejected_even_with_explicit_rationale(')
    end = text.index('    def test_cross_entity_same_window_merge_rejected_without_explanation(', start)
    section = text[start:end]
    section = section.replace('2026-06-30", 2026)', '2026-06-30", 2026, definition="Segment A recognized revenue")')
    section = section.replace('        validate_document(data)\n',
                              '        with self.assertRaisesRegex(ForecastInputError, "double counts"):\n            validate_document(data)\n')
    return text[:start] + section + text[end:]


edit('tests/test_w05_dated_contribution_composition.py', correct_overlap_test)
edit('tests/test_w05_dated_contribution_contract.py', lambda text: text.replace('    unit: str = "USD million",', '    unit: str | None = None,', 1).replace('        "unit": unit,', '        "unit": unit or f"{data[\'currency\']} {data[\'unit\']}",', 1))


def correct_cny_builder(text):
    text = text.replace('from test_recognition_bridge import forecast_document  # noqa: E402',
                        'from test_recognition_bridge import forecast_document  # noqa: E402\nfrom test_w05_dated_contribution_composition import redenominated_document  # noqa: E402', 1)
    text = text.replace('def case1_acquisition() -> dict:\n    data = forecast_document()',
                        'def case1_acquisition() -> dict:\n    # Entire surrounding fixture is synthetic CNY; the sealed amount remains\n    # 1.29190208 CNY million rather than being silently relabeled USD.\n    data = redenominated_document("CNY", "million", 1.0)', 1)
    return text


edit('docs/handoffs/w05-rf-flow/e2e/build_inputs.py', correct_cny_builder)

# Matrix includes aliases so only changing a derived node's definition cannot
# launder its original semantic or physical-source identity.
EXTRA = '''

@pytest.mark.parametrize("target_definition", ["Segment A recognized revenue", "A completely renamed output"])
def test_derived_aliases_cannot_launder_same_scope_overlap(target_definition):
    data = schema_3_10_document()
    add_window_parameter(data, "actual_h1", 55.0, "2026-01-01", "2026-06-30", 2026,
                         definition="Segment A recognized revenue")
    add_window_parameter(data, "actual_q2", 30.0, "2026-04-01", "2026-06-30", 2026,
                         definition="Segment A recognized revenue")
    for name, source, value, start in (("alias_h1", "actual_h1", 55.0, "2026-01-01"),
                                      ("alias_q2", "actual_q2", 30.0, "2026-04-01")):
        add_window_parameter(data, name, value, start, "2026-06-30", 2026, kind="derived_fact", claim=False,
                             formula="x0", input_parameter_ids=[source], definition=f"Renamed {name}")
    add_window_parameter(data, "alias_sum", 85.0, "2026-01-01", "2026-06-30", 2026,
                         kind="derived_fact", claim=False, formula="x0+x1", input_parameter_ids=["alias_h1", "alias_q2"],
                         definition=target_definition, rationale="Two relabeled operands")
    with pytest.raises(ForecastInputError, match="double counts"):
        run_forecast(data)


def test_same_original_flow_cannot_be_reused_via_distinct_derived_aliases():
    data = schema_3_10_document()
    add_window_parameter(data, "original", 20.0, "2026-06-01", "2026-06-10", 2026)
    for name in ("alias_left", "alias_right"):
        add_window_parameter(data, name, 20.0, "2026-06-01", "2026-06-10", 2026,
                             kind="derived_fact", claim=False, formula="x0", input_parameter_ids=["original"],
                             definition=f"Distinct alias {name}")
    add_window_parameter(data, "double_alias", 40.0, "2026-06-01", "2026-06-10", 2026,
                         kind="derived_fact", claim=False, formula="x0+x1", input_parameter_ids=["alias_left", "alias_right"],
                         rationale="These labels are different")
    with pytest.raises(ForecastInputError, match="double counts"):
        run_forecast(data)


def test_disjoint_business_scopes_may_compose_the_same_dates_with_explanation():
    data = schema_3_10_document()
    add_window_parameter(data, "entity_a", 20.0, "2026-06-01", "2026-06-10", 2026, definition="Entity A standalone revenue")
    add_window_parameter(data, "entity_b", 15.0, "2026-06-01", "2026-06-10", 2026, definition="Entity B standalone revenue")
    add_window_parameter(data, "combined_entities", 35.0, "2026-06-01", "2026-06-10", 2026,
                         kind="derived_fact", claim=False, formula="x0+x1", input_parameter_ids=["entity_a", "entity_b"],
                         rationale="A and B are disjoint standalone businesses; no group/subsidiary duplication")
    run_forecast(data)
'''
edit('tests/test_w05_root_temporal_lineage.py', lambda text: text + EXTRA)
print('Prepared leaf lineage, overlap RED standard and CNY E2E fixture.')
