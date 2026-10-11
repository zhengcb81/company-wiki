# Findings

2026-10-11 已有真实公共入库记录带完整acquisition.request/candidate/receipt及hash/size，但steady source-fact assertion为空。二者责任脱节；旧期在resolver层已排除，却在local_reconcile被重新当作当前缺口。依赖于它的ET未启动应记前置未运行，不归ET缺陷。独立根因报告在母W06 evidence/root-ff-matrix-acceptance/root-cause-review/。

禁止方案：为测试手填verified assertion；把所有metadata字段当事实；跳过原文SHA；整个禁用local_metadata_gap；按CN/US/具体年号绕过；提高deadline/cap或放宽原case期望。应复用入库时已有事实资格并在来源层判断相关性，保持未验scan与目标损坏来源的诚实失败。

## 来源事实资格设计
独立 scope_origin_design 已只读确认：scan acquisition/r4_provenance 无 writer origin；journal 只绑定 request scope，不绑定完整 candidate/sidecar。采用已有 source-facts 表和同事务内部 hook，事实证据明确 provider import vs primary-DEI；禁止以缺 correction assertion 判无正常来源事实。

## 已实现责任和兼容边界
正常 provider canonical 入库自动写已有 source-facts，证据是 provider-metadata-import/1 + canonical-commit locator/摘要；不冒原文DEI。原件先落盘，单组登记/facts/reactivate一个SQLite事务；失败保持raw和staged可重试，失败不得写成功journal。更强/先前scope冲突不覆盖，物理去重仍登记缺失事实；explicit unknown correction不盲填。
历史仅真实成功journal（downloaded_new/deduplicated_after_download）+重算attempt/request SHA+version SHA/size/MIME+candidate/provider/accession/URL绑定资格升级显式request scope；不以老物理路径判可信，不升级未绑定candidate出版日期/title，且每local操作最多一次有界journal读。缺证/冲突/越预算是UNKNOWN/具名阻断，不造人工assertion。新的完整facts支持同期间真实byte复用；历史仅范围证明不冒完整源事实。
SEC HTML仍归原文DEI资格 owner；provider声明不得冒/覆盖其证据。非目标可信旧期先排除，不再读旧raw/恢复retired/重复身份master。当前同entity未知来源仍走原修复；公开pathless DTO用可选local_preparation(status,reason,blocks_download,causes)，不暴露路径、许可或新签收链。真正空湖not_found；本地事实失败blocked/unavailable/ambiguous。
191测试证明本source范围；没有证明真实provider网络完整性、OCR/LLM质量、经济预测或整个41 matrix完成。
