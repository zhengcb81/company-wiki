# W09-RF-RESEARCH：正式引用、角色与买方经营桥修复

状态：**READY，可立即启动**。这是独立研究与 RF 方法改进包，A/B/C 连续推进，不等 ROOT 对 A 另行签收。最终新 CWP 摘要采用、中央 run 导入和 W12 四路审查由 ROOT 负责。

施工卡唯一正本就是本文件。工区只放 ROOT 创建的 `START_HERE` 指针与本包专属 PWF，不复制第二份卡。同目录的 `INTERFACES.md`、`INPUTS.json`、`handoff.template.json` 由 ROOT 统一维护，是跨包接口正本；本卡解释 W09 的研究语义和执行步骤，交接字段以这些接口文件合并后的定义为准。

## 0. 交给执行 harness 的指令

完整阅读本卡。在指定独立工区完成 W09 研究修复、离线原生主/压力计算、报告与快照，将通用经验写回现有 RF 方法卡。任务结束前必须调用独立审查 agent，全面检查完整度、来源与数字、研究质量及改动质量；修复发现的全部可修复问题，再让独立 agent 复核最终版本，才能交接。公开资料不能识别的未来经营量必须诚实保留未知与暴露，不以编造或不断调参数取得“通过”。

这张卡本身已授权范围内实施与测试，不新增人工许可、授权文件、canary、签收等待或逐小步审批。

## 1. 工作目录、基线和写入所有权

| 项目 | 固定值 |
|---|---|
| 工区 | `C:/Users/郑曾波/Projects/revenue-forecast-r1-research`，由 ROOT 创建 |
| 分支 | `codex/r1-w09-research-20261023` |
| RF 基线 | `10bf611166013bd68ce14bfa19bb70e89a92dd5b` |
| 独立PWF目录 | 本工区 `docs/plans/r1-research-20261023/`；其余根目录旧PWF不作为本包执行队列 |
| 唯一新研究/测试运行/交接目录 | 本工区 `delivery/w09/` |
| 可改现有方法文件 | `references/buy-side-methodology.md`、`references/evidence-role-calibration.md`、`references/input-construction.md` |
| 源码例外 | 只有实际 RED 证明通用确定性 bug 时，才窄改现有 authoring helper/必要测试；先在本包记录根因与所有权。不能为本公司增加生产特判、企业词典、第二计算引擎或新审批层 |

开始先确认 `git rev-parse --show-toplevel`、`git branch --show-current`、`git rev-parse HEAD`、`git status --short`。上表是代码基线；ROOT的开工文档提交后实际start HEAD见本工区`START_HERE.md`和母卡同目录`dispatch.json`，不把该正常文档提交误当代码偏离。工区或基线不符先报告 ROOT，不能在母仓自行 checkout/reset；用户不需要再授权。若此前安装/索引工具不同，记录实际状态，禁止修改 `core.bare` 来“修好”沙箱 Git。

**不可写**：原 RF 母仓、CWP/W08 工区、filing-fetch、ET、审计技能仓与所有安装副本、Dayu、IQS、中央 audit run、母 PWF、生产配置、原件、费用 ledger。不能启动新采集、模型、翻译、收费 API、旧脚本整批重跑、生产 assurance 日/周任务、安装同步或主线合并。

本包只读使用现有已付摘要，不等待 W08。W08 尚未正式发布的新摘要不能被写成已消费。其他并行包不拥有这三张 RF 方法卡和本工区的 `delivery/w09/`。

## 2. 只读输入：准确路径和字节绑定

下文 `RUN` 仅是文档缩写：

`C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec`

读取前在本包生成 `delivery/w09/inputs/readonly-inputs.json`，记录真实绝对路径、SHA-256、字节数、用途及可迁移的逻辑名；不得修改下面任何文件。先核对下表，再核对准备包 handoff 内全部 `artifacts`。不要复制 PDF/SQLite/完整旧 run。

