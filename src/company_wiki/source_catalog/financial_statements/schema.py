"""DDL owner for financial statements and compact content transitions.

Two generic long tables keyed by ``statement_type`` — not one wide table per
statement and not company Markdown. ``store._DDL`` appends this text so fresh
databases and every in-place upgrade share one definition.
"""

from __future__ import annotations

FINANCIAL_STATEMENTS_SCHEMA_NOTE = "catalog 1.4.0: statements with ordered content observations"

FINANCIAL_STATEMENTS_DDL = """
CREATE TABLE IF NOT EXISTS financial_statement_versions (
    statement_version_id TEXT PRIMARY KEY,
    entity TEXT NOT NULL,
    market TEXT NOT NULL,
    security_id TEXT NOT NULL,
    exchange TEXT NOT NULL,
    code TEXT NOT NULL,
    provider TEXT NOT NULL,
    statement_type TEXT NOT NULL CHECK (
        statement_type IN ('income_statement', 'balance_sheet', 'cash_flow')
    ),
    period_end TEXT NOT NULL,
    period_kind TEXT NOT NULL CHECK (
        period_kind IN ('annual', 'semi_annual', 'q1', 'q3')
    ),
    period_start TEXT,
    consolidation TEXT NOT NULL CHECK (
        consolidation IN ('consolidated', 'parent', 'unknown')
    ),
    currency TEXT,
    provider_rType TEXT,
    provider_publish_date TEXT,
    provider_update_time TEXT,
    provider_is_audit TEXT,
    provider_data_source TEXT,
    provider_date_description TEXT,
    provider_report_date_type INTEGER,
    canonical_report_sha256 TEXT NOT NULL,
    normalizer_version TEXT NOT NULL,
    source_id TEXT NOT NULL,
    document_id TEXT NOT NULL,
    source_url TEXT,
    row_count INTEGER NOT NULL CHECK (row_count >= 0),
    quality_flags_json TEXT NOT NULL,
    captured_at TEXT NOT NULL,
    first_seen_at TEXT NOT NULL,
    last_checked_at TEXT,
    UNIQUE (
        security_id, provider, statement_type, period_end, consolidation,
        canonical_report_sha256
    ),
    FOREIGN KEY(source_id) REFERENCES sources(source_id),
    FOREIGN KEY(document_id) REFERENCES documents(document_id)
);
CREATE INDEX IF NOT EXISTS idx_finstat_versions_query
ON financial_statement_versions(security_id, statement_type, period_end);
CREATE INDEX IF NOT EXISTS idx_finstat_versions_source
ON financial_statement_versions(source_id);
CREATE TABLE IF NOT EXISTS financial_statement_observations (
    observation_id INTEGER PRIMARY KEY,
    statement_version_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    order_verified INTEGER NOT NULL DEFAULT 1,
    FOREIGN KEY(statement_version_id)
        REFERENCES financial_statement_versions(statement_version_id)
);
CREATE INDEX IF NOT EXISTS idx_finstat_observation_version
ON financial_statement_observations(statement_version_id, observed_at);
-- Pre-release 1.3 captures remain readable; their within-second ordering was
-- never recorded. Do not pretend a hash ordering proves an observation order.
INSERT INTO financial_statement_observations(statement_version_id, observed_at, order_verified)
SELECT v.statement_version_id, v.captured_at, 0
FROM financial_statement_versions v
WHERE NOT EXISTS (SELECT 1 FROM financial_statement_observations o
                  WHERE o.statement_version_id=v.statement_version_id)
ORDER BY v.captured_at, v.statement_version_id;
CREATE TABLE IF NOT EXISTS financial_statement_values (
    statement_version_id TEXT NOT NULL,
    row_ordinal INTEGER NOT NULL CHECK (row_ordinal >= 1),
    provider_field TEXT NOT NULL,
    label TEXT NOT NULL,
    raw_value TEXT,
    value_decimal TEXT,
    value_kind TEXT NOT NULL CHECK (
        value_kind IN ('numeric', 'null', 'empty', 'non_numeric', 'group')
    ),
    unit TEXT,
    scale INTEGER,
    provider_precision TEXT,
    json_pointer TEXT NOT NULL,
    item_group_no INTEGER,
    item_display_type INTEGER,
    quality_flags_json TEXT NOT NULL,
    PRIMARY KEY (statement_version_id, row_ordinal),
    FOREIGN KEY (statement_version_id)
        REFERENCES financial_statement_versions(statement_version_id)
);
CREATE INDEX IF NOT EXISTS idx_finstat_values_field
ON financial_statement_values(statement_version_id, provider_field);
CREATE TABLE IF NOT EXISTS financial_statement_coverage (
    security_id TEXT NOT NULL,
    provider TEXT NOT NULL,
    statement_type TEXT NOT NULL,
    advertised_report_count INTEGER,
    observed_periods INTEGER NOT NULL,
    first_period_end TEXT,
    last_period_end TEXT,
    terminal_reason TEXT,
    fetched_from TEXT,
    fetched_to TEXT,
    last_http_requests INTEGER,
    last_response_bytes INTEGER,
    observed_at TEXT NOT NULL,
    PRIMARY KEY (security_id, provider, statement_type)
);
"""

__all__ = ["FINANCIAL_STATEMENTS_DDL", "FINANCIAL_STATEMENTS_SCHEMA_NOTE"]
