# G1 收口：先去掉多余阻断，再完成虚拟化

> 本卡是 [task_plan](task_plan.md) 的当前第一优先施工细则，覆盖旧审计中的下一步；不是新的审批合同。基线代码 `1cfec10` 已发布，CI37188829582 success；文档基线 `376ed90`。只在 G1 收口、S3 联调两个大节点集中验证。总指挥独占共享计划及合入。

## 已完成，不再开工

- private/public访问与外部LLM逐文档人工许可已取消；prompt review、待修复提案与 review store故障只是诊断。
- AUTO Approval 公共类型/CRUD、gold/shadow/Work Unit人工签收已退役，历史事实表保留。
- activation/rollback/restore/map的 reviewer 已可省略，自动记 actor；签名、信任根、TTL evaluator已退出。
- reader pin已缩到实际读取字段；全snapshot完整性仍自动校验。
- 旧全库Worker启动/执行链已退出；新有限批次N4A/N4B已集中验收。commit不跑pytest，日常push/CI只有快速集合。
- `secret_audit` 的 ignored本机凭证已只作诊断，不再为此安排代码改造；真实待发布密钥检查保留。

## G1 执行顺序与文件归属

| 顺序 | 负责人 | 具体动作 | 完成输出 |
|---|---|---|---|
| 1（可并行） | G1-LEGACY外部harness | 去掉兼容脚本双环境变量许可；让来源/只读维护入口行为一致；删除已经完成的一次性六脚本链 | 独立分支、专属测试、短交接；见[施工卡](harness_lanes/g1_legacy_entry_and_retirement.md) |
| 1（主线同时做） | MAIN | 清理 `source_reader` 中 filing_reuse 对HTTPS、retrieved_at、collector_name/version的逐用途资格阻断 | 缺采集描述字段的真实可验证来源可读，诊断缺口；不伪造verified元数据 |
| 2 | MAIN | 清理 `automation/narrative_transport.py::_require_historical_source` 的额外采集日期截止 | 公开日在as-of之前、后来才下载的资料可用于叙述读取；未来公开资料仍拒绝 |
| 3 | MAIN | 核查 normalizer版本、摘要字段/片段校验、GapPlan是否还有无必要整份阻断 | 有具体误拒才改；旧版本须能真实解码/回放，不能随便改成接受所有版本；坏引用丢片段且报coverage |
| 4 | MAIN | 接收G1-LEGACY，处理真实冲突；将46项分类为已退出、必要自动校验、能力边界或外仓owner事项 | 当前清单无重复待办；一次G1责任包GREEN、普通commit/push |

外部harness不改 `src/`、catalog CLI、生产配置或原件；MAIN不改外包列出的脚本和专属测试直到交付。需要修改共享调用者时，外线交精确接口缺口，由MAIN合入时处理。

## TDD锁定的公开行为

1. source ID/公司/证券/期次/公开日期和真实bytes SHA正确，但没有collector描述字段，仍能按SourceRef打开原件；缺字段有诊断。假URL或缺URL不能升级成“已证实网络来源”，也不能禁止本地真实原件的读取。
2. 2023公开、2025下载的来源，在2024 as-of可用；2025才公开的来源在2024不可用。`query_local` 已按公开日筛选，新增测试框住叙述入口，避免改回查询端。
3. 缺review receipt或review数据库锁住不阻断正常来源，已给定SHA不吻合、公司/期次冲突、locator不能回放仍真实失败。
4. 兼容入口无需两枚环境变量；永久退休的投资研究/Wiki writer仍退出78。该约束是产品职责，不是个人权限。

现有相关责任包：

```powershell
$env:PYTEST_ADDOPTS='-p no:langsmith_plugin'
python -m pytest tests/contract/test_source_version_reader.py tests/contract/test_source_catalog_latest_mode.py tests/integration/test_narrative_transport.py -q
```

先调整“publication_and_capture_both_must_precede_cutoff”这条旧语义测试为上面第2项，看到新期望RED后改实现；不是删掉未来信息反例来获得GREEN。其他测试只在实际行为变更范围更新，不恢复全Contract/coverage长测。

## G1后才做的S3收口

- SourceRef/SourceExport v2、迁根与原文验证已经存在，RF/StockWiki也有实读证据；不重新造文件网关。
- 核对安装示例与当前provider位置。`config/source_acquisition.yaml` 本机隔离worktree路径不提交到通用生产配置；用已有安装/配置机制解决，不新加访问角色/合同签收。
- [ET-DEADLINE](harness_lanes/et_retrieval_deadline_closeout.md)可在独立ET目录预先实施；它的结果进入S3联调，不抢MAIN来源代码。
- [ET-LIVE](harness_lanes/et_transcript_live_import_acceptance.md)只在独占目录做一次真实ET取数与临时CWP导入；FF companion确定性覆盖和ET live段分别记账，不能将直接ET调用冒称完整FF live链。
- 最终一次受影响的FF/ET→CWP正式入口联调，核period/语言/SHA/size/pathless迁根/无额外下载，以及测试目录恢复。无需逐字段人工签收。

## 保留的最小自动校验及理由

| 保留项 | 理由与所在层 |
|---|---|
| 实际打开时bytes SHA、immutable raw、写入归属/路径包含 | 存储层保护原件并阻止错文件；业务层不重复检查物理目录 |
| 公司/证券/期次/公开日期、版本与撤回事实 | 来源层避免串公司、期次错配和未来信息 |
| 可回放locator、引用与来源对应 | 解析层保证摘要有真实依据；partial不等于需要人批准 |
| lease/generation/幂等、预算预留/未知usage | 调度/资源层保证丢包恢复、重复不收费、不会无限占用 |
| 必要schema版本、快速lint/公共接口类型、待发布密钥检查 | 自动接口与发布正确性；不做全量覆盖率、人工签名、固定场景数门 |

## 不扩张范围

Dayu零代码改动。RF/StockWiki/IQS现有owner工作树只读；其规则发现交owner，而不是MAIN跨仓清理。PDF SourceExport只支持manifest的限制是当前能力，已有NarrativeTransport PDF回放不重复实现。没有请求方需要严格“当时本机已经收集到”模式时，不为了删一个capture限制新增配置/权限体系。

G1/S3收口后才进入N4C四类真实文档、1/2/4并行吞吐/空间测量，再实施S5/S6。G1没有固定待满计数或逐项签收文件；完成依据是已核实的多余阻断退出、相关责任包绿色与真实接口回归。
