# ET-S3 独立任务：统一电话会采集入口与有限批次

> 当前状态（2026-10-04）：已交付并合ET main 93fe52c。不要再启动本卡；新增硬deadline缺口使用et_retrieval_deadline_closeout.md。 下文启动基线为历史施工记录，以总计划当前状态为准。

## 可以现在启动；独占目录

唯一写入 worktree：`C:\Users\郑曾波\Projects\earnings-transcripts-s3-runtime`。公司Wiki、FF、RF、StockWiki、IQS、全局技能只读；ET不直接写CWP公司目录或catalog，由现有CWP importer统一保存。root负责跨仓联调。

基线仓：`C:\Users\郑曾波\Projects\earnings-transcripts\earnings-transcripts`，main/origin/main `4924d57044ae061d5fec3ccd4f1b7e74633f013a`，tracked干净；已有未跟踪 `.workbuddy-ai/`、`eval_results.json` 是旧工具笔记/评测，不复制进交付、不清理它们。

建议基于已发布commit新建 `codex/et-s3-bounded-runtime`、worktree到独占目录；若已存在同线目录先核status/PWF，不reset。所有本包实现、测试、`.planning/s3-et-bounded-runtime-20261003/{task_plan,findings,progress}.md`都只写此worktree。不要覆盖本仓旧活动计划或CWP总PWF。

## 目标与已完成内容

现代 `transcript_api.py`、`transcript_tool.py`已交付：精确FY/Q、一次download_authorized、immutable ProviderSettings、Fool默认disabled、FMP具名不可用、原语言、现行`/2` goldens。先复用，不重写W、不重复实现翻译flag或CWP importer。

真正剩下的是 `scraper.py` 旧批量入口与现代工具分化：

- 默认 `--source fool`，旧两个Scraper直接Session.get、resp.text/json，没有现代流式byte/deadline/host约束；FMP仍调用旧`/api/v3`，异常吞成空列表。
- 下载后默认翻译；`--source fmp --list`可落入下载/保存/翻译，`--source fmp --dry-run`可引用未定义`dry_counts`。
- list/dry-run开始就创建目录/日志；单请求timeout和sleep不能限制整个批次。

本包把旧CLI变为现代API的薄批量编排器：一个provider边界、一种未翻译原件路径、明确期间/限额、计划模式真正只读。不新建采集审批服务或任务数据库。

## 对外接口固定，内部批次行为明确

### 不改的跨仓协议

- FF经 `EARNINGS_TRANSCRIPTS_TOOL` 调用 `--request-stdin --include-source-payload`；输入`earnings-transcript-request/1`，返回当前ET `/2`。
- FMP与Motley serializer字段集、provider_payload_sha256、canonical_content_sha256/content_bytes、publication未知语义保持。不要原版本加字段，不伪造日期、不降成Motley形状。CWP import `/2`请求和`/3`响应由root持有。
- provider是否可用由现有ProviderSettings和真实能力决定；明确采集请求也不绕过disabled provider。缺key/402/限流/坏响应分别报告，不伪成功、不自动换季度/provider。

### 旧CLI收敛（本包可以新增内部参数）

- `scraper.py`保为入口，具体下载/发现复用当前`fetch_transcript`/provider transport；退休重复HTTP实现。新薄batch模块可放本仓，不要把网络细节复制第二遍。
- `--periods 2025Q4,2026Q1`作为**新的明确期间列表**；每项由同一exact请求验证。不把旧`--quarters N`当作fiscal quarter值。旧最近N季度仅在metadata discovery给出明确FY/Q后有限展开；无法唯一确定则`period_unresolved`/需明确期间，零正文抓取，不猜Q4。
- 默认原语言、不翻译；若保留旧翻译能力，只有显式`--translate`才调用。原有`--no-translate`/`--disable-translation`兼容为关闭。FF工具路径始终无翻译，不添加无作用flag。
- `--list`只做必要metadata发现/列表，零正文下载、零保存/翻译；metadata请求也计入额度。`--dry-run`完全零HTTP/写入，给本地可知的计划和unknown项，不造不存在的候选。两者在目录/日志/translator初始化之前结束。
- 新批次参数：`--max-requests`正整数、`--max-seconds`正有限秒、`--max-response-bytes`正整数（批次累计）、`--max-output-bytes`正整数（本次新文件）。每次HTTP前核剩余额度；单请求cap/timeout取现代API配置与剩余批次额度较小值。默认值明确写README，不设unlimited/隐式重试；不为吞吐用多provider fallback。
- `--output`覆盖本次原件/日志/缓存/临时/锁全部写入位置。已有原件不覆盖；重复内容复用，身份/字节冲突具名失败。临时文件失败也finally清理；正文不重复写入日志。ET不产生CWP source ID/公司目录/研究结论。

