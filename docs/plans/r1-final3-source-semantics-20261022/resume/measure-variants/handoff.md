# W08 Step3 经营 measure 共因修复交接

## 当前状态与释放范围

工程回归已绿，**policy 文件现在释放给 ROOT**，供后续 guidance 串行实施。未 Git 提交、未发布、未同步安装。生产仅修改 narrative_business_policy.py，新增唯一正式测试 test_reading_operating_measure_variants.py；精确 SHA 在 handoff.json。

## 解决的责任层问题

1. 体积/體積与原有 volume/capacity 进入同一个 quantity owner，明确“提升至/增加至/increased to”等源文关系与 kL/L/m³/m3/cubic metre 的原始词形得到识别。没有单位转换、数据常量或公司例外。
2. 具名业务的收入同比增长/下降与 amount/share 共享局部业务主体和同一 actual-state gate。amount/share 保留原 business_revenue_measure；收入 rate 是既有 direction → operating_metric_change，不伪造 amount/share 或 ObservedMeasure schema。
3. 变化必须带原文明确比较基准；基准绑定在该谓词内、紧跟后缀或裸前置 comparison frame，不能借用同句税费同比。裸财务百分比不因附近业务词或美好叙述变成完整经营 observation。因果消费者仍只消费原来同一个 owner，没有第二套判定旁路。
4. 明年/下一年度/Next year 及未来期间的前置 frame 不会因逗号而失去未来作用域；后置独立未来计划不抹去已经披露的本期同比。

## 证据与范围

最初冻结58项为24FAIL/34PASS，source/test 前后相同；原测试完整快照保留 frozen-initial-test.py（SHA 仍 a1f873d5…）。随后反控依次证明未来 frame、缺失比较基准、跨财务谓词借同比；原 RED 期望未删。

最终新 measure77项全过；相关五文件349PASS；全部 selection（只排除 ROOT 新 OPEN guidance 文件）1110PASS，72.93s，完整源码前后 SHA 一致。初次完整 selection 的10FAIL包括本轮已修的3个既有财务反控和 ROOT 待做的7个 guidance 失败，原 full-selection.txt/xml 保留。排除的 guidance 整份测试不算通过，下一阶段由 ROOT 承接；最终大节点仍须全部跑。

单 policy 类型检查按 CI 实际 Python3.12 通过（1 source file，follow-imports=silent），不是 full-src typing。第一次默认 pyproject3.11 目标因母环境 NumPy stub 要求3.12而失败，mypy.txt 保留，未改配置。Ruff通过。

一条后来新增的“current+later plan”英文夹具原先漏写同比口径，后来补 year over year 使其真正隔离未来独立性；旧版本 pre-local-comparison-controls.py 和对应失败收据保留。原58项输入/期望无此改动，不借 fixture 修改隐藏产品失败。

## 下一步仍属于 ROOT

必须由独立 reviewer 检查本实现；本作者没有自签独审。guidance/forecast、跨段限制条件、真实14组全源选材、正式模型摘要、缓存恢复与 RF 联调均未在本任务宣称完成。policy 已释放，ROOT 可以在其上串行接 guidance；之后不能把本轮旧 SHA 的工程绿直接签到新源码。

0 PDF 原件/下载/副本、0 API/模型/网络、0 Git 写。cleanup-final.json 再次验证全部实际重定位测试目录、请求目录和自有 mypy cache 均不存在。原件、生产配置及外包 W09/W11 没有触碰。
