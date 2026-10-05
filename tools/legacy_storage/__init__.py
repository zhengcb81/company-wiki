"""Legacy derived/evidence storage retirement tools (P5-STORAGE).

Maintenance-only tools: inventory (read-only), retire-derived, prune-spans,
vacuum.  They never touch originals, source facts or new narrative finals.
"""

from legacy_storage.facts import FACT_TABLES, facts_overview, source_facts
from legacy_storage.inventory import run_inventory
from legacy_storage.retirement import run_retire_derived
from legacy_storage.shrink import run_vacuum
from legacy_storage.spans import run_prune_spans

REPORT_SCHEMA = "cwp-storage-retirement/1"
MANIFEST_SCHEMA = "cwp-storage-manifest/1"
SELECTION_SCHEMA = "cwp-span-selection/1"

__all__ = [
    "FACT_TABLES",
    "SELECTION_SCHEMA",
    "MANIFEST_SCHEMA",
    "REPORT_SCHEMA",
    "facts_overview",
    "run_inventory",
    "run_prune_spans",
    "run_retire_derived",
    "run_vacuum",
    "source_facts",
]
