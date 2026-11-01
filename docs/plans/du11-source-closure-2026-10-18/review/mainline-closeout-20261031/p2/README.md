# P2 华利同一真实摘要的native采用验收

**有界工程验收通过，整家公司经济研究仍OPEN。** 不以形式发布或旁收据代替完整公司四审；不替Berkshire/P1总体或P3签收。

RF已[0559d75c](https://github.com/zhengcb81/revenue-forecast/commit/0559d75c928695306ee1d3f95c2d5368176ff397)根修、[535604fa](https://github.com/zhengcb81/revenue-forecast/commit/535604fa468e8a69be44e073dc7e29eacde80cbc)并线推送，精确[CI41254752622](https://github.com/zhengcb81/revenue-forecast/actions/runs/41254752622)成功；正常pre-push679P+36subtests/71.88s。首commit的CI材料缺失失败保留，未删除断言或扩大CI；在无docs夹具工区复现1F，6份原字节夹具归tests，81P及独审通过。

完整t3五段support+一段context、采用理由、artifact和summary SHA、原文定位、实际parameter/formula依赖随native input→forecast/report→snapshot持久。原生claim的短excerpt明确只是定位锚，未让首段代替完整语义。旧无summary-use行为保留；闭包复用一个owner，投影复用既有wire。计算/展示层不读目录、不解析PDF、不调用模型、不造授权链。

实际来源准备经FF→CWP→新浪接口取2024/2025基线，再请求0HTTP；API unit/scale null原样保留，用FF→CWP→StockInfoDLSimple实际缺年报下载和官方原文核对人民币元/营收值/万双，第二FF请求0下载。早期配置/序列化/查询夹具失误留证；曾发生两次隔离年报下载（v3,v4），不冒称整个实验只下载一次。规范化一次8452span/10.20s，后续只读派生材料。

actual v5采用同一已付费M8 body ec1831a2...；0新增POST/下载，必要CWP定位回放实执行。1%实际参数扰动对Footwear/base和合并收入生效、Other及其他情景不变，6断言通过；32独立离线检查通过。代码与产物SHA见[最终独审](review-v5-final.md)，测试材料迁移见[独审增补](fixture-migration-addendum.md)。

RF三份逻辑技能入口已按canonical安装器定点部署8运行文件；.claude是.agents别名，实际2物理目标/16处变化，不是3物理副本/24次写入。重复安装零写，三逻辑入口在3个新进程验证真实冻结输入通过；配置/输出不在部署范围。主仓3份外来定时assurance WIP哈希保持不变。

测试新下载的年报压缩副本及整篇规范化已删除，释放4662644B；保留62份实际使用的原文span/哈希/获取收据。原有华利IR与Dropbox Berkshire原件SHA均不变。临时测试湖和publication registry均恢复清除；不复制整库备份。早期坏前缀负例假绿、compact subject中间5F和旧零解析误述不覆盖为PASS。

2023IR只作历史机制：部分客户下降、其他增长、新客户预计部分补缺，不能写完全抵消、2026新订单/产能或当年管理指导。FY2026销量/单价情景显式条件假设；最新2026沟通、独立需求/竞争与校准仍缺。正式input/report/snapshot留在RF的自有PWF包，本仓仅存来源/工程审计记录。离线重现用RF review/replay.py；新下载的测试PDF已清除，不声称可不获取任何原件就重做完整来源E2E。
