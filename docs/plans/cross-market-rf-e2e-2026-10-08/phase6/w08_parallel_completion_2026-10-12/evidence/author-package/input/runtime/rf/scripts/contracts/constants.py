"""Shared literal constants, extracted from revenue_core.py (R9 split).

Single source of truth for schema/enum constants; revenue_core re-exports
them so the external ``from revenue_core import X`` surface is unchanged.
"""

from __future__ import annotations


SCENARIOS = ("low", "base", "high")


# P7-RF (scoped calibration binding): 4.2.1 re-emits the optional
# research-adequacy calibration diagnostics — actual conversions must be
# carried by bound conversion observations and outputs must be consumed by
# the declared business scope. Revenue arithmetic, schemas and the optional
# operating-research input contract are unchanged.
#
# W05-RF-FLOW: 4.3.0 adds schema 3.10 (dated consolidated contributions).
# The 4.2.1 emit history stays pinned in schema_compatibility.py.
SKILL_VERSION = "4.3.0"


FORECAST_SCHEMA_VERSION = "3.7"


# ZR-711: additive opt-in schema — 3.8 = 3.7 + operating_units (mine-year
# operations per ZR-605) for the mining layer. Opt-in only: 3.7 stays the
# canonical version and its validation behavior is unchanged.
OPT_IN_SCHEMA_VERSION = "3.8"


# M3-FLOW (root cause R20): schema 3.9 = 3.8 + typed dated period flows
# (``time_basis=period_flow`` with ``period_start``/``period_end``) and the
# role-aware mechanism triangulation in the growth-driver tree. Opt-in only;
# 3.7/3.8 keep their exact legacy semantics and reject the new fields.
PERIOD_EVIDENCE_SCHEMA_VERSION = "3.9"


# W05-RF-FLOW: schema 3.10 = 3.9 + dated consolidated contributions: any real
# finite inclusive window (``period_start <= period_end``, same-day flows
# included) may carry a period_flow amount inside its fiscal-year window, with
# explicit derived composition honesty for full-year claims. 3.9 keeps its
# strict 3/6/12-month rule; 3.7/3.8 keep failing closed on the dated fields.
DATED_CONTRIBUTION_SCHEMA_VERSION = "3.10"


# Schemas whose ``time_basis`` vocabulary includes ``period_flow``.
PERIOD_FLOW_SCHEMA_VERSIONS = frozenset({
    PERIOD_EVIDENCE_SCHEMA_VERSION,
    DATED_CONTRIBUTION_SCHEMA_VERSION,
})

# Schemas whose growth-driver triangulation is role-aware (only
# ``mechanism_direction`` claims prove a future mechanism).
MECHANISM_ROLE_SCHEMA_VERSIONS = PERIOD_FLOW_SCHEMA_VERSIONS


SUPPORTED_FORECAST_SCHEMA_VERSIONS = {
    "3.0",
    "3.1",
    "3.2",
    "3.3",
    "3.4",
    "3.5",
    "3.6",
    FORECAST_SCHEMA_VERSION,
    OPT_IN_SCHEMA_VERSION,
    PERIOD_EVIDENCE_SCHEMA_VERSION,
    DATED_CONTRIBUTION_SCHEMA_VERSION,
}


WORKFLOW_RECEIPT_SCHEMA_VERSION = "1.0"


PUBLICATION_RECEIPT_SCHEMA_VERSION = "1.0"


PARAMETER_KINDS = {
    "reported_fact",
    "derived_fact",
    "management_guidance",
    "analyst_assumption",
    "scenario_stress",
}


SOURCE_RANKS = {
    "audited_filing": 1,
    "exchange_filing": 1,
    "regulatory_filing": 1,
    "official_statistics": 1,
    "company_release": 2,
    "investor_presentation": 2,
    "earnings_transcript": 2,
    "official_operating_data": 2,
    "contract_award": 3,
    "customer_filing": 3,
    "tender_document": 3,
    "sector_regulator": 3,
    "industry_association": 4,
    "primary_market_dataset": 4,
    "specialist_research": 5,
    "reputable_news": 5,
}


PARAMETER_DIMENSIONS = {
    "revenue",
    "quantity",
    "ratio",
    "revenue_per_unit",
    "activity",
    "revenue_per_activity",
    "monetary_balance",
    "area",
    "revenue_per_area",
    "backlog",
    "coverage_units",
    "reserve_volume",
}


# ZR-602: asset fact basis contract — ownership/standard/measurement-date
# vocabulary for mining asset facts (resource/reserve/grade/capacity/permit).
# ``basis`` is an additive optional parameter key: when present it must carry
# every required field (fail-closed, no half-baked basis), and asset-fact
# family drivers are unit-consistent (normalized equality, no kt-vs-t drift).
ASSET_FACT_OWNERSHIP_BASES = {
    "one_hundred_percent",
    "equity_share",
    "consolidated",
}

ASSET_FACT_BASIS_REQUIRED = (
    "ownership_basis",
    "reporting_standard",
    "measurement_date",
)

# Generic mining asset-fact model families (model ids are generic mining
# vocabulary, not company/mine names — zero product hardcoding).
ASSET_FACT_MODELS = frozenset({"resource", "reserve_depletion"})


