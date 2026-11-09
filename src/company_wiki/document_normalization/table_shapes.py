"""Compatibility exports for the former table shapes module."""

from company_wiki.document_model.table_shapes import (
    has_tabular_value_tail as has_tabular_value_tail,
    has_unbound_numeric_cells as has_unbound_numeric_cells,
    observe_value_cells as observe_value_cells,
)

__all__ = [
    "has_tabular_value_tail",
    "has_unbound_numeric_cells",
    "observe_value_cells",
]
