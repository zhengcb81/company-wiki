# DU11-FF ROOT 独立验收

## 结论：CHANGES_REQUIRED

本地电话会 TXT 优先复用、缺失只下载一次、随后复用的主链路有效；两项新的独立反控发现必须修复的问题，当前不建议并线。原作者独审有效但没有覆盖这两种反例，不能以作者测试通过替代 ROOT 接收审查。

## 版本与范围

- 作者 HEAD：`8a83e27863269b14c897dc2c7ba953f3b9102ef1`；基线 `f1a939e522c22b23659712a8bd2b344f5eb0a364`。
- 作者独审绑定 `5dee9a20c1c5952688673caf784fdce4e9391a50`。从该版本到最终 HEAD 只有计划/收据变更，实际实现未变；独立核对源码 SHA、Git 差异和干净状态。
- 实现只改三个 transcript 脚本；测试为四个 DU11 模块、一个新合成 fixture；其余为本包计划。未改 FF 请求/配置、原 41 矩阵、CWP/ET/Dayu/IQS 或安装技能。
- 三源码 SHA：`transcript_companion.py` = `7e3f28a5928270850af308b9d20f4187cbaa985f1e0a5b4dffb83c3a1c0084be`；`transcript_tool_transport.py` = `20f8903df96af64de94d3ce6959ecdb0a36555589f6c410a8e83e9f9a6276999`；`transcript_reuse_selection.py` = `8591e9968d5d23c4e056a32062ea4b4fdbac63c3421523d921f3176d93823231`。

## 独立离线复验

只从作者提交创建自有隔离源码快照，没有在作者工区执行脚本。最小系统运行环境、不继承凭证、不加载 dotenv、禁用自动 pytest 插件，`-B`、无 pytest cache、专用 basetemp；网络审计保护传播至 CLI 子进程。所有数据为合成 fixture，无实际原件复制。

**102 PASS，0 FAIL，0 SKIP，52.72 秒；网络尝试 0。** 其中 99 项为 selection/contract/恢复夹具测试，3 项是真实 FF CLI / CWP 公共入口链路：

1. 已登记 TXT 经查询与 reader 验 SHA 后复用；不调用 ET。
2. 未知发布日期保留 excluded 诊断，不下载、不读原文。
3. 缺失时通过合成 ET 下载一次，经真实 CWP import/read；下一次请求纯复用。

CWP 执行依赖固定 `34a7dd71aaa49d18c13fcdd300ce79581114ca5b`，ET 是离线进程 fixture，不冒称真实联网供应商验收。精确命令、XML、源码清单和 archive SHA 在同目录 `du11-ff-independent.json`。

## 必须修复

### P1：最终 reader 发布日期仍可能错误声明 as-of 合格

`transcript_tool_transport.py:457` 的 `_manifest_published_date` 接受任意字符串；最终 manifest 日期为 None 时回退旧查询日期。`:534–540` 只判断日期是否存在，没有重新验证当前日期有效性与截止时间。

最小反例：请求截止 `2026-09-30`，查询曾返回合格日期 `2026-07-22`，同一 SHA 原文的最终 reader manifest 分别返回 `2027-01-01`、`not-a-date`、None。三个真实 FF companion/transport 控制均得到 `reused` 与 `as_of_cutoff_verified=true`；None 还被旧日期掩盖。四个控制均没有 provider 调用。

根因是将查询时资格当作永久事实，而原文 SHA 不绑定当前可变元数据。应由来源责任层提供当前资格或严格拒绝查询/读取之间变化；未知、无效或晚于 as-of 不得变成历史合格，也不得作为缺失触发重复下载。已有 date primitive / source qualification 可以复用，不需要人工许可。

### P2：FF 再次引入不分市场的证券代码归一化

`transcript_tool_transport.py:486–503` 对所有市场执行 `lstrip("0").casefold()`。US 请求 MSFT，查询返回 MSFT，最终有效原文字节 manifest 却为 US / `0MSFT`，实际 FF 仍返回 `reused`。通用 AAPL 错配测试不能覆盖这个反例。

CWP 已有 market-qualified `security_code` 单一 owner：HK/CN 仅在已知市场内处理数字补位；US 保留前导零、点和连字符；未知市场不能借请求补成已知身份。FF 应消费该 owner 的 canonical 投影并保留 observed manifest，而不是再写第二套身份规则。兼容旧 receipt 时可严格相等或如实 unresolved，不能错误合并证券。

两项修复均需保留真实字节 SHA、期间和 as-of 约束，补正反控后独立复审；不增加下载/人工签收门禁。

## 清理与证据限度

作者工区状态和所检查源码/测试/fixture 字节均未改变；专用 sentinel SHA/mtime 未变，自有外层 Temp 已删除。没有生产配置、原件、密钥、网络或收费调用。

独立收据的 snapshot post-check 有一个明确的行尾比较错误：两个 test/fixture 的 Git archive LF 与作者工作树 CRLF SHA 比较被标 false，逐文件 LF 规范化已证相同。三个产品脚本 post-check 均 true，作者原文件仍未变。快照已删除，未保留那两个快照的实际 post-hash，不能补造全文件 post-hash PASS。初始快照仍由提交与 archive SHA 绑定；更正保留在 JSON 中，不隐去原标志。

作者全套结果为 1320 PASS / 9 FAIL / 16 SKIP；其复审仅证 8 项在基线复现，第 9 项是并行 CWP 状态 guard，不将整套称绿。当前 ROOT 最新 CWP 契约未在此包执行；未验证真实供应商调用、任意语言偏好或全部并发崩溃恢复场景。原文原语言复用已覆盖，但请求没有语言偏好字段，不能声称已实现语言筛选。

报告是独立接收结论；没有修改作者实现、生产运行时、索引、HEAD，没有合并或推送。
