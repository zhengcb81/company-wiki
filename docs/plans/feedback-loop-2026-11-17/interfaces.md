# 反馈输入、调度和回告

## 公开观察 `feedback-observation/1`

UTF-8 JSONL，每个 invocation 一个专用输出。`RESEARCH_FEEDBACK_OUT` 可指定此文件。`RESEARCH_FEEDBACK_RUN_ID` 和 `RESEARCH_FEEDBACK_ATTEMPT_ID` 可提供上下文；独立测试可生成自己的标识。父子进程各有独占输出，父端关联各自原生 ID。现有 stdout、stderr、错误信封和既有计费回执保留其协议。输出文件写失败时由外层记录追踪不完整，业务使用原始终态。

```json
{"schema_version":"feedback-observation/1","owner":"filing-fetch","origin_owner":"revenue-forecast","run_id":"weekly-example","attempt_id":"first","step_id":"download-cn","check_id":"bounded-request","expected":"limits-present","actual":"limits-missing","disposition":"deviation","issue_key":"download-request-omits-limits","version":"fixture-before","evidence_ref":"weekly-example/cn"}
```

| 字段 | 约定 |
|---|---|
| `owner`, `origin_owner` | 前者是可处理本项的仓，后者是观察并需回告的仓，缺省等于前者。路由清单见[分工](dispatch.md)。 |
| `run_id`, `attempt_id`, `step_id`, `check_id` | 与两端 owner 合在一起定位一次观察。步骤及检查使用原生稳定标识。真实重试使用新 attempt，同一完成回执重复投递使用原身份。 |
| `expected`, `actual` | 原生检查可比较的稳定结果词。必填字符串。数字、严重度、币种、限定词等细节由 owner 的证据引用保留。 |
| `disposition` | `expected` 表示符合原检查，`deviation` 表示偏离，`unknown` 表示未能评估。缺省对比两结果词。明确 unknown 只读对账。 |
| `issue_key`, `version`, `evidence_ref`, `details_ref`, `parent_step_id`, `terminal_check_id` | 可选字符串。`issue_key` 是经 owner 认可的规则签名。开始记录用 `terminal_check_id` 指定配对检查；其余字段定位执行版本、公开证据、脱敏诊断和上游步骤。源材料、可执行命令及凭据留在原责任边界。 |

同一 run/attempt 有多份材料或子进程时，step_id 或 check_id 带原生 invocation/item ID；亦可由调用方分配独立 attempt。文件次序不决定身份。带来实质新证据、修复代次或外部条件变化时，由取得该证据的 owner 在新 attempt 发观察，保留同一发现方和指向首笔发生的可选 `original_occurrence_id`。重放引用原场景，同时记录新证据。未知用量先向原作业查账。已经终结的旧收据保持原判。

开始、结束、分支选择、失败原因链、耗时和用量保存在**本仓完整步骤日志**。以上格式是对检查结果的跨仓投影。保留成功、跳过、预期拒绝和错误成功的区别；同一原生 finding 可在另一个审查轮次表示不同问题。报告/原始 stderr 的脱敏详情在产生方只保存一次，按引用重读。成功详细记录按本仓轮转，开放 issue 的最小复现和固定回归随 issue 留存。

`action-started` 是正确的原始观察。若缺少同 owner、发现仓、run、attempt、step 的配对终态，总控登记原行并进入查账；其他文档、期次或预算检查不能替代它。旧 ET 和 SID 继续使用其已发布的结果检查。FF 的 `step_id` 为 `<owner_job_id>/<native_attempt>`；只读结果和成本状态分开保留。仅有开始、落盘不完整或证据引用无法定位时不触发新下载。

## ROOT 和宿主的控制端口

`python -m tools.feedback_loop plan FILE...` 只读汇总显式交付文件。`python -m tools.feedback_loop tick --hosts CONFIG FILE...` 处理交付批次，每次调用有限。后续唤醒仍使用同一批观察及同一外部宿主。`CONFIG` 是运维显式供应的 JSON，以 owner 为键、已配置的宿主命令参数数组为值。进程工作目录由宿主部署配置负责。请求作为 JSON 经 stdin 传给该固定命令，stdout 回一个 JSON。观察里的文本不决定命令行。生产需要能持久保存作业、查得其状态并按 key 原子提交的宿主。普通一次性聊天命令不能证明这种能力。

请求格式 `feedback-action/1`，含 `method`（`lookup` 或 `submit`）、`action_id`、`request_digest`、`kind`、`owner` 和 `payload`。回复格式 `feedback-action-result/1` 需回显 `action_id`、`request_digest`、`state`。`done` 时另有 `result` 对象。状态为 `absent`、`pending`、`unknown`、`failed` 或 `done`。同一 action ID 的内容变化必须报告冲突。只有权威 `absent` 才提交；宿主先持久登记再启动实际任务，同时来的同 key 提交复用同一作业。超时、失联或未知费用继续查原作业。调用方程序不会用这些情况产生新的付费尝试。

