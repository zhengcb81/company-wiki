"""Record canonical pytest discovery and partition it for actual CI execution."""

from __future__ import annotations

from argparse import ArgumentTypeError
from hashlib import sha256
import json
from pathlib import Path


def parse_shard(value: str) -> tuple[int, int]:
    try:
        index, count = map(int, value.split("/"))
        if 0 <= index < count:
            return index, count
    except ValueError:
        pass
    raise ArgumentTypeError("expected zero-based SHARD/COUNT")


def pytest_addoption(parser) -> None:
    parser.addoption("--cwp-ci-membership", metavar="FILE")


def pytest_configure(config) -> None:
    if output := config.getoption("--cwp-ci-membership"):
        config.pluginmanager.register(_Inventory(Path(output)))


class _Inventory:
    def __init__(self, output: Path):
        self.output = output
        self.deselected: dict[str, list[str]] = {}

    def pytest_deselected(self, items) -> None:
        self.deselected.update(_markers(items))

    def pytest_collection_finish(self, session) -> None:
        self.output.write_text(json.dumps({
            "selected": _markers(session.items),
            "deselected": self.deselected,
        }, ensure_ascii=True), encoding="utf-8")


def _markers(items) -> dict[str, list[str]]:
    return {item.nodeid: sorted({mark.name for mark in item.iter_markers()}) for item in items}


def classify(inventory: dict, membership: dict, policy: dict) -> dict:
    selected, deselected = membership["selected"], membership["deselected"]
    if set(selected) != set(inventory["node_ids"]) or set(selected) & set(deselected):
        raise ValueError("canonical pytest membership contradicts the independent collector")
    deferred = policy.get("deferred", {})
    named_obligations = {}
    for node, marks in sorted(deselected.items()):
        reasons = sorted(set(marks) & deferred.keys())
        if not reasons:
            raise ValueError(f"no documented reason for excluded test {node}")
        for reason in reasons:
            obligation = named_obligations.setdefault(reason, {"reason": deferred[reason], "node_ids": []})
            obligation["node_ids"].append(node)
    suites = policy.get("suites", {})
    runs: dict[str, list[str]] = {name: [] for name in ("native", *suites)}
    for node, marks in sorted(selected.items()):
        owners = [name for name, marker in suites.items() if marker in marks]
        if len(owners) > 1:
            raise ValueError(f"multiple run environments for {node}")
        runs[owners[0] if owners else "native"].append(node)
    return {
        "schema": "cwp-ci-test-distribution/1",
        "revision": inventory["revision"],
        "platform": inventory["platform"],
        "collected": len(selected) + len(deselected),
        "applicable": len(selected),
        "deselected": len(deselected),
        "obligations": named_obligations,
        "suites": runs,
    }


def paths_for(distribution: dict, suite: str, shard: tuple[int, int], revision: str, platform: str) -> list[str]:
    if (distribution.get("schema") != "cwp-ci-test-distribution/1"
            or distribution.get("revision") != revision or distribution.get("platform") != platform):
        raise ValueError("test distribution belongs to a different schema, platform, or revision")
    index, count = shard
    paths = {node.split("::", 1)[0] for node in distribution["suites"][suite]}
    selected = []
    for path in sorted(paths):
        file = Path(path)
        if (not file.parts or file.parts[0].startswith("-") or file.is_absolute()
                or ".." in file.parts or file.suffix != ".py" or not file.is_file()):
            raise ValueError(f"invalid discovered test file {path}")
        digest = sha256(path.encode("utf-8")).digest()
        if int.from_bytes(digest[:8], "big") % count == index:
            selected.append(path)
    if not selected:
        raise ValueError(f"test shard has no discovered files for {suite} {index}/{count}")
    return selected
