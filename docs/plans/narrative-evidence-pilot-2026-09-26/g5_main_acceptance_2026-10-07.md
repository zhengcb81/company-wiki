# G5 三包：MAIN 接收、接线与并线

## 当前状态

in_progress。用户已报告三包完成并要求查收；三个工作树 clean、handoff 均 `ready_for_main`。MAIN 已实读变动代码、责任反例与接线表，尚未把外线 GREEN 报告当成主线验收。

| 包 | 实现 / 交付 tip | MAIN 责任 |
|---|---|---|
| CWP-CHECKS | b3e7f74 / 9aa2dbb | 合入六个纯 stdlib 退休薄壳与测试；更新现行 caller 分类文档；当前 G2 获取代码和合入后 Unit/E2E 一次集中验收 |
| SID-RUNTIME | 7a4bf0d / 47e1059 | 快进实际 `v2-clean-rewrite`，保留11个 owner tracked 改动及未跟踪资料；真实无 org_id/cache 请求与 CWP 消费执行，零浏览器/外网，不称不存在的CI绿 |
| RF-INSTALL | a2116ca6 / 0d8b5ded | 快进 main，保留三 owner 日志；33个定点安装责任/真实三 tmp 目录 E2E；合入后真实安装仅同步卡定义8文件，核24逻辑候选/2物理根，无额外文件或目录删除 |

## 接口与保留边界

- CWP 六旧脚本统一 exit78/退休标记，无模型、Store、复制目录或新收据。canonical 来源/定位/预算/恢复职责保留；gold 真实坏来源/未来公开/定位反例留在测试内。
- SID adapter 仍 `stockinfo-cninfo/1.3.0`、原候选/receipt/budget wire；identity 查询计入同一字节与时间预算，无强加 org_id 请求字段；Dayu/IQS零写。
- RF `--file` 是定点选择，`--plan` 仅零写诊断，不是许可文件。部分失败需准确报告 written/not_written/conflicts，重跑收敛；用户 config/output/安装内旧 tests 等未选文件保留。
- RF 当前兼容 manifest 的 CWP pin 仍旧；MAIN 本次获取链发布要更新真正已发布代码组合，避免 FF CI 使用旧 CWP。该文件由 MAIN 管理，不属于外包写集。

## 大节点与发布

1. G2实际 FF/ET/CWP 离线链已 passed：CN v1/v2下载一次、重复0下载；US原件复用、真实ET worker一次HTTP夹具获取/入库/重复0调用。真实binary source reader校验四份返回字节，未知公开日保持未知。测试根恢复absent、生产和原件不变，付费/翻译0。供应商身份/HTTP为明确fixture，不冒称live下载。
2. MAIN 先正常提交已验证G2源码，再合入G5CWP；在合入结果执行 CWP Unit及G5真实退休 E2E，SID责任/实际CLI节点、RF33责任/tmp E2E并行运行且测试根互不重叠。不反复重跑外线已绿全套。
3. 实际安装定点 apply 在合入后做，先按8个文件 read-only plan 与保护指纹核现状，后读真实安装help/version和幂等；不整套替换/目录清理。
4. 责任节点绿后正常提交推送；CWP/RF/FF各自新代码精确CI，SID无workflow。仅收据/Markdown跟进不重复长测试。所有owner保护与临时根恢复结果写小JSON。

## 尚未完成

本页in_progress不代表全部G2或PWF完成。生产metadata、正式生产摘要及RF/StockWiki消费、R5最终收口仍需按总计划执行；模型配置与200000 tokens/$0.12累计额度不改。
