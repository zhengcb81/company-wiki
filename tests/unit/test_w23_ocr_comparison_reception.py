"""Independent ROOT reception regressions: no OCR model and no network."""
import json
import struct
import sys
import time
from pathlib import Path
import pytest

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))


def test_normalized_micro_uses_normalized_reference_length():
    from tools.ocr_comparison.compare import evaluate_page, aggregate
    page = evaluate_page("A B C", {"status": "ok", "text": "A X C"}, english=True)
    assert aggregate([page])["micro_cer_narrow"] == pytest.approx(1 / 3)


def test_numeric_identity_retains_distinct_units_and_currency():
    from tools.ocr_comparison.metrics import extract_numbers, number_prf
    assert len(extract_numbers("1亿 1万")) == 2
    gold = extract_numbers("RMB 1 billion USD 1 billion")
    assert len(gold) == 2
    result = number_prf(gold, extract_numbers("USD 1 billion"))
    assert result["recall"] == 0.5
    assert number_prf(extract_numbers("RMB 1 billion"), extract_numbers("USD 1 billion"))["recall"] == 0


def test_duplicate_and_wrong_identity_records_are_rejected():
    from tools.ocr_comparison.compare import evaluate_split
    manifest = {"documents": {"doc": {"language": "en", "content_sha256": "source", "source_id": "id"}},
                "pages": [{"page_id": "p", "doc": "doc", "role": "eval", "png_sha256": "image", "pdf_page_index": 0}]}
    gold = {"pages": {"p": {"full_text": "hello"}}}
    record = {"page_id": "p", "status": "ok", "text": "hello"}
    with pytest.raises(ValueError, match="duplicate"):
        evaluate_split(gold, [record, record], manifest, arm="TEST")
    with pytest.raises(ValueError, match="identity mismatch"):
        evaluate_split(gold, [dict(record, page_identity={"page_image_sha256": "wrong"})], manifest, arm="TEST")


@pytest.mark.parametrize("deadline,total", [(181, 1800), (180, 1801), (float("nan"), 1), (0, 1)])
def test_request_and_total_limits_cannot_be_raised(deadline, total):
    from tools.ocr_comparison.run_x1 import validate_card_limits
    with pytest.raises(ValueError):
        validate_card_limits(deadline, total)


def test_precision_artifacts_and_runtime_change_backend_identity(tmp_path):
    from tools.ocr_comparison.backends.xiaomi_x1 import XiaomiX1
    (tmp_path / "model.fp32.safetensors").write_bytes(b"one")
    (tmp_path / "processor_config.json").write_text("{}")
    a = XiaomiX1(model_dir=str(tmp_path), deadline_seconds=1, weights_mode="mapped-f32").identity_manifest
    assert a["precision"] == "float32-cpu"
    assert a["runtime"]["package_versions"]
    (tmp_path / "model.fp32.safetensors").write_bytes(b"two")
    b = XiaomiX1(model_dir=str(tmp_path), deadline_seconds=1, weights_mode="mapped-f32").identity_manifest
    assert a["artifact_sha256"] != b["artifact_sha256"]


def test_explicit_converter_widens_bytes_without_torch(tmp_path):
    from tools.ocr_comparison.make_fp32_copy import convert_checkpoint
    source, output = tmp_path / "source", tmp_path / "output"
    header = json.dumps({"w": {"dtype": "BF16", "shape": [2], "data_offsets": [0, 4]}}).encode()
    source.write_bytes(struct.pack("<Q", len(header)) + header + bytes.fromhex("803f00c0"))
    result = convert_checkpoint(source, output)
    assert result["tensors"] == 1
    with output.open("rb") as f:
        length = struct.unpack("<Q", f.read(8))[0]
        converted = json.loads(f.read(length))
        assert converted["w"]["dtype"] == "F32"
        assert f.read() == bytes.fromhex("0000803f000000c0")
    with pytest.raises(FileExistsError):
        convert_checkpoint(source, output)
    assert not list(tmp_path.glob("*.tmp"))


