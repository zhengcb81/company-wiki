# G3-SOURCE-FACTS：真实来源准备与内部原件空间核实

**状态：ready，可现在独立开工。只读调查包；不是生产迁移/删除施工包。**

## 1. 任务与完成条件

本包供应PWF R2/R4的真实决策依据。生产九样本目前有S01–S04 retired/缺公开日、S05/S06旧other、S07证券名标签/公开日NULL、S08活动日期与published_date冲突、S09电话会未统一登记。试点fixture不能证明生产metadata正确，文件存在也不能证明应复活retired。另RAW-DUP工具已完成，历史约158MB跨根验证不能证明CWP内部真实物理收益。

交付两项：①九样本逐份原文/官方来源/目录事实与retired追溯，小范围可应用metadata提案；②仅company_raw内部重复的真实上界、有限实读、是否值得进一步对象化的判断。缺证据保持unknown/conflict，收益不足可得出不迁移；不靠“全核实成功”凑结论。MAIN以后经正式入口应用生产，本卡不写生产、不重造解析器或duplicate工具。

## 2. 独占目录与写集

CWP基线master`5930a644453ed46494c2c83c5ecfb97767fa9492`。新工作树`C:/Users/郑曾波/Projects/_g3/SOURCE-FACTS/company-wiki`，分支`codex/g3-source-facts`，与CWP-MAINT目录互不包含：

```powershell
git -C 'C:/Users/郑曾波/Projects/company-wiki' status --short
git -C 'C:/Users/郑曾波/Projects/company-wiki' worktree add -b codex/g3-source-facts 'C:/Users/郑曾波/Projects/_g3/SOURCE-FACTS/company-wiki' 5930a644453ed46494c2c83c5ecfb97767fa9492
```

仅可写本工作树`docs/implementation/g3-source-facts/**`和`tools/g3_source_facts/**`（本卡只读提案生成/验证脚本和测试），scratch=`.planning/g3-source-facts/scratch`。不改src、已有RAW-DUP/benchmark工具、总PWF、仓内`config/**`、CLI/Store/reader/AUTO；第6节自己的scratch只读调查配置可生成。不写/下载到生产companies、不写生产SQLite/sidecar/ET目录。若要增加生产接口或修现有工具，交MAIN具体缺陷，不擅自扩写集。

## 3. 实际只读输入与边界

- live CWP根`C:/Users/郑曾波/Projects/company-wiki`；生产配置`config/source_catalog.yaml`，DB由配置解析到`.source_catalog`，不可假设SQLite文件名。生产公司原件在`companies`，只读打开；owner `config/source_acquisition.yaml`不使用、不改。
- 冻结样本登记：`benchmarks/narrative_document_types/samples.json`（S01–S09完整SHA/bytes）、`golden.json`、README；`g1_sample_manifest.json`是P01–P09早期别名，不混作当前source ID。从生产登记中查真实document/source/version/location ID，不拿样本编号造SourceRef。
- ET原始TXT：`C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts/transcripts/MSFT/MSFT_Q4_2026_earnings_call.txt`，66324B、SHA`4ac3b4f0fa1be928b56b4ef9775cac694a1712d46785bb1fa28d2a6a68d7852a`；只读该明确样本/必要已有sidecar，不启动scraper、翻译或扫43份全部历史。若实际不同，记录差异，不猜其期次/公开日。
- SQLite只用官方只读reader或`mode=ro`+`query_only`，一轮读事务取所需事实/版本。不构造Store/writer，不PRAGMA迁移/VACUUM/backup，不复制整个222MB库。发生并发变化报告观测版本/不能证明稳定，不能用immutable忽略WAL或阻止别的任务。
- 公开网可只读查公司IR、交易所/CNINFO/SEC等一手元数据；不读FMP/API密钥、不付费、不使用LLM。单次网页最大5MiB，累计网络响应上限50MiB，重试总次数有界，来源访问失败保留unknown。不要下载一整份重复PDF来证明发布日期；确需小官方文件只放scratch并清理，记费用0与下载实际次数。
- 原文读取总预算512MiB（metadata核SHA与R4实读合计，重复读计入）；RAW-DUP每轮明确最多20组、最多256MiB、120秒，两轮合计不能超总额。不恢复全46G、不全盘递归/全文md转换、不云hydrate/跟随reparse；数据库元数据与原文字节计量分开。

