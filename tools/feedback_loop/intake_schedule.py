"""Coalesce inbox wakeups while keeping observations in their original stores."""

from contextlib import ExitStack, contextmanager
import json
import logging

from company_wiki.diagnostic_logging import log_exception
import os
from pathlib import Path
from tempfile import NamedTemporaryFile
import time
from typing import Callable
from uuid import uuid4

from company_wiki.file_mutex import FileMutexLockedError, os_file_mutex, win32_filesystem_path

from .host import read_hosts


_logger = logging.getLogger(__name__)
_STARTUP_SECONDS = 30
WAKE_ERRORS = (OSError, FileMutexLockedError, ValueError, TypeError, KeyError, RecursionError)


class IntakeSchedule:
    def __init__(self, settings: Path, *, database: Path | None = None):
        self.settings = settings.resolve()
        if database is None:
            database = self.settings.parent / read_hosts(win32_filesystem_path(self.settings))["state"]
        self.database = database.resolve()
        self.directory = win32_filesystem_path(self.database.with_name(self.database.name + ".intake"))
        self.directory.mkdir(parents=True, exist_ok=True)
        self.state_path = self.directory / "wakes.json"
        self.control_path = self.directory / "wakes.lock"
        self.scan_path = self.directory / "scan.lock"

    def scope(self, hosts: Path, owner: str | list[str] | None, wait_seconds: int) -> str:
        names = [owner] if isinstance(owner, str) else (owner or [])
        return json.dumps([str(self.settings), str(hosts.resolve()), sorted(set(names)), wait_seconds], ensure_ascii=True)

    @contextmanager
    def scan(self):
        """Use the same OS lock for the scheduler and every background intake."""
        with ExitStack() as held:
            try:
                held.enter_context(os_file_mutex(self.scan_path, timeout_seconds=0.01))
            except FileMutexLockedError:
                yield False
            else:
                yield True

    def _read(self) -> dict:
        try:
            state = json.loads(self.state_path.read_bytes())
            if (isinstance(state, dict) and isinstance(state.get("pending"), dict)
                    and type(state.get("starting_until")) in (int, float)):
                for scope, ticket in tuple(state["pending"].items()):
                    if isinstance(ticket, str):
                        state["pending"][scope] = {"generation": ticket, "save_result": False}
                    elif (not isinstance(ticket, dict) or not isinstance(ticket.get("generation"), str)
                          or type(ticket.get("save_result")) is not bool):
                        del state["pending"][scope]
                        _logger.warning("Skipping one unreadable wake hint; the original inbox stays available")
                return state
            raise ValueError("invalid intake wake state")
        except FileNotFoundError:
            pass
        except ValueError as exc:
            log_exception(_logger, logging.WARNING,
                          "Unreadable wake hints; the saved observation inboxes remain available", exc)
        return {"pending": {}, "starting_until": 0}

    def _write(self, state: dict) -> None:
        temporary = None
        try:
            with NamedTemporaryFile(dir=self.directory, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(json.dumps(state, ensure_ascii=True).encode("ascii"))
                stream.flush()
                os.fsync(stream.fileno())
            temporary.replace(self.state_path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    def request(self, scope: str, launch: Callable[[], None], *, save_result: bool = False) -> None:
        with os_file_mutex(self.control_path):
            state = self._read()
            prior = state["pending"].get(scope, {})
            state["pending"][scope] = {"generation": uuid4().hex, "save_result": save_result or prior.get("save_result", False)}
            self._write(state)
            self._launch_if_needed(state, launch)

    def _launch_if_needed(self, state: dict, launch: Callable[[], None], skip=()) -> None:
        if state["starting_until"] > time.time() or not any(
            (scope, ticket["generation"]) not in skip for scope, ticket in state["pending"].items()
        ):
            return
        with self.scan() as available:
            if not available:
                return
            # The hint bridges interpreter startup. The scan lock itself has
            # no expiry and is released by the OS if its owning process dies.
            state["starting_until"] = time.time() + _STARTUP_SECONDS
            self._write(state)
        try:
            launch()
        except OSError:
            state["starting_until"] = 0
            self._write(state)
            raise

    def continue_pending(self, launch: Callable[[], None], *, skip=()) -> None:
        with os_file_mutex(self.control_path):
            self._launch_if_needed(self._read(), launch, skip)

    def pending(self, *, started: bool = False) -> dict[str, dict]:
        with os_file_mutex(self.control_path):
            state = self._read()
            if started and state["starting_until"]:
                state["starting_until"] = 0
                self._write(state)
            return state["pending"]

    def acknowledge(self, scope: str, generation: str | None) -> None:
        if generation is None:
            return
        with os_file_mutex(self.control_path):
            state = self._read()
            if state["pending"].get(scope, {}).get("generation") == generation:
                del state["pending"][scope]
                self._write(state)
