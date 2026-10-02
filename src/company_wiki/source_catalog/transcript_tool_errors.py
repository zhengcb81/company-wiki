"""Shared errors for transcript provider boundary contracts."""


class TranscriptToolContractError(ValueError):
    """The provider tool result does not satisfy its frozen contract."""
