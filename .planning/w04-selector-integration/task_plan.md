# W04 selector：并线准备（只读）

## 目标和范围

从旧工程工作树 HEAD `35a9a64591169bf217f05e87aba633dc4204033a` 的已冻结 selector 工作，形成当前 canonical master `d75f0d42` 的精确三方接收清单和实施步骤。此包只调查和编写计划；不修改产品、Git、配置或原件，不重跑 375 项或六原件。

唯一写域：`C:/Users/郑曾波/Projects/company-wiki/.planning/w04-selector-integration/`。不覆盖已有共享 PWF。

## 阶段

| 阶段 | 状态 | 交付 |
| --- | --- | --- |
| 1. 固定 base/main/frozen target 与写集 | complete | 25 行三方字节 SHA；18 接收、4 G2 延后、3 CI 保留主线 |
| 2. 梳理业务分组/0.8/阶段断言依赖和验收出处 | complete | 8 源 / 10 测试；27 个直接导入条目；验收链与精确出处 |
| 3. 汇总三方接收与一次集成复验步骤 | complete | integration-manifest.json、下述 ROOT 实施步骤 |

## Next Step

本线程 STOP。ROOT 在当前 master 的干净新工作区，按 integration-manifest.json 接收 18 文件并做一次集成批次。此文档的准备已完成，接收/测试/commit/push 尚未由本线程执行。

## 约束与边界

- semantic7 产品依赖原生完整组、公共 selector 默认 0.8、显式旧版本与阶段断言；不能只孤立复制 budget。
- CI/testscope 已被主线吸收的同内容改动排除；G2 配置单列，不能混入 selector 接收。
- 预留最低覆盖配额保持；质量带在普通/预留各自通道内部排序。
- 已有工程及真实数据证据复用；只在合并节点建议一次普通集成测试，无小节点人工审批。

## Errors Encountered

| 问题 | 处理 |
| --- | --- |
| CodeGraph context 初次参数为 query，不是 task | 修正为 task；索引未含该工作树 WIP，已知文件直接读取 |
| 沙箱内只读 Git 无法进入外部旧工作树（Permission denied） | 使用已授权只读审计的沙箱外执行；仅 Git status/rev-parse/ls-tree/cat-file，不写 index |
| 旧 WP02 未使用假定的 manifest.json 文件名 | 改读实际 task_plan/progress 与已知冻结文件，不制造缺失证据 |

## 接收结论

- selector 写集：8 个源文件 + 10 个测试文件，共 18。逐行完整 SHA 与动作在 `integration-manifest.json` 的 `rows` 中，`package=selector_accept`。
- 18 行当前主线内容均等于旧 base，无三方内容冲突；5 个依赖源及既有测试的冻结仍逐字节匹配早期 semantic freeze，其余 7 个产品以 Phase2 freeze 为准。
- G2 的 `config.py`、configured CLI、两个配置测试共 4 文件，单列 `g2_configuration_deferred`，不复制。
- `.github/workflows/ci.yml`、`tools/changed_unit_tests.py` 当前 main 已含旧 target 内容，排除。`test_ci_push_selection.py` 当前 main 比旧 target 多 6 个 OCR 资源回归正控，保留 main，不复制旧文件。
- 主线 OCR/normalization、acquisition、scope、scanner、portability 新改动全部保留。接收文件不与这些写集重叠。normalization 新的隔离 OCR / deadline 注入保持当前接口，selector 不修改它。

## ROOT 的实施步骤（一次接收节点，一次集成节点）

### 1. 创建并固定干净接收工作区

优先使用管理工具 `create_worktree`，`allowAsync=true`，`name=w04-selector-integration`，`ref=d75f0d42e0fc11caa50d5030d16fa238c0e02d55`，后续命令在返回的 workspace 运行。不要在旧 22 WIP 混合工作树中 reset/clean 或整树提交。新 worktree 不复制旧未提交文件。

若 master 已比这里记录的 commit 更前，基于最新 master 建接收树；仅对本 manifest 的 18 文件重算 base/main/target 三方比较。当前结果无冲突；新的主线内容不得被旧 target 静默覆盖。这是一次接收操作的常规三方合并，不是新的人工许可。

三方定义：

1. BASE：不可变 Git blob，commit `35a9a64591169bf217f05e87aba633dc4204033a`。
2. OURS：当前 main，不是旧混合树的 HEAD 或共享工作目录未提交文件。
3. THEIRS：manifest 的 `pending_worktree.sha256` 对应旧树文件。来自全部 18 文件联合包，不能仅接收 Phase2 7 文件。

