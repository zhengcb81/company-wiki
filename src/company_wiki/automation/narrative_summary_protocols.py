"""Explicit scoped-summary recipes and their artifact format; no IO or models."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ScopedSummaryProtocol:
    projection: str
    prompt: str
    request_schema: str
    decoder: str
    plan_max_claims: int
    assess_fidelity: bool = False


LEGACY_SCOPED = ScopedSummaryProtocol('reading-model-input/4','reading-source-scoped/4.1.0',
    'narrative-model-request/5','reading-scoped-task-decoder/4',20)
FIDELITY_SCOPED = ScopedSummaryProtocol('reading-model-input/6','reading-source-scoped/4.2.0',
    'narrative-model-request/7','reading-scoped-task-decoder/6',40,True)


def scoped_protocol_for_prompt(prompt: str) -> ScopedSummaryProtocol:
    for protocol in (LEGACY_SCOPED,FIDELITY_SCOPED):
        if protocol.prompt==prompt:
            return protocol
    raise ValueError('unknown scoped summary prompt')


@dataclass(frozen=True)
class SummaryBundleFormat:
    raw_schema: str
    projected_schema: str
    producer: str
    assessed: bool


LEGACY_BUNDLE = SummaryBundleFormat('narrative-bundle/2.0','narrative-bundle/3.0','1.0.0',False)
ASSESSED_BUNDLE = SummaryBundleFormat('narrative-bundle/2.1','narrative-bundle/3.1','1.1.0',True)


def summary_bundle_format(prompt: str | None) -> SummaryBundleFormat:
    return ASSESSED_BUNDLE if prompt==FIDELITY_SCOPED.prompt else LEGACY_BUNDLE
