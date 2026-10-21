# R1 contract 债修复独立审查（2026-10-21）

结论：**PASS，按实际内容 SHA 绑定；0 个未关闭阻断项。** 独立审查未修改作者源码或测试。作者可按正常流程提交这份内容；母仓源码仍与 `45195e96cb15a1652b13899a99cfb827932a62f1` 一致，此结论不执行合并或发布，也不签公司业务审查。

审查对象为 `C:\Users\郑曾波\.codex\worktrees\du11-extractive-runtime\company-wiki`，分支 `codex/r1-contract-debt`。审查时 HEAD 仍为 base，实际修复通过以下内容 SHA 以及 JSON 内全部源码/测试/golden 指纹绑定；最终 GREEN 前后指纹一致，审查时当前文件再次逐项匹配。

| 生产文件 | SHA-256 |
|---|---|
| `src/company_wiki/automation/store.py` | `fdc4a8f713116e5cfa2c63f0afdb530a364945b0e4927efd6d63e0b99e93b624` |
| `src/company_wiki/automation/terminal_receipt_contracts.py` | `4113dda30f530f6fdf217c0280a1cddc5efdd8f1507964359e5b1154b85671df` |
| `src/company_wiki/automation/narrative_run_store.py` | `ebbb54bbd1acaab71d29016b650c470198a6f1b67da592be66c092cdf661c15f` |

## 实际验证

最终 `green-reviewed`：**195 passed / 0 failed / 0 errors / 0 skipped，exit=0**；UTC `2026-10-21T21:36:55.305839Z` → `2026-10-21T21:38:52.413483Z`，pytest 115.28 秒。当前两份 contract 为 33 项（原31项加2个 WAL 外部等待反例）；全部通过。相关范围还覆盖既有 WAL、终态压缩、paid recovery、wire/current read、历史 parser、run store/ownership/budget 测试。

母 `.venv` 只提供解释器，cwd/PYTHONPATH 和收据中的 imports 均指向隔离 tree；独立探针再核对了 store/run_store/parser 模块实际路径。完整 argv、所有变更文件及旧 golden 的 before/after SHA、每模块计数和收据 SHA 已嵌入 [JSON报告](r1-contract-debt-fix-review-20261021.json)。

| 原始轮次 | passed / failed / skipped | exit |
|---|---:|---:|
| red-original | 27 / 4 / 0 | 1 |
| red-projections | 0 / 3 / 0 | 1 |
| red-target | 0 / 2 / 0 | 1 |
| green | 151 / 1 / 0 | 1 |
| green-final | 152 / 0 / 0 | 0 |
| red-run-readers | 0 / 4 / 0 | 1 |
| green-reviewed | 195 / 0 / 0 | 0 |

前两轮名含 green 的152项结果均为保留的中间收据；最终接收轮次为 `green-reviewed`。原始收据在母仓 `.planning/r1ctfix/logs/`，独立探针在 `.planning/r1rv21/`；不把这些本机文件描述为 fresh clone 天然具备。

## 关闭的独立发现

**R1-F1（P2，已修复）：reservation 的同一投影共因不能由测试绕开。** 首轮扩列后 public `reservations_for_run` 真实抛 `TypeError`。作者一度把费用比较改为测试自行读取 SQL；独审与 ROOT 要求恢复公共接口断言。四个公开读取反例随后先红，均定位到 `SELECT * → ReservationRecord(**dict(row))`。

修复现由可信 `ReservationRecord` 字段定义生成一份明确 SQL 列表，四处 DTO 读取共同使用：`_reservation`、`_budget`、`model_attempts_for_job`、`reservations_for_run`。原费用快照断言已恢复。审查者另用内存 SQLite、独立手写合法 record 加内部列直接调用实际 `_reservation`，同一脚本由 TypeError RED 转为 PASS，源码 SHA 与最终 GREEN 一致。这次修复因此覆盖了被反例揭示的相关共因。

## 代码与证据判断

- `FinalArtifactPin.effect_target` 接管共享发布身份计算；store 消费中立 pin。raw 目标字符串原样保留，official JSON 目标保留 subject 与 generation 两份 hash；anchor 验证和序列化字段未弱化。独立字面公式探针验证了 raw 以及三组 subject/generation 身份区分。
- 原 store 的三处 wildcard 全部改为实际使用字段。三个未来内部列反例检查真实 cursor.description，并覆盖压缩幂等、summary/verify 精确重排、attempt/fee 保留及单次 provider fixture 调用。
- WAL 静态例外限定在原有 `_open_connection` 的两个等待 token；其他禁令保留，外部等待反例及原有 peer/deadline/nonbusy 行为测试通过。运行时重试实现没有改动。
- 旧六个 JSON 的 SHA 均与母仓一致。current-v2 恰有12个已解释路径变化：parser/selector/prompt、core_business、reason 顺序、派生 span SHA/ID 及其引用。57字符管理层原话、source SHA/字节数、locator 与原文半开区间32:94一致，未加入数字或单位。
- current golden 来自真实离线 runtime/CLI；审查 helper 仅允许明确列出的变化后要求全对象相等，并保留事实、单位和错误 citation 反例。它没有抹掉版本、接受任意 hash 或单纯重刷旧答案。
- 独立 spy 观察到真正按保存版本调用 parser0.1.1 和0.3.1；另一个 natural-format 输入使 legacy 和 current 产生不同结果，确认不是只换标签。此项证明保存 parser 的来源重放与 wire 兼容，不宣称当前 selector 能重新生成旧0.4.2历史输出。

## 隔离与范围

母仓当前 HEAD 为 `0aa544565fbbca7d33d88dc35646a5b0af8de6ac`，`src/scripts/config/tests` 相对 base 及工作树仍无 diff，生产配置 SHA 为 `3d159a4edc8e0e4d09b83afa95601c5ec885a18f7bd5d163579f3ff446e3f968`。最终收据保护的96文件前后相同；审查者写入仅限指定报告与独占合成 tmp，未访问并行 RF run 数据、下载、联网、调用模型、安装或修改生产配置/原件。未新增逐材料许可、canary 或运行门禁。

未跑全量7k、全contract或真实 RF/FF；本结论覆盖本次修复及已揭示的 reservation DTO 共因，不代表全仓继承代码已无任何 wildcard。最终 source commit 由作者正常提交后可回填，当前通过以上完整内容 SHA 精确定位。
