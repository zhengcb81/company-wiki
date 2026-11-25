"""Stable error vocabulary shared by AUTO persistence owners."""


class AutomationStoreError(Exception):
    code = "automation_store_error"

    def __init__(self, detail: str = "") -> None:
        super().__init__(detail or self.code)
        self.detail = detail


class InvalidStorePathError(AutomationStoreError):
    code = "invalid_store_path"


class StoreBusyError(AutomationStoreError):
    code = "store_busy"


class IntegrityViolationError(AutomationStoreError):
    code = "integrity_violation"


class TerminalResultCompactedError(IntegrityViolationError):
    """The original result was retired; read the exact final artifact instead."""

    code = "terminal_result_compacted"


class IdempotencyConflictError(AutomationStoreError):
    code = "idempotency_conflict"


class RecordNotFoundError(AutomationStoreError):
    code = "record_not_found"


class ConcurrentUpdateError(AutomationStoreError):
    code = "concurrent_update"


class CorruptRecordError(AutomationStoreError):
    code = "corrupt_record"


class RuntimeGateClosedError(AutomationStoreError):
    code = "runtime_gate_closed"


class RuntimeGenerationError(AutomationStoreError):
    code = "runtime_generation_mismatch"


class LeaseLostError(AutomationStoreError):
    code = "lease_lost"
