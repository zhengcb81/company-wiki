# 发现

2026-10-13：CWP基线eeca43dd876579e82f02f1bfaaa9126d597096a0，RF b9208a2117b8423f4b355dfca885aaf0d56a05bb，FF 64b4d294a1e61e595e330b4a7d4075c289f9fdc3。三仓CodeGraph均已初始化，可做结构审查。RF原有assurance/runs的daily_alert、weekly_alert、weekly_manifest修改及output保持；FF/CWP已跟踪文件干净。

文档理解已确认共享引擎＋多份阅读策略，profiles/structure/benchmark三包正在其他harness施工。质量线不写这些包及冻结DU/1接口；由ROOT防止重复改造。其他结论待独立审查证据，当前不宣称存在全部类别缺陷或已完成全面升级。

## A阶段根因与协调

- CWP：写入去重依赖历史absolute_path而非当前RootSpec+relative_path，与读取侧虚拟化存在职责分叉；多处同PID临时文件提交有并发冲突。由该agent验证反例，复用存储定位，抽取一次性文件原子替换，保留不可变raw的独立并发语义。
- FF：配置token/JSON在入口、ET、doctor重复实现；query/ensure的pathless候选投影不一致，嵌套物理字段可穿透query；日期仅匹配格式，不判断真实日历。根因由共享解析/投影收敛，不增加许可。原“query缺hash一致性”初步怀疑已撤回，共享validate_handle_metadata已有该检查。
- RF：计算/研究/叙述消费分别遍历依赖，叙述只认model driver，遗漏carry-in/progress/并表adjustment；研究用carry-in长度==horizon导致短lag原生依赖漏掉。共享用途visitor及derived ancestry，数值引擎保持原计算顺序。内容manifest仅hash文件名而不是内容，且安装工具持另一份包清单；统一runtime可安装包的清单/指纹。极大数/非法幂应报ForecastInputError，不抛裸异常。CodeGraph索引片段落后于当前主线，结构定位后读取具体文件判定真实行为；不能据旧片段声明已删除或未实现。
- ROOT：Windows rg不展开参数中的glob；改用目录＋-g过滤，不重复错误搜索。下一步集中跨仓复用/虚拟化/数学输出回放，付费真实摘要和公司审查仍属母计划。

## 集中节点新增实证

- ROOT三公司core现主线回放32PASS及1FAIL：HK两claim引用同业务表但各谈H1下降/Q2改善，RF把excerpt hash当命题ID导致误拒。修正机器可证明的范围，不将同物理引用直接当逻辑矛盾；真同claim/同命题双用仍拒绝。冻结输入不改，测试目录已恢复。
- CWP新reader/writer原生迁移及并发131项已过；配置30新TDD中15在原基线失败，修复后全绿。既有架构契约还捕获local_reconcile.root.kind布局双分支；布局属adapter，不是存储根名，ROOT已安排收敛而不放松测试。正式交接计数以各仓最终报告为准。

## 最终工程节点

本地主线CWP1f9f0673、FFe2efa81d、RFf0d694d6。ROOT247.189秒完整离线真链48PASS/0FAIL（原基线腾讯formal FAIL消失），正式三公司数值/快照/原文复用/移根保持；HTTP fixture FF→ET→CWP PASS。整体PARTIAL来自offline不做的真实供应商/研究与已具名HK fresh出处、offline_no_OCR图片PPTX，不是发现错误后改PASS。

九型finite G2全部PASS（66.658秒），9实际RF读取、8首批loopback POST/0复用/2版本失效POST；0远端模型费用。展开38文件226,324字节逐字节归档为60,309字节ZIP后删除自有展开副本，owned根恢复，原件没有删除。真实摘要质量仍由母计划供应商及独立四审验收。

部署根因已系统收口：FF低层copy明确scope状态与完整runtime drift分开、执行NOT_EVALUATED；ROOT先完整plan再定点应用、fresh入口核验。发现.codex FF1旧依赖、RF7旧依赖/说明后分别定点补齐，未全目录覆盖或替换用户config。RF退休队列作为历史工具保留Git/legacy回放，生产无enqueue/发货；原schema/model会计常量及有实际调用的wire/attestation不盲删。

最终发布事实：三仓全部主线/远端及精确CI通过，完整owned安装闭包和fresh运行已核。冻结旧实现只保留有实际legacy调用的边界，生产ghost queue已退休；协议/货币/数学模型常量没有任意配置化。ROOT不宣称逐行证明无任何缺陷：真实资料/模型语义、DU策略召回仍按母计划验收，避免工程绿取代业务质量。
