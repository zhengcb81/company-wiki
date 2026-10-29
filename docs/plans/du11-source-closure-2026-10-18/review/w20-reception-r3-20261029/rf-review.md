# W20-RF-ADOPTION 第三轮 ROOT 独立复验（2026-10-29）

**PASS，范围内 OPEN=0，可由 ROOT 合入主线。** 本轮两项实质返工均已关闭，没有以作者独审签名代替复验。实际工作树HEAD `3e8fbc5522a814abc4db7d828c3e4dcf84f308b8`，产品实现 `f75c9fe253a1f2114e83f0a84e58beb043450f31`（含`956b51d4`材料边/解压修复）。ROOT在实际HEAD独立运行短包 **42 passed / 9.91秒**（40单元+2真实本地子进程e2e，资料为synthetic）。

## 两项返工关闭

- **RF-R2-01 FIXED：** 原始`material_probe.py`原样重跑，两个真实consume run同capture/claim_id/parameter但选择CEO回答与表格行；A forecast+B receipt现在为unverifiable、cited_by空，locator和excerpt hash均发receipt_claim_material_mismatch。匹配的A+A baseline仍used。实现核的是既有consume一次绑定创建唯一claim的材料身份，不普遍要求所有研究quote等于每一份支持、不禁止同参数多个证据；缺可选字段仍unknown。
- **RF-R2-02 FIXED：** 原19B坏DEFLATE经真实CLI子进程现在exit2、input_decompress_failed，无traceback或半输出。仅精确增加zlib.error归一，未抬解压额度或笼统吞异常。

原异源借哈希与fake source_id探针仍unverifiable；同span合法两年采用映射2026/2027完整保留；133B gzip展开100000B仍在1024B额度前拒绝。不是只验证新happy-path。

## 多父、缺hash和多证据兼容

独立`additional_probe.py`重新走经真实wire校验的/3多父context→真实consume→真实forecast：实际父在refs[1]，正常used；缺receipt hash仍used并记录hash_missing_unknown；明确给错refs[0] hash则unverifiable。42项还包括合法两span两claim支撑同参数、拆回执/顺序不变聚合、legacy stray source_locator守护、context-only拒支撑、旧格式及CLI输出保护。

## 精确版本说明（INFO，已在本轮受测）

作者handoff写f75之后仅文档不完全准确：`f75c9fe2..3e8fbc55`还把test_scaling旧`t1>0.02`墙钟下限改为恒执行`t2 < 4*t1 + 0.05`比例加绝对余量，保留items倍数与资源界断言；产品源码未变。本次42项实跑使用实际HEAD，故同时覆盖了这份最终测试；**tested/reviewed commit按3e8记录，不把f75旧测试收据借给新测试。** 这是已澄清记录项，不需再增加签收轮。ROOT可在集成记录统一说明。四份最终源码/测试SHA见`rf-review.json`，与最新交接哈希一致。

## 隔离、证据及验收边界

小脚本/结果/JUnit/cleanup在`rf-evidence/`。作者工区前后clean，未改其代码/索引/安装或合线；测试只在ROOT自有`.planning/w20-reception-r3-20261029/rf`，临时pytest树已核实绝对边界与无symlink后清理，原本不存在的gzip/输出恢复不存在。0外网、下载或模型费用。

本次通过的是W20采用观察工具工程及合成正式产物接线；工具继续明确“无执行追踪/非模型内心/非经济质量签收”。**不代签真实公司RF模型实际采用，也不关闭主线公司循环。** 旧R1/R2问题报告保留为历史。合线由ROOT负责，无需再交作者返工。
