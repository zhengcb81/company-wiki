"""Capture a local source-reader process with limits enforced while reading."""

from __future__ import annotations

from dataclasses import dataclass, field
from io import BufferedReader
import math
import os
import subprocess
from threading import Event, Thread
import time
from typing import BinaryIO, Sequence, cast

from company_wiki_narrative_contracts import NarrativeTransportError, REQUEST_LIMIT
from company_wiki_narrative_tree import ProcessTree
from company_wiki_narrative_posix import transfer_posix


@dataclass(frozen=True)
class ReaderOutput:
    returncode: int
    stdout: bytes
    stderr: bytes


@dataclass
class _Capture:
    stream: BufferedReader
    limit: int
    overflow: Event
    data: bytearray = field(default_factory=bytearray)
    error: bool = False

    def collect(self) -> None:
        try:
            while True:
                chunk = self.stream.read1(min(4096, self.limit - len(self.data) + 1))
                if not chunk:
                    return
                if len(self.data) + len(chunk) > self.limit:
                    self.overflow.set()
                    return
                self.data.extend(chunk)
        except (OSError, ValueError):
            self.error = True


def _write_input(stream: BinaryIO, data: bytes) -> None:
    try:
        stream.write(data)
        stream.flush()
    except (BrokenPipeError, OSError, ValueError):
        pass
    finally:
        try:
            stream.close()
        except (BrokenPipeError, OSError, ValueError):
            pass


def _options(command: Sequence[str], data: bytes, timeout: float, limits: tuple[int, int]) -> None:
    _command_option(command)
    if not isinstance(data, bytes) or len(data) > REQUEST_LIMIT:
        raise NarrativeTransportError("blocked", "request_size_limit")
    _timeout_option(timeout)
    if any(type(limit) is not int or limit < 1 for limit in limits):
        raise NarrativeTransportError("blocked", "invalid_reader_limit")


def _command_option(command: Sequence[str]) -> None:
    if not command or not all(isinstance(arg, str) and arg for arg in command):
        raise NarrativeTransportError("blocked", "invalid_reader_command")


def _timeout_option(timeout: float) -> None:
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)):
        raise NarrativeTransportError("blocked", "invalid_reader_timeout")
    if not math.isfinite(timeout) or timeout <= 0:
        raise NarrativeTransportError("blocked", "invalid_reader_timeout")


def _wait(process: subprocess.Popen[bytes], overflow: Event, threads: list[Thread],
          deadline: float) -> str | None:
    # Parent exit is not EOF: a wrapper's descendants may still own both pipes.
    while True:
        if overflow.is_set():
            return "reader_output_limit"
        if process.poll() is not None and not any(thread.is_alive() for thread in threads):
            return None
        if time.monotonic() >= deadline:
            return "reader_timeout"
        time.sleep(0.01)


def _join_threads(threads: list[Thread], deadline: float) -> bool:
    for thread in threads:
        if thread.ident is not None:
            thread.join(timeout=max(0, deadline - time.monotonic()))
    return not any(thread.is_alive() for thread in threads)


def _close_streams(process: subprocess.Popen[bytes], threads: list[Thread]) -> None:
    pipes = (process.stdout, process.stderr, process.stdin)
    if not threads:
        for pipe in pipes:
            if pipe is not None:
                pipe.close()
        return
    for pipe, thread in zip(pipes, threads):
        if not thread.is_alive() and pipe is not None:
            pipe.close()  # Never close a buffered pipe held by a live reader.


def _cleanup(tree: ProcessTree, process: subprocess.Popen[bytes] | None,
             threads: list[Thread]) -> bool:
    # One bounded budget for reaping and all drains, not N seconds per pipe.
    try:
        tree.terminate()
    except OSError:
        pass  # Windows kill-on-close remains the independent fallback.
    tree.close()
    if process is None:
        return True
    deadline = time.monotonic() + 1.0
    if process.poll() is None:
        process.kill()  # Handles startup failure before assignment to the job.
    try:
        process.wait(timeout=max(0, deadline - time.monotonic()))
    except subprocess.TimeoutExpired:
        return False
    joined = _join_threads(threads, deadline)
    _close_streams(process, threads)
    return joined


