"""Partition CI execution by test module without narrowing the canonical inventory."""

from __future__ import annotations

from argparse import ArgumentTypeError
from hashlib import sha256

import pytest


def parse_shard(value: str) -> tuple[int, int]:
    try:
        index, count = map(int, value.split("/"))
        if 0 <= index < count:
            return index, count
    except ValueError:
        pass
    raise ArgumentTypeError("expected zero-based SHARD/COUNT")


def pytest_addoption(parser) -> None:
    parser.addoption("--cwp-ci-shard", metavar="SHARD/COUNT", type=parse_shard)


@pytest.hookimpl(trylast=True)
def pytest_collection_modifyitems(config, items) -> None:
    shard = config.getoption("--cwp-ci-shard")
    if shard is None:
        return
    if config.getoption("collectonly"):
        raise pytest.UsageError("The canonical CWP inventory must not be sharded.")
    index, count = shard
    selected, deselected = [], []
    for item in items:
        module = item.nodeid.split("::", 1)[0]
        digest = sha256(module.encode("utf-8")).digest()
        bucket = int.from_bytes(digest[:8], "big") % count
        (selected if bucket == index else deselected).append(item)
    config.hook.pytest_deselected(items=deselected)
    items[:] = selected
