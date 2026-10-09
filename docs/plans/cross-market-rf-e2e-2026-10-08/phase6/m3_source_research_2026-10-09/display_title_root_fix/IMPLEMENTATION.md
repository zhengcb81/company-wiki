# M3共用来源显示标题修复（先测试，再实现）

## 实证与责任边界

三份MSFT FY26 10-Q经公开CWP预览和RF原文reader均可打开，来源manifest title=null。真实RF source_preparation却在company_wiki_source_v2两处_required_text(title)失败，0下载且有字节/资格。正常补源title观察可解除症状，但不能解决所有缺标题原件的产品根因。失效源记录和capture9c6df69a3eba44918b0383531d65383d保留，不以补元数据后的绿核销缺陷。

已知输入：revenue-forecast-audit/runs/m3-20261009T184946-us-msft/execution/original_reads.json #/2至#/4以及execution/requests/fy26q1.json；来源C963/A60/769 SHA原件不改。

## 实施顺序与写集

1. 复用干净RF隔离工作树，MAIN独占scripts/company_wiki_source_v2.py、tests/test_company_wiki_source_v2.py及现有短CLI集成/共享smoke入口。保护RF owner assurance三文件与output；零生产catalog/config/原件变更。
2. 先写 nullable/空白title的legacy与minimal候选行为测试，真正源trace维持null/空白而native RF source记录产生明确source-ID显示标签； present标题保持原字节，非字符串metadata仍拒绝。先RED。现有missing title测试改为新责任期望并记录此前设计耦合，不删除真实hash/bytes/错period/未来date拒绝。
3. 共用转换层只将缺标题从资格转为显示fallback（document_kind+SourceRef ID），不猜公司/年度/原件标题，不创建新事实，不写CWP历史。RF既有source schema继续非空title，trace保存真正未知。
4. 原生RF source_preparation CLI离线有界集成覆盖null标题成功、0download与不漂移来源trace；语义bytes/ref/date/candidate拒绝保留。短责任模块列入当前既有CI/push共用集，长跨仓/真实收费试验不进入commit。
5. 一次集中责任测试+实际三份原件sealed manifest重放（公共读取，不改旧源）验收；正常commit/push，定点同步这一运行文件，再由executor实际新capture复跑。结构/工程绿不代替四路研究审查。

## 验收与禁止事项

缺标题仍可消费已经资格/字节验证的财报，实际源标题unknown保留，生成显示标签不宣称真实标题；reference/file hash/as-of/dates/候选事实一致性拒绝不弱化。不新增身份DTO、人签、全库扫描、重下载、资金预算、测试按公司特判或原报告覆盖。公开事实丰富是正常独立动作，不成为RF新许可。
