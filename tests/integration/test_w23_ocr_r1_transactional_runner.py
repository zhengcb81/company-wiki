"""Real campaign X1/R0 routing with tiny stub runner, never a model backend."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

REPO = Path(__file__).resolve().parents[2]


@pytest.fixture
def tmp_path(tmp_path_factory):
    """This suite owns its scratch and restores it after every process test."""
    base = tmp_path_factory.getbasetemp().resolve()
    temporary = tempfile.TemporaryDirectory(prefix="w23-r6-owned-", dir=base)
    path = Path(temporary.name).resolve()
    try:
        assert path.is_relative_to(base)
        yield path
    finally:
        assert Path(temporary.name).resolve().is_relative_to(base)
        temporary.cleanup()


STUB = r'''
import hashlib,json,os,sys,time,types
from pathlib import Path
repo,work,mode,variant=map(str,sys.argv[1:])
sys.path[:0]=[repo,str(Path(repo)/"src")]
root=Path(work)
run=types.ModuleType("tools.ocr_comparison.run_x1")
run._model_dir=lambda value: root
def invoke(pages,**kwargs):
    with (root/"calls.txt").open("a",encoding="utf-8") as handle:
        handle.write(mode+"\n")
    if mode.endswith("raise"): raise RuntimeError("injected runner failure after start")
    if mode.endswith("die"): os._exit(23)
    time.sleep(0.05)
    elapsed=min(0.25,kwargs["deadline"])
    if mode=="overrun": elapsed=2.0
    if mode=="nan_elapsed": elapsed=float("nan")
    return {"records":[{"page_id":p["page_id"],"status":"ok","text":"captured",
                         "request_seconds":elapsed} for p in pages],
            "identity":kwargs["backend_identity"],
            "receipt":{"child":{"wall_seconds":elapsed,"events":[]}}}
run.run_x1_batch=invoke
sys.modules[run.__name__]=run
backend=types.ModuleType("tools.ocr_comparison.backends.xiaomi_x1")
class Model:
    def __init__(self,**kwargs):
        self.identity_manifest={"arm":"X1","model_sha256":"a"*64,"prompt_sha256":"b"*64,
            "preprocess":variant,"max_new_tokens":kwargs["max_new_tokens"],
            "request_deadline_seconds":kwargs["deadline_seconds"]}
backend.XiaomiX1=Model
sys.modules[backend.__name__]=backend
r0=types.ModuleType("tools.ocr_comparison.backends.rapidocr_r0")
class Rapid:
    def __init__(self,config,deadline_seconds):
        self.deadline_seconds=deadline_seconds
        self.identity_manifest={"arm":"R0","model_sha256":"c"*64,"preprocess":variant}
    def run_page(self,png):
        return invoke([{"page_id":"p1"}],deadline=self.deadline_seconds,
                      backend_identity=self.identity_manifest)["records"][0]
r0.RapidOCRR0=Rapid
r0.load_production_config=lambda path: None
sys.modules[r0.__name__]=r0
from tools.ocr_comparison import campaign
if mode=="die_after_cache":
    original=campaign._finalize_reservation
    def die(*args,**kwargs): os._exit(24)
    campaign._finalize_reservation=die
ledger=root/"ledger.json"
result=campaign.run_campaign_batch(ledger_path=ledger,ledger=campaign.load_ledger(ledger),
    arm="R0" if mode.startswith("r0") else "X1F",pages=[{"page_id":"p1","png":str(root/"page.png"),
                       "png_sha256":hashlib.sha256(b"fixture page").hexdigest()}],
    cache_dir=root/"cache",model_dir=str(root))
print(json.dumps(result))
'''


def call(tmp_path, mode="ok", variant="same"):
    return subprocess.run([sys.executable, "-I", "-B", "-X", "utf8", "-c", STUB,
                           str(REPO), str(tmp_path), mode, variant],
                          capture_output=True, text=True, encoding="utf-8", timeout=20)


def setup(tmp_path, budget=1):
    from tools.ocr_comparison.campaign import create_ledger
    create_ledger(tmp_path / "ledger.json", plan_id="stub-runner", budget_seconds=budget)
    (tmp_path / "page.png").write_bytes(b"fixture page")


def calls(tmp_path):
    p = tmp_path / "calls.txt"
    return p.read_text(encoding="utf-8").splitlines() if p.exists() else []


@pytest.mark.parametrize("mode", ["ok", "r0_ok"])
def test_two_real_routes_reuse_cache_and_original_measurement(tmp_path, mode):
    setup(tmp_path)
    first, second = call(tmp_path, mode), call(tmp_path, mode)
    assert first.returncode == second.returncode == 0, first.stderr + second.stderr
    one, two = json.loads(first.stdout), json.loads(second.stdout)
    assert calls(tmp_path) == [mode]
    assert two["records"][0]["cache_hit"] is True
    assert two["records"][0]["request_seconds"] == one["records"][0]["request_seconds"]
    assert two["remaining_seconds"] == one["remaining_seconds"]


@pytest.mark.parametrize("mode", ["raise", "die", "r0_raise", "r0_die"])
def test_failed_started_runner_keeps_reservation_and_cannot_retry_for_free(tmp_path, mode):
    from tools.ocr_comparison.campaign import load_ledger, remaining_seconds
    setup(tmp_path)
    first = call(tmp_path, mode)
    assert first.returncode != 0
    ledger = load_ledger(tmp_path / "ledger.json")
    assert ledger["inflight"]
    assert remaining_seconds(ledger) == 0
    second = call(tmp_path, "r0_ok" if mode.startswith("r0") else "ok")
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["records"][0]["status"] == "not_run"
    assert calls(tmp_path) == [mode]


def test_zero_balance_never_enters_runner_and_keeps_denominator(tmp_path):
    from tools.ocr_comparison.campaign import load_ledger, record
    setup(tmp_path)
    path = tmp_path / "ledger.json"
    record(load_ledger(path), path, arm="R0", page_id="old", seconds=1, status="ok")
    result = call(tmp_path)
    assert result.returncode == 0, result.stderr
    assert [r["page_id"] for r in json.loads(result.stdout)["records"]] == ["p1"]
    assert json.loads(result.stdout)["records"][0]["status"] == "not_run"
    assert calls(tmp_path) == []


def test_zero_balance_still_serves_real_x1_cache(tmp_path):
    from tools.ocr_comparison.campaign import load_ledger, record, remaining_seconds
    setup(tmp_path)
    first = call(tmp_path)
    assert first.returncode == 0
    path = tmp_path / "ledger.json"
    ledger = load_ledger(path)
    record(ledger, path, arm="R0", page_id="other-work", seconds=remaining_seconds(ledger), status="ok")
    second = call(tmp_path)
    assert second.returncode == 0, second.stderr
    assert json.loads(second.stdout)["records"][0]["cache_hit"]
    assert json.loads(second.stdout)["remaining_seconds"] == 0
    assert calls(tmp_path) == ["ok"]


def test_legacy_ledger_is_readable_but_cannot_silently_renew_unknown_work(tmp_path):
    setup(tmp_path)
    path = tmp_path / "ledger.json"
    original = json.loads(path.read_text(encoding="utf-8"))
    del original["inflight"]
    original["entries"].append({"arm": "R0", "page_id": "historical", "seconds": 0, "status": "ok"})
    path.write_text(json.dumps(original), encoding="utf-8")
    before = path.read_bytes()
    result = call(tmp_path)
    assert result.returncode == 0, result.stderr
    value = json.loads(result.stdout)
    assert value["records"][0]["error"] == "prior_inference_cost_unknown"
    assert not value["accounting_complete"] and value["execution_status"] == "partial"
    assert calls(tmp_path) == [] and path.read_bytes() == before


@pytest.mark.parametrize("known_cost", [0, 0.25])
def test_empty_or_fully_recorded_legacy_ledger_migrates_without_budget_reset(tmp_path, known_cost):
    from tools.ocr_comparison.campaign import load_ledger
    setup(tmp_path)
    path = tmp_path / "ledger.json"
    original = json.loads(path.read_text(encoding="utf-8"))
    del original["inflight"]
    if known_cost:
        original["entries"].append({"arm": "R0", "page_id": "historical", "seconds": known_cost, "status": "ok"})
        original["spent_seconds"] = known_cost
    path.write_text(json.dumps(original), encoding="utf-8")
    done = call(tmp_path)
    assert done.returncode == 0, done.stderr
    ledger = load_ledger(path)
    assert ledger["inflight"] == [] and ledger["budget_seconds"] == 1
    assert ledger["spent_seconds"] >= known_cost + 0.25
    assert calls(tmp_path) == ["ok"]


def test_cache_still_serves_when_legacy_real_cost_is_unknown(tmp_path):
    setup(tmp_path)
    assert call(tmp_path).returncode == 0
    path = tmp_path / "ledger.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["entries"].append({"arm": "R0", "page_id": "unknown-old", "seconds": 0, "status": "ok"})
    path.write_text(json.dumps(value), encoding="utf-8")
    done = call(tmp_path)
    assert done.returncode == 0, done.stderr
    assert json.loads(done.stdout)["records"][0]["cache_hit"]
    assert not json.loads(done.stdout)["accounting_complete"]
    assert calls(tmp_path) == ["ok"]


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -1, True, 2 ** 2048])
def test_invalid_budget_cannot_be_created_or_recorded(tmp_path, value):
    from tools.ocr_comparison.campaign import create_ledger, load_ledger, record
    with pytest.raises(ValueError):
        create_ledger(tmp_path / "invalid.json", plan_id="bad", budget_seconds=value)
    assert not (tmp_path / "invalid.json").exists()
    setup(tmp_path)
    path = tmp_path / "ledger.json"
    before = path.read_bytes()
    with pytest.raises(ValueError):
        record(load_ledger(path), path, arm="R0", page_id="bad", seconds=value, status="ok")
    assert path.read_bytes() == before


def test_result_captured_before_settle_recovers_without_runner(tmp_path):
    from tools.ocr_comparison.campaign import load_ledger
    setup(tmp_path)
    first = call(tmp_path, "die_after_cache")
    assert first.returncode == 24
    second = call(tmp_path)
    assert second.returncode == 0, second.stderr
    assert calls(tmp_path) == ["die_after_cache"]
    assert json.loads(second.stdout)["records"][0]["cache_hit"] is True
    ledger = load_ledger(tmp_path / "ledger.json")
    assert ledger["inflight"] == [] and len(ledger["entries"]) == 1


def test_changed_preprocessing_does_not_reuse_an_old_output(tmp_path):
    setup(tmp_path)
    first, second = call(tmp_path), call(tmp_path, variant="new preprocessing")
    assert first.returncode == second.returncode == 0, first.stderr + second.stderr
    assert calls(tmp_path) == ["ok", "ok"]


def test_actual_overrun_is_not_censored_to_the_reserved_budget(tmp_path):
    from tools.ocr_comparison.campaign import load_ledger
    setup(tmp_path)
    done = call(tmp_path, "overrun")
    assert done.returncode == 0, done.stderr
    value = json.loads(done.stdout)
    assert value["resource_limit_exceeded"] and value["execution_status"] == "partial"
    assert load_ledger(tmp_path / "ledger.json")["spent_seconds"] == 2
    assert value["remaining_seconds"] == 0


def test_invalid_runner_measurement_keeps_the_durable_hold(tmp_path):
    from tools.ocr_comparison.campaign import load_ledger, remaining_seconds
    setup(tmp_path)
    done = call(tmp_path, "nan_elapsed")
    assert done.returncode != 0
    assert remaining_seconds(load_ledger(tmp_path / "ledger.json")) == 0
    again = call(tmp_path)
    assert again.returncode == 0 and calls(tmp_path) == ["nan_elapsed"]


@pytest.mark.parametrize("field", ["budget_seconds", "spent_seconds"])
@pytest.mark.parametrize("number", [float("nan"), float("inf"), -float("inf"), True])
def test_nonfinite_or_boolean_ledger_cannot_supply_budget(tmp_path, field, number):
    from tools.ocr_comparison.campaign import LedgerCorrupt, load_ledger
    setup(tmp_path)
    path = tmp_path / "ledger.json"
    ledger = json.loads(path.read_text(encoding="utf-8"))
    ledger[field] = number
    path.write_text(json.dumps(ledger), encoding="utf-8")
    with pytest.raises(LedgerCorrupt):
        load_ledger(path)


def test_concurrent_same_key_starts_only_one_real_runner(tmp_path):
    setup(tmp_path)
    command = [sys.executable, "-I", "-B", "-X", "utf8", "-c", STUB,
               str(REPO), str(tmp_path), "ok", "same"]
    first = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    second = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        out1, err1 = first.communicate(timeout=20)
        out2, err2 = second.communicate(timeout=20)
        assert first.returncode == second.returncode == 0, (err1, err2)
        assert calls(tmp_path) == ["ok"]
        assert len(json.loads(out1)["records"]) == len(json.loads(out2)["records"]) == 1
        final = call(tmp_path)
        assert final.returncode == 0 and json.loads(final.stdout)["records"][0]["cache_hit"]
        assert calls(tmp_path) == ["ok"]
    finally:
        for proc in (first, second):
            if proc.poll() is None:
                proc.kill()
                proc.wait()


def test_two_stale_process_snapshots_cannot_double_allocate(tmp_path):
    from tools.ocr_comparison.campaign import load_ledger
    import time
    setup(tmp_path)
    program = r'''
import sys,time
from pathlib import Path
repo,work,tag=sys.argv[1:]
sys.path[:0]=[repo,str(Path(repo)/"src")]
from tools.ocr_comparison.campaign import load_ledger,record
root=Path(work); path=root/"ledger.json"
snapshot=load_ledger(path)
(root/(tag+".ready")).write_text("ready")
deadline=time.monotonic()+10
while not (root/"go").exists():
    if time.monotonic()>deadline: raise TimeoutError("barrier")
    time.sleep(0.01)
record(snapshot,path,arm="R0",page_id=tag,seconds=0.75,status="ok")
'''
    args = [sys.executable, "-I", "-B", "-X", "utf8", "-c", program, str(REPO), str(tmp_path)]
    first = subprocess.Popen([*args, "a"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    second = subprocess.Popen([*args, "b"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    until = time.monotonic() + 10
    try:
        while len(list(tmp_path.glob("*.ready"))) < 2:
            assert time.monotonic() < until, "both processes must observe the same old balance"
            time.sleep(0.01)
        (tmp_path / "go").write_text("go")
        first.communicate(timeout=15)
        second.communicate(timeout=15)
        assert sorted([first.returncode, second.returncode]) == [0, 1]
        assert load_ledger(tmp_path / "ledger.json")["spent_seconds"] == 0.75
    finally:
        for proc in (first, second):
            if proc.poll() is None:
                proc.kill()
                proc.wait()
