"""The retired whole-catalog worker and startup writers are not public CLI paths."""

from __future__ import annotations

import pytest

from company_wiki.source_catalog.cli import _parser


@pytest.mark.parametrize(
    "command",
    [
        "normalize",
        "summarize",
        "run",
        "worker",
        "worker-start",
        "worker-resume",
        "worker-pause",
        "install-startup",
    ],
)
def test_retired_background_and_full_catalog_commands_are_not_registered(command):
    with pytest.raises(SystemExit) as raised:
        _parser().parse_args([command])

    assert raised.value.code == 2


@pytest.mark.parametrize(
    "command",
    ["scan", "status", "query", "export", "worker-status", "worker-stop", "uninstall-startup"],
)
def test_source_maintenance_and_worker_cleanup_commands_remain(command):
    args = _parser().parse_args([command])

    assert args.command == command
