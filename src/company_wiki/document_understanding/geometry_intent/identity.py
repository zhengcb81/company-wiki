"""Public fingerprints of the geometry-planning components."""

from company_wiki.implementation_identity import code_sha256


def geometry_algorithm_hashes() -> dict[str, str]:
    from . import contracts, planner, reading

    return {
        module.__name__: code_sha256(module.__file__)
        for module in (reading, planner, contracts)
    }


__all__ = ["geometry_algorithm_hashes"]
