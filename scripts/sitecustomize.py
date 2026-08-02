"""Interpreter-start fence for every directly executed script in scripts/."""

from __future__ import annotations

import os
import sys

from writer_policy import enforce_direct_cli


try:
    enforce_direct_cli("__main__", sys.argv[0])
except SystemExit as exc:
    # Raising SystemExit while Python imports sitecustomize is reported as a
    # fatal site initialization error with a platform-dependent exit code.
    # Flush the policy message and terminate with the stable contract code.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(int(exc.code))

