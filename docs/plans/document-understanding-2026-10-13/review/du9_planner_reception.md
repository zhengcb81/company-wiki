# DU9 PLANNER 接收与跨组件验收 — 2026-10-17

## 当前结论

**组件及真实 POLICY 接口联调通过，已发布且精确远端 CI 成功。** 保留完整作者历史 e4f946a2（受审源码 db126f24）合入主线 f4ef8531；ROOT 两项共因修复冻结 a4ca0a85。独立审查 PASS / 未解决0，11个最终源/测试/fixture SHA 读回一致。[独审报告](du9_planner_root_review.md)、[机器收据](du9_planner_reception.json)。作者原工区只读。

## 发现与修复

1. 旧公平预留只算页数，忽略更紧请求数。64页/2请求时前部吃光请求，后部项目虽有名额仍无法读。以 min(页限,请求限) 统一可执行容量，未提高预算。
2. 旧逻辑把唯一扣费归因当作唯一读取意图，吞掉同页嵌套 fine。现在合法 reserved 覆盖规则合并 discover/fine，同父文同物理页仍仅扣一份；取消规则不能借其他规则激活 fine。

ROOT 先保留2FAIL/5PASS，修复后集中796PASS/17SKIP（25.46秒）；独立审查另以不变反例从7PASS/2FAIL复放到9PASS，并实际运行55项 planner 测试通过。范围重叠，计数不可相加。原64/64手算gold不改。旧单请求测试改独立单类夹具，仍严格断言quota1/花费1/第二次拒绝，去掉不合理的“先到行政必须拿到公平名额”假设。

## 可复现与清理

集中执行命令及第一次RED在[收据目录](du9-planner-receipts)。独审原运行路径保留在报告中；reviewer_probe.py及前后JSON现逐字节保存进该目录，原路径→保存路径→SHA见接收JSON。归档probe依赖原有目录布局且会写同目录收据，不在归档位置直接运行。可复现的固定回归从仓根运行 `python -B -m pytest -q -p no:cacheprovider -o addopts= tests/unit/du9_geometry_planner`；如重放独审probe，应先在独立临时目录适配ROOT/HERE输出位置，保留归档字节与前后收据。0供应商、0下载/原件复制、0生产配置写入、0作者工区写入，自有临时目录清理、sentinel内容与mtime不变。未清理此前无关 .planning 证据。

## 保留边界与下一步

本次证明纯组件/真实编译策略、预算、去重和JSON恢复。not_arrived仅指reserved-but-unused，不是实际未访问页面事实。性能实测50/300/1000窗约0.4/1.7/6.8ms/admit，不承诺作者泛化的亚毫秒；当前64页上限未实证阻塞，不扩加许可或防伪链。

随后由ROOT独占生产接线：native windows→唯一matcher→POLICY→PLANNER→同一WorkBudget→source单parse，再做真实PDF深页表格、实际配置供应商正式摘要、缓存恢复及未见公司质量验收，见[下一默认深页实施](pdf_page_intent_implementation.md)。这些仍OPEN，不把本组件通过写成全项目完成。RF/ET作者任务保持只读等待，FF完整41例C和完整中断恢复仍是ROOT责任。

旧du8-du9定时任务更新返回“不存在，可能手工删除”，因此未重建；不能承诺后台巡查仍有效。其余自动任务不受影响。

## 发布完成

主线与origin已正常推送 c300e801fd4d3735078ec4b77ced26ddb3a5a59d（包含完整作者历史及a4ca0a85修复）。pre-push 6336PASS/24SKIP、311.06秒，无skip-hook；[精确CI39008113871](https://github.com/zhengcb81/company-wiki/actions/runs/39008113871) SUCCESS，06:00:37Z完成。[发布收据](du9-planner-receipts/publication.json)。其后仅补本发布文档，源码/测试冻结不变。
