"""Real SDK entry evidence for the deployed runtime. Explicit opt-in only.

Run standalone, never in routine CI::

    W22_PDF_DEPLOYMENT_E2E=1 \
    W22_PDF_DEPLOYMENT_CONFIG=<deployed paragraph-runtime config> \
    python -m pytest tests/integration/test_w22_pdf_deployment_entry.py -v

The config path selects the owned ASCII deployment under test. No production
profile, parent environment or persistent state is touched; the selection is
process-local for these tests.
"""
import json
import os
from hashlib import sha256
from pathlib import Path
import shutil
import tempfile
import time

import pytest

from tools.pdf_runtime_deployment import deployment

pytestmark = [pytest.mark.integration, pytest.mark.e2e]

REPO_ROOT = Path(__file__).resolve().parents[2]
REPO_SRC = REPO_ROOT / "src"


def deployment_config() -> Path:
    if os.environ.get("W22_PDF_DEPLOYMENT_E2E") != "1":
        pytest.skip("real SDK entry is opt-in: set W22_PDF_DEPLOYMENT_E2E=1")
    configured = os.environ.get("W22_PDF_DEPLOYMENT_CONFIG")
    if configured is None:
        pytest.skip("set W22_PDF_DEPLOYMENT_CONFIG to the deployed runtime config")
        raise AssertionError("pytest.skip must not return")
    return Path(configured)


def synthetic_pdf(folder: Path) -> bytes:
    """Two pages; each carries one wrapped-prose fracture without terminal
    punctuation, so the native triage genuinely demands enhancement. Drawn
    with an embedded system font carrying a proper ToUnicode CMap — see
    tools/pdf_runtime_deployment/_synthetic_pdf.py for why the pymupdf
    built-in CJK font is not a fair fixture."""
    from tools.pdf_runtime_deployment._synthetic_pdf import build_two_page_wrapped_prose_pdf

    data, _digest = build_two_page_wrapped_prose_pdf(folder / "synthetic.pdf")
    return data


def receipts_dir() -> Path:
    configured = os.environ.get("W22_PDF_DEPLOYMENT_RECEIPTS")
    path = Path(configured) if configured else REPO_ROOT / "delivery" / "w22-pdf-deploy" / "receipts"
    path.mkdir(parents=True, exist_ok=True)
    return path


def test_l0_light_verify_of_deployed_environment():
    config_path = deployment_config()
    observation = deployment.verify_light(config_path, repo_src=REPO_SRC)
    assert observation["status"] == "PASS"
    assert observation["sdk_imports"] == 0
    assert observation["enable_user_site"] is False


def test_l1_production_config_load():
    config_path = deployment_config()
    observation = deployment.verify_config_load(config_path, repo_src=REPO_SRC,
                                                python=None)
    assert observation["status"] == "PASS"
    assert observation["environment_algorithm"] == "pdf-runtime-closure/2"


def test_l2_no_document_constructor():
    config_path = deployment_config()
    raw = json.loads(config_path.read_text(encoding="utf-8"))
    observation = deployment.constructor_probe(raw["python"], raw["artifacts"])
    assert observation["status"] == "CONSTRUCTOR_OK"
    assert observation["seconds"] <= 30


