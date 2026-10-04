# MeetingConverter：CI 零任务根因与快速可靠门

Status: ACCEPTED / MERGED TO MASTER / PUBLISHED / MAIN CI GREEN
Card date: 2026-10-04
Target repository: C:/Users/郑曾波/Projects/MeetingConverter
Owner: isolated MeetingConverter harness; company-wiki MAIN only accepts the handoff.

MAIN 已验收并快进发布 `master@8a33a7f`，新主线 CI 一个 job 实际跑测试并成功，22 秒。见 [MAIN 验收收据](results/meetingconverter_ci_acceptance_2026-10-04.md)。以下为原施工要求，不重新派发。

## Goal

查明并修复 MeetingConverter 的 CI 是否仍存在“workflow 失败但 jobs=0、实际测试没有运行”的问题；让每次代码 push 都执行一组明确、快速、真实的本地适用测试。目标是一个 Actions job 在 120 秒左右完成；若当前远端状态已修复该问题，先证明现状，不为产生代码改动而改工作流。

已验收的只读盘点报告记录：HEAD 3c0b053 的一条历史 GitHub Actions run 失败且 jobs total_count=0，因此当时没有测试步骤可供判断。该收据没有查明 run 之后的最新状态；开工必须重新核对。

## 工作目录与写集

在 MeetingConverter 仓库建立独立干净 worktree/分支；不要在 company-wiki、StockQAbyLLM、invest-quick-scan 或其他仓库操作。

允许写入：

- .github/workflows/ci.yml
- 仅在需要且可由当前仓库现有工具验证时，增加 CI workflow 合同测试；新测试只能放在独立 CI 配置测试文件中
- docs/implementation/reviews/ci-fast-gate-2026-10-04/HANDOFF.md

禁止修改应用 src、业务测试、依赖锁文件、配置密钥、PWF 的其他阶段、任何公司/音频/转录资料。

必须原样保留审计报告中的 tracked .coverage（53,248 B）、ignored output/、config.json、所有未跟踪和 ignored 内容。不得清理、还原、重命名、重新生成或暂存这些项目。

## 开工核查与实现步骤

1. 记录当前 branch、HEAD、live origin/master、tracked/untracked/ignored 状态；只读取 CI 日志和工作流，不覆盖 .coverage。
2. 查询远端最新 Actions run 与 jobs/steps。确认 historical jobs=0 是配置触发条件、workflow path filter、语法错误还是其他根因；不得把“YAML 能解析”当成 CI 通过。
3. 如果最新 CI 已有稳定非空 jobs 且实际测试运行，则交付根因分析与无需改代码的结论；不得为了制造施工量更改工作流。
4. 如果问题仍存在，只在允许写集中修改。保留对有效业务行为有用的快速测试，优先去掉重复、易抖动或慢速 coverage 上传；不得无证据删除业务回归测试。
5. 对 push 和 pull_request（若仓库当前支持）确认至少一个 job 实际运行；脚本失败必须使 job 失败，不能以 always()/continue-on-error 把测试红灯伪装成成功。
6. 单 Python 版本优先；除非真实兼容性风险有证据，不增加版本矩阵。不得新增包管理器或全仓 coverage 作为每次提交门。

## 测试与完成条件

- 用当前 workflow 相同的 Python 版本和测试选择器在独立 worktree 运行。
- YAML/工作流静态验证使用仓库已有工具；不要新增外部依赖仅为测试 YAML。
- 记录每个本机测试包时长，CI 端用新 push run 的 jobs/steps 确认它确实运行了测试，并报告总时长。最终状态须是新 run success 且耗时不超过 180 秒；若 GitHub runner 基础安装导致无法达到该时长，列出 step timing 与唯一瓶颈，不删除更多测试凑数。
- 只在确有代码变化且本地选择性测试通过后提交并推送该专用分支；不合并到 main。
- handoff 必须包含 base/head SHA、根因证据（run URL、job/step）、改动路径、确实执行的测试与耗时、最新 run URL/结果/总时长、保护文件状态确认、未解决事项。

此卡无外部公司数据、模型、API 或成本依赖。不得读取或操作 invest-quick-scan。
