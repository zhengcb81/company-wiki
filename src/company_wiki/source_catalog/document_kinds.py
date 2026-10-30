"""One mapping from declared document kinds to upstream source families."""
from company_wiki.source_contract import SourceType

SIDECAR_KIND_MAP = {
    "annual_report": (SourceType.REGULATORY_FILING, "annual_report"),
    "semi_annual_report": (SourceType.REGULATORY_FILING, "semi_annual_report"),
    "quarterly_report": (SourceType.REGULATORY_FILING, "quarterly_report"),
    "regulatory_filing": (SourceType.REGULATORY_FILING, "regulatory_filing"),
    "broker_research": (SourceType.BROKER_RESEARCH, "broker_research"),
    "investor_relations": (SourceType.INVESTOR_RELATIONS, "investor_relations"),
    "investor_call_transcript": (SourceType.INVESTOR_RELATIONS, "investor_call_transcript"),
    "prospectus": (SourceType.PROSPECTUS, "prospectus"),
    "equity_offering_prospectus": (SourceType.PROSPECTUS, "equity_offering_prospectus"),
    "convertible_bond_prospectus": (SourceType.PROSPECTUS, "convertible_bond_prospectus"),
    "news": (SourceType.ORIGINAL_NEWS, "news"),
    # W19: third-party multi-period statement datasets (sina_finance). A
    # dataset is source material, not a periodic filing: no fictitious FY.
    "financial_statement_dataset": (SourceType.OTHER, "financial_statement_dataset"),
}
SOURCE_FACT_KINDS = {kind: source_type.value for kind, (source_type, _) in SIDECAR_KIND_MAP.items()}
SOURCE_FACT_KINDS["other"] = SourceType.OTHER.value

# These source families describe reporting periods. Presentations, research,
# announcements and other nonperiodic originals do not acquire a fictitious FY.
PERIODIC_DOCUMENT_KINDS = frozenset({
    "annual_report", "semi_annual_report", "quarterly_report",
    "regulatory_filing", "investor_call_transcript",
})


def sec_primary_document_kind(form_type: str) -> str:
    """Classify an observed primary SEC form independently of a query."""
    return 'annual_report' if form_type.removesuffix('/A') in {'10-K','20-F'} else 'regulatory_filing'


def requested_kind_candidates(requested: str) -> tuple[str, ...]:
    """A generic regulatory request includes its concrete financial families."""
    if requested == 'regulatory_filing':
        return tuple(sorted(kind for kind, source_type in SOURCE_FACT_KINDS.items()
                            if source_type == SourceType.REGULATORY_FILING.value))
    return (requested,)


def document_kind_matches(requested: str, observed: str) -> bool:
    return observed in requested_kind_candidates(requested)