def test_parent_watchdog_interrupts_blocked_request_without_model(tmp_path, monkeypatch):
    import subprocess
    from tools.ocr_comparison import run_x1
    from tools.ocr_comparison.backends import xiaomi_x1
    class Backend:
        def __init__(self, **kwargs):
            self.identity_manifest = {"arm": "TEST"}
    monkeypatch.setattr(xiaomi_x1, "XiaomiX1", Backend)
    monkeypatch.setattr(run_x1, "require_memory_limit", lambda: None)
    monkeypatch.setattr(run_x1, "_model_dir", lambda _: tmp_path)
    monkeypatch.setattr(run_x1, "host_memory_snapshot", lambda: {"avail_phys_bytes": 2 * run_x1.GIB})
    active = []
    class Job:
        def __init__(self, cap): pass
        def assign(self, process):
            assert process is active[0]  # own the Popen handle, not a reopened PID
        def peak_process_bytes(self): return 1
        def terminate(self): active[0].kill()
        def close(self): pass
    monkeypatch.setattr(run_x1, "JobMemoryLimit", Job)
    original = subprocess.Popen
    def popen(*args, **kwargs):
        process = original([sys.executable, "-c", "import time; time.sleep(5)"], **kwargs)
        active.append(process)
        return process
    monkeypatch.setattr(run_x1.subprocess, "Popen", popen)
    start = time.monotonic()
    result = run_x1.run_x1_batch([{"page_id": "p", "png": "unused"}], deadline=0.15,
                                 total_budget=1, workdir=tmp_path, model_dir="unused")
    assert time.monotonic() - start < 3
    assert result["records"][0]["status"] == "timeout"
    assert result["receipt"]["child"]["backstop_hit"] is True


def test_common_x1_entry_delegates_to_isolated_runner(tmp_path, monkeypatch):
    from tools.ocr_comparison import run_comparison, run_x1
    plan = tmp_path / "plan"
    plan.mkdir()
    (plan / "sample_manifest.json").write_text(json.dumps({"pages": [{"page_id": "p"}]}))
    (plan / "gold.json").write_text("{}")
    monkeypatch.setattr(run_comparison, "_plan_dir", lambda _: plan)
    monkeypatch.setattr(run_comparison, "render_pages", lambda *a: [{"page_id": "p", "png": "unused", "sha256": "sha"}])
    monkeypatch.setattr(run_comparison, "resource_snapshot", lambda: {})
    monkeypatch.setattr(run_comparison, "evaluate_split", lambda *a, **kw: {})
    monkeypatch.setattr(run_comparison, "build_run_manifest", lambda *a, **kw: {"limits": {}, "cache": {}})
    monkeypatch.setenv("CWP_PROJECT_ROOT", str(REPO))
    (tmp_path / "model.safetensors").write_bytes(b"toy")
    monkeypatch.setenv("W23_XIAOMI_MODEL_DIR", str(tmp_path))
    calls = []
    def isolated(pages, **kwargs):
        calls.append((pages, kwargs))
        return {"identity": {"arm": "X1"}, "records": [{"page_id": "p", "status": "ok"}]}
    monkeypatch.setattr(run_x1, "run_x1_batch", isolated)
    monkeypatch.setattr(run_x1, "require_memory_limit", lambda: None)
    destination = tmp_path / "comparison.json"
    assert run_comparison.main(["--arms", "X1", "--memory-cap-gb", "1", "--max-new-tokens", "123", "--out", str(destination)]) == 0
    assert calls[0][1]["max_new_tokens"] == 123
    assert "memory_cap_bytes" not in calls[0][1]
    assert json.loads(destination.read_text())["run_manifest"]["limits"]["max_new_tokens"] == 123


def test_persistent_cache_corruption_is_a_miss(tmp_path):
    from tools.ocr_comparison.cache import ResultCache
    cache = ResultCache(tmp_path)
    cache.put("key", {"status": "ok", "engine_seconds": 12.5})
    assert ResultCache(tmp_path).get("key")["engine_seconds"] == 12.5
    path = tmp_path / "key.json"
    envelope = json.loads(path.read_text())
    envelope["record"]["engine_seconds"] = 0
    path.write_text(json.dumps(envelope))
    assert ResultCache(tmp_path).get("key") is None
    path.write_text('{"record":')
    assert ResultCache(tmp_path).get("key") is None
    assert not list(tmp_path.glob("*.tmp"))


