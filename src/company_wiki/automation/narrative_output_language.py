"""Finite offline observations of actual summary prose and its cited originals.

This is not a language header validator, a translation detector for every word,
or an entailment test. Short labels and contradictory/mixed prose abstain. The
identifier's normalized posterior is deliberately not treated as accuracy.
"""
from __future__ import annotations

from collections.abc import Sequence
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
from importlib import import_module
from importlib.metadata import PackageNotFoundError, version as distribution_version
import os
from pathlib import Path
import re
import threading
from typing import Any, Literal, Protocol

from company_wiki.source_catalog.narrative_evidence import SummaryClaim
from company_wiki.source_contract.evidence_span import EvidenceSpan


@dataclass(frozen=True)
class LanguageObservation:
    state: Literal["compatible", "different", "uncertain", "unavailable"]
    output_family: str | None
    source_families: tuple[str, ...]
    prose_claims: int


class _Identifier(Protocol):
    def classify(self, text: str) -> tuple[str, float]: ...


_IDENTIFIERS = threading.local()
_LANGUAGE_RESOURCE_DIGESTS: OrderedDict[tuple, tuple[str, int]] = OrderedDict()
_LANGUAGE_RESOURCE_DIGEST_LOCK = threading.Lock()
_LANGUAGE_RESOURCE_DIGEST_LIMIT = 16
_MAX_CLAIMS = 20
_MAX_SPANS = 96
_MAX_CITED_CHARS = 48_000
_MAX_CLAIM_CHARS = 5_600
_WORDS = re.compile(r"[^\W\d_]+", re.UNICODE)
_CLAUSE_END = re.compile(r"[.!?。！？;；]")
# A semicolon/operating list is still part of its grammatical claim. Splitting
# it can turn retained English product names in Spanish prose into a false
# second language. Independent complete sentences can add mixed-prose evidence.
_SENTENCES = re.compile(r"(?<=[.!?。！？])\s*|\n+")
_QUOTES = re.compile(r'"([^"\n]+)"|“([^”\n]+)”|‘([^’\n]+)’|«([^»\n]+)»|「([^」\n]+)」|『([^』\n]+)』')


def _language_distribution(name: str) -> dict[str, Any]:
    try:
        actual = distribution_version(name)
    except (PackageNotFoundError, OSError, ValueError):
        actual = None
    if not isinstance(actual, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+!_-]{0,127}", actual):
        actual = None
    return {"distribution": name, "version": actual,
            "status": "available" if actual is not None else "unavailable"}


def _language_resource_identity(path: Any, *, code: bool) -> dict[str, Any]:
    """Memoize static software assets only, never document text or classifiers.

    Stat keys notice deletion/replacement/change. The digest is pathless; an
    identical install at another location produces the same public identity.
    Weight hashing streams bytes once rather than rereading it for every source.
    """
    unavailable = {"status": "unavailable", "sha256": None, "bytes": None}
    try:
        resource = Path(path)
        def file_key():
            stat = resource.stat()
            return (str(resource.resolve()), stat.st_dev, stat.st_ino, stat.st_size,
                    stat.st_mtime_ns, stat.st_ctime_ns, code)
        key = file_key()
        with _LANGUAGE_RESOURCE_DIGEST_LOCK:
            cached = _LANGUAGE_RESOURCE_DIGESTS.get(key)
            if cached is not None:
                _LANGUAGE_RESOURCE_DIGESTS.move_to_end(key)
        if cached is None:
            digest = hashlib.sha256()
            count = 0
            if code:
                contents = resource.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                digest.update(contents)
                count = len(contents)
            else:
                with resource.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                        count += len(chunk)
            if file_key() != key:
                return unavailable  # Do not pin a changing resource's partial bytes.
            cached = (digest.hexdigest(), count)
            with _LANGUAGE_RESOURCE_DIGEST_LOCK:
                _LANGUAGE_RESOURCE_DIGESTS[key] = cached
                _LANGUAGE_RESOURCE_DIGESTS.move_to_end(key)
                while len(_LANGUAGE_RESOURCE_DIGESTS) > _LANGUAGE_RESOURCE_DIGEST_LIMIT:
                    _LANGUAGE_RESOURCE_DIGESTS.popitem(last=False)
    except (OSError, RuntimeError, TypeError, ValueError):
        return unavailable
    return {"status": "available", "sha256": cached[0], "bytes": cached[1]}


