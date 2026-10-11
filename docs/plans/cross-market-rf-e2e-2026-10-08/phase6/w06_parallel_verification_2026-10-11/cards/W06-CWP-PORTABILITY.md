# W06-CWP-PORTABILITY：虚拟存储根迁移回归工具

**独立开工，不等 OCR/selector。** 工作目录 C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-portability；分支 codex/w06-cwp-portability；基线 01ea86a37edb5506d6269b6e10d9cb56a1270efd。读 AGENTS.md、src/company_wiki/source_catalog/{source_reader,config,service,store}.py、SourceExport接口与当前 root tests，再读本树 docs/handoffs/w06-cwp-portability/input/。本线 PWF .planning/w06-cwp-portability/。

## 目标

用户要求公司/Dayu/Dropbox路径属于存储细节，上层只用一个来源湖。建设独立、离线、多根迁移与引用回放套件，检验该抽象。已有 N5-DOCSET 检验真实内容语义，本包不重做。未证实迁移现在必然失败，先观察真正代码；发现缺陷写最小重放证据，不擅改存储层抢ROOT源码。

## 排他写集

仅新 tools/source_root_portability/（runner、fixture builder、oracle、tests、README），新 tests/unit/test_w06_root_portability_oracle.py、新 tests/integration/test_w06_root_portability.py、本线 PWF/交接。**src/scripts/config/现有tests/CI/安装全只读**；不写W05 OCR、ROOT narrative预算/config/readers/契约，不改 Dayu/IQS/StockWiki。

## 固定接口与边界

runner `python -B tools/source_root_portability/run.py --owned-root <fresh-root> --out-root <new-attempt-root>`。只用本树真实 CWP SourceCatalog、SourceVersionReader、版本化 export/正常 CLI；每阶段记录实际代码 HEAD/模块来源/SHA、配置摘要、source_ref/receipt/export refs与验证状态。报告 schema cwp-root-portability/1，场景预期/实际/错因/清理。SourceRef 2.0 只给 identity/SHA/size/MIME/schema，不往消费者添物理路径/新身份票据。

注册、扫描和 source-facts 仅在 ≤6 synthetic 原件的小型 fixture root；prefer 精确 register，不扫生产。tmp root_id=local/company、external/dayu、external/dropbox只是模拟三位置，**不访问真正Dayu/Dropbox服务或目录**。存储fixture持有路径正常，上层 consumer probe只接受SourceRef/export，不直接glob/walk/rawPath读内容。

## 迁移场景和期望

1. 建3配置根（含空格/中文），有效PDF、HTML、原语言TXT各一份；源元数据显式synthetic/固定日期。经真实 register→query_ref→SourceVersionReader.open_version→export。精确原文SHA与期次/文档类保持。不得直接把fixture SHA填入假receipt跳reader；没有名为 open_verified 的公开方法，先核真实 signature 和 CLI help。
2. 同 root_id/relative_path 把整个 fixture 根从 A 移到 B，使用真实临时配置重映射：在catalog保持对应版本的情况下，上层旧SourceRef能按当前根读同bytes；绝对旧path不可成为消费者依赖。若当前实现不支持，失败正确报PARTIAL，别假改expected。配置变化导致receipt policy SHA改变可接受，不是新授权门。
3. 改relative_path/跨root迁移用**正常重新登记/来源更新**；记录旧/新document_id、source_id/contentSHA及实际revision关系。稳定性只对接口承诺的字段，不预先规定所有document_id都永不变；旧ref可继续读或具名旧位置 unavailable 均按实际文档契约分类，需要ROOT决定的identity稳定性明确UNKNOWN，不能混成已通过same-ID迁移。
4. 两根同bytes、相同来源metadata，不同配置priority。正确候选不按磁盘路径由消费者选；记录去重/候选歧义/物理副本，不能以两个物理文件宣称两个新业务来源。原逻辑注册计数和物理副本计数分别记录。tmp内删一个已确认synthetic副本后，用真实reader验证其他可用版本；不做真实文件删除。
5. 仅raw不可用/目录暂不存在时，原有索引不能伪称字节已验真；恢复目录后正常read恢复，不需要人工签收/canary。打开后bytes损坏或登记后内容变更→真实SHA拒绝；新内容须新版本，不覆写旧内容当原版本。测试中改坏只限synthetic，结束恢复。
6. as-of/period/document_kind 不因根移动变成未知/伪日期；nonperiodic IR/prospectus不获假FY。主体和时期沿所属层职责，不能新造private/public或权限票。
7. export/pathlessconsumer可在新短生命周期进程复现，不能借原 Python对象持有旧buffer冒称迁移后真正 reopen。PNG/PPTX OCR不在本卡，别等待W05。raw-only多根抽象测清即可。

路径包含在存储配置/本机调试日志不等于上层泄漏；SourceRef业务对象和consumer签名禁止path。历史legacy兼容输出可能带path要分清接口，不能据此擅自删legacy。test root mapping的合法范围校验是防错/数据完整性，不能用放开生产任意path替代虚拟化。

## TDD与三个大节点

A：实读真实公开API后写 oracle反例：漏一次 reopen、SHA只核metadata、消费者偷偷open(rawPath)、转根就新建假日期、把物理dup当逻辑来源、无实际policy变化观察、清理越界/丢sentinel。RED证明工具会拒绝虚假PASS，不把未初始化/ImportError当生产漏洞。

B：工具/fixture实现，单元和短集成：

```powershell
python -B -m pytest -q tests/unit/test_w06_root_portability_oracle.py tests/integration/test_w06_root_portability.py
```

集成至少一个真正 SourceVersionReader+临时catalog，且不mockbyte验证；跨进程Consumer spy会记录任何直接文件访问，仅保留正式reader执行存储操作。

C：完整手动runner≤120s，一次总结迁移/损坏/恢复/重复/实际export，source-read调用次数/费用HTTP0。new scratch初始absent或明确sentinel，finally关SQLite/子进程，恢复原样；持久小报告≤8MiB，不保留全catalog/大PDF/parsed dump。CLI每次新attempt，产品失败归PARTIAL固定期望，已有失败不覆写。

交 input/handoff_contract.md 所需普通commit/JSON/MD/manifest/RED/GREEN/E2E及ROOT fix建议。工具正确和报告准确即范围完成，不暗改src来全绿；ROOT合并后负责共因修复/再回放/选CI快测。默认CI不自动遍历全真实湖。
