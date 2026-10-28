"""Completed PDF pages survive later process failure, with strict wire bounds."""
from copy import deepcopy
from dataclasses import replace
from hashlib import sha256
import json
import base64
import sys
from types import SimpleNamespace

import pytest

from company_wiki._bounded_process import ChildFailed, ChildTimeout
from company_wiki.resource_budget import WorkBudget
from company_wiki.source_catalog.narrative_pdf_enhancement import ParagraphEnhancement
from company_wiki.source_catalog import narrative_pdf_page_checkpoints as wire
from unit.test_pdf_paragraph_runtime import config, source


PAGE_SCHEMA = "pdf-paragraph-page-checkpoint/1"
COMPLETE_SCHEMA = "pdf-paragraph-pages-complete/1"


def two_pages():
    data, parsed = source()
    more = tuple(replace(unit,
        unit_id="urn:company-wiki:narrative-unit:sha256:" + sha256((unit.unit_id + "page2").encode()).hexdigest(),
        coordinates=replace(unit.coordinates, page_number=2)) for unit in parsed.units)
    return data, replace(parsed, units=(*parsed.units, *more), page_count=2, pages_read=2)


def binding(request, parsed):
    result = {key: request[key] for key in ("source_sha256", "docling_version", "model_sha256",
        "model_config_sha256", "runtime_versions", "environment_sha256")}
    if "environment_algorithm" in request:
        result["environment_algorithm"] = request["environment_algorithm"]
    return {**result, "source_id": request.get("source_id", parsed.source_id),
        "request_schema": request["schema_version"], "requested_pages": request["pages"],
        "request_sha256": request.get("request_sha256", "f" * 64), "converter_instances": 1}


def page_frame(request, parsed, page=1, sequence=0):
    return {**binding(request, parsed), "schema_version": PAGE_SCHEMA, "sequence": sequence,
        "page": page, "peak_job_commit_bytes": 4096,
        "items": [{"label": "text", "text": " ".join(u.raw_text for u in parsed.units
            if u.coordinates.page_number == page), "provenance": [{"page_no": page,
            "bbox": {"l": 60, "r": 500, "t": 700, "b": 665, "coord_origin": "BOTTOMLEFT"}}]}]}


def complete_frame(request, parsed, total_items=2):
    return {**binding(request, parsed), "schema_version": COMPLETE_SCHEMA,
        "sequence": len(request["pages"]), "completed_pages": request["pages"], "total_items": total_items}


def encoded(*frames):
    return b"".join(json.dumps(frame, ensure_ascii=False).encode() + b"\n" for frame in frames)


def assert_first_page_only(parsed, result):
    assert result.layout_diagnostics[-1]["status"] == "partial_enhanced"
    execution = result.layout_coverage["reading_execution"]
    assert execution["completed_pages"] == [1] and execution["pending_pages"] == [2]
    assert not execution["stream_complete"]
    assert all("paragraph_membership" in u.metadata["reading_layout"] for u in result.units[:2])
    assert all("paragraph_membership" not in u.metadata["reading_layout"] for u in result.units[2:])
    assert [(u.unit_id, u.raw_text, u.coordinates) for u in result.units] == [
        (u.unit_id, u.raw_text, u.coordinates) for u in parsed.units]


@pytest.mark.parametrize("failure,tail", (("timeout", b""), ("failed", b""),
    ("timeout", b'{"schema_version":"pdf-paragraph'), ("failed", b'{"sequence":')))
def test_finished_page_survives_later_failure_or_truncated_final_record(failure, tail):
    data, parsed = two_pages()
    def runner(command, **kwargs):
        request = json.loads(kwargs["input_bytes"])
        assert request["pages"] == [1, 2]
        raw = encoded(page_frame(request, parsed)) + tail
        if failure == "failed":
            raise ChildFailed("child failed", returncode=9, stdout=raw)
        error = ChildTimeout("child timed out")
        error.stdout, error.stderr = raw, b""
        raise error
    result = ParagraphEnhancement(config(), runner=runner).enhance(data, parsed,
        work_budget=WorkBudget(100000), deadline=None)
    assert_first_page_only(parsed, result)
    assert result.layout_coverage["reading_execution"]["truncated_final_record"] == bool(tail)


