"""One diagnostic control: bypass only OPEN_START, keep current finish logic."""
from pathlib import Path
from dataclasses import replace
from collections import Counter
import hashlib
import json
import runpy
import tempfile

HERE = Path(__file__).resolve().parent
h = runpy.run_path(str(HERE/'probe.py'), run_name='offline_helpers')
run = h['run']
G = run.__globals__
OUT = HERE/'ablation-open-start-only'
OUT.mkdir(exist_ok=False)
G['OUT'] = OUT
before = h['bindings']()
from company_wiki.document_understanding import narrative_continuity as native
from company_wiki.source_catalog import narrative_reading as reading

actual_finish = native._Analysis.finish
actual_build = reading.build_native_continuity
actual_prose = reading._prose_reading_packages
previous = {}
provenance_by_id = {}
observed = {'first_three_bypassed': [], 'bypassed_count': 0}
pages = Counter()


def capture_build(units, *, provenance, **kwargs):
    # Existing observed units only: retain transient pointers, not another
    # original/text representation or a derived source file.
    previous.clear()
    provenance_by_id.clear()
    provenance_by_id.update(provenance)
    prior = None
    for unit in units:
        previous[unit['unit_id']] = prior
        prior = unit
    return actual_build(units, provenance=provenance, **kwargs)


def skip_only_open_start(self, run, proof):
    if run and not run[0].left_closed:
        current = run[0]
        observed['bypassed_count'] += 1
        pages[current.page] += 1
        if len(observed['first_three_bypassed']) < 3:
            prev = previous.get(current.unit['unit_id'])
            pm = provenance_by_id.get(prev['unit_id'], {}) if prev else {}
            text = prev.get('text', '') if prev else ''
            observed['first_three_bypassed'].append({
                'unit_id': current.unit['unit_id'], 'page': current.page,
                'paragraph': current.paragraph, 'ordinal': current.ordinal,
                'run_member_count': len(run), 'current_text_prefix': current.unit['text'][:30],
                'current_provenance': dict(current.provenance),
                'previous_unit': None if prev is None else {
                    'unit_id': prev['unit_id'], 'page': prev.get('page'),
                    'ordinal': prev.get('ordinal'), 'kind': prev.get('kind'),
                    'text_suffix': text[-30:], 'provenance': dict(pm),
                    'terminal_actual': native._terminal(text),
                    'terminal_with_additional_closequotes': text.rstrip().rstrip(
                        '\"\'”’）)]》」』】').endswith(('。', '！', '？', '.', '!', '?', ';', '；')),
                },
                'scope': 'actual current observed native/provenance before diagnostic replacement',
            })
        # New singleton OPEN_END and all remaining current finish behavior stay.
        run = [replace(current, left_closed=True), *run[1:]]
    return actual_finish(self, run, proof)


def capture_prose(*args, **kwargs):
    result = actual_prose(*args, **kwargs)
    control = result[2]
    observed['continuity'] = {k: control.get(k) for k in ('feature_version',
        'work_units', 'observed_unit_count', 'complete', 'deferred_unit_count', 'diagnostics')}
    observed['continuity']['window_count'] = len(control.get('windows', ()))
    observed['continuity']['blocked_count'] = len(result[3])
    return result


meta = json.loads((G['MOTHER']/'.planning/shared-reading-production/du11/metadata-registered-source-facts-20261017.json').read_text(encoding='utf-8'))
sample = next(s for s in meta['samples'] if s['sample_id'] == 'hk-annual')
try:
    reading.build_native_continuity = capture_build
    reading._prose_reading_packages = capture_prose
    native._Analysis.finish = skip_only_open_start
    with tempfile.TemporaryDirectory(prefix='du11-hk-openstart-') as temporary:
        owned = Path(temporary)
        assert not list(owned.iterdir())
        record = run(sample)
        assert not list(owned.iterdir())
    observed.update(source_bindings=before, source_files_unchanged=h['bindings']() == before,
        owned_temp_removed=not owned.exists(), selected_required=record.get('selected_required'),
        canonical_required=record.get('canonical_required'), required_total=record.get('required_total'),
        diagnostic_override='Current finish; only replace(run[0], left_closed=True) in memory',
        current_finish_source_sha256=hashlib.sha256(Path(native.__file__).read_bytes()).hexdigest(),
        status='DIAGNOSTIC_ABLATION_NOT_PRODUCTION_PASS',
        bypassed_pages_top_ten=pages.most_common(10), api_calls=0, raw_copies=0)
finally:
    native._Analysis.finish = actual_finish
    reading.build_native_continuity = actual_build
    reading._prose_reading_packages = actual_prose
    (OUT/'ablation.json').write_text(json.dumps(observed, ensure_ascii=False, indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:observed.get(k) for k in ('selected_required', 'canonical_required',
        'bypassed_count', 'continuity', 'source_files_unchanged')},ensure_ascii=False),flush=True)
