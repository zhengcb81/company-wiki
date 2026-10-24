# 三包接口和交接约定

总控母计划 `du11-source-closure-2026-10-18` / `docs/plans`。本文件与对应卡一起构成施工说明。新harness只维护自己的子PWF，不改母CURRENT_STATUS/task_plan/progress/findings或本目录。

## 1. 固定输入与责任

| Owner | 写范围 | 输入 | 不能代签的结论 |
|---|---|---|---|
| ROOT | CWP业务源码、母PWF、真实campaign和费用账 | 当前annual14及公司资料 | 仅工程绿不能证明完整内容 |
| W13 | CWP `tools/pre_push_gate.py`、`tools/changed_unit_tests.py`、`.githooks/pre-push`、卡指定调度测试与子PWF | CWP `a31300a70215319e6bcf3a03d32b2882bdf1aeaa` | 本地快速绿≠全量绿/CI成功 |
| W14 | RF既有跨仓E2E及专属support/测试/子PWF | RF `599d17b89d8baee42ce203747496731ace2d0148`；FF `7f6a9268da90281c28b55d437860bc2d2b60106e`；CWP上述冻结版本 | 合成夹具真实代码E2E≠真实公司内容/真实下载通过 |
| W15 | Audit专属工程export/replay工具、夹具/测试/子PWF | Audit `af255d4161f9ea19748f35af45447584a0bdbeee`；已有W10测试合同 | 可搬迁、可回放≠阅读质量或公司PASS |

W14输入中的commit是复现版本证据；缺对象/依赖输出具体 `environment_unavailable` 和失败状态，不创建“需人工登记hash才能执行”的新许可门。不得改历史源码pin后冒称重跑过。W14用 `git archive`/等价读取冻结tracked文件部署到自己scratch，只展开运行必需源码/无密钥资源，排除`.planning`、旧output/run、生产原件；逐仓实际执行路径/commit写收据，防止editable install或PYTHONPATH指向别处。

跨包唯一交接是Git提交与固定delivery文件，无共享可变任务库。W13不写RF/Audit；W14不写CWP/FF；W15不写RF/FF/CWP。真实来源缺口归ROOT；其他仓库、Dayu、IQS、StockWiki、ET及安装技能本批均无写范围。

## 2. A/B/C三个大节点

**A：调查与冻结测试期望。** 读本卡及实际源码，记录基线、当前失败/时间和接口；先写反控测试。A结束自行继续B，无需ROOT或用户额外签收。

**B：实现与集中验证。** 找共因改既有责任层，避免公司名/目录/旧hash特判。小模块有明确输入/输出/错误；复用现有生产合同。每次相关测试够用即可，不每个小补丁跑全仓。

**C：完整验证、独立审查与修复后交接。** 按卡一次集中运行相关单元/集成/E2E及规定完整检查。必须实际调用独立agent，审查需求完整度、最终diff、模块化/泛化、正反例、错误路径、清理、代码真实调用和测试是否掩盖缺陷。独审不得由实现者改名自评；报告保留审查者角色、实际命令、发现和关闭证据。全部内部发现修完并复审最终改动。发现真实跨边界缺陷按下节处理，不伪造全通过。

## 3. 测试与空间约定

- 测试仅在包自有临时根运行；已存在的根放sentinel，记录初始相对路径/字节hash，分配独占子目录。成功/失败/timeout/异常均恢复；测试前原本没有的下载物/DB/缓存删除，原有文件不改。
- 删除或移动前解析绝对路径，确认在本次拥有的测试子根。禁止 `rmtree(work_root)` 清空用户给的非空父目录；拒绝复用非空输出目录或使用独占attempt，不能覆盖历史结果。
- 离线测试阻止外网和模型/供应商调用并记录尝试数；本机loopback只在明确测试使用。Windows沙箱网络限制单列为执行环境问题，不删除断言或换成假响应冒称生产通过。
- 子进程使用当前解释器/显式代码根，收据记录运行来源；不读/打印key，环境清洗只在子进程副本中进行。生产配置无写入，夹具最小、无真实secret。
- 冻结fixtures可用少量已跟踪公开测试材料或中性有效PDF/TXT；标明synthetic与real-source excerpt的差别。不要复制公司原件或旧临时湖。
- 新交付≤16MiB为控制膨胀目标，不是增加人工许可；超出要列必要性和去重结果。只保留最终必要证据，完整旧失败日志保留原处而非复制多份。

## 4. 固定交接

W13：`delivery/w13/handoff.md`、`handoff.json`；W14：`delivery/w14/...`；W15：`delivery/w15/...`。统一使用同目录[handoff.template.json](handoff.template.json)的现有 `r1-harness-handoff/1` 文档格式，可加字段，不引入生产schema。

最少内容：逐需求PASS/FAIL/EXTERNAL_LIMIT/NOT_EXECUTED及证据；base/start/最终分支和commit；changed_paths；实际测试命令/退出码/数量/时间；真实CLI收据；测试目录前后恢复；新增字节数；独审原报告及全部发现修复/复审；ROOT下一步和已知边界。无remote如实记录，不虚构CI；未执行/超时不能填PASS。

先提交实现，再独审最后一次代码；以 `reviewed_code_commit` 加被审产品/测试/fixture文件SHA绑定。之后仅交接文档commit可改变HEAD，不必制造循环签收；再改被审代码则对差异补审。最终交接前确保新增源码/测试已commit；只stage自己的明确文件，不用 `git add -A` 带入他人WIP。可正常推自身codex分支，不合/推主线、不force-push、不安装技能；ROOT统一并线和发布。

`interface_requests`只列真实跨边界缺陷：触发输入、预期/实际、原始错误、复现命令、建议责任层、受影响需求和已完成不依赖部分。包内可修问题应直接修，不把它变成等待批准。若该外部缺陷阻止卡的核心验收，交接标 `INCOMPLETE_EXTERNAL_BLOCKER`，不能用 `COMPLETE_WITH_EXTERNAL_LIMITS` 隐藏核心未完成。

## 5. 当前授权和预算

会话已授权本批规划、工程改造、测试、commit/push及CodeGraph必要初始化；无需逐文件/逐步骤再次问权限。外部harness本批0收费调用/下载，故不争用母账；ROOT实际模型任务仍按 `config/resource_budget.yaml` 的累计10M tokens/USD20与公司软目标执行，unknown不清零。不改模型表、凭证或预算配置；平台审批不能靠命令改写绕过。
