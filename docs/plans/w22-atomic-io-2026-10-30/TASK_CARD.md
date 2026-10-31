# W22-CWP-ATOMIC-IO：共享原子写入与深目录可移植性

状态：READY_TO_DISPATCH；独立施工，不等待 ROOT 的 M8。只在最终大节点独审，不增加每小步许可。

## 立即启动的信息

- 仓库：company-wiki。
- **工作目录：`C:/Users/郑曾波/Projects/company-wiki-w22-atomic-io`**。
- 分支：`codex/w22-atomic-io-20261030`；基线 `662f821e`，从本工区 `git rev-parse HEAD` / setup 取得完整 SHA。
- `PLAN_ID=w22-atomic-io-2026-10-30`；`PWF_PLAN_ROOT=docs/plans`。
- 本地唯一计划：`docs/plans/w22-atomic-io-2026-10-30/`；先读 `TASK_CARD.md`、task_plan/progress/findings。ROOT 总工区只读。
- 输出：本工区 `delivery/w22-atomic-io/handoff.md` 与 `handoff.json`。
- 解释器优先已安装宿主 `C:/Miniconda/python.exe -B -X utf8`。环境/沙箱写入差异先定位，可用平台支持的正常宿主执行，不改 ACL/MIC、不绕平台拒绝。

## 为什么做，什么已经确认

ROOT 接收 W21 时独立复现：同一 staging 名，在 NTFS/LongPathsEnabled=0 下 254 字符能创建、270 字符报 FileNotFoundError/errno2。原测试在 persist_projection 保存夹具时失败，尚未运行到语义断言。

共享 `src/company_wiki/_atomic_file.py::atomic_output` 用 `tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+'.', suffix='.tmp', delete=False)`；目标 basename 又复制进 staging 名，深目录放大路径。`_replace_closed_stage` 仅对 Windows 5/32/33 做最多4次、共35ms backoff。`tools/pre_push_gate.py::_run_pytest_gate` 把 TEMP/TMP/SQLITE_TMPDIR/basetemp 都放 PROJECT_ROOT/cwpp-*；工区名增长也会触发。

两个贡献 owner 要一起处理：修存储 primitive 的真实路径兼容；让测试临时布局不随 checkout 深度任意膨胀。不能只给 projection 加拒绝错误、移动一个测试、删断言或关闭 hook。

只读依据：ROOT `docs/plans/du11-source-closure-2026-10-18/review/w21-root-reception-20261030/README.md`、`review.md`、`review.json`；必要原作者证据在 `C:/Users/郑曾波/Projects/company-wiki-w21-pdf-runtime/delivery/`，只读，不运行作者脚本。上述 ROOT 接收资料已在基线提交，不需读在途 M8。

## 独占写入边界

允许修改：

1. `src/company_wiki/_atomic_file.py`。如确有必要，可新增一个 `src/company_wiki/_atomic_path.py` 私有 leaf；不得创建第二套 writer。
2. `tools/pre_push_gate.py` **只改临时目录选取/清理/错误诊断**；保留选测、FAST_CONTRACT_CASES、超时、退出码与输出上限的原政策。
3. `tests/unit/test_atomic_replace_contention.py`、`tests/unit/test_pre_push_gate.py` 中与该边界相关的测试；新增 `tests/unit/test_w22_atomic_*.py`、`test_w22_gate_scratch.py`。
4. 本卡计划、`delivery/w22-atomic-io/`。可新增专属小 probe `tools/w22_atomic_probe.py`。

