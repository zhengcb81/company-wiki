"""Nonblocking POSIX pipe ownership; no background reader threads."""
from __future__ import annotations

import os
import selectors
import sys
import time
from typing import BinaryIO

from company_wiki_narrative_contracts import NarrativeTransportError


def _register(selector: selectors.BaseSelector, streams: tuple[BinaryIO, BinaryIO, BinaryIO],
              data: bytes, limits: tuple[int, int]) -> None:
    if sys.platform != "win32":
        for pipe in streams:
            os.set_blocking(pipe.fileno(), False)
    else:
        raise NarrativeTransportError("unavailable", "invalid_reader_platform")
    if data:
        selector.register(streams[0], selectors.EVENT_WRITE, (-1, 0))
    else:
        streams[0].close()
    for index, (pipe, limit) in enumerate(zip(streams[1:], limits)):
        selector.register(pipe, selectors.EVENT_READ, (index, limit))


def _write(selector: selectors.BaseSelector, key: selectors.SelectorKey, data: bytes,
           cursor: int, stdin: BinaryIO) -> int:
    try:
        cursor += os.write(key.fd, data[cursor:])
    except BlockingIOError:
        return cursor
    except BrokenPipeError:
        cursor = len(data)
    if cursor == len(data):
        selector.unregister(key.fileobj)
        stdin.close()
    return cursor


def _read(selector: selectors.BaseSelector, key: selectors.SelectorKey,
          buffers: list[bytearray], index: int, limit: int) -> None:
    try:
        chunk = os.read(key.fd, min(4096, limit - len(buffers[index]) + 1))
    except BlockingIOError:
        return
    if not chunk:
        selector.unregister(key.fileobj)
        return
    if len(buffers[index]) + len(chunk) > limit:
        raise NarrativeTransportError("unavailable", "reader_output_limit")
    buffers[index].extend(chunk)


def transfer_posix(streams: tuple[BinaryIO, BinaryIO, BinaryIO], data: bytes,
                   buffers: list[bytearray], limits: tuple[int, int], deadline: float) -> None:
    """Own and cancel local descriptors even if an unsupported child detaches."""
    cursor = 0
    try:
        with selectors.DefaultSelector() as selector:
            _register(selector, streams, data, limits)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise NarrativeTransportError("unavailable", "reader_timeout")
                for key, _event in selector.select(timeout=remaining):
                    index, limit = key.data
                    if index == -1:
                        cursor = _write(selector, key, data, cursor, streams[0])
                    else:
                        _read(selector, key, buffers, index, limit)
    except OSError as exc:
        raise NarrativeTransportError("unavailable", "reader_pipe_failed") from exc
