# Progress — N5-DOCSET

## Session 1 (2026-10-06)

- Worktree (lane checkout, see handoff.json for the absolute path), branch `codex/n5-document-quality`, baseline `e46108b4f30d5b7e47bfc712e360f173c00b702c` (clean at start).
- Read the lane card, the N5 parallel-package card, N4 implementation rules; mapped parser/selector/locator/routing/official read-only interface (see findings.md).
- Selected 9 real originals covering 年报/半年报/季报/招股书/增发/可转债/有价值IR/程序性IR/英文电话会; SHA-256 + byte size measured; `samples.json` + `local.json` (git-ignored) written.
- Read originals page-by-page via `tools/extract_pages.py` (read-only extraction into `tmp/n5-docset-extract/`), wrote `golden.json` with **86 points** (S01 11, S02 10, S03 8, S04 8, S05 8, S06 11, S07 10, S08 8, S09 12); every quote verified against the cited original page/line, `quote_sha256` + TXT byte offsets filled.
- Replaced a broken-extraction procedural IR candidate (中际旭创, 10 KB web-template stub) with a readable 3-page procedural record (周大生 2023-06-26) so the ≥6-point floor is met honestly.
- Wrote `evaluator.py` (schema `narrative-document-quality/1`) and `tests/test_evaluator_unit.py` counterexamples; RED observed (22 collected → 11 failed on fixture/validator defects), then GREEN: **22 passed**.
- Wrote `run_benchmark.py`; smoke run on S03 passed self-validation: required 0.75, optional 1.0, noise 0.0, role/modality confusion 0, locator roundtrip 0 failed, status `selected`, coverage_complete true.

### Test commands

```powershell
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD='1'
$env:CW_BASETEMP_FALLBACK_ROOT="$PWD	mp"
python -m pytest -p no:cacheprovider --basetemp tmp/n5-docset-test benchmarks/narrative_document_types/tests/test_evaluator_unit.py
```

Note: the repo's short-basetemp rule relocates any `--basetemp` inside this worktree (cwd 57 chars + suffix > 60), so `CW_BASETEMP_FALLBACK_ROOT` pins the fallback root inside `tmp/` as the card requires; the root is created fresh and removed in `pytest_unconfigure` (verified: `CW-BASETEMP-CLEANUP ... "removed": true`).

### Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| `Quote not found on page 19` (S01 legal quote) | 1 | Original reads `误导性陈述或重大遗漏` (no 者); quote corrected to the original wording and re-verified |
| `SyntaxError: def test_quote_hash_helper_matches hashlib()` | 1 | Typo in test name repaired, suite re-collected |
| `EvidenceSpan.create() missing quality_flags` | 1 | Fixture now passes `quality_flags=()` |
| `duplicate ratio does not match arithmetic` when 0 selected | 1 | Validator defines `0.0` (not null) for a zero-total duplicate ratio; evaluator + validator aligned |
| `TypeError: string indices must be integers` in runner | 1 | `_golden_points_for` returned the sample entry instead of `entry["points"]` |
| Accidental `tmp/n5-ir-candidates.json` written into source repo | 1 | Removed immediately; all later scratch writes go to the lane worktree |

## Next Step

Phase 4: run the full 9-sample benchmark to produce `report.json`, then Integration/E2E tests, README, handoff.

## Session 2 (2026-10-06) — 跑批、测试与交付

- 修复 `temp_peak_bytes` 恒为 0（度量文件存活 < 采样间隔）：度量文件大小改为同步记账。
- 全量跑批产出 `report.json`：9 份 / 86 golden / 712 span，回放 712 通过 0 失败，
  required 0.3333、optional 0.2353、噪声 0.0833、重复 0.0674、角色/情态混淆 0，
  耗时 260.823s、临时峰值 152,604B；报告自校验通过。
- Integration 6 + E2E 1 + Unit 22 = **29 passed / 37.62s**；`ruff check` 全绿；`git diff --check` 干净。
- E2E 回执（S02/S03/S05）：`open_version(purpose=narrative_derivation)` 读到的字节 SHA 与登记一致，
  271 个 span 全部回放通过，原件指纹不变，tmp 根 `finally` 恢复。
- miss 归因抽样核对：S01 p40、S06 p87 的 golden 单位**已由 parser 产出但未被 selector 选中**（真漏）；
  S09 L200 单位已产出但未入选（498 unit 仅 14 candidate）。
- 提交 `9ff251ec9ce5b29b294477d66f84336a464fc29c`（代码 + golden + 报告 + PWF），
  随后补 `docs/implementation/handoffs/N5-DOCSET/`。
- 清理 `tmp/` 抽页与索引残留；`local.json` 保持未跟踪；跟踪文件内无机器绝对目录。

### 测试结果

| 节点 | 结果 |
|---|---|
| Unit（评估器反例） | 22 passed |
| Integration（真实 parser/selector + 报告契约） | 6 passed |
| E2E（独立 catalog + 正式只读接口 + 回放 + 恢复） | 1 passed |
| ruff（本包） | All checks passed |
| 全节点 | 29 passed in 37.62s |