禁止修改：`.githooks/pre-push`（ROOT 有外来 mode WIP）、CI workflow、changed_unit_tests 选测规则、生产 config、原件/数据库、narrative/*/cache/parser/selector/actor/QA/LLM；尤其不改 M8 文件或 PDF runtime/worker/env、`tools/pdf_runtime_deployment/`、别的仓库、共享 PWF、全局技能。上层调用接口与 wire/recipe 不因本任务变化。

## A：调查并冻结行为（无需 ROOT 中间签收）

1. 核对 branch/base/status，解释已知计划 seed；读 AGENTS、共享 writer 的 CodeGraph callers/impact 和现有测试。文件较多时只读受影响 owner，不重跑全仓。
2. 分开复现“目标自身合法，旧 staging 额外变长导致失败”和“目录自身已经超过宿主原生路径支持”。记录 Unicode/ASCII、目标/stage 的字符长度及 winerror；不依赖主机注册表切换或全局长路径开关。
3. 冻结成功/失败合同：同目录 exclusive stage、关闭后 os.replace、原目标成功前不变、失败不丢原目标、不删其他并发操作 stage、不改变锁/immutable 判定责任。模式/编码/newline/sync/异常保留。不能靠 cross-volume move 或全局 temp stage 换取成功。

## B：先测试 RED，再修共同 owner

1. 用短 ASCII basename 的独占随机 stage 消除重复长 basename；依据实际平台能力决定是否在 primitive 内封装 Windows extended-length 路径（不是预定必须实现它）。要覆盖绝对/相对、盘符/合法 UNC 与非 Windows；路径表示不向上层 SourceRef、报告或公开 JSON 泄漏。不可把真实 PermissionError 误认为“路径太长”。
2. 只属于该次调用的 stage 负责清理。异常、flush/fsync、replace 失败与有限 contention retry 都不掩盖最初故障；保持已有并发/同步策略，不能加新全局锁/后台重试/权限门。
3. gate scratch 用实际可写、路径有界的调用专属根，保留所有 child temp env 的统一隔离；不能重新依赖可能不可写的 host TEMP，也不能硬编码用户名或只对本机目录成立。候选不可写时给出可解释结果/有限 fallback，不无限探测。仅验证所需路径，不扫描整盘。
4. 临时目录 lifetime 覆盖 child，从成功、失败、超时路径全部清理自己的文件/进程；不要改 `_bounded_process`、全局 pytest conftest 或机器设置。

## C：测试包、真实小型 E2E、独立审查

最低覆盖按风险分组，不机械凑数量：

- 单元：wb/w+UTF8/newline；目标旧字节；writer body/flush/fsync/replace 失败；失败原目标不变；并发两个 stage 互不删除；已有 Windows5/32/33 有界重试；其他错误立即传播；sync=False 不额外 fsync。
- 路径：深 Unicode 目录＋长 basename；刚好超过旧 staging 界但目标有效；深目录自身支持与否要分开记录。Windows 做实际 NTFS probe，Linux 做原生路径与文本/并发回归，平台不可运行项明确 NOT_RUN，不伪造另一系统通过。
- 集成：用真实已有 persist_projection/derived artifact writer 保存一个小 fixture 再读回 SHA；不调用模型/SDK、不构造新研究报告。这个用例证明共享路径实际被消费者用到，不直接调 helper 冒充整链。
- gate：保留同一 fast 目标/参数，验证新 cwd 深度下临时布局；一次轻量真实 child 和错误/超时清理用例足够。不让测试再起完整 pytest/全仓/整 SDK。不能增宽 daily push 或放宽原断言来制造绿。
- 测试资料仅在本卡 owned TMP。前后记录初态；结束删除测试新增文件/DB/派生物，恢复 sentinel/不存在状态。不要恢复完整备份演练，不清理他人 historical .planning。

示例短域命令（根据新增文件补齐，不跑全仓）：

```powershell
C:/Miniconda/python.exe -B -X utf8 -m pytest -q --tb=short -p no:cacheprovider tests/unit/test_atomic_replace_contention.py tests/unit/test_pre_push_gate.py --basetemp=.w22-a-tmp
```

`--basetemp` 必须确认不存在或确属本任务；probe 自己覆盖长路径，不能把所有测试 basetemp 设成长目录再陷入初始化故障。保留 RED/修复/最终绿日志和实际耗时。lint/typecheck 针对受影响文件，正常 commit/push hook，不绕 hook，不为本卡增加 CI job。

**交接前必须调用真正独立审查 agent**：逐条对原卡/差分/调用边界/上述测试/Windows实测/清理审查，独立补反例。修完所有范围内问题，再复审最终代码。不能把剩余自身缺陷推给 ROOT、作者自签或拿用例数量代替审查。A/B 不需要人工审查，只有这个交接大节点。工具/模型额度不可用就记录 REVIEW_NOT_RUN，不虚构签收。

## 交付协议与完成标准

不新增产品 DTO；保留 `atomic_output(path,mode,encoding,newline,sync)` 行为和同目录 stage。新路径细节属于 leaf 内部。ROOT 集成此包后再跑必要 consumer/cache 短域；作者不替 ROOT 签 M8 摘要或 RF 验收。

`handoff.json` 用 `schema_version="harness-handoff/1"`，必需字段：card_id、status（READY_FOR_ROOT/PARTIAL）、workdir、branch、base_commit、implementation_commits、tested_commit、reviewed_commit、code_files（path/raw_sha256/lf_sha256）、requirements（逐项 implemented/tested/partial）、tests（命令/exit/耗时/证据路径）、real_windows_probe、consumer_integration、independent_review（reviewer/target/reports/open_findings）、cleanup、compatibility、remaining、pushed_to_remote。未知用 null/NOT_RUN，不能编 PASS/0。独审后只允许文档提交；若改代码必须补相关测试和独审绑定。

正常提交并推自己的分支；不合 master、不安装全局副本、不提交临时 PDF/env/SDK/大日志。只提交小型稳定 fixture 和紧凑证据（大日志仅本地留路径/SHA）。最终实现/测试/清理/独审均完成才 READY_FOR_ROOT，然后 STOP，ROOT 接线。
