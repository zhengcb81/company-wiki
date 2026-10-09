"""Incremental HTTP content decoding with caller-bounded output allocations."""
from __future__ import annotations

from collections.abc import Callable, Iterator
from tempfile import SpooledTemporaryFile
from typing import Protocol
import zlib


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


class _DeflateCandidate:
    """Keep only a capped provisional prefix until framing is decidable.

    No speculative bytes go to the SDK. An invalid interpretation cannot
    later become valid; its peer may then resume ordinary streaming. Temporary
    prefixes spill after 64 KiB and are closed by the owning response.
    """

    def __init__(self, framing: int):
        self.decoder: _Inflater = zlib.decompressobj(framing)
        self.prefix = SpooledTemporaryFile(max_size=65536, mode="w+b")
        self.produced = 0
        self.state = "active"

    def feed(self, data: bytes, ceiling: int, output_limit: Callable[[], int]) -> None:
        if self.state in {"invalid", "over_cap"}:
            return
        if self.state == "complete":
            if data:
                self.state = "invalid"
            return
        pending, drain = data, False
        while pending or drain:
            output_limit()  # Also observes the response's total deadline.
            limit = max(1, min(65536, ceiling - self.produced))
            previous = pending
            try:
                output = self.decoder.decompress(pending, limit)
            except zlib.error:
                self.state = "invalid"
                return
            pending = self.decoder.unconsumed_tail
            drain = len(output) == limit
            if output:
                self.prefix.write(output)
                self.produced += len(output)
            if self.produced >= ceiling:
                self.state = "over_cap"
                return
            if self.decoder.eof:
                self.state = "invalid" if self.decoder.unused_data else "complete"
                return
            if not output and pending and pending == previous:
                self.state = "invalid"
                return

    def finish(self) -> None:
        if self.state == "active":
            self.state = "invalid"

    def chunks(self, output_limit: Callable[[], int]) -> Iterator[bytes]:
        self.prefix.seek(0)
        try:
            while True:
                part = self.prefix.read(max(1, min(65536, output_limit())))
                if not part:
                    return
                yield part
        finally:
            self.close()

    def close(self) -> None:
        self.prefix.close()


class ContentDecoder:
    """One response with bounded working chunks and no unbounded flush.

    Gzip members and CRC are checked by zlib. Deflate is tried as both zlib
    framing and legacy raw DEFLATE: a valid raw stream may have a zlib-looking
    prefix. Ambiguous prefixes are capped at the current entity allowance;
    after a candidate fails, its peer streams directly. At EOF, two valid
    candidates prefer standard framing. The response owns all scratch.
    """

    def __init__(self, coding: str):
        self.coding = coding
        self._decoder: _Inflater | None = None
        self._members = 0
        self._finished = False
        self._candidates = ([_DeflateCandidate(zlib.MAX_WBITS),
                             _DeflateCandidate(-zlib.MAX_WBITS)]
                            if coding == "deflate" else None)
        self._scratch = list(self._candidates or [])
        self._ceiling: int | None = None

    def _choose(self) -> _DeflateCandidate | None:
        assert self._candidates is not None
        viable = [c for c in self._candidates if c.state in {"active", "complete"}]
        if len(viable) == 2:
            return None
        if viable:
            return viable[0]
        oversized = [c for c in self._candidates if c.state == "over_cap"]
        if oversized:
            return oversized[0]  # Delivery records cap+1 before the budget stops.
        raise InvalidContentCoding("invalid compressed entity")

    def _select(self, candidate: _DeflateCandidate,
                output_limit: Callable[[], int]) -> Iterator[bytes]:
        assert self._candidates is not None
        for other in self._candidates:
            if other is not candidate:
                other.close()
        self._candidates = None
        self._decoder = candidate.decoder
        self._finished = candidate.state == "complete"
        self._members = int(self._finished)
        return candidate.chunks(output_limit)

    def feed(self, data: bytes, output_limit: Callable[[], int]) -> Iterator[bytes]:
        if self.coding == "identity":
            if data:
                yield data
            return
        if self._candidates is not None:
            if self._ceiling is None:
                self._ceiling = max(1, output_limit())
            for candidate in self._candidates:
                candidate.feed(data, self._ceiling, output_limit)
            chosen = self._choose()
            if chosen is not None:
                yield from self._select(chosen, output_limit)
            return
        pending, drain = data, False
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

    def finish(self, output_limit: Callable[[], int] = lambda: 65536) -> Iterator[bytes]:
        if self._candidates is not None:
            for candidate in self._candidates:
                candidate.finish()
            valid = [c for c in self._candidates if c.state == "complete"]
            chosen = valid[0] if valid else self._choose()
            if chosen is None:
                raise InvalidContentCoding("incomplete compressed entity")
            return self._select(chosen, output_limit)
        if self.coding != "identity" and (
                not self._members or (self._decoder is not None and not self._decoder.eof)):
            raise InvalidContentCoding("incomplete compressed entity")
        return iter(())

    def close(self) -> None:
        for candidate in self._scratch:
            candidate.close()
