# MAIN W03 shared 接线实施细则

本卡是内部原W03的共享接线，不是额外外包，ROOT归总/并线/发布。依据W03_CONTINUATION.md、evidence/w03-shared-version-design.md（SHA da1e11d7d369880c847ea4a3c85ce2cc91b1dc060ee777034c152bd5ba1cd750）。W04已交回batch/store源码，pure W03已修future-default规则泄漏；冻结旧研究/157问题包与原失败记录不改。

## 写集与接口

共享内部实施者只改 automation/narrative_worker_factory.py、narrative_runtime.py、narrative_select.py、narrative_official_json.py、narrative_verify.py，source_catalog/narrative_retrieval.py，必要一个内聚selector-binding helper；新unit/integration shared-version测试和必要现有custom-selector夹具明确固定策略声明。只自己 evidence/w03-shared-reception/** 回执。不改W04六模块/失败helper/store/batch预算恢复、pure policy/candidates/evidence（ROOT最后切默认）、parser叶、request/generation schema、模型提示、配置/raw/安装/RF/AUDIT、ROOTPWF，不commit/push。若确实需要batch改动先报告具体反例，ROOT决定，不直接扩写集。

既有run.binding_json执行版本与generation settings是唯一冻结解释，factory只解码一次交runtime。已支持0.6.0与0.7.0由pure resolver执行能力决定；未知冻结策略typed拒绝、不能缺省回current、不能叫预算/人工授权错误。新直接built-in无pin使用current；finished history仍既有只读分支，unfinished旧run保留明确new-run-required，不沉默重标/重签/计费。不新schema/registry/签名/身份重验，不改字节reader资格。

## 一个内聚选择策略适配

built-in绑定effective版本并真正传selector_version；raw/official同一callable、结果stamp及verify expected都取该实际pin。旧custom callable旧call shape保留，但固定policy版本由其调用者明确声明并实际pin其实现；version-aware custom可由调用者显式partial绑定版本，同一adapter记录声明，拒绝与runtime冻结版本冲突。不得凭函数名字/是否缺keyword推断旧版本，不捕获内部TypeError后二次调用，不伪current标签。避免多套wrapper/多个声明文件，接口仅编程策略能力，不是用户许可。

## TDD顺序与验收

先写共享8锚点责任反例RED：raw/official真实新0.7执行与metadata；冻结0.6漂移下结果/verify一致；completeempty不能绕unknown；custom固定旧shape/显式version-aware/内部TypeError只一次/冲突typed；真实resolver旧0.6完整fingerprint与新0.7；同内容新selector generation不同且不误reuse旧pin；finished旧run/read/resume零新调用/fees/attempt/DB mutation（允许协调锁）；unfinished旧run保既有typed拒绝。使用实际旧record/真实TXT/source span定位，禁止只断言tag。

先用显式0.7测试共享接线，默认0.6阶段不能提前掩盖旧路径；ROOT最后一次切全局default0.7（已支持有效版本），然后集中mixed raw+official公共CLI→child→loopback→publish/read/reuse/resume一次大节点和旧fingerprint回放。预算/原件/SHA/asof/角色/partial仍由各责任层保留。0provider/model收费，ownedTEMP恢复。只有大节点独立复核和正常commit/push/exactCI；不逐helper审批，不重复109/168整包。中间source-stable进度可普通commit合并一次push。

## 真实研究边界

工程通过不核销完整财报所有业务召回、摘要命题质量和三年预测。后续配置供应商真实原三家四审/新三家泛化/loop按根PWF执行，累计USD20/2M及旧unknown保持。

## ROOT集中公共补强（2026-10-11）

现有mixed样本虽然跨真实CLI/child/HTTP/publish/read/reuse，却未证明0.7独有语义；旧effort history也不等于0.6筛选历史。ROOT独占新tests/integration/test_w03_selector_public_node.py，唯一集中三项：

1. actual缺省mixed raw TXT+两issuer两页JSON中，新增具体出口许可变化（不依赖product/customer词）在精选/公开原定位读取及实际冻结0.7均可见；同run resume SQL dump/账本不变，新run精确复用零新增POST。
2. first公共CLI producer真实声明0.6，实际Worker按冻结0.6执行/发布（不改旧结果tag或metadata）；升级0.7 fresh CLI对finished history只读，原binding/generation/原件/账本/尝试/outbox保持。新0.7 run不把旧策略缓存误命中，只有真实3缺项再次POST。版本bootstrap只修改该工程child producer实际版本，Worker由factory frozen pin执行，无fake artifact/同一请求外人工许可。
3. 全66324B真实MSFT TXT旧0.6完整指纹11ad9c7…、新0.7的103candidate/96selected/7omitted partial；两saved policy分别真实resolver回放全部精选group的原文/locator/hash，无重标、无复制生产全湖，自有单文件TEMP删除恢复。

先保存真实RED与前后源码SHA（如并行共享源变化真实标记），最终ROOT切默认后集中GREEN与独立关键复核，不反复已有W04/109/168整包。loopback模型仍400输出限额、原request caps、同账本；0外部provider/model费。测试驱动错误与产品原因分开记录。
