# R6 R5 来源合同修复 — 最终集中独审

结论：**PASS_R5_SOURCE_ENGINEERING_ONLY**。当前冻结范围未发现需阻断的产品 P1/P2。ROOT 可结合精确候选完整 CI 绿正常整合；真实 H1、正式摘要、缓存恢复、RF 实际采用、T3 和整个目标仍未由本报告验收。

审查人 `/root/rectification_review_a`，2026-11-02。实测源码正常提交 **`10767b86318e63094c2bb49451447c9aedffc32c`**，工区 `C:/Users/郑曾波/Projects/company-wiki/tmp/architecture-r2`。设计基线 `2b0787dc`。初次读取时 ROOT 正在正常保存同字节源码，提交本身未改被审文件。独审前后 9 源码＋3 自增测试＋ROOT 预算 spy 的 **13 项 raw SHA 全匹配**，Git LF blob 全匹配；freeze manifest SHA 为 `d45fc6875e411b2e2911e78e838b84a47af98fdf27c35c50438e5bc03b863650`。细项和复现源见同名 JSON。

## 合同与共因修复

按三路 R5 合同调查：eligible 是来源资料召回，independent payload 是来源信息自足，source scope 是披露类型，均不验证现实世界真伪。新实现撤掉 scope 的统一资料否决，闭合具名目录不再依赖认识成员所在行业；计划、定义、范围依其信息可用性保留，仍不能凭它们生成已完成事件、发行人归属或观测数值。

`source_nominal_members` 由原 assertion/disclosure owner 共用，处理闭合成员与悬空连接词，没有公司/行业/营销词清单。关系回调和投影复用同一观察。`detect_reading_business_fact` 现在取统一准备结果的 `text_fact`，生产 `fact` 再消费既有资源/关系能力；不是先跑另一套分类器后删 reason。新资源语义不泄漏进历史 text API，同时旧来源目录/计划/定义不会被 legacy 事件策略抹掉。

资源 purpose 优先用同一 canonical clause 的 prepared roles，确需准备子范围时先扣现有 19n 并透传同一个 WorkBudget。金融整句的拒绝由同 prepared scope 的 `financial_context_keys` 保留，不能再从孤立因果子句或 broad legacy background 回退复活。旧预算/partial/缓存边界保留。

## 有界独立实际验证

正常宿主 Python 3.13.9 / pytest 9.1.1，显式候选 config/rootdir/confcutdir，断言实际模块属于候选树。只用合成文字/内存结构、确定性 request/card 编译和自有短 tmp；无原件、下载、付费模型或全仓运行。

首轮 **28 项：26 passed /2 failed，5.95 秒**。两条均为独审自有断言的边界假设错误，见下一节；产品及旧测试未改。只定点重验这两条，**2 passed，2.21 秒**。因此是 **28 个唯一场景**的限定结果，不冒称此后另跑过最终全 28 组，更没有重跑作者 1048/99。

- 原独立五个 weak function/goal 加两个未见目标仍 None、unresolved、无业务相关和稀缺材料资格，没有恢复 default-specific。
- 新 EN/CN 陌生服务成员名及陌生品牌目录是自足 material/support；无行业词典要求，也没有制造当前状态/里程碑/数值。
- 新 EN/CN 定性计划及未定日期保留，指标定义可作信息，但不变为观测增长。未知制造代号保持 relevant/unresolved，原 engine binding 仍 False，重复 session 读取不再收费。
- EN/CN 完整财务因果句、无问号 WH、模板、悬空名单都不能获得 support/relevance。独立的财务总数不借同文档的目录放行。
- 实际 prepared resource 产出 text/production 两视图，生产保资源信息而历史 text 不扩权；资源 purpose 显式账户同对象、工作前预扣、重复读取免费。预算停机不缓存半份 assertions，mixed 缺资源走 partial。
- 原 TXT 同 turn 计划＋限定真正进入 model request/card，draft 不能变 actual；原 EN 有限 12 spans 确实保住不同经营信息。这些均无真实模型调用。

## 独审自身的透明纠正

第一条原断言把中文 semantic role 的规范化文字当成逐字 raw quote，误要求句末 `。` 必须留在 role 中。修正后仍逐字检查全部语义与限定文字，只规范化终止标点；真正原文卡/request 的保留由实际 seam 测试另验。没有改产品去适应探针。

第二条误要求 `source_processing_complete=True` 必须推出 dependency inventory complete。所用 `_document` 是缺 carrier/scope 描述的合成结构夹具，默认 PDF 且 regime/family/form/purpose 都 unknown；它如实报 `INVENTORY_INCOMPLETE` / `INVENTORY_NOT_COMPLETE`。目录 selected 和来源处理完成可以与不可复用的 partial 库存并存。定点修正反而要求保 partial 和明确诊断，不伪造缓存复用证明。原失败 JUnit、实际库存诊断和纠正理由均留 JSON。

一次直接传中文 pytest 参数显示名导致 exit 4、0 测试执行，属选择入口错误；随后从原 JUnit 读取两个精确 escaped node ID，确实运行两条并通过。错误记录保留，不计产品 RED。

## 旧合同、收据和完整 CI

原 13 个 CI 失败文件中，除 ROOT 两个 budget spy 包装函数适配外，其余 **12 个整文件与基线字节一致**。spy 保留原 support/admission/一次准备断言，只传 `work_budget` 并验证同对象。R4 自增的过严“scope=无资料”“未知名单必须无信息”断言有明确 erratum；没有替换原 70 个期待。

核作者当前 8 份历史 JUnit SHA 均一致：最后 1048 为 1044P/4F，17 项定点恢复；资源 99 为 98P/1F，最后同 prepared text/production 投影 16P。不能把这些相加，也不能写成最后实现后重跑了整 1048/99。

本地 ROOT 精确完整 CI 收据已只读核对：run **`41380285347`**，head **`10767b86`**，status completed、conclusion success。该收据 SHA 写入 JSON；独审没有另跑完整 CI。两份证据可供 ROOT 做正常整合决定。

## 清理和未签范围

独占 `C:/Users/郑曾波/Projects/company-wiki/tmp/k5` 初态 absent，最终核绝对精确路径、无任何 reparse 后 native 清理，结束 **absent**。脚本、观测和 JUnit 已存报告，不保留临时资料副本。源码、Git/index、生产配置/DB、原件、主 PWF、T3 和外来 hook mode 未改；作者工区仍只有原 hook mode WIP 和 T3 未跟踪目录。

本次仅签冻结 13 项 R5 来源工程，未重审此前各域已有收据的整体 100 paths，未签 T3、真实 H1/摘要/cache/RF 或全项目完成。**STOP**，交 ROOT 正常并线与后续既有大节点。