def test_success_requires_all_completed_pages_and_terminal_frame():
    data, parsed = two_pages()
    def runner(command, **kwargs):
        request = json.loads(kwargs["input_bytes"])
        return {"stdout": encoded(page_frame(request, parsed), page_frame(request, parsed, 2, 1),
                                  complete_frame(request, parsed))}
    result = ParagraphEnhancement(config(), runner=runner).enhance(data, parsed,
        work_budget=WorkBudget(100000), deadline=None)
    assert result.layout_diagnostics[-1]["status"] == "enhanced"
    execution = result.layout_coverage["reading_execution"]
    assert execution["stream_complete"] and execution["completed_pages"] == [1, 2]
    assert execution["pending_pages"] == []


@pytest.mark.parametrize("broken", ("source", "sha", "environment", "request", "model", "order",
    "duplicate", "sequence", "foreign_item_page", "oversized_items", "oversized_bytes", "bad_complete_record",
    "garbage_tail", "valid_unterminated_record", "missing_terminal", "duplicate_key", "nonfinite"))
def test_invalid_complete_record_never_salvages_a_good_preceding_page(broken):
    data, parsed = two_pages()
    def runner(command, **kwargs):
        request = json.loads(kwargs["input_bytes"])
        first, second = page_frame(request, parsed), page_frame(request, parsed, 2, 1)
        key = {"source": "source_id", "sha": "source_sha256", "environment": "environment_sha256",
               "request": "request_sha256", "model": "model_sha256"}.get(broken)
        if key:
            second[key] = "wrong" if key == "source_id" else "0" * 64
        if broken == "order":
            first, second = second, first
        elif broken == "duplicate":
            second = deepcopy(first)
        elif broken == "sequence":
            second["sequence"] = 3
        elif broken == "foreign_item_page":
            second["items"][0]["provenance"][0]["page_no"] = 3
        elif broken == "oversized_items":
            second["items"] *= 2049
        raw = encoded(first, second)
        if broken == "oversized_bytes":
            raw += b" " * config().max_output_bytes
        elif broken == "bad_complete_record":
            raw = encoded(first) + b'{"schema_version":bad}\n'
        elif broken == "garbage_tail":
            raw = encoded(first) + b"garbage"
        elif broken == "valid_unterminated_record":
            raw = encoded(first) + json.dumps(second).encode()
        elif broken == "duplicate_key":
            raw = encoded(first) + b'{"page":2,"page":2}\n'
        elif broken == "nonfinite":
            second["items"][0]["provenance"][0]["bbox"]["r"] = float("nan")
            raw = encoded(first, second)
        if broken == "missing_terminal":
            return {"stdout": raw}
        raise ChildFailed("child failed", returncode=9, stdout=raw)
    result = ParagraphEnhancement(config(), runner=runner).enhance(data, parsed,
        work_budget=WorkBudget(100000), deadline=None)
    assert result.units == parsed.units
    assert result.layout_diagnostics[-1]["status"] == "native_fallback"


def test_no_completed_page_keeps_native_fallback():
    data, parsed = two_pages()
    def runner(command, **kwargs):
        error = ChildTimeout("before first page")
        error.stdout, error.stderr = b'{"schema_version":', b""
        raise error
    result = ParagraphEnhancement(config(), runner=runner).enhance(data, parsed,
        work_budget=WorkBudget(100000), deadline=None)
    assert result.units == parsed.units and result.layout_diagnostics[-1]["status"] == "native_fallback"
    execution = result.layout_coverage["reading_execution"]
    assert execution["completed_pages"] == [] and execution["pending_pages"] == [1, 2]
    assert not execution["stream_complete"] and execution["truncated_final_record"]


