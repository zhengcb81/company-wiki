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
}
SOURCE_FACT_KINDS = {kind: source_type.value for kind, (source_type, _) in SIDECAR_KIND_MAP.items()}
SOURCE_FACT_KINDS["other"] = SourceType.OTHER.value
