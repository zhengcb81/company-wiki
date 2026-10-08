# N5：三个已分派的独立施工包

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

**最新：三包全部交付并经MAIN接收。** DOCSET工具43不同case通过、9原件/86点/744定位回放；12/33实际业务覆盖缺口按[S7细则](../s7_document_quality_implementation_2026-10-06.md)继续。RAW-DUP与ET已并线发布，DOCSET本次实际merge发布中。下方旧状态不再产生任务，不重派N5。

> **最新：N5-RAW-DUP已交付e40b4ec并经MAIN集中修正；51项/9.09秒、两CLI与Ruff绿，已合入master a41244a并推远端、精确CI37523080920/57秒绿。** [验收卡](n5_raw_duplicate_main_acceptance_2026-10-06.md)；ET已验收，DOCSET交接2c3583e已到待MAIN验收，不重派。下方旧未交付叙述属历史。

MAIN负责共享接口、生产状态、所有合入和总PWF，N4C真实有限样本已收口。本总包不增加N4C完成屏障；三个包已交不同harness，不重派。不改IQS、RF、Dayu、StockWiki；旧consumer/身份/gate不重派。

**2026-10-06最新交付状态：**ET-TXT已交完整HANDOFF.md/handoff.json，MAIN验收92项/26.24秒、10 goldens及相关Ruff；43份真实TXT只读audit保持原件与配置，零网络/翻译/收据写入。已快进并推本地/真实远端 main `2b9fb84660f98ce27a05709a7e31342ab044b4d2`，见[收据](results/n5_et_text_main_acceptance_2026-10-06.json)。DOCSET/RAW-DUP仍有各自PWF/工具未提交材料，尚无完整交付；MAIN不接管写集、不冒称已确认live进程。RAW-DUP约7.44GiB只是元数据逻辑上界，不是确认可删或已释放量。

| 包 | 任务/规模 | 源仓库 | 独占工作目录 | 卡 |
|---|---|---|---|---|
| N5-DOCSET | 多类型真实文档质量基准，较大 | company-wiki | `C:/Users/郑曾波/Projects/cwp-lanes-20261006/document-quality` | [质量卡](n5_document_quality_benchmark.md) |
| N5-RAW-DUP | 原件重复占用的只读工具与实证，较大 | company-wiki | `C:/Users/郑曾波/Projects/cwp-lanes-20261006/raw-duplicate-audit` | [去重调查卡](n5_raw_duplicate_audit.md) |
| N5-ET-TXT（已验收并线） | ET本地TXT复用验真修复，中等 | earnings-transcripts/earnings-transcripts | `C:/Users/郑曾波/Projects/cwp-lanes-20261006/et-local-text` | [TXT卡](n5_et_local_text_integrity.md) |

两个CWP包虽然同源仓库，但使用不同物理worktree，并且允许写的子目录也完全分离；均不改src、scripts、生产配置、生产数据库或原件。ET仅改ET本地批次，不改公共transcript_tool wire。MAIN对接时先吸收工具/夹具，再判断基准发现的运行时缺口和实际去重收益；外线不能自行改主线。

## 启动与并发边界

1. 读自己的卡、源仓AGENTS及当前PWF，只使用卡内独立计划。新建明确分支/worktree；若已存在，核归属后复用，不reset、clean或切owner树。Git使用正常用户环境，避免sandbox ACL假删除。
2. 基线CWP `e46108b4f30d5b7e47bfc712e360f173c00b702c`；ET `63c4090`须在源仓解析为完整SHA并保存。MAIN后续提交不自动成为外线依赖。不存在基线/文件时写清原因，先完成可独立范围，不凭记忆补合同。
3. 运行时资料只能只读；所有测试DB/WAL/缓存/raw复制放自己的短tmp根，测试前后快照。不可写源仓companies/.source_catalog/config、其他worktree或已安装skills。
4. 零LLM、零付费API、零真实下载为本三包测试预算，不消费MAIN模型campaign额度。ET测试provider用fake HTTP；确有必要的真实请求先报告具体收益，不随意扩provider。
5. 大节点一次集中Unit/Integration/E2E；不每helper签收、不新增人工批准文件、不扩日常CI矩阵或运行时间。原件不删、不移动、不硬链接、不复制进Git；报告必须分清实测、fixture和估计。

## 统一交接接口

在各自worktree提交卡指定的`HANDOFF.md`、`handoff.json`及独立PWF。JSON：

```json
{
  "schema_version": "cwp-independent-handoff/1",
  "lane_id": "N5-DOCSET|N5-RAW-DUP|N5-ET-TXT",
  "status": "complete|partial",
  "repo": "absolute source repo",
  "worktree": "absolute exclusive checkout",
  "branch": "codex/...",
  "base_head": "40-char SHA",
  "delivery_head": "40-char code commit SHA before final report",
  "commits": [],
  "changed_paths": [],
  "upstream_pins": {},
  "public_commands": [],
  "tests": [{"command":"exact command", "passed":0,"failed":0,"skipped":0,"seconds":0}],
  "real_samples": [{"sample_id":"...","sha256":"...","byte_size":0,"metadata_is_fixture":false}],
  "protection": {"originals_unchanged":true,"production_state_unchanged":true,"owner_files_unchanged":true},
  "cleanup": {"before":"absent or inventory","after":"same as before","restored":true},
  "calls": {"model_posts":0,"provider_http":0,"downloads":0},
  "open_items": []
}
```

外线只推自己的分支；MAIN统一验收合入、更新总PWF和安装部署。不跨仓补缺口；缺口以文件位置、输入、期望/实际和重放命令交接。报告保留小证据，不交整套临时目录、数据库或测试日志。`complete`只能覆盖本卡范围，不能宣称整个项目完成。
