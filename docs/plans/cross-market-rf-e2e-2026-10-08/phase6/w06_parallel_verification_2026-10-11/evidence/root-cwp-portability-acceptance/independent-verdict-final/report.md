# W06-CWP-PORTABILITY 共用 verdict 修复独立复验

**PASS_WITH_SCOPE；无新增 blocker；STOP 交 ROOT 并线。**

## 本轮实跑

- 53 个纯工具案例，0 个不符预期，0.033 秒（不含 Python 启动和导入）。
- 原独审四个误判案例使用原 base report 和原 JSON patch 重放。四个有效输入 SHA 完全一致，现在 S2 与 overall 均为 FAIL。
- Finding 构造器与检查 helper 都默认 FAIL。覆盖每种基础状态与每种显式 outcome，包括 None 诊断；结果单调、与 finding code 名称和排列顺序无关，不修改输入 status map。
- 无特殊前缀的新硬契约能够升级 FAIL；带 false_pass 名称但显式 None 的诊断保持 PASS。未知及错误类型的 outcome 在公开入口得到结构化 INVALID_RECORD。
- 准确的 UNKNOWN、PARTIAL、未完成清理但未丢字节的 PARTIAL，以及身份关系、policy 变化、阻断 socket、测试警告和 SKIP 诊断保持原有分类。

## 保全与范围

11 个冻结产品及 8 个 producer 文件在前后 SHA 校验中完全一致。与前一冻结相比只有 oracle.py、run.py 和本卡 unit 测试这三个产品文件变化。原独审 FAIL、原四个反例及其 base report 未改写；独立 scratch 已恢复为 absent。

已绑定并核对作者最后节点：69 PASS、1 host-symlink SKIP、1 disabled-asyncio-plugin warning，9.07 秒；真实 synthetic Reader/CLI 七场景 PASS，4.051 秒；原文件、空目录及 producer SHA 保全。这里读取现有收据，没有重跑七场景或大测试。此前非作者对 fullRef 错误 size/MIME/schema 拒绝、raw CLI 保存、环境与清理的检查已通过，原审查唯一新增 blocker 就是本次共用汇总修复。

本轮网络、provider、LLM、费用、真实原件访问均为 0。不涉及 POSIX、真实云/Dayu/Dropbox、OCR/LLM 或投资质量认证。4 个 doc_key 仍共 3 个逻辑 source，不能误报为 4 个独立来源。

完整重放、逐项结果与冻结保全信息见 probes.py、results.json；本报告 JSON 与 manifest 是交接接口。
