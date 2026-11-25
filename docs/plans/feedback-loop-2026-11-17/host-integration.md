# ROOT 实施细则：接真实 agent 与 P1 消费者

本页由 ROOT 实施，外派作者只交本仓专用观察和修复技能。起点是已通过的[离线控制端](f1-acceptance.md)。终点是交付一份真实公司任务后，发生的问题自行进入责任仓，正确版本回到原消费者，并经中断恢复。负责工程修复的作业和公司采集、模型调用有不同的作业 ID。

## 1. 选定可恢复的宿主并接入

已通过[真实 Codex 与 FF 中断演练](f3a-host-acceptance.md)和 [F4 首条闭环](f4-acceptance.md)。使用 `python -m tools.feedback_loop.local_host --config SETTINGS rpc` 接入 owner map。`SETTINGS` 由运维提供，其中 `state` 是相对配置目录或绝对的 SQLite 文件，`owners` 按 owner 配置 `cwd` 和 `timeout_seconds`。`actions` 以 `triage`、`repair`、`replay`、`report` 为键，分别指向可信固定 argv。非交互 Codex 使用 `mode: codex-jsonl`、`argv` 和固定 `instruction`，依原生 `thread.started` 与 `turn.completed` 结算。机器复验、回告必须由配置的 owner 命令输出 `result` 对象；`observe` 的去重登记留在宿主。

`filing-fetch` 配置 `ff_status_argv` 指向 FF 公开 `ff_job.py --jobs-dir`，接受 `ff-job/1/<原生ID>` 证据引用。先 `get_status`；原生确认只能 `reconcile` 且部署提供 `ff_reconcile_config` 时，用同一作业、同一 attempt、稳定键执行 owner 的只读对账。结果和费用分别核对。重启运行 `local_host --config SETTINGS recover --hosts HOSTS --sidecar FILE --wait-seconds N`，从原 sidecar 接续。Phase C 回调也能设置 `RESEARCH_FEEDBACK_WAIT_SECONDS` 跟随旧作业。一个已启动但确实无法验证终态的写作业仍占用原工作区，其他隔离工作区能够继续。原作业未知时不另开作业。

本机已有的 CWP/FF 配置位于 `.planning/shared-reading-production/feedback-host`。`hosts.json` 定义端口，`settings.json` 定义命令和本机动作登记。将 `RESEARCH_FEEDBACK_HOSTS` 指向该 `hosts.json` 即可从已配置的业务阶段触发。两份真实收据按最终检查回放进入动作登记，首轮 12 条，重复投递增加 0 条，新增 agent 作业、FF 作业及业务模型调用均为零。

RF/Audit 已在独立真实宿主运行一条闭环。配置 `revenue-forecast.actions.reconcile` 调用 `scripts/rf_job_feedback.py reconcile --owner-root ROOT`，`report` 调用同脚本 `report --reports-dir DIR`。查询回告使用 `get-report --reports-dir DIR ACTION_ID`。Audit 的 `reconcile` 为 `feedback_owner.py --run RUN reconcile`，复验为 `feedback_owner.py --run RUN replay -- CHECK_ARGV...`。`CHECK_ARGV` 来自运维配置，以固定只读检查读原责任仓的公开接口，给出原 finding 引用及实际验证版本。RF/Audit 原生发布各用独占的 `RESEARCH_FEEDBACK_OUT`。复用同一已配置状态库和原始 sidecar 接续，不把两仓的作业目录交给总控解析。适用范围和实际命令的可执行样例见 [RF/Audit 收据](f4-rf-audit-acceptance.md)。

本机 FF 的 `actions.report` 指向 FF 公开 `ff_job_feedback.py --reports-dir OWNER_DIR report`，`get-report ACTION_ID` 核原发现、版本和证据。自动对账优先使用 FF 发布的 `actions.reconcile`，由 FF 按原尝试和原连接配置处理。`owner-json` 由责任仓落原生完成收据，再由宿主登记；worker 丢回复时读回同一结果。各仓实际配置和限定范围见[分仓上线](f4-rollout.md)。

