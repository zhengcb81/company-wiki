"""Offline engineering wire probe, never an RF research-adoption assertion."""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[3]
RF = ROOT.parent / 'revenue-forecast'
sys.path[:0] = [str(ROOT / 'src'), str(ROOT / 'tests'), str(RF / 'scripts')]
from unit.test_atomic_summary_artifacts import materials
from unit.test_narrative_source_owned_model_boundary import official_reading
from company_wiki.automation.narrative_verify import NarrativeVerifyHandler
from narrative_summary_observations import validate_summary_observation

rows = []
for version in ['reading-model-input/6', 'reading-model-input/7']:
    for projected in [False, True]:
        source, summary, _ = materials(official_reading() if projected else None, version=version)
        wire = NarrativeVerifyHandler._bundle(source, summary, source.prompt_review,
                                               reading_projection_version=version).to_dict()
        report = validate_summary_observation(wire)
        assert report == wire['summary_assessment']
        actual = report['validator']['version']
        report['validator']['version'] = ('source-summary-assessment/1.0.0'
            if actual.endswith('1.1.0') else 'source-summary-assessment/1.1.0')
        wire['summary_assessment'] = report
        try:
            validate_summary_observation(wire)
        except ValueError:
            rejected = True
        else:
            raise AssertionError('mixed prompt/assessor was accepted')
        rows.append({'projection': version, 'projected': projected, 'assessor': actual,
                     'actual_producer_wire_accepted': True, 'mixed_assessor_rejected': rejected})
result = {'status': 'PASS', 'scope': 'offline wire only; no forecast consumption', 'cases': rows,
          'model_posts': 0, 'downloads': 0, 'pdf_parses': 0}
Path(__file__).with_name('rf-actual-producer-wire.json').write_text(
    json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps(result, ensure_ascii=False))
