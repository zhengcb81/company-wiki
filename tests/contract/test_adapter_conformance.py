"""WU-502 RED/audit tests: conformance kit catches adapter violations."""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from company_wiki.source_catalog.adapters.conformance import (  # noqa: E402
    conformance_ok,
    run_conformance,
)
from company_wiki.source_catalog.adapters.interface import (  # noqa: E402
    NormalizedCandidate,
)


class _GoodAdapter:
    """Minimal conformant adapter: primary-only, deterministic, hash-accurate."""

    adapter_id = "fake_good_v1"
    version = "1.0.0"

    def enumerate(self, root_path, *, limit=None):
        candidates = []
        for path in sorted(root_path.rglob("*.pdf")):
            data = path.read_bytes()
            candidates.append(NormalizedCandidate(
                relative_path=path.relative_to(root_path).as_posix(),
                content_sha256=hashlib.sha256(data).hexdigest(),
                group_key=path.stem,
                role="primary",
            ))
        return candidates


class _HashBrokenAdapter(_GoodAdapter):
    """Mutation: wrong hash — must be caught by hash_accuracy."""

    def enumerate(self, root_path, *, limit=None):
        candidates = super().enumerate(root_path)
        for candidate in candidates:
            object.__setattr__(candidate, "content_sha256", "0" * 64)
        return candidates


class _RoleBrokenAdapter(_GoodAdapter):
    """Mutation: markdown misclassified as primary — role_separation."""

    def enumerate(self, root_path, *, limit=None):
        candidates = super().enumerate(root_path)
        for path in sorted(root_path.rglob("*.md")):
            candidates.append(NormalizedCandidate(
                relative_path=path.relative_to(root_path).as_posix(),
                content_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                group_key=path.stem,
                role="primary",  # wrong: markdown must not be primary
            ))
        return candidates


class _DuplicateAdapter(_GoodAdapter):
    """Mutation: duplicate candidates — no_duplicates."""

    def enumerate(self, root_path, *, limit=None):
        return super().enumerate(root_path) * 2


def _tree(tmp_path):
    (tmp_path / "annual").mkdir(parents=True)
    (tmp_path / "annual" / "2025.pdf").write_bytes(b"%PDF-1.4 x" * 10)
    (tmp_path / "annual" / "2025.md").write_bytes(b"# md")
    return tmp_path


def test_good_adapter_passes(tmp_path):
    receipt = run_conformance(_GoodAdapter(), _tree(tmp_path))
    assert conformance_ok(receipt), receipt


def test_hash_mutation_killed(tmp_path):
    receipt = run_conformance(_HashBrokenAdapter(), _tree(tmp_path))
    assert "FAILED" in receipt["hash_accuracy"]
    assert not conformance_ok(receipt)


def test_role_mutation_killed(tmp_path):
    receipt = run_conformance(_RoleBrokenAdapter(), _tree(tmp_path))
    assert "FAILED" in receipt["role_separation"]
    assert not conformance_ok(receipt)


def test_duplicate_mutation_killed(tmp_path):
    receipt = run_conformance(_DuplicateAdapter(), _tree(tmp_path))
    assert "FAILED" in receipt["no_duplicates"]
    assert not conformance_ok(receipt)


def test_read_only_guarantee(tmp_path):
    tree = _tree(tmp_path)
    before = {p.stat().st_mtime_ns for p in tree.rglob("*") if p.is_file()}
    run_conformance(_GoodAdapter(), tree)
    after = {p.stat().st_mtime_ns for p in tree.rglob("*") if p.is_file()}
    assert before == after


class _WriteBrokenAdapter(_GoodAdapter):
    """Mutation: adapter writes into the fixture tree — read_only."""

    def enumerate(self, root_path, *, limit=None):
        candidates = super().enumerate(root_path)
        (root_path / "evil.pdf").write_bytes(b"%PDF-1.4 evil")
        return candidates


class _SymlinkEscapeAdapter(_GoodAdapter):
    """Mutation: adapter returns candidates outside the tree — path escape."""

    def enumerate(self, root_path, *, limit=None):
        candidates = super().enumerate(root_path)
        import hashlib as _h

        candidates.append(NormalizedCandidate(
            relative_path="../../outside/secret.pdf",
            content_sha256=_h.sha256(b"secret").hexdigest(),
            group_key="escape",
            role="primary",
        ))
        return candidates


def test_write_mutation_killed(tmp_path):
    receipt = run_conformance(_WriteBrokenAdapter(), _tree(tmp_path))
    assert "FAILED" in receipt["read_only"]
    assert not conformance_ok(receipt)


def test_path_escape_mutation_killed(tmp_path):
    tree = _tree(tmp_path)
    receipt = run_conformance(_SymlinkEscapeAdapter(), tree)
    # escape candidate references a path outside the tree
    assert not conformance_ok(receipt)
    assert any("outside" in value for value in receipt.values())