外层 worker 退出时，尚未到原生命令的动作仍为 `queued`，恢复唤醒同一 action ID。`owner-json` 的执行器在写启动回执前原子领取，`codex-jsonl` 在原生会话启动前使用同一工作区互斥。并发恢复时只有一个领取者执行。尚未领取且发现 Codex 不可用时，保留 `codex_executable_unavailable` 并等待原定时恢复。已经领取且终态不明、缺回执或费用未知时查原作业。

旧版曾将明确未发现 Codex 的动作记为终态，可用 `python -B -m tools.feedback_loop.local_host --config SETTINGS retry-unstarted ACTION_ID` 恢复单一原动作。此命令只接受冻结请求及原运行配置一致、旧收据确认为启动不可用且原生捕获确实不存在的记录。配置改过、存在捕获或结果未知时保留原记录。原失败记在现有宿主诊断中，恢复仍使用同一个 action ID 和工作区领取。

新启动的只读 Codex 分诊可在输入中得到原生诊断的结构化事实。证据来自发布方已配置的收件目录，诊断和同名原观察都通过路径约束及原动作绑定。传输字段限诊断指纹、标准异常类型和适用的系统错误号，沿原 action ID 冻结请求。明细缺失、冲突或采用只有共享监督流的旧格式时，分诊仍执行。完整异常链继续按原 owner 观察查回。

升级宿主代码时先结束旧外层启动器，避免旧 worker 先领取后误用新版 helper。保留现有 SQLite、原生回执和专用 sidecar，再用正常 `recover` 接续。历史 `running` 状态仍以原生结果核对。本次发布前只读核对本机反馈操作库有 12 条 `done`，排队和在运行的动作均为零。

责任仓的写端口以原子落盘作为最终效果时，可为 `owner-json` 的 `triage`、`repair`、`replay` 或 `report` 同时配置 `argv` 和 `lookup_argv`，尾部 ACTION_ID 由宿主追加。两条命令随首次登记的动作保存。恢复读取 `{"receipt":{"request":原提交,"result":原结果}}`，请求完整匹配时补记同一动作。FF 和 RF 的 `get-report` 旧格式继续支持。无证据就保留原状态。后来修改宿主设置时，恢复仍沿用原动作的查询命令。

MeetingConverter 的四个执行路由共用 `feedback_owner.py --db DB --sidecar-dir DIR`，各配置原生动作名与只读 `get-action`。`reconcile` 走同命令的只读原转录状态查询。现有本机 `feedback-host/settings.json` 与 `hosts.json` 已增加 MC，CWP 和 FF 路由保留。原任务可把独占的侧车写到 MC `output/.feedback/observations` 后交给总控的 `tick` 或 `recover`，回执库为 MC `output/.feedback/owner.sqlite`。现场只读探针得到原作业未知，合成强退测试使用独占数据库。[MC 运行端口](../../../../MeetingConverter/docs/plans/f2-mc-output/runtime.md)

