# 定期更新接口与组合约定

2026-11-21 冻结的施工约定。下列新增 schema/CLI 是实施目标。已有 owner 的旧调用保持可用。

## 1. FF 控制面

建议从 `scripts/ff_scheduled_refresh.py --config <FF部署配置> --jobs-dir <原FF作业目录>` 接入。子命令固定为 `status`、`configure --request-stdin`、`runs --cursor …`、`tick`。测试接线可用显式时钟和隔离配置，正式任务仅调用 `tick`。设置与每轮状态保存在 FF owner 目录，可与 `ff-job/1` 的作业收据一起查回。

FF 已实现该形状。运行部署默认读取 `--config` 同目录的 `scheduled_refresh.json`，也可显式给 `--refresh-config`。Dashboard 继续使用原有 `--config` 与 `--jobs-dir` 组合。运行回执可附当前已经接纳的 `active_action`。关闭与接纳在相同状态锁内生效，外部动作在释放锁后执行。

Dashboard 使用以下接口，配置写入走已有本机命令认证和请求处理。读取只调用状态或历史。

| HTTP | FF 子命令 | 语义 |
|---|---|---|
| `GET /api/v1/scheduled-refresh` | `status` | 当前配置、调度就绪、下次时间、最新运行和实际限额。无历史时数组为空。 |
| `PUT /api/v1/scheduled-refresh` | `configure` | 一次更新配置。成功回同一状态结构。写设置零采集、零模型。 |
| `GET /api/v1/scheduled-refresh/runs` | `runs` | 分页读运行回执。可选 `cursor`，空历史正常。 |

配置请求样本，名单 ID 用 owner 的实际选择值替换。手动导入的定版名册可以使用 `{"mode":"pinned","roster_ref":"…"}`。

```json
{
  "schema_version": "ff-scheduled-refresh-config/1",
  "settings": {
    "enabled": false,
    "cadence": {"frequency": "weekly", "weekday": 1, "local_time": "07:30", "time_zone": "Europe/London"},
    "roster": {"mode": "universe", "universe_id": "universe-fixture"},
    "document_kinds": ["annual_report", "semi_annual_report", "quarterly_report"],
    "transcripts_enabled": true,
    "reading_level": "local",
    "backlog_enabled": true
  }
}
```

- 日频省略 `weekday`，周频用 ISO 星期 1–7。时区由 owner 翻译为实际当地时钟，持久化截止日和 UTC 时间。临时缺失名单可保存为停用状态。开关开启要求已明确范围，未知或尚无数据的合法范围正常显示覆盖状态。
- `reading_level` 为 `off`、`local` 或 `summary`。 `local` 零模型，并保留到业务原文的证据。 `summary` 在同一读流程中调用实际已配置模型。两者只改变处理方式，保持同一原文目录和 SourceRef。
- `expected_revision` 可随设置提交。只有调用方给出旧修订号、且实际发生不同设置来回覆盖时才报告配置冲突。重复提交同一设置幂等。UI 可读回当下设置并表示，版本增量字段保留兼容。
- 状态输出使用 `ff-scheduled-refresh-status/1`，含 `settings, revision, scheduler.state, scheduler.next_check_at, next_due_at, current_run, last_run, effective_limits, reason_codes`。未安装、未开启、未运行和数据不可用分别表达。部署配置决定实际 provider 与限额。状态/日志只提供必要的范围和用量，避免传凭证或本地私有路径。
- 历史输出为 `ff-scheduled-refresh-runs/1`，含 `items, next_cursor`。运行摘要含 `run_id, slot_id, roster_snapshot_id, started_at, updated_at, state, counts, usage, reason_codes`。计数至少含候选数、已复用、新登记、已阅读、已摘要、已跳过、待续、失败。结果状态和用量状态独立。

名单来源使用现行公开 Universe 口，核对同一名单 ID、快照 ID，取完全部页，保留按发行人/挂牌绑定的选择。FF 的适配器可直接读现有 IQS 产品公开面。Dashboard 无需作后台代理。定版模式通过 FF 的同一名单接口导入，后续配置引用它的 ID。两种模式均禁止拼目录、直接读任何他仓数据库或用列表页面第一部分代替完整名单。