这些是本包接口选择，不能再另发一套手工授权文件/rights receipt。需要真实新wire能力时交root协调；当前工作足以在不改 `/2` 的情况下完成。

## 实施步骤与一个大节点

1. 读本仓AGENTS/PWF/Git、上述三入口与现有goldens。列legacy类实际调用者（仅测试的旧类随退役迁移；外部真caller留薄兼容），不要因旧主线118项曾绿就认为legacy没有bug。
2. 先RED：Fool默认disabled在旧/现代入口均零HTTP；FMP list零正文/写入；FMP dry-run零HTTP/目录变化；默认原语言不创建translator；明确期间不是recent-N；批次请求/秒/累计byte限额不能被重试绕过。
3. 重构旧scraper为薄编排，统一ProviderSettings/实际流式transport与错误；原语言默认、精确期间列表、计划先行。不得保留“现代API失败就旧Session直接抓”的后门。
4. 接批次limits和output隔离。付费/未知响应不吞为[]；超过资源cap返回具名partial/failure与已经完成的文档，不回滚/覆盖已有原件。只保存必要原件+小manifest，不生成翻译/完整重复正文cache。
5. 一次责任包+真实CLI离线E2E完成后，更新最少README/SKILL示例与本仓局部PWF、commit/push自己的codex分支并交接。现代 `/2` serializergolden应语义/字段保持，changed行为只来自legacy批次/默认翻译。

小helper/每文档不增加人工审查；不用coverage/固定场景数签收。复核在整个旧入口收敛节点一次完成。

## 独立测试包与恢复要求

- 复用 `tests/test_transcript_api.py`、`tests/test_translation_controls.py`和本仓实际CLI/provider tests，先查现有文件；不mock整段fetch为成功。
- 本地fake FMP transport给200/402/429/慢流/超大响应，**假key**；走真CLI dispatch→现代API→受限transport。验证累计请求/bytes/时间在执行层生效、超时关闭连接、0额度或disabled provider零请求。
- 用subprocess验证list/dry-run和显式periods真实退出路径；request日志只输出ID/状态/bytes/时间，不含key/body。已有output keep文件不动；默认翻译关闭时translator构造和翻译API次数均0。
- exact重复请求不覆盖原件，异常中断临时文件回收；短独立测试根同账号创建/执行/finally恢复，新下载资料测试副本退出删除。生产ET旧output/CWP配置/raw/catalog不变。
- 不读live FMP凭证、不发真实paid provider或LLM请求、不把fake能力报成live权益。真实provider本次状态unknown/此前402，现代具名失败继续保持。

最终一个集中责任包足够；红灯只重跑对应风险。旧类专属无价值镜像测试随实现退休，period/hash/原语言/错误/流式限制反例保留。

## 交接给总指挥

本仓 `docs/implementation/s3-et-runtime-handoff.md`：base/branch/commit、真实改动清单、legacy→现代路由表、CLI参数/默认值/退出码、periods与recent-N语义、limits前置和流式执行证据、现代`/2` golden无变化或需协调的真实diff、测试命令/结果/临时根恢复、明确live权益未知。

只提交代码、测试、小golden和简短报告，原件/翻译文件/成本CSV/大日志不入Git。发回commit及报告路径，不自行合main/修改FF/安装技能。root做一次FF→ET→CWP受影响链验证（原语言、FY/Q、hash、限额、不可用降级），再合并发布。FF-S3无需等你的内部重构完成才能开工。