def test_cli_two_process_resume_does_not_infer_twice(tmp_path):
    import subprocess
    plan = tmp_path / "plan"
    plan.mkdir()
    (plan / "sample_manifest.json").write_text(json.dumps({"pages": [{"page_id": "p"}]}))
    (plan / "gold.json").write_text("{}")
    (tmp_path / "model.safetensors").write_bytes(b"toy")
    script = tmp_path / "resume.py"
    script.write_text("\n".join([
        "import sys,json,os",
        "from pathlib import Path",
        "repo=Path(sys.argv[1]); root=Path(sys.argv[2]); sys.path.insert(0,str(repo))",
        "from tools.ocr_comparison import run_comparison as cli, run_x1",
        "os.environ['CWP_PROJECT_ROOT']=str(repo);os.environ['W23_XIAOMI_MODEL_DIR']=str(root)",
        "cli._plan_dir=lambda _:root/'plan'",
        "cli.render_pages=lambda *a:[{'page_id':'p','png':'unused','sha256':'image'}]",
        "cli.evaluate_split=lambda *a,**k:{}",
        "cli.build_run_manifest=lambda *a,**k:{'limits':{},'cache':{}}",
        "def infer(pages,**kwargs):",
        "    count=root/'inferences'; count.write_text(str(int(count.read_text())+1) if count.exists() else '1')",
        "    return {'identity':kwargs['backend_identity'],'records':[{'page_id':'p','status':'ok','text':'result','engine_seconds':12.5}]}",
        "run_x1.run_x1_batch=infer",
        "run_x1.require_memory_limit=lambda:None",
        "cli.main(['--arms','X1','--memory-cap-gb','1','--cache-dir',str(root/'cache'),'--out',str(root/'result.json')])",
    ]))
    for _ in range(2):
        subprocess.run([sys.executable, "-B", "-X", "utf8", str(script), str(REPO), str(tmp_path)], cwd=REPO,
                       check=True, capture_output=True, text=True, encoding="utf-8", timeout=30)
    assert (tmp_path / "inferences").read_text() == "1"
    report = json.loads((tmp_path / "result.json").read_text(encoding="utf-8"))
    raw = json.loads((tmp_path / report["arms"]["X1"]["raw_output_file"]).read_text(encoding="utf-8"))
    assert raw["records"][0]["cache_hit"] is True
    assert raw["records"][0]["engine_seconds"] == 12.5
    assert raw["records"][0]["inference_runs"] == 0


def test_cli_imports_on_datetime_without_python311_utc_alias():
    """Exercise the supported 3.10 datetime API in an independent process."""
    import subprocess
    code = "import datetime; hasattr(datetime, 'UTC') and delattr(datetime, 'UTC'); import tools.ocr_comparison.manifest; import tools.ocr_comparison.run_x1; import tools.ocr_comparison.run_comparison"
    subprocess.run([sys.executable, "-B", "-c", code], cwd=REPO, check=True,
                   capture_output=True, text=True, encoding="utf-8", timeout=30)


def test_parameter_and_cli_imports_without_windows_dll_in_fresh_process():
    import subprocess
    code = "\n".join([
        "import ctypes,sys",
        "sys.platform='linux'",
        "hasattr(ctypes,'WinDLL') and delattr(ctypes,'WinDLL')",
        "from tools.ocr_comparison import job_limit,run_x1,run_comparison,manifest",
        "run_x1.validate_card_limits(180,1800)",
        "assert job_limit.memory_limit_capability()['supported'] is False",
        "assert job_limit.self_peak_commit_bytes() is None",
        "try: job_limit.JobMemoryLimit(1024)",
        "except job_limit.MemoryLimitUnavailable: pass",
        "else: raise AssertionError('unsupported limit must not run unbounded')",
    ])
    subprocess.run([sys.executable, "-B", "-c", code], cwd=REPO, check=True,
                   capture_output=True, text=True, encoding="utf-8", timeout=30)


def test_unavailable_real_enforcement_fails_before_model_or_child(tmp_path, monkeypatch):
    from tools.ocr_comparison import run_x1, job_limit
    monkeypatch.setattr(job_limit.sys, "platform", "linux")
    monkeypatch.setattr(run_x1, "host_memory_snapshot", lambda: {"avail_phys_bytes": 1024 * 1024})
    monkeypatch.setattr(run_x1, "_model_dir", lambda _: pytest.fail("must reject before model inspection"))
    monkeypatch.setattr(run_x1.subprocess, "Popen", lambda *a, **kw: pytest.fail("must not launch"))
    with pytest.raises(job_limit.MemoryLimitUnavailable, match="requires Windows Job"):
        run_x1.run_x1_batch([], deadline=1, total_budget=1, model_dir=str(tmp_path))


