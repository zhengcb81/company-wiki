"""Observe ordinary Dashboard failure coverage using an isolated, read-only FF fixture.

Run with the Dashboard's Python: python -B dashboard.py PATH_TO_DASHBOARD.
No external owner, authentication, scheduler or model is used.
"""

import argparse
from contextlib import closing
import http.client
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from tempfile import TemporaryDirectory


OWNER = '''from pathlib import Path
import sys
with Path(__file__).with_name("calls.txt").open("a", encoding="utf8") as calls:
    calls.write(sys.argv[-1] + "\\n")
print("fixture-sr-reason-205", file=sys.stderr)
print('{"error":{"code":"schedule_state_unavailable","message":"fixture state unavailable"}}')
raise SystemExit(1)
'''


def inspect(root):
    observation = root / 'observations.jsonl'
    files = sorted(path for path in (root / 'data').rglob('*') if path.is_file())
    tables = {}
    for path in files:
        with path.open('rb') as stream:
            if stream.read(16) != b'SQLite format 3\0':
                continue
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True)) as db:
            for (table,) in db.execute("SELECT name FROM sqlite_master WHERE type='table'"):
                quoted = table.replace('"', '""')
                tables[table] = db.execute(f'SELECT count(*) FROM "{quoted}"').fetchone()[0]
    return {'owner_calls': (root / 'owner/scripts/calls.txt').read_text().splitlines(),
            'supplied_sidecar_exists': observation.is_file(),
            'supplied_sidecar_rows': len(observation.read_bytes().splitlines()) if observation.is_file() else 0,
            'data_files': [str(path.relative_to(root / 'data')) for path in files], 'table_rows': tables}


def run(dashboard, root):
    script = root / 'owner/scripts/ff_scheduled_refresh.py'
    script.parent.mkdir(parents=True)
    script.write_text(OWNER, encoding='utf8')
    data = root / 'data'
    data.mkdir()
    env = {key: os.environ[key] for key in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TEMP', 'TMP', 'USERPROFILE',
                                              'LOCALAPPDATA', 'APPDATA', 'COMSPEC', 'HOME') if key in os.environ}
    env.update(DASHBOARD_FF_SCHEDULED_ROOT=str(script.parent.parent), DASHBOARD_FF_SCHEDULED_PYTHON=sys.executable,
               RESEARCH_FEEDBACK_OUT=str(root / 'observations.jsonl'), RESEARCH_FEEDBACK_RUN_ID='dash-failure-audit',
               RESEARCH_FEEDBACK_ATTEMPT_ID='attempt-1', PYTHONDONTWRITEBYTECODE='1', PYTHONUTF8='1')
    process = subprocess.Popen([sys.executable, '-B', '-m', 'backend.dashboard.main', '--mode', 'owner', '--port', '0',
                                '--data-dir', str(data)], cwd=dashboard, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE, encoding='utf8')
    results = []
    try:
        banner = process.stdout.readline()
        address = re.search(r'127\.0\.0\.1:(\d+)', banner)
        if not address:
            raise RuntimeError('Dashboard startup failed: ' + process.stderr.read())
        for path in ('scheduled-refresh', 'scheduled-refresh/runs', 'jobs', 'capabilities?unexpected_probe_q=yes',
                     'not-a-public-route'):
            with closing(http.client.HTTPConnection('127.0.0.1', int(address[1]), timeout=10)) as conn:
                conn.request('GET', '/api/v1/' + path)
                response = conn.getresponse()
                body = json.loads(response.read())
                results.append({'request': path, 'status': response.status, 'code': body.get('code'),
                                'dispatch_state': body.get('dispatch_state'),
                                'returned_correlation_id': bool(body.get('correlation_id'))})
    finally:
        process.terminate()
        stdout, stderr = process.communicate(timeout=10)
    readback = subprocess.check_output([sys.executable, '-B', str(Path(__file__).resolve()), '--inspect', str(root)],
                                       env=env, encoding='utf8')
    return {'http': results, 'after_server_exit': json.loads(readback),
            'access_log_requests': (stdout + stderr).count('HTTP/1.1'),
            'child_marker_in_server_streams': 'fixture-sr-reason-205' in stdout + stderr}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--inspect', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.inspect:
        print(json.dumps(inspect(args.path)))
    else:
        with TemporaryDirectory(prefix='f4-dash-audit-') as directory:
            print(json.dumps(run(args.path.resolve(), Path(directory).resolve()), indent=2))