| 逻辑输入 | RUN 下相对路径 | 预期 SHA-256 |
|---|---|---|
| W09 原卡 | `remediation/r1-final3-review-20261022/work_packages/W09.md` | 开始实读并记录，不能当成执行过的凭据 |
| 准备交接 | `roles/executor/r1-remediation-02/w09-bridge/handoff.json` | `b1820987692ac6ceb3c715bf3f670938af593a1e568d9c8c29e5d00eec54082c` |
| 准备解读 | `roles/executor/r1-remediation-02/w09-bridge/handoff.md` | 由本包实读并记录 |
| 三审集合与根因 | `diagnosis/r1-final3-review-20261022/root_causes.json` | `45e088482d956ce18d6fd64548aed69711299c11fb35fc35df795a8efca72bab` |
| 封存正式旧输入 | `execution_replays/r1-remediation-01/phase_b/forecast/final3-input.json` | `e54ba7df7a5914772222e88e56661d0822e251e257814b9dc7c976c454660257` |
| 封存正式旧输出 | `execution_replays/r1-remediation-01/phase_b/forecast/final3-forecast.json` | `41ea79efa319226ac93e65d5210bb304b4d458cfac95ef5998fdf06eaf12279d` |
| 两 PDF 十页真实复核 | `execution_replays/r1-remediation-02/phase_b/research/verified-source-pages.json` | `66dced5bfbe7c5b6f206e62252a8f9dfca86d03b4e17293cb053b2a076537e7a` |
| 年报 p183 精确元表补读 | `execution_replays/r1-remediation-02/phase_b/research/source-page-addendum-20261023.json` | `993cc92c0c914430e5f93edfca6b3bbc421624da146490435c4dda3f0e478a98` |
| 49 项绑定建议 | `execution_replays/r1-remediation-02/phase_b/research/w09-preparation/claim-scope-bindings.json` | `7e7dd04ecf6b9c20194790af268f87d4f9ac3644e5e60bbd8bf45408eb43cf88` |
| 可复算经营桥 | `execution_replays/r1-remediation-02/phase_b/research/w09-preparation/component-bridge.json` | `95eccc0622b12ec5e292ae6817ab2154a7f98da44ab287255f2d9df09cb40bc7` |
| RPO 建议 | `execution_replays/r1-remediation-02/phase_b/research/w09-preparation/rpo-role-advice.json` | `70d04b6f58be2c0075ab90ddf596905392603897c3dc4653b1287c6c347e605d` |
| 已付旧 public bundle | `reports/r1-remediation-01/storage-source-inventory/B/public-bundle.json` | `d4aaddb10fedc7204cb8e278bb998380c59eff44ce8c7a4dac0be85453bf62e4`，415965B |

准备包同目录还包含 `claim-binding-request.json`、`calculation-request.json`、MD 与 `receipt.json`。可复用的离线复算/反控脚本在 `RUN/roles/executor/r1-remediation-02/w09-bridge/prepare_w09.py` 与 `selfcheck_w09.py`，其 SHA 均在 handoff；**不能在原位置运行它们**，因为默认写回中央新 attempt。需要复用时，只复制小型声明数据与脚本到本工区，改为接收本包路径参数、输出本包目录，并记录原始/派生 SHA。不要复制现有 hardcoded 输出路径后直接执行。

两份原件的 SourceRef/content SHA：年报 `7f1431d66eae399d4b35639bb650e23287c7f52dacbb47b4b4a197fb5026d6a2`；H1 `d0dba19ede6e35ae3e127a1da91a42f04262e90d14efeb847bdfbff9b6354a5f`。source_id 为现有 `urn:company-wiki:source:sha256:<SHA>`，不要新建来源身份。原件 bytes 已由 SourceVersionReader 实读；本包使用页文本与旧来源收据，不伪造本轮打开/下载/模型事件。确实缺页时先写明缺页及影响并报告 ROOT，同时完成不依赖该页的工作。

## 3. 必须理解的事实与修复边界

### 3.1 49 个不同 claim，不能把审查集合直接相加

