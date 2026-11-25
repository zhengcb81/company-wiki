"""Public implementation identities for the pure geometry-planning component."""


def geometry_algorithm_sources() -> dict[str, str | None]:
    from . import contracts, planner, reading

    return {module.__name__: module.__file__ for module in (reading, planner, contracts)}


__all__ = ["geometry_algorithm_sources"]
