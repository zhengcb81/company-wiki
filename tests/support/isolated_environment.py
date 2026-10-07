"""Test-only environment isolation helpers migrated from ``clean_env_gate``.

``scripts/clean_env_gate.py`` retired in G5-CWP-CHECKS, but the environment
its gate used to sanitise is still consumed by the hermetic runtime tests:
API keys must be stripped, dotenv must stay disabled and the network/model
switches must be pinned.  This module is a test support file — it is not a
production module and it adds no user permission switch.  It uses only the
Python standard library and never reads repository credentials.
"""

from __future__ import annotations

import os


def sanitized_environment() -> dict[str, str]:
    """Return an environment with credentials removed and hermetic pins set."""
    environment = {
        key: value
        for key, value in os.environ.items()
        if not key.upper().endswith("_API_KEY")
        and key.upper()
        not in {
            "OPENAI_API_KEY",
            "DEEPSEEK_API_KEY",
            "MINIMAX_API_KEY",
            "MIMO_API_KEY",
            "TAVILY_API_KEY",
            "COMPANY_WIKI_WRITE_MODE",
            "COMPANY_WIKI_LEGACY_WRITERS",
        }
    }
    environment.update(
        {
            "PIP_NO_INDEX": "1",
            "PIP_DISABLE_PIP_VERSION_CHECK": "1",
            "COMPANY_WIKI_REAL_LLM": "0",
            "COMPANY_WIKI_NETWORK": "blocked",
            "PYTHON_DOTENV_DISABLED": "1",
            "NO_PROXY": "*",
        }
    )
    return environment