## 4. TDD先框住提案，不先改事实

先在`tools/g3_source_facts/tests`写反例：只从文件名推公开日必须标unverified；活动日不等公告公开日；原文SHA不匹配禁止建议verified；retired原因未知不能建议active；两个官方记录冲突保持conflict；sample/fixture ID不能当生产ID；外根/同一physical file/hardlink不计内部多副本；未实读不计verified收益；超过字节预算停止而非报完整。

提案脚本只产JSON/小Markdown到本卡报告根。用tmp小SQLite/原件夹具验证读取阶段0writer/0源目录写、坏SHA/缺日期、no-op/冲突、报告恢复。脚本不附apply按钮/DELETE/UPDATE/自动sidecar写；输出不是新的人工许可receipt，也没有authorization/token/expiry。

## 5. 来源核实的逐项方法

1. 从冻结samples定位九原件、完整SHA与字节；先stat/云标记/路径包含，预算内一次stream hash，不从filename猜事实。只抽必要页的原文日期/封面/证券/期次信息，不留全文。PDF需要视觉辨识时按pdf技能读取选页，渲染放自身scratch。
2. 用生产只读事实匹配location→source→document/version/acquisition记录。S01–S04退休追正式journal/scan/supersession记录，区分真正撤回/被替代、旧派生退休、扫描missing/误分类或未知；明确文件尚在与版本可复用不是同一事实。无合法依据不提出active恢复。
3. 对年报/半年报/季报/招股/增发/可转债/两IR，核官方证券代码、表单、财年/期间、语言、公开时间、相关公告链接与accession。明确公开日、活动日、文件封面日期、下载日/mtime各自含义，published_date只取可核真实公开信息。S05/S06分类采用已发布R1正式融资族，不造新枚举；市场和security_id使用当前正式identity规则。
4. S09从TXT正文/已知ET回执核ticker、FY2026 Q4、原语言、日期。旧抓取无可信provider receipt就保持legacy_unverified；不能补写假历史下载回执，也不因未翻译拒绝入库。给MAIN现有ET导入/复用接口的最小请求和当前caller定位，不执行导入。
5. 产每样本`no_change/update_metadata/register_new/do_not_reactivate/unresolved`建议。选一份元数据可核的有价值IR或TXT、一个已有合适纯流程零模型skip候选，编制pathless生产SourceRef建议（已登记才有ID）。没有合适零模型skip也明确缺口，不能为凑样本下载或把业务文档误当无价值。

## 6. CWP内部空间核实

复用现`tools/raw_duplicate_audit/cli.py`的scan/verify，不改工具、不执行delete/move/hardlink/object迁移。读取live config后在自身scratch生成**只含company_raw且路径显式指回live companies/DB**的调查配置；`catalog_dir`绝对定位真实库，不能指向worktree空库。此配置不是生产更新，不复制owner acquisition配置。

先离线fixture确认该配置过滤：未配置外根不被stat/hash，用于内部收益的组全部成员root_id=company_raw。现工具会读取全库登记元数据并报告unknown_root/全局registered_totals；这些诊断可保留，必须标成全库统计，不能当company_raw统计或要求它们全变成0。最终raw_space_decision单独汇总内部组，不修改现工具来凑限定报告。实际参数使用现有CLI：`scan/verify --config <自身绝对配置> --project-root <live CWP绝对根> --output <自身报告> --max-groups 20 --max-read-bytes 268435456 --deadline-seconds 120 --max-detail-rows 100`。下一轮max-read-bytes还须取本卡剩余总额与268435456的较小值；未读完标partial。不要使用`--hash-catalog`把完整数据库SHA再计作本轮raw实读；默认保留元数据/只读事实证据即可。不使用`--overwrite`覆盖未知文件，Git报告不带本机绝对路径；必要local-output留本卡ignored本地根。

