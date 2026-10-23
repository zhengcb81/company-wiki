# W11-CWP-SOURCES — 官方材料发现的离线根因修复

状态：**可启动**。ROOT 已创建并实际检出下述独立工区，代码基线为 a2f99db6，支线名已核。开工文档提交后的实际start HEAD见工区`START_HERE.md`及母卡同目录`dispatch.json`。只有本卡属于本 harness；ROOT 主线正在做 W08，不等本线逐步签收。

## 0. 交付目标与停止边界

复核真实已封存的官方 IR 发现结果、实际可取得的响应正文及既有发现代码，用跨公司中性小夹具定位**确定性漏解析、误分类和覆盖状态错误**。有真实可复现内部缺陷才改产品；若材料正文根本没有出现在已保存响应内，交付诚实的 external_limit 和可复查的不改结论，同样是有效交付。

本线是**离线工程**：0 新互联网请求、0 模型请求、0 新资料下载、0 生产来源库写入。ROOT 后续才在 W11/W12 的统一预算与新 attempt 里做真实有界来源恢复。本线不替 ROOT 重试网站、跑浏览器、开 provider、找密钥或采集原件。

## 1. 工区、基线与职责

- 工作目录：`C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery`。
- 支线：`codex/r1-w11-source-recovery-20261023`。
- ROOT 建区基线：`a2f99db676846b7f475def253c541e12c49ae5fe`。
- 本线计划：工区 `docs/plans/r1-source-recovery-20261023/{task_plan,findings,progress}.md`。
- 本线交付目录：工区 `delivery/w11/`。统一交接 JSON 的最终字段以母仓本卡同目录 `INTERFACES.md` / `INPUTS.json` / `handoff.template.json` 为准；不要另创一套签收 schema。母仓路径前缀为 `C:/Users/郑曾波/Projects/company-wiki/docs/plans/du11-source-closure-2026-10-18/harness_lanes/20261023/`。

启动先读工区 AGENTS.md、ROOT 总卡 README/INTERFACES/INPUTS/交接模板、本卡与原 W11 卡。核对 `git status --short`、实际 HEAD 和模块 `__file__`；若工区不可用或基线不符，报告具体差异，不能借用母仓开始施工。不要切换、清理或覆盖其他 harness 的工区。本卡唯一正本留在母仓上述路径，不复制第二份任务卡。

### 独占可写

1. `src/company_wiki/source_catalog/official_discovery.py`。
2. **实际 CLI** `src/company_wiki/source_catalog/official_source_cli.py`，仅限 discover 操作分支；import/capture/read/recover/project/replay/export 的语义不属于本卡。
3. `tests/integration/test_official_source_flow.py` 中发现相关回归；建议新增独立 `tests/integration/test_official_discovery_offline.py`，必要时新增本线专用的小型测试 fixture。不要改通用 conftest、共享测试 helpers 或其他线的测试。
4. 上述本线 PWF 与 `delivery/w11/`。

**禁止改写**：narrative_*、sections/layout/selector、transport/bounded_http/download_budget、adapter_process、费用账、共享 SourceRef/Acquisition DTO/schema、RF/FF/ET/Dayu/IQS、生产 config、共享资料湖、母仓 CURRENT_STATUS/README/INTERFACES。不新增 provider、公司名称白名单、第二发现注册表、缓存库、任务库或人工许可。类型判定来自共享分类器；若确需改它，先把精确输入、期望和接口建议交 ROOT，继续不依赖的部分，本线不越界修改或反复索要权限。

## 2. 已核实的真实证据与重要缺口

以下均只读，不能回写 sealed 旧 attempt。公共前缀：

`C:/Users/郑曾波/Projects/revenue-forecast-audit/runs/r1-20261021-cn-wuxi-apptec/`

### 必读证据

