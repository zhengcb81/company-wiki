"""Owned synthetic execution boundary; no production permissions or gates."""
from __future__ import annotations

import contextlib
import os
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Iterator

_STARTUP_ENV = frozenset({"SYSTEMROOT", "WINDIR", "COMSPEC", "PATH", "PATHEXT"})


def checked_path(path: Path) -> Path:
    # Inspect lexical ancestors before resolve: resolve would conceal a junction.
    absolute = Path(os.path.abspath(path))
    for item in (absolute, *absolute.parents):
        if not item.exists() and not item.is_symlink():
            continue
        metadata = item.lstat()
        if stat.S_ISLNK(metadata.st_mode) or (
            getattr(metadata, "st_file_attributes", 0) & 0x400
        ):
            raise ValueError("synthetic execution paths must not traverse reparse points")
    return absolute


def validate_roots(owned_root: Path, out_root: Path) -> tuple[Path, Path]:
    owned, output = checked_path(owned_root), checked_path(out_root)
    if owned == output or owned in output.parents or output in owned.parents:
        raise ValueError("owned and output containers must be disjoint")
    if (owned.exists() and not owned.is_dir()) or (
        output.exists() and not output.is_dir()
    ):
        raise ValueError("execution containers must be directories")
    return owned, output


class OwnedAttempt:
    """Only the unique child created by this instance may be recursively removed."""
    def __init__(self, container: Path):
        self.container = checked_path(container)
        self.created_container = not self.container.exists()
        self.created_dirs = []
        cursor = self.container
        while not cursor.exists():
            self.created_dirs.append(cursor)
            cursor = cursor.parent
        self.container.mkdir(parents=True, exist_ok=True)
        try:
            self.path = Path(tempfile.mkdtemp(prefix="w06-owned-", dir=self.container))
        except Exception:
            for directory in self.created_dirs:
                directory.rmdir()
            raise
        self._created = True

    def cleanup(self) -> None:
        if self._created:
            target = checked_path(self.path)
            if target.parent != self.container or target == self.container:
                raise ValueError("owned child left its creation container")
            if target.exists():
                shutil.rmtree(target)
            self._created = False
        for directory in self.created_dirs:
            # Only remove directories created here, and only when still empty.
            if directory.exists():
                directory.rmdir()


def child_env(worktree: Path, workspace: Path) -> dict[str, str]:
    base = checked_path(workspace)
    home, temp = base / "home", base / "temp"
    home.mkdir(parents=True, exist_ok=True)
    temp.mkdir(parents=True, exist_ok=True)
    env = {key: value for key, value in os.environ.items()
           if key.upper() in _STARTUP_ENV}
    env.update(HOME=str(home), USERPROFILE=str(home), APPDATA=str(home / "appdata"),
               LOCALAPPDATA=str(home / "localappdata"), TEMP=str(temp), TMP=str(temp),
               PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1",
               PYTHON_DOTENV_DISABLED="1",
               PYTHONPATH=os.pathsep.join((str(worktree / "src"), str(worktree))))
    if os.name == "nt":
        env["HOMEDRIVE"] = home.drive
        env["HOMEPATH"] = str(home)[len(home.drive):]
    return env


@contextlib.contextmanager
def synthetic_environment(env: dict[str, str]) -> Iterator[None]:
    original = dict(os.environ)
    try:
        os.environ.clear()
        os.environ.update(env)
        yield
    finally:
        os.environ.clear()
        os.environ.update(original)


@contextlib.contextmanager
def offline_guard() -> Iterator[list[str]]:
    active, blocked = True, []
    def audit(event, args):
        if not active:
            return
        if event.startswith("socket.") and event not in {"socket.__new__"}:
            blocked.append("network")
            raise RuntimeError("network forbidden in synthetic portability harness")
        if event == "open" and args and isinstance(args[0], (str, bytes)):
            name = os.path.basename(os.fsdecode(args[0])).lower()
            if name in {".env", ".env.local", "credentials"} or (
                "api_key" in name and not name.endswith((".py", ".pyc"))
            ):
                blocked.append("credential_file")
                raise RuntimeError("credential files forbidden in synthetic harness")
    sys.addaudithook(audit)
    try:
        yield blocked
    finally:
        active = False


def main() -> int:
    """Child bootstrap installs isolation before any company_wiki import."""
    import argparse
    import runpy
    parser = argparse.ArgumentParser()
    parser.add_argument("--module", required=True)
    args, remainder = parser.parse_known_args()
    if args.module not in {
        "company_wiki.source_catalog.source_export_v2_cli",
        "company_wiki.source_catalog.source_reader_cli",
        "tools.source_root_portability.consumer_spy",
    }:
        raise ValueError("unsupported synthetic child entry")
    root = Path(__file__).resolve().parents[2]
    sys.path[:0] = [str(root / "src"), str(root)]
    sys.argv = [args.module, *remainder]
    with offline_guard():
        runpy.run_module(args.module, run_name="__main__")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