# ZR-604: dual-assertion conflict resolution — when parameters with the
# same semantic key (definition/period/unit/scenario) carry different
# values, ALL must carry resolution_status and at most one is accepted;
# otherwise the original hard-fail (unresolved conflict) applies.
# Assertion_status identifies which assertion is primary vs secondary;
# resolution_status tracks the review outcome.
ASSERTION_STATUSES = {
    "primary",
    "secondary",
}

RESOLUTION_STATUSES = {
    "accepted",
    "rejected",
    "pending_review",
    "under_review",
}


MONETARY_DIMENSIONS = {
    "revenue",
    "revenue_per_unit",
    "revenue_per_activity",
    "monetary_balance",
    "revenue_per_area",
    "backlog",
}


TIME_BASES = {"annual", "point_in_time"}

# M3-FLOW (R20): the dated-flow basis is accepted only on schema 3.9 — it is
# deliberately NOT added to TIME_BASES so 3.7/3.8 documents fail closed on it.
PERIOD_FLOW_TIME_BASIS = "period_flow"

# Calendar month lengths a period_flow may cover (3/6/12). Non-calendar or
# transition fiscal years are covered by the fiscal-window containment rule
# in contracts.period_flow, not by extra lengths.
PERIOD_FLOW_MONTH_LENGTHS = frozenset({3, 6, 12})


# M3-FLOW (R20): the only claim role that asserts an operating mechanism of
# the modeled future growth. History bases, financing background, value
# ranges, conversions, recognition policies, peer analogies, comparisons and
# counterevidence stay disclosed but never count as future-mechanism support.
MECHANISM_EVIDENCE_ROLES = frozenset({"mechanism_direction"})


RECOGNITION_MODES = {"modeled_as_recognized", "lagged_activity"}


RECOGNITION_TIMING = {"point_in_time", "over_time", "mixed"}


PRESENTATIONS = {"gross", "net", "mixed"}


ADJUSTMENT_CATEGORIES = {
    "intersegment_elimination",
    "acquisition_contribution",
    "disposal_contribution",
    "foreign_exchange",
    "reclassification",
    "other",
}


RESEARCH_DIMENSIONS = (
    "company_foundation",
    "growth_curve",
    "industry_market",
    "competition",
    "capacity",
    "technology",
    "policy",
    "customers",
    "demand",
)


RESEARCH_COVERAGE_STATUSES = {"modeled_driver", "data_gap", "immaterial"}


MANAGEMENT_COMMUNICATION_CATEGORIES = (
    "latest_annual_filing",
    "latest_results_release",
    "latest_earnings_call",
    "latest_investor_presentation",
    "latest_strategy_communication",
    "material_announcements_since_last_filing",
)


MANAGEMENT_COMMUNICATION_STATUSES = {"checked", "not_available", "not_applicable", "not_checked", "incomplete"}


MANAGEMENT_TARGET_TREATMENTS = {
    "modeled_scenario",
    "scenario_boundary",
    "independent_benchmark",
    "sensitivity_only",
    "unmodeled_data_gap",
    "out_of_horizon",
}


MANAGEMENT_TARGET_PERIMETERS = {"matched", "reconciled", "mismatch"}


MANAGEMENT_TARGET_COMPARISONS = {"at_least", "at_most", "approximately", "greater_than", "less_than"}


MANAGEMENT_TARGET_MEASUREMENT_BASES = {
    "annual_period",
    "run_rate_at_period_end",
    "cumulative_periods",
    "quarterly_period",
    "ambiguous",
}


# R6-RF-INPUT I2: additive management-target semantics (absent on legacy
# inputs, so existing inputs keep their previous behavior exactly).
MANAGEMENT_TARGET_CURRENCY_BASES = {"reported", "constant_currency"}

MANAGEMENT_TARGET_PRESENTATION_BASES = {"gross", "net"}

MANAGEMENT_TARGET_RAW_VALUE_KINDS = {"numeric", "numeric_range", "qualitative_range"}


GROWTH_DRIVER_TREE_STATUSES = {"modeled", "data_gap"}


GROWTH_DRIVER_PERSISTENCE = {
    "multi_year_structural",
    "cyclical",
    "temporary",
    "uncertain",
}


GROWTH_DRIVER_INFERENCE_DISTANCES = {"direct", "one_step", "analogical", "contrary"}


# R6-RF-INPUT I3: additive evidence roles for claims. Optional on legacy
# inputs; when present the engine enforces role/support-type consistency and
# the growth-driver triangulation excludes peer analogies.
GROWTH_DRIVER_EVIDENCE_ROLES = {
    "history_base",
    "mechanism_direction",
    "value_range",
    "counter_comparison",
    "peer_analogy",
    "conversion_assumption",
    "recognition_policy",
    "counterevidence",
}

# Roles that state a direction or analogy, never a numeric value.
DIRECTIONAL_EVIDENCE_ROLES = {
    "mechanism_direction",
    "peer_analogy",
    "counter_comparison",
    "conversion_assumption",
    "history_base",
    "counterevidence",
}


GROWTH_DRIVER_COUNTEREVIDENCE_STATUSES = {"found", "searched_none_found", "data_gap"}
