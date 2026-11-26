"""Control RPC to owner programs selected by the operator, never by source text."""

import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from .coordinator import Deferred
from .observations import unique_fields


BACKGROUND_CREATION_FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
_SYSTEM_ENV = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "SYSTEMDRIVE", "HOME", "USERPROFILE",
               "TEMP", "TMP", "TMPDIR", "APPDATA", "LOCALAPPDATA", "LANG", "LC_ALL")
_HOST_ONLY_ENV = {"RESEARCH_FEEDBACK_OUT", "RESEARCH_FEEDBACK_HOSTS"}
RECONCILE_DEFERRED = "reconcile_deferred"


def read_hosts(path: Path) -> dict:
    config = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique_fields)
    if not isinstance(config, dict):
        raise ValueError("expected an owner map")
    return config


def host_environment(pass_env=(), *, source=None) -> dict[str, str]:
    values = os.environ if source is None else source
    return {name: values[name] for name in (*_SYSTEM_ENV, *pass_env)
            if name in values and name.upper() not in _HOST_ONLY_ENV}


class BatchedReconcile:
    """Collect the native read-only requests from one inbox scan."""

    def __init__(self, local):
        self.local = local
        self.groups = {}
        self.replies = {}
        self.metrics = {}
        self.collecting = True

    def lookup(self, request, *, environment):
        owner = request["owner"]
        bound = (request["action_id"], request["request_digest"])
        if not self.collecting:
            return self.replies.get(bound)
        if not self.local.supports_batch_reconcile(owner):
            return None
        _, requests = self.groups.setdefault(owner, (environment, {}))
        requests[bound] = request
        raise Deferred(RECONCILE_DEFERRED, "reconcile")

    def resolve(self):
        self.collecting = False
        for owner, (environment, requests) in self.groups.items():
            replies, measurements = self.local.reconcile_batch(owner, requests.values(), environment=environment)
            self.replies.update(replies)
            self.metrics[owner] = measurements


def process_host(config, timeout=30, *, local=None, batched_reconcile=None):
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
        env = host_environment(extra)
        if same_host:
            try:
                if batched_reconcile is not None and (request["kind"], request["method"]) == ("reconcile", "lookup"):
                    reply = batched_reconcile.lookup(request, environment=env)
                    if reply is not None:
                        return reply
                return local.handle(request, environment=env, pass_env=extra)
            except sqlite3.Error as exc:
                raise OSError("local feedback database unavailable") from exc
        outcome = subprocess.run(argv, input=json.dumps(request, ensure_ascii=True).encode("ascii"), env=env,
                                 capture_output=True, timeout=timeout, check=True, shell=False,
                                 creationflags=BACKGROUND_CREATION_FLAGS)
        return json.loads(outcome.stdout.decode("utf-8"), object_pairs_hook=unique_fields)
    return call
