"""Finite source-reading annotations, separate from original field identity.

Writers and verified projection replay share this explicit registry. Arbitrary
reading_* keys are not annotations and remain part of original evidence.
"""
from collections.abc import Mapping
from typing import Any


READING_ANNOTATION_FIELDS = (
    'reading_priority', 'reading_value_band', 'reading_fact_purpose', 'reading_score',
)


def reading_annotations(reading: Mapping[str, Any], score: int) -> dict[str, Any]:
    values = (reading['priority'], reading.get('value_band', 'description'),
              reading.get('fact_purpose', 'unknown'), score)
    return dict(zip(READING_ANNOTATION_FIELDS, values, strict=True))