def language_observer_identity() -> dict[str, Any]:
    """Actual classifier software/data identity without loading a classifier.

    Missing components stay visible and restoring them changes causality. This
    is diagnostic software identity, not document processing permission.
    """
    classifier = _language_distribution("py3langid")
    unavailable = {"status": "unavailable", "sha256": None, "bytes": None}
    try:
        module = import_module("py3langid.langid")
    except (ImportError, OSError, RuntimeError, ValueError):
        classifier["module"] = dict(unavailable)
        classifier["model"] = dict(unavailable)
    else:
        classifier["module"] = _language_resource_identity(getattr(module, "__file__", None), code=True)
        try:
            model_name = getattr(module, "MODEL_FILE", None)
            if model_name is None:
                raise ValueError("classifier model resource is missing")
            model_file = Path(model_name)
            # LanguageIdentifier.from_model_file resolves relative resources
            # against its MODEL_DIR, not the document worker's current directory.
            if not model_file.is_absolute():
                model_dir = getattr(module, "MODEL_DIR", None)
                if model_dir is None:
                    raise ValueError("classifier model resource base is missing")
                model_file = Path(model_dir) / model_file
        except (OSError, RuntimeError, TypeError, ValueError):
            classifier["model"] = dict(unavailable)
        else:
            classifier["model"] = _language_resource_identity(model_file, code=False)
    if (classifier["module"]["status"] != "available"
            or classifier["model"]["status"] != "available"):
        classifier["status"] = "unavailable"
    return {"schema_version": "narrative-language-observer/1",
            "py3langid": classifier, "numpy": _language_distribution("numpy")}


def _new_identifier() -> _Identifier:
    # Never use the library's mutable module-level identifier or limit its
    # languages to our test corpus. The shipped model currently has 140 labels.
    from py3langid.langid import LanguageIdentifier, MODEL_FILE  # type: ignore[import-untyped]

    return LanguageIdentifier.from_model_file(MODEL_FILE, norm_probs=True)


def _get_identifier() -> _Identifier:
    pid = os.getpid()
    if getattr(_IDENTIFIERS, "pid", None) != pid:
        identifier = _new_identifier()
        _IDENTIFIERS.identifier = identifier
        _IDENTIFIERS.pid = pid
    return _IDENTIFIERS.identifier


def _han_letters(text: str) -> int:
    return sum("\u3400" <= char <= "\u9fff" or "\U00020000" <= char <= "\U0003134f" for char in text)


def _has_prose(text: str) -> bool:
    # These are finite information floors, not a calibrated correctness score.
    # A long identifier alone and a short sentence cannot establish a language.
    han = _han_letters(text)
    letters = sum(char.isalpha() for char in text)
    words = len(_WORDS.findall(text))
    clauses = bool(_CLAUSE_END.search(text))
    return (han >= 20 and (clauses or han >= 40)) or (
        letters >= 40 and words >= 6 and (clauses or words >= 12)
    )


def _long_prose(text: str) -> bool:
    return _han_letters(text) >= 40 or (
        sum(char.isalpha() for char in text) >= 100 and len(_WORDS.findall(text)) >= 12
    )


def _family(label: str) -> str | None:
    if label in {"zh", "wuu", "yue"}:
        return "zh"
    if not isinstance(label, str) or label == "zxx" or not re.fullmatch(r"[a-z]{2,3}", label):
        return None
    return label


def _own_prose(text: str, originals: tuple[str, ...]) -> tuple[str, bool]:
    stripped = text.strip()
    if any(stripped in original for original in originals):
        return stripped, True
    outer = _QUOTES.fullmatch(stripped)
    if outer is not None:
        quoted = next(value for value in outer.groups() if value is not None)
        if any(quoted in original for original in originals):
            return quoted, True

    def retained_quote(match: re.Match[str]) -> str:
        quoted = next(value for value in match.groups() if value is not None)
        # Only exact text in this claim's own citations is an original quote.
        # An unreferenced foreign passage never erases generated claim prose.
        return " " if any(quoted in original for original in originals) else match.group()

    return _QUOTES.sub(retained_quote, text).strip(), False


