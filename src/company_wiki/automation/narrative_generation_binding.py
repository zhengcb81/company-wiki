"""Frozen generation manifests shared by the coordinator and its workers."""

from .models import canonical_json_hash


_SOURCE_FIELDS = frozenset({
    "source_ref", "source_metadata", "parser_component", "parser_components",
    "material_extractor", "subject_binding", "source_adapter", "language",
    "selection_generation", "reading_dependencies",
})


class FrozenGenerationBindingError(ValueError):
    """The stored binding does not reproduce its recorded generation."""

    def __init__(self) -> None:
        super().__init__("BATCH_FROZEN_BINDING_INVALID")


def generation_sha256(manifest):
    return canonical_json_hash(manifest)


def freeze_generation_manifests(manifests):
    """Store common settings once and preserve every source-specific binding."""
    settings, records = {}, {}
    for document, manifest in manifests.items():
        common = {key: value for key, value in manifest.items() if key not in _SOURCE_FIELDS}
        digest = canonical_json_hash(common)
        settings[digest] = common
        records[document] = {
            "settings_sha256": digest,
            "generation_sha256": generation_sha256(manifest),
            "source_inputs": {key: value for key, value in manifest.items() if key in _SOURCE_FIELDS},
        }
    return {"generation_settings": settings, "generation_manifests": records}


def thaw_generation_manifests(frozen):
    """Recover and verify the recorded manifests without loading current software."""
    settings, records = frozen["generation_settings"], frozen["generation_manifests"]
    if not isinstance(settings, dict) or not isinstance(records, dict):
        raise FrozenGenerationBindingError()
    manifests = {}
    for document, record in records.items():
        if not isinstance(record, dict) or set(record) != {
            "settings_sha256", "generation_sha256", "source_inputs",
        }:
            raise FrozenGenerationBindingError()
        common = settings[record["settings_sha256"]]
        source = record["source_inputs"]
        if (
            not isinstance(common, dict)
            or canonical_json_hash(common) != record["settings_sha256"]
            or not isinstance(source, dict)
            or not (
                {"subject_binding", "source_adapter", "language", "parser_component"} <= source.keys()
                if common.get("schema_version") == "narrative-generation/2"
                else {"source_ref", "source_metadata", "parser_component"} <= source.keys()
            )
            or not source.keys() <= _SOURCE_FIELDS
            or source.keys() & common.keys()
        ):
            raise FrozenGenerationBindingError()
        manifest = {**common, **source}
        if generation_sha256(manifest) != record["generation_sha256"]:
            raise FrozenGenerationBindingError()
        manifests[document] = manifest
    return manifests


__all__ = [
    "FrozenGenerationBindingError", "freeze_generation_manifests", "generation_sha256",
    "thaw_generation_manifests",
]
