# N5-RAW-DUP：MAIN集中验收与修正

## 收到的交付

完整分支e40b4ec1c1613fe6ff1e1dd51679e2a7347792b3（代码87a7e60、测试a1418a0），独占tools/raw_duplicate_audit、本线PWF与handoff。MAIN复测原包30项单元/集成6.63秒、Ruff绿；外线生产只读E2E31项总150.40秒已有收据，不重复全量慢测。源码暂存集成后才集中修补，合并提交须此节点绿。

## 必须修正的实际缺口

1. --local-output未独立校验保护根，--overwrite可写入原件或配置；主报告固定.tmp也可能覆盖无关旧文件。先写真实fixture反例：raw/config/catalog/另一输出/已有未知文件一律拒绝且字节不变；主报告临时文件独占随机名，finally清理，不覆盖同名未知.tmp。--overwrite只允许本工具同schema报告，非人审门。
2. hash_file按固定1MiB读取，剩余预算不足一块仍会先超读再报错；恰好文件大小的预算又在EOF前误拒绝。先写非整块硬cap、精确EOF与部分读取账反例；每次读取min(chunk,remaining)，达到初始文件大小即可完成，partial字节必须进入每文件/组/总量，不伪零。
3. Windows GetCompressedFileSizeW在普通文件返回文件大小而非簇分配量，ctypes默认signed restype还可误算大文件。该可选指标改null并说明未测磁盘分配量，保留POSIX st_blocks测量。保留外线历史报告不篡改，根收据明确该字段无效、不能引用为实测物理收益。
4. 云占位候选不进入逻辑上界、不查询allocation、不打开；读取前复核新属性、物理身份、realpath与size/mtime，变化诊断而非重试/猜测。补云属性变化/同大小替换反例，保留一份原件底线。

## 一个验收节点

新反例RED→实现→工具Unit/Integration/Ruff集中一次；真实CLI使用隔离当前schema/真实文件和副本，硬cap partial、复核SHA/报告/原件不变/目录清理，不触碰生产或外部网络。既有生产3组实读证据仅证明158223532 B潜在逻辑副本，并非已释放；7,804,167,537 B仍为登记候选上界，3528组未实读。0原件删除、0LLM/HTTP、不扩日常CI或新门禁。

总PWF、接收JSON和卡状态由MAIN更新；绿后完成真实merge、正常推送与精确CI。DOCSET独立，不改其benchmarks/或PWF。用户config源SHA3609e707保持，RF/IQS/Dayu零写。

## 集中验收结果

首轮17反例16 RED/1 GREEN，实现后49项9.14秒绿；继续查同一节点的报告非组明细与路径诊断，补两个反例修复。路径初断言比较repr而假绿，改为精确静态诊断后真正RED；报告2.69MB反例RED后所有列表有限截断、字节计数固定点修复。最终51项/9.09秒、Ruff、diff check绿，包括两项真实CLI隔离联调。保留原公共来源合同、原件和费用配置，不扩日常CI。

首次清理发现旧ACL测试finally的icacls恢复未检查exit，四个临时文件残留deny-read。移除deny与Set-Acl均失败；核自有tmp绝对路径后仅直接删除四个新夹具，再Remove-Item目录，全部恢复absent。测试改为PermissionError注入，不再改任何真实ACL；最终测试清理成功。

Windows可选分配量现在null。微软[GetCompressedFileSizeW官方说明](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-getcompressedfilesizew)指出普通文件返回文件大小，因此原交付7,804,167,537 B该字段不能当簇分配/实际磁盘收益。历史两报告保持原blob，主收据纠正指标与6字节report-size描述差异。7.27GiB逻辑候选/3组151MiB实读与deleted0保留；3528组未实读，不自动删原件。

截断列出的510组中497组为CWP/Dropbox跨根候选、11组CWP/Dayu，只有1组CWP内部；这只是所列子集，不能外推全部3531组。下一阶段先核独立物理盘/云文件与引用迁移，再决定是否值得做CWP内部一份原件；现阶段不实施全库对象迁移/硬链接，不动Dayu或Dropbox。读取deadline是边界协作检查，不能冒称阻塞文件系统I/O精确可中断。

**Status: local_green，待合并提交对应CI。** [主验收收据](results/n5_raw_duplicate_main_acceptance_2026-10-06.json)、[交付blob事实](results/n5_raw_duplicate_delivery_facts_2026-10-06.json)。