列总候选/已读/因额度未读、same-path/hardlink/不同物理文件/缺失/云占位/状态未知，分别给注册逻辑上界、实读相同字节上界、实际allocation能证实的值或unknown。只报告company_raw内部多余distinct physical copies；跨Dayu/Dropbox副本、同inode两location、语义相似/同size不同SHA、唯一raw不能计节省。verified_duplicate_bytes也不自动等于可以安全释放的allocated bytes。

最后输出`no_migration_recommended/prepare_followup/not_enough_evidence`决策及成本收益、覆盖范围/未知项。有显著收益则给MAIN现有SourceRef/locations全部引用如何保留的后续步骤建议；**本卡不实施**。空间释放实际0；历史已清5.66GB和原46G不得相加为本包成绩。

## 7. 集中验证与恢复

一次责任包：`python -m pytest -q tools/g3_source_facts/tests`；真实环节是只读九样本证据核实+RAW-DUP有界scan/verify，不重跑九PDF全文解析/摘要benchmark。报告校验未知/冲突不会被转成ready，sourceIDs全为生产事实或明确未登记，预算读数字可加和，所有净释放字段0。

运行前/后核生产配置字节、所读样本大小/SHA、生产DB只读关键事实/文件元数据与小表计数；若MAIN合法并发写发生，记录它与本卡0写的边界，不要求全DB SHA永不变。自身测试/网页/渲染/tmp新副本finally恢复absent/原清单；只留小审计结果、URL/访问时间、简短原文locator，不提交原文PDF/TXT/整页HTML/密钥/机器绝对路径清单。与MAINT卡共享输入只读，无锁生产/修改原文件。

## 8. 可直接消费的交接格式

本仓`docs/implementation/g3-source-facts/{task_plan.md,findings.md,progress.md,HANDOFF.md,handoff.json,metadata_proposals.json,raw_space_decision.json,evidence_index.md}`；正常commit，可推自己的分支、不合master。JSON若忽略，只精确add本卡结果。

`metadata_proposals.json`：

```json
{"schema_version":"g3-metadata-proposals/1","observation_time":"实际UTC","catalog_observation":{},"items":[{"sample_id":"S07","source_id":null,"document_id":null,"source_version_id":null,"location_id":null,"content_sha256":"实际完整SHA","current":{},"proposed":{},"action":"unresolved","retired_reason":null,"evidence":[{"field":"published_date","url":"一手实际URL或null","locator":"原文页码/段落或元数据字段","observed_value":null,"status":"unknown"}],"conflicts":[],"main_request":null}]}
```

`raw_space_decision.json`：schema=`g3-raw-space-decision/1`，范围company_raw；实际命令/输入版本、candidate/verified/incomplete组数、read_bytes/deadline/limits_hit、registered_upper_bound_bytes、verified_distinct_copy_bytes、allocated_bytes（不能证明则null）、releasable_bytes（不能证明则null）、deleted_bytes=0、decision、reason、followup。不能把unknown写0。

`handoff.json`：schema=`g3-handoff/1`、lane=`G3-SOURCE-FACTS`、base/head/branch/worktree/commits/changed_paths/tests真实command/exit/seconds/counts、protected_state/cleanup/remaining；external_effects含实际public_http_requests/downloads/read_bytes，model_posts=0/production_writes=0/raw_deleted=0；main_integration引用上述两个报告及必要正式写入口/预期修改范围。HANDOFF把可应用、未知、冲突分清；MAIN再核当前事实并经正式有限入口应用，不能直接执行报告内容或把文件路径传给下游研究层。
