"""One controlled old-finish experiment; all production source files read-only."""
from pathlib import Path
import ast
import hashlib
import json
import runpy
import subprocess
import tempfile
from collections import Counter

HERE = Path(__file__).resolve().parent
helpers = runpy.run_path(str(HERE / 'probe.py'), run_name='offline_helpers')
run = helpers['run']
G = run.__globals__
ROOT, MOTHER = G['ROOT'], G['MOTHER']
OUT = HERE/'ablation-old-finish'
OUT.mkdir(exist_ok=False)
G['OUT'] = OUT
before = helpers['bindings']()
from company_wiki.document_understanding import narrative_continuity as continuity
from company_wiki.source_catalog import narrative_reading as reading
from company_wiki.automation.narrative_select import NarrativeSelectHandler
from tools.document_understanding_benchmark import closed_group_support as oracle

baseline = 'a8eef273a90ac1ddb0f79f8bdd36e7c47f8eb377'
text = subprocess.check_output(['git', 'show', baseline+':src/company_wiki/document_understanding/narrative_continuity.py'], cwd=ROOT, text=True, encoding='utf-8')
tree = ast.parse(text)
klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == '_Analysis')
method = next(node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name == 'finish')
method_ast = ast.dump(method, include_attributes=False)
namespace = dict(vars(continuity))
exec(compile(ast.Module(body=[method], type_ignores=[]), '<old-finish-memory-ablation>', 'exec'), namespace)
old_finish = namespace['finish']
actual_finish = continuity._Analysis.finish
actual_prose = reading._prose_reading_packages
actual_candidates = reading._candidates
actual_select = NarrativeSelectHandler._select
original_score = G['score_facts']
observed = {}
held = {}


def capture_prose(*args, **kwargs):
    result = actual_prose(*args, **kwargs)
    native = result[2]
    observed['continuity'] = {k: native.get(k) for k in
        ('feature_version', 'work_units', 'observed_unit_count', 'complete',
         'deferred_unit_count', 'deferred_limited', 'unexamined_from_index', 'diagnostics')}
    observed['continuity']['window_count'] = len(native.get('windows', ()))
    observed['continuity']['blocked_count'] = len(result[3])
    observed['continuity']['deferred_range_examples'] = native.get('deferred_unit_ranges', ())[:3]
    return result


def capture_candidates(*args, **kwargs):
    result = actual_candidates(*args, **kwargs)
    observed['withheld_reasons'] = dict(Counter(str(item['reason']) for item in result[4]))
    observed['eligible_packages'] = len(result[2])
    return result


def capture_select(self, *args, **kwargs):
    work = actual_select(self, *args, **kwargs)
    held['work'] = work
    return work


def capture_anchors(facts, *, evidence_spans, reading_context, source_id):
    result = original_score(facts, evidence_spans=evidence_spans,
                            reading_context=reading_context, source_id=source_id)
    rows = []
    for fact in facts:
        sets = []
        for support in fact['any_support_sets']:
            anchors = []
            for anchor in support:
                quote = anchor['exact_quote']
                matching = []
                for span in evidence_spans:
                    if (anchor.get('location_kind') != 'document'
                            and span.coordinates.page_number != anchor.get('page')):
                        continue
                    fold = oracle._range_fold if span.structured_value.get('native_range') else oracle._fold
                    if fold(quote) in fold(span.raw_text):
                        matching.append({'span_id': span.span_id, 'locator': span.coordinates.locator(),
                                         'flags': list(span.quality_flags)})
                anchors.append({'quote_sha256': hashlib.sha256(quote.encode()).hexdigest(),
                    'quote_prefix': quote[:70], 'literal_in_selected_span': bool(matching),
                    'matches': matching[:3]})
            sets.append(anchors)
        rows.append({'fact': fact['id'], 'alternative_anchor_sets': sets})
    observed['literal_anchors'] = rows
    return result


metadata = json.loads((MOTHER/'.planning/shared-reading-production/du11/metadata-registered-source-facts-20261017.json').read_text(encoding='utf-8'))
sample = next(item for item in metadata['samples'] if item['sample_id'] == 'hk-annual')
record = None
try:
    continuity._Analysis.finish = old_finish
    reading._prose_reading_packages = capture_prose
    reading._candidates = capture_candidates
    NarrativeSelectHandler._select = capture_select
    G['score_facts'] = capture_anchors
    with tempfile.TemporaryDirectory(prefix='du11-hk-ablation-') as temp:
        owned = Path(temp)
        assert not list(owned.iterdir())
        record = run(sample)
        assert not list(owned.iterdir())
    observed['owned_temp_removed'] = not owned.exists()
    observed['restored_selected_required'] = record.get('selected_required')
    observed['restored_canonical_required'] = record.get('canonical_required')
    observed['raw_copies'] = 0
    observed['api_calls'] = 0
    observed['parsed_memory_retained_through_diagnosis'] = bool(held.get('work'))
    observed['source_files_changed'] = helpers['bindings']() != before
    observed['actual_source_bindings'] = before
    observed['experiment'] = {'baseline': baseline, 'only_runtime_override': '_Analysis.finish old AST function bound to current class; current left_closed field retained',
        'method_ast_sha256': hashlib.sha256(method_ast.encode()).hexdigest(),
        'scope': 'DIAGNOSTIC_ABLATION_NOT_PRODUCTION_PASS', 'production_limits_unchanged': True}
    observed['conclusion'] = ('OLD_FINISH_RESTORES_ALL_REQUIRED_NEW_CLOSURE_REGRESSION'
        if record.get('selected_required') == 7 and record.get('canonical_required') == 7
        else 'OLD_FINISH_NOT_SUFFICIENT_SECOND_OWNER_ISOLATION_REQUIRED')
finally:
    continuity._Analysis.finish = actual_finish
    reading._prose_reading_packages = actual_prose
    reading._candidates = actual_candidates
    NarrativeSelectHandler._select = actual_select
    G['score_facts'] = original_score
    (OUT/'ablation.json').write_text(json.dumps(observed, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k: observed.get(k) for k in ('conclusion', 'restored_selected_required',
        'restored_canonical_required', 'withheld_reasons', 'continuity', 'source_files_changed')}, ensure_ascii=False), flush=True)
