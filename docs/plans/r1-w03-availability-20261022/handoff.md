# W03-A CWP producer 交接

**ENGINEERING_GREEN_READY_FOR_ROOT_INDEPENDENT_REVIEW**。产品 `aff8be80c68b9f39c76dad2011354031132c9cef`，基线 `20a7fb0c`，工区 `C:/Users/郑曾波/.codex/worktrees/du11-extractive-runtime/company-wiki`，分支 `codex/r1-narrative-availability`。未并线、未推送、未安装；不表示W03-B/W07或真实RF质量已完成。

## 实现与兼容

唯一产品文件 `src/company_wiki/automation/narrative_transport.py`，21行增加/5行删除。原件buffer按现流程实读验真后，只取一次现有 `verified_availability_evidence(catalog, ref)`，与raw reader2.2共用owner。将同SHA证明交现有 `qualify_source`，让合法availability补足unknown publication的历史资格；已知未来/非法日期仍拒绝，不填造published_date或retrieved_at。

仅raw `narrative-read-receipt/1`增加optional顶层 `availability_evidence`，完全复用现有六字段DTO，无proof省略。proof只属于读取收据；原Bundle、generation、模型输入、cache identity、请求字段不变。projected receipt/3不接根proof，多parent不借A的证明覆盖B。未改source-facts writer、summary/runstore、RF或生产默认。

## TDD与验证

有效RED：**7 FAIL / 15 deselected /29.78s**。真实PDF/nativeJSON × prior_capture/current_open的raw2.2已给出合法proof，而narrative CLI仍source_publication_unknown；单次读取和artifact冻结反例亦失败。初次环境尝试的XML被.codex NTFS拒绝，另留日志，不当作有效RED。后续XML在自有短TEMP写入后用原生PowerShell封存。

最终集中节点：**167 collected，166 PASS，0 FAIL，1 SKIP，168.51s；新22例全PASS**。唯一skip为未提供显式只读真实SEC HTML原件，未下载补跑。包含公开CLI/golden、无proof/错SHA/晚proof/非法schema或类型/裸mtime、已知未来和非法日期优先、当前模式、原件tamper、格式及双parent隔离。全src mypy **366文件PASS**，ruff PASS；正常commit的ruff/mypy/host guard均PASS，无跳钩。

一次完整候选的invalid-publication测试只改投影列、留下canonical source_fact_patch=null，真实owner正确按null投影。已修正测试的canonical证据，并先断言manifest真的非法日期；产品未为该夹具问题作放宽。有效RED的七个正例及输入不变。保留21P/1F、单项复核和最终全绿日志，未删反控。

## 一次读取、冻结与清理

PDF/JSON各断言：每次narrative操作原件byte reader **1次**、availability owner **1次**、新source-fact writer **0次**。raw2.2与narrative proof精确相同。public CLI返回原artifact字节和原reference，manifest日期不补值，读取前后catalog DB/WAL字节一致。双parent projected不调用raw proof helper，另一parent篡改仍拒绝。

**0 API、0下载、0模型、$0**；生产原件/配置/费用账未改。独占TEMP `.planning/r1w3a`初始不存在，清理前1176文件/29,606,869bytes，绝对路径确认后原生删除并恢复不存在。实测采样30,030,280bytes，不冒称连续精确峰值。旧工区已有 `.planning`/temp全部保留。精确命令、UTC、source实际字节SHA及LF映射、跳过原因和清理收据见[handoff.json](handoff.json)。证据只有小日志/XML/hash，不复制原件。

## ROOT下一步

ROOT集中非作者审查并跑真实CWP→RF公开CLI组合；**先RF consumer兼容发布与定点安装，再CWP producer**。CWP无技能安装副本，本worker不merge/push/install。后续仍需W03-B显式0.9/v5语义和旧0.8冻结、W07配置内真实摘要/普通paid恢复/cache/used parameter+formula消费、W06四审及新公司泛化；不得用此工程绿代签。暂不改默认0.8。