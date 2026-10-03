"""Record a local operation's actor; this label is not an approval credential."""

import getpass


def operation_actor(label: str | None = None) -> str:
    if label is not None:
        if not isinstance(label, str):
            raise TypeError("operation actor label must be text")
        if label.strip():
            return label.strip()
    try:
        return getpass.getuser() or "local-process"
    except (ImportError, KeyError, OSError):
        return "local-process"
