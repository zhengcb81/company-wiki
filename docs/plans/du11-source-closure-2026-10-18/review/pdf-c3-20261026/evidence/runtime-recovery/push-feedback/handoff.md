# C3 pre-push feedback repair

Ready for independent review; no commit or project push performed.

Daily selection expands only small affected tests/unit targets. Non-unit recommendations are explicitly deferred to existing CI or separate major-node acceptance; all 29 original FAST targets are byte-equivalent as Python inventory values. Broad/unknown recommendations keep FAST only. The existing 32 affected-target bound remains.

Reuses company_wiki._bounded_process.run_bounded with its Windows Job bootstrap ownership barrier, bounded pipes, one deadline and owned-tree cleanup. The base implementation is unchanged. Child failure codes remain real; timeout returns 124; overflow returns 125 with retained diagnostics. Daily pytest adds verbose node progress and durations.

Limits: daily total 180s versus previous 600s, selected because prior healthy 154-case smoke took about 52s; full explicit mode remains 600s. stdout cap is 4MiB and stderr cap 512KiB (plus the bounded transport single probe byte), replacing unbounded capture. Output exceeding a cap is RED, with a truncation message and captured progress.

TDD: red.txt reproduces three scope failures and a live owned grandchild after timeout (4 failed, 1 passed). venv-final-green.txt: 40 passed in 22.55s, including real Windows descendant termination, launcher descendant held-file release before scratch cleanup, both output caps, preserved exit=7, prior TEMP/SQLITE/Git isolation/worker regressions. host-git-normal.txt: all 30 policy tests passed in 37.73s including real local Git hook pushes. ruff and diff whitespace checks passed.

The restricted-shell host run had 153 passed and five MSYS NtCreateDirectoryObject denials; changing Python alone could not change the inherited Low token. All five were subsequently verified in the authorized normal-integrity host run. No ACL or integrity labels were changed. A first new launcher fixture used 2s and raced startup under load; its timeout is now 4s and its real cleanup assertion passed.

Existing test changes preserve their intent: timeout mocks moved from subprocess.run to the bounded runner; mixed-selection expectation now enforces the requested unit-only policy and every FAST member; Git fixture copies both real owner modules. Windows Job and launcher/file-lock lifetime tests are scoped to Windows.

All TEMP/TMP/TMPDIR/SQLITE_TMPDIR test roots used push-feedback/temp; that owned root has been removed after test completion. No unrelated process was stopped.

Changed-file SHA-256:

- tools/pre_push_gate.py: `4175973f5bfd2f727fdff54567f9f4361d5834bfe7c47bcbdc735e64148fc538`
- tests/unit/test_pre_push_gate.py: `624d413e16236550188731feb4b6cb8b2673dbb578d9b2f3d67959490d065d96`
- tests/unit/test_pre_push_process_cleanup.py: `d7a2d0bd5d18514280d48abf5a1100f95c1c9b81e9738deeb0b5bb5584000896`
- tests/unit/test_pre_push_temp_scope.py: `ccf736630701507b431ba9e933f2189e3133c23977301d1adf926e0b1e88b7d3`
- tests/unit/test_daily_push_policy.py: `931871fea16df19129d972f5a87b09df92b95bf111f04201ce18a71163642efc`