def test_linux_memory_observation_is_measured_and_missing_stays_unknown(tmp_path):
    from tools.ocr_comparison import job_limit
    path = tmp_path / "meminfo"
    path.write_text("MemTotal: 100 kB\nMemAvailable: 40 kB\nCommitLimit: 80 kB\nCommitted_AS: 30 kB\n", encoding="ascii")
    observed = job_limit._linux_memory_snapshot(path)
    assert observed["total_phys_bytes"] == 102400
    assert observed["avail_phys_bytes"] == 40960
    assert observed["commit_free_bytes"] == 51200
    assert observed["observation_source"] == "/proc/meminfo"
    path.write_text("MemTotal: 100 kB\n", encoding="ascii")
    assert job_limit._linux_memory_snapshot(path)["avail_phys_bytes"] is None
    assert job_limit._linux_memory_snapshot(tmp_path / "missing")["avail_phys_bytes"] is None
    with pytest.raises(job_limit.MemoryLimitUnavailable, match="unknown"):
        job_limit.card_memory_cap_bytes(None)


def test_windows_adapter_delegates_original_process_handle_to_shared_owner(monkeypatch):
    from types import SimpleNamespace
    from tools.ocr_comparison import job_limit
    from company_wiki import _process_tree
    monkeypatch.setattr(job_limit.sys, "platform", "win32")
    seen = []
    class Owner:
        def __init__(self, handle, *, memory_limit_bytes):
            seen.append((handle, memory_limit_bytes))
        def peak_commit_bytes(self): return 123
        def terminate(self): seen.append("terminate")
        def close(self): seen.append("close")
    monkeypatch.setattr(_process_tree, "WindowsJob", Owner)
    limit = job_limit.JobMemoryLimit(456)
    limit.assign(SimpleNamespace(_handle=789))
    assert limit.peak_process_bytes() == 123
    limit.terminate()
    limit.close()
    assert seen == [(789, 456), "terminate", "close"]


def test_common_real_x1_refuses_unsupported_platform_before_model(tmp_path, monkeypatch):
    from tools.ocr_comparison import run_comparison, run_x1, job_limit
    monkeypatch.setattr(job_limit.sys, "platform", "linux")
    plan = tmp_path / "plan"
    plan.mkdir()
    (plan / "sample_manifest.json").write_text(json.dumps({"pages": [{"page_id": "p"}]}))
    (plan / "gold.json").write_text("{}")
    monkeypatch.setattr(run_comparison, "_plan_dir", lambda _: plan)
    monkeypatch.setattr(run_comparison, "render_pages", lambda *a: [{"page_id": "p", "png": "unused", "sha256": "sha"}])
    monkeypatch.setattr(run_comparison, "resource_snapshot", lambda: {})
    monkeypatch.setattr(run_x1, "_model_dir", lambda _: pytest.fail("unsupported real backend must not inspect model"))
    monkeypatch.setenv("CWP_PROJECT_ROOT", str(REPO))
    with pytest.raises(job_limit.MemoryLimitUnavailable, match="requires Windows Job"):
        run_comparison.main(["--arms", "X1", "--memory-cap-gb", "1", "--out", str(tmp_path / "out.json")])


def test_assignment_failure_does_not_release_bootstrap_and_reaps_child(tmp_path, monkeypatch):
    from tools.ocr_comparison import run_x1
    events = []
    class Input:
        def write(self, value): pytest.fail("must not release before successful job assignment")
        def close(self): events.append("stdin-close")
    class Process:
        stdin = Input()
        def kill(self): events.append("kill")
        def wait(self):
            events.append("wait")
            return 1
    process = Process()
    class Job:
        def __init__(self, cap): pass
        def assign(self, actual):
            assert actual is process
            events.append("assign")
            raise OSError("assignment refused")
        def close(self): events.append("job-close")
    monkeypatch.setattr(run_x1, "require_memory_limit", lambda: None)
    monkeypatch.setattr(run_x1, "host_memory_snapshot", lambda: {"avail_phys_bytes": 1024 * 1024})
    monkeypatch.setattr(run_x1, "_model_dir", lambda _: tmp_path)
    monkeypatch.setattr(run_x1, "JobMemoryLimit", Job)
    monkeypatch.setattr(run_x1.subprocess, "Popen", lambda *a, **kw: process)
    with pytest.raises(OSError, match="assignment refused"):
        run_x1.run_x1_batch([], deadline=1, total_budget=1, workdir=tmp_path,
                            backend_identity={"arm": "TEST"})
    assert events == ["assign", "stdin-close", "kill", "wait", "job-close"]
