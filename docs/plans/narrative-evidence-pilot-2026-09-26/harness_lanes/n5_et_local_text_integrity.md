# N5-ET-TXT：本地电话会TXT正确复用与小收据

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](../task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

**已验收并入本地/远端 main，不再派发。** 2026-10-06：交付代码 `96c9bc8b0b4610a4e4660918bbfb9cbe80fa0395`、交接 `2b9fb84660f98ce27a05709a7e31342ab044b4d2`；MAIN 92项测试、10 goldens、相关 Ruff 通过，真实43份TXT只读 audit 全为 legacy_unverified，原件/配置不变、测试根清理。见[验收收据](results/n5_et_text_main_acceptance_2026-10-06.json)。以下是原施工边界与重放方法，不能据此再次开工。

这是ET本地scraper批次资料可靠性修复，不解锁FMP付费权益，也不改变FF→ET→CWP公共合同。旧无收据TXT仅证明当前头部与字节可读，不能冒充已验证的下载完整性。

## 1. 已证实缺口

ET main63c4090：`scraper.py`的FMP现有文件路径调用`_finalize_existing(...expected_url=None)`；该函数不验ticker/期间/provider/正文完整性。`completed_entry`以errors=ignore读取，把头部Characters当content_bytes。只读Mock复现空文件、错ticker/quarter、截断正文+Characters500000仍reused；`tests/test_batch_runtime.py`现有stored original例子未覆盖反例。这是原件不丢且不能错复用的实际缺口，不新增人工门。

## 2. 独占工作目录与接口

- 源仓`C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts`。
- 新树`C:/Users/郑曾波/Projects/cwp-lanes-20261006/et-local-text`；分支`codex/n5-et-local-text`，从63c4090开始（解析完整SHA保存）。
- 允许写`scraper.py`、新`transcript_artifact.py`、新可选`transcript_audit.py`、`tests/test_transcript_artifact.py`、`tests/test_batch_runtime.py`及确有关系的本地批次测试、README、本卡`.planning/n5-et-local-text/`与`docs/implementation/handoffs/N5-ET-TXT/`。
- 不改`transcript_tool.py`、`transcript_api.py`、公共/1、/2、discovery/candidate wire、goldens、provider policy、翻译配置、CI策略、源仓owner文件或跨仓代码。源仓.workbuddy-ai/、eval_results.json不动，不安装skills。

```powershell
git -C 'C:/Users/郑曾波/Projects/earnings-transcripts/earnings-transcripts' worktree add -b codex/n5-et-local-text 'C:/Users/郑曾波/Projects/cwp-lanes-20261006/et-local-text' 63c4090
```

现有`task_plan.md`、`progress.md`、S3/ET deadline交接先读；新增独立PWF，别覆盖根历史计划。CodeGraph未初始化时先报告，当前可读已定位具体文件继续，不随意初始化。

## 3. 本地资料规则（TDD先写）

新落盘正文原语言、不翻译，保持既有TXT格式和已有命名。每个新文件保存小receipt，schema `et-local-text-receipt/1`，绑定ticker、明确fiscal year/quarter、provider、source_url（如实际已知）、extraction/version、canonical body SHA/UTF8 byte_size、stored-file SHA/byte_size。receipt是ET本地附件，不能宣称provider原HTTP hash、公开日/as-of证明、CWP准入或创建第二canonical来源库。timestamp是取得时间，不冒充公开日。

复用时重新严格UTF8解码、实算body与stored bytes/hash、对比身份/期次及receipt。Characters只作历史元数据诊断，不作字节长度。已有文件不得自动覆盖、删除或悄悄补下载；冲突/损坏具名失败，仍保留原件。错误身份不能仅凭文件名“纠正”。

历史无receipt文件：能从原文头部证明身份/期间且非空，可保守报告`legacy_unverified`并保持原文件；证明不了就明确`unknown/identity_missing`，不是verified reused。允许显式本地audit产生“当前字节/可证明字段”的receipt，但标注legacy，不能补造下载时hash或来源字段。没有可靠信息的发布日继续null；不需要人工签名或授权文件。

receipt与TXT写入采用既有原子落盘/可恢复机制；中断、文件已存在、receipt半写/坏JSON时不丢原件。固定run_manifest不是唯一可靠历史，不全量复制run日志；不追加永久全文缓存。新增audit CLI只读为默认，可显式在独立目标目录输出小报告，0网络、0翻译、0外部LLM。若增加write-current-receipt模式，目标仅本地附件、不覆盖原件，说明清楚。

## 4. 实施与集中测试节点

1. 先复现空文件/错ticker/错期间/Characters虚报，写RED；锁定已有兼容文件格式、调用者与输出码，不能改goldens让错误变绿。
2. 提取小纯函数进行身份/正文/字节验证，batch调用它；本地receipt与audit复用同一实现，不散落多个判断算法。不改公共producer默认或新增provider。
3. Unit覆盖有效中文/英文、空/截断/乱码、角色头部、不同季度、哈希冲突、缺失或坏receipt和不同newline。不能仅按几个关键词推定完整；真实完整性证明边界写清。
4. Integration/E2E一次集中：fake HTTP真实现有批次CLI→原子TXT+receipt→再次运行零HTTP正确复用；随后篡改/错期次/中断/坏receipt明确失败且原件保留；translate=false时translator调用陷阱必为0。所有fake provider费用0、不读真实key。
5. 只读现有MSFT原语言TXT做实际audit，核前后SHA/size/mtime；测试目录开始不存在则finally删除，预有文件恢复，不在源仓transcripts生成收据。相关测试、已有10份goldens和Ruff集中一次，别重跑已完成172包每个小commit；不扩CI矩阵。
6. 正常提交本分支，交`docs/implementation/handoffs/N5-ET-TXT/HANDOFF.md`及统一handoff.json：本地旧格式兼容策略、具体命令、actual vs fixture、生产/公共wire未改、小收据尺寸和残留问题。MAIN统一合入，报告本包不能声称免费provider或CWP准入已升级。
