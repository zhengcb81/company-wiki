"""One changed-source IPO replay; same account/caps, reserve-caller diagnostics."""
from collections import Counter
from dataclasses import asdict
from functools import wraps
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'src'))
from company_wiki.resource_budget import WorkBudget, WorkBudgetExceeded, budget_policy_path, new_document_work_budget
from company_wiki.document_understanding import pipeline
from company_wiki.document_understanding.geometry_intent.reading import PdfReadingContext
from company_wiki.source_catalog import narrative_evidence as engine, narrative_reading as reading
from company_wiki.source_catalog.config import load_catalog_config
from company_wiki.source_catalog.service import SourceCatalog
from company_wiki.source_catalog.source_reader import SourceRef, SourceVersionReader

NODE = ROOT / 'docs/plans/du11-source-closure-2026-10-18/review/cf-source-20261025'
BASE = NODE.parent / 'local-flow-cross-market-20261025/cn-ipo.json'
BASE_CHARGE = WorkBudget.charge.__code__


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot():
    paths = sorted((ROOT / 'src/company_wiki').rglob('*.py'))
    paths.append(ROOT / 'src/company_wiki/document_understanding/profiles/reading_catalog.json')
    return {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}


def location(frame):
    path = Path(frame.f_code.co_filename)
    return (path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.name,
            frame.f_code.co_name, frame.f_lineno)


class ProfileBudget(WorkBudget):
    def __post_init__(self):
        super().__post_init__()
        self.accepted, self.rejected = Counter(), Counter()
        self.unresolved = 0

    def charge(self, n=1):
        frame = sys._getframe(1)
        try:
            for _ in range(4):
                if frame.f_code is not BASE_CHARGE:
                    break
                frame = frame.f_back
            if frame.f_code is BASE_CHARGE:
                self.unresolved += 1
            direct = location(frame)
            # One known reservation helper only; bounded constant-depth access.
            if direct[0].endswith('structure/_work.py') and direct[1] == 'reserve':
                frame = frame.f_back
            caller = location(frame)
            key = direct, caller
        finally:
            del frame
        before = self.used
        try:
            return super().charge(n)
        except WorkBudgetExceeded:
            self.rejected[key] += n
            raise
        finally:
            self.accepted[key] += self.used - before


def main():
    output = NODE / 'cf3-ipo-replay.json'
    if output.exists():
        raise FileExistsError(output)
    baseline = json.loads(BASE.read_text(encoding='utf-8'))
    cfg_path = ROOT / 'config/source_catalog.yaml'
    cfg = load_catalog_config(cfg_path, project_root=ROOT)
    protected = [cfg_path, cfg.database_path, budget_policy_path()]
    protected_before = {p.relative_to(ROOT).as_posix(): sha(p) for p in protected}
    source_before = snapshot()
    configured = new_document_work_budget()
    assert configured.used == 0 and configured.max_work_units == 16_000_000
    budget = ProfileBudget(configured.max_work_units, phase=configured.phase)
    stages, restores = [], []

    def instrument(owner, name, label, wrapper=None):
        original = getattr(owner, name)
        if wrapper is None:
            @wraps(original)
            def wrapper(*args, **kwargs):
                entry, start = budget.used, time.monotonic()
                try:
                    return original(*args, **kwargs)
                finally:
                    stages.append({'stage': label, 'inclusive_work': budget.used-entry,
                                   'wall_seconds_diagnostic': round(time.monotonic()-start, 4)})
        restores.append((owner, name, original))
        setattr(owner, name, wrapper)
        return wrapper

    instrument(reading, '_understand', 'reading._understand')
    wrapper = instrument(reading, 'understand_units', 'pipeline.understand_units')
    instrument(pipeline, 'understand_units', 'pipeline.understand_units', wrapper)
    instrument(reading, '_candidates', 'reading._candidates')
    catalog = SourceCatalog(cfg)
    parsed = package = None
    error = parse_work = None
    start = time.monotonic()
    try:
        ref = SourceRef(**baseline['source_ref'])
        verified = SourceVersionReader(catalog).open_version(ref, purpose='preview')
        assert hashlib.sha256(verified.data).hexdigest() == ref.content_sha256
        parsed = engine.parse_pdf_bytes(verified.data, source_id=ref.source_id,
            source_sha256=ref.content_sha256, language=baseline['language'], selector_version='0.9.0',
            reading_context=PdfReadingContext(baseline['title'], baseline['declared_kind'], baseline['language']),
            work_budget=budget)
        parse_work = budget.used
        if not budget.exhausted:
            package = engine.select_narrative_evidence(parsed, title=baseline['title'],
                existing_kind=baseline['declared_kind'], max_selected=112,
                selector_version='0.9.0', work_budget=budget)
    except WorkBudgetExceeded as exc:
        error = {k: getattr(exc, k, None) for k in ('phase', 'used', 'requested', 'limit')}
    finally:
        for owner, name, original in reversed(restores):
            setattr(owner, name, original)
        write_store_constructed = catalog._store is not None
        catalog.close()
    protected_after = {p.relative_to(ROOT).as_posix(): sha(p) for p in protected}
    assert protected_before == protected_after and source_before == snapshot()
    assert not write_store_constructed and sum(budget.accepted.values()) == budget.used and budget.unresolved == 0
    quotes = [{'span_id': s.span_id, 'locator': s.locator, 'page': s.coordinates.page_number,
               'quote': s.raw_text, 'quality_flags': list(s.quality_flags)} for s in package.evidence_spans] if package else []
    assert len(quotes) <= 112
    keys = set(budget.accepted) | set(budget.rejected)
    hot = [{'direct': k[0], 'reserve_caller': k[1], 'accepted_work': budget.accepted[k],
            'rejected_requested': budget.rejected[k]} for k in sorted(keys, key=lambda x: (-budget.accepted[x], x))]
    result = {'schema_version': 'cf3-source-replay/1', 'source_ref': asdict(ref),
        'head': subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,encoding='utf-8').strip(),
        'source_sha256': source_before, 'runner_sha256': sha(Path(__file__)), 'baseline_sha256': sha(BASE),
        'parsed_units': len(parsed.units) if parsed else None, 'parsed_pages': parsed.page_count if parsed else None,
        'parse_work': parse_work, 'work_used': budget.used, 'work_limit': budget.max_work_units,
        'exhausted': budget.exhausted, 'status': package.status if package else None,
        'candidate_count': package.candidate_count if package else None, 'selected_count': len(quotes),
        'budget_exception': error, 'stages_inclusive_do_not_sum': stages, 'caller_hotspots': hot,
        'selected_quotes': quotes, 'content_grade': 'NOT_GRADED_NO_FORMAL_IPO_GOLD',
        'wall_seconds_diagnostic_not_benchmark': round(time.monotonic()-start, 4),
        'protected_sha256': protected_before, 'protected_unchanged': True, 'write_store_constructed': False,
        'source_code_stable': True, 'hooks_restored': all(getattr(o,n) is v for o,n,v in restores),
        'accepted_work_equals_account': True, 'calls': {'model':0,'api':0,'download':0,'raw_copy':0}}
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ('parsed_units','parsed_pages','parse_work','work_used','exhausted','status','candidate_count','selected_count','stages_inclusive_do_not_sum','wall_seconds_diagnostic_not_benchmark')},ensure_ascii=False))
    print(json.dumps(hot[:16],ensure_ascii=False))


if __name__ == '__main__':
    main()
