"""Source-local decision dependencies: the identity of a selection decision.

The engine that chooses narrative material caches its expensive work per generation.
Hashing only the payload it finally sent is not enough to justify that cache: a
component that *participated* in the decision but lost -- an unmatched matcher in the
same family, a candidate that was ranked and dropped -- can win on the next run after
its priority or matching signals change. Reusing then would silently serve a selection
the current policy would no longer make.

This package therefore freezes the *decision* rather than its outcome:

* the source-local decision scope (parent and child scopes of this one source),
* every component the caller actually inspected, including the losers,
* the full candidate membership (added/moved/removed, eligible or not),
* the algorithm versions actually in force,

and compares two such freezes causally, so array order is not a difference and a
changed participant is.

Boundaries this package deliberately keeps:

* It does **not** discover candidates. The caller supplies the scope, the components it
  inspected and the inventory it saw; nothing here routes, ranks, selects, or reads a
  catalog, a file, the clock or the network.
* It does **not** certify the caller's inventory. ``inventory_complete`` is the caller's
  claim. What this package *can* catch are the degenerate shapes of a winners-only
  trace -- no candidate membership at all, and inspected components that no candidate
  ever references -- which are refused as ``complete``. What it cannot catch is a
  fully-shaped forged inventory that omits participants and still asserts
  ``inventory_complete: true``: the trace is the only evidence, and there is no catalog
  read to cross-check it against. That external omission is the caller's responsibility
  and is documented as such in the handoff.
* ``same`` is not a cache hit. ROOT still performs the original-text/locator read check
  and owns the Store/CAS decision; this component only says whether the decision
  identity changed.
"""

from __future__ import annotations

from .compare import compare_decision_dependencies
from .freeze import freeze_decision_dependencies

__all__ = [
    "compare_decision_dependencies",
    "freeze_decision_dependencies",
]
