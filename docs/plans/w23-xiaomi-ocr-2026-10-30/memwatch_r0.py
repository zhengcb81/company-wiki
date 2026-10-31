"""Driver for the R0 engine-peak measurement (delta review OPEN D3).

Renders one representative page with pypdfium2 in THIS process, then launches
a fresh interpreter (memwatch_r0_engine_child.py) whose process-lifetime peaks
measure the R0 engine (ONNX det/cls/rec sessions) without render pollution.
Writes the corrected receipt over the mislabeled one.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))

from tools.ocr_comparison.render_pages import render_pages  # noqa: E402


def main():
    tmp = Path(tempfile.mkdtemp(prefix="w23-mem-engine-"))
    try:
        rendered = render_pages(
            REPO / "docs/plans/w23-xiaomi-ocr-2026-10-30/sample_manifest.json", tmp)
        png = next(r for r in rendered if r["page_id"] == "byd_ar_2024_p021")["png"]
        proc = subprocess.run(
            [sys.executable, str(REPO / "docs/plans/w23-xiaomi-ocr-2026-10-30/memwatch_r0_engine_child.py"), png],
            capture_output=True, text=True, encoding="utf-8", timeout=300,
            cwd=str(REPO), env={"PYTHONUTF8": "1", "SYSTEMROOT": __import__("os").environ["SYSTEMROOT"],
                                 "USERPROFILE": __import__("os").environ["USERPROFILE"]},
        )
        if proc.returncode != 0:
            raise RuntimeError(f"child failed: {proc.stderr[-800:]}")
        child = json.loads(proc.stdout.strip().splitlines()[-1])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    receipt = {
        "schema_version": "cwp-ocr-memwatch-receipt/2",
        "purpose": "self-audit gap: R0 engine peak memory on a representative page (instrumented run, not for accuracy)",
        "page": "byd_ar_2024_p021",
        "method": (
            "fresh-interpreter child process; process-lifetime peaks cover stdlib baseline + "
            "LocalOCRAdapter engine load (three ONNX sessions) + one transcribe; the pypdfium2 "
            "page render happened in the parent, so it does not pollute the child's peaks"
        ),
        "excludes": (
            "the IsolatedOCRAdapter child-process boundary overhead; the production child "
            "performs the same ONNX work with the same model bytes, so this is the engine "
            "footprint, not a whole-request figure"
        ),
        "status": child["status"],
        "line_count": child["line_count"],
        "engine_seconds": child["engine_seconds"],
        "baseline_import": child["baseline"],
        "after_import": child["after_import"],
        "after_engine_load": child["after_engine_load"],
        "final": child["final"],
        "engine_peak_workingset_gb": child["engine_peak_workingset_gb"],
        "engine_peak_commit_gb": child["engine_peak_commit_gb"],
        "engine_delta_over_import_commit_gb": child["engine_delta_over_import_commit_gb"],
        "supersedes": "cwp-ocr-memwatch-receipt/1 (mislabeled: measured the parent process whose peak was the pdfium render; delta review OPEN D3)",
    }
    out_path = REPO / "delivery/w23-xiaomi-ocr/memwatch_r0_receipt.json"
    out_path.write_text(json.dumps(receipt, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({k: receipt[k] for k in (
        "status", "line_count", "engine_peak_workingset_gb", "engine_peak_commit_gb",
        "engine_delta_over_import_commit_gb")}, indent=1))
    print("WROTE", out_path)


if __name__ == "__main__":
    main()
