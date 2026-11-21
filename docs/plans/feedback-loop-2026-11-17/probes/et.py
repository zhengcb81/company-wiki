"""Offline ET failure census. Run with the ET Python and the ET checkout as argv[1]."""

import json
import os
from collections import Counter
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[4]


def readback(folder):
    sidecar = folder / 'observations.jsonl'
    details = folder / 'observations.jsonl.details.jsonl'
    args = [sys.executable, '-B', '-m', 'tools.feedback_loop', 'plan', str(sidecar)]
    cases = json.loads(subprocess.check_output(args, cwd=ROOT)) if sidecar.exists() else {'observations': []}
    observations = cases['observations']
    native = [json.loads(row) for row in details.read_bytes().splitlines()] if details.exists() else []
    report = folder / 'report/transcript_audit_report.json'
    return {'checks': dict(Counter(r['disposition'] for r in observations)),
            'refusal_rows': sum('refusal_code' in r for r in observations),
            'details_rows': len(native), 'native_codes': sorted({r['error_type'] for r in native if r.get('error_type')}),
            'txt_report': json.loads(report.read_text(encoding='utf8'))['counts'] if report.is_file() else None}


def census(et, root):
    env = {k: os.environ[k] for k in ('PATH', 'PATHEXT', 'COMSPEC', 'SYSTEMROOT', 'WINDIR', 'SYSTEMDRIVE') if k in os.environ}
    guard = root / 'guard'
    guard.mkdir()
    (guard / 'sitecustomize.py').write_text("import sys\ndef guard(event, args):\n if event in ('socket.connect','socket.getaddrinfo'): raise RuntimeError('audit forbids external access')\nsys.addaudithook(guard)\n", encoding='utf8')
    env.update(TEMP=str(root), TMP=str(root), TMPDIR=str(root), PYTHONPATH=str(guard),
               PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    tests = [('bad-cli', ['transcript_tool.py', '--operation', 'bad'], ''),
             ('bad-wire', ['transcript_tool.py', '--request-stdin', '--report-usage'], '{'),
             ('scraper', ['scraper.py', '--periods', 'not-a-period'], ''),
             ('txt-root', ['transcript_audit.py', '--root', '{case}/absent'], ''),
             ('corrupt-txt', ['transcript_audit.py', '--root', '{case}/txt', '--report-dir', '{case}/report'], ''),
             ('worker-loss', ['tools/run_request_budget_e2e.py', '--case', 'worker-loss'], ''),
             ('account-refusal', ['tools/replay_feedback_case.py', '--case', 'fmp-entitlement-402', '--out', '{case}/observations.jsonl'], ''),
             ('lost-receipt', ['tools/replay_feedback_case.py', '--case', 'usage-receipt-suppressed', '--out', '{case}/observations.jsonl'], '')]
    results = []
    for name, (script, *args), data in tests:
        folder = root / name
        folder.mkdir()
        if name == 'corrupt-txt':
            (folder / 'txt').mkdir()
            (folder / 'txt/ACME_Q3_2026_earnings_call.txt').write_bytes(b'\xff\x00')
            (folder / 'report').mkdir()
        argv = [sys.executable, '-B', str(et / script), *(arg.replace('{case}', str(folder)) for arg in args)]
        env.update(RESEARCH_FEEDBACK_OUT=str(folder / 'observations.jsonl'), RESEARCH_FEEDBACK_RUN_ID='et-census-' + name,
                   RESEARCH_FEEDBACK_ATTEMPT_ID='one')
        response = subprocess.run(argv, input=data, capture_output=True, cwd=folder, env=env, encoding='utf8', timeout=32)
        if name in ('worker-loss', 'account-refusal', 'lost-receipt') and response.returncode:
            raise RuntimeError('ET fixture did not complete: ' + name + '\n' + response.stderr)
        output = json.loads(response.stdout) if response.stdout.lstrip().startswith('{') else {}
        business = output.get('native', output)
        observed = subprocess.check_output([sys.executable, '-B', str(Path(__file__).resolve()), '--read', str(folder)],
                                           cwd=ROOT, env=env, timeout=15)
        results.append({'case': name, 'exit': response.returncode, 'business': business.get('status'),
                        'code': business.get('error_code'), **json.loads(observed)})
    return results


if __name__ == '__main__':
    if sys.argv[1] == '--read':
        print(json.dumps(readback(Path(sys.argv[2]))))
    else:
        with TemporaryDirectory(prefix='et-f4-') as tmp:
            print(json.dumps(census(Path(sys.argv[1]).resolve(), Path(tmp).resolve()), indent=2))