原集合 storage13/process28/analyst28 的并集是 **49**，旧真实角色为31个 `mechanism_direction` 和18个 `conversion_assumption`。准备包已把49个旧摘录逐字定位到源页，给出29项本业务摘录、18项明确间接价格背景、2项未知机制建议。建议是作者准备，不是独立经济签收。

- Biology：H1 p12 页首是 TIDES/测试业务，自己的 `（3）生物学业务` 在下半。其9个 activity claim + driver 应使用自己的连续段，不拿固定页首650字符。年报 p14 的 Biology 自身段提供历史基准/方向。
- 三个 Biology H2 rebase 是分析师条件金额，建议 `conversion_assumption`；年报 p183 精确基数2677.17503051 CNYm 减 H1 p11 可比1251.6049 =1425.57013051 CNYm。说明“未来H2若重复可比H2”及舍入，不再使用与其无关的 TIDES 基准理由；不得改称未来已报告实绩。
- 18个化学/TIDES价格 claim **原本就已是 `conversion_assumption`**。保持这个正确反控；年报 p16 价格压力直接说测试/生物学毛利，不能叫化学已观测净价。若继续用于化学，写清跨业务间接市场风险、净价/组合及其分析假设，或者换用有真实同范围证据的支撑，不能靠换标签掩盖范围。
- non-TIDES：H1 p11 的 R/D&M 业务段支持经营方向，Chemistry 总收入含 TIDES；D&M 与余项不能共用一个“已观测统一活动量”。未来幅度及0.6/0.4延续仍是条件，并非源页提供的分布。
- TIDES 后期 activity：用其自己的客户/分子段及相邻金额/限定，项目/客户数不等于未来确认收入。
- `claim_driver_other`、`claim_driver_discontinued`：只有历史下降/零收入与处置分类上下文，不能套正向经营链。真实弱化 driver 命题、证据类型/角色及范围说明，或按现有 schema 移除无根据的机制主张，同时保留收入加总和负贡献。不能向 native enum 填准备 JSON 的 `unknown_mechanism_no_role_fix`，它只是准备诊断，不是正式字段值；不得造机制来完成固定数量配额。

### 3.2 RPO 预期与历史实绩分开

年报 p184 的 `4,220,706.46 万元预计将于2026年度确认收入` =42207.0646 CNYm，建议参数 kind 从 `reported_fact` 改 `management_guidance`，数值 claim 使用现有合法 `value_range` + `exact_value`，说明是发行人预计的一个点，不是经验区间/未来 actual。FY25 末 RPO 存量仍可为真实 point-in-time reported fact，不能用“future year”关键词一刀切拒绝合法存量或已完成窗口。

这个预期参数旧版本没有收入 DAG 消费，纠正本身不改预测数字。它不是全年硬下限，不能再加全部 H1 实际或新订单，也不能擅自分给子业务。保留原披露日、opening-cohort范围与尚未识别的兑现分配。

### 3.3 最大驱动必须有独立经营桥

保持六个互斥分区，TIDES 仅计一次；研究 cross-check 分解 `non-TIDES = 小分子D&M + 残余`。残余不是独立披露的 Research-only 收入。

准备桥已展示：FY25 D&M199.2亿元、H1 FY26 D&M149.9亿元/+72.7%；源数均有 physical page、精确连续范围、单位和 JSON pointer。以下只是应能复现的旧Base条件推论，**不是必须维持的新预测答案**：

- H1 残余同比约5.62%，与 D&M +72.7%不同；不能由此机械规定未来增速。
- 旧 Base FY26 non-TIDES35519.58 CNYm、H2约17793.63 CNYm。在残余H2重复可比H2的条件下，D&M H2隐含同比约35.30%。
- 旧 Base FY28 non-TIDES46008.52 CNYm；残余保持FY25收入的条件下，D&M需约FY25的2.05倍。残余条件变化应改变D&M隐含要求，而不是暗改旧Base。
- non-TIDES FY28增量约20912.67 CNYm，占集团**净**增量约65.82%；旧输出正向 driver 增量分母的份额约61.57%，分母不同，不混写。

