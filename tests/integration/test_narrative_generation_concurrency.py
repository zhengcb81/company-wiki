"""Actual concurrent configured launchers serialize one stable generation."""

from concurrent.futures import ThreadPoolExecutor
import time
import pytest
from integration.test_narrative_generation_reuse import (
    setup_source,
    request_path,
    invoke,
    public_read,
    record_proof,
    official,
)
from integration.test_narrative_batch_recovery_e2e import (
    interrupted_model_server as _interrupted_fixture,
)


interrupted_model_server = _interrupted_fixture


@pytest.mark.parametrize("distinct_database", [False, True])
def test_concurrent_generation_waits_or_retries_then_reuses_one_post(
    interrupted_model_server, monkeypatch, distinct_database
):
    server = interrupted_model_server
    monkeypatch.setenv("DEEPSEEK_API_KEY", official.batch_fixtures.KEY)
    with setup_source(server.endpoint) as (root, catalog, config, llm, imported, kind):
        first_path = request_path(root, imported, server.endpoint, "concurrent-a")
        next_path = request_path(root, imported, server.endpoint, "concurrent-b")
        with ThreadPoolExecutor(max_workers=2) as pool:
            first_future = pool.submit(
                invoke, root, config, first_path, llm, "concurrent-a"
            )
            try:
                assert server.first_received.wait(timeout=25), (
                    "configured first launcher never reached POST"
                )
                next_future = pool.submit(
                    invoke,
                    root,
                    config,
                    next_path,
                    llm,
                    "concurrent-b",
                    database=root / "other.sqlite"
                    if distinct_database
                    else root / "AUTO.sqlite",
                )
                if distinct_database:
                    time.sleep(0.8)
                    assert not next_future.done() and len(server.requests) == 1
                else:
                    process, busy = next_future.result(timeout=10)
                    assert (
                        process.returncode == 1
                        and busy["error"] == "NARRATIVE_BATCH_FileMutexLockedError"
                    ), busy
                    assert len(server.requests) == 1
            finally:
                server.release_first.set()
            process, first = first_future.result(timeout=45)
            assert process.returncode == 0 and first["status"] == "completed", first
            if distinct_database:
                process, reused = next_future.result(timeout=45)
            else:
                process, reused = invoke(root, config, next_path, llm, "concurrent-b")
            assert process.returncode == 0 and reused["status"] == "completed", reused
            assert len(server.requests) == 1 and not server.errors
            assert (
                reused["documents"][0]["artifact_ref"]
                == first["documents"][0]["artifact_ref"]
            )
            assert (
                reused["budget"]["tokens"]
                == reused["budget"]["estimated_micro_usd"]
                == 0
            )
            _, _, receipt = public_read(root, config, imported, kind)
            record_proof(
                "concurrent-" + ("different-db" if distinct_database else "same-db"),
                server,
                reused,
                receipt,
            )
