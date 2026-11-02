# R7 RF 独立审查

结论：**PASS（本次 29 文件冻结改动的独立有界工程审查）**。未发现需要返修的实质问题。本报告不代替跨仓最终 CI、真实公司/H1、付费摘要、缓存恢复或 RF 实际采用验收；Linux 仅静态审查，不冒称本机执行了 Linux。

## 绑定版本与范围

- 作者报告 `R7-RF-implementation.json` SHA-256：`246954d02a40f58471127fb933f65585cd80fe055c20873f5904dff932c9d4ab`。
- 29/29 交付文件在独审开始、结束均逐字节匹配 `delivery_files_sha256`；完整前后 manifest、独立测试源码及日志 SHA 见同名 JSON。
- 独审不写 RF 源码、测试、配置、安装目录或 Git；既有四份 assurance 运行 WIP 的 SHA 与作者记录一致，未修改。
- CodeGraph 查询返回 `.planning` 旧快照而非本次脚本入口，未使用这些旧节点替代当前源码证据，亦未更新索引。入口复核基于已定位当前文件。

## 独立检查结果

新建 12 项合成反控（含参数化项），另执行 1 项既有合法短引文反控。有效结果为首轮 10 PASS，修正独审夹具后 1 PASS，最后 2 PASS。没有把早先夹具失败覆盖成历史全绿，也没有重复作者的 268/61/40 项集合。

| 检查 | 结果与边界 |
|---|---|
| assessment、prompt review、model label 同时损坏 | 原 summary、EvidenceSpan 完整保留；三类 unavailable 观察明确可见，不当作语义通过。 |
| 长中文 research_reason | 全文保留，原问答 context、两条 span 和原 claim 不变，无长度截断。 |
| 移除必要问题上下文／替换来源 parent | 文档的真实 provenance 校验仍拒绝；未用不可信可选诊断绕过。 |
| 错误 fiscal_year 且 assessment 不可用 | 实际 wire 入口仍拒绝。 |
| stdout/stderr 的 None 与显式预算 | UTF-8 两通道分别完整返回 30,000/15,000 字节；20,000 字节显式 stdout 限额仍拒绝，不按字符数计。 |
| None 不取消真实超时 | 本机 Windows 实际子进程被 0.2 秒 deadline 收停，整个调用小于 4 秒。 |
| 索引路径不可写 | 返回自足合法 formal/unattested 结果；原障碍文件不变。 |
| 已重算外层 result SHA 的千倍数值篡改 | 自足预测校验仍拒绝，放松索引不放松计算一致性。 |
| immutable original | 修改输入字典及 getter 副本不改变已验来源；同一原件三个投影累计只作一次原始 body SHA。 |
| 100,001 字符多语 adopted anchor | 全文与结尾计划限定均保留，通过完整 provenance。 |
| 未经证明的可选签名响应 | 仍可 formal，明确 unattested，不伪造 host_signed。 |
| 合法短引文 | 既有真实校验入口不因字符数拒绝。 |

## 控制流与保留边界

`decode_object` 的默认 BODY/RECEIPT/REQUEST 配额已为 None；reading JSON 是迭代遍历，原始有限 JSON/引用类型/源 SHA/时间/主体/期间校验仍在。`read_narrative_context` 的默认 stdout 边界是请求声明的精确 artifact 字节数，不是另一个任意成功结果许可；显式更小下载预算及真实 timeout 仍有效。引用理由是完整文本；结构化 reason code 的协议格式不等于人工签收。

`assessment_observation`、review observation、selection trace/diagnostics 损坏只产生 unavailable/absent；reading group/citation partition、required context、parent source 和完整 anchor 则继续由原 owner 核验。RF 不重新实施 CWP 源材料的业务分类或把诊断的 not_evaluated 变为投资结论。

`VerifiedOriginalRead` 固化 body 和元数据，正常 open → prepare → compose 复用该结果；历史 raw tuple 注入路径重新验真，不能仅靠布尔标志跳过。Source ID/manifest 字段比较保留是投影配对，不重新整份 SHA。

索引 `_append` 不读取旧全链或 chmod，I/O 故障记诊断；正常发布只依赖自足验证。`lookup/audit/rebuild` 是显式维护入口，其坏输入或真正写失败仍报错，不成为发布许可。默认无 signer；选择性签名保留真假标签的边界而不阻断合法未签名产物。

POSIX 分支静态核对：None 限额每次 read 4096 字节，显式限额使用剩余+1 探测，deadline 在 selector 循环内，进程组归属和 finally cleanup 保留。Windows 分支由 Job Object 先归属后运行、kill-on-close 和并发双管道 drain；本轮字节与超时测试实际执行 Windows。没有把外部原文当命令，也没有后台任务或模型调用。

## 失败记录与清理

独审首次快照用例误让 candidate 引用待修改 ref，正确触发 candidate mismatch；复制 candidate 后又使用了两个不受支持的 source_type（company_filing、annual_report），正确触发类型拒绝。最终使用原合同 regulatory_filing，1 PASS。三份失败日志保留；未为此改任何产品代码或旧测试期待。

pytest 自动关闭插件后报告现有 `asyncio_mode` unknown 配置 warning，不影响所选同步用例。pytest 将本次 basetemp 迁到其独占宿主临时目录，每次日志均确认清理。自建 `tmp/r7rf-independent-a2` 初始不存在，独审源码已固化到 JSON 后删除自身目录，清理收据与实际 absent 结果见 JSON；没有删除其他运行产物、pip cache 或用户资料。

后续由 ROOT 集成、提交、推送并按 PWF 完成真实节点；本独审到此 STOP，不扩施工范围。