## 2. CWP 元数据公开口

目标命令 `source_catalog.cli discover-incremental --request-stdin`，或 CWP 原公开入口的等价参数。共享实现使用配置对应的市场源和有界 provider discovery。增长来自公开枚举与续页能力，既有 `ensure` 继续负责字节获取和登记。

| 字段 | 约定 |
|---|---|
| 请求版本 | `cwp-incremental-discovery-request/1` |
| 请求范围 | `request_id, identity, source_market, document_kinds, since_date, as_of_date, cursor, limits`。身份用现有公开 issuer/listing 坐标，来源市场独立。起止日均包含。首个 cursor 可空。 |
| 输出版本与范围 | `cwp-incremental-discovery/1`，回传 `request_id, scope, coverage, next_cursor, candidates, usage, reason_codes`。 `coverage=complete/partial/unavailable`，游标用 owner 提供的值。 |
| 候选 | `provider, provider_document_id, source_market, document_kind, published_at`，以及已知 `fiscal_period`、编订/更正标志、对应上市范围、已有 SourceRef。非期次文档允许期次为空。未证发布时间保留诊断，不推进完整水位。 |
| 执行和恢复 | 现有元数据字节、时间、请求数/费用上限。正常发现不取正文。响应丢失时可重放相同范围。缺页、限流、截断和 provider 无完整枚举时为部分覆盖。没有匹配且范围真正完整是一种完成结果。 |

FF 只根据核对过的候选调用原有精确 `ff-job/1` 采集。发现与采集之间的请求保留候选键；若现行 `provider_document_id` 精确入参还能复用另一个期次版本，修正所属层的候选选择或登记，不把标题比较放进调度器。CWP 的元数据返回不得把上游 provider 的内部 URL 作为 UI 可传入的下载目标。

联调时核对响应 `scope.identity.entity_id`、`scope.identity.listing_id` 与 `scope.source_market`。连续分页用 `next_cursor`，页面覆盖是否完整由 `coverage` 单独表示。前页有真实缺口时，后续页的完整结果不能补做前页的覆盖证明。

## 3. 电话会与阅读

FF 在 `ff-job/1` 内增加独立电话会种类 `transcript.acquire`。请求含权威 issuer/listing、明确的 FY/Q、截止时间、`intent` 和仅该电话会的 `acquisition_limits`。复用已登记 transcript → 有证期间且 provider 支持时发起 ET → CWP 以正常导入登记 → 返回同一 SourceRef。原有 `companion_transcript` 调用仍走其兼容外观。相同作业恢复读取原 job、ET usage 和 CWP 来源记录。

CWP 为有限阅读提供 `cwp-incremental-read-request/1` 与 `cwp-incremental-read/1`。实现可以组合现有请求入口。跨仓以同一 wire 语义为准。

- 请求含 `run_id, reading_level, sources, limits`。 `sources` 为精确 SourceRef v2，绑定当前已登记来源。现有批次配置及 profile 由 CWP 选择，FF 不携带模型名、正文、本地路径或内部 cache key。提交同一 `run_id` 续原批次。重复资料的 lookup 和已处理结果复用由 CWP 保存并确认。
- 响应每份来源回 `source_ref, state, result_ref, reused, reason_codes`。结果可用时，`result_ref` 通过 CWP 已有或本次补的公开读取返回带出处的选段与摘要。 `state` 至少区分 `read`、`summarized`、`skipped`、`deferred`、`failed`、`uncertain`。同批单份失败保留成功产物。批次收据名额由现有 owner 资源设置衡量，展示可分页。
- 本地选段和正式摘要的恢复不靠文件名、mtime 或目录猜测。使用原文 SHA、其来源身份和 owner 的正式处理索引。长期阅读入口旧版本不存在可返回具名未处理，不能以此拒绝独立验真原文。
- 同一批次存在旧的未知费用记录时复用原 `run_id`。旧批次范围、名单或阅读档位已不适用时，FF 通过只读 `incremental_read_status` 查询。部署可以为该动作声明 CWP 等价公开命令。请求用 `cwp-incremental-read-status-request/1` 和原 `run_id`，响应沿 `cwp-incremental-read/1` 的 `run_id/items`。当前 owner 尚未提供这个动作时保持具名待核。
- 增量积压入口根据本轮挂牌、文种与日期从 CWP 原件目录给未达到该阅读档位的引用。复用 CWP 查询/派生索引。初次处理、已完成、明确低价值、可安全重试和需对账的项目保留关联。循环跳过已有相同结果。

