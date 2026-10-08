"""Read field quality without turning auxiliary metadata into a byte permission."""

from dataclasses import dataclass
from typing import Any

from .store import metadata_state

_COLUMN_DECLARATIONS = {
    'title': ('source_title',), 'published_date': ('filing_date', 'published_date'),
    'document_kind': ('document_kind',), 'source_type': ('source_type',),
}


@dataclass(frozen=True)
class MetadataObservation:
    metadata: dict[str, Any]
    conflicted_fields: tuple[str, ...]
    problems: tuple[str, ...]
    disputed_declarations: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        # Values, source text and physical locations do not belong in diagnostics.
        return {'conflicted_fields': list(self.conflicted_fields), 'problems': list(self.problems)}

    def reason(self) -> str:
        descriptions = {
            'metadata_unreadable': 'shared metadata column is not readable JSON',
            'metadata_not_object': 'shared metadata column is not a JSON object',
            'provenance_not_object': 'reserved provenance key is not an object',
            'provenance_fields_not_object': 'reserved provenance fields are not an object',
        }
        if self.problems:
            return '; '.join(descriptions[problem] for problem in self.problems)
        if self.conflicted_fields:
            return 'field conflict recorded for: ' + ', '.join(self.conflicted_fields)
        return ''

    def project_document(self, document: dict[str, Any]) -> dict[str, Any]:
        result = {**document, 'metadata': self.metadata}
        for column in _COLUMN_DECLARATIONS:
            if column in self.disputed_declarations:
                result[column] = None
        return result


def observe_metadata(value: object) -> MetadataObservation:
    """Project disputed declarations as unknown; never edit persisted observations."""
    if isinstance(value, dict):
        shared, problem = value, None
    else:
        shared, problem = metadata_state(value)
    if problem:
        return MetadataObservation({}, (), ('metadata_' + problem,))
    provenance = shared.get('r4_provenance')
    fields = provenance.get('fields', {}) if isinstance(provenance, dict) else {}
    problems: tuple[str, ...] = ()
    if fields is None:
        fields = {}
    if provenance is not None and not isinstance(provenance, dict):
        problems = ('provenance_not_object',)
    elif not isinstance(fields, dict):
        problems = ('provenance_fields_not_object',)
        fields = {}
    conflicts = tuple(sorted(str(key) for key, record in fields.items()
                             if isinstance(record, dict) and record.get('conflicts')))
    # A byte-identical copy named "different-name.txt" can have a different
    # inferred kind. It does not contradict an issuer's declared period/type.
    # Legacy provenance without declaration flags stays explicitly disputed.
    disputed = tuple(key for key in conflicts if not (
        key in {'title', 'document_kind', 'source_type'}
        and
        isinstance(fields[key].get('sources'), list) and fields[key]['sources']
        and all(isinstance(source, dict) and source.get('declared') is False
                for source in fields[key]['sources'])
    ))
    projected = dict(shared)
    for container in ('acquisition', 'dayu_meta'):
        capture = shared.get(container)
        if not isinstance(capture, dict):
            continue
        capture = dict(capture)
        disputed_capture = set()
        for path in disputed:
            if path.startswith(container + '.'):
                disputed_capture.add(path.split('.', 1)[1])
            elif path.startswith('capture.'):
                disputed_capture.add(path.split('.', 1)[1])
            elif '.' not in path:
                disputed_capture.update(_COLUMN_DECLARATIONS.get(path, (path,)))
        for field in disputed_capture:
            capture[field] = None
        # This private observation prevents selection from mistaking disagreement
        # for an absent optional identity declaration or a filename-derived year.
        if disputed_capture:
            capture['_conflicted_fields'] = tuple(sorted(disputed_capture))
        projected[container] = capture
    return MetadataObservation(projected, conflicts, problems, disputed)