| 路径（相对于上述前缀） | 已核大小 / SHA-256 | 用途 |
| --- | --- | --- |
| `remediation/r1-final3-review-20261022/work_packages/W11.md` | 5795 B；`6a18ccf053525daff75f68cc07d586953b04d59e94d927a56f8fcd383ffa2ba3` | 原完整 W11 责任；本外包只承接 discovery 工程子集 |
| `reports/r1-remediation-01/fetch.md` | 18661 B；`1649aa7e13a674cf9ea209b7c4a511503894f3a528b2886d1573f152c1b50215` | FETCH-002：演示材料、IR/Q&A、公告窗口仍不完整；不是已证明价格或金额错误 |
| `execution_replays/r1-remediation-01/phase_b/research/phase_b_manifest.json` | 124325 B；`24d857e09fca9f8ee033434d602774ecfe9712beacb67d583617caa0d894546f` | 501 件封存清单；历史只读，不把后续文件塞回去 |
| `execution_replays/r1-remediation-01/roles/executor/commands/faa5bf2650964e9480566759c565ce11/stdout.txt` | 2839 B；`1c33f18b24354c5a30e1d71258cf09c89ad23baec43bc42111082bc2fe7e7f52` | 真实 discover 结果和真实 fetch receipt，不是完整 HTML |
| 同一 capture 目录 `input-0001-9c235138bbbf.json` / `consume-0001-9c235138bbbf.json` | 250 B；`9c235138bbbf066125fc40629578fe5c7f8840031b932b1130d2371cf6de5f4c` | 实际请求：2026-01-01..2026-10-21、30 items、1048576 B、20 s |
| `execution_replays/r1-remediation-01/roles/executor/events.jsonl` | 按 capture_id 精确定位，不整份复制 | 原 executed_command、frozen/consumed 输入及结果状态 |
| `execution_replays/r1-remediation-01/research/web_discovery.json` | 1507 B；`d4276ba93bf68b017c7ddbbbdd728498b0123a01d0e2479f886893a921c35b0a` | 搜索查询及 native response ID/lead；不能冒充离线可读搜索正文或穷尽 |

### 真实页面的已知状态，不可抹平

- URL：`https://www.wuxiapptec.cn/investors/announcement/ir-material`。
- receipt event：`official-index-6eed999bdccb40c595c01c5c4b76f16c`。
- receipt 记录真实响应 **486789 B**，SHA **`f1e822a8067c0b8eb7fc6376d8e1491acfa1ae3b60ce605db90c06326603396e`**。
- 实际 discover 结果仅三个 privacy/terms PDF 导航候选，`dynamic_content_unresolved`、日期未知、`coverage_status=partial`、`no_documents_claimed=false`。
- **ROOT 前置检查在该 audit run 和 CWP `.planning/shared-reading-production/r1-holdout-20261021` 的有限范围内没有找到这 486789 B 的原始 HTML 文件。receipt 的 body hash 不等于已保存 body。** 你必须先区分结果/receipt/完整正文是否实际存在。可以沿清单/原脚本引用做有界只读定位；不得全盘复制或为此重抓网页。
- 找到正文：校验确切大小/SHA，再注明材料位于哪个原生元素/JSON pointer/字符范围。找不到：在 inventory 留 `body_available=false` 和已查范围；禁止从三个候选“复原”486789 B 响应，禁止凭旧 sha 宣称 replay 已过。
- 可从真实结果构造最小导航反例，但必须标 `derived_minimal_fixture`、绑定上述结果 SHA、注明**并非原始网页重放**。纯中性 synthetic fixture 同样如实标记。

现有报告还包含 ET unsupported_exchange/0 requests 与 CN wire/fee unknown；**它们不是本线待修代码**。本卡不改 ET 供给，不反推费用，不释放旧 unknown hold，不把表格矩阵问题重做一遍。

## 3. 真实产品入口与当前能力

实际定义：

