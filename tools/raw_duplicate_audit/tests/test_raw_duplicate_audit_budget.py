"""RED budget tests: streaming reads must stop on byte cap and deadline."""

from __future__ import annotations

import io
import time

import pytest

from raw_duplicate_audit.core import (
    HASH_CHUNK_BYTES,
    Budget,
    BudgetExceeded,
    hash_file,
    iter_chunks,
)


def test_chunk_size_is_one_mib():
    assert HASH_CHUNK_BYTES == 1 << 20


def test_iter_chunks_streams_in_one_mib_pieces():
    payload = b"x" * (3 * (1 << 20) + 7)
    sizes = [len(chunk) for chunk in iter_chunks(io.BytesIO(payload))]

    assert sizes == [1 << 20, 1 << 20, 1 << 20, 7]


def test_hash_file_streams_and_accounts_every_byte(tmp_path):
    target = tmp_path / "blob.bin"
    payload = b"y" * (2 * (1 << 20) + 13)
    target.write_bytes(payload)

    budget = Budget(max_read_bytes=1 << 30, deadline_seconds=30.0)
    digest = hash_file(target, budget)

    import hashlib

    assert digest == hashlib.sha256(payload).hexdigest()
    assert budget.read_bytes == len(payload)


def test_read_budget_stops_before_reading_the_whole_file(tmp_path):
    target = tmp_path / "big.bin"
    target.write_bytes(b"z" * (8 << 20))

    budget = Budget(max_read_bytes=1 << 20, deadline_seconds=30.0)

    with pytest.raises(BudgetExceeded) as excinfo:
        hash_file(target, budget)

    assert excinfo.value.reason == "read_bytes"
    assert budget.read_bytes <= (1 << 20) + HASH_CHUNK_BYTES
    assert budget.read_bytes < target.stat().st_size


def test_deadline_stops_before_starting_another_file(tmp_path):
    first = tmp_path / "first.bin"
    first.write_bytes(b"a" * 1024)

    budget = Budget(max_read_bytes=1 << 30, deadline_seconds=0.0)

    with pytest.raises(BudgetExceeded) as excinfo:
        hash_file(first, budget)

    assert excinfo.value.reason == "deadline"
    assert budget.read_bytes == 0


def test_budget_reports_which_limits_were_hit():
    budget = Budget(max_read_bytes=10, deadline_seconds=0.0)
    budget.mark_hit("read_bytes")
    budget.mark_hit("deadline")

    assert budget.limits_hit() == ["read_bytes", "deadline"]


def test_elapsed_is_measured_from_construction():
    budget = Budget(max_read_bytes=1, deadline_seconds=30.0)
    time.sleep(0.01)

    assert budget.elapsed_seconds() >= 0.01