## 4. 持久语义

1. 每轮先冻结名单、配置和到期时间。每天/每周按当地周期算一个逻辑槽位。进程实际唤醒时间不参与槽位身份。过期多日可在最新到期槽位做合并补范围，历史覆盖水位独立。
2. 每个计划只允许一个活动调度，FF 原生 OS 锁及原子替换用于崩溃恢复。先写候选、固定业务键、子作业幂等键再提交。逻辑子作业键绑定候选的正式原文版本或精确电话会范围，与重启、再次触发及展示配置修改无关。
3. 续跑先查询已经登记的子作业。若 job 成功但调用方未保存 SourceRef，则通过相同 job 查回。如果状态或费用未知，走原端口对账，不能当作免费失败重发。CWP 的读作业按原 `run_id` 查收据。继续工作只针对经过 owner 确认可安全开始的剩余项。
4. 候选持久入账、范围覆盖证实后更新发现水位。入库和阅读的成功分别记录。发现已完整、采集尚待时，下轮直接接续待处理候选。候选必须绑定唯一可验证身份或明确保留缺项。
5. 关闭开关只停止接纳新作业。读取状态、查询已保存结果和收尾仍可进行。重新打开从原水位和原待处理项续跑。范围修改后把旧运行记为已取代，按选定新名单重新核定待办。无业务范围变化的同槽改钟点保留原一次运行。失败、部分、缺配置和未知费用的情况按相同 F4 原因记录，并保留“拒绝先审视门禁”的字段。

## 5. 跨仓共用验收夹具

| 夹具 | 最小输入 | 预期 |
|---|---|---|
| A1 | 一个短窗口两条 CN 发布，其中一份原字节已登记、另一份修订 accession 缺失。供应方返回两页。 | 两条均入账。旧原件下载 0，新版本 1 次，原 SHA 和新 SHA 各可查回。 |
| A2 | 一个 HK 非期次再融资/IR 项、一个 US 明确 FY/Q 的 TXT。该季度财报刻意缺失。 | 非期次可通过 accession 归档。TXT 可独立获取并定位，无翻译或 PDF 路径。拟制年报 Q4 均拒绝发请求。 |
| A3 | 同日两个启动，关机跨周，部分发现，组合重启；分别中断在作业发布、原件登载、模型响应已返回前后。 | 相同范围只出现一个活动运行。发现水位不越过部分。FF 与 CWP 使用原 owner ID。重复下载和重复付费计数为 0。 |
| A4 | 既有未处理已登记原件；数据完整 PDF、TXT、无业务内容模板；同 SHA 查回。 | 本地阅读可回定位，模板具名跳过，无模型 POST。摘要模式用 loopback 恰当生成，第二次读取复用。 |
| A5 | 动态名单三页；一次名单不可用、一次成员移出；关闭/重开、时区 DST 与实际用量上限。 | 名单不截断、下一轮使用新快照。关闭后无新增作业。命中真实限额后回告并继续有界接续，页面可读。 |
| A6 | Dashboard 停用、启用、改周/日频，owner 离线、费用未知、历史空和分页。 | 保存设置没有采集副作用。UI 正确区分状态并保持其他卡片可用。 |

组合验收记录至少包含三市场的原版 SHA、作用范围、调用计数、恢复前后 ID、实际模型请求数量、临时环境清理及当前 owner HEAD。正式启用前需有真实文档、真实供应方的一次有界小批测试。测试夹具的“零重复”包括在新进程读回。
