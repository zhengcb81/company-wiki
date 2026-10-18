"""Card section 5.5.1: ref roundtrip, plus the two tamper cases from section 6.

The positive case runs the published reader and exporter for real and requires
their manifests, the raw bytes and the recomputed bundle digest to agree.  The
negative cases mutate exactly one property and require the comparator to fail.
"""

from __future__ import annotations

from .support import checks, cwp
from .support import constants as C


def _spans_for(p4_manifest: dict, item: dict) -> list[dict]:
    return [s for s in p4_manifest["spans"] if s["source_id"] == item["source_id"]]


def test_p4_ref_roundtrip(p4_case, p4_sources, p4_manifest, p4_reads) -> None:
    """Export manifest, read receipt and raw bytes agree for every fixture ref."""
    case = p4_case()
    bundle = p4_manifest["bundle"]
    recomputed = cwp.recompute_bundle_sha256(bundle)
    assert recomputed == bundle["bundle_sha256"], (
        "recomputed bundle_sha256 must equal the declared digest "
        f"(declared={bundle['bundle_sha256']}, recomputed={recomputed})"
    )
    for item in p4_sources:
        read = p4_reads[item["relative_path"]]
        manifest = cwp.manifest_for(bundle, item["source_id"])
        outcomes = checks.check_ref_roundtrip(
            expected_ref=item,
            manifest=manifest,
            receipt=read.receipt["manifest"],
            raw_bytes=read.data,
            bundle_sha256=bundle["bundle_sha256"],
            recomputed_bundle_sha256=recomputed,
        )
        failing = [o.name for o in outcomes if not o.ok]
        case.check(f"ref_roundtrip::{item['relative_path']}",
                   "fail" if failing else "pass", {"failing": failing})
        assert not failing, (
            f"{item['relative_path']}: roundtrip checks failed -> {failing}"
        )
    case.settle("pass")


def test_p4_byte_size_off_by_one_fails(
    p4_case, p4_sources, p4_manifest, p4_reads
) -> None:
    """A receipt byte_size that differs by one must fail the roundtrip."""
    case = p4_case()
    item = p4_sources[0]
    read = p4_reads[item["relative_path"]]
    manifest = cwp.manifest_for(p4_manifest["bundle"], item["source_id"])
    receipt = dict(read.receipt["manifest"])
    receipt["byte_size"] = receipt["byte_size"] + 1

    outcomes = checks.check_ref_roundtrip(
        expected_ref=item, manifest=manifest, receipt=receipt, raw_bytes=read.data,
    )
    failing = {o.name: o for o in outcomes if not o.ok}
    assert "manifest_vs_receipt" in failing, (
        "a byte_size differing by one must fail manifest_vs_receipt; "
        f"observed {sorted(failing)}"
    )
    assert failing["manifest_vs_receipt"].code == C.CODE_FIELD_MISSING, (
        f"expected {C.CODE_FIELD_MISSING}; got {failing['manifest_vs_receipt'].code}"
    )
    case.check("byte_size_off_by_one_detected", "pass", {
        "code": C.CODE_FIELD_MISSING,
        "differing": failing["manifest_vs_receipt"].detail["differing"],
    })
    case.settle("pass")


def test_p4_same_length_tamper_fails(
    p4_case, p4_sources, p4_manifest, p4_reads
) -> None:
    """A same-length byte tamper is caught by the digest, not by the size."""
    case = p4_case()
    item = p4_sources[0]
    read = p4_reads[item["relative_path"]]
    manifest = cwp.manifest_for(p4_manifest["bundle"], item["source_id"])
    tampered = bytearray(read.data)
    tampered[0] ^= 0x01
    assert len(tampered) == len(read.data), "the tamper must keep the byte length"

    outcomes = checks.check_ref_roundtrip(
        expected_ref=item, manifest=manifest,
        receipt=read.receipt["manifest"], raw_bytes=bytes(tampered),
    )
    by_name = {o.name: o for o in outcomes}
    assert not by_name["read_bytes_sha256"].ok, (
        "a same-length byte tamper must fail read_bytes_sha256"
    )
    assert by_name["read_bytes_sha256"].code == C.CODE_FIELD_MISSING
    assert by_name["read_bytes_size"].ok, (
        "the length is unchanged, so only the digest can catch this tamper"
    )
    case.check("same_length_tamper_detected", "pass",
               {"code": by_name["read_bytes_sha256"].code})
    case.settle("pass")
