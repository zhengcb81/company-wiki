# G4 两包 MAIN 正式验收与并线 — 2026-10-07

<!-- CURRENT_PWF_NAV -->
> **历史施工/调查材料：**当前状态与唯一下一步见[总计划](task_plan.md)。下方旧待办、暂停、人工签收和预算只是当时记录，不自动恢复；R3/R5的真实剩余范围以总计划为准。

## 结论

两包accepted/published，全部交付历史已合实际执行分支、正常推远端。整体目标仍paused；只完成本次查收与必要接线，不启动生产/付费、不混入未完成G2-12。

| 包 | 外线交付 | 正式代码 | 集中验收 | 发布 |
|---|---|---|---|---|
| CWP-PIPELINE | 6e6f77c（实现306ecf9） | df7d7ba58955e224c1799355f479ad5378ef38a7 | 211 pass /38.78s；保留实际PDF解析反例 | master已推；[精确CI37673393822](https://github.com/zhengcb81/company-wiki/actions/runs/37673393822)全部job/step成功74s |
| SID-LATEST | 201a8f0（实现d958a0f） | eb8495ceb76892ff6f4a95889b6a19f0a78d769c | 127 pass /27.02s，相关Ruff/format绿 | v2-clean-rewrite已推；原remote名StockInfoDownloader，未动旧main；该仓无workflow |

## 实际变化

1. 删除11个旧Gate模块、pipeline_rules和旧专属测试；full_pipeline仅stdlib薄退休/import零初始化/direct exit78（含-S）。部署报告和指南推荐当前来源CLI。现行PDF提取责任保留；hook/CI/mypy没有旧族import，不添新工程门。
2. CN latest按as-of有限三年窗口、最多五页、共享字节/时间预算，真实年/半年/季候选；exact旧行为不变。SID adapter1.3.0、成功/失败wire仍1.0。
3. MAIN修真实缺陷：最后页读数少于totalRecordNum、hasMore与零总数/末页矛盾被误称完整。三个TDD先RED；修后latest具名discovery_incomplete/non-retryable。不同于来源身份/字节正确性，未增个人权限或人工签收。
4. CN配置旧pending是预算工作树/1.2.0/true；现统一canonical v2-clean-rewrite/1.3.0/true。逐字段验证仅这三个值由MAIN接管，其余配置语义完全保持。

## 真实离线 E2E 与错误

SID literal -m CLI、urllib实际读取loopback HTTP、控制PDF fetch与实际SHA/size；CWP从已提交df7d7ba导出真实JsonCommandAdapter消费，而非造CLI响应。新增四例用实际提交配置的name/version/capability/command；仅runtime/config挪到独立测试根。年初上一份年报、五页未完、覆盖但无可用候选、矛盾末页均按候选/具名失败与实际usage传播。旧1.1无bounded配置四例先RED，接1.3后GREEN；未将旧本地来源称latest。

原SID120责任第一轮107pass/13setup errors是MAIN basetemp父目录未创建，补父目录后13pass/0.36s；最终新增反例后整个127单命令全绿。没有重跑外线已绿1916/216全unit，CWP正常代码CI执行本次全Unit/精选合同。SID的12个mypy为外线对base已有同12，无新增，未另造全量门。首个沙箱外仓git status失败已改真实OS执行；CWP机器交接部分中文乱码用实际Git/UTF8 Markdown校准。无live HTTP/付费/翻译，不冒称端到端正式生产摘要。

## 保护和恢复

初始76份未提交文件SHA/size清单见[g4_protection_before](g4_protection_before_2026-10-07.json)。两原仓快进后仅上述CN配置SHA改变，其他75份完整字节相同，含所有G2源码/测试与SID11个tracked owner及未跟踪名单/scripts。总PWF更新随后属于本次明确文档写集，不混入未完成源码。CN旧pending只对单文件stash，核三个值与其他所有值后快进，实读新配置SHA等于接收树才drop该指定stash；未对其他文件stash/reset/clean。

独立mc/ms短接收树，所有测试先退出进程/HTTP/DB再原生核abs路径和无reparse删除 owned根。CWP g4t1008530B、SID g4t/g4r2670B及Ruff缓存393B已恢复absent；si4l-*副本/fixture由测试finally恢复。两短接收树正常发布后删除；外线工作树、已跟踪.planning小收据、原G2五临时目录、SID三个未跟踪PWF镜像不清理。原件/生产manifest/DB未被本次代码或测试调用，删除原件0；Dayu/IQS/RF/FF无写。不是完整46G备份恢复演练。

## 下一继续点（未完成）

- G2-03旧Pipeline整族已完成；G2-04旧维护已由G3完成。其他mixed-frozen stage/caller、兼容/工程同步/实际安装仍对账，不称全面清理结束。
- 完整G2-12统一ensure/FF/ET/CWP下载→入库、跨进程single-flight、重复复用与失败清理仍未提交。当前provider+consumer合同绿不能替代此节点；CN latest不猜年份，incomplete/empty不能静默复用旧件。
- R2生产metadata/融资/ET登记、R3正式有限批次与consumer、R5收口未完成；R4已有“不对象化”收益决策。
- 预算/模型配置不变，总目标不resume；恢复后先G2，再R2→R3→R4→R5。实际代码CI与纯文档最终提交分开记，防止错误引用别的SHA。
