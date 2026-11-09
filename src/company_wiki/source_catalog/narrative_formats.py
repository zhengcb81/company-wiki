"""Source-owned parser identity and carrier routing for narrative material."""

from company_wiki.source_catalog.narrative_evidence import (
    NARRATIVE_PARSER_NAME,
    NARRATIVE_PARSER_VERSION,
    transcript_parser_contract,
)

NORMALIZED_MIME_TYPES = frozenset({
    "text/html", "application/xhtml+xml",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
})


def parser_component(
    mime_type: str,
    source_class: str = "filing",
    *,
    normalization=None,
    parser_version=None,
    pdf_reading=None,
) -> tuple[str, str]:
    if source_class == "filing" and mime_type == "application/pdf":
        if pdf_reading is None:
            from company_wiki.source_catalog.narrative_pdf_reading import PdfReading

            pdf_reading = PdfReading()
        return pdf_reading.parser_identity()
    if source_class == "filing" and mime_type in NORMALIZED_MIME_TYPES:
        if normalization is None:
            from company_wiki.source_catalog.narrative_normalization import NarrativeNormalization

            normalization = NarrativeNormalization()
        identity = normalization.identity(mime_type, parser_version=parser_version)
        return identity["parser_name"], identity["parser_version"]
    if source_class == "transcript":
        contract = transcript_parser_contract(parser_version)
        return contract.parser_name, contract.parser_version
    return NARRATIVE_PARSER_NAME, NARRATIVE_PARSER_VERSION


def source_class_for(mime_type: str, document_kind: str) -> str:
    """Route source bytes to the parser family without changing document kind."""
    if mime_type in {"text/plain", "application/json"}:
        return "transcript"
    if document_kind == "investor_call_transcript" and mime_type in {"text/html", "application/xhtml+xml"}:
        return "transcript"
    return "filing"


__all__ = [
    "NORMALIZED_MIME_TYPES",
    "NARRATIVE_PARSER_NAME",
    "NARRATIVE_PARSER_VERSION",
    "parser_component",
    "source_class_for",
    "transcript_parser_contract",
]
