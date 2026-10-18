# P3-IDENTITY-AUDIT 进度

| 阶段 | 状态 | 证据 |
|---|---|---|
| 0 侦察既有契约 | DONE | 见 findings.md |
| 1 RED 用例（≥15） | DONE | `red-1-pre-implementation.log`（44 failed / 2 passed，exit 1，全部为显式断言失败，非 ImportError） |
| 2 实现 tools/identity_audit | DONE | `core.py` `cli.py` `receipt.py` `export.py` `__init__.py` `__main__.py` `README.md`（均在本卡写集内） |
| 3 GREEN（pytest/ruff/mypy/CLI） | DONE | `green-1.log`（46 passed / 0 skipped，exit 0）；`static-1.log`（ruff 0 违例；mypy 6 文件 0 问题；手动 CLI demo exit 0） |
| 4 只读与字段证明 | DONE | 测试内字节级快照（sha256+size+mtime_ns）证明除 `--out` 外零改动；demo 脚本 `demo-cli-run.py` 同证；`receipt.json` 字段与 `identity-audit-receipt/1` 完全一致（shell 7 键由 test_2 固定断言） |
| 5 独立审查 + 修复 + 复审 | DONE | 首轮 `review/independent.md`：REJECT（1 BLOCKER + 2 MAJOR + 4 MINOR + 4 NOTE，绑定 `99a67f06`）；修复提交 `20a43fab`；复审（同一独立 agent）：**APPROVE**，F1–F7 全部验证修复，无新增 BLOCKER/MAJOR，3 个非阻塞 MINOR/NOTE 转入 handoff known_limits |
| 6 交接 ROOT | DONE | `handoff.md` / `handoff.json`（本文件定稿后单独提交；实现提交 99a67f06、修复提交 20a43fab、交接提交为第三个提交） |

## 日志

- RED：`python -B -m pytest tests/unit/test_identity_audit -q -p no:cacheprovider` → 44 failed / 2 passed，exit 1 → `red-1-pre-implementation.log`。
- GREEN #1：同命令 → **46 passed，0 skipped**，exit 0 → `green-1.log`。
- 静态 #1：`python -m ruff check tools/identity_audit tests/unit/test_identity_audit` → All checks passed；`python -m mypy`（6 个 lane 生产模块）→ 0 问题 → `static-1.log`。
- 手动 CLI #1：`demo-cli-run.py` → exit 0、status=ok、counts={checked:6, passed:5, not_applicable:1}、合成树逐字节零改动 → `receipt.json` + `static-1.log`。
- 独立审查 #1（非作者 agent，绑定 `99a67f06`）→ **REJECT**，详见 `review/independent.md`。
- GREEN #2（修复后）：同 pytest 命令 → **50 passed，0 skipped**（新增 4 个回归用例），exit 0 → `green-2.log`。
- 静态 #2 + 手动 CLI #2：ruff / mypy 0 问题；demo exit 0 → `static-2.log`。
- 独立审查 #2（同一独立 agent，绑定最终 SHA `20a43fab`）→ **APPROVE**；F1–F7 逐项复验修复，全套验收重跑（50 passed ×2 稳定、ruff/mypy 0、diff 25 文件全在写集内、`99a67f06..20a43fab` 测试差异 +81/−0 无删除弱化），详见 `review/independent.md`。

## 独立审查第一轮发现与修复对照（作者提交，全部为 lane 写集内改动）

| 级别 | 发现 | 修复 |
|---|---|---|
| BLOCKER F1 | `_validate_span` 用自研校验取代卡 §5.2 指定的 `EvidenceSpan.from_dict`；全 null 坐标 span 令 `_unit_check` 抛 `TypeError` → CLI exit 1、stdout 空（违反 §5.1） | `core.py::_validate_span` 改为调用冻结的 `EvidenceSpan.from_dict`，任何拒绝 → `blocked`/`invalid_argument`（`invalid_request` 非 §3 发布码，故用已发布的 `invalid_argument`） |
| MAJOR F2 | 同根因：全 null 坐标 span 的 `char_start/char_end=None` 令 `text[None:None]` 全文相等 → 未知→通过 | F1 修复后该 shape 在校验层即被拒绝；新增回归用例 2 个（core 层 + CLI 层 exit 3 单行 JSON） |
| MAJOR F3 | `char_end=10^9` 越界 offset 被 Python 切片静默截断 → `pass` 且回显荒谬 offset | `_audit_one_span` 增加显式越界检查 → `p3_span_ungrounded` + `detail.bounds_violation`；新增回归用例 |
| MINOR F4 | `_bytes_check` 通过分支不复核请求侧摘要 | 增加防御性复核：重算 sha256/长度与请求不符 → `p3_bytes_mismatch` |
| MINOR F5 | `source_availability_unknown` 计入 checked 但无裁决桶，桶和≠checked 未披露 | `LIMITATIONS` 增加披露行（计数词表冻结，无桶是契约事实） |
| MINOR F6 | 卡 §5.4(4) 要求 `detail.date_provenance`，实现在 `observed` 内 | period 检查的**每个** `detail` 均带 `date_provenance`（`observed` 副本保留，既有断言不变） |
| MINOR F7 | `--out` 未拒绝 `..` 穿越与符号链接目标 | `cli.py::_refused_out_path`：`..` 分量或已存在 symlink → `blocked`/`invalid_argument`；新增回归用例 |
| NOTE F8–F11 | F8/F9/F10 契约内可接受（字段超集、额外 reason、未达错误码），F11 `static-1.log` 含早期失败 demo 轨迹 | F11：重新生成 `static-2.log`（干净的 ruff+mypy+demo 输出）；F8–F10 在 handoff `known_limits`/`limitations` 内保留披露 |

修复期间的自查：一次 edit 曾把 `inputs` 定义放在使用之后（ruff F821 + mypy used-before-def 同时捕获），当轮 pytest 亦失败；已修正并全量复跑（50 passed / ruff 0 / mypy 0）。

## 待办

- 无。阶段 0–6 全部完成，等待 ROOT 按 README §6 验收清单接收。