def test_l3_synthetic_e2e_through_production_entry():
    config_path = deployment_config()
    from company_wiki.resource_budget import WorkBudget
    from company_wiki.source_contract import source_id_for_sha256
    from company_wiki.source_catalog import narrative_evidence as native
    from company_wiki.source_catalog.narrative_pdf_enhancement import configured_paragraph_runtime
    from company_wiki.source_catalog.narrative_pdf_paragraphs import ParagraphProposal, align_paragraphs
    from company_wiki.source_catalog.narrative_pdf_reading import PdfReading, PdfReadingRequest

    scratch = Path(tempfile.mkdtemp(prefix="w22-e2e-"))
    receipt: dict[str, object] = {"scope": "two-page synthetic PDF through the real production entry",
                                  "config_path": str(config_path), "status": None,
                                  "warmup": None, "error": None}
    previous = os.environ.get("COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG")
    os.environ["COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG"] = str(config_path)
    try:
        # Phase 1: pay the documented one-time child bytecode-compile cost
        # through the exact production launch command (no document, no
        # readiness claim). The first E2E attempt honestly timed out inside
        # this cold-compile cost; warm-then-measure keeps the canonical run
        # under unchanged caps instead of raising any limit.
        receipt["warmup"] = deployment.warm_child_bytecode_cache(config_path, repo_src=REPO_SRC)
        data = synthetic_pdf(scratch)
        digest = sha256(data).hexdigest()
        started = time.monotonic()
        enhancement = configured_paragraph_runtime()
        assert enhancement is not None, "explicit config must select"
        config = enhancement.config
        native_parse = native.parse_pdf_bytes(data, source_id=source_id_for_sha256(digest),
                                              source_sha256=digest, language="zh")
        native_texts = [unit.raw_text for unit in native_parse.units]
        reading = PdfReading()
        request = PdfReadingRequest(source_id_for_sha256(digest), digest, "zh", "W22部署验收样张", "annual_report")

        class Selector:
            selector_version = "0.9.0"

            def __call__(self, parsed, **kwargs):
                return native.select_narrative_evidence(parsed, selector_version="0.9.0", **kwargs)

        parsed, selected = reading.select(data, request, selector=Selector(),
                                          work_budget=WorkBudget(10_000_000), checkpoint=lambda: None)
        diagnostic = parsed.layout_diagnostics[-1]
        texts_preserved = [unit.raw_text for unit in parsed.units] == native_texts
        replay_verified, replay_failed = reading.replay(data, source_id=request.source_id,
                                                        source_sha256=digest,
                                                        evidence_spans=selected.evidence_spans, language="zh")
        # Negative control on the real parsed structure: one altered character
        # with valid geometry must stay rejected.
        members = [unit for unit in parsed.units
                   if unit.coordinates.page_number == 1 and unit.unit_kind == "pdf_text_block"]
        negative_accepted = 0
        if len(members) >= 2:
            layout = dict(members[0].metadata.get("reading_layout", {}).get("layout", {}))
            tampered = ParagraphProposal(parsed.source_id, parsed.source_sha256, 1,
                                         "tampered mismatching text", tuple(layout.get("bbox", (0, 0, 1, 1))),
                                         layout.get("page_width", 1.0), layout.get("page_height", 1.0),
                                         coordinate_frame=layout.get("coordinate_frame", "dict"))
            negative_accepted = align_paragraphs(parsed, [tampered], work_budget=WorkBudget(100_000)).accepted_groups
        receipt.update(
            status=diagnostic.get("status"),
            seconds=round(time.monotonic() - started, 3),
            pdf_sha256=digest, page_count=native_parse.page_count,
            diagnostic=json.loads(json.dumps({key: diagnostic.get(key) for key in (
                "status", "pages", "gap_signals", "accepted_groups", "rejected_groups", "actual_engine",
                "engine_version", "model_sha256", "converter_instances", "peak_job_commit_bytes", "seconds",
                "reason", "last_stage", "worker_error", "worker_returncode", "temporary_root_restored_absent",
                "completed_pages", "pending_pages", "stream_complete", "truncated_final_record",
                "checkpoint_protocol")}, ensure_ascii=True)),
            runtime_identity={"python_ascii": all(ord(c) < 128 for c in config.python),
                              "artifacts_ascii": all(ord(c) < 128 for c in config.artifacts),
                              "environment_sha256": config.environment_sha256,
                              "docling_version": config.docling_version},
            source_preserved=texts_preserved,
            evidence_span_count=len(selected.evidence_spans),
            replay_verified=len(replay_verified), replay_failed=list(replay_failed),
            negative_control_rejected=negative_accepted == 0,
            known_non_ascii_failure=(diagnostic.get("worker_error") in {"FileNotFoundError", "OSError"}
                                     and diagnostic.get("status") == "native_fallback"),
        )
        # Conversion must genuinely complete through the deployed interpreter:
        # the known non-ASCII resource failure surfaced as PAGE_1 ChildFailed.
        assert receipt["known_non_ascii_failure"] is False, receipt
        assert diagnostic.get("completed_pages"), receipt
        assert texts_preserved, receipt
        # Positive control: real aligned enhancement, not just conversion.
        assert diagnostic.get("accepted_groups", 0) >= 1, receipt
        assert receipt["negative_control_rejected"], receipt
    except BaseException as failure:
        receipt["error"] = f"{type(failure).__name__}: {failure}"
        raise
    finally:
        if previous is None:
            os.environ.pop("COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG", None)
        else:
            os.environ["COMPANY_WIKI_PDF_ENHANCEMENT_CONFIG"] = previous
        shutil.rmtree(scratch, ignore_errors=True)
        receipt["cleanup"] = {"scratch_restored_absent": not scratch.exists()}
        path = receipts_dir() / "w22-synthetic-e2e.json"
        path.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
