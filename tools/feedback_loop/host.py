"""Control RPC to owner programs selected by the operator, never by source text."""

import json
import os
from pathlib import Path
import subprocess
import sys

from .coordinator import Deferred
from .observations import unique_fields


BACKGROUND_CREATION_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def read_hosts(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
    if not isinstance(config, dict):
        raise ValueError("expected an owner map")
    return config


def process_host(config, timeout=30, *, local=None):
    local_argv = ["-B", "-m", "tools.feedback_loop.local_host", "--config",
                  str(local.config), "rpc"] if local is not None else []
    executable = Path(sys.executable)
    launchers = {executable}
    if os.name == "nt" and executable.name.lower() in ("python.exe", "pythonw.exe"):
        launchers.update(executable.with_name(name) for name in ("python.exe", "pythonw.exe"))

    def call(owner, request):
        spec = config.get(owner)
        argv = spec.get("argv") if isinstance(spec, dict) else spec
        extra = spec.get("pass_env", []) if isinstance(spec, dict) else []
        if not isinstance(argv, list) or not argv or not all(isinstance(s, str) and s for s in argv):
            raise Deferred("host_unconfigured", request["kind"])
        if not isinstance(extra, list) or not all(isinstance(name, str) for name in extra):
            raise Deferred("host_unconfigured", request["kind"])
        same_host = (local is not None and Path(argv[0]) in launchers
                     and argv[1:] in (local_argv, ["-B", "-X", "utf8", *local_argv[1:]]))
        if same_host:
            cached = local.settled_lookup(request)
            if cached is not None:
                return cached
        names = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE", "HOME", "USERPROFILE",
                 "TEMP", "TMP", "TMPDIR", "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL", *extra)
        env = {name: os.environ[name] for name in names if name in os.environ
               and name.upper() not in {"RESEARCH_FEEDBACK_OUT", "RESEARCH_FEEDBACK_HOSTS"}}
        if same_host and local.recovery_owners:
            from .local_host import RECOVERY_OWNERS_ENV
            env[RECOVERY_OWNERS_ENV] = " ".join(local.recovery_owners)
        if same_host and request["method"] == "lookup" and request["kind"] == "reconcile":
            return local.handle(request, environment=env)
        outcome = subprocess.run(argv, input=json.dumps(request, ensure_ascii=True).encode("ascii"), env=env,
                                 capture_output=True, timeout=timeout, check=True, shell=False,
                                 creationflags=BACKGROUND_CREATION_FLAGS)
        return json.loads(outcome.stdout.decode("utf-8"), object_pairs_hook=unique_fields)
    return call
