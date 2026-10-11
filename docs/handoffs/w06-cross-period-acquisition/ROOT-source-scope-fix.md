# ROOT W06 共用 acquisition scope 修复交接

## 状态

作者实现和有限工程节点完成；STOP待ROOT，未commit/merge/push/install。最终受影响191PASS（50.947s），ruff和diff-check绿。原41matrix未运行。

## 工作目录/冻结

TREE：C:/Users/郑曾波/Projects/_harness_worktrees/w06/cwp-acquisition-scope-root

branch：codex/root-w06-cwp-acquisition-scope-20261011；base：e2e19ea200bf87b13dd41d6389897ea5f2711d93。

中央证据：C:/Users/郑曾波/Projects/company-wiki/docs/plans/cross-market-rf-e2e-2026-10-08/phase6/w06_parallel_verification_2026-10-11/evidence/root-ff-matrix-acceptance/producer-scope-fix/

以product-freeze.json的12文件SHA接收；tracked-product.patch只含9个既有tracked模块，另3个新文件canonical_scope.py和两份tests须按freeze从TREE接收，不能只应用patch漏新文件。本线3PWF在.planning/w06-cross-period-acquisition/。

## 问题与系统实现

已验正常入库没有 repair assertion，不等于没有 source facts。正常writer在已有source_metadata_assertions自动投影事实，证据明确 provider metadata和canonical提交；只扫描同形.source.json不会写此事实。source ScopeRelation MATCH/NOT_RELEVANT/UNKNOWN在来源层负责。可信旧期先排除，避免无关raw重读/identity master重新查询/retired恢复。未知来源不当空湖处理。

register_catalog_sources内部有限单组on_registered回调沿scanner的coalesced事务写事实/恢复；不新增表或许可。_prepare_source_fact_write提供同连接read port和保留canonical_commit摘要。数据库失败回滚事实/登记/重激活；先落盘原件保留以恢复。dedup不改原件或首份sidecar，当前provider只能填未有字段，相反scope拒绝，不覆盖原文proof。

历史兼容资格：真实成功journal结果、重算attempt_id与原request_id、当前SourceRef SHA/size/MIME和candidate/provider/accession/URL一致；仅使用已哈希绑定的明确request scope。未绑定发布日期、title等不提升。单请求一次有界journal读，4MiB metadata上限及原local总体预算执行；无日志/坏日志/缺证/冲突是UNKNOWN，不能补人工签收。迁移根后不依赖旧canonical_path。真实相同期间重开仍验全文SHA和当前root/type/as-of。

REUSED之前直接记成功journal，现由SourceVersionReader终点验真实字节后记录，失败只failed，provider_started=false。PDF receipt真实SHA+PDF magic验过后，可以纠正同SHA内容曾因.htm扫描猜成HTML的source type，不改整个scanner。未知publication已有ambiguous拒绝合法，仍无伪source/重复下载。

## 接口

SourceRef/SourceExport v2不变。AcquisitionResult可选local_preparation：status∈blocked/unavailable/ambiguous；reason、causes都是有限具名code；blocks_download=true。SourceOperationInput和pathless operation DTO转投这项诊断，失去本地事实不再笼统not_found；已有budget acquisition_observation不改，未provider调用false可观察。FF消费映射由ROOT决定，作者不改FF。

## 已测试范围

公共正常writer三市场年度、HK同年Q2→Q3和半年跨年、cold一次/new期再次零下载、原SHA不变；未验scan无内部facts；真实旧writer行为shim暖库+真实成功journal；fresh catalog初扫request/attempt/版本/candidate binding负控；target同尺寸改SHA没有成功reuse journal；unknown publication拒绝/zero-provider；老retired无关不阻断/不恢复；facts失败原子回滚/可重试；失败explicit重新获取不激活；假PDF拒绝；同字节不同期scope拒绝不污染facts/raw；重扫facts保留；canonical claim绑定冲突具名；原文事实优先；既有SEC原文DEI、local限额、scope、预算/usage CLI integration。

原public RED和control RED保存，初期构造器/budget/staging接线错误另存不算产品根因。历史侧车原库重扫保留已有声明，故负控使用独立fresh catalog；unknown日期不强定missing而验真实拒绝。191PASS不是全3314/41matrix/网络/LLM/OCR/收入模型验收。

## ROOT下一步

1. 非作者按freeze接受和少量针对性反例，无小节点审批。
2. ROOT用原41matrix+原期望回放，关注FF新的local原因分类和ET真实TXT supervisor路径；原失败证据保留。
3. 大节点通过后ROOT正常提交、并线、推送、精确CI/必要定点安装；更新母PWF，返W04→G2→G4→G5。

所有独立scratch已恢复；生产raw/配置/密钥/其他项目和作者Port工具未动；费用0。作者STOP。