| kind | 提交目标和幂等范围 | `done.result` |
|---|---|---|
| `observe` | 发现仓已有记录按发生 ID 原子绑定内容摘要，涵盖成功、未知、偏差。属于轻量本地登记，绝不启动模型、代码修理或下载。这样分批重投的相互矛盾结果也能发现。 | `recorded: true`。同 key 不同内容须回显原摘要或明确报冲突。 |
| `reconcile` | 发现仓，缺终态或结果/费用未知时只调用 `lookup`。允许原作业公开端口执行只读核对并在同一作业登记结果。 | 用 `status: known` 和 `evidence_ref` 核对。FF 可附可信 `job_status` 与 `cost_state` 形成 `reconciled`；若已找回业务结果但费用仍未知，返回 `status: cost_unknown`，总控保留未知并展示同一作业结果。旧格式仍等补充观察。 |
| `triage` | 责任仓，每次发生单独登记。payload 含 `observation` | `decision` 取 `repair`、`fixed`、`expected`、`external` 或 `needs_evidence`。`repair` 需 `issue_ref`、`generation`，同一根因的实际修复轮次由 owner 管理。`fixed` 需 `issue_ref`、`fixed_version`。不同异常可合并，同名异常可拆。 |
| `repair` | 责任仓，按 `issue_ref` 和 `generation`。用本仓技能和 PWF，执行 RED、架构归因、定向 GREEN、必要独审和发布 | `fixed_version` 为可以由发现方运行的版本。重复的发生记录共享修复。合法行为、外部限制和证据不足分别落在分诊处置。 |
| `replay` | 原发现仓，按原发生、责任仓问题及修复版本。用公开入口重放原条件 | `verdict` 取 `verified`、`regressed`、`unknown`。确定结论需 `verified_version` 等于请求修复版本，并给 `evidence_ref`。unknown 保持待核。 |
| `report` | 责任仓，按发生、问题、版本及确定的复验结果。附原发现与其回执 | `recorded: true` 由责任仓端口落盘后返回，可独立查询。未配置 owner 端口、历史仅总控登记不能声称回告完成。owner 汇总同一问题未覆盖的发生，复发可用新证据重开。 |

稳定 action ID 由种类、目标及上表幂等范围生成。申请内容摘要用于识别同 ID 的不同请求。一个运行的损坏旁路行、互相矛盾的重复观察和无宿主的 owner 单列诊断；同批其他可判断的观察独立处理。历史业务作业和退出码由原生产端保存。

分诊可返回 `decision: refer` 和 `next_owner`。总控只向已配置的目标转交同一原观察，发现方保持不变，循环转派报告未验证。共享 repair 的 payload 仅含 `issue_ref`、`generation`，发生详情由各自的 triage 登记，各自 replay/report 回告。regressed 被回告后，owner 按新证据开启新代次；原输入静止时不重复派工。修复版本指发现端实际运行的发布版本，内容 SHA 和消费者本地 artifact ID 各在消费证据里表达。

未显式处置且有枚举词 `unknown` 按未知处理。原生证据/详情/消费证明按发现仓命名空间解析，issue_ref 和 generation 按实际承办仓命名空间解析。replay 明示 `acquisition: reuse_only`，优先留存的付费响应、来源或离线样本。同一笔作业同时有质量偏差与用量未知时，质量诊断继续进行，核对原生作业，不盲目再付费。真实新生成在正常预算及可核算的独立正式 attempt 进行。

控制宿主只继承启动所需环境。需本仓具体运行设置时，可将短数组改为 `{"argv":["本仓宿主绝对路径"],"pass_env":["本仓需要的变量名"]}`。配置只写变量名。主机机密不进入公共观察，原生诊断按各仓脱敏。成功日志轮转时保留已关联发生的轻量身份绑定和开放问题最小证据。

在 Phase C 总控验收入口同时指定 `RESEARCH_FEEDBACK_OUT` 与运维 `RESEARCH_FEEDBACK_HOSTS` 时，原生 overall.json 先完成，宿主控制 tick 在独立子进程处理。启动回执在同一运行目录的 feedback-delivery.json，控制结果在 feedback-dispatch.json。两者与 OUT 各用不同文件。运行中断时，可对原 OUT 执行 tick 重接，不必重新跑模型。重建已留存原生结果可运行 `python -m tools.document_understanding_benchmark.phase_c_feedback <本次overall.json> --out <独立输出>`，将 --out 换成 `--ref <原生引用>` 可复核模式、selector 版本和产物 SHA。

启动或重启调用 `python -m tools.feedback_loop.local_host --config SETTINGS recover --hosts HOSTS --sidecar FILE --wait-seconds N`。可重复 `--sidecar` 传原开始和终态文件。先恢复现有动作，随后有限等待、继续原观察；不重新发起公司运行。FF 端点需配置实际作业所属的 `--jobs-dir`，以及可选的 `ff_reconcile_config` 指向该作业使用的 owner 查询配置。对账只允许 `get_status` 和 `act reconcile`，按同一作业与 attempt，既不发 `run`/`retry`，也不向外部证明 latest。

## 本仓问题卡与修复技能

已有 issue 系统的仓直接关联其原件。其余仓可用本仓 PWF 邻近 `issues/` 的版本化小卡，正式问题登记有预期/实际和影响、原发生与版本、可运行最小输入、责任与已证/待证根因、修复提交与用例、消费方复验。`open`、`working`、`verified` 足以区分可领取、正在修及验证完成。外部阻塞记录恢复条件，按真实状态回告。小样本可随测试保存，原文和生产数据库由来源 owner 持有。无人值守时由单个 owner 写者或现有作业端口归并，新事件不会直接改 Git 共享索引或覆盖其他 harness 的工作。

每个 `repair-…-issue` 技能一次处理一个根因。在现有 PWF 写最小实施范围和验收条件，先从公开入口使回归变红，再修责任层，用合法对照、必要的另一文种/公司检测过拟合。修复技能只能改本仓，新的跨仓缺口回报给对应 owner。日常运行继续使用已有预算、限时和授权，内容和报告长度不构成许可。测日志断路与业务完成之间的隔离。重大节点独审用最终版本和复现命令，不设置逐小步签收。
