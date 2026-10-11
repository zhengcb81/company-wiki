# W04 G1 RF consumer independent review — STOP

结论：在 WP03 已交付的 RF consumer 技术范围内，未发现可复现的责任层契约缺陷。技术审查通过，保留明确剩余事项；不构成公司经济预测质量签收。

审查对象为 RF 隔离分支 `codex/w04-rf-public-consumer-20261011`，head/base `47f497ad9dee9dc47f66fca37016e9ba6b6b6f33`。9 份源码与 15 份封存 evidence 均逐一 SHA 匹配；manifest SHA `f8caa96ce87de895dbd97057028ce10b74da13d9f3ad9a1e206661c56d4ccda8`，rf.diff SHA `e91d09016010aee0abf6099337e7f23e1eab719148d587b371d79cdcd00d15b6`。

| 审查项 | 独立证据与结论 |
|---|---|
| `/3` public request/reference/receipt/body | 精确外层键、generation/ref/receipt 绑定、完整 subject 及 parent lineage 验证；真实封存 body 为 59247 B，65 parents、6 spans，未伪装成单一 SourceRef。每 span 保留原 parent/pointer。 |
| `/1` 历史 metadata | 旧四键兼容，新增声明第五键保留；真实 CN H1 145904 B / 96 spans 的 `language=zh` 与 `declared_language=zh-CN` 共存。 |
| 已登记非期间来源 | 3 个离线正例无需 FF 采集事件字段；9 个错误 FY/period/security 约束被拒绝。invalid acquisition event、unknown document kind 均具名拒绝，无 SEC 回退。真实 US 两原件的已封存 positive proof 已做 SHA 核对。 |
| FF typed sibling | 四种 typed request diagnostic 穿过两个 RF error wrapper，六字段 upstream cause 不变；错误 field_path 被丢弃。真实 FF producer 集成尚未实施/签收。 |
| native snapshot | 子独审 microprobe 确认 3.7/3.8/3.9 的 input/result/header、ID 与 registry anchor 一致；单行 compact、第二次写入拒绝。历史错 header 仅诊断，对象与 registry 字节不变。 |
| 实际叙述消费 | 实际 H1 public read → 实际 verified SourceCapture → explicit rationale claim → `0_base_2026` → `Segment A/base/direct_revenue/revenue/recognized_revenue` → 真正 `run_forecast` 已运行。所有参数值、source records、原输入及公司汇总收入相同；临时 registry 2 条、audit=[]。输入为完整技术 fixture，不是公司经济预测。 |

`/3` 的受测真实 management parent `c620093812d9e420a4847ea0348906e5d167b9dc429a181f223c730c00064271` 在 `as_of=2026-10-08` 下，receipt 2.1 和 2.2 均因 `source_availability_unknown: publication unknown and no reliable prior availability proof` 正确拒绝。未制造发布日期、receipt、FY 或 SourceRef。它说明该实际投影的完整经济输入链仍未验证，不是 consumer 缺陷；后续 WP02/WP06/G2 与 ROOT 跨仓验收仍须处理。

重签 synthetic `/3` 的 decoded-hash、d-end、raw-text 变体被接受，但这改变了调用方的 pinned reference 与 body，并不能证明真实 public transport 可被绕过。producer 明确拥有 decoded 原值及 NFC display 的 replay；该现象不列为缺陷。

本审查仅执行四组定点微探针，没有重跑 204-case 局部大套、WP01 91-check 或旧 RF 284/551 安装套。源码未写入，网络/供应商/模型/新增费用均为零。独有 workspace TEMP 已删除，环境已恢复。首次完整 engine 探针遗漏 registry redirect，首次 append 被 sandbox PermissionError 拒绝；默认隔离 registry 最后写入时间在本审查之前，未完成写入。子探针首次默认 sandbox TEMP 也遇权限拒绝，之后 exact-path 查询不存在；后续在独有 workspace TEMP 完成并清理。

剩余：真实 FF typed sibling producer；有可靠 prior-availability 的真实投影 read/capture/完整经济输入链；公司经济质量重验；ROOT 正常发布/安装、TRUST_BOUNDARY/report 链接和最终跨仓闭环。

详细 hash、断言、失败尝试和复现入口见 `review.json`、`microprobe-results.json` 与 `executed-commands.json`。STOP：G1 不修改工程实现，不 commit/push/install。

附加静态核对：RF 新增的五种 document kind 均已在真实 CWP `SIDECAR_KIND_MAP` 注册，具体原 producer family / RF source_type 映射与源码 SHA 见 `source-kind-compatibility.json`。
