"""Only this explicit system suite loads producer and consumer implementations."""
import os
import importlib.util
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
CWP = HERE.parents[1]
RF = Path(os.environ.get("RF_CODE_ROOT", CWP.parent / "revenue-forecast"))
FF = Path(os.environ.get("FF_V2_CODE_ROOT", CWP.parent / "filing-fetch"))
for path in [CWP / "src", RF / "scripts", RF / "tests", RF / "tools", FF / "scripts", HERE]:
    sys.path.insert(0, str(path))
os.environ["PYTHONPATH"] = str(CWP / "src")
os.environ["CWP_V2_CODE_ROOT"] = str(CWP)
os.environ["FF_V2_CODE_ROOT"] = str(FF)
os.environ["PYTHONUTF8"] = "1"
os.environ["PYTHON_DOTENV_DISABLED"] = "1"
spec = importlib.util.spec_from_file_location("e2e_support", HERE / "e2e_support/__init__.py",
    submodule_search_locations=[str(HERE / "e2e_support")])
package = importlib.util.module_from_spec(spec)
sys.modules["e2e_support"] = package
spec.loader.exec_module(package)
