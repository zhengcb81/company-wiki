"""Public owned-process lifecycle interface."""

from ._process_tree import (
    WindowsJob,
    assign_windows_job,
    kill_owned_group,
    pid_is_alive,
)

__all__ = [
    "WindowsJob",
    "assign_windows_job",
    "kill_owned_group",
    "pid_is_alive",
]
