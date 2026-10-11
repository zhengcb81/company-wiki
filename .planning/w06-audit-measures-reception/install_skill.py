"""Narrow sync using the project's existing tool, with exact before/after receipts."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

PROJECT = Path('C:/Users/郑曾波/Projects/revenue-forecast-audit')
ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-audit-measures-acceptance'
EXPECTED = {'SKILL.md', 'references/review-process.md', 'references/review-analyst.md',
            'references/financial-measure-audit.md', 'scripts/financial_measure_audit.py'}
DESTINATIONS = [Path.home() / '.claude/skills/revenue-forecast-audit',
                Path.home() / '.agents/skills/revenue-forecast-audit']
SPEC = importlib.util.spec_from_file_location('audit_narrow_sync', PROJECT / 'tools/sync_skill.py')
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)

def digest(data):
    return hashlib.sha256(data).hexdigest()

def head():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=PROJECT, text=True).strip()

def installed(files, destination):
    return {name: digest((destination/name).read_bytes()) if (destination/name).is_file() else None
            for name in files}

def persist(name, value):
    path = EVIDENCE/name
    assert not path.exists(), f'receipt already exists: {path}'
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

if sys.argv[1:] == ['--preview']:
    baseline = sync.package_files(PROJECT/'skills/revenue-forecast-audit')
    assert len(baseline) == 24
    expected = {name: digest(data) for name, data in baseline.items()}
    before = {'head': head(), 'baseline_files': expected, 'destinations': {}}
    for destination in DESTINATIONS:
        hashes = installed(baseline, destination)
        assert hashes == expected, f'pre-existing installed drift: {destination}'
        before['destinations'][str(destination)] = hashes
    persist('installation-before.json', before)
    print('24 existing files x 2 installed copies MATCH; no writes')
elif sys.argv[1:] == ['--sync']:
    before = json.loads((EVIDENCE/'installation-before.json').read_text(encoding='utf-8'))
    files = sync.package_files(PROJECT/'skills/revenue-forecast-audit')
    assert len(files) == 26
    assert {name for name, data in files.items()
            if before['baseline_files'].get(name) != digest(data)} == EXPECTED
    for destination in DESTINATIONS:
        assert installed(before['baseline_files'], destination) == before['destinations'][str(destination)]
        assert all(not (destination/name).exists() for name in EXPECTED-set(before['baseline_files']))
    results = []
    for destination in DESTINATIONS:
        result = sync.synchronize(PROJECT/'skills/revenue-forecast-audit', destination)
        assert set(result['changed']) == EXPECTED
        assert not sync.synchronize(PROJECT/'skills/revenue-forecast-audit', destination, check=True)['mismatches']
        assert installed(files, destination) == {name: digest(data) for name, data in files.items()}
        results.append(result)
    persist('installation-after.json', {'head': head(), 'files_per_copy':26,
            'changed_per_copy':sorted(EXPECTED), 'installations':results,
            'configuration_and_output_preserved':True})
    print('26 files x 2 MATCH; only 5 named package files/copy and manifest changed')
else:
    raise SystemExit('choose --preview or --sync')
