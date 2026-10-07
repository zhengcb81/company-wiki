"""Pure source-group selection; no store, resolver, downloader or model dependencies."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Protocol, TypeVar

class GroupCandidate(Protocol):
    relative_path: str
    group_key: str


CandidateT = TypeVar("CandidateT", bound=GroupCandidate)


@dataclass(frozen=True)
class SourceRegistrationScope:
    root_id: str
    relative_paths: frozenset[str]

    def __post_init__(self) -> None:
        if not isinstance(self.root_id, str) or not self.root_id or not self.relative_paths:
            raise ValueError("registration requires one root and non-empty relative paths")
        for value in self.relative_paths:
            if (not isinstance(value, str) or not value or "\\" in value or ":" in value
                    or value.startswith("/") or any(part in {"", ".", ".."} for part in value.split("/"))):
                raise ValueError("relative paths must be normalized root-relative paths")

    def select_groups(self, candidates: list[CandidateT]) -> list[CandidateT]:
        matched = {item.relative_path: item.group_key for item in candidates
                   if item.relative_path in self.relative_paths}
        if set(matched) != self.relative_paths:
            raise ValueError("registration path is not an available source candidate")
        groups = set(matched.values())
        return [item for item in candidates if item.group_key in groups]

    def company_paths(self, root: Path, company: str, sidecar_suffix: str) -> list[Path]:
        selected: set[Path] = set()
        for value in self.relative_paths:
            if not value.startswith(company + "/raw/"):
                continue
            primary = value.removesuffix(sidecar_suffix)
            for name in (primary, primary + sidecar_suffix):
                path = root / name
                if path.is_file():
                    try:
                        path.resolve(strict=True).relative_to(root.resolve(strict=True))
                    except ValueError as exc:
                        raise ValueError("registration path escapes configured root") from exc
                    selected.add(path)
        return sorted(selected)

    def resolve_path(self, root: Path, relative: str) -> Path:
        path = root / relative
        try:
            path.resolve(strict=True).relative_to(root.resolve(strict=True))
        except ValueError as exc:
            raise ValueError("source group escapes configured root") from exc
        return path

    def paired_paths(self, root: Path, sidecar_suffix: str) -> list[Path]:
        selected: set[Path] = set()
        for relative in self.relative_paths:
            primary = relative.removesuffix(sidecar_suffix)
            for value in (primary, primary + sidecar_suffix):
                path = root / value
                if path.is_file():
                    selected.add(self.resolve_path(root, value))
        return sorted(selected)

    def directory_entries(self, root: Path, sidecar_suffix: str) -> list[tuple[str, list[str], list[str]]]:
        grouped: dict[Path, list[str]] = {}
        for path in self.paired_paths(root, sidecar_suffix):
            grouped.setdefault(path.parent, []).append(path.name)
        return [(str(parent), [], sorted(names)) for parent, names in sorted(grouped.items())]

    def filing_paths(self, root: Path, walk_files: Callable[[Path], Iterable[Path]]) -> list[Path]:
        selected: set[Path] = set()
        for relative in sorted(self.relative_paths):
            path = self.resolve_path(root, relative)
            group = filing_group_key(relative)
            if group != relative:
                selected.update(walk_files(self.resolve_path(root, group)))
            else:
                selected.add(path)
        return sorted(selected)


def filing_group_key(relative: str) -> str:
    parts = Path(relative).parts
    if len(parts) >= 3 and parts[1] == "filings":
        count = 4 if len(parts) >= 4 and parts[2] == ".rejections" else 3
        return Path(*parts[:count]).as_posix()
    return relative