- `official_discovery.discover_official_documents(pages, *, entity, as_of_date, start_date, max_items=30, max_bytes=8388608)`：纯解析 page snapshot。
- `official_discovery.fetch_official_indexes(urls, *, max_bytes=8388608, max_seconds=120, transport=None)`：既有有界 GET；本线只可用 MockTransport 或明确 loopback 夹具测试，不访问实际 URL。
- `official_source_cli.main` 的 `--operation discover` 支持 `pages`（本地 HTML 文件）或 `urls` 二选一。
- **仓库不存在 `official_discovery_cli.py`。** 不要为匹配卡名新增 CLI；实际公共命令为：

```powershell
$env:PYTHONPATH = 'C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery/src;C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery/tests'
& 'C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe' -X utf8 -B -m company_wiki.source_catalog.official_source_cli --help
```

离线请求示例（在独占 tmp 中生成 `input_file` 的**绝对路径**，替换示例字段；不是生产配置）：

```json
{
  "schema_version": "official-discovery-request/1",
  "entity": "Neutral Instruments",
  "start_date": "2026-01-01",
  "as_of_date": "2026-10-21",
  "max_items": 30,
  "max_bytes": 65536,
  "pages": [
    {
      "input_file": "<owned tmp 中实际已创建的绝对 HTML 路径>",
      "url": "https://neutral.example/investors/",
      "mime_type": "text/html",
      "capture_id": "fixture-offline-one"
    }
  ]
}
```

实际命令：

```powershell
& 'C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe' -X utf8 -B -m company_wiki.source_catalog.official_source_cli --operation discover --request '<owned tmp 中实际请求 JSON 绝对路径>'
```

discover 的本地 pages 分支无需打开生产 catalog 或传生产 config。不要运行示例中尚未替换的路径，也不要把 `pages` 改成真实 `urls` 来“补验证”。

### 当前代码观察，只是调查起点

当前解析扫描 `a[href]`；带外部 script 或 loading 文本即记录 dynamic_content_unresolved；PDF 等后缀也会使 footer/privacy 链接进入候选；earnings 标题目前可被标作 transcript。外包须先用真实证据/中性反例验证每项是否是实际缺陷，不能预设必须改所有行为。

嵌入 JSON 是否实际含材料、空壳框架是否只有未执行 JS、页面是否已静态列全材料，必须分别判断。含 script **不证明**索引未解析；没有可解析 body **不证明**“无资料”。链接是 metadata lead，任何 title/kind 都不是内容验真或已读 Q&A。

## 4. A / B / C 三个大节点，无中间人工许可

### A — 冻结证据、期望和 RED

1. 读上述证据、当前模块和现有测试；记录真实 HEAD、dirty 路径、解释器、实际 import 路径。创建本线三份 PWF，记录不重叠写集。
2. 用 `evidence_inventory.json` 区分 original_snapshot / result_receipt / derived_minimal_fixture / synthetic_fixture。每项 path、bytes、SHA、上游引用、可支持和不可支持的结论写明。
3. 列“可观察行为 → 期望 → 责任 → 状态”表。至少覆盖：业务材料/法律导航、notice/deck/真实 transcript 或 Q&A/财报原件、主体归属、日期和 as-of、未知字段、相对链接、重复、静态完整/动态框架、内嵌结构、截断。
4. 先运行未改产品的最小正反回归；若真实观察到缺陷，保留原 RED stdout/JUnit 和失败断言。有缺陷要精确到输入节点/输出字段，不拿 fixture 自报结论作为 oracle；无缺陷路径如实记录`RED_not_observed`和实际all-pass，不为了满足“有RED”制造失败。
5. **无需等 ROOT 对 A 签收即可继续 B/C。** 无原 body 或无内部 bug 也继续完成覆盖、外限说明和独审，不进入无限查找/联网补齐。

### B — 共有根因修复和隔离验证

