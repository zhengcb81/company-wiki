"""Keep CLI stdout reserved for the public response, including native writers."""

from collections.abc import Iterator
from contextlib import contextmanager, redirect_stdout
import os
import sys

__all__ = ["operation_diagnostics"]


@contextmanager
def operation_diagnostics() -> Iterator[None]:
    """Reserve stdout for the final receipt, including native FD writers.

    This is the finite CLI process boundary, not a library-wide logging policy.
    In-memory callers have no descriptors and use the Python-stream path.
    Both descriptor and stream bindings are restored on success or exception.
    """
    output = sys.stdout
    diagnostics = sys.stderr
    output_fd = None
    saved_fd = None
    try:
        output.flush()
        # Native dependencies write the process stdout descriptor (1), which
        # need not equal an embedding/capture stream's private descriptor.
        output_fd = 1
        saved_fd = os.dup(output_fd)
        os.dup2(diagnostics.fileno(), output_fd)
    except (AttributeError, OSError, ValueError):
        if saved_fd is not None:
            os.close(saved_fd)
        saved_fd = None
    try:
        with redirect_stdout(diagnostics):
            yield
    finally:
        try:
            diagnostics.flush()
        finally:
            if saved_fd is not None and output_fd is not None:
                try:
                    os.dup2(saved_fd, output_fd)
                finally:
                    os.close(saved_fd)
