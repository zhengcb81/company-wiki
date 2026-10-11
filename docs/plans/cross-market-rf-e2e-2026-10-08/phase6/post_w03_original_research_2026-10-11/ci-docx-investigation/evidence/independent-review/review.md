# 集中独立审查：changes_required

审查 UTC：2026-10-11T02:05:22.988869+00:00。范围为 native 物理分组、0.7.1 身份/旧版兼容及 CI 调度；不签投资研究结论或尚未发布的新 HEAD 远端 CI。

## 唯一 material 发现

**NATIVE-DOCX-HEADING-01（P2）——真实 DOCX heading 的源结构没有进入 native 单元。**

最小原件 `docx_heading_minimal.docx`（SHA256 `c29c7c0d1a40da78cdf6215bb9675f27773b461af49d71f8e1877136d944702c`）的 `word/document.xml` 第 2 个段落显式带 `w:pStyle=Heading1`，文本为 `Efficiency assumptions`。实际 normalize 后它仍是 `docx_paragraph`，metadata 只有 normalization_schema、format、source_sha256、source_locator、transform，没有 style、heading、outline 标记。

0.7.1 将 heading `cwp-docx-body/1|p=1` 作为 business_group_context / operating_qualification，与后续 qualifier `|p=2` 分成同一组。混合 DOCX 探针还将 heading 两侧段落放入同一组。所有原 locator 都能精确 replay，说明 replay 的正确性没有替代物理语义边界的正确性。实际输入/完整 metadata/FAILED 预期见 `heading-minimal-results.json` 与 `probe-results.json`。

责任行：`docx_parser.py:267–279` 对所有 w:p 固定发出 docx_paragraph 且没有 metadata 参数；`emit():187,203–216` 只复制外部 metadata。新 `narrative_business_groups.py` 依赖 native unit_kind 不同来阻断 heading/paragraph，因此此处缺少源层结构信息。需要保留真实源 heading/style 边界供 0.7.1 使用，并保留 frozen 0.6/0.7 的 parser/locator/replay 身份；补真实 DOCX heading 回归及同段落正控。

## 已通过的核查

- 两源 SHA 审查前、3 个组合探针后、最小 metadata 探针与报告封存前一致，且等于集中 GREEN：business_groups `701876166fa4547483425358475fbaf5d5a91e8171e73fb37bb6f41b4e57f230`；evidence `a04b7d90e9b304e726036e7c14d2463bd0c680a8c2f8f9dcff768cc03c84ee3f`。
- native 物理遍历由 normalize 提供；0.7.1 用 units 序列位置，不以 SHA 或 paragraph/table 独立计数重建物理邻接。三种真实格式混合财表的 Revenue、Net income、12345、67890 均未被重加。DOCX/PPTX 业务 cell 实际独立选中；既有 DOCX 业务 cell 正控保留。
- 实际 HTML heading 正控边界通过。真实 PPTX 不同 shape context 未被加入，同 shape context+qualifier 被加入并能 replay。
- 旧 0.6/0.7 分支保留旧 order/barrier/relation；当前为 0.7.1。集中公共测试断言冻结旧 binding/generation 和 SQLite dump 原样，新的 0.7.1 artifact_version_id 不沿用旧缓存。全 TXT 旧指纹和 96 原公共 locator 的断言保留。
- CI 精确 diff 仅为 push/pull_request 增加 docs/plans/** ignore；生产 src/tests/config 未扩大忽略，仍执行完整 pytest tests/unit。runtime/config 字面路径检查无 docs/plans 依赖；normal prepush 分类工具没有 diff。
- 六份实际日志 SHA 与其 receipt 一致，原失败 CI `38101290406 / 114357569625` 保留 `301bcfd856beef2c1bf469e4f940d2a6d6dd3687835b9b8cc68fa7ea25cf1002`。责任证据为 112 PASS、公共 **3 PASS + 1 FAIL 后只该 TXT 项 1 PASS**、调度 42 PASS；没有声称重跑整包 4 PASS。

## 探针解释和限制

一轮 3 个不同格式组合探针加 1 个必要的 heading 最小化探针，原件和输出全部保留；0 provider/model/付费调用，没有改源码、tests、生产 config 或 canonical。

首轮脚本中“3 个重复业务段落都必须选中”“context 数量必须恰为 1”的预期不适用于既有 n6 whole-group/contained signature 去重及合法的段落组补全；其原始 FAILED 记录保留，但不作为 material 发现。三格式 normalize 都保留 3 个重复文本的独立 unit_id/source_locator。HTML 同文业务 table cell 的省略属于既有去重，不据此扩大修复范围。最小 metadata 探针首次仅证据 JSON 的 nested mappingproxy 序列化失败；修复自有序列化代码后沿用相同输入字节记录结果。

未重复执行 112-unit/4-public 整包。新代码 HEAD 尚未发布远端 CI，该 check 为 BLOCKED，仍由 ROOT 在真实 executor seal 后执行发布门槛。最终建议为 **changes_required**，仅因上述真实 DOCX heading 源结构缺口。
