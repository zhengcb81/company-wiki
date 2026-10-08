# HK00700 v4 竞争证据分类修复交接

**实现与执行验证完成，待同一独立 reviewer 复核；完整产品链仍 PARTIAL。**

## 修复范围

- sealed v3的NetEase同行节点只证明跨公司竞争风险，无Tencent正向增长的明确因果桥，不能算作evergreen/new-launch机制的独立正面支撑。
- `inference_distance`改为`contrary`，evidence_type和结论明确竞争风险、analogical同行距离、NET/perimeter不同以及没有测定Tencent份额或替代。单改`analogical`在当前引擎仍会被计入正面triangulation，因此不采用该枚举单改。
- 正式引擎现将Games恢复为`limited`，confidence恢复“Growth driver evergreen_and_launch_monetization is not triangulated across two evidence types and sources”。分值仍64，是工程/证据质量说明，不是未来成功概率。

## 不变及完整验证

- 325条claims和53个参数记录全文保持，来源/capture、其余认定及业务模型保持，原45未来增长率未调。全部收入、CAGR、敏感性与sealed v3逐项完全一致。
- 实际lint、只读hash-check、validate-only、engine、same-source强验证/render、所有45曲线/9合计/15敏感性、immutable snapshot、registry audit/chain/anchors全部通过。输入只有7处分类/说明/版本变化，详见classification_v4.json。
- 188项原TEMP及sealed v3全文件、旧工程manifest/receipts、raw/config逐一SHA/bytes保持。51runtime文件与canonical及v3发出时一致；没有producer/source-facts/Dayu/邻仓/配置/安装写操作。

## 复查入口

- 新研究四产物和独立registry：`C:\Users\郑曾波\AppData\Local\Temp\cwp-rf-e2e-20261008\HK-00700\v4`。
- manifest_v4.json：四主产物真实SHA/bytes、环境、原文件完整性与所有交接路径。
- classification_v4.json：节点前后、7项精确inputdiff、实际输出标签与confidence依赖；repair_v4.json：原审查finding及全部正式命令日志接口。
- v4_delivery_verification.json / v4_registry_integrity.json / after_v4_integrity.json：完整测试和旧文件证据。
- 不运行旧build或v3脚本，不改sealed v3；独立reviewer只审变化依赖闭包。

## 保留限制

- 年报官方同SHA和确切发布日期未证实；日期仅明确的available-asof上界。
- Dayu有界缺文档下载→复用、ET电话会、全公告区间、HK canonical Worker仍BLOCKED/未证明。
- 五业务仍条件direct_growthfallback，无虚构量价/客户分母、无未来实绩回测，无准确率或预测区间保证。

执行者不自行签收。
