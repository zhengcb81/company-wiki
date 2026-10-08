"""Enable task-only process tracing with CWP_AUDIT_PROCESS_DIR."""
import atexit
import datetime
import json
import os
from pathlib import Path
import re
import sys

trace = os.environ.get('CWP_AUDIT_PROCESS_DIR')
if trace:
    root = Path(trace)
    root.mkdir(parents=True, exist_ok=True)
    dest = root / f'process-{os.getpid()}.jsonl'

    def emit(event, data):
        raw = json.dumps(data, ensure_ascii=False, default=str)
        for key, value in os.environ.items():
            if re.search('KEY|TOKEN|SECRET|PASSWORD', key, re.I) and len(value) >= 8:
                raw = raw.replace(value, '[REDACTED]')
        with dest.open('a', encoding='utf-8') as f:
            f.write(json.dumps({'timestamp_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
                                'pid': os.getpid(), 'ppid': os.getppid(), 'event': event,
                                'data': json.loads(raw)}, ensure_ascii=False) + '\n')

    emit('python_start', {'executable': sys.executable, 'argv': sys.argv, 'cwd': os.getcwd()})

    def audit(event, args):
        if event == 'subprocess.Popen':
            emit('subprocess_spawn', {'executable': args[0], 'argv': args[1], 'cwd': args[2]})

    sys.addaudithook(audit)
    atexit.register(emit, 'python_exit', {})
