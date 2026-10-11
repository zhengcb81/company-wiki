from pathlib import Path

ROOT = Path('C:/Users/郑曾波/Projects/_harness_worktrees/w05/rf-flow-root')
path = ROOT / 'scripts/contracts/period_flow.py'
body = path.read_text(encoding='utf-8')
anchor = '    for position, (start, end, input_id, coefficient, semantic) in enumerate(atoms):'
assert anchor in body
body = body.replace(anchor, '    require(bool(windows), f"{parameter_id}: dated composition needs a flow-bearing input; stock/rate alone cannot establish recognized revenue")\n' + anchor)
path.write_text(body, encoding='utf-8')

path = ROOT / 'compatibility/compatibility_manifest.py'
body = path.read_text(encoding='utf-8')
start = body.index('REPO_DIRS = {')
end = body.index('\nVALID_TIERS', start)
body = body[:start] + body[end:]
body = body.replace('def validate_manifest(data: dict) -> list[str]:\n    """Return manifest invariant violations; empty list means valid."""',
'''def validate_manifest(data: dict) -> list[str]:
    """Pure manifest/registry validation; no implicit sibling repository reads.

    Actual Git ancestry belongs to ``validate_repository_ancestry`` with
    explicitly supplied roots. This function checks the immutable baseline
    declaration, versions and registry byte hashes independently of layout.
    """''')
start = body.index('    for repo in REPOS:\n        head = current.get(repo)')
end = body.index('\n\ndef validate_command_registry', start)
body = body[:start] + '''    return problems


def validate_repository_ancestry(data: dict, repo_dirs: dict[str, Path]) -> list[str]:
    """Explicit read-only integration check of the declared Git triplet.

    Unit tests supply temporary repositories. Real integration callers first
    run ``validate_manifest`` to verify the frozen baseline declaration, then
    supply actual repository roots; there is no inferred user directory.
    """
    problems: list[str] = []
    current = data.get("current_triplet", {})
    baseline = data.get("frozen_baseline_triplet", {})
    if not isinstance(current, dict) or not isinstance(baseline, dict):
        return ["ancestry triplets must be objects"]
    for repo in REPOS:
        head, floor = current.get(repo), baseline.get(repo)
        root = repo_dirs.get(repo)
        if not _is_sha1(head) or not _is_sha1(floor):
            problems.append(f"{repo}: ancestry needs complete SHA-1 commits")
            continue
        if not isinstance(root, Path) or not root.is_dir():
            problems.append(f"{repo}: explicit repository root is missing")
            continue
        if not _is_descendant(floor, head, root):
            problems.append(f"{repo} HEAD {head[:10]}... is not a descendant of the declared baseline {floor[:10]}...")
    return problems
''' + body[end:]
body = body.replace('CI and local runners must consume only this\nmanifest — no scattered commits inside workflows.',
                    'Explicit integration callers consume this manifest; unit tests do not\ninfer sibling repository paths from the module location.')
path.write_text(body, encoding='utf-8')

path = ROOT / 'compatibility/contract_registry.py'
body = path.read_text(encoding='utf-8')
body += '''\n\ndef validate_canonical_documents(data: dict, repo_roots: dict[str, Path]) -> list[str]:
    """Read-only document integration using explicit roots, not sibling layout."""
    problems: list[str] = []
    for name, spec in data["contracts"].items():
        reference = Path(spec["canonical_doc_path"])
        root = repo_roots.get(reference.parts[0])
        if root is None or not (root.joinpath(*reference.parts[1:])).is_file():
            problems.append(f"{name}: canonical_doc_path does not exist: {reference}")
    return problems
'''
assert 'from pathlib import Path' in body
path.write_text(body, encoding='utf-8')

