# W22-CWP-ATOMIC-IO ROOT independent reception — 2026-10-31

原交付结论：**FIX_FIRST**。冻结作者 HEAD `d19bda0453faaa10d58764a5fd233596f2fc7cb5` 的 READY_FOR_ROOT/SHIP 不能原样接收。本轮用真实 Windows 中性反例确认四个失败，另确认相对 scratch 根的选择错误，并静态发现 POSIX 测试路径错误。ROOT 后续明确授权在隔离 integration `C:/Users/郑曾波/Projects/_w22r` 修复；修复已完成、未提交，独立交叉审查 **PASS final patch scope**，状态为 **READY_FOR_ROOT_INTEGRATION**，不冒充 ROOT 最终发布签收。

## 版本与审查边界

- 原卡：`docs/plans/du11-source-closure-2026-10-18/harness_lanes/20261030/W22-CWP-ATOMIC-IO.md`，已逐项阅读。
- 作者树完全只读：`C:/Users/郑曾波/Projects/company-wiki-w22-atomic-io`；base `662f821e749bc221c8c308986e54e00465834332`；完整 diff 为 21 文件，修改范围全部在原卡允许目录。
- 作者实现 `d04b72b2bae9ea8442474997263dbed5f84d9f3a`，修复/声称 reviewed/tested commit `e8896a84fe5995829a7a84a6b01c5d71da95d513`。`e8896a84..d19bda04` 仅交接和 progress 文档，没有独审后改代码。
- 只读核对作者七个代码/测试文件，文件 LF SHA 全部匹配冻结 HEAD blob，也匹配交接哈希。原始/raw 与 LF SHA 完整列在本目录 `source-bindings.json`。
- integration 基点 `d8b61d8a1a6a4b22fb1b1fb42cbf9d49a6b2b948`。本 agent 仅改 `_atomic_file.py`、`_atomic_path.py`、`pre_push_gate.py`、`w22_atomic_probe.py`、`test_w22_atomic_paths.py`、`test_w22_gate_scratch.py`，新增 `test_w22_reception_regressions.py`。
- 未在作者树执行脚本/测试、未 checkout、未改索引；不写 M8、生产 config、公司原件、数据库、全局技能或 `.githooks/pre-push`。CodeGraph 作者树未初始化，未违背只读约束运行 init；先查询 ROOT 已有 CodeGraph 的 owner/caller 上下文，再直接读冻结 diff 和具体文件。

## 实际问题与处置

以下行号均指冻结作者文件；不是 ROOT 修复后的行号。

