# P5-RF：默认来源准备迁至现有SourceRef v2

**ready，可以立即开工；较大代码包。** 仅负责revenue-forecast，与P5-FF/P5-STORAGE和MAIN的CWP N4C并行。不是已经完成的RF N3a叙述consumer卡。

## 1. 背景与验收目标

2026-10-05实读RF已发布main `8a153f3387ae75fb172e70f8ab63ffd38100779a`：`scripts/source_preparation.py:prepare_source`仍默认`source_reader_v2=False`，CLI `--source-reader-v2`仍opt-in；legacy路径调用`company_wiki_source.select_artifact_roles/verify_artifact_reads`，会读normalized/summary/sections正文。这是CWP约2.826 GB旧derived不能删除的实际调用者。

现有v2实现、verified raw reader、RevenueSourceRecord builder和三仓E2E已在main；N3a叙述读取是另一接口，且已完成。本包**复用已发布能力，迁真实默认入口与调用者**，保持收入预测/证据/hash-pending等语义。完成后：只有原件、没有任何旧derived的来源，可经正常RF入口形成合法SourceRecord；对错误SHA/身份/期次/as-of仍明确失败。

## 2. 独占目录、基线与写集

- 源仓：`C:/Users/郑曾波/Projects/revenue-forecast`。该checkout为fcap `5319ee26`，两份`assurance/runs/weekly_alert.jsonl`、`weekly_manifest.json`是owner改动，别动。
- 新worktree：`C:/Users/郑曾波/Projects/cwp-lanes-20261005/rf-source-v2`。
- 分支：`codex/p5-rf-source-default`，从最新已发布`origin/main`开始；先核至少含`8a153f33`和正式N3a。
- 目录不存在且分支名未占用时，可以执行：

```powershell
git -C 'C:/Users/郑曾波/Projects/revenue-forecast' worktree add -b codex/p5-rf-source-default 'C:/Users/郑曾波/Projects/cwp-lanes-20261005/rf-source-v2' origin/main
```

若已存在，先核branch/status/计划归属，复用本卡目录或选择新的本卡兄弟目录并在handoff记录；不reset未知工作，不切原checkout，不改全局safe.directory。正常用户环境执行Git，避免sandbox ACL造成虚假删除。

允许写RF来源准备链、实际调用点、其测试、相关CLI/SKILL说明及本卡PWF/交接。主要入口：`scripts/source_preparation.py`、`filing_fetch_client.py`、`company_wiki_source_reader_v2.py`、`company_wiki_source_v2.py`。它们之外的实际调用点先查现有PWF与提交记录，再按依赖修改；不改预测计算、UC/closure/hash-pending、研究结果、assurance运行数据、`.git`配置/其他分支、CI矩阵或跨仓代码。

独立PWF：worktree内`.planning/p5-rf-source-default/`，含task_plan/findings/progress。交接见§7。读取本仓AGENTS/当前主计划，用户明确要求的简化和本卡范围优先于历史小节点签收。

## 3. 已冻结的接口与部署责任

- Producer基线：CWP `f775406`（包含selector `0.3.0`），现有`tests/golden/source_v2/`及serializer是合同输入；SourceRef `2.0`与verified-open receipt版本不变。
- RF调用当前FF时继续显式传现有`--source-ref-v2`；不等待FF新卡，不要求FF改schema或返回不同candidate。FF v2请求已自动走该route，本包不重复实现它。
- CWP catalog配置是部署层注入：复用`--company-wiki-catalog-config`及既有配置解析。一份明确配置贯通真实CLI/调用者，不能靠相邻目录、raw根、文件名猜身份，也不能缺配置时偷偷退回legacy。
- 新默认路径使用已有`open_source_version_v2`及`build_revenue_source_record_from_verified_read`；真正打开时由CWP验证当前raw字节SHA、source身份/期间/as-of及根/配置。RF仍验证自己的证据文件SHA。
- RevenueSourceRecord/reuse receipt既有schema保持兼容。保留实际download outcome/count；没有实际parser/LLM计量时沿用现有null语义，不伪造0。`artifact_read`不再代表旧正文被读；不把metadata-only reference称为已验证可用证据。
- 本卡不接预测计算、不扩N3a、不修改StockWiki/IQS/CWP/FF。`not_reviewed`诊断和已允许的hash-pending闭环语义保持。

## 4. TDD与实施步骤

