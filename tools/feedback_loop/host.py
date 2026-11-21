"""Control RPC to owner programs selected by the operator, never by source text."""

import json
import os
from pathlib import Path
import subprocess
import sys

from .coordinator import Deferred
from .observations import unique_fields


def read_hosts(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
    if not isinstance(config, dict):
        raise ValueError("expected an owner map")
    return config


def process_host(config, timeout=30, *, local=None):
    local_argv = [sys.executable, "-B", "-m", "tools.feedback_loop.local_host", "--config",
                  str(local.config), "rpc"] if local is not None else []

    def call(owner, request):
        spec = config.get(owner)
        argv = spec.get("argv") if isinstance(spec, dict) else spec
        extra = spec.get("pass_env", []) if isinstance(spec, dict) else []
        if not isinstance(argv, list) or not argv or not all(isinstance(s, str) and s for s in argv):
            raise Deferred("host_unconfigured", request["kind"])
        if not isinstance(extra, list) or not all(isinstance(name, str) for name in extra):
            raise Deferred("host_unconfigured", request["kind"])
        if local is not None and (argv == local_argv or argv == [*local_argv[:2], "-X", "utf8", *local_argv[2:]]):
            cached = local.settled_lookup(request)
            if cached is not None:
                return cached
        names = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE", "HOME", "USERPROFILE",
                 "TEMP", "TMP", "TMPDIR", "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL", *extra)
        env = {name: os.environ[name] for name in names if name in os.environ
               and name.upper() not in {"RESEARCH_FEEDBACK_OUT", "RESEARCH_FEEDBACK_HOSTS"}}
        outcome = subprocess.run(argv, input=json.dumps(request, ensure_ascii=True).encode("ascii"), env=env,
                                 capture_output=True, timeout=timeout, check=True, shell=False)
        return json.loads(outcome.stdout.decode("utf-8"), object_pairs_hook=unique_fields)
    return call