def _start(command: Sequence[str], tree: ProcessTree) -> subprocess.Popen[bytes]:
    environment = dict(os.environ)
    environment.update(PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1", PYTHON_DOTENV_DISABLED="1")
    try:
        process = subprocess.Popen(
            list(command), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env=environment, shell=False, creationflags=tree.creationflags,
            start_new_session=tree.start_new_session,
        )
        return process
    except OSError as exc:
        raise NarrativeTransportError("unavailable", "reader_unavailable") from exc


def _capture_result(process: subprocess.Popen[bytes], captures: list[_Capture], overflow: Event,
                    reason: str | None, clean: bool) -> ReaderOutput:
    if not clean:
        raise NarrativeTransportError("unavailable", "reader_cleanup_failed")
    if reason or overflow.is_set():
        raise NarrativeTransportError("unavailable", reason or "reader_output_limit")
    if any(capture.error for capture in captures):
        raise NarrativeTransportError("unavailable", "reader_pipe_failed")
    return ReaderOutput(process.returncode, bytes(captures[0].data), bytes(captures[1].data))


def _captures(process: subprocess.Popen[bytes], limits: tuple[int, int],
              overflow: Event) -> list[_Capture]:
    return [_Capture(cast(BufferedReader, process.stdout), limits[0], overflow),
            _Capture(cast(BufferedReader, process.stderr), limits[1], overflow)]


def _channels(process: subprocess.Popen[bytes], limits: tuple[int, int], data: bytes,
              overflow: Event) -> tuple[list[_Capture], list[Thread]]:
    captures = _captures(process, limits, overflow)
    threads = [Thread(target=capture.collect, name=f"rf-narrative-{process.pid}-pipe-{index}")
               for index, capture in enumerate(captures)]
    threads.append(Thread(target=_write_input, args=(process.stdin, data),
                          name=f"rf-narrative-{process.pid}-input"))
    return captures, threads


def _start_threads(threads: list[Thread]) -> None:
    try:
        for thread in threads:
            thread.start()
    except RuntimeError as exc:
        raise NarrativeTransportError("unavailable", "reader_unavailable") from exc


def _run_posix(process: subprocess.Popen[bytes], captures: list[_Capture], data: bytes,
               limits: tuple[int, int], deadline: float) -> None:
    streams = (cast(BinaryIO, process.stdin), cast(BinaryIO, process.stdout), cast(BinaryIO, process.stderr))
    transfer_posix(streams, data, [capture.data for capture in captures], limits, deadline)


def run_bounded(
    command: Sequence[str], data: bytes, *, stdout_limit: int,
    stderr_limit: int, timeout_seconds: float = 30,
) -> ReaderOutput:
    """Cap bytes and contain the tree through wait, drain and shared cleanup."""
    _options(command, data, timeout_seconds, (stdout_limit, stderr_limit))
    deadline = time.monotonic() + timeout_seconds
    try:
        tree = ProcessTree()
    except OSError as exc:
        raise NarrativeTransportError("unavailable", "reader_unavailable") from exc
    process = None
    threads: list[Thread] = []
    overflow = Event()
    reason = None
    try:
        process = _start(command, tree)
        try:
            tree.attach(process)
        except OSError as exc:
            raise NarrativeTransportError("unavailable", "reader_unavailable") from exc
        limits = (stdout_limit, stderr_limit)
        if tree.start_new_session:
            captures = _captures(process, limits, overflow)
            _run_posix(process, captures, data, limits, deadline)
        else:
            captures, threads = _channels(process, limits, data, overflow)
            _start_threads(threads)
        reason = _wait(process, overflow, threads, deadline)
    finally:
        clean = _cleanup(tree, process, threads)
    return _capture_result(process, captures, overflow, reason, clean)