def request_fixture(*, pages=None, v2=False):
    _, parsed = two_pages()
    selected = config()
    request = {"schema_version": "pdf-paragraph-request/2" if v2 else "pdf-paragraph-request/1",
        "checkpoint_protocol": wire.CHECKPOINT_PROTOCOL, "source_id": parsed.source_id,
        "source_sha256": parsed.source_sha256, "source_page_count": 2, "pages": pages or [1, 2],
        "docling_version": selected.docling_version, "model_sha256": selected.model_sha256,
        "model_config_sha256": selected.model_config_sha256, "runtime_versions": dict(selected.runtime_versions),
        "environment_sha256": selected.environment_sha256, "cpu_threads": selected.cpu_threads,
        "max_seconds": selected.max_seconds, "max_memory_bytes": selected.max_memory_bytes,
        "max_output_bytes": selected.max_output_bytes}
    if v2:
        request["environment_algorithm"] = "pdf-runtime-closure/2"
    request["request_sha256"] = wire.request_sha256(request)
    return request, parsed


@pytest.mark.parametrize("field,value", (
    ("source_id", "urn:company-wiki:source:sha256:" + "e" * 64), ("source_sha256", "e" * 64),
    ("model_sha256", "e" * 64), ("model_config_sha256", "e" * 64), ("environment_sha256", "e" * 64),
    ("pages", [2, 1]), ("source_page_count", 3), ("cpu_threads", 2), ("max_seconds", 119),
    ("max_memory_bytes", 1024), ("max_output_bytes", 1024),
))
def test_request_digest_binds_every_runtime_source_page_and_resource_field(field, value):
    request, _ = request_fixture()
    request[field] = value
    with pytest.raises(ValueError):
        wire.validate_request(request)


@pytest.mark.parametrize("field,value", (
    ("pages", [1, 1]), ("pages", [1, 3]), ("pages", [True, 2]), ("pages", [1, 2, 3, 4]),
    ("source_page_count", True), ("max_seconds", 300.1), ("max_seconds", float("nan")),
    ("max_memory_bytes", 8 * 1024**3 + 1), ("max_output_bytes", 32 * 1024**2 + 1),
))
def test_checkpoint_contract_never_raises_existing_resource_or_page_bounds(field, value):
    request, _ = request_fixture()
    request[field] = value
    with pytest.raises(ValueError):
        wire.request_sha256(request)


def test_shared_public_ceilings_keep_explicit_configs_and_request_bounds_compatible():
    runtime = replace(config(), max_pages=wire.MAX_PAGES, max_seconds=wire.MAX_SECONDS,
        max_input_bytes=wire.MAX_INPUT_BYTES, max_memory_bytes=wire.MAX_MEMORY_BYTES,
        max_output_bytes=wire.MAX_OUTPUT_BYTES, cpu_threads=wire.MAX_CPU_THREADS)
    request, _ = request_fixture()
    request.update(pages=list(range(1, runtime.max_pages + 1)), source_page_count=runtime.max_pages,
        max_seconds=runtime.max_seconds, max_memory_bytes=runtime.max_memory_bytes,
        max_output_bytes=runtime.max_output_bytes, cpu_threads=runtime.cpu_threads)
    request["request_sha256"] = wire.request_sha256(request)
    wire.validate_request(request)
    for field in ("max_pages", "max_seconds", "max_input_bytes", "max_memory_bytes", "max_output_bytes", "cpu_threads"):
        with pytest.raises(ValueError):
            replace(runtime, **{field: getattr(runtime, field) + 1})
    request.update(pages=list(range(1, 18)), source_page_count=17)
    with pytest.raises(ValueError):
        wire.request_sha256(request)


@pytest.mark.parametrize("source_id", ("", "   ", "x" * 4097, None, True))
def test_opaque_source_id_still_requires_a_nonempty_bounded_string(source_id):
    request, _ = request_fixture()
    request["source_id"] = source_id
    with pytest.raises(ValueError):
        wire.request_sha256(request)