执行者应独立重建简洁 bridge、关键敏感性与反证，可选择已有 native 互斥/derived/sum 结构或研究 cross-check，只有独立依据才调整正式路径。不得为贴近管理层 guidance 反推 Base，不要求无未来 actual 就全部 null。项目/客户/分子/反应釜容量 stock 不能直接乘虚构 ASP/利用率；新增699与期末净变化不等于测得取消量。H1 p139 的履约进度/控制权、p186 的单客户>集团10%风险不能被分配成未知子业务份额。单位换算/显示舍入/条件压力与经验校准分别披露。

## 4. 实施步骤与三个大节点

### A：冻结输入、判据与独立基准

1. 继续工区 `docs/plans/r1-research-20261023/` 的 `task_plan.md`、`findings.md`、`progress.md`，明确本卡所有权和下一步。保存开工 Git/Python/RF版本及原输入SHA。母 PWF 不写。
2. 读取上表、原W09卡及旧final3相关说明；将需要的小型研究数据放本包 `inputs/`，记录源→派生关系。保存49项集合、旧角色及 target/period，准备会暴露原来错引的对照，不把合法条件预测写成引擎bug。
3. 在看到正式新数字前保存 `research/acceptance-checkpoints.json`：引用自身范围/跨期转换、预期vsactual、最大驱动组件、互斥范围、单位/舍入、未来未知、反证及金额暴露。以真实语义判据为准，不以“新收入必须更高/低”作为GREEN。
4. 保存简洁独立组件桥和旧路径对比。准备 bridge 可复用，但独立审查者必须自己复算关键量级，不能仅读作者生成的PASS布尔值。

**A完成即可继续B，无需等待人工签收。**

### B：新输入与真正原生离线执行

1. 将封存旧输入复制为本包新 `forecast/main-input.json`，新 forecast_version，不覆盖旧记录。按49项逐条修复引用、target-own范围、角色/推导理由；没有支撑的机制诚实弱化，不能只换名字。新增研究项使用现有字段，未知诊断放研究 sidecar，不扩展正式 schema。
2. 记录逐项 diff：旧/new `claim_id`、source_id、locator、连续excerpt及SHA、role、target、parameter kind/rationale/value/formula/来源变更及理由。来源历史 capture 保持其真实原事件；额外记录本轮消费的 source-page inventory/选段SHA，禁止伪造 receipt 或把复用说成下载。
3. 完成RPO、Biology自身重基与最大驱动桥。构造一个有经济意义、预先声明的共享压力版本 `forecast/stress-input.json`，保留六分区与共同shock/时点/FX只计一次；不能简单改文件名当压力测试。已有压力可复用逻辑但必须更新已修引用/角色并解释共同根因。
4. 只有变更后的草稿才运行 `lint_input.py` 和 `fix_hashes.py`；先作者修好内容，再刷新hash，再冻结调用输入。不能对已捕获输入事后改hash，不能改验证器迁就本公司。
5. 对 main、stress 各运行真正 native `validate`、`compute+render`、`snapshot create`，使用指定 RF工区脚本。每次都用现有审计 `execution_request build → audit_run capture`冻结确切消费字节，保存所有失败尝试，不用手写“命令已执行”列表代替 native 输出。
6. 报告、快照和 registry 对账：原始/可比基数、三情景年度路径、六分区集团加总、增量分母、H1+H2、RPO没有重复加总、主/压力实际变化、claim/parameter trace、输出和snapshot真实输入SHA一致。尚未识别的未来量保留unknown和影响，计算成功不等于经济质量认证。
7. 将通用经验写回三张现有 references：最小必要解释与反例，去重已有段落，不新建第四套方法/审批。用一个不同公司/业务结构的离线合成例（例如SaaS平台+服务、存量订阅+新产品）检验范围/经营桥思路，不把D&M、公司名或中文标题词变成通用代码规则。

### C：独立全面复核、修复与交接

