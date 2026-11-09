"""Public process-safe file mutex interface shared by application packages."""

from ._file_mutex import FileMutexLockedError, os_file_mutex

__all__ = ["FileMutexLockedError", "os_file_mutex"]