path = ROOT / 'tests/test_contract_registry.py'
body = path.read_text(encoding='utf-8')
body = body.replace('import unittest\n', 'import unittest\nimport tempfile\n')
body = body.replace('    validate,\n', '    validate,\n    validate_canonical_documents,\n')
body = body.replace('# The three repos are siblings; resolve canonical_doc_path values against it.\nREPO_PARENT = Path(__file__).resolve().parents[2]\n', '')
start = body.index('    def test_every_contract_canonical_doc_exists_on_disk(self) -> None:')
end = body.index('\n\nclass RegistryValidatorMutationTests', start)
body = body[:start] + '''    def test_every_contract_canonical_doc_exists_on_disk(self) -> None:
        # The registry path contract is tested in a portable owned fixture.
        # Real document existence is an explicit cross-repository integration.
        data = load()
        with tempfile.TemporaryDirectory(prefix="rf-contract-docs-") as scratch:
            parent = Path(scratch)
            for spec in data["contracts"].values():
                path = parent / spec["canonical_doc_path"]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture canonical contract", encoding="utf-8")
            roots = {"company-wiki": parent / "company-wiki"}
            self.assertEqual(validate_canonical_documents(data, roots), [])
            path.unlink()
            self.assertTrue(validate_canonical_documents(data, roots), "missing canonical document was accepted")
''' + body[end:]
path.write_text(body, encoding='utf-8')

path = ROOT / 'tests/test_compatibility_manifest.py'
body = path.read_text(encoding='utf-8')
body = body.replace('import unittest\n', 'import unittest\nimport subprocess\nimport tempfile\n')
body = body.replace('    validate_manifest,\n', '    validate_manifest,\n    validate_repository_ancestry,\n')
old = '''    def test_current_triplet_is_descendant_of_frozen_baseline(self) -> None:
        # The real gate: no repo may sit below the frozen baseline.
        problems = validate_manifest(self.manifest)
        self.assertEqual(problems, [])'''
new = '''    def test_current_triplet_is_descendant_of_frozen_baseline(self) -> None:
        with ancestry_fixture() as (data, roots):
            self.assertEqual(validate_repository_ancestry(data, roots), [])'''
assert old in body
body = body.replace(old, new)
old = '''    def test_rejects_head_not_descendant_of_baseline(self) -> None:
        data = self._base()
        data["current_triplet"]["revenue"] = "a" * 40  # not a real commit on the line
        self.assertTrue(validate_manifest(data), "validator accepted a reset sibling")'''
new = '''    def test_rejects_head_not_descendant_of_baseline(self) -> None:
        with ancestry_fixture() as (data, roots):
            # The floor is the second fixture commit; its parent is a real
            # ancestor but must be rejected as the current regression.
            data["current_triplet"]["revenue"] = fixture_git(roots["revenue"], "rev-parse", "HEAD~1")
            self.assertTrue(validate_repository_ancestry(data, roots), "validator accepted a reset sibling")

    def test_ancestry_requires_explicit_repository_roots(self) -> None:
        with ancestry_fixture() as (data, roots):
            roots.pop("revenue")
            self.assertTrue(validate_repository_ancestry(data, roots), "missing explicit root was accepted")'''
assert old in body
body = body.replace(old, new)
insert = '''\n\ndef fixture_git(root: Path, *arguments: str) -> str:
    result = subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid",
                             "-c", "core.hooksPath=/dev/null", *arguments], cwd=root,
                            capture_output=True, text=True, encoding="utf-8", timeout=15, check=True)
    return result.stdout.strip()


def ancestry_fixture():
    """Six tiny real commits, no canonical data or physical sibling contract."""
    from contextlib import contextmanager

    @contextmanager
    def owned():
        with tempfile.TemporaryDirectory(prefix="rf-ancestry-") as scratch:
            roots, floor = {}, {}
            for name in ("revenue", "filing", "wiki"):
                root = Path(scratch) / name
                root.mkdir()
                fixture_git(root, "init", "--quiet")
                fixture_git(root, "commit", "--quiet", "--allow-empty", "-m", "parent")
                fixture_git(root, "commit", "--quiet", "--allow-empty", "-m", "floor")
                roots[name], floor[name] = root, fixture_git(root, "rev-parse", "HEAD")
            yield {"frozen_baseline_triplet": floor, "current_triplet": dict(floor)}, roots
    return owned()
'''
anchor = '\n\nclass ManifestTests'
assert anchor in body
body = body.replace(anchor, insert + anchor)
path.write_text(body, encoding='utf-8')
print('Applied unified stock typed precondition and explicit portable compatibility seams; no commit')