1. 调用一个或多个**未参与实现的独立agent**，给实际基线、diff、原件页证据、完整输出、执行记录和检查点，不给“应该通过”的结论。至少覆盖49项（含18正确反控/2真实弱化）、RPO、全部关键收入数字/币种/亿→million、主/压力native链、经营桥与最大driver、三方法卡泛化、代码质量及未完成项。若有helper源码变更，还须审查硬编码、模块边界、负控和旧行为兼容。
2. 审查必须记录 `reviewed_code_sha`（或明确各源码SHA）、`reviewed_artifacts` SHA与输入版本、逐问题位置/根因/严重度/修复建议；审查者至少独立执行关键复算/实际CLI探针。纯方法研究也应独立审读，不能因为无源码就省略。
3. 可修复问题全部修复，复跑受影响的B大节点，不无故重复所有旧网络/模型步骤；独立agent复核**最终**版本，不拿修复前收据签收修复后代码。真实外部未知不靠造值消除，明确它限制了哪项结论、金额和用途；未解决重大实现/事实错误不能交付“通过”。
4. 产出交接接口，清理所有本包临时目录并验证原状态，提交本分支。本包不merge、不安装、不推送主线。可以正常推送本包codex支线，记录实际推送状态，不force-push或创建新的remote。ROOT接收后串行导入中央run、适配新summary、W12四审与主线发布。

## 5. 原生CLI与可复现录制：用实际接口，不猜参数

已确认工具位置：

- RF：本工区 `scripts/revenue_forecast.py`、`scripts/revenue_backtest.py`、`scripts/lint_input.py`、`scripts/fix_hashes.py`。
- 只读审计录制器：`C:/Users/郑曾波/.agents/skills/revenue-forecast-audit/scripts/audit_run.py` 与 `execution_request.py`；开工记录其实际SHA，不改它们。
- 可用Python：`C:/Miniconda/python.exe`；原回放也用过 `C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe`。选一个实际可用解释器并记录版本，不能静默切不同版本；`PYTHONPATH`不得把imports导回其他RF工区。

先保存上述工具的 `--help` 和 backtest `create --help`。本卡撰写时的 native 形式为：

```text
python scripts/revenue_forecast.py <INPUT> --validate-only --verbose
python scripts/revenue_forecast.py <INPUT> --output <JSON> --markdown <MD>
python scripts/revenue_backtest.py create <INPUT> --version <NEW_VERSION> --output <SNAPSHOT_JSON>
```

这些是被 recorder 启动的**子命令形状**，正式验收不得仅直接跑后手工补一张capture。

隔离方式：在本包用现有 `audit_run.py init --root <delivery/w09/recorder> --company 药明康德 --as-of 2026-10-21 --run-id w09-rf-research-20261023` 建本地录制run，使用实际返回的run路径。为本地run写scope，其profile=P1，模型/下载调用均不启动、max_cost_usd=`0.00`，只记录本包路径与已有配置指纹；不复制中央run的陈旧repo_roots/许可链。不读取密钥。

`execution_request.py build` 的现有模板字段为 `request_id`、`purpose`、`profile`、`native_adapter: revenue-forecast/business/1`、`request`（实际native输入对象）、`command`（argv数组，输入位置只出现一次`{request}`）。scope使用`resource_limits`，deploy使用`profile`+`caps`；二者取更小限制，均是本地执行描述，不是人工授权文件。build使用：

```text
python <execution_request.py> build --scope <LOCAL_SCOPE> --deploy <LOCAL_DEPLOY>
  --template <LOCAL_TEMPLATE> --out-root <ABS_DELIVERY_REQUESTS_ROOT>
```

读取实际返回 `execution_request.json` 的 `argv`、`request_file`、`input_argv_positions`、`request_sha256`、`request_bytes`，用现有 capture 消费它们：

```text
python <audit_run.py> capture --run <LOCAL_RUN> --role executor
  --timeout-seconds 210 --max-log-bytes 131072 --max-input-bytes 4194304
  --freeze-input <BUILT_REQUEST_FILE>
  --expected-input-sha256 <ARG_INDEX>:<BUILT_SHA>:<BUILT_BYTES>
  -- <ACTUAL_BUILT_ARGV...>
```

