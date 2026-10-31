# W22-CWP-ATOMIC-IO Handoff

状态：READY_FOR_ROOT。卡：`docs/plans/du11-source-closure-2026-10-18/harness_lanes/20261030/W22-CWP-ATOMIC-IO.md`。

## 交付了什么

共享原子写入 primitive 与 push-gate 临时布局现在都对 Windows 原生路径预算有真实兼容性，两处都在一个卡里解决：

1. `src/company_wiki/_atomic_file.py`：stage 名不再复制目标 basename，改为同目录独占随机名 `.atomic-<8rand>.tmp`（20 字符，与目标名解耦）。
2. `src/company_wiki/_atomic_path.py`（新私有 leaf，无 I/O）：`openable()` 针对完整已存在路径（绝对长度 >259 用 `\\?\` 或 `\\?\UNC\` 形式，幂等、非 Windows 恒等）；`stage_dir()` 针对将接收有界 stage 名的父目录（`abs(parent)+21 > 259` 即 wrap）。混合 extended→plain `os.replace` 实测可用。
3. `tools/pre_push_gate.py`：scratch 不再固定嵌在 checkout 根下；`_probe_writable` 单次 mkdir 有界探测候选（env TEMP/TMP/TMPDIR，无则 gettempdir，加 PROJECT_ROOT，按长度排序去重），deny-ACE 候选立即记录并回落，全败给出逐候选原因；TEMP/TMP/TMPDIR/SQLITE_TMPDIR 统一隔离到 owned root；try/finally 覆盖成功/失败/超时清理。选测、FAST_CONTRACT_CASES、超时、退出码、输出上限政策零改动。
4. 测试三件＋probe：`tests/unit/test_w22_atomic_paths.py`（11 用例）、`test_w22_atomic_consumer_integration.py`（3）、`test_w22_gate_scratch.py`（10），`tools/w22_atomic_probe.py` 四段实测证据 `docs/plans/w22-atomic-io-2026-10-30/logs/probe-final.json`。

## 平台事实（本宿主 NTFS，LongPathsEnabled=0；只读观察，未改注册表）

- 普通文件创建 ≤259 OK / 260 起 `FileNotFoundError errno 2`；普通 mkdir ≤247 OK / 248 起 `winerror 206`。目录上限低于文件上限，所以 stage 决策必须按"父目录+stage 名"而非目标名。
- 457 字符深目录仅扩展长度形式可达（plain `winerror 3`），扩展形式 mkdir/create/replace/unlink 全 OK；混合 extended-stage→plain-dest replace OK。
- 真实竞争错误（句柄占用）是 `PermissionError errno 13 / winerror 5`——与路径长度失败形态可区分，路径处理不改写错误类型。

## 验证

- RED：`logs/red-atomic-tests.log`（6F/4P/1S）、`logs/red-gate-tests.log`（5F/3P）——新用例在基线上真实失败。
- 短域（基线 owner＋新文件）：`43 passed, 1 skipped`，作者 14.02s（`logs/green-review-fixes.log`），审查方独立复跑 21.33s exit 0。跳过项＝POSIX 恒等测试（Windows 上诚实 NOT_RUN，不伪造）。
- 消费链集成：真实 `persist_projection`→`load_projection` 回环＋SHA 边界目录变体，真实 `SourceCatalog._atomic_write` 边界写；不直接调 helper 冒充。
- gate 真实 child：成功/失败（exit 1）/超时（124）三路径清理各一例。
- ruff（7 文件）/mypy（2 src 文件）干净。推送时 pre-push gate 正常通过（新 scratch 的一次真实走查）。

## 独立审查

真正独立 agent（未参与施工），两轮：

- 首轮 target `d04b72b2`：**FIX_FIRST**，5 项（P1 deny-ACE 候选因 `mkdtemp` 重试至 `os.TMP_MAX` 无限挂起；P2 finally-unlink 可用 cleanup 错误替换在途原始故障；P2 工区 `.w22-a-tmp` 残留；P3 `stage_dir` 对已扩展输入非幂等；P3 probe 文档少列一段）。审查方独立反例：8 线程同目标/异目标并发零残留、目标 255/276 字符写入成功、`stage_dir` 边界 238/239 精确、mixed replace 全过、既有 gate 断言全保留。
- 修复 `e8896a84` 后复审：**SHIP**。5 项全 CLOSED，以真实机制复验：`icacls /deny` 候选 0.000s 探测拒绝、0.001s 回落无残留、全败 RuntimeError 0.001s 逐名；真实无 FILE_SHARE_DELETE 句柄下原始 `ValueError` 保留＋note 可见＋目标不变；幂等与深写回归全过。

## Remaining（不阻塞，ROOT 集成时知悉）

- N1：`_probe_writable` 与 `mkdtemp` 之间理论 TOCTOU（相邻 syscall 间 ACE 翻转）；无实际触发路径，不为此换掉 mkdtemp。
- N2：deny-ACE 测试若将来移除 `_probe_writable` 会表现为挂起而非红——测试设计观察。
- N3：`add_note` 需 Python ≥3.11，`pyproject.toml` 声明 ≥3.10；`_bounded_process.py` 既有同样用法，属全局 floor 清理，不在本卡范围。
- N4：探测 rmdir 与 AV/indexer 极端竞态可残留随机名空目录，有界可接受。
- 消费方深目录局限：`_projections_root` 普通 `mkdir(parents=True)` 在目录 >247 字符会 `winerror 206`；共享 writer 已可深目录写，消费者 mkdir 不在本卡允许文件清单内未改，ROOT 决定是否另开卡。

## 给 ROOT 的集成提示

- `atomic_output(path, mode, encoding, newline, sync)` 签名与同目录 stage 行为不变；上层调用接口/wire/recipe 零变化；无新增 DTO。
- `_replace_closed_stage` 参数从 Path 变 str（仅私有函数，唯一调用方是 `atomic_output`）。
- ROOT 集成后按需跑 consumer/cache 签名域；作者不替 ROOT 签 M8 摘要或 RF 验收。
- 独审后仅文档提交（progress.md 终态＋本 handoff）；实现/测试的 reviewed commit 绑定 `e8896a84`。
