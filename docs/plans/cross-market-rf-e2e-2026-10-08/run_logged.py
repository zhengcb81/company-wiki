"""Task-local subprocess ledger. Not a production entry point."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def redact(value):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    for key, secret in os.environ.items():
        if re.search(r"KEY|TOKEN|SECRET|PASSWORD", key, re.I) and len(secret) >= 8:
            text = text.replace(secret, "[REDACTED]")
    return re.sub(r"(?i)(Bearer\s+|api[_-]?key[=:]\s*)([^\s\"']+)", r"\1[REDACTED]", text)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--log-dir", required=True)
    p.add_argument("--label", required=True)
    p.add_argument("--cwd", default=os.getcwd())
    p.add_argument("--timeout", type=float, default=600)
    p.add_argument("command", nargs=argparse.REMAINDER)
    a = p.parse_args()
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd:
        p.error("command is required")
    root = Path(a.log_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    ident = f"{time.time_ns()}-{re.sub(r'[^A-Za-z0-9_.-]', '_', a.label)}"
    record = dict(id=ident, label=a.label, started_at=now(), cwd=a.cwd,
                  command=json.loads(redact(cmd)), timeout_seconds=a.timeout)
    ledger = root / "index.jsonl"
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(dict(record, event="start"), ensure_ascii=False) + "\n")
    started = time.monotonic()
    env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUTF8="1")
    try:
        result = subprocess.run(cmd, cwd=a.cwd, env=env, capture_output=True,
                                timeout=a.timeout, check=False)
        out, err, rc = result.stdout, result.stderr, result.returncode
    except subprocess.TimeoutExpired as ex:
        out, err, rc = ex.stdout or b"", ex.stderr or b"", 124
        record["error"] = "timeout"
    except OSError as ex:
        out, err, rc = b"", str(ex).encode(), 125
        record["error"] = type(ex).__name__
    files = {}
    for kind, raw in (("stdout", out), ("stderr", err)):
        data = redact(raw.decode("utf-8", errors="replace")).encode("utf-8")
        dest = root / f"{ident}.{kind}.txt"
        dest.write_bytes(data)
        files[kind] = dict(path=str(dest), byte_size=len(data), sha256=hashlib.sha256(data).hexdigest())
    record.update(event="finish", ended_at=now(), elapsed_seconds=round(time.monotonic()-started, 3),
                  returncode=rc, outputs=files)
    with ledger.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(json.dumps(record, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    sys.exit(main())
