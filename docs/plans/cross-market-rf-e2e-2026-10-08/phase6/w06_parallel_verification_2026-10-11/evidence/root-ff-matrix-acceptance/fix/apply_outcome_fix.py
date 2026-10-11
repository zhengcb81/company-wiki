"""Install shared factual outcome predicates and repair known helper mistakes."""
from pathlib import Path

tree = Path(r"C:\Users\郑曾波\Projects\_harness_worktrees\w06\ff-contract-matrix-root")
folder = tree / "tools/offline_contract_matrix"
(folder/"outcome.py").write_text('''"""Shared typed observations; missing evidence is never measured zero."""
from dataclasses import dataclass
from typing import Any, Mapping


def count(value: Any) -> int | None:
    return value if type(value) is int and value >= 0 else None


def source_ref(value: Any) -> dict | None:
    if not isinstance(value, dict):
        return None
    required = ("document_id", "source_id", "content_sha256", "byte_size", "mime_type")
    if not all(k in value for k in required):
        return None
    if not all(isinstance(value[k], str) and value[k] for k in required if k != "byte_size"):
        return None
    if len(value["content_sha256"]) != 64 or count(value["byte_size"]) is None:
        return None
    return value


@dataclass(frozen=True)
class Outcome:
    status: str | None
    reason: str | None
    reference: dict | None
    requests: int | None
    usage_complete: bool | None
    fiscal_year: Any
    fiscal_quarter: Any
    raw: Mapping[str, Any]

    @classmethod
    def observe(cls, value: Mapping[str, Any]):
        return cls(value.get("status"), value.get("reason"), source_ref(value.get("source_ref")),
            count(value.get("provider_requests")), value.get("provider_usage_complete"),
            value.get("fiscal_year"), value.get("fiscal_quarter"), value)

    def rejected_quarter(self) -> bool:
        return self.status not in {None, "downloaded", "reused", "unknown_publication"} and (
            self.reason in {"quarter_mismatch", "fiscal_quarter_mismatch", "period_mismatch"})

    def rejected_cutoff(self) -> bool:
        return self.status not in {None, "downloaded", "reused"} and self.reason in {
            "after_as_of", "after_as_of_date", "past_cutoff", "call_after_as_of",
            "published_after_as_of", "publication_after_as_of", "cutoff_exceeded"}

    def preserves_unknown_usage(self) -> bool:
        return (self.raw.get("provider_requests") is None
            and self.usage_complete is False and self.status in {
                "upstream_error", "provider_unavailable", "failed", "timeout"}
            and isinstance(self.reason, str) and bool(self.reason))


def filing_reused(first: Mapping[str, Any], second: Mapping[str, Any], kind: str) -> bool:
    ref1, ref2 = source_ref(first.get("source_ref")), source_ref(second.get("source_ref"))
    return bool(ref1 and ref1 == ref2 and first.get("document_kind") == kind
        and second.get("document_kind") == kind
        and first.get("resolution_outcome") in {"downloaded_new", "reused_after_discovery"}
        and second.get("resolution_outcome") == "reused_existing"
        and count(first.get("download_events")) is not None
        and count(first.get("download_events")) >= 1
        and count(second.get("download_events")) == 0)
''', encoding="utf-8")

path = folder/"matrix_cases.py"
text = path.read_text(encoding="utf-8")
text = text.replace('from fixture_builder import make_valid_pdf, CN, US, HK, Identity  # noqa: E402\n',
    'from fixture_builder import make_valid_pdf, CN, US, HK, Identity  # noqa: E402\nfrom outcome import Outcome, filing_reused, count  # noqa: E402\n')
text = text.replace('    d1 = f1.get("download_events") or 0\n    d2 = f2.get("download_events") or 0\n',
    '    d1 = count(f1.get("download_events"))\n    d2 = count(f2.get("download_events"))\n')
text = text.replace('        (d2 == 0, "run2 reuses without re-download"),',
    '        (filing_reused(f1, f2, kind), "run2 exact source reuses without re-download"),')
old = '''    cutoff_diagnostic = (t.get("status") in {"provider_unavailable", "upstream_error", "unknown_publication"}
                         or t.get("as_of_cutoff_verified") is False)
'''
assert text.count(old) == 1
text = text.replace(old, '    cutoff_diagnostic = Outcome.observe(t).rejected_cutoff()\n')
text = text.replace('    ok = t.get("status") != "downloaded" or t.get("fiscal_quarter") == 2\n',
    '    ok = Outcome.observe(t).rejected_quarter()\n')
text = text.replace('    unknown_reported_as_zero = (requests == 0 and usage_complete is True)\n',
    '    unknown_reported_as_zero = (requests == 0 and usage_complete is not True)\n')
text = text.replace('    ok = usage_complete is not True and not unknown_reported_as_zero and not calls_swallowed\n',
    '    ok = Outcome.observe(t).preserves_unknown_usage() and not calls_swallowed\n')
path.write_text(text, encoding="utf-8")

path = folder/"oracle.py"
text = path.read_text(encoding="utf-8")
text = text.replace('from typing import Any\n', 'from typing import Any\nfrom outcome import count\n')
text = text.replace('    cases = report.get("cases") or []\n', '''    cases = report.get("cases") or []
    if not cases:
        findings.append(Finding("empty_matrix", None, "no cases were executed"))
    if "code_binding" in report and (report.get("code_binding") or {}).get("verified") is not True:
        findings.append(Finding("unbound_code", None, "supplied producer code binding is unverified"))
    if report.get("runner"):
        required = set(report.get("required_cases") or [])
        observed = [c.get("id") for c in cases]
        if not required or required != set(observed) or len(observed) != len(set(observed)):
            findings.append(Finding("coverage_gap", None, "required case registry is missing, incomplete or duplicated"))
        if (report.get("code_binding") or {}).get("verified") is not True:
            findings.append(Finding("unbound_code", None, "matrix lacks verified import binding"))
        if (report.get("scope") or {}).get("batch_elapsed_seconds", float("inf")) > 180:
            findings.append(Finding("deadline_exceeded", None, "absolute batch deadline exceeded"))
''')
text = text.replace('if expected.get("run_twice") and (counters.get("run2_fixture_requests") or 0) != 0:',
    'if expected.get("run_twice") and count(counters.get("run2_fixture_requests")) != 0:')
text = text.replace('            if actual.get("unknown_usage_reported_as_zero") or actual.get("calls_swallowed"):',
    '''            if (actual.get("unknown_usage_reported_as_zero") or actual.get("calls_swallowed")
                    or ("provider_requests" in actual and actual.get("provider_usage_complete") is not True
                        and actual.get("provider_requests") is not None)):''')
path.write_text(text, encoding="utf-8")
print("Shared typed predicates installed; exact negative response and missing counter mistakes repaired.")
