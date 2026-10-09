"""Incremental HTTP content decoding with caller-bounded output allocations."""
from __future__ import annotations

from collections.abc import Callable, Iterator
import zlib
from typing import Protocol


class InvalidContentCoding(Exception):
    """Malformed or incomplete compressed entity; partial data is not original."""


class _Inflater(Protocol):
    @property
    def unconsumed_tail(self) -> bytes: ...

    @property
    def unused_data(self) -> bytes: ...

    @property
    def eof(self) -> bool: ...

    def decompress(self, data: bytes, max_length: int = 0) -> bytes: ...


class ContentDecoder:
    """One response, no unbounded flush or full-body buffering.

    Gzip members and CRC are checked by zlib. HTTP deflate accepts standard
    zlib framing and legacy raw DEFLATE. The two-byte prefix is bounded and
    retained across arbitrary transport chunk boundaries.
    """

    def __init__(self, coding: str):
        self.coding = coding
        self._prefix = b""
        self._decoder: _Inflater | None = None
        self._members = 0
        self._finished = False

    def feed(self, data: bytes, output_limit: Callable[[], int]) -> Iterator[bytes]:
        if self.coding == "identity":
            if data:
                yield data
            return
        pending = data
        if self.coding == "deflate" and self._decoder is None:
            self._prefix += pending
            if len(self._prefix) < 2:
                return
            pending, self._prefix = self._prefix, b""
            a, b = pending[:2]
            framed = (a & 15 == 8 and a >> 4 <= 7 and (a * 256 + b) % 31 == 0)
            self._decoder = zlib.decompressobj(zlib.MAX_WBITS if framed else -zlib.MAX_WBITS)
        drain = False
        while pending or drain:
            if self._finished:
                raise InvalidContentCoding("compressed entity has trailing bytes")
            if self._decoder is None:
                self._decoder = zlib.decompressobj(zlib.MAX_WBITS + 16)
            previous = pending
            limit = max(1, min(65536, output_limit()))
            try:
                output = self._decoder.decompress(pending, limit)
            except zlib.error as exc:
                raise InvalidContentCoding("invalid compressed entity") from exc
            pending = self._decoder.unconsumed_tail
            drain = len(output) == limit
            if self._decoder.eof:
                pending = self._decoder.unused_data
                self._members += 1
                drain = False
                if self.coding == "gzip":
                    self._decoder = None
                else:
                    self._finished = True
            if output:
                yield output
            elif pending == previous and pending and self._decoder is not None:
                raise InvalidContentCoding("compressed entity made no progress")

    def finish(self) -> None:
        if self.coding == "identity":
            return
        if self._prefix or not self._members or (self._decoder is not None and not self._decoder.eof):
            raise InvalidContentCoding("incomplete compressed entity")
