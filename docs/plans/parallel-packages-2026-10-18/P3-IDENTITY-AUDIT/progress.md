# P3-IDENTITY-AUDIT 进度

| 阶段 | 状态 | 证据 |
|---|---|---|
| 0 侦察既有契约 | DONE | 见 findings.md |
| 1 RED 用例（≥15） | DONE | `red-1-pre-implementation.log`（44 failed / 2 passed，exit 1，全部为显式断言失败，非 ImportError） |
| 2 实现 tools/identity_audit | DONE | `core.py` `cli.py` `receipt.py` `export.py` `__init__.py` `__main__.py` `README.md`（均在本卡写集内） |
| 3 GREEN（pytest/ruff/mypy/CLI） | DONE | `green-1.log`（46 passed / 0 skipped，exit 0）；`static-1.log`（ruff 0 违例；mypy 6 文件 0 问题；手动 CLI demo exit 0） |
| 4 只读与字段证明 | DONE | 测试内字节级快照（sha256+size+mtime_ns）证明除 `--out` 外零改动；demo 脚本 `demo-cli-run.py` 同证；`receipt.json` 字段与 `identity-audit-receipt/1` 完全一致（shell 7 键由 test_2 固定断言） |
| 5 独立审查 + 修复 + 复审 | IN_PROGRESS | `review/independent.md` 待写 |
| 6 交接 ROOT | PENDING | `handoff.md` / `handoff.json`（实现提交之后的独立提交） |

## 日志

- RED：`python -B -m pytest tests/unit/test_identity_audit -q -p no:cacheprovider` → 44 failed / 2 passed，exit 1 → `red-1-pre-implementation.log`。
- GREEN：同命令 → **46 passed，0 skipped**，exit 0 → `green-1.log`。
- 静态：`python -m ruff check tools/identity_audit tests/unit/test_identity_audit` → All checks passed（此前 5 个 F401 已用 `--fix` 清除）；`python -m mypy`（6 个 lane 生产模块）→ 0 问题 → `static-1.log`。
- 手动 CLI：`demo-cli-run.py` 构建 tmp 合成夹具 → `python -B -m tools.identity_audit --config … --request … --out receipt.json --pretty` → exit 0、status=ok、counts={checked:6, passed:5, not_applicable:1}、合成树逐字节零改动、`--out` 与 stdout 内容等价 → `receipt.json` + `static-1.log`。

## RED→GREEN 期间的作者修正（均在卡规则允许范围内，未删除用例、未加 skip、未弱化冻结断言）

1. `test_2_receipt_shell.py`：`CHECK_FIELDS` 扩为卡 §5.3 实际定义的检查形状（增加 `observed`/`expected`/`tokens`）。原清单与同卡 test_1 对 `identity["observed"]` 等的断言互相矛盾；状态词表断言（该测试的冻结点）原样保留。
2. `test_1_checks.py` 三处夹具/平台修正：
   - 快照键统一 POSIX 化（Windows 反斜杠使 `startswith("out/")` 失效），bytes 翻转用例的目录前缀改为 `catalog/`（快照以夹具根为基准）。
   - identity `not_applicable` 用例改为「默认建库 + `record_source_facts` 置空 market/security_id」——建库期置空会让扫描器派生出空 `source_id`，`query_ref` 直接拒绝（与 probe 13 的记录路径一致）。
   - 非 ISO 日期用例改为侧写期注入 `period_end="2026/06/30"`——`record_source_facts` 自身强制严格 ISO，无法注入非法值。
3. `cli.py`：stdout 改为字节级写出（Windows 文本模式会把 `\n` 翻译成 `\r\n`，违反单行规范 JSON 契约）。

## 待办

- [ ] 阶段 5：非作者 agent 独立审查（含一字节翻转只读触发 `bytes.fail` 复核）→ 修复 → 绑定最终 SHA 复审 → `review/independent.md`。
- [ ] 阶段 6：实现提交之后，单独提交 `handoff.md` / `handoff.json`（README §8 两段式提交）。
