# V5 版本合同 rev4：独立设计复审（G1 最终闭合，2026-09-09）

审查者：independent design review agent（非作者，复审）
范围：rev4 `v5-version-contract.md`（commit `2fbbe5e`）、`tools/v5_*.py`、重生成的证据 JSON/MD、`progress.md`/`findings.md` 更正行。
方法：只读复算——两工具 `--check` 只读模式（均 exit 0）＋自有内存复现（拦截 `Path.write_text`，证据文件未落盘；`sys.dont_write_bytecode` 已避免缓存写入）。

结论：**accepted**。G1 阻断项已闭合，H1/H2/H3/G2 全部关闭，V5-1 判定完成、**V5-2 可以开始**。残留两条 P3（K1/K2）不阻断开工。

## 闭合判定

| ID | 状态 | 证据（本次复算） |
|---|---|---|
| G1 阻断项 | **closed** | §5.1:51 现为「必填字段 **19 项**」且含 `evidence_tools[]`（程序化计数：声明 19 = 列举 19，`evidence_tools` 在列）；N4（`:110`）「缺必填字段或出现未知字段」与 N17（`:123`）不再冲突 |
| G1 其余 | closed | §5.2:56-62 的 51 = 48 + 3 未变；`:64` 增「派生规则（可机器校验）」（`imported`/`v5_own_governing`/`total`/`self_excluded`）；`:65` 增 checker 路径规则（＝`pre_freeze_check.command` 中的脚本，`equivalence = v5_own`）；N13–N17（`:119-123`）齐备 |
| H1 | closed | 三份证据文件在我的自有内存复现下**逐字节相同**：inventory.json sha256 `b7612e0f…`、inventory.md `0240a85f…`、equivalence.json `79ac6ca4…`；`--check` 亦 exit 0；运行后 `git status` 为空 |
| H2 | closed | §6.2:83 改为「文件总数以 `git ls-files`/`Get-ChildItem` **实时查询**为准（不写死）」；`:88` 审查记录行改为 `v5-version-contract-review*.md`（逐轮追加） |
| H3 | closed | 两工具新增只读 `--check`（scan `:149-166`、equivalence `:68-74`，仅 `read_text`＋退出码）；实测均 `CHECK OK`、exit 0、无写入 |
| G2 | closed | `progress.md:13`、`findings.md:41-42` 均改为「精确 tracked 数以 `git ls-files` 实时查询为准（本页不写死）」；两文档再无硬编码 tracked 数（残留「64」仅为 SHA-256 子串） |
| K1（新） | P3（非阻断） | §5.2:66 只说证据工具「各自 hash 绑定」，未给 `evidence_tools[]` 的条目类型；建议在 §5.1/§5.2 写明 `{path, sha256, size_bytes}` |
| K2（新） | P3（非阻断） | 两处 `--check` 用 `read_text()`（通用换行）比对 LF 载荷（scan `:156-158`、equivalence `:69-70`），CRLF↔LF 漂移会被放过；当前三份文件 CRLF=0，故本次通过为真实。建议改 `read_bytes()` 严格比对（v4 事故正是 EOL 漂移） |

## 声明

本复审只读、非作者；除本文件外未写入任何文件（证据复现全部在内存完成，`tools/` 仍为 2 个文件，`git status` 为空）。未提交、未运行产品测试或旧 checker/worker、未联网。本审查**只绑定规划文档完整性**，不授权实施：V5-1 通过仅表示该合同可作 V5-2 输入；V5-2 仍须实现 N1–N17、跑全套一致性检查、生成 `plan_manifest.v5.json`，并在三路独立审查且 P0/P1 全关后才可作为实施依据。
