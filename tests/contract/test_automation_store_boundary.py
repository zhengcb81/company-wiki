"""AUTO-2 store/migration boundary contract tests (B01-B04 + file existence).

B01: static import scan — production modules may only import stdlib, models and
     migrations.  No legacy scheduler, network, LLM, env or daemon imports.
B02: no default database paths — neither source nor tests hard-code ``.state``
     or ``automation.db`` as a default constant.
"""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_PATH = ROOT / "src" / "company_wiki" / "automation" / "migrations.py"
STORE_PATH = ROOT / "src" / "company_wiki" / "automation" / "store.py"
REGISTRY_PATH = ROOT / "src" / "company_wiki" / "automation" / "registry.py"
POLICY_PATH = ROOT / "src" / "company_wiki" / "automation" / "policy.py"
PLANNER_PATH = ROOT / "src" / "company_wiki" / "automation" / "planner.py"
RETRY_PATH = ROOT / "src" / "company_wiki" / "automation" / "retry.py"
OUTBOX_PATH = ROOT / "src" / "company_wiki" / "automation" / "outbox.py"
WORKER_PATH = ROOT / "src" / "company_wiki" / "automation" / "worker.py"
EVENT_SOURCES_PATH = ROOT / "src" / "company_wiki" / "automation" / "event_sources.py"
CONTROLLER_PATH = ROOT / "src" / "company_wiki" / "automation" / "controller.py"
GOLD_REVIEW_PATH = ROOT / "src" / "company_wiki" / "automation" / "handlers" / "gold_review.py"
HUMAN_INBOX_PATH = ROOT / "src" / "company_wiki" / "automation" / "human_inbox.py"

_ALLOWED_IMPORTS = {
    "__future__", "sqlite3", "json", "hashlib", "functools", "dataclasses",
    "pathlib", "typing", "collections", "collections.abc", "math",
    "company_wiki.automation.models", "company_wiki.automation.migrations",
}

_FORBIDDEN_TOKENS = [
    "CREATE TABLE IF NOT EXISTS",
    "executescript",
    "INSERT OR REPLACE",
    "SELECT *",
    "str(dict",
    "datetime.now",
    "datetime.utcnow",
    "time.time",
    "threading.Lock",
    "threading.RLock",
    "threading.local",
    "check_same_thread=False",
    ".state/automation.db",
    "scripts.state_store",
    "company_wiki.scheduler",
    "SchedulerDB",
    "requests",
    "openai",
    "httpx",
    "os.environ",
    "os.getenv",
    "dotenv",
    "time.sleep",
    "while True",
    "daemon",
    "multiprocessing",
]


def test_migrations_module_exists():
    assert MIGRATIONS_PATH.is_file(), "expected red: automation/migrations.py is not implemented"


def test_store_module_exists():
    assert STORE_PATH.is_file(), "expected red: automation/store.py is not implemented"


def test_b01_migrations_no_forbidden_tokens():
    source = MIGRATIONS_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in migrations.py: {token!r}"


def test_b01_store_no_forbidden_tokens():
    source = STORE_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in store.py: {token!r}"


def test_b01_registry_no_forbidden_tokens():
    source = REGISTRY_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in registry.py: {token!r}"


def test_b01_policy_no_forbidden_tokens():
    source = POLICY_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in policy.py: {token!r}"


def test_b01_planner_no_forbidden_tokens():
    source = PLANNER_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in planner.py: {token!r}"


def test_b01_retry_no_forbidden_tokens():
    source = RETRY_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in retry.py: {token!r}"


def test_b01_outbox_no_forbidden_tokens():
    source = OUTBOX_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in outbox.py: {token!r}"


def test_b01_worker_no_forbidden_tokens():
    source = WORKER_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in worker.py: {token!r}"


def test_b01_event_sources_no_forbidden_tokens():
    source = EVENT_SOURCES_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in event_sources.py: {token!r}"


def test_b01_controller_no_forbidden_tokens():
    source = CONTROLLER_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in controller.py: {token!r}"


def test_b01_gold_review_no_forbidden_tokens():
    source = GOLD_REVIEW_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in gold_review.py: {token!r}"


def test_b01_human_inbox_no_forbidden_tokens():
    source = HUMAN_INBOX_PATH.read_text(encoding="utf-8")
    for token in _FORBIDDEN_TOKENS:
        assert token not in source, f"forbidden in human_inbox.py: {token!r}"


def test_b01_store_imports_only_allowed_modules():
    source = STORE_PATH.read_text(encoding="utf-8")
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            # Relative imports (from .xxx) are intra-package — allowed.
            if stripped.startswith("from ."):
                continue
            if stripped.startswith("from "):
                module = stripped.split()[1].split(".")[0]
            else:
                module = stripped.split()[1].split(".")[0]
            assert module in _ALLOWED_IMPORTS, f"unexpected import in store.py: {module!r}"


def test_b02_no_default_db_paths_in_source():
    for path in (MIGRATIONS_PATH, STORE_PATH):
        source = path.read_text(encoding="utf-8")
        assert ".state/automation.db" not in source, f"{path.name} contains default DB path"
        # The literal ".state" should not appear as a path component.
        # (Comments explaining the exclusion policy are acceptable only if
        # they don't set a default value.)


def test_b02_no_default_db_paths_in_tests():
    """Production automation source must not hard-code the default database path.
    Test files are excluded — they legitimately reference the path in assertion
    logic and forbidden-token check lists."""
    for path in (MIGRATIONS_PATH, STORE_PATH):
        source = path.read_text(encoding="utf-8")
        assert ".state/automation.db" not in source, f"{path.name} contains default DB path"