| ID | 级别 | 文件位置 | 中性反例与影响 | ROOT integration 处置 |
|---|---|---|---|---|
| A1 | P2 | `src/company_wiki/_atomic_path.py:49` | `openable()` 在 `len(given)<=259` 提前返回，忽略 cwd 长度。240 字符合法 cwd + 35 字符相对目标：stage 使用 extended 形式成功，但 replace 到普通相对目标报真实 WinError 3。原卡绝对/相对路径合同未满足。 | 用绝对路径预算决定是否扩展，短的有效表示仍原样返回。真实 Windows RED→GREEN。 |
| A2 | P2 | `src/company_wiki/_atomic_path.py:35` | Python `len(str)` 与 Win32 UTF-16 单位不同。含非 BMP 字符的真实目录中，Python 路径长度<259、Win32 单位>259，stage 创建报真实 errno 2。 | UTF-16 code units（surrogatepass）计长，stage 与目标共用预算规则。真实 Windows RED→GREEN。 |
| A3 | P2 | `src/company_wiki/_atomic_file.py:83` | 新增无条件 `original.add_note()`，声明支持 Python>=3.10 却调用 3.11 API。清理失败时，AttributeError 替换正在传播的原始 body 异常。原交接把它降为“别处已有”不能消除本卡新增退化。 | 有 API 时附 note；3.10 缺 API 时保留原始异常。通过当前解释器模拟缺 API 的中性 RED→GREEN；没有声称实际运行 Python3.10。 |
| A4 | P2 | `tools/w22_atomic_probe.py:239` | probe 确实建出 485 字符深树并执行四段，却用普通路径 `rmtree(ignore_errors=True)` 静默留下 owned sec2 树、exit0。与交接“probe scratch 自动删除”相矛盾。 | Windows 使用 extended cleanup，去掉忽略错误。真实 probe RED→GREEN；中性测试 finally 自清，最终 basetemp 另有 cleanup 收据。 |
| A5 | P2 | `tools/pre_push_gate.py:208` | TEMP='.' 按字面 1 字符被排在实际更短的绝对根之前，实际 scratch 深度随 cwd 增长；3.10 mkdtemp 保留相对目录时还可能与 child cwd=PROJECT_ROOT 不一致。候选函数中性测试真实 1F。 | 排序/去重前用无 I/O 的 abspath 规范化候选。1F→20P gate/中性回归，未改选测/超时/退出码/输出限制。 |
| A6 | P3 | `tests/unit/test_w22_atomic_paths.py:95` | POSIX 分支创建原生深目录后仍无条件用 Windows `\\?\` 形式读回，Linux 测试本身会读错路径。 | 仅 Windows 扩展读，POSIX 直接读 target；Windows 受影响用例1P。Linux 真实执行 NOT_RUN。 |
| A7 | P2 | `tools/pre_push_gate.py:244` | 仅排序候选不能保证 scratch有界。原实现接受所有可写深根，现有 conftest 再嵌 relocation 子目录可能更深，原卡短路径布局保证没有可执行条件。 | 按 ROOT 明确补充要求，Windows 绝对 UTF-16 root长度+14固定scratch reserve须<=现有60界；超界在probe前跳过，记录所需/预算单位；短候选有限fallback，全败明确报无法获得预算内可写scratch。创建后再核真实长度，超界先cleanup再continue。5个边界节点通过。 |

同目录 exclusive stage、关闭后 replace、原子替换的调用顺序、caller 负责 immutable/锁、`sync=False` 不额外 fsync、5/32/33 四次35ms有限重试均保持；短域已覆盖两 writer 并发、foreign stage 保留、body/fsync/replace 失败、编码/newline/BOM。没有引入第二 writer、跨卷 staging、全局锁或后台重试。`stage_dir()` 对绝对路径也经 abspath，使需扩展的合法 `..` 路径先规范化；未另宣称该额外变体已 Windows 独立实测。

## 原交付证据是否可复核

可复核：原卡、完整 diff、实现、三份新测试、probe 源码、`probe-final.json` 四段真实错误形态、UTF-16 保存的 RED/GREEN 原始日志、交接 JSON/Markdown、版本提交链、代码 SHA。作者绿日志明确 Python3.13.9，44 collected、43P/1S，且 POSIX 跳过诚实。

作者RED不能机械算成对应数量的production缺陷：atomic 6F含一个后来修正的newline测试误解、两个缺新leaf导入；gate 5F多数是新helper尚不存在，另有真实环境隔离断言失败。`red-new-tests.log` 更早还只有collection ImportError。保留其TDD历史价值，但不把未触达行为的收集失败充作长路径/错误合同验证。作者task_plan仍是pending seed，实际进展以代码、progress、日志分别核实。

不可独立复核：交接 `independent_review.reports` 仅一句“全文见本卡会话记录”，没有报告文件或可读会话标识/原文；reviewer 仅 generic agent 描述。五个首审问题关闭、真实 icacls 0.001s、8线程反例、独审21.33s、真实句柄 note 复验均只有作者转述，不能视作原始独审收据。`probe-final.json` 本身无 commit/解释器绑定，也无清理检查；本轮 A4 已实际反证其 cleanup 总结。**不把原交付 SHIP 自述当作本次验收依据。** 本轮 raw 日志和 final SHA 是新增独立接收证据。

## 本轮实际验证

所有运行均在 ROOT integration，宿主 Windows / Python3.13.9 / NTFS 实际边界；未改注册表、ACL/MIC 或机器设置。未启动模型、SDK、下载、收费任务或全仓测试。

| 证据 | exit | 实际结果 |
|---|---:|---|
| `red-counterexamples.log` | 1 | 4 failed，2.33s；相对路径、非BMP、缺add_note、真实probe清理四例全部触达语义。 |
| `green-regression.log` | 0 | 原W22六个短域文件 + ROOT四例：47P/1S，26.22s；真实 persist_projection→load_projection / SourceCatalog writer / gate成功失败超时child均保留。 |
| `red-gate-relative-candidate.log` | 1 | 相对TEMP候选1 failed，1.28s。 |
| `green-final-gate.log` | 0 | ROOT五例 + 原gate两个文件：20P，16.31s。 |
| `green-native-deep-path.log` | 0 | POSIX读回分支调整后，Windows受影响用例1P，0.36s。 |
| `green-bounded-gate.log` | 0 | 最后有界布局修复后，原gate两个文件+相对排序/超界拒绝/短根fallback/全深失败：19P，11.77s。真实child成功、失败、timeout和TEMP统一隔离断言均保留。 |
| `green-budget-boundaries.log` | 0 | 五个新gate边界：超界不probe、短候选fallback、无短根诊断、exact60成功、实际生成名超界后清理：5P，0.50s。 |
| `ruff.log` | 0 | 六个本轮变更文件，`--no-cache`，All checks passed。 |
| `ruff-final.log` | 0 | 最后七个本轮变更文件，`--no-cache`，All checks passed。 |
| `mypy.log` | 0 | 两个 primitive/path source 文件，no incremental/cache NUL，success。 |
| `source-bindings.json` | 0 | 8个 integration 文件 Python3.10 grammar parse PASS；7个作者文件冻结 blob LF SHA 绑定全部 match。 |
| `cleanup.json` | 0 | `.a-tmp` 初态不存在；本轮结束 extended rmtree 后不存在。 |

首次普通沙箱 pytest 因 integration 写权限仅产生4 setup errors，不算产品 RED；已走现有授权的正常宿主提权后运行同一命令。首次 ruff 默认 cache 写入拒绝，不算 lint通过；随后 `--no-cache` 真正0。只读 git status/diff 工作树命令返回“must be run in a work tree”，没有为此修改 git配置或索引；版本绑定改由只读 `git show` + LF SHA 完成。平台没有自动审批拒绝，只有普通沙箱权限错误。

本轮验证是分阶段的：47P/1S 后改 gate候选归一化和一个测试的POSIX读分支，分别按受影响域复跑20P与1P；ROOT追加有界布局根修后，仅gate受影响域19P及五个边界节点5P。没有把累计数字写成最终同一命令全域通过。原gate模块内 tmp_path夹具改为 `tmp_path_factory.mktemp('g')`，避免长node名占掉产品已存在的60界；没有降低成功/失败/timeout、退出码、环境隔离或清理断言。

## 未验证与保留边界

- Linux/POSIX 实际运行 NOT_RUN；Python3.10 实际运行 NOT_RUN（只有 grammar检查和缺 API 模拟）；UNC 只沿用结构单测，没有真实联网 share 挂载。不能声称跨平台全绿。
- 本轮没有重新改 ACL 测 deny-ACE。代码 `_probe_writable` 单次 mkdir 能拒绝稳定拒写；原单元模拟以及gate真实child域通过。原交接“真实icacls独审收据”仍不可查。
- probe 单次 mkdir 与 TemporaryDirectory 分配间仍存在权限改变的 TOCTOU，未扩大为无界重试；原 deny-ACE 单测缺独立进程deadline，若将来删 probe 会变挂起。保持为 P3 观察，建议未来有界进程回归。
- gate现在在Windows保证选出的scratch绝对UTF-16长度<=60；所有候选过深则诚实失败，不承诺任意深根都能成功，不扫描磁盘或改系统TEMP。沿用根conftest已有60边界（当前源码是210-150）；未改conftest、fast目标列表、timeout、退出码、输出上限、机器/ACL/MIC。
- `_projections_root` 自身普通 mkdir 的 >247 限制是消费者 owner边界，原交付已披露，未修改；深目录 primitive成功不能冒充所有消费链深路径已通过。
- 不接受原交付的推送/clean 状态自述为本轮实际验收；本 agent 不提交、不推送。ROOT委托的独立交叉审查已对最终字节完成，见下节；最终提交/发布仍由ROOT负责。

## 最终修复的独立交叉审查

ROOT委托未参与 ATOMIC修复的 `/root/w22_pdf_reception` 对最终补丁独立复审；本 agent 已实际读取原始报告文件，不只接收 agent聊天结论。

- 报告：`C:/Users/郑曾波/Projects/company-wiki/.planning/w22-w23-reception-20261031/pdf/atomic-cross-review.md`。
- 报告 raw SHA-256：`ec2d66f763d4ef8b3dc4e50437978524269e9902f2061afbe3ecb54fda2ab0dd`。
- 结论：PASS for the final ROOT patch scope；8个integration文件逐个独立raw/LF重哈希全部匹配本报告最终绑定。
- 最后gate字节下，独立复跑短候选fallback、exact60、实际name超界清理：3P / 0.31s；原始 `atomic-cross-final-tests.txt`、`atomic-cross-sha256.json` 同在pdf报告目录。
- 此前独立5个中性回归5P/0.36s及真实deep-cwd/TEMP='.' tiny child收据属于最后预算修复之前，未扩称为最终gate字节重跑全域。
- reviewer的 `.px-tmp` / `.px-neutral` 还原不存在；未修改本模块代码。Python3.10实际运行、Linux实际运行、网络UNC实际文件系统仍NOT_RUN，权限TOCTOU限制保留。

## 最终 raw/LF SHA

完整源文件、原始交付冻结文件、测试和 raw 日志 hash 均在同目录 `source-bindings.json`。其中本轮改动的最终字节：

| 文件 | raw SHA-256 | LF SHA-256 |
|---|---|---|
| `_atomic_file.py` | `cbe20ea2066aeba85fdb9c47cf66ae66134fb6b2ec0d8e28e0433c48139d5453` | `13a80a2e65b81bd05f87d79b317cd4da581563a4e97cba139ca45d48a52cb305` |
| `_atomic_path.py` | `62d8f4e3c7163c5a1972efc6e659f5bb1ec94a2b30a4a74a39dfecc4eb1e0f86` | `b3cc1ebfc6f3b899a5b4693978c3f1f697436c422f5c74dc40a94a447428c372` |
| `pre_push_gate.py` | `b0d0c42f4e535980cbefb9cd81c03916cf5959bca08b6cf3261d44077adc59e6` | `db5d9e7378d0145abbdfd84bb2710d8e4940cc096ab65cffc26a79a60a5cd371` |
| `w22_atomic_probe.py` | `cdeabd57f9118ec2510436eff4a5ba33a979e4b0a0b937b0c8d25b6c1ac7d3d7` | `372fbbb28424f28c4e9da80459e770baf0fecf59ba1eab5b8eb219241356fcfd` |
| `test_w22_atomic_paths.py` | `23e296755896d0e9083d042f7fd1fadaeec615ceac1d8ab1efd9ee337dfe75a5` | `5e57db7de11caa8f5d99634db1edd9f6f98db7d1fa982b192284210375062afb` |
| `test_w22_gate_scratch.py` | `7c5e1fde503c782ecdf893fc0d22174fe0b2dda86d333e4bb94212f743c5970f` | `8f66e90cf647b4d10cc1528c81734107a557f2f2ccb45725e146158c58853920` |
| `test_w22_reception_regressions.py` | `a4102b187a32d7029789fa584bed31e3fa7e78e5a05aabb801623046aa95548f` | 同raw |
