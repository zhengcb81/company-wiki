"""Explicit test subprocess hook: prohibit remote sockets, log argv, never env."""
import json
import os
from pathlib import Path
import socket
import subprocess

if os.environ.get("CMRF_PROCESS_LOG"):
    original = subprocess.Popen.__init__

    def traced(self, args, *rest, **kwargs):
        original(self, args, *rest, **kwargs)
        path = Path(os.environ["CMRF_PROCESS_LOG"]) / (str(os.getpid()) + ".jsonl")
        with path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"parent_pid": os.getpid(), "pid": self.pid,
                                     "argv": args, "cwd": str(kwargs.get("cwd", ""))}) + "\n")

    subprocess.Popen.__init__ = traced

if os.environ.get("CMRF_OFFLINE") == "1":
    connect = socket.socket.connect

    def local_only(self, address):
        if not isinstance(address, tuple) or address[0] not in {"127.0.0.1", "::1", "localhost"}:
            raise RuntimeError("cross-market replay forbids external network")
        return connect(self, address)

    socket.socket.connect = local_only
