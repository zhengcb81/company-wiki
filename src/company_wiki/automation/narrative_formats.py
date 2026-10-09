"""Parser routing and generation identity shared by selection and replay."""
from company_wiki.source_catalog.narrative_evidence import NARRATIVE_PARSER_NAME, NARRATIVE_PARSER_VERSION, TRANSCRIPT_PARSER_VERSION

NORMALIZED_MIME_TYPES = frozenset({
    "text/html", "application/xhtml+xml",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
})


def parser_component(mime_type: str, source_class: str = "filing", *, normalization=None, parser_version=None) -> tuple[str, str]:
    if source_class == "filing" and mime_type in NORMALIZED_MIME_TYPES:
        if normalization is None:
            from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization
            normalization = NarrativeNormalization()
        identity = normalization.identity(mime_type, parser_version=parser_version)
        return identity["parser_name"], identity["parser_version"]
    if source_class == "transcript":
        version = parser_version or TRANSCRIPT_PARSER_VERSION
        if version not in {NARRATIVE_PARSER_VERSION, TRANSCRIPT_PARSER_VERSION}:
            raise ValueError("unsupported transcript parser version")
        return NARRATIVE_PARSER_NAME, version
    return NARRATIVE_PARSER_NAME, NARRATIVE_PARSER_VERSION


def source_class_for(mime_type: str, document_kind: str) -> str:
    """Choose a byte/locator parser, keeping the real document kind separate.

    A PDF earnings call remains an investor_call_transcript but uses page/block
    replay. Plain TXT/JSON and provider transcript HTML use transcript byte
    lineage. IR/release HTML uses deterministic DOM/table coordinates.
    """
    if mime_type in {"text/plain", "application/json"}:
        return "transcript"
    if document_kind == "investor_call_transcript" and mime_type in {"text/html", "application/xhtml+xml"}:
        return "transcript"
    return "filing"