argv通过Python `subprocess.run(list)`传递，不拼字符串/eval；工具会将输入实参替换为实际冻结消费副本。检查 `child_started`、exit、input/output_complete、consumed_unchanged、截断和清理结果。native输入在argv重复出现时按实际help使用`--freeze-arg-index`，不猜固定索引。每次改草稿后重新build新request，不复用旧SHA。

设置 `REVENUE_PUBLICATION_REGISTRY` 到 `delivery/w09/registry/publications.jsonl`，恢复进程原环境，禁止默认写母仓或安装目录registry。版本包含本包和main/stress；快照write-once，重跑用新文件/版本，不删旧快照伪装首次执行。

## 6. 测试包、资源和恢复

仅在A/B/C大节点集中检查，不增加小签收。最低测试包：

| 范围 | 必须验证 |
|---|---|
| 引用与角色 | 49集合无漏重；自身业务连续范围/物理页/源SHA；18原正确价格角色保留；3个rebase合理转换；2未知不造机制；错业务同句反控 |
| 预期/实绩 | 同一页历史实际、RPO stock、未来预计分开；合法条件和已完成窗口不被误拒绝；native trace/render一致 |
| 经营桥 | 单位、舍入、六分区、TIDES唯一计数、D&M+残余可复算、H1/H2及FY28条件暴露、不同增量分母、反证真正影响条件或解释不改原因 |
| 正式E2E | main/stress各自真实validate→compute/render→snapshot→独立registry；确切冻结输入与实际输出对应；所有失败保留 |
| 泛化/质量 | 不同业务合成正反例、无企业生产特判；方法卡无新门禁；有源码bug先RED再实现，测同一共因而非复制实现 |
| 隔离/清理 | 原件/只读输入SHA不变、母仓/安装/中央run未写、临时目录起止一致，最终工区每一未提交路径可解释 |

复用相关既有测试（先查看实际文件和现行测试命令）：`tests/test_research_evidence_roles.py`、`tests/test_m3_evidence_roles.py`、`tests/test_input_construction_consistency.py`、`tests/test_input_semantics_e2e.py`、`tests/test_evidence_input_lineage.py`。方法-only无需无故扩展全仓数十分钟CI；如有源码变更，跑影响面对应测试+必要回归并交ROOT大节点统一全套。测试目录有自己的夹具，合成例不能伪装实证。

包的新增网络/模型/下载成本为**0**，不创建/重置费用账本、不释放旧unknown hold。建议持久交付≤32MiB、临时≤64MiB、日志每call≤128KiB、单call210s；观察这些上限，靠去掉重复中间副本维持，不复制原件、不省掉关键证据。若确有必要超限，报告真实原因给ROOT，不自行付费或扩大生产配置。

临时目录限定本包 `delivery/w09/tmp/` 或`TemporaryDirectory`：测试前记录是否存在及清单，失败finally也恢复；初始不存在则测试后删除，初始存在则不动已有内容，另建唯一子目录。保留正式capture/request/失败收据/输出，清理收据引用其SHA；递归删除前核对解析后的绝对路径仍在本包已声明tmp内。不能用“恢复测试”删除原件、旧run或其他owner文件。

## 7. 必须交付的文件与JSON接口

独立三份PWF在本工区`docs/plans/r1-research-20261023/`；下列产物均在`delivery/w09/`，不写中央run。

```text
inputs/readonly-inputs.json
inputs/consumed-inputs.json
research/{acceptance-checkpoints,claim-changes,component-bridge,sensitivity,remaining-unknowns}.json
research/{research-memo,method-changes}.md
forecast/{main-input,main-forecast,stress-input,stress-forecast}.json
forecast/{main-forecast,stress-forecast}.md
snapshots/<MAIN_AND_STRESS_NEW_VERSION>.json
registry/publications.jsonl
recorder/ ... 实际命令、冻结输入、stdout/stderr、事件
review/{independent-review,review-fixes,final-independent-review}.md/json
cleanup/receipt.json
handoff.md
handoff.json
```

目录不必另造数据库；允许在上述同属本包目录加可复算小脚本/日志，manifest列出全部真实产物。正式JSON字段以当前RF schema为准，下面 sidecar 是跨harness交接，不注入正式forecast输入：

