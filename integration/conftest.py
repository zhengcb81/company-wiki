"""Explicit source-system deployment for integration tests only."""
import os
import importlib.util
from pathlib import Path
import sys
import pytest

ROOT = Path(__file__).resolve().parents[1]
FF = Path(os.environ.get("FF_V2_CODE_ROOT", ROOT.parent / "filing-fetch"))
RF = Path(os.environ.get("RF_CODE_ROOT", ROOT.parent / "revenue-forecast"))
for directory in [ROOT / "src", RF / "scripts", RF / "tests", RF / "tools",
                  FF / "scripts", FF / "tests", ROOT / "integration/revenue_forecast"]:
    sys.path.insert(0, str(directory))
os.environ["FILING_FETCH_V2_WIKI_SRC"] = str(ROOT / "src")
os.environ["FF_V2_CODE_ROOT"] = str(FF)
os.environ["RF_CODE_ROOT"] = str(RF)
os.environ["CWP_V2_CODE_ROOT"] = str(ROOT)
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
os.environ["W02_FF_CODE_ROOT"] = str(FF)
os.environ["W07_ET_TOOL"] = str(Path(os.environ.get("ET_CODE_ROOT",
    ROOT.parent / "earnings-transcripts/earnings-transcripts")) / "transcript_tool.py")

# Producer/private fixture ownership stays in ROOT even when only FF tests run.
support = ROOT / "integration/revenue_forecast/e2e_support"
spec = importlib.util.spec_from_file_location("e2e_support", support / "__init__.py",
    submodule_search_locations=[str(support)])
package = importlib.util.module_from_spec(spec)
sys.modules["e2e_support"] = package
spec.loader.exec_module(package)


@pytest.fixture(autouse=True)
def no_real_provider_credentials(monkeypatch):
    for key in ("FMP_API_KEY", "FMP_API_KEY_FILE", "MIMO_API_KEY", "DEEPSEEK_API_KEY",
                "MINIMAX_API_KEY", "OPENAI_API_KEY"):
        monkeypatch.delenv(key, raising=False)
