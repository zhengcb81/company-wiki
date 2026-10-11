from pathlib import Path

ROOT=Path('C:/Users/郑曾波/Projects/_harness_worktrees/w07/root-ff-perf-reception')
def replace(relative,before,after):
    p=ROOT/relative
    text=p.read_text(encoding='utf-8')
    assert before in text,(relative,before[:90])
    p.write_text(text.replace(before,after,1),encoding='utf-8')

runtime='tools/offline_contract_matrix/runtime.py'
replace(runtime,'        cache_created = not cache.exists()','        cache_created = True')
replace(runtime,'''            if cache_created:
                cache.mkdir()
                created.append(cache)''','''            # Cache is always newly owned. Never import/write into a previous
            # attempt's cache; independent batches must not delete each other's.
            for name in ["pc", *(f"p{i:02x}" for i in range(256))]:
                candidate = owned_parent / name
                try:
                    candidate.mkdir()
                except FileExistsError:
                    continue
                cache = candidate
                created.append(cache)
                break
            else:
                raise FileExistsError("no free compact cache child under owned root")''')
replace(runtime,'''        # Only a cache dir created by this attempt is removed; a pre-existing one
        # is non-owned and stays untouched (which is a preserved state, not a leak).''','''        # Only the exclusive cache created by this attempt is removed.
        # Pre-existing caches are never used and remain untouched.''')
replace(runtime,'''        except Exception:
            stdout, stderr = b"", b""
        raise DeadlineExceeded''','''        except Exception:
            stdout, stderr = b"", b""
        finally:
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
        raise DeadlineExceeded''')
replace(runtime,'''        except Exception:
            pass
        raise
    return subprocess.CompletedProcess''','''        except Exception:
            pass
        finally:
            try:
                proc.wait(timeout=5)
            except Exception:
                pass
        raise
    return subprocess.CompletedProcess''')

run='tools/offline_contract_matrix/run.py'
replace(run,'or (self.scratch.parent / "pc")','or (self.scratch / "pc")')
replace(run,'''        receipts = []
        for entry, row in zip(entries, summary.get("requests", [])):''','''        rows = summary.get("requests", [])
        if summary.get("schema_version") != "w07-seed-batch/1" or len(rows) != len(entries):
            raise ValueError("seed helper schema/request cardinality differs from submitted batch")
        receipts = []
        for entry, row in zip(entries, rows):
            if row.get("tag") != entry["tag"] or row.get("request_argv") != entry["argv"]:
                raise ValueError("seed helper request order or identity differs from submitted batch")''')

cli='tools/offline_contract_matrix/cli_main.py'
replace(cli,'''def run_case_group(''','''def _merge_source_proofs(target: dict, part: dict, group: str) -> None:
    """Retain every owned wiki proof; a later group cannot hide an earlier failure.

    Legacy oracle consumes a flat document-ID map. Its projection is conservative
    for collisions: every group's proof must verify and agree on the byte/version
    facts. Full unmodified worker proof records remain available alongside it.
    """
    groups = target.setdefault("worker_groups", {})
    if group in groups:
        raise ValueError(f"duplicate worker proof group: {group}")
    groups[group] = part
    merged = target.setdefault("proofs", {})
    for key, row in (part.get("proofs") or {}).items():
        previous = merged.get(key)
        if previous is None:
            merged[key] = dict(row)
        else:
            facts = ("content_sha256", "byte_size", "source_versions", "original_locations",
                     "physical_originals", "document_kind", "original_language_content_sha256")
            agrees = all(previous.get(f) == row.get(f) for f in facts)
            combined = dict(previous)
            combined["verified"] = previous.get("verified") is True and row.get("verified") is True and agrees
            combined["worker_collision"] = True
            if not combined["verified"]:
                combined["error"] = "worker proof collision includes a failed or incompatible verification"
            merged[key] = combined
    target.setdefault("catalog_snapshot", []).extend(part.get("catalog_snapshot") or [])


def run_case_group(''')
replace(cli,'    registry = _case_registry()','    registry = []')
replace(cli,'    try:\n        env = None','    try:\n        registry = _case_registry()\n        env = None')
replace(cli,'''            for ctx in ctxs:
                part = _fresh_proofs(ctx)
                proofs["proofs"].update(part.get("proofs") or {})
                proofs["catalog_snapshot"].extend(part.get("catalog_snapshot") or [])''','''            for index, ctx in enumerate(ctxs):
                part = _fresh_proofs(ctx)
                _merge_source_proofs(proofs, part, f"g{index + 1}")''')
# A diagnostic/measurement failure may propagate but must never bypass cleanup.
p=ROOT/cli
s=p.read_text(encoding='utf-8')
start=s.index('    finally:\n        for ctx in ctxs:')
cleanup=s.index('        with timer.span("cleanup"):',start)
finish=s.index('    observed = {r.id for r in results}',cleanup)
instrumentation=s[start+len('    finally:\n'):cleanup]
tail=s[cleanup:finish]
s=s[:start]+'    finally:\n        try:\n'+''.join('    '+line if line.strip() else line for line in instrumentation.splitlines(keepends=True))+'        finally:\n'+''.join('    '+line if line.strip() else line for line in tail.splitlines(keepends=True))+s[finish:]
p.write_text(s,encoding='utf-8')

# Correct one implementation-pinning author assertion. Strengthen actual
# preservation and exclusive ownership instead of demanding reuse of old pc.
replace('tests/test_w07_matrix_efficiency.py','''    assert attempt.cache_created is False
    restore = attempt.cleanup()''','''    assert attempt.cache_created is True
    assert attempt.cache != cache, "pre-existing cache must never be used for new writes"
    restore = attempt.cleanup()''')
print('Shared ownership/proof/seed/finally fixes applied; original41 oracle/handlers unchanged.')
