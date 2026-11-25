"""Public fingerprint of the geometry policy compiler."""

from company_wiki.implementation_identity import code_sha256


def geometry_policy_hashes() -> dict[str, str]:
    from . import geometry_policy

    return {geometry_policy.__name__: code_sha256(geometry_policy.__file__)}


__all__ = ["geometry_policy_hashes"]