def observe_summary_language(
    claims: Sequence[SummaryClaim], *, evidence_spans: Sequence[EvidenceSpan],
) -> LanguageObservation:
    """Observe only actual claim prose and unique raw spans it actually cites.

    Bounds or unavailable classification return explicit abstention. No body,
    probability, source metadata, provider call, permission, or persistent state
    is emitted. Canonical citation and fact validation remain their owners' job.
    """
    unavailable = LanguageObservation("unavailable", None, (), 0)
    if len(claims) > _MAX_CLAIMS or len(evidence_spans) > _MAX_SPANS:
        return unavailable
    if sum(len(claim.text) for claim in claims) > _MAX_CLAIM_CHARS:
        return unavailable
    known = {span.span_id: span for span in evidence_spans}
    cited_ids = tuple(dict.fromkeys(span_id for claim in claims for span_id in claim.evidence_ids))
    if any(span_id not in known for span_id in cited_ids):
        return LanguageObservation("uncertain", None, (), 0)
    cited = tuple(known[span_id].raw_text or "" for span_id in cited_ids)
    if sum(map(len, cited)) > _MAX_CITED_CHARS:
        return unavailable
    observations = []
    for claim in claims:
        originals = tuple(known[span_id].raw_text or "" for span_id in claim.evidence_ids)
        text, verbatim = _own_prose(claim.text, originals)
        if _has_prose(text):
            observations.append((text, verbatim, claim.evidence_ids))
    prose_claims = len(observations)
    if not observations:
        return LanguageObservation("uncertain", None, (), 0)

    try:
        identifier = _get_identifier()
        cache: dict[str, str | None] = {}

        def classify(text: str) -> str | None:
            if text not in cache:
                label, _uncalibrated_posterior = identifier.classify(text)
                cache[text] = _family(label)
            return cache[text]

        def families(text: str) -> tuple[set[str], bool]:
            chunks = [part for part in _SENTENCES.split(text) if _has_prose(part)]
            if not chunks and _has_prose(text):
                chunks = [text]
            if not chunks:
                return set(), True
            labels = [classify(part) for part in chunks]
            present = {label for label in labels if label is not None}
            aggregate = classify(text)
            return present, None not in labels and aggregate is not None and aggregate in present

        output_labels: set[str] = set()
        output_agrees = True
        output_by_claim = []
        for text, _verbatim, _citations in observations:
            labels, agrees = families(text)
            output_by_claim.append((labels, agrees))
            output_labels.update(labels)
            output_agrees = output_agrees and agrees and len(labels) == 1
        output_aggregate = classify("\n".join(text for text, _verbatim, _citations in observations))
        output_agrees = output_agrees and len(output_labels) == 1 and output_aggregate in output_labels
        output_family = next(iter(output_labels)) if output_agrees else None

        source_labels: set[str] = set()
        source_agrees = True
        source_prose = [text for text in cited if _has_prose(text)]
        source_by_id: dict[str, tuple[set[str], bool]] = {}
        for span_id in cited_ids:
            text = known[span_id].raw_text or ""
            labels, agrees = families(text)
            source_by_id[span_id] = (labels, agrees)
            source_labels.update(labels)
            source_agrees = source_agrees and agrees
        source_aggregate = classify("\n".join(source_prose)) if source_prose else None
        source_agrees = source_agrees and bool(source_labels) and source_aggregate in source_labels
        local_observable = True
        local_supported = True
        locally_compatible = True
        strong_local_difference = False
        for (text, verbatim, citations), (output, output_consensus) in zip(
            observations, output_by_claim, strict=True
        ):
            local_labels: set[str] = set()
            local_agrees = True
            for span_id in citations:
                labels, agrees = source_by_id[span_id]
                local_labels.update(labels)
                local_agrees = local_agrees and agrees
            local_observable = local_observable and bool(local_labels) and local_agrees
            local_supported = local_supported and output_family in local_labels
            own_family = next(iter(output)) if output_consensus and len(output) == 1 else None
            own_observable = bool(local_labels) and local_agrees and own_family is not None
            # Each substantive claim owns its language proof. A different
            # claim's native lane, abstention or output language cannot erase
            # a strong mismatch here. Reuse this pass's source/output families;
            # never run the whole source analysis again for every claim.
            strong = own_observable and _long_prose(text)
            if strong and not verbatim and own_family not in local_labels:
                strong_local_difference = True
            locally_compatible = locally_compatible and (
                verbatim or strong and own_family in local_labels
            )
    except Exception:
        # Missing library/model or internal classifier faults are observable;
        # they must not masquerade as English, compatibility, or translation.
        return LanguageObservation("unavailable", None, (), prose_claims)

    source_families = tuple(sorted(source_labels))
    if all(verbatim for _text, verbatim, _citations in observations):
        return LanguageObservation("compatible", output_family, source_families, prose_claims)
    if strong_local_difference:
        return LanguageObservation("different", output_family, source_families, prose_claims)
    if locally_compatible and source_agrees and output_aggregate in output_labels:
        # Several independently supported native languages need no invented
        # single output family; None honestly describes their aggregate.
        return LanguageObservation("compatible", output_family, source_families, prose_claims)
    enough_output = prose_claims >= 2 or any(_long_prose(text) for text, _verbatim, _citations in observations)
    if not output_agrees or not source_agrees or not enough_output or not local_observable:
        return LanguageObservation("uncertain", output_family, source_families, prose_claims)
    if output_family in source_labels and not local_supported:
        # A different claim's citation is not language evidence for this one.
        return LanguageObservation("uncertain", output_family, source_families, prose_claims)
    state: Literal["compatible", "different"] = "compatible" if output_family in source_labels else "different"
    return LanguageObservation(state, output_family, source_families, prose_claims)
