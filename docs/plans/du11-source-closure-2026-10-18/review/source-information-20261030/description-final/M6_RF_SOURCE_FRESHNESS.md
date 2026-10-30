# M6：同源引用不能制造新鲜度（RF采用验收优先项）

## 真实暴露

中微真实半年报/5原产物、原始SHA和旧完整generation，经正式Store新本地UUID恢复、CWP asof2026-10-08真实prior_verified_capture及112locator读回，RF摘要→原文claim→equipment_units_base_2026→实际units公式、native formal报告与snapshot已实际执行。原参数value/单位/期间/币种/analyst_assumption及三个情景数值不变，但confidence 65.38058062293638→65.39469303281442；只有source_freshness8.679411732699949→8.693524142577989变动。原v3收尾NameError已从保存产物纯finish，失败保留，不再跑整链或API。

新增的是同一H1资料的rationale，不能当新信息。scripts/analysis/confidence.py按parameter.claim_ids逐条平均来源published_date的age bucket，导致同源引用多投票。它没有用verified_date，本例不是重读日期变新；不要误修时钟或提高额度。实质P2，RF采用节点暂不总签通过。

## TDD与责任层

1. 独立最小反例先锁同参数/同来源，新增等价claim、换claimID、顺序改变均不改source_freshness；真正不同日期的新来源可以改变，多个独立测量/不同支持角色仍保留，不把整份PDF只准一个事实。用现有capture.snapshot_sha256/source_id表达来源，不建身份库、授权文件或外部查询。
2. 只由RF confidence owner聚合资料新鲜度，CWP/FF不计算投资置信。质量/数值支持、方向/约束与freshness分别处理，不从一个症状重写全部经济研究。需要处理同SHA来源别名和冲突日期时采用明确、保守且可交换的政策，未知不伪造新鲜。
3. 保留旧产物及其stable-fsum/1数值。先调查已有CONFIDENCE_CALCULATION_VERSION与强验证recomputation接口；优先在既有算法版本责任层作有限新revision/旧replay，不改旧快照、不把旧数改成新、也不新造schema门禁。若必须engine patch则更新唯一version及兼容矩阵/CHANGELOG，并保持历史4.3.0是已知发出者。新正式输出只能发新算法，历史校验按声明算法。具体方式经独立设计诊断定案后实施。
4. 相关短域+旧v1真实产物/数值防篡改+新版本变形测试+独审；禁止删除旧断言或只更新golden迎合实现。新rank/quote内容与RF收入公式都不改，不增加LLM调用。
5. 修后使用保存的本公司真实baseline与consumed input复算：同源新增证据后confidence不变，实际summary_use、公式引用、数字和质标保留。正式run/snapshot用独立registry/临时目录，原旧报告/原件/三WIP/147output不改。全流程独审后才能把RF实际采用节点签通过。

## 发布

CWP新模板/5政策已65P作者/38P独审，可以独立提交；本M6为RF仓不重叠主线。每个大节点正常commit/push、定点部署、重复零写/新进程、精确CI及PWF；不扩小节点签收或全仓超时。跨市场holdout/完整公司loop仍后置，不把局部采用当全部完成。
