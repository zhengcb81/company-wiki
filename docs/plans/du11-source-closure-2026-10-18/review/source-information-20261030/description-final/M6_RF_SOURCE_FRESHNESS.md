> 2026-10-30 M6发布后当前指针：本局部最终独审与正式组合addendum0OPEN，RF09be0974已推main/CI41079560122 success、定点安装与全新进程通过。下列原始OPEN/待审仅是历史过程。 唯一当前状态在上级CURRENT_STATUS.md/json；下一操作见 [M7](M7_C3_SOURCE_HOLDOUT_NEXT.md)，最终证据见 [M6验收](m6-source-evidence-2/README.md)。

---

# M6：同源引用不能制造新鲜度（RF采用验收优先项）

## 真实暴露

中微真实半年报/5原产物、原始SHA和旧完整generation，经正式Store新本地UUID恢复、CWP asof2026-10-08真实prior_verified_capture及112locator读回，RF摘要→原文claim→equipment_units_base_2026→实际units公式、native formal报告与snapshot已实际执行。原参数value/单位/期间/币种/analyst_assumption及三个情景数值不变，但confidence 65.38058062293638→65.39469303281442；只有source_freshness8.679411732699949→8.693524142577989变动。原v3收尾NameError已从保存产物纯finish，失败保留，不再跑整链或API。

新增的是同一H1资料的rationale，不能当新信息。scripts/analysis/confidence.py按parameter.claim_ids逐条平均来源published_date的age bucket，导致同源引用多投票。它没有用verified_date，本例不是重读日期变新；不要误修时钟或提高额度。实质P2，RF采用节点暂不总签通过。另经合法M1源合同正例确认，published_date=None会在评分器崩溃；中性混合质量对照复制exact引文使quality17→18，均来自引用条数被当评分权重。

## TDD与责任层

1. 独立最小反例先锁同参数/同来源，新增等价claim、换claimID、顺序改变均不改source_freshness；真正不同日期的新来源可以改变，多个独立测量/不同支持角色仍保留，不把整份PDF只准一个事实。用现有capture.snapshot_sha256/source_id表达来源，不建身份库、授权文件或外部查询。
2. 只由RF confidence owner聚合资料新鲜度，CWP/FF不计算投资置信。新版本source-evidence/2中，freshness每参数每原capture一次；quality每参数每(origin,support_type)一次。不同角色仍各保留一份，不删独立测量或任何claims。避免用大量同一来源同角色引用抬分；真正新资料或角色可影响评分。未知publication不给freshness信用，availability只证明cutoff。需要处理同SHA来源别名和冲突日期时采用明确、保守且可交换的政策，未知不伪造新鲜。
3. 保留旧产物及其stable-fsum/1数值。先调查已有CONFIDENCE_CALCULATION_VERSION与强验证recomputation接口；优先在既有算法版本责任层作有限新revision/旧replay，不改旧快照、不把旧数改成新、也不新造schema门禁。若必须engine patch则更新唯一version及兼容矩阵/CHANGELOG，并保持历史4.3.0是已知发出者。新正式输出只能发新算法，历史校验按声明算法。已通过设计调查选择既有calculation_version的有限source-evidence/2分发，不需要整体engine/schema bump；strong replay按声明的stable-fsum/1/无marker旧算法保持历史数值及64ULP规则，未知/null拒绝。
4. 相关短域+旧v1真实产物/数值防篡改+新版本变形测试+独审；禁止删除旧断言或只更新golden迎合实现。新rank/quote内容与RF收入公式都不改，不增加LLM调用。
5. 修后使用保存的本公司真实baseline与consumed input复算：同源新增证据后confidence不变，实际summary_use、公式引用、数字和质标保留。正式run/snapshot用独立registry/临时目录，原旧报告/原件/三WIP/147output不改。全流程独审后才能把RF实际采用节点签通过。

## 发布

CWP新模板/5政策已65P作者/38P独审，可以独立提交；本M6为RF仓不重叠主线。每个大节点正常commit/push、定点部署、重复零写/新进程、精确CI及PWF；不扩小节点签收或全仓超时。跨市场holdout/完整公司loop仍后置，不把局部采用当全部完成。

## 分层与当前发布

新模板策略599f6cf6已推master，正常167P/34.35秒，精确CI41068344080 success；不是全局默认切换。真实RF旧v3由独审确认源/112locator/asof、summary_use/参数公式/原生正式输出及快照都真实存在，但P2保留。正式input/forecast/report/snapshot/registry已由RF owner保存到RF/.planning/source-quote-adoption-20261030/v3；CWP7份副本均核镜像SHA后清除，只保留source bundle和技术receipts。不把研究state沉淀到CWP。后续M6复算也只写RF自有测试区。

## 最后联调发现与收口（非新门禁）

1. 独审以真实旧registry4行缺marker记录+完全同一input新算法重跑，证实两个strong合法产物被旧engine/schema分组误报冲突。已在existing publication_registry派生confidence revision作generation维度；旧缺字段解释stable1但原行/chain不重写；同代冲突/坏字段仍拒。24RED/1P→38P，待最后补审。不是强迫用户改forecast_version或清历史。
2. 完整M1未知URL/pub源native/strong已通过，但renderer产生`](None)`假相对链接。已在共享来源表条件输出纯ID/未知日期，2RED→5P并保留已知HTTP链接正对照，JSON None不变。此项待同节点补审。
3. 两份真实旧native输出已固化RF自有135KB压缩fixture，无PDF/keys/DB，保留旧算法两分数并验证当前native同源重复评分不变、经济trace不变且有恰1实际claim增量。三份直接新回归仍在既有单pytest smoke，不增加workflow或超时。
4. ROOT新算法正式run/report/snapshot已在RF自有独立registry生成；初始全parameter_trace相等断言错误，因为正确采用必须新增claimID，错误日志保留，纯finalize改核经济字段不变及唯一预期claim，不重复模型/原文或native链。真实模型数值及新算法confidence前后相同。最终独审/发布部署后才总签本局部验收；不冒签全文、新holdout、最新研究周期或整个公司循环。