`old_base`/`current_main` SHA 是 Git blob 原始字节；`pending_worktree` SHA 是冻结工作树原始字节。CRLF/LF 差异仅在源/测试的三方比较使用单独 normalized SHA；不对原件、历史证据做归一化。

### 2. 一次应用精确 18 文件联合包

一次读取 manifest 并整体核对 THEIRS 的 18 文件 SHA：原有产品未变化才能复用原验收。当前 18 文件 base/main 无冲突，因此按 `ADD` 或 `REPLACE_EXACT_FROZEN_WORKTREE_BYTES` 复制完整文件；父目录不存在时只创建该源/测试目录。不得 glob 整个 src/tests/scripts，也不得把所有旧 WIP 作一个提交。

如果未来某行 OURS 与 BASE 有真实内容变化，用同一 BASE/OURS/THEIRS 三方合并该行，保留 OURS 非冲突改动；记录实际接收字节 SHA。若合并改变了阶段断言源，下一节同一测试批次加两个 stage 模块即可，不开新小节点审查。

接收的必需链：

`narrative_evidence` 公共版本解析一次、默认0.8 → 原生业务/上下文组 enrich → 共用 `narrative_stage_assertions` → finalize 的完整组 signature → budget 的有界数值/主体/阶段 novelty 与质量带。成员原文/locator/span 成本、硬cap、旧路由和省略 policy 的 legacy 均保留。

排除 G2 4 文件和 CI 3 文件；不覆盖旧 `.planning/w04-wp02`、root-selector、novelty 的计划、失败记录或任何共享 docs/PWF。独立准备包和最终集成结果只追加到本包。既有测试 fixture/helper 全部已在 main，无新原文资料写入。

### 3. 只做一次普通集成测试批次

在新接收树根目录执行，下例 `<独占短临时目录>` 由 ROOT 创建在自己的接收工作区 `.tmp/w04-selector-<uuid>`，必须记录其初始缺席：

```text
python -X utf8 -B -m pytest -q
  tests/unit/test_w04_selector_version_dispatch.py
  tests/integration/test_w04_semantic_budget_finalize.py
  tests/integration/test_w04_novelty_finalize.py
  tests/integration/test_w04_quality_band_budget.py
  -p no:cacheprovider --basetemp <独占短临时目录>/pytest
```

上述换行为排版，实际命令一次提交全部参数。使用现有 `tests/conftest.py`：自动绑定本树 src/scripts、隔离真实凭证、阻断真实 socket，不改生产配置。运行有界短任务，预期秒级，硬截止 90 秒；超时留实际失败，不能用跳过断言制造通过。

只有三方冲突导致实际修改 `narrative_stage_assertions.py` / 阶段业务组时，在**同一批**加 `tests/unit/test_w04_stage_public_assertions.py`、`tests/unit/test_w04_stage_predicate_scope.py`。当前无冲突无需追加。

四模块检查点：公共 default0.8/显式旧路由、一次版本绑定；实际原文 whole-group/span cost；数量/主体/计划与实现/否定新事实不会因软重复被降级；普通/预留各自质量带和既有最低覆盖配额。不是所有通道全局质量排序。

既有 10 模块 375PASS、原件六份 fixed checkpoint PASS、6 个 legacy 有序 package 指纹与 raw SHA、17 独立小探针、4 完整组主体归属核验均沿用，不重复完整原件/自定义探针。若普通集成出现具体失败，沿该失败定位根因，不复跑无关套件。

测试日志留在本独立计划包。退出后仅删除本次独占短临时目录，先校验 resolved 路径在该 worktree 的 `.tmp/` 内、basename 等于本次创建名，再恢复初始缺席。不能恢复/删除共享 TEMP、原件或其他 agent 的 pytest 目录。

### 4. ROOT 集中提交、并主线、推送

只 stage manifest 的 18 个源/测试路径和 ROOT 实际更新的本独立计划记录，不能 `git add -A` 混入其他 WIP。工作树复制时核对 exact THEIRS SHA；Git 暂存的文本可能按既有 `.gitattributes`/autocrlf 归一化，用 manifest 的单独 LF normalized SHA核对源/测试，不能把换行差异误判为新业务改动，也不能改原件字节。

集成批次通过后正常 commit，再由 ROOT 快进/接收该集中提交到 master 并 push。沿用既有本地 hook/CI；不新增人工签收、canary、审批 JSON 或重复重验门。若主线期间出现别的提交，仅对 18 文件的真实冲突作三方处理并针对具体改变复验。

本节点完成后 ROOT 回填实际接收 commit、远端 commit、单次测试日志与 scratch 恢复结果；然后回主线 G2 configured 三 provider 原语言摘要及真实 RF 消费。摘要/研究质量尚未评估，不能因本包接收称整个项目完成。
