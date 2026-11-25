"""Public implementation identity of the geometry policy compiler."""


def geometry_policy_sources() -> dict[str, str | None]:
    from . import geometry_policy

    return {geometry_policy.__name__: geometry_policy.__file__}


__all__ = ["geometry_policy_sources"]
