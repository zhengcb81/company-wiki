# F4-ET-BATCH-REPLAY · 批量电话会逐项复原

状态：可独立启动。工作目录 `C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts`。核对当前 `main` 与同版远端，从包含 `f2512176` 的干净源码起步。已有工作区正在写时，先用本仓短路径独立 worktree。先读本仓的 `docs/plans/feedback-loop-2026-11-17/F4-ET-FAILURES.md` 与交接中的“逐公司逐期次”余项。

## 要解决什么

普通 `scraper.py` 已建立 recorder。批量路径的逐项记录仍主要靠 `_record_entry` 写日志和最终 `run_manifest.json`。某公司某期读取失败而整批正常退出，或在下一项硬停时，反馈端无法从普通入口查回已经完成的失败。把逐项观测接入现有 ET recorder、收件箱及查证命令。已有 `fetch_batch_cli` 的机制优先复用。

基线复现用真实 scraper supervisor、子进程和本仓离线 HTTP launcher。两期都返回 HTTP 500，显式 OUT 和默认目录模式各自退出 1。各有两条 `provider_error/provider_http_500` 原记录，两次夹具请求，反馈文件数为零。两期都返回 HTTP 200 空列表的正常对照，退出 0、两项 `not_found`。可复用 `tests/test_batch_runtime.py` 的 `run_main` 和 `tests/test_retrieval_runtime.py` 的 `fake_spec`。无需凭据或真实供应商。

## 写入边界和接口

- 只改 ET 的 scraper、已有本仓反馈实现、相关测试和本仓 F4 子计划。FF、CWP、总控协议和真实电话会目录由各自 owner 维护。继续用 ET 的现有 provider 与计量接口。
- 在每次可能派发的请求前写稳定的原 run、attempt、公司和期次或源项目标识，并绑定已分配的 request ID。每一项完成时立即保留原阶段、结果、脱敏原因链、是否派发及原计量状态。完整原因仍经本仓明细引用冷读。抓取、解析、TXT 保存和名单发现按真实阶段区分。正常无电话会是合法空结果。
- 同一批次的 A 期失败不能被 B 期成功覆盖。进程强退后，经 ET 现有公开 owner 命令 `src.feedback_owner` 或已公开的本仓等价入口查同一原尝试。明确未派发可报 `not_applicable`，原 provider 费用未核到继续保留 `unknown`。总控只收已有 `feedback-observation/1`、`evidence_ref` 和 ET 自有侧车。恢复期间的 provider 请求及新增付费次数均为 0。
- 业务原 stdout、退出码、manifest 及原语言 TXT 在原来的语义下继续工作。反馈旁路异常或缺少可选元数据不影响业务返回；确因门禁拒绝时按原码留痕，分诊先审视该门禁。

## 先写测试，再修复

1. 把本仓既有离线 provider launcher 指到新的短临时根，以实际 `scraper.py` 子进程走 FMP 两期。让第一期明确失败、第二期合法无命中或成功。使用常态入口且不传 `RESEARCH_FEEDBACK_OUT`，从第二进程按第一期原身份查失败，验证两期和整批的原始结果分别一致。
2. Fool 覆盖发现后逐项抓取及 `--list` 的失败与合法空结果；验证同外层结果的两个不同原因能冷读区分。模拟预算在发出前耗尽及在已开始项中断。使用现有 F4 恢复查证入口，比较事件、真实子进程退出、调用计数和原用量。
3. 在第一期的终态落盘后、下一期尚未完成时硬停一个隔离子进程。新进程只能按原身份查到已完成失败和未确认项。双次查询和重复投递均不新增业务调用。再用一个非公司特判的正常样本验证。
4. 只跑本仓受影响回归和以上真实子进程验收，临时根恢复原样。交接前由一名未写实现的独立 agent 按最终源码复跑关键正反例，发现的问题全部修完并复审。

## 交接

更新本仓 `docs/plans/feedback-loop-2026-11-17/` 的下一步和独立交接。给出工作目录、基线与终版源码 commit、执行命令、按实际启动运行计数的分母、每项是否可定位及是否可离线复现、真实退出码、脱敏明细引用、费用未知和强停证据、复跑调用数、清理和独审记录。提交推送本仓正式线。ROOT 接收后用现有总控命令做一次隔离组合验证。