- 在实际运行 agent 的宿主检查能否按调用者提供的稳定 ID 创建及查询作业、取回终态、区分确知不存在与状态未知。以两个并发提交和故意丢失一次提交回复验证。已安装可执行文件、一次会话中的 agent 列表、测试 SQLite 的绿色结果分别只证明相应能力。
- ROOT 在工程运行环境提供固定的控制命令。各 owner 的映射取自运维配置，工作目录、技能路径和可写仓由该映射确定。业务或报告正文作为待分析数据传入。公开接口为[控制端口](interfaces.md)；可使用宿主已有持久作业接口或给原生作业加一层薄适配。FF 的下载 job 只管理下载，CWP 来源 AUTO 只管理资料，Audit 的 pool_progress 继续管理选样建议。
- 宿主以 action ID 原子登记原生作业和请求摘要，再交付执行。若工具只提供一次性启动，先在已有 owner 作业设施实现按 key 领取、存原生运行 ID 和接收结果。启动与回执之间崩溃时按原 key/原生 ID 核对。无法判断是否已实际启动时回 unknown，等待原生终态或新证据。owner 端将 action 的处置投影为协议中的标准状态。
- `observe` 是本地发生登记，`reconcile` 只查询原始作业。稳定偏差经 `triage` 选由哪个 owner 处理。只有 `repair` 才调用该仓修理技能。调度器将本仓 PWF、原始 issue、小型复现、已有版本作为输入。已有 worktree 正在被其他项目使用时，由本仓沿用现有隔离策略；同一可写工作树一次只有一个写者。不同 owner 可以并发，预算和 provider 并发沿用各自实际账户。
- 拒绝原因和门禁审视随已有分诊作业记录，自动完成结果也可读回 `gate_reviews`。检查真实保护目标和可用反例后，再决定删除、收窄、保留或取证。与拒绝同一作业的明确未知费用先查原账本。[拒绝审视协议](interfaces.md#拒绝先审视门禁)

## 2. 接入结束事件与重启

本机已使用统一的 `intake run` 与 `drain`。每个入口使用独占旁路，后续原生动作完成后自动继续未结的观察。父 CLI 与它调用的 provider 共用旁路时仍按原生发现方路由。原数据、尝试和各 owner 回告仍由相应 owner 保存。具体命令和生产接线状态见 [F4 分仓上线](f4-rollout.md#统一运行与接续)。

- 将公开观察登记在既有运行的终态旁，按原生 run/attempt/item 关联。正常结束、异常及独审完成都可唤醒。不同 owner 通过自己的导出接口发布，ROOT 接受显式交付的旁路。
- CWP Phase C 已实现本地示例。其原生 overall.json 先持久化，发布旁路后独立启动一次 tick。宿主重启时复用已有未完成作业/终态收据清单，交回同一 tick；每次运行有限，不递归触发公司池。首次部署在隔离运行数据根验证自动唤醒和实际查账，保存原生作业 ID。保留正常业务原退出码。
- 在观察写一半、登记后丢回复、修复后回告前中断三处注入故障。按原 key 核对未知，验证影响范围；对另一仓正常作业测并发控制。以真实源下载请求及实际模型 POST 计数检查恢复，不从重复脚本退出 0 推断成本安全。专用日志留下实际大小、轮转后仍可回放的最小证据和清理结果。

## 3. 一次 P1 公司试点

1. 从[父计划](../du11-source-closure-2026-10-18/task_plan.md)取冻结 H1 和投资者关系对照，固定来源、文种/版本、检查点、预期来源归属、第二样本。沿用运行时的模型配置和总预算。在同库先以留存结果建立可复现反例；正式新生成在该节点的独立 attempt 中进行。
2. CWP 经过公开选材、原语言摘要和证据回放，登记在原文能定位却被摘要漏掉的内容、主体/条件变形、未能完成的检查。程序退出正常时同样对比预先冻结的检查点。发现真正的共因后，由实际 agent 用本仓技能执行复现、TDD、修复与独审。
3. 按同 run 重启、跨 run 重用验证实际原文和摘要内容 SHA，核对原生 POST、费用及回放结果。RF 通过公开入口消费修复后的资料，将来源证据追到至少一处实际采用的驱动/假设、计算、报告和快照；用旧版本对照验证读取了正确缓存。新版内容证据与执行的代码版本分别报告。
4. 确认同一 issue 关联的各原始场景都回告，消费者仍复现则保留未完成；若需要新修复代次，带入新的现场证据。在另一文种或公司验证泛化，独立 reviewer 根据真实来源和运行收据验收。公司池另由其本来计划启停。

**移交结果**在本总调度 progress.md 给实际 host 能力和版本、原生 job 与 run/attempt 引用、owner 修复提交、回归/反例、原公司实际 replay、去重/付费/存储观测及仍待验证范围。只登记大节点。部署前后各保留一条基线，后续对照同类故障复发率、误报、从发现到定位的时间及每次运行日志字节。