**`inputs/consumed-inputs.json`**至少有：`schema_version`、`package_id: W09-RF-RESEARCH`、`rf_base_commit`、`rf_implementation_commit`或明确未提交源码SHA、`python`、`rf_cli_sha256`、`recorder_sha256`、`source_inputs[] {logical_name, path, sha256, byte_size, locator}`、`summary {generation: old_paid_w07, path, sha256, versions, actually_consumed, new_w08_consumed:false}`、`root_input_manifest {path:null,sha256:null,status:not_supplied_nonblocking}`。实际没有从summary引入内容时`actually_consumed=false`，禁止为了填表写true。

**ROOT输入版本预留**：消费映射中注明供ROOT后续替换的`source_refs[]`、`summary {path,sha256,versions}`及`effective_versions`。若已有assembler/重放脚本，可接受可选版本manifest；不为这项预留强制新写框架。缺省继续旧已付摘要离线阶段并如实记录。若ROOT后续提供新manifest，核对真实SHA并在**新**输出版本记录实际采用变化，不覆盖本包旧capture；字段不兼容报告差异，不假定新摘要已生效。本包不等待它才开工，也不负责发布W08/中央W12。

**`research/claim-changes.json`**：`expected_union_count:49`、`rows[] {claim_id, old_input_pointer, old_source_id, old_locator, old_role, new_source_id, new_locator, new_excerpt_sha256, physical_page, contiguous_span, new_role, target_type, target_id, parameter_changes, rationale, resolution, remaining_limit}`，以及`old/new_role_counts`、18个正确价格反控、2个unknown处置。新增/移除claim须保留旧ID映射，不能让集合统计因删条失真。

**`component-bridge.json`与`sensitivity.json`**：每个数字有`value`（金额CNY million、比率fraction）、`unit/currency/period`、原文physical page+locator或准确native JSON pointer、`input_ids/formula`、`role`（reported/derived/condition）和`rounding_basis`；结果含组件→non-TIDES→集团对账、条件量级/分母、压力变化/反证、unknown/金额暴露。不能把显示区间叫经验置信区间。

**`handoff.json`必须从共享`handoff.template.json`填真实数据**：`schema_version=r1-harness-handoff/1`，`status`仅填`COMPLETE`或`COMPLETE_WITH_EXTERNAL_LIMITS`，沿用`code_base_commit/start_head/final_head/workdir`等公共字段，不新增第二套交接schema。最后一次仅装入handoff的提交，用其前一份实施commit作为`final_head`，另记录该文档提交即可；独审始终绑定产品/数据文件SHA，不要求自指未来commit。W09专属内容放一个`research`扩展对象：

```json
{
  "research": {
    "implementation_commits": [],
    "source_tree_sha256": "填实际最终源码/方法清单hash",
    "claim_coverage": {"expected": 49, "actual": null, "preserved_price_negative_controls": null},
    "native_calls": [],
    "summary_generation": "old_paid_w07",
    "new_w08_consumed": false,
    "remaining_unknowns": []
  }
}
```

`research.native_calls[]`必须列operation/main_or_stress、request与capture路径/SHA、实际输入SHA/bytes、实际output/snapshotSHA、exit及complete结果；公共`artifacts[]`列相对路径/SHA/bytes；公共`independent_review`指向最终独审实际文件/SHA、被审版本和问题关闭情况。unknown放公共`external_limits`和research具体暴露；后续采用新摘要、中央run导入及W12四审放公共`root_next_actions`，不能伪装本包已完成全循环。

交接前`git diff --check`、范围检查、完整工区status解释。仅显式stage本包三方法卡、真正必要且审过的helper/tests及小型交付；不stage其他目录/原始文档/运行时隐私或密钥。先commit实施与测试，再commit最终handoff可避免收据自指。记录独审源码hash可在handoff-only commit后仍对应同一源码，不能以“有新commit”自动作废或拿旧源码审查冒充新源码。由ROOT负责合并、推送主线与安装接入。
