"""Parser routing and generation identity shared by selection and replay."""
from company_wiki.document_normalization import PARSER_NAME, PARSER_VERSION
from company_wiki.source_catalog.narrative_evidence import NARRATIVE_PARSER_NAME, NARRATIVE_PARSER_VERSION

NORMALIZED_MIME_TYPES = frozenset({
    "text/html", "application/xhtml+xml",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
})


def parser_component(mime_type: str, source_class: str = "filing") -> tuple[str, str]:
    if source_class == "filing" and mime_type in NORMALIZED_MIME_TYPES:
        return PARSER_NAME, PARSER_VERSION
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
