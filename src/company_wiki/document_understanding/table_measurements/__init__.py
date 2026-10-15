"""DU4-TABLE: value -> native column -> header path -> period binding.

Pure in-memory component over ``du4-table-observation/1``; see the package
module :mod:`.bindings` for the contract.  Public entry point:
:func:`bind_operating_table`.
"""

from __future__ import annotations

from .bindings import bind_operating_table

__all__ = ["bind_operating_table"]
