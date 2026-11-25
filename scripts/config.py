"""Compatibility entry for maintenance scripts using the runtime config."""

from importlib.util import find_spec
from pathlib import Path
import sys

# Keep bare-checkout maintenance launches working when only scripts/ is on
# PYTHONPATH. Package entry points never import this compatibility module.
if find_spec("company_wiki") is None:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from company_wiki import runtime_config

if __name__ == "__main__":
    raise SystemExit(runtime_config.main())

sys.modules[__name__] = runtime_config
