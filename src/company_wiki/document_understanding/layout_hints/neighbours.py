"""Indexed conservative vertical clearance: two sweeps, O(n log n).

Any positive horizontal overlap counts as nearby context. This is conservative:
smaller clearances may lower a heading confidence, never create extra whitespace.
Coordinates are the caller's own boxes; no geometry or source identity is made.
"""

from __future__ import annotations
from bisect import bisect_left
from math import inf


class _RangeNearest:
    def __init__(self, size, *, above, budget):
        self.size = size
        self.above = above
        self.budget = budget
        self.identity = -inf if above else inf
        self.values = [self.identity] * (max(1, size) * 4)
        self.lazy = [None] * (max(1, size) * 4)

    def _push(self, node):
        value = self.lazy[node]
        if value is not None:
            for child in (node * 2, node * 2 + 1):
                self.values[child] = value
                self.lazy[child] = value
            self.lazy[node] = None

    def assign(self, left, right, value):
        if left < right:
            self._assign(1, 0, self.size, left, right, value)

    def _assign(self, node, start, end, left, right, value):
        self.budget.charge()
        if left <= start and end <= right:
            self.values[node] = value
            self.lazy[node] = value
            return
        self._push(node)
        middle = (start + end) // 2
        if left < middle:
            self._assign(node * 2, start, middle, left, right, value)
        if right > middle:
            self._assign(node * 2 + 1, middle, end, left, right, value)
        combine = max if self.above else min
        self.values[node] = combine(self.values[node * 2], self.values[node * 2 + 1])

    def query(self, left, right):
        return (
            self._query(1, 0, self.size, left, right) if left < right else self.identity
        )

    def _query(self, node, start, end, left, right):
        self.budget.charge()
        if left <= start and end <= right:
            return self.values[node]
        self._push(node)
        middle = (start + end) // 2
        values = []
        if left < middle:
            values.append(self._query(node * 2, start, middle, left, right))
        if right > middle:
            values.append(self._query(node * 2 + 1, middle, end, left, right))
        return (max if self.above else min)(values)


def vertical_clearances(units, budget):
    boxes = {}
    for unit in units:
        budget.charge()
        box = unit.bbox
        if box is not None and box[0] < box[2] and box[1] < box[3]:
            boxes[unit.unit_id] = box
    if not boxes:
        return {}
    edges = sorted({edge for box in boxes.values() for edge in (box[0], box[2])})
    intervals = {
        uid: (bisect_left(edges, box[0]), bisect_left(edges, box[2]))
        for uid, box in boxes.items()
    }
    result = {uid: [inf, inf] for uid in boxes}
    for above in (True, False):
        tree = _RangeNearest(len(edges) - 1, above=above, budget=budget)
        candidate_edge = 3 if above else 1
        query_edge = 1 if above else 3
        candidates = sorted(
            boxes, key=lambda uid: (boxes[uid][candidate_edge], uid), reverse=not above
        )
        queries = sorted(
            boxes, key=lambda uid: (boxes[uid][query_edge], uid), reverse=not above
        )
        cursor = 0
        for uid in queries:
            budget.charge()
            boundary = boxes[uid][query_edge]
            while cursor < len(candidates):
                other = candidates[cursor]
                edge = boxes[other][candidate_edge]
                if edge > boundary if above else edge < boundary:
                    break
                tree.assign(*intervals[other], edge)
                cursor += 1
            nearest = tree.query(*intervals[uid])
            result[uid][0 if above else 1] = (
                boundary - nearest if above else nearest - boundary
            )
    return result