1. **先定位实际入口**：读RF现有PWF、N3a交接、当前source-preparation测试和commit；追踪`prepare_source`调用与CLI/SKILL运行示例。列表写到本卡findings，区分活动代码、历史运行记录、测试。不要扫描3,833条ACL假删除作为施工输入。
2. **先写关键RED**：调用正常来源准备入口时不传旧opt-in flag、注入合法catalog配置、没有derived也成功；陷阱legacy正文读取若触发立即失败。缺配置在外发前具名失败；错raw SHA/身份/期次/as-of失败；重复读取不下载、不生成normalized或调用模型。
3. **迁默认与所有活动调用者**：默认走现有v2，一处配置解析。旧`--source-reader-v2`可留为兼容no-op；不能增加新“双开关”或fallback。若保留显式legacy解析器供历史离线fixture，隔离在非生产调用链并记录真实用途；无调用者代码直接删，不留第二套默认入口。
4. **保持接线可运行**：CLI、Python入口及已证明存在的上层调用者都携带明确配置；同步帮助和调用示例。只改默认bool、导致所有默认入口缺配置失败，不算完成。
5. **集中一次集成/E2E**：用当前已提交CWP/FF真实代码和独立catalog，调用RF公开CLI，不仅mock私有函数。正例、缺配置/来源变更负例、原件/旧派生可独立删除、重复reuse和目录恢复一起验收；不逐helper再签收。
6. 相关测试与已有发布门通过后提交本卡代码/报告；有remote可推自己的codex分支。不要自行合main、切owner树或安装全局技能，MAIN统一整合。

## 5. 测试包与真实资料

复用当前main的：

- `tests/test_source_preparation.py`
- `tests/test_company_wiki_source_ref_v2.py`
- `tests/test_company_wiki_source_reader_v2.py`
- `tests/test_source_ref_v2_three_repo_e2e.py`
- `tests/test_fc904_artifact_selection.py`、`test_fc905b_trusted_receipt.py`中仍有明确合同价值的断言；不要整文件删除，迁默认行为或标为历史离线fixture。
- `tests/test_zr701_f1_draft_formal.py`中的真实source-preparation调用者责任。

新包建议`tests/test_p5_source_default_v2.py`和`tests/test_p5_source_default_cli_e2e.py`。先跑新增RED，再相关包GREEN，节点一次既有快速发布门；不每commit全仓长测。

真实原文候选：CWP中微公司2025年报，SHA `d64c410832f22f5127277bad6dc357c664aede523561af99150c494857fd3aa5`。只读原件，复制到本worktree独立短临时根，通过现成fixture/admission生成真实catalog/SourceRef。元数据来自fixture须标注，不伪称生产历史资格。没有CWP production目录或owner数据库写入。

生产者与FF测试依赖固定已提交HEAD，允许只读源码/测试辅助；不依赖MAIN未提交改动，不把跨仓私有实现导入运行时代码。整个E2E离线、网络/下载/模型0次。

测试根运行前快照，finally关闭连接、回收自己创建的进程并恢复原样。开始不存在的根结束删除；预有文件不删。临时raw/DB/WAL/cache/outputs都在测试根内；小handoff在根外保留。Windows使用短根及UTF-8，不改本机生产配置/原文/assurance记录。

## 6. 一次节点验收标准

- 默认真实RF CLI用SourceRef raw route，删除fixture旧derived后成功；有合法配置且不是仅显式opt-in测试。
- 活动调用链0 legacy正文读取/目录扫描/隐式转换；抓错来源时失败，SourceRecord不含业务层storage路径。
- 原件及source事实不变；capture/reuse outcome与download计数真实；错误不变成功，missing usage不变0。
- 重复reuse 0下载、0LLM，测试根恢复，owner文件不变，集中责任测试和本仓已有快速门绿。
- 消费迁移已交付不等于CWP生产derived已删，报告明确划界。

## 7. 自包含交接

在本worktree提交`docs/implementation/handoffs/P5-RF/HANDOFF.md`和`handoff.json`。使用[统一字段格式](p5_parallel_packages_2026-10-05.md#统一交接格式)，填写真实base/delivery/commit列表、路径、固定upstream HEAD、公开默认CLI示例、测试结果、原件SHA与fixture说明、before/after清根摘要、0外部调用证据和残留调用者。

附一张“活动旧caller → 当前新入口/已退出”表；报告是否还存在生产读取normalized/summary/sections的路径及精确位置。不要交授权文件、签名、测试全文或复制大批运行历史。发现共享接口缺口时写具体hold并继续本仓可做部分，不越仓补洞。