def test_every_byte_cut_of_a_valid_page_is_an_extendable_strict_prefix():
    request, parsed = request_fixture()
    first = encoded(page_frame(request, parsed))
    second = page_frame(request, parsed, 2, 1)
    second["items"][0]["text"] = 'neutral 中文 \x01 marker " slash \\ and tab\t'
    frame = wire.encode_page(request, 2, 1, second["items"], 4096)
    # Exclude the complete object immediately before its atomic newline.
    for cut in range(1, len(frame) - 1):
        observed = wire.decode_output(first + frame[:cut], request, process_failed=True)
        assert observed.pages == (1,) and observed.truncated_final_record, cut


@pytest.mark.parametrize("tail", (b'{"x":1,"\\u0078":', b'{"x":1,"x"',
    b'{"nested":{"x":1,"x":', b'{"array":[{"x":1,"x":',
    b'{"x":"\\u0g', b'{"x":1,}', b'{"x":[1,]', b'{"x":"\\u00\xe4\xb8'))
def test_irreparable_prefix_grammar_never_salvages_a_committed_page(tail):
    request, parsed = request_fixture()
    with pytest.raises(ValueError):
        wire.decode_output(encoded(page_frame(request, parsed)) + tail, request, process_failed=True)


def test_prefix_key_sets_belong_to_each_object_and_unclosed_keys_can_extend():
    request, parsed = request_fixture()
    for tail in (b'{"x":1,"x', b'{"x":{"x":1},"items":[{"x":2},{"x":',
                 b'{"x":' + b'[' * 1200):
        observed = wire.decode_output(encoded(page_frame(request, parsed)) + tail, request, process_failed=True)
        assert observed.pages == (1,) and observed.truncated_final_record


def test_requested_order_is_the_only_order_and_items_are_bounded_across_pages():
    request, parsed = request_fixture(pages=[2, 1])
    first, second = page_frame(request, parsed, 2, 0), page_frame(request, parsed, 1, 1)
    observed = wire.decode_output(encoded(first, second, complete_frame(request, parsed)), request, process_failed=False)
    assert observed.complete and observed.pages == (2, 1)
    first["items"] *= 1025
    second["items"] *= 1025
    with pytest.raises(ValueError, match="aggregate"):
        wire.decode_output(encoded(first, second), request, process_failed=True)


@pytest.mark.parametrize("field,value", (("converter_instances", True), ("converter_instances", 1.0),
    ("requested_pages", [True, 2]), ("environment_algorithm", None)))
def test_checkpoint_identity_does_not_coerce_booleans_floats_or_algorithm(field, value):
    request, parsed = request_fixture(v2=True)
    frame = page_frame(request, parsed)
    frame[field] = value
    with pytest.raises(ValueError):
        wire.decode_output(encoded(frame), request, process_failed=True)


@pytest.mark.parametrize("tail", (b'{"value":1e-', b'{"value":-', b'{"value":1.',
    b'{"text":"\xe4\xb8', b'{"value":tru'))
def test_only_syntactically_unfinished_final_object_can_be_ignored(tail):
    request, parsed = request_fixture()
    observed = wire.decode_output(encoded(page_frame(request, parsed)) + tail, request, process_failed=True)
    assert observed.pages == (1,) and observed.truncated_final_record
    with pytest.raises(ValueError):
        wire.decode_output(encoded(page_frame(request, parsed)) + tail + b"\n", request, process_failed=True)


@pytest.mark.parametrize("tail", (b'{"value":1.e-', b'{"value":01', b'{"value":nope', b'{"x":"\\q'))
def test_malformed_unterminated_tail_is_not_misreported_as_truncation(tail):
    request, parsed = request_fixture()
    with pytest.raises(ValueError):
        wire.decode_output(encoded(page_frame(request, parsed)) + tail, request, process_failed=True)


