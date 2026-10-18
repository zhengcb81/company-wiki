"""Frozen names for the P4 consumer-contract lane.

Every value here is copied from ``card.md`` section 5 or ``INTERFACES.md``; this
module redefines nothing the runtime owns and is read-only to the rest of the
lane.
"""

from __future__ import annotations

from pathlib import Path


# --- frozen schema versions (card 5.2 - 5.4) --------------------------------

P4_COMMANDS_SCHEMA = "p4-consumer-commands/1"
P4_OBSERVATION_SCHEMA = "p4-consumer-observation/1"
P4_RECEIPT_SCHEMA = "p4-contract-receipt/1"
P4_FIXTURE_SCHEMA = "p4-fixture-expectations/1"

# Read-only upstream versions this lane consumes but must never redefine.
SOURCE_REF_SCHEMA_VERSION = "2.0"
SOURCE_READ_RECEIPT_SCHEMA_VERSION = "2.1"
AVAILABILITY_RECEIPT_SCHEMA_VERSION = "2.2"
SOURCE_EXPORT_V2_SCHEMA_VERSION = "2.0.0"
EVIDENCE_SPAN_SCHEMA_VERSION = "1.0.0"

# --- environment switches (card 5.1: the only switching mechanism) -----------

ENV_CATALOG = "CWP_P4_CATALOG_CONFIG"
ENV_FF_ROOT = "CWP_P4_FF_ROOT"
ENV_RF_ROOT = "CWP_P4_RF_ROOT"
ENV_CONSUMER_COMMANDS = "CWP_P4_CONSUMER_COMMANDS"
ENV_REQUIRE = "CWP_P4_REQUIRE"

REQUIRE_CATALOG_REASON = "P4 requires CWP_P4_CATALOG_CONFIG"
REQUIRE_COMMANDS_REASON = "P4 requires CWP_P4_CONSUMER_COMMANDS"

# --- error codes (INTERFACES.md section 3) -----------------------------------

CODE_FIELD_MISSING = "p4_consumer_field_missing"
CODE_UNIT_RESCALED = "p4_consumer_unit_rescaled"
CODE_AVAILABILITY_LOST = "p4_unknown_availability_lost"
CODE_NETWORK_ATTEMPTED = "p4_network_attempted"
CODE_MODEL_ATTEMPTED = "p4_model_attempted"

CODE_INVALID_JSON = "invalid_json"
CODE_INVALID_ARGUMENT = "invalid_argument"
CODE_LIMIT_EXCEEDED = "limit_exceeded"
CODE_RECEIPT_TOO_LARGE = "receipt_too_large"
CODE_DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
CODE_NOT_CONFIGURED = "not_configured"

UNMAPPED_CONSUMER_OUTPUT = "unmapped_consumer_output"

# --- statuses ---------------------------------------------------------------

TOP_LEVEL_STATUSES = ("ok", "partial", "fail", "blocked", "unavailable")
CASE_STATUSES = ("pass", "fail", "skip", "not_evaluated")
CHECK_STATUSES = ("pass", "fail", "not_applicable", "not_evaluated")

# --- limits (card section 8) -------------------------------------------------

MAX_RECEIPT_BYTES = 16 * 1024 * 1024
MAX_CONSUMER_STDOUT_BYTES = 16 * 1024 * 1024
CONSUMER_STDOUT_PREFIX_BYTES = 2 * 1024
MAX_COMMAND_TIMEOUT_S = 300
CASE_TIMEOUT_S = 300

# --- layout ------------------------------------------------------------------

SUPPORT_DIR = Path(__file__).resolve().parent
LANE_DIR = SUPPORT_DIR.parent
REPO_ROOT = LANE_DIR.parents[2]
CARD_DIR = REPO_ROOT / "docs" / "plans" / "parallel-packages-2026-10-18" / "P4-CONSUMER-CONTRACT"
FIXTURES_DIR = CARD_DIR / "fixtures"
RECEIPT_PATH = CARD_DIR / "receipt.json"
PRODUCTION_CATALOG_CONFIG = REPO_ROOT / "config" / "source_catalog.yaml"

# --- observation shape (card 5.3, verbatim keys) -----------------------------

OBSERVATION_KEYS = frozenset({
    "schema_version", "consumer", "source_ref", "facts", "availability",
    "quotes", "downloads", "model_calls",
})
SOURCE_REF_KEYS = frozenset({
    "document_id", "source_id", "content_sha256", "byte_size", "mime_type",
    "schema_version",
})
FACT_KEYS = (
    "document_kind", "canonical_entity_id", "market", "security_id",
    "fiscal_year", "fiscal_period", "period_end", "published_date",
    "form_type", "language",
)
FACT_KEY_SET = frozenset(FACT_KEYS)
AVAILABILITY_KEYS = frozenset({"status", "evidence"})
QUOTE_KEYS = frozenset({"text", "unit_tokens"})
UNIT_TOKEN_KEYS = frozenset({"text"})
COUNT_KEYS = frozenset({"count"})

AVAILABILITY_UNKNOWN = "source_availability_unknown"
AVAILABILITY_OBSERVED = "observed"
CONSUMERS = ("ff", "rf")

# The five fields compared literally in the ref-roundtrip check (card 5.5.1).
REF_ROUNDTRIP_FIELDS = (
    "document_id", "source_id", "content_sha256", "byte_size", "mime_type",
)

LIMITATIONS = [
    "未跑真实生产 catalog：全部输入来自本卡 fixtures/ 的合成 catalog。",
    "消费端是否真实只读取决于 ROOT 提供的命令清单；"
    "本卡只执行清单 argv，不探测子命令。",
    "hidden checks only prove the lane's own comparators; "
    "consumer behaviour is proven only when ROOT supplies a manifest.",
]