- 只有实际 captured response 包含材料却被漏掉，或真实 lead/result 能直接证明确定性误分类时，才形成产品补丁。没有可核内因则明确“不改”；不能为制造交付强行加 provider/抓取器。
- 保持既有纯解析 + 薄 CLI + 现有 transport 的分层。提取逻辑共用、输入有界、无 JS 执行/任意代码执行，不为某家公司/域名/年份写分支。
- 若支持某种内嵌结构，先证明来源是实际响应中可识别的声明性数据；限制处理大小/层数/条目，传播不支持/坏结构/部分解析。不要递归猜测所有字符串为 URL，不让外链脚本文件名变成材料。
- 沿现有结果 schema 表达 candidate/date_unknown/index_notice/partial、limitations 和 receipt；来源 metadata 不升级成 business original。共享 schema 需变更时交 ROOT 接口建议，本线不私自改。
- 时间窗口边界分别测试在 start、as-of 当天、之前/之后、非法日期/无日期。页面检索时间不替代材料发布日期；报告期间不自动等于发布日期；没有正文身份证据不得确认 issuer。
- URL 处理测试相对 URL、同 URL 多锚、query/fragment、非法 scheme/credentials、不同 URL 同标题。明确去重语义，不能用表面标题把合法不同材料抹掉。
- “Earnings release / presentation / event notice”不因 earnings 一词成为 transcript；Q&A/电话会身份只能作为可核的文档类型线索，**不能**声称已取得问答正文。静态法律导航不充业务资料。
- 保留实际来源查询 scope。只看一个 index，最多 checked_index_only；partial、截断、未知不能变成完整站点 coverage 或搜索已穷尽。

### C — 公共 CLI E2E、独立审查、交付

1. 使用独占 tmp、去标识小夹具和当前公共 CLI 本地 pages 分支真实 subprocess；禁网，核模块路径来自本工区。至少两家中性 issuer，交换顺序/名称也保持同一语义。不可只 mock discover 返回值或手写“预期通过”结果。
2. 若测试 GET 连接层，只用已配置 MockTransport/明确 loopback，正文为小 HTML fixture，响应大小/超时/HTTP失败沿当前接口传播；不改 budget 代码、不扩大上限。先复用现有相关测试，避免新造完整 transport 套件。
3. 检查 E2E 结束后：起始文件/配置逐字节不变、测试新增目录恢复初始不存在、无生产 raw/catalog/cache 写入、外部请求/模型调用=0。保留小型清理 receipt，不持久化整个 tmp 湖、源码副本或冗长完整网页。
4. **必须调用独立审查 agent**，检查功能完整度、代码架构、泛化、输入上限、覆盖诚实性、实际 CLI、正负控、误分类/日期/主体和清理；审查绑定最终产品源码 SHA/相关 commit。独审自己运行必要的对抗样本与合法正控，不能仅复述作者测试数量。
5. 发现问题全部修复，补共有回归，再由独立 agent 复审同一最终版本，通过后才交接。若真实外限无法消除，审查需确认分类诚实、无伪造通过；列为 external_limit，不把不可观察事实列成软件已修。
6. 正常 commit hooks，不 skip、不禁测试；清理当前进程 `PYTHONPATH` 后提交。只提交本线批准路径和小收据。**不合母线、不推母线、不安装技能**；可以正常推送本包codex支线，记录实际推送状态，不force-push或自行创建remote。

## 5. 测试入口与最低检查点

已存在且已实读的文件：`tests/integration/test_official_source_flow.py`。

现有相关测试：
- `test_discovery_notice_dynamic_future_and_unknown_are_explicit`
- `test_discovery_limits_do_not_turn_truncation_into_no_materials`
- `test_official_index_http_uses_existing_shared_budget_with_mock_transport`
- `test_cn_fundraising_index_and_old_ipo_exclusion_are_honest`

A/B 的集中命令（工作目录必须为本卡工区）：

```powershell
$env:PYTHONPATH = 'C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery/src;C:/Users/郑曾波/Projects/company-wiki-r1-source-recovery/tests'
& 'C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe' -X utf8 -B -c "from pathlib import Path; import company_wiki.source_catalog.official_discovery as d; import company_wiki.source_catalog.official_source_cli as c; r=Path.cwd()/'src'; assert all(Path(m.__file__).resolve().is_relative_to(r.resolve()) for m in (d,c)); print(d.__file__, c.__file__)"
& 'C:/Users/郑曾波/Projects/company-wiki/.venv/Scripts/python.exe' -X utf8 -B -m pytest tests/integration/test_official_source_flow.py -q -k 'discovery or official_index_http or cn_fundraising' -p no:cacheprovider
```

