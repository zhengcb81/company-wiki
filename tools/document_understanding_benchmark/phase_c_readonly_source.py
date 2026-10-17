"""Test-side registration of an explicit original in an isolated catalog.

The source owner resolves configured roots, registers one group and verifies the
public reference. No original, sidecar, metadata or production database is written.
"""

from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import yaml


class ReadonlySourceGap(ValueError):
    """The existing public source contract cannot supply this test subject."""

    def __init__(self, reason: str, *, detail: dict | None = None):
        self.reason = reason
        self.detail = detail or {}
        super().__init__(reason)


def prepare_registered_source(
    *,
    source_config: Path,
    owned_root: Path,
    original: Path,
    expected_sha256: str,
    descriptor: dict,
    as_of_date: str,
) -> dict:
    from company_wiki.source_catalog.config import load_catalog_config
    from company_wiki.source_catalog.resolver import SourceRequest
    from company_wiki.source_catalog.service import SourceCatalog
    from company_wiki.source_catalog.source_location import (
        inside_configured_roots,
        resolve_source_location,
        SourceLocationError,
    )
    from company_wiki.source_catalog.source_reader import (
        SourceVersionReader,
        SourceReadError,
    )

    source_config, owned_root = (
        Path(source_config).resolve(),
        Path(owned_root).resolve(),
    )
    original = Path(original).absolute()
    source = load_catalog_config(source_config)
    # Map only this explicit input through the source owner's configured roots.
    # Root paths/policies are never inferred from company names or providers.
    locations = []
    for spec in source.roots:
        try:
            relative = original.relative_to(spec.path).as_posix()
            resolved = resolve_source_location(spec, relative)
        except (ValueError, SourceLocationError):
            continue
        if resolved == original.resolve():
            locations.append((spec, relative))
    if not locations:
        raise ReadonlySourceGap("registered_source_outside_configured_roots")
    if len(locations) != 1:
        raise ReadonlySourceGap("registered_source_root_ambiguous")
    spec, relative = locations[0]
    if hashlib.sha256(original.read_bytes()).hexdigest() != expected_sha256:
        raise ReadonlySourceGap("registered_source_sha_mismatch")
    catalog_dir = owned_root / "catalog"
    if catalog_dir.resolve() == source.catalog_dir.resolve() or inside_configured_roots(
        catalog_dir, source.roots
    ):
        raise ReadonlySourceGap("registered_source_catalog_not_isolated")
    target = owned_root / "config/source_catalog.yaml"
    if target == source_config:
        raise ReadonlySourceGap("registered_source_configuration_not_isolated")
    # Keep every current declared root/adapter/route rule; only expand paths and
    # move the catalog. The owner's normal config loader remains authoritative.
    value = yaml.safe_load(source_config.read_text(encoding="utf-8"))
    paths = {root.root_id: str(root.path) for root in source.roots}
    for row in value["roots"]:
        row["path"] = paths[row["root_id"]]
    value["catalog_dir"] = str(catalog_dir)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    configured = load_catalog_config(target, project_root=owned_root)
    catalog = SourceCatalog(configured)
    try:
        registration = catalog.register_sources(
            root_id=spec.root_id, relative_paths={relative}
        )
        if registration.errors:
            raise ReadonlySourceGap(
                "registered_source_registration_failed",
                detail={"errors": registration.errors},
            )
        request = SourceRequest(
            entity=descriptor["entity"],
            document_kind=descriptor["document_kind"],
            as_of_date=as_of_date,
            market=descriptor.get("market"),
            security_id=descriptor.get("security_id"),
            fiscal_year=descriptor.get("fiscal_year"),
            fiscal_period=descriptor.get("fiscal_period"),
            form_type=descriptor.get("form_type"),
            mode="exact",
            allow_download=False,
        )
        reader = SourceVersionReader(catalog)
        query = reader.query_local(request)
        if query.status != "found" or len(query.matches) != 1:
            raise ReadonlySourceGap(
                "registered_source_" + query.status,
                detail={
                    "reason": query.reason,
                    "excluded_candidates": list(query.excluded_candidates),
                },
            )
        ref = query.matches[0]
        if ref.content_sha256 != expected_sha256:
            raise ReadonlySourceGap("registered_source_sha_mismatch")
        opened = reader.open_version(ref, purpose="narrative_derivation")
        manifest = reader.describe_version(ref)
        for field in (
            "market",
            "security_id",
            "document_kind",
            "fiscal_year",
            "fiscal_period",
            "published_date",
            "source_url",
            "language",
        ):
            expected = descriptor.get(field)
            if expected is not None and (
                type(manifest.get(field)) is not type(expected)
                or manifest.get(field) != expected
            ):
                raise ReadonlySourceGap(
                    "registered_source_metadata_gap", detail={"field": field}
                )
        if opened.content_sha256 != expected_sha256:
            raise ReadonlySourceGap("registered_source_sha_mismatch")
        return {
            "source_ref": asdict(ref),
            "manifest": manifest,
            "catalog_config": str(target),
            "raw_copies": 0,
            "verified_sha256": opened.content_sha256,
            "registration": {
                "root_id": spec.root_id,
                "relative_paths": [relative],
                "files_seen": registration.files_seen,
            },
            "download_events": 0,
        }
    except SourceReadError as error:
        raise ReadonlySourceGap("registered_source_" + error.reason) from error
    finally:
        catalog.close()
