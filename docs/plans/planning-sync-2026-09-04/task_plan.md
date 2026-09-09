# 三仓 planning-with-files 全量一致性核对

> 2026-09-06后继：本目录是9/4～9/5历史文档同步记录；当前状态与新一轮同步见[原痛点审计目录](../painpoint-outcome-audit-2026-09-05/README.md)。原全文阅读与hash库存保留，不把历史snapshot哈希当活动文档永久不变合同。verify_sync.py可能因合法活动文档同步报INVENTORY-HASH/SIZE，应使用新目录当前校验并保留差异；不能改旧库存掩盖漂移。

范围由用户明确指定：Projects/company-wiki、Projects/filing-fetch、Projects/revenue-forecast。
目标：完整盘点并阅读根目录/各层子目录的planning文档，对照代码、Git与证据更新实际状态。
只修改文档与本次审计辅助文件，不实施产品功能，不运行生产worker或外发，不改生产配置/数据。

## Phase 1 — inventory / completed

- [x] 获取三仓根目录/AGENTS、HEAD、脏工作树与所有planning组清单。
- [x] 逐项区分活动计划、历史计划、不可变审查证据、导入快照、测试fixture副本。
- [x] 为每份文档记录内容读取覆盖和处理决定，禁止用标题/关键词扫描冒充全文阅读。
- [x] 不可访问目录明确记UNKNOWN；13个revenue临时fixture目录保持UNKNOWN并明确排除于canonical范围。

## Phase 2 — evidence / completed

- [x] 全文读取每份canonical规划文档与关联当前状态入口；执行receipt单独分类，不冒充planning正文。
- [x] 对关键完成/待办声明核对代码、提交、收据/manifest、既有测试结果；区分历史通过和当前重验。
- [x] 不因代码存在就伪造独立review PASS、动态运行成功、用户批准或生产部署完成。
- [x] 核对跨仓FC/WU/ZR/GP状态一致性；对被取代计划明确当前权威入口。

## Phase 3 — docs sync / completed

- [x] 活动文档修正过时状态、矛盾、断链、下一步与日期。
- [x] 历史append-only/冻结文件保留字节，通过非冻结CURRENT_STATUS/索引标记历史地位和替代入口。
- [x] 已有其他任务改动不覆盖；revenue并发漂移后废弃旧patch，按2cbd585重审重编。
- [x] 外部两个仓库写入走明确权限通道，只应用通过独立复核且CAS匹配的文档patch。

## Phase 4 — verification / completed

- [x] 独立审查关键状态变更与全部覆盖清单；first-stage、pre-apply与final post-apply均有明确verdict。
- [x] 检查链接/状态合同、现有不可变manifest和v5 import完整性。
- [x] diff只包含明确文档变化；记录未完成/不可证实项，不伪称全部功能通过。
- [x] 输出逐仓总结、变更清单和全部检查范围。

## 错误记录

- 沙箱Git读取两个外部仓库提示dubious ownership；以只读授权查询解决，未设置global safe.directory。
- 初次全Markdown清单混入大量测试fixture并截断输出；改为先保存/分组planning清单再分批全文阅读。
- PowerShell foreach语句直接接管道解析失败；改用ForEach-Object后取得文件尺寸，未写文件。
- 一次findings补丁使用错误标题上下文被完整拒绝；重读精确原文后重新应用，不存在部分写入。
- rg误入.pytest_cache被拒；缓存不作为活动计划，后续明确排除，未改变权限。
- metadata清单JSON被rg权限诊断前缀干扰解析失败；全层缓存排除，并识别JSON明确起点后完成盘点，不计语义全文覆盖。
- filing外仓补丁首次经批处理包装调用时因末行换行形态被`apply_patch`完整拒绝；确认无部分写入后，改用已核验patch文本直接调用Codex apply-patch入口并成功。
- company inventory首次批量状态补丁比实际`prior_work`条目多写了两个重复hunk，补丁原子拒绝；重新按唯一path上下文生成精确补丁后成功，未发生部分写入。
- revenue全文审计agent在补读后段触发用量上限而中断；已保留其审计日志并于2026-09-05派新独立agent从文件游标继续，未把中断当成完成。
- revenue续读agent第二次在后段达到用量上限；已完成区间均落盘，随后把剩余ADR/remediation/范围复核拆成三个短独立任务完成，避免第三次从头重读。
- 一次PowerShell带行号输出使用`"$i:..."`触发变量解析错误；改用`-f`格式化后成功，无写入。
- 读取最新revenue log时Git再次因dubious ownership拒绝，但同一命令中的普通文件读取成功；未修改global safe.directory，HEAD由独立只读范围审查确认。
- 一次试图直接修改patch中并不存在的目标表格正文，`apply_patch`原子拒绝；改为向patch文本增加第二个目标文件hunk，无部分写入。
- 合并读取unified state与多个README时输出被截断；不把该输出当state全文覆盖，状态结论仅采用已解析机器字段和独立清单/hash复核。
- revenue补丁首次应用调用了已随Codex升级失效的旧版本化`codex.exe`路径；PowerShell未把“命令不存在”转成可靠LASTEXITCODE，尾部误打印成功标记。立即核对根状态页仍不存在、六目标hash不变，确认零写；随后通过`Get-Command codex`定位当前入口，重新做HEAD+patch+六CAS检查后成功应用。
- 原post-apply reviewer在最终复核中触发用量上限；预应用PASS及复核日志已落盘，另派一个全新短范围独立agent完成post-apply审查，不把中断当PASS。