新增离线测试完成后执行它的实际路径，加上上述相关现有回归。若 conftest 重新注入路径，必须在 pytest 会话内部核实模块 `__file__`；外层命令通过不能代签内部 import。用专属 basetemp 并确认 cleanup，保留 raw stdout、JUnit、实际耗时/通过数，不反复跑全仓上千测试；全仓及跨仓验收由 ROOT 大节点统一安排。

最低测试矩阵（可以参数化归并，不要求每一小项独审）：

| 类别 | 正控 | 负控/限制 |
| --- | --- | --- |
| 材料分类 | deck、annual/interim report、明确 transcript 线索 | event notice、earnings release、privacy/terms、仅导航不能冒充 Q&A 正文 |
| 时间/主体 | 原可读日期在窗口内且 scope 归属明确 | 日期未知/非法/未来/旧材料、别的 issuer；scope 不能充来源身份核验 |
| URL/去重 | 相对链接解析、不同材料合法保留 | credential/scheme、query/fragment、重复锚、同标题不同原件 |
| 页面载荷 | 另一 issuer 的静态真实材料链接；已证实声明性内嵌材料 | 空 shell、仅外部 script、坏/不支持内嵌结构，未知保持 partial |
| 有界/公共入口 | pages CLI 真 subprocess、MockTransport 正常响应 | items/bytes 截断、失败响应，不能洗为 no_documents/完整覆盖 |
| 复原 | tmp 前后清单、预存 sentinel/hash 保持 | 不能写生产目录、不能留副本/本轮新临时目录 |

新测试应有语义价值；不要只镜像实现或把所有输入都拒绝来获得负控绿。若某矩阵分支未实现且不在已观察能力内，明确 not_supported / not_run 的理由，不伪造“全支持”。

## 6. 交付物与 ROOT 对接

本线 PWF 保持事实同步，最终：

- `delivery/w11/handoff.md`：一句话结果、共有根因/不改理由、产品改动、实际测试与独审、真实缺口、ROOT 下一步。
- `delivery/w11/handoff.json`：使用 ROOT 总接口；至少提供 lane/base/branch、产品 commit、允许写集与实际 changed paths、精确文件 SHA、测试原日志、独审原报告及其绑定版本、0 新联网/模型/下载声明、清理 receipt、external_limits。
- `delivery/w11/evidence_inventory.json`：可实读原 body 与结果/lead/derived/synthetic 逐项区分；不能把 response_id 当已保存 body。
- `delivery/w11/test_results.json` 和审查目录：实际命令、exit code、passed/failed/skipped、耗时、输入和最终源码 SHA。有真实RED则保留首次RED，不覆盖失败证据；无缺陷如实写`RED_not_observed`。
- `delivery/w11/cleanup.json`：初始/最终 tmp 状态、原文件 hash、只清本线新增、移除成功；真实原件不删改。
- `delivery/w11/root_followup.md`：可由 ROOT 当前已配置工具一次有界恢复的真实 lead/查询意图、验证条件、尚缺 body/日期/材料内容；不写猜测原件 URL，不把未取得影响估为0。

如果没有产品补丁：`code_change=false`、真实未改的产品 SHA、已验证能力和外限要完整交付，不为了 commit 而改无关代码。若审查后的最后一次 commit 仅装入报告，报告绑定的产品文件 SHA 必须与最终 HEAD 一致；不要要求报告自指自己尚不存在的最终 commit。

ROOT 接收后负责与 W09 新研究/W10 逐文档矩阵/W12 四审集成、真实来源恢复、母线并线/发布和 PWF 总入口更新。**本线工程通过不代表已取得新 IR/Q&A 原件，也不代表原公司审查已 clean。**
