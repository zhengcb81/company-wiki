"""Explicit scoped-summary recipes and their artifact format; no IO or models."""
from dataclasses import dataclass
from types import MappingProxyType


@dataclass(frozen=True)
class ScopedSummaryProtocol:
    projection: str
    prompt: str
    request_schema: str
    decoder: str
    plan_max_claims: int
    assess_fidelity: bool = False
    instruction_profile: str = 'legacy'
    material_profile: str = 'source_scoped/1'
    output_profile: str = 'legacy'
    assessor_version: str | None = None
    allows_subset: bool = True


LEGACY_SCOPED = ScopedSummaryProtocol('reading-model-input/4','reading-source-scoped/4.1.0',
    'narrative-model-request/5','reading-scoped-task-decoder/4',20)
FIDELITY_SCOPED = ScopedSummaryProtocol('reading-model-input/6','reading-source-scoped/4.2.0',
    'narrative-model-request/7','reading-scoped-task-decoder/6',40,True,
    'fidelity','source_scoped/1','coverage','source-summary-assessment/1.0.0',False)
ATOMIC_SCOPED = ScopedSummaryProtocol('reading-model-input/7','reading-source-scoped/4.3.0',
    'narrative-model-request/8','reading-scoped-task-decoder/7',40,True,
    'atomic','source_frames/1','coverage','source-summary-assessment/1.1.0',False)

SCOPED_PROTOCOLS = (LEGACY_SCOPED, FIDELITY_SCOPED, ATOMIC_SCOPED)
_BY_PROJECTION = MappingProxyType({item.projection: item for item in SCOPED_PROTOCOLS})
_BY_PROMPT = MappingProxyType({item.prompt: item for item in SCOPED_PROTOCOLS})
_BY_REQUEST = MappingProxyType({item.request_schema: item for item in SCOPED_PROTOCOLS})
if any(len(index) != len(SCOPED_PROTOCOLS) for index in (_BY_PROJECTION, _BY_PROMPT, _BY_REQUEST)):
    raise ValueError('duplicate scoped protocol identity')
SCOPED_PROJECTIONS = frozenset(_BY_PROJECTION)
ASSESSED_PROMPTS = frozenset(item.prompt for item in SCOPED_PROTOCOLS if item.assess_fidelity)


def scoped_protocol_for_projection(version: str | None) -> ScopedSummaryProtocol | None:
    return _BY_PROJECTION.get(version) if isinstance(version, str) else None


def scoped_protocol_for_request(version: str) -> ScopedSummaryProtocol | None:
    return _BY_REQUEST.get(version) if isinstance(version, str) else None


def scoped_protocol_for_prompt(prompt: str) -> ScopedSummaryProtocol:
    if not isinstance(prompt, str):
        raise ValueError('unknown scoped summary prompt')
    try:
        return _BY_PROMPT[prompt]
    except KeyError as exc:
        raise ValueError('unknown scoped summary prompt') from exc


@dataclass(frozen=True)
class SummaryBundleFormat:
    raw_schema: str
    projected_schema: str
    producer: str
    assessed: bool


LEGACY_BUNDLE = SummaryBundleFormat('narrative-bundle/2.0','narrative-bundle/3.0','1.0.0',False)
ASSESSED_BUNDLE = SummaryBundleFormat('narrative-bundle/2.1','narrative-bundle/3.1','1.1.0',True)


def summary_bundle_format(prompt: str | None) -> SummaryBundleFormat:
    if prompt is not None and not isinstance(prompt, str):
        raise ValueError('unknown scoped summary prompt')
    if prompt in ASSESSED_PROMPTS:
        return ASSESSED_BUNDLE
    if prompt is not None and prompt.startswith('reading-source-scoped/'):
        scoped_protocol_for_prompt(prompt)
    return LEGACY_BUNDLE