@pytest.mark.parametrize("failure", ("timeout", "failed"))
@pytest.mark.timeout(10)
def test_actual_cold_small_child_retains_checkpoint_without_docling_or_pdf(failure):
    from company_wiki._bounded_process import run_bounded
    data, parsed = two_pages()
    script = (
        "import base64,json,sys,time\n"
        "request=json.loads(sys.stdin.buffer.read())\n"
        "sys.stdout.buffer.write(base64.b64decode(request['stdout']));sys.stdout.buffer.flush()\n"
        "time.sleep(20) if request['mode']=='timeout' else sys.exit(9)\n"
    )
    def runner(command, **kwargs):
        request = json.loads(kwargs["input_bytes"])
        payload = {"stdout": base64.b64encode(encoded(page_frame(request, parsed)) + b'{"next":').decode(),
                   "mode": failure}
        return run_bounded([sys.executable, "-B", "-S", "-c", script],
            input_bytes=json.dumps(payload).encode(), env=kwargs["env"], timeout_seconds=1.5,
            stdout_cap_bytes=kwargs["stdout_cap_bytes"], stderr_cap_bytes=kwargs["stderr_cap_bytes"])
    observed = ParagraphEnhancement(config(), runner=runner).enhance(data, parsed,
        work_budget=WorkBudget(100000), deadline=None)
    assert_first_page_only(parsed, observed)
    assert observed.layout_diagnostics[-1]["reason"] == ("ChildTimeout" if failure == "timeout" else "ChildFailed")


def test_worker_flushes_completed_page_before_next_conversion(capfdbinary):
    from company_wiki.source_catalog import _paragraph_worker as worker
    request, parsed = request_fixture()
    calls = []
    class Converter:
        def convert(self, stream, **kwargs):
            page = kwargs["page_range"][0]
            calls.append(page)
            if page == 2:
                raise ValueError("second page conversion failed")
            item = page_frame(request, parsed)["items"][0]
            source_item = SimpleNamespace(label=item["label"], text=item["text"],
                prov=[SimpleNamespace(model_dump=lambda **_: item["provenance"][0])])
            return SimpleNamespace(status="ConversionStatus.SUCCESS", errors=[],
                document=SimpleNamespace(iterate_items=lambda: iter([(source_item, 0)])))
    with pytest.raises(ValueError, match="second page"):
        worker._convert_pages(Converter(), lambda **kwargs: kwargs, b"not a PDF", request, checkpoints=wire)
    stdout = capfdbinary.readouterr().out
    observed = wire.decode_output(stdout, request, process_failed=True)
    assert calls == [1, 2] and observed.pages == (1,)
    assert b"pdf-paragraph-page-checkpoint/1" in stdout and not observed.complete


@pytest.mark.parametrize("broken", ("boolean_converter", "boolean_page", "duplicate_key", "nonfinite_peak"))
def test_complete_legacy_json_still_requires_strict_identity_and_finite_observations(broken):
    data, parsed = two_pages()
    def runner(command, **kwargs):
        request = json.loads(kwargs["input_bytes"])
        response = {key: request[key] for key in ("source_sha256", "docling_version", "model_sha256",
            "model_config_sha256", "runtime_versions", "environment_sha256")}
        response.update(schema_version="pdf-paragraph-response/1", pages=request["pages"],
            converter_instances=1, items=[page_frame(request, parsed, page, index)["items"][0]
                                        for index, page in enumerate(request["pages"])])
        if broken == "boolean_converter":
            response["converter_instances"] = True
        elif broken == "boolean_page":
            response["pages"] = [True, 2]
        elif broken == "nonfinite_peak":
            response["peak_job_commit_bytes"] = float("nan")
        body = json.dumps(response).encode()
        if broken == "duplicate_key":
            body = body.replace(b'{"source_sha256":', b'{"source_sha256":"wrong","source_sha256":', 1)
        return {"stdout": body}
    result = ParagraphEnhancement(config(), runner=runner).enhance(data, parsed,
        work_budget=WorkBudget(100000), deadline=None)
    assert result.units == parsed.units and result.layout_diagnostics[-1]["status"] == "native_fallback"
